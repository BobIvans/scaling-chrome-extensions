"""Action records/outbox/skills in the canonical Core SQLite, with no worker.

Execution is admitted by Core's existing jobs/leases/cancellation mechanism.
Adapters are operator-owned code, never model-supplied commands or selectors.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import time
import uuid

from automation_core import connection, digest, encoded, event, identifier
from action_intent import compile_intent, exact, registry, text


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS action_control(id INTEGER PRIMARY KEY, stopped INTEGER, epoch INTEGER);
        INSERT OR IGNORE INTO action_control VALUES(1,0,1);
        CREATE TABLE IF NOT EXISTS action_intents(id TEXT PRIMARY KEY, revision INTEGER, payload TEXT, compiled TEXT, state TEXT, policy_digest TEXT);
        CREATE TABLE IF NOT EXISTS action_inputs(intent_id TEXT, revision INTEGER, payload TEXT, PRIMARY KEY(intent_id,revision));
        CREATE TABLE IF NOT EXISTS action_targets(id TEXT PRIMARY KEY, revision INTEGER, payload TEXT, identity_digest TEXT, state TEXT);
        CREATE TABLE IF NOT EXISTS action_packets(id TEXT PRIMARY KEY, intent_id TEXT, revision INTEGER, count INTEGER, sha TEXT, state TEXT);
        CREATE TABLE IF NOT EXISTS action_parts(packet_id TEXT, ordinal INTEGER, part_id TEXT, sha TEXT, raw BLOB, PRIMARY KEY(packet_id,ordinal), UNIQUE(packet_id,part_id));
        CREATE TABLE IF NOT EXISTS action_attempts(id TEXT PRIMARY KEY, job_id TEXT, packet_id TEXT, ordinal INTEGER, target_id TEXT, target_revision INTEGER, identity_digest TEXT, state TEXT, invocations INTEGER, observation TEXT, UNIQUE(job_id,packet_id,ordinal));
        CREATE TABLE IF NOT EXISTS action_attempt_prompts(attempt_id TEXT PRIMARY KEY, payload TEXT);
        CREATE TABLE IF NOT EXISTS action_coverage(packet_id TEXT, part_id TEXT, source_version TEXT, kind TEXT, payload TEXT, PRIMARY KEY(packet_id,part_id,source_version,kind));
        CREATE TABLE IF NOT EXISTS action_results(id TEXT PRIMARY KEY, intent_id TEXT, revision INTEGER, payload TEXT, sha TEXT, UNIQUE(intent_id,revision));
        CREATE TABLE IF NOT EXISTS action_skills(id TEXT, version TEXT, payload TEXT, code_digest TEXT, state TEXT, PRIMARY KEY(id,version));
        CREATE TABLE IF NOT EXISTS action_skill_deps(skill_id TEXT, version TEXT, dependency TEXT, digest TEXT, PRIMARY KEY(skill_id,version,dependency));
        CREATE TABLE IF NOT EXISTS action_failures(id TEXT PRIMARY KEY, skill_id TEXT, version TEXT, payload TEXT);
    ''')


class ActionRuntime:
    def __init__(self, core, adapter=None):
        self.core, self.store = core, core.store
        self.config = registry(core.policy.get('actions'))
        self.adapter = adapter
        db = connection(self.store)
        try:
            initialize(db)
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        db = connection(self.store)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _intent(self, db, intent_id):
        row = db.execute('SELECT * FROM action_intents WHERE id=?', (identifier(intent_id),)).fetchone()
        if not row:
            raise ValueError('ACTION_INTENT_NOT_FOUND')
        if row['policy_digest'] != digest(self.core.policy):
            raise ValueError('ACTION_POLICY_CHANGED')
        return dict(row)

    def _admit(self, db, intent_id, revision, job=None):
        row = self._intent(db, intent_id)
        if type(revision) is not int or row['revision'] != revision or row['state'] != 'COMPILED':
            raise ValueError('ACTION_REVISION_FENCED')
        if db.execute('SELECT stopped FROM action_control WHERE id=1').fetchone()[0]:
            raise ValueError('ACTION_STOPPED')
        if job:
            current = db.execute('SELECT * FROM jobs WHERE id=?', (job['id'],)).fetchone()
            if (not current or current['state'] != 'RUNNING' or current['cancel_requested'] or
                    current['lease_token'] != job['lease_token'] or current['lease_until'] < time.time()):
                raise ValueError('ACTION_JOB_FENCED')
        return json.loads(row['compiled'])

    def create(self, value):
        compiled = compile_intent(value, self.config)
        key = uuid.uuid4().hex
        with self.transaction() as db:
            db.execute('INSERT INTO action_intents VALUES (?,?,?,?,?,?)',
                       (key, 1, encoded(value), encoded(compiled), compiled['state'], digest(self.core.policy)))
            db.execute('INSERT INTO action_inputs VALUES (?,?,?)', (key, 1, encoded(value)))
        return {'intent_id': key, 'revision': 1, **compiled}

    def get(self, key):
        with self.transaction() as db:
            row = self._intent(db, key)
        return {'intent_id': row['id'], 'revision': row['revision'], 'input': json.loads(row['payload']),
                **json.loads(row['compiled']), 'state': row['state']}

    def correct(self, key, revision, value):
        compiled = compile_intent(value, self.config)
        with self.transaction() as db:
            row = self._intent(db, key)
            if type(revision) is not int or row['revision'] != revision:
                raise ValueError('ACTION_REVISION_CONFLICT')
            # Original text/transcript belongs to its immutable first input.
            original = json.loads(row['payload']).get('original_text', json.loads(row['payload'])['text'])
            value = dict(value, original_text=original)
            db.execute('INSERT INTO action_inputs VALUES (?,?,?)', (key, revision + 1, encoded(value)))
            db.execute('UPDATE action_intents SET revision=?,payload=?,compiled=?,state=? WHERE id=?',
                       (revision + 1, encoded(value), encoded(compiled), compiled['state'], key))
            for job in db.execute("SELECT * FROM jobs WHERE state NOT IN ('SUCCEEDED','FAILED','CANCELLED','BLOCKED')").fetchall():
                payload = json.loads(job['payload'])
                if payload.get('kind') == 'action_plan' and payload.get('intent_id') == key:
                    state = job['state'] if job['state'] in {'RUNNING','NEEDS_RECONCILIATION'} else 'CANCELLED'
                    db.execute('UPDATE jobs SET cancel_requested=1,state=? WHERE id=?', (state, job['id']))
                    event(db, job['id'], state, {'reason':'INTENT_SUPERSEDED','revision':revision + 1})
            db.execute("UPDATE action_attempts SET state='EFFECT_UNKNOWN' WHERE job_id IN (SELECT id FROM jobs WHERE cancel_requested=1) AND state='SEND_ARMED'")
        return {'intent_id':key,'revision':revision + 1,**compiled}

    def enqueue(self, key, revision):
        # Use Core's jobs table and event owner in the same admission transaction.
        with self.transaction() as db:
            compiled = self._admit(db, key, revision)
            payload = {'kind':'action_plan','intent_id':key,'revision':revision}
            task_key = 'action-' + digest(payload)
            old = db.execute('SELECT id,state FROM jobs WHERE task_key=?', (task_key,)).fetchone()
            if old:
                return {'id':old['id'],'state':old['state'],'reused':True}
            job_id, now = uuid.uuid4().hex, time.time()
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,'QUEUED',0,1,?,0,NULL,0,'{}','{}',?,?)",
                       (job_id,task_key,encoded(payload),digest(payload),digest(self.core.policy),now,now,now))
            event(db,job_id,'QUEUED',{'intent_id':key,'revision':revision,'semantic_hash':compiled['semantic_hash']})
        return {'id':job_id,'state':'QUEUED','reused':False}

    def stop(self):
        with self.transaction() as db:
            db.execute('UPDATE action_control SET stopped=1,epoch=epoch+1 WHERE id=1')
            for row in db.execute("SELECT id,state FROM jobs WHERE state NOT IN ('SUCCEEDED','FAILED','CANCELLED','BLOCKED')").fetchall():
                state = row['state'] if row['state'] in {'RUNNING','NEEDS_RECONCILIATION'} else 'CANCELLED'
                db.execute('UPDATE jobs SET cancel_requested=1,state=? WHERE id=?',(state,row['id']))
                event(db,row['id'],state,{'reason':'INDEPENDENT_STOP'})
            db.execute("UPDATE action_attempts SET state='EFFECT_UNKNOWN' WHERE state='SEND_ARMED'")
        return {'state':'STOPPED','remote_cancellation':'NOT_ASSERTED'}

    def resume(self):
        # Resume admission, never resurrect cancelled jobs or unknown sends.
        with self.transaction() as db:
            db.execute('UPDATE action_control SET stopped=0,epoch=epoch+1 WHERE id=1')
        return {'state':'READY','unknown_attempts':'RECONCILIATION_REQUIRED'}

    def bind(self, handle):
        adapter = self.browser()
        observed = adapter.observe(handle)
        exact(observed, {'origin','account','workspace','conversation','focused','contract_digest'}, {'repo','branch'})
        if not all(observed.get(k) for k in ('origin','account','workspace','conversation','contract_digest')):
            raise ValueError('ACTION_TARGET_IDENTITY_UNAVAILABLE')
        identity = {k:v for k,v in observed.items() if k != 'focused'}
        key = digest(identity)
        with self.transaction() as db:
            old = db.execute('SELECT * FROM action_targets WHERE id=?',(key,)).fetchone()
            revision = old['revision'] + 1 if old else 1
            payload = {'identity':identity,'handle':handle,'adapter_version':adapter.version}
            db.execute('INSERT INTO action_targets VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,state=excluded.state',
                       (key,revision,encoded(payload),digest(identity),'BOUND'))
        return {'binding_id':key,'revision':revision,'identity':identity,'state':'BOUND'}

    def browser(self):
        if self.adapter is None:
            from browser_cdp import BrowserAdapter
            self.adapter = BrowserAdapter(self.config.get('browser'))
        return self.adapter

    def _target(self, db, target_id):
        row = db.execute('SELECT * FROM action_targets WHERE id=?',(target_id,)).fetchone()
        if not row or row['state'] != 'BOUND':
            raise ValueError('ACTION_TARGET_REBIND_REQUIRED')
        return dict(row), json.loads(row['payload'])

    def check_target(self, target):
        adapter = self.browser()
        if adapter.version != target['adapter_version']:
            raise ValueError('ACTION_ADAPTER_STALE')
        observed = adapter.observe(target['handle'])
        if not observed.pop('focused'):
            raise ValueError('ACTION_USER_TAKEOVER')
        if observed != target['identity']:
            raise ValueError('ACTION_TARGET_REBIND_REQUIRED')
        adapter.canary(target['handle'])

    def packet_start(self, intent_id, revision):
        with self.transaction() as db:
            self._admit(db,intent_id,revision)
            key = uuid.uuid4().hex
            db.execute('INSERT INTO action_packets VALUES (?,?,?,0,NULL,?)',(key,intent_id,revision,'OPEN'))
        return {'packet_id':key,'state':'OPEN','part_count':0}

    def packet_append(self, key, ordinal, part_id, raw):
        identifier(part_id)
        if type(ordinal) is not int or ordinal < 0 or not isinstance(raw, bytes):
            raise ValueError('ACTION_PACKET_PART_SCHEMA')
        with self.transaction() as db:
            packet = db.execute('SELECT * FROM action_packets WHERE id=?',(key,)).fetchone()
            if not packet or packet['state'] != 'OPEN':
                raise ValueError('ACTION_PACKET_IMMUTABLE')
            self._admit(db,packet['intent_id'],packet['revision'])
            existing = db.execute('SELECT * FROM action_parts WHERE packet_id=? AND ordinal=?',(key,ordinal)).fetchone()
            sha = hashlib.sha256(raw).hexdigest()
            if existing:
                if existing['part_id'] != part_id or existing['sha'] != sha:
                    raise ValueError('ACTION_PART_CONTENT_CONFLICT')
                return {'part_id':part_id,'sha256':sha,'reused':True}
            if ordinal != packet['count']:
                raise ValueError('ACTION_PART_CURSOR_CONFLICT')
            db.execute('INSERT INTO action_parts VALUES (?,?,?,?,?)',(key,ordinal,part_id,sha,raw))
            db.execute('UPDATE action_packets SET count=count+1 WHERE id=?',(key,))
        return {'part_id':part_id,'sha256':sha,'reused':False}

    def packet_seal(self, key):
        with self.transaction() as db:
            packet = db.execute('SELECT * FROM action_packets WHERE id=?',(key,)).fetchone()
            if not packet or not packet['count']:
                raise ValueError('ACTION_PACKET_EMPTY')
            if packet['state'] == 'SEALED':
                return {'packet_id':key,'packet_sha256':packet['sha'],'part_count':packet['count']}
            self._admit(db,packet['intent_id'],packet['revision'])
            db.execute("UPDATE action_packets SET state='SEALING' WHERE id=?",(key,))
        h = hashlib.sha256()
        db=connection(self.store)
        try:
            for row in db.execute('SELECT ordinal,part_id,sha,length(raw) AS size FROM action_parts WHERE packet_id=? ORDER BY ordinal',(key,)):
                h.update(encoded(dict(row)).encode() + b'\n')
        finally:
            db.close()
        sha=h.hexdigest()
        with self.transaction() as db:
            self._admit(db,packet['intent_id'],packet['revision'])
            db.execute("UPDATE action_packets SET state='SEALED',sha=? WHERE id=?",(sha,key))
        return {'packet_id':key,'packet_sha256':sha,'part_count':packet['count']}

    def packet_page(self, key, offset=0, limit=20):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('ACTION_PACKET_PAGE_SCHEMA')
        with self.transaction() as db:
            packet = db.execute('SELECT * FROM action_packets WHERE id=?',(key,)).fetchone()
            if not packet:
                raise ValueError('ACTION_PACKET_NOT_FOUND')
            rows = [dict(row) for row in db.execute('SELECT ordinal,part_id,sha,length(raw) AS size FROM action_parts WHERE packet_id=? AND ordinal>=? ORDER BY ordinal LIMIT ?',(key,offset,limit))]
        next_offset = offset + len(rows)
        return {'packet_id':key,'packet_sha256':packet['sha'],'parts':rows,'part_count':packet['count'],
                'next_offset':next_offset,'eof':next_offset >= packet['count']}

    def run(self, job):
        payload = job['payload']
        with self.transaction() as db:
            compiled = self._admit(db,payload['intent_id'],payload['revision'],job)
        plan = compiled['plan']
        results = []
        for step in plan['steps']:
            self.core.heartbeat(job)
            with self.transaction() as db:
                self._admit(db,payload['intent_id'],payload['revision'],job)
            cap = self.config['capabilities'][step['capability']]
            if cap['operation'] == 'send_packet':
                result = self.deliver(job,plan)
                if result['state'] == 'NEEDS_RECONCILIATION':
                    self.core.transition(job,'NEEDS_RECONCILIATION',result=result)
                    return
            else:
                result = self.local(cap['operation'],plan,job)
            results.append({'step_id':step['id'],'outcome':result})
        self.core.transition(job,'SUCCEEDED',result={'steps':results,'semantic_hash':compiled['semantic_hash']})

    def local(self, operation, plan, job):
        slots=plan['slots']
        if operation in {'find_context','request_more_context'}:
            from automation_core import search
            return {'items':search(self.store,slots['namespace'],plan['goal'],limit=20),'scope':'SEARCH_PAGE'}
        if operation == 'prepare_repo_context':
            import repo_context
            alias=slots['repo']; profile=self.config['repositories'][alias]
            key=repo_context.start_scan(self.store,alias,profile,progress=lambda:self.core.heartbeat(job))
            while True:
                self.core.heartbeat(job)
                with self.transaction() as db:
                    self._admit(db,job['payload']['intent_id'],job['payload']['revision'],job)
                result=repo_context.scan_page(self.store,profile['namespace'],key)
                if result['state'] in {'READY','COMPLETE','FAILED','BLOCKED'}:
                    return result
                if result.get('cursor') == result.get('total'):
                    return result
        if operation == 'compile_ai_packet':
            packet=self.packet_start(job['payload']['intent_id'],job['payload']['revision'])
            db = connection(self.store)
            try:
                from source_eligibility import current_text_sql
                predicate=current_text_sql(db)
                for ordinal,ref in enumerate(plan['source_refs']):
                    row=db.execute('SELECT items.payload FROM items JOIN sync_heads ON items.id=sync_heads.item_id WHERE namespace=? AND present=1 AND items.id=? AND '+predicate,(slots['namespace'],ref)).fetchone()
                    if not row:
                        raise ValueError('ACTION_SOURCE_UNAVAILABLE')
                    item=json.loads(row['payload'])
                    if item.get('namespace')!=slots['namespace']:
                        raise ValueError('ACTION_SOURCE_NAMESPACE_MISMATCH')
                    raw=item['text'].encode('utf-8')
                    self.core.heartbeat(job)
                    self.packet_append(packet['packet_id'],ordinal,ref,raw)
            finally:
                db.close()
            return self.packet_seal(packet['packet_id'])
        if operation == 'show_packet':
            return self.packet_page(slots['packet_id'])
        if operation == 'inspect_result':
            with self.transaction() as db:
                row=db.execute("SELECT r.payload FROM action_results r JOIN jobs j ON json_extract(j.payload,'$.intent_id')=r.intent_id JOIN action_attempts a ON a.job_id=j.id WHERE a.packet_id=? ORDER BY r.revision DESC LIMIT 1",(slots['packet_id'],)).fetchone()
            return {'result':json.loads(row[0]) if row else None}
        raise ValueError('ACTION_HANDLER_UNAVAILABLE')

    def deliver(self, job, plan):
        target_id=plan['slots']['destination']; packet_id=plan['slots']['packet_id']
        grants=self.config.get('grants',{})
        if target_id not in grants.get('targets',[]) or 'AI_MESSAGE' not in grants.get('effects',[]):
            raise ValueError('ACTION_SEND_SCOPE_REQUIRED')
        adapter=self.browser()
        adapter.require_qualified()
        with self.transaction() as db:
            target_row,target=self._target(db,target_id)
            packet=db.execute('SELECT * FROM action_packets WHERE id=?',(packet_id,)).fetchone()
            if not packet or packet['state'] != 'SEALED':
                raise ValueError('ACTION_SEALED_PACKET_REQUIRED')
            self._admit(db,packet['intent_id'],packet['revision'])
        # One Core job owns this writer globally. Different browser contexts
        # cannot bypass Core claim; all part attempts persist in this same DB.
        for ordinal in range(packet['count']):
            self.core.heartbeat(job)
            with self.transaction() as db:
                self._admit(db,job['payload']['intent_id'],job['payload']['revision'],job)
                existing=db.execute('SELECT * FROM action_attempts WHERE job_id=? AND packet_id=? AND ordinal=?',(job['id'],packet_id,ordinal)).fetchone()
                if existing:
                    if existing['state']=='MESSAGE_OBSERVED':
                        continue
                    return {'state':'NEEDS_RECONCILIATION','attempt_id':existing['id']}
                part=db.execute('SELECT * FROM action_parts WHERE packet_id=? AND ordinal=?',(packet_id,ordinal)).fetchone()
                if not part or hashlib.sha256(part['raw']).hexdigest()!=part['sha']:
                    raise ValueError('ACTION_PART_HASH_MISMATCH')
                attempt_id=uuid.uuid4().hex
                prompt={'schema':'occ.ai-part.v1','task_id':job['payload']['intent_id'],'intent_revision':job['payload']['revision'],
                        'attempt_id':attempt_id,'packet_sha256':packet['sha'],'part_id':part['part_id'],
                        'part_sha256':part['sha'],'part_ordinal':ordinal,'part_count':packet['count'],
                        'goal':plan['goal'],'criteria':plan['criteria'],'text':part['raw'].decode('utf-8'),
                        'source_authority':'DATA_ONLY','requested_result':'Correlate task_id, attempt_id, packet hash and source hashes; received/used are model claims.'}
                db.execute('INSERT INTO action_attempts VALUES (?,?,?,?,?,?,?,?,0,?)',(attempt_id,job['id'],packet_id,ordinal,target_id,target_row['revision'],target_row['identity_digest'],'PREPARED',encoded(prompt)))
                db.execute('INSERT INTO action_attempt_prompts VALUES (?,?)',(attempt_id,encoded(prompt)))
            self.check_target(target)
            adapter.prepare(target['handle'],prompt)
            with self.transaction() as db:
                self._admit(db,job['payload']['intent_id'],job['payload']['revision'],job)
                current,_=self._target(db,target_id)
                if current['revision'] != target_row['revision']:
                    raise ValueError('ACTION_TARGET_REBIND_REQUIRED')
                db.execute("UPDATE action_attempts SET state='SEND_ARMED',invocations=1 WHERE id=? AND state='PREPARED'",(attempt_id,))
            try:
                # From arming through observation, uncertainty survives every
                # exception, cancellation and process crash. No second click.
                self.check_target(target)
                with self.transaction() as db:
                    self._admit(db,job['payload']['intent_id'],job['payload']['revision'],job)
                adapter.send(target['handle'],prompt)
                observed=adapter.reconcile(target['handle'],prompt)
                state='MESSAGE_OBSERVED' if observed.get('state')=='MESSAGE_OBSERVED' else 'EFFECT_UNKNOWN'
            except Exception:
                observed={'state':'EFFECT_UNKNOWN','reason':'ADAPTER_OUTCOME_UNOBSERVED'}; state='EFFECT_UNKNOWN'
            with self.transaction() as db:
                db.execute('UPDATE action_attempts SET state=?,observation=? WHERE id=?',(state,encoded(observed),attempt_id))
                if state=='MESSAGE_OBSERVED':
                    self._coverage(db,packet_id,part['part_id'],part['sha'],'UI_OBSERVED',observed)
            if state!='MESSAGE_OBSERVED':
                return {'state':'NEEDS_RECONCILIATION','attempt_id':attempt_id}
        return {'state':'MESSAGE_OBSERVED','packet_id':packet_id,'parts':packet['count'],'context_used':'NOT_PROVEN'}

    def reconcile(self, attempt_id):
        with self.transaction() as db:
            row=db.execute('SELECT * FROM action_attempts WHERE id=?',(attempt_id,)).fetchone()
            if not row:
                raise ValueError('ACTION_ATTEMPT_NOT_FOUND')
            if row['state']=='MESSAGE_OBSERVED':
                return {'state':'MESSAGE_OBSERVED','attempt_id':attempt_id}
            target_row,target=self._target(db,row['target_id'])
            if target_row['revision'] != row['target_revision']:
                raise ValueError('ACTION_TARGET_REBIND_REQUIRED')
            frozen=db.execute('SELECT payload FROM action_attempt_prompts WHERE attempt_id=?',(attempt_id,)).fetchone()
            if not frozen:
                raise ValueError('ACTION_ATTEMPT_PROMPT_UNAVAILABLE')
            prompt=json.loads(frozen[0])
        self.check_target(target)
        self.browser().require_qualified()
        observed=self.browser().reconcile(target['handle'],prompt)
        state=observed.get('state')
        if state not in {'MESSAGE_OBSERVED','CONFLICT'}:
            state='EFFECT_UNKNOWN'
        with self.transaction() as db:
            db.execute('UPDATE action_attempts SET state=?,observation=? WHERE id=?',(state,encoded(observed),attempt_id))
            if state=='MESSAGE_OBSERVED':
                part=db.execute('SELECT part_id,sha FROM action_parts WHERE packet_id=? AND ordinal=?',(row['packet_id'],row['ordinal'])).fetchone()
                self._coverage(db,row['packet_id'],part['part_id'],part['sha'],'UI_OBSERVED',observed)
        return {'state':state,'attempt_id':attempt_id,'observation':observed}

    def _coverage(self,db,packet,part,version,kind,payload):
        db.execute('INSERT OR IGNORE INTO action_coverage VALUES (?,?,?,?,?)',(packet,part,version,kind,encoded(payload)))

    def import_result(self,value):
        exact(value,{'intent_id','revision','attempt_id','packet_sha256','conversation','finalized','coverage','findings','done'})
        if value['finalized'] is not True or type(value['done']) is not bool or type(value['revision']) is not int or value['revision']<1 or not isinstance(value['coverage'],list) or not isinstance(value['findings'],list):
            raise ValueError('ACTION_RESULT_INCOMPLETE')
        sha=digest(value)
        with self.transaction() as db:
            row=db.execute('SELECT * FROM action_attempts WHERE id=?',(value['attempt_id'],)).fetchone()
            if not row or row['state']!='MESSAGE_OBSERVED':
                raise ValueError('ACTION_RESULT_ATTEMPT_MISMATCH')
            job=db.execute('SELECT payload FROM jobs WHERE id=?',(row['job_id'],)).fetchone()
            target_row,target=self._target(db,row['target_id'])
            packet=db.execute('SELECT * FROM action_packets WHERE id=?',(row['packet_id'],)).fetchone()
            if (json.loads(job[0])['intent_id']!=value['intent_id'] or packet['sha']!=value['packet_sha256'] or
                    target['identity']['conversation']!=value['conversation'] or target_row['revision']!=row['target_revision']):
                raise ValueError('ACTION_RESULT_CORRELATION')
            existing=db.execute('SELECT * FROM action_results WHERE intent_id=? AND revision=?',(value['intent_id'],value['revision'])).fetchone()
            if existing:
                if existing['sha']!=sha:
                    raise ValueError('ACTION_RESULT_REVISION_CONFLICT')
                return {'result_id':existing['id'],'reused':True}
            for claim in value['coverage']:
                exact(claim,{'part_id','source_sha256','kind'})
                if claim['kind'] not in {'RECEIVED','USED'}:
                    raise ValueError('ACTION_COVERAGE_CLAIM_KIND')
                part=db.execute('SELECT sha FROM action_parts WHERE packet_id=? AND part_id=?',(row['packet_id'],claim['part_id'])).fetchone()
                if not part or part['sha']!=claim['source_sha256']:
                    raise ValueError('ACTION_COVERAGE_SOURCE_MISMATCH')
                self._coverage(db,row['packet_id'],claim['part_id'],part['sha'],'MODEL_REPORTED_'+claim['kind'],claim)
            key=uuid.uuid4().hex
            db.execute('INSERT INTO action_results VALUES (?,?,?,?,?)',(key,value['intent_id'],value['revision'],encoded(value),sha))
        return {'result_id':key,'reused':False,'done_authority':'MODEL_CLAIM_ONLY'}

    def skill_record(self,value):
        exact(value,{'skill_id','version','intent_id','dependencies','preconditions','invariants','recovery','credential_refs','recording_refs'})
        for field in ['skill_id','version']:
            identifier(value[field])
        for field in ['preconditions','invariants','recording_refs']:
            if not isinstance(value[field],list) or not value[field]:
                raise ValueError('ACTION_SKILL_CONTRACT')
        if not {'STOP','TARGET_IDENTITY','REVISION_FENCE'}<=set(value['invariants']):
            raise ValueError('ACTION_SKILL_MANDATORY_INVARIANTS')
        if not isinstance(value['dependencies'],dict) or not value['dependencies']:
            raise ValueError('ACTION_SKILL_DEPENDENCIES')
        if not isinstance(value['credential_refs'],list) or any(not isinstance(ref,str) or not ref.startswith('credential:') for ref in value['credential_refs']):
            raise ValueError('ACTION_SKILL_CREDENTIAL_REFERENCE_REQUIRED')
        with self.transaction() as db:
            intent=self._intent(db,value['intent_id'])
            for ref in value['recording_refs']:
                if not isinstance(ref,str) or not ref.startswith('job:'):
                    raise ValueError('ACTION_SKILL_OBSERVED_CORE_TRACE_REQUIRED')
                trace=db.execute('SELECT payload,state FROM jobs WHERE id=?',(ref[4:],)).fetchone()
                expected={'kind':'action_plan','intent_id':value['intent_id'],'revision':intent['revision']}
                if not trace or trace['state']!='SUCCEEDED' or json.loads(trace['payload'])!=expected:
                    raise ValueError('ACTION_SKILL_OBSERVED_CORE_TRACE_REQUIRED')
            current=self.dependency_versions()
            if any(current.get(k)!=v for k,v in value['dependencies'].items()):
                raise ValueError('ACTION_SKILL_DEPENDENCY_MISMATCH')
            dependencies={**value['dependencies'],'registry':current['registry'],'runtime_code':current['runtime_code']}
            payload=dict(value,dependencies=dependencies,recorded_input=json.loads(intent['payload']),plan=json.loads(intent['compiled']),failure_memory_namespace=value['skill_id'])
            # Record only a typed plan. Raw UI events/credential values are not
            # accepted by this interface; recording refs point at sanitized data.
            code=digest(payload)
            db.execute('INSERT INTO action_skills VALUES (?,?,?,?,?)',(value['skill_id'],value['version'],encoded(payload),code,'CANDIDATE'))
            for dependency,version in dependencies.items():
                db.execute('INSERT INTO action_skill_deps VALUES (?,?,?,?)',(value['skill_id'],value['version'],text(dependency),text(version)))
        return {'skill_id':value['skill_id'],'version':value['version'],'code_digest':code,'dependency_digest':digest(dependencies),'dependencies':dependencies,'state':'CANDIDATE'}

    def dependency_versions(self):
        base=Path(__file__).parent
        return {**self.config.get('dependency_versions',{}), 'registry':digest(self.config),
                'runtime_code':digest([hashlib.sha256((base/name).read_bytes()).hexdigest() for name in ['action_runtime.py','action_intent.py','automation_core.py']])}

    def optimize_skill(self,key,version,new_version):
        """Only duplicate pure reads are candidates for removal; never promote."""
        identifier(new_version)
        with self.transaction() as db:
            row=db.execute('SELECT * FROM action_skills WHERE id=? AND version=?',(key,version)).fetchone()
            if not row or row['state'] not in {'QUALIFIED','FIXTURE_QUALIFIED'}:
                raise ValueError('ACTION_SKILL_UNQUALIFIED')
            old=json.loads(row['payload']);value=dict(old['recorded_input'])
            compiled=old['plan']['plan'];steps=compiled['steps']
            seen={};redirect={};kept=[]
            for step in steps:
                cap=self.config['capabilities'][step['capability']]
                signature=digest([step['capability'],step['input_refs'],step['dependencies']])
                if cap['effect']=='LOCAL_READ' and signature in seen:
                    redirect[step['id']]=seen[signature]
                else:
                    seen[signature]=step['id'];kept.append(dict(step))
            for step in kept:
                step['dependencies']=list(dict.fromkeys(redirect.get(ref,ref) for ref in step['dependencies']))
            value['steps']=kept
            proposed=compile_intent(value,self.config)
            if proposed['state']!='COMPILED':
                raise ValueError('ACTION_SKILL_OPTIMIZATION_REJECTED')
            payload={**old,'version':new_version,'recorded_input':value,'plan':proposed,'optimized_from':version,
                     'optimization':{'removed_read_steps':sorted(redirect),'qualification':'NEW_UNSEEN_AND_FAULT_REQUIRED'}}
            payload.pop('qualification',None)
            code=digest(payload)
            db.execute('INSERT INTO action_skills VALUES (?,?,?,?,?)',(key,new_version,encoded(payload),code,'CANDIDATE'))
            for dependency,value in old['dependencies'].items():
                db.execute('INSERT INTO action_skill_deps VALUES (?,?,?,?)',(key,new_version,dependency,value))
        return {'skill_id':key,'version':new_version,'code_digest':code,'dependency_digest':digest(old['dependencies']),
                'state':'CANDIDATE','removed_steps':sorted(redirect),'failure_capsules':'RETAINED_ALL_VERSIONS'}

    def qualify_skill(self,key,version,receipt):
        exact(receipt,{'code_digest','dependency_digest','normal','unseen','fault','scope','evidence_refs'})
        if not all(receipt[k] is True for k in ['normal','unseen','fault']) or receipt['scope'] not in {'FIXTURE','SKILL_DEVICE'} or not receipt['evidence_refs']:
            raise ValueError('ACTION_SKILL_QUALIFICATION_REQUIRED')
        with self.transaction() as db:
            row=db.execute('SELECT * FROM action_skills WHERE id=? AND version=?',(key,version)).fetchone()
            if not row:
                raise ValueError('ACTION_SKILL_NOT_FOUND')
            payload=json.loads(row['payload'])
            if row['state']=='STALE' or any(self.dependency_versions().get(k)!=v for k,v in payload['dependencies'].items()):
                raise ValueError('ACTION_SKILL_DEPENDENCY_MISMATCH')
            if row['code_digest']!=receipt['code_digest'] or digest(payload['dependencies'])!=receipt['dependency_digest']:
                raise ValueError('ACTION_SKILL_QUALIFICATION_MISMATCH')
            payload['qualification']=receipt
            # Fixture qualification remains distinct from device usability.
            state='FIXTURE_QUALIFIED' if receipt['scope']=='FIXTURE' else 'QUALIFIED'
            db.execute('UPDATE action_skills SET payload=?,state=? WHERE id=? AND version=?',(encoded(payload),state,key,version))
        return {'state':state,'skill_id':key,'version':version}

    def invalidate(self,dependency,new_digest):
        with self.transaction() as db:
            affected=[dict(r) for r in db.execute('SELECT * FROM action_skill_deps WHERE dependency=? AND digest!=?',(dependency,new_digest))]
            for row in affected:
                db.execute("UPDATE action_skills SET state='STALE' WHERE id=? AND version=?",(row['skill_id'],row['version']))
        return {'stale':affected,'unrelated_receipts':'RETAINED_BY_EXPLICIT_DEPENDENCY_INDEX'}

    def failure(self,key,version,value):
        exact(value,{'input_refs','environment_ref','observed_state','error','counterexample_ref','recovery_ref','evidence_refs'})
        with self.transaction() as db:
            if not db.execute('SELECT 1 FROM action_skills WHERE id=? AND version=?',(key,version)).fetchone():
                raise ValueError('ACTION_SKILL_NOT_FOUND')
            capsule=digest([key,version,value])
            db.execute('INSERT OR IGNORE INTO action_failures VALUES (?,?,?,?)',(capsule,key,version,encoded(value)))
        return {'failure_capsule_id':capsule}

    def invoke_skill(self,key,version,value,dependencies):
        with self.transaction() as db:
            row=db.execute('SELECT * FROM action_skills WHERE id=? AND version=?',(key,version)).fetchone()
            if not row or row['state'] not in {'QUALIFIED','FIXTURE_QUALIFIED'}:
                raise ValueError('ACTION_SKILL_STALE_OR_UNQUALIFIED')
            stored=json.loads(row['payload'])
            if stored['dependencies']!=dependencies or any(self.dependency_versions().get(k)!=v for k,v in stored['dependencies'].items()):
                raise ValueError('ACTION_SKILL_DEPENDENCY_MISMATCH')
            old=stored['recorded_input']
            new=compile_intent(value,self.config)
            if (new['state']!='COMPILED' or new['plan']['command']!=stored['plan']['plan']['command'] or
                    new['plan']['steps']!=stored['plan']['plan']['steps'] or value['source_refs']!=old['source_refs'] or value['criteria']!=old['criteria']):
                raise ValueError('ACTION_SKILL_SCOPE_GROWTH')
            # Same registered capability/scope. Input text may vary; changing a
            # recipient/root/mode must go back through an explicit new template.
            if value['slots']!=old['slots']:
                raise ValueError('ACTION_SKILL_SCOPE_GROWTH')
            if row['state']=='FIXTURE_QUALIFIED' and new['plan']['capability']['effect']!='LOCAL_READ':
                raise ValueError('ACTION_SKILL_DEVICE_QUALIFICATION_REQUIRED')
        result=self.create(value)
        return self.enqueue(result['intent_id'],result['revision'])

    def handle(self,action,value):
        if action=='INFO':
            exact(value,set())
        operations={
            'INFO':lambda:{'state':'READY','commands':self.config['capabilities'],'repositories':list(self.config['repositories']),
                           'namespaces':self.config['namespaces'],'browser':'OPTIONAL_REQUIRES_QUALIFICATION','laya':'UNVERIFIED_DIRECT_UI_FALLBACK',
                           'voice':self.config.get('voice'), 'queue_owner':'CORE_JOBS'},
            'CREATE':lambda:self.create(value),
            'GET':lambda:self.get(exact(value,{'intent_id'})['intent_id']),
            'CORRECT':lambda:self.correct(value['intent_id'],value['revision'],exact(value,{'intent_id','revision','input'})['input']),
            'ENQUEUE':lambda:self.enqueue(value['intent_id'],exact(value,{'intent_id','revision'})['revision']),
            'STOP':lambda:self.stop() if exact(value,set()) is not None else None,
            'RESUME':lambda:self.resume() if exact(value,set()) is not None else None,
            'BIND':lambda:self.bind(exact(value,{'handle'})['handle']),
            'PACKET_START':lambda:self.packet_start(value['intent_id'],exact(value,{'intent_id','revision'})['revision']),
            'PACKET_APPEND':lambda:self.packet_append(value['packet_id'],value['ordinal'],value['part_id'],text(exact(value,{'packet_id','ordinal','part_id','text'})['text']).encode('utf-8')),
            'PACKET_SEAL':lambda:self.packet_seal(exact(value,{'packet_id'})['packet_id']),
            'PACKET_PAGE':lambda:self.packet_page(value['packet_id'],value['offset'],exact(value,{'packet_id','offset'}) and 20),
            'RECONCILE':lambda:self.reconcile(exact(value,{'attempt_id'})['attempt_id']),
            'IMPORT_RESULT':lambda:self.import_result(value),
            'SKILL_RECORD':lambda:self.skill_record(value),
            'SKILL_INVOKE':lambda:self.invoke_skill(value['skill_id'],value['version'],value['input'],exact(value,{'skill_id','version','input','dependencies'})['dependencies']),
            'CONTINUE':lambda:self.continue_delivery(value['job_id'],exact(value,{'job_id','process_stopped'})['process_stopped']),
        }
        if action not in operations:
            raise ValueError('ACTION_OPERATION_UNAVAILABLE')
        return operations[action]()

    def continue_delivery(self, job_id, process_stopped):
        if process_stopped is not True:
            raise ValueError('OPERATOR_PROCESS_STOP_CONFIRMATION_REQUIRED')
        with self.transaction() as db:
            row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
            if not row or row['state']!='NEEDS_RECONCILIATION':
                raise ValueError('ACTION_JOB_RECONCILIATION_REQUIRED')
            payload=json.loads(row['payload'])
            if payload.get('kind')!='action_plan' or row['cancel_requested']:
                raise ValueError('ACTION_JOB_FENCED')
            self._admit(db,payload['intent_id'],payload['revision'])
            if db.execute("SELECT 1 FROM action_attempts WHERE job_id=? AND state!='MESSAGE_OBSERVED' LIMIT 1",(job_id,)).fetchone():
                raise ValueError('ACTION_EFFECT_UNKNOWN')
            db.execute("UPDATE jobs SET state='QUEUED',lease_token=NULL,lease_until=0 WHERE id=?",(job_id,))
            event(db,job_id,'QUEUED',{'reason':'OBSERVED_EFFECT_RECONCILED','operator_process_stopped':True})
        return {'id':job_id,'state':'QUEUED'}
