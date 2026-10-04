"""Independent intent/outcome cases with real Core/SQLite and fault adapters.

Browser doubles are fixture evidence, never selected UI/device qualification.
"""
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
import time
import unittest

from automation_core import Core, connection, digest
from action_intent import compile_intent, LayaAdapter, permission_diff, review_roles
from action_runtime import ActionRuntime
from content_lab import save_item
import native_adapter


def configuration():
    operations={
        'find':('find_context','LOCAL_READ',['namespace']),
        'packet':('compile_ai_packet','LOCAL_WRITE',['namespace']),
        'show':('show_packet','LOCAL_READ',['packet_id']),
        'send':('send_packet','AI_MESSAGE',['destination','packet_id']),
    }
    return {'schema':'occ.action-registry.v1','enabled':True,'version':'1',
            'namespaces':['code'],'repositories':{},'grants':{'effects':['AI_MESSAGE'],'targets':[]},
            'dependency_versions':{'adapter':'v1'},
            'capabilities':{key:{'operation':op,'version':'1','effect':effect,'required_slots':slots,'aliases':[key]} for key,(op,effect,slots) in operations.items()}}


def input_value(command='find',**slots):
    return {'text':'Send context; не merge main' if command=='send' else 'Find context; не merge main; dry-run','modality':'TEXT','command':command,
            'slots':{'namespace':'code',**slots},'criteria':['all scoped source IDs accounted'],'source_refs':[]}


class FixtureBrowser:
    version='fixture-browser.v1'
    def __init__(self):
        self.identity={'origin':'https://fixture.invalid','account':'account-1','workspace':'workspace-1',
                       'conversation':'conversation-1','focused':True,'contract_digest':'fixture-ui-v1'}
        self.sent=[];self.fail=False;self.visible=True;self.prepare_hook=None
    def observe(self,handle):return dict(self.identity)
    def canary(self,handle):return {'state':'FIXTURE_ONLY'}
    def require_qualified(self):return None
    def prepare(self,handle,prompt):
        if self.prepare_hook:self.prepare_hook()
    def send(self,handle,prompt):
        self.sent.append(dict(prompt))
        if self.fail:raise OSError('lost acknowledgement after remote commit')
    def reconcile(self,handle,prompt):
        matches=[x for x in self.sent if x['attempt_id']==prompt['attempt_id']]
        return {'state':'MESSAGE_OBSERVED' if len(matches)==1 and self.visible else 'CONFLICT' if len(matches)>1 else 'EFFECT_UNKNOWN','evidence_kind':'FIXTURE'}


class IntentTests(unittest.TestCase):
    def setUp(self):self.config=configuration()

    def test_text_voice_parity_and_source_negation(self):
        v=input_value();voice=dict(v,modality='VOICE',original_text='raw misrecognition')
        a=compile_intent(v,self.config);b=compile_intent(voice,self.config)
        self.assertEqual(a['semantic_hash'],b['semantic_hash'])
        self.assertIn('не merge main',a['plan']['goal'])
        changed=copy.deepcopy(self.config);changed['version']='2'
        self.assertNotEqual(a['semantic_hash'],compile_intent(v,changed)['semantic_hash'])

    def test_unknown_and_missing_destination_are_not_guessed(self):
        unknown=compile_intent(input_value('invented-shell'),self.config)
        self.assertEqual(unknown['state'],'UNKNOWN_CAPABILITY')
        missing=compile_intent(input_value('send'),self.config)
        self.assertEqual(missing['state'],'NEEDS_INPUT')
        self.assertEqual(missing['missing_slots'],['destination','mode_SEND','packet_id'])

    def test_mode_and_negation_win_over_send_selection(self):
        for mode in ['dry-run','LIVE',None]:
            value=input_value('send',destination='target',packet_id='packet',mode=mode)
            self.assertEqual(compile_intent(value,self.config)['state'],'NEEDS_INPUT')
        value=input_value('send',destination='target',packet_id='packet',mode='SEND')
        value['text']='Send context dry-run'
        self.assertEqual(compile_intent(value,self.config)['state'],'NEEDS_INPUT')

    def test_out_of_order_dag_waits_for_dependency(self):
        steps=[{'id':'last','capability':'find','dependencies':['first'],'input_refs':[]},
               {'id':'first','capability':'find','dependencies':[],'input_refs':[]}]
        result=compile_intent(dict(input_value(),steps=steps),self.config)
        self.assertEqual([s['id'] for s in result['plan']['steps']],['first','last'])

    def test_document_cannot_add_argv_grants_or_root(self):
        for key in ['argv','grant','root','verifier']:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ACTION_SCHEMA'):
                compile_intent(dict(input_value(),**{key:'malicious'}),self.config)

    def test_cycle_duplicate_missing_and_smuggled_effect(self):
        base={'id':'one','capability':'find','dependencies':[],'input_refs':[]}
        trials=[([base,base],'DUPLICATE'),([dict(base,dependencies=['one'])],'CYCLE'),
                ([dict(base,dependencies=['missing'])],'MISSING_DEPENDENCY'),
                ([dict(base,input_refs=['missing'])],'MISSING_INPUT'),
                ([dict(base,capability='send')],'SCOPE_MISMATCH')]
        for steps,error in trials:
            with self.subTest(error=error),self.assertRaisesRegex(ValueError,error):
                compile_intent(dict(input_value(),steps=steps),self.config)

    def test_negated_send_never_compiles_as_effect(self):
        v=input_value('send',destination='x',packet_id='y');v['text']='Не отправляй это в чат'
        self.assertEqual(compile_intent(v,self.config)['state'],'NEEDS_INPUT')

    def test_laya_unavailable_and_advisory_validation(self):
        self.assertEqual(LayaAdapter().discover()['fallback'],'DIRECT_TYPED_UI')
        bad=LayaAdapter(lambda _:dict(input_value(),argv=['rm']),version='fixture')
        with self.assertRaisesRegex(ValueError,'ACTION_SCHEMA'):bad.propose({},self.config)
        good=LayaAdapter(lambda _:input_value(),version='fixture')
        self.assertEqual(good.propose({},self.config)['state'],'COMPILED')

    def test_critic_missing_source_and_permission_growth(self):
        intent=input_value();h=digest(intent)
        result=review_roles(intent,{'available_refs':[],'missing_refs':['one']},
                {'intent_hash':h,'proposal':{}},{'intent_hash':h,'verdict':'ACCEPT','missing_refs':[]})
        self.assertEqual(result['state'],'NEEDS_CONTEXT')
        old={'hosts':['a'],'roots':['r'],'targets':['t'],'effects':['LOCAL_READ']}
        self.assertTrue(permission_diff(old,old)['compatible_grant_reuse'])
        self.assertTrue(permission_diff(old,dict(old,hosts=['a','b']))['requires_new_scope'])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Path(self.temp.name)/'store';self.browser=FixtureBrowser()
        self.policy={'schema':'occ.automation-policy.v1','max_parallel':1,'money_budget':0,'sources':{},'repos':{},'actions':configuration()}
        self.core=Core(self.store,self.policy,action_adapter=self.browser)
        self.runtime=self.core.actions

    def read_db(self,sql,args=()):
        db=connection(self.store)
        try:return [dict(x) for x in db.execute(sql,args)]
        finally:db.close()

    def packet(self,n=1):
        intent=self.runtime.create(input_value())
        packet=self.runtime.packet_start(intent['intent_id'],1)['packet_id']
        for i in range(n):self.runtime.packet_append(packet,i,'part-'+str(i),('bytes-'+str(i)).encode())
        return self.runtime.packet_seal(packet)

    def send_job(self,n=1):
        target=self.runtime.bind('transient-tab')
        self.policy['actions']['grants']['targets']=[target['binding_id']]
        packet=self.packet(n)
        intent=self.runtime.create(input_value('send',destination=target['binding_id'],packet_id=packet['packet_id'],mode='SEND'))
        job=self.runtime.enqueue(intent['intent_id'],1)
        return intent,job,packet

    def test_core_executes_registered_read_in_existing_jobs(self):
        intent=self.runtime.create(input_value());first=self.runtime.enqueue(intent['intent_id'],1)
        self.assertEqual(first['id'],self.runtime.enqueue(intent['intent_id'],1)['id'])
        self.assertEqual(self.core.run_once()['state'],'SUCCEEDED')
        self.assertEqual(len(self.read_db('SELECT * FROM jobs')),1)

    def test_installer_layout_runs_isolated_native_cli_and_worker(self):
        lab = Path(__file__).resolve().parent
        installer = (lab.parent / 'agent-bridge' / 'Install.ps1').read_text()
        names = re.findall(r"'([^']+)'", re.search(
            r'foreach\(\$occFile in @\((.*?)\)\)', installer).group(1))
        installed = Path(self.temp.name) / 'installed'
        installed.mkdir()
        for name in names:
            shutil.copyfile(lab / name, installed / name)
        policy_path = installed.parent / 'policy.json'
        policy_path.write_text(json.dumps(self.policy), encoding='utf-8')
        profile_path = installed.parent / 'profile.json'
        profile_path.write_text(json.dumps({
            'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy_path), 'namespaces': ['code'], 'templates': {}}),
            encoding='utf-8')

        def native(request):
            process = subprocess.run([
                sys.executable, '-I', '-X', 'utf8', str(installed / 'native_adapter.py'),
                '--profile', str(profile_path)], input=json.dumps(request).encode(),
                capture_output=True, check=True, timeout=20)
            reply = json.loads(process.stdout)
            self.assertTrue(reply['ok'], reply)
            return reply['result']['action']

        def cli(action, value):
            payload_path = installed.parent / 'payload.json'
            payload_path.write_text(json.dumps(value), encoding='utf-8')
            process = subprocess.run([
                sys.executable, '-I', '-X', 'utf8', str(installed / 'action_cli.py'),
                '--profile', str(profile_path), action, '--payload', str(payload_path)],
                capture_output=True, check=True, timeout=20)
            return json.loads(process.stdout)['action']

        self.assertEqual(cli('INFO', {})['queue_owner'], 'CORE_JOBS')
        intent = native({'type': 'durable.action', 'action': 'CREATE', 'payload': input_value()})
        job = cli('ENQUEUE', {'intent_id': intent['intent_id'], 'revision': 1})
        subprocess.run([
            sys.executable, '-I', '-X', 'utf8', str(installed / 'automation_core.py'),
            '--store', str(self.store), 'work', '--policy', str(policy_path)],
            capture_output=True, check=True, timeout=20)
        self.assertEqual(self.core.get(job['id'])['state'], 'SUCCEEDED')
        self.assertEqual(native({'type': 'durable.action', 'action': 'STOP',
                                 'payload': {}})['state'], 'STOPPED')

    def test_correction_cancels_old_unexecuted_job_preserves_raw(self):
        raw=dict(input_value(),modality='VOICE',original_text='raw ASR')
        intent=self.runtime.create(raw);job=self.runtime.enqueue(intent['intent_id'],1)
        value=dict(input_value(),text='Corrected goal')
        revised=self.runtime.correct(intent['intent_id'],1,value)
        self.assertEqual(revised['revision'],2);self.assertEqual(self.core.get(job['id'])['state'],'CANCELLED')
        self.assertEqual(self.runtime.get(intent['intent_id'])['input']['original_text'],'raw ASR')
        with self.assertRaisesRegex(ValueError,'FENCED'):self.runtime.enqueue(intent['intent_id'],1)

    def test_policy_and_boolean_revision_fences(self):
        intent=self.runtime.create(input_value())
        with self.assertRaisesRegex(ValueError,'FENCED'):self.runtime.enqueue(intent['intent_id'],True)
        self.policy['actions']['version']='changed'
        with self.assertRaisesRegex(ValueError,'POLICY_CHANGED'):self.runtime.get(intent['intent_id'])

    def test_independent_stop_blocks_admission_and_does_not_resurrect_job(self):
        intent=self.runtime.create(input_value());job=self.runtime.enqueue(intent['intent_id'],1)
        self.runtime.stop()
        with self.assertRaisesRegex(ValueError,'STOPPED'):self.runtime.enqueue(intent['intent_id'],1)
        self.runtime.resume();self.assertEqual(self.core.get(job['id'])['state'],'CANCELLED')

    def test_packet_is_immutable_and_has_no_twenty_part_cap(self):
        packet=self.packet(257);key=packet['packet_id'];seen=[];offset=0
        while True:
            page=self.runtime.packet_page(key,offset);seen+=page['parts'];offset=page['next_offset']
            if page['eof']:break
        self.assertEqual(len(seen),257);self.assertEqual([x['ordinal'] for x in seen],list(range(257)))
        with self.assertRaisesRegex(ValueError,'IMMUTABLE'):self.runtime.packet_append(key,258,'last',b'x')
        self.assertEqual(self.runtime.packet_seal(key),packet)

    def test_packet_cursor_and_duplicate_content(self):
        intent=self.runtime.create(input_value());key=self.runtime.packet_start(intent['intent_id'],1)['packet_id']
        self.runtime.packet_append(key,0,'p',b'a')
        self.assertTrue(self.runtime.packet_append(key,0,'p',b'a')['reused'])
        with self.assertRaisesRegex(ValueError,'CONTENT_CONFLICT'):self.runtime.packet_append(key,0,'p',b'b')
        with self.assertRaisesRegex(ValueError,'CURSOR_CONFLICT'):self.runtime.packet_append(key,2,'two',b'a')

    def test_complete_multipart_delivery_does_not_claim_used_context(self):
        _,job,packet=self.send_job(21)
        result=self.core.run_once()
        self.assertEqual(result['state'],'SUCCEEDED');self.assertEqual(len(self.browser.sent),21)
        self.assertEqual(result['result']['steps'][0]['outcome']['context_used'],'NOT_PROVEN')
        self.assertTrue(all(r['invocations']==1 for r in self.read_db('SELECT * FROM action_attempts')))

    def test_lost_acknowledgement_survives_restart_without_duplicate_send(self):
        intent,job,packet=self.send_job(2);self.browser.fail=True;self.browser.visible=False
        self.assertEqual(self.core.run_once()['state'],'NEEDS_RECONCILIATION')
        self.assertEqual(len(self.browser.sent),1)
        restarted=Core(self.store,self.policy,action_adapter=self.browser)
        self.assertEqual(restarted.run_once()['state'],'IDLE');self.assertEqual(len(self.browser.sent),1)
        attempt=self.read_db('SELECT * FROM action_attempts')[0]
        self.assertEqual(restarted.actions.reconcile(attempt['id'])['state'],'EFFECT_UNKNOWN')
        with self.assertRaisesRegex(ValueError,'UNKNOWN'):restarted.actions.continue_delivery(job['id'],True)
        self.browser.fail=False;self.browser.visible=True
        self.assertEqual(restarted.actions.reconcile(attempt['id'])['state'],'MESSAGE_OBSERVED')
        restarted.actions.continue_delivery(job['id'],True)
        self.assertEqual(restarted.run_once()['state'],'SUCCEEDED');self.assertEqual(len(self.browser.sent),2)

    def test_armed_crash_never_becomes_permission_to_click(self):
        _,job,_=self.send_job()
        claimed=self.core.claim()
        with self.runtime.transaction() as db:
            db.execute('INSERT INTO action_attempts VALUES (?,?,?,?,?,?,?,?,?,?)',('armed',job['id'],'unknown-packet',0,'target',1,'digest','SEND_ARMED',0,'{}'))
            db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
        self.assertIsNone(self.core.claim());self.assertEqual(self.core.get(job['id'])['state'],'NEEDS_RECONCILIATION')
        self.assertEqual(len(self.browser.sent),0)

    def test_target_and_user_focus_drift_before_send(self):
        for key,value in [('account','wrong'),('focused',False)]:
            with self.subTest(key=key):
                old=self.browser.identity[key]
                _,job,_=self.send_job();self.browser.identity[key]=value
                self.assertEqual(self.core.run_once()['state'],'BLOCKED')
                self.assertEqual(len(self.browser.sent),0);self.browser.identity[key]=old

    def test_correction_during_draft_fences_send(self):
        intent,job,_=self.send_job()
        self.browser.prepare_hook=lambda:self.runtime.correct(intent['intent_id'],1,input_value())
        result=self.core.run_once()
        self.assertEqual(result['state'],'CANCELLED');self.assertEqual(len(self.browser.sent),0)

    def test_cancel_unknown_effect_keeps_reconciliation_state(self):
        _,job,_=self.send_job();self.browser.fail=True;self.browser.visible=False
        self.core.run_once();self.runtime.stop()
        self.assertEqual(self.core.get(job['id'])['state'],'NEEDS_RECONCILIATION')
        self.assertEqual(self.read_db('SELECT state FROM action_attempts')[0]['state'],'EFFECT_UNKNOWN')

    def test_result_correlation_idempotency_and_old_head(self):
        intent,job,packet=self.send_job();self.core.run_once();attempt=self.read_db('SELECT * FROM action_attempts')[0]
        value={'intent_id':intent['intent_id'],'revision':2,'attempt_id':attempt['id'],'packet_sha256':packet['packet_sha256'],
               'conversation':'conversation-1','finalized':True,'coverage':[],'findings':['DATA_ONLY: shell strings are not executed'],'done':True}
        first=self.runtime.import_result(value);self.assertTrue(self.runtime.import_result(value)['reused'])
        self.runtime.import_result(dict(value,revision=1))
        rows=self.read_db('SELECT revision FROM action_results ORDER BY revision DESC');self.assertEqual(rows[0]['revision'],2)
        for change in [{'conversation':'wrong'},{'packet_sha256':'wrong'},{'finalized':False},{'argv':['oops']}]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.runtime.import_result(dict(value,**change))

    def test_coverage_claim_requires_exact_part_version(self):
        intent,job,packet=self.send_job();self.core.run_once();attempt=self.read_db('SELECT * FROM action_attempts')[0]
        value={'intent_id':intent['intent_id'],'revision':1,'attempt_id':attempt['id'],'packet_sha256':packet['packet_sha256'],
               'conversation':'conversation-1','finalized':True,'coverage':[{'part_id':'part-0','source_sha256':'bad','kind':'USED'}],'findings':[],'done':True}
        with self.assertRaisesRegex(ValueError,'SOURCE_MISMATCH'):self.runtime.import_result(value)
        self.assertFalse(self.read_db("SELECT * FROM action_coverage WHERE kind LIKE 'MODEL_%'"))

    def test_skill_unseen_receipt_hash_stale_and_retained_failures(self):
        intent=self.runtime.create(input_value())
        job=self.runtime.enqueue(intent['intent_id'],1);self.core.run_once()
        record={'skill_id':'skill','version':'1','intent_id':intent['intent_id'],'dependencies':{'adapter':'v1'},
                'preconditions':['known source'],'invariants':['STOP','TARGET_IDENTITY','REVISION_FENCE'],
                'recovery':'reconcile','credential_refs':[],'recording_refs':['job:'+job['id']]}
        result=self.runtime.skill_record(record)
        capsule={'input_refs':['fixture:bad'],'environment_ref':'fixture:env','observed_state':'BLOCKED','error':'counterexample','counterexample_ref':'fixture:x','recovery_ref':'fixture:r','evidence_refs':['fixture:e']}
        self.runtime.failure('skill','1',capsule)
        receipt={'code_digest':result['code_digest'],'dependency_digest':result['dependency_digest'],
                 'normal':True,'unseen':True,'fault':True,'scope':'FIXTURE','evidence_refs':['fixture:independent-outcome']}
        with self.assertRaisesRegex(ValueError,'MISMATCH'):self.runtime.qualify_skill('skill','1',dict(receipt,code_digest='bad'))
        self.assertEqual(self.runtime.qualify_skill('skill','1',receipt)['state'],'FIXTURE_QUALIFIED')
        self.runtime.invoke_skill('skill','1',dict(input_value(),text='unseen goal'),result['dependencies'])
        self.assertFalse(self.runtime.invalidate('unrelated','v2')['stale'])
        self.assertTrue(self.runtime.invalidate('adapter','v2')['stale'])
        with self.assertRaisesRegex(ValueError,'STALE'):self.runtime.invoke_skill('skill','1',input_value(),{'adapter':'v2'})
        self.assertEqual(len(self.read_db('SELECT * FROM action_failures')),1)

    def test_record_requires_observed_success_and_code_drift_blocks_replay(self):
        intent=self.runtime.create(input_value());job=self.runtime.enqueue(intent['intent_id'],1)
        record={'skill_id':'trace','version':'1','intent_id':intent['intent_id'],'dependencies':{'adapter':'v1'},
                'preconditions':['explicit namespace'],'invariants':['STOP','TARGET_IDENTITY','REVISION_FENCE'],
                'recovery':'review','credential_refs':[],'recording_refs':['job:'+job['id']]}
        with self.assertRaisesRegex(ValueError,'OBSERVED_CORE_TRACE'):self.runtime.skill_record(record)
        self.core.run_once();result=self.runtime.skill_record(record)
        receipt={'code_digest':result['code_digest'],'dependency_digest':result['dependency_digest'],'normal':True,'unseen':True,
                 'fault':True,'scope':'FIXTURE','evidence_refs':['fixture:gold']}
        self.runtime.qualify_skill('trace','1',receipt)
        from unittest.mock import patch
        changed={**self.runtime.dependency_versions(),'runtime_code':'changed'}
        with patch.object(self.runtime,'dependency_versions',return_value=changed),self.assertRaisesRegex(ValueError,'DEPENDENCY_MISMATCH'):
            self.runtime.invoke_skill('trace','1',input_value(),result['dependencies'])

    def test_optimizer_keeps_new_candidate_unqualified(self):
        steps=[{'id':'a','capability':'find','dependencies':[],'input_refs':[]},
               {'id':'b','capability':'find','dependencies':[],'input_refs':[]}]
        intent=self.runtime.create(dict(input_value(),steps=steps));job=self.runtime.enqueue(intent['intent_id'],1);self.core.run_once()
        record={'skill_id':'opt','version':'1','intent_id':intent['intent_id'],'dependencies':{'adapter':'v1'},
                'preconditions':['explicit namespace'],'invariants':['STOP','TARGET_IDENTITY','REVISION_FENCE'],
                'recovery':'review','credential_refs':[],'recording_refs':['job:'+job['id']]}
        result=self.runtime.skill_record(record)
        receipt={'code_digest':result['code_digest'],'dependency_digest':result['dependency_digest'],'normal':True,'unseen':True,
                 'fault':True,'scope':'FIXTURE','evidence_refs':['fixture:gold']}
        self.runtime.qualify_skill('opt','1',receipt)
        optimized=self.runtime.optimize_skill('opt','1','2')
        self.assertEqual(optimized['removed_steps'],['b']);self.assertEqual(optimized['state'],'CANDIDATE')
        with self.assertRaisesRegex(ValueError,'UNQUALIFIED'):self.runtime.invoke_skill('opt','2',input_value(),result['dependencies'])

    def test_packet_compiler_uses_only_selected_namespace(self):
        from automation_core import sync,search
        root=Path(self.temp.name)/'sources';root.mkdir();(root/'code.txt').write_text('fixture exact text')
        sync(self.store,'code',root);ref=search(self.store,'code','fixture')[0]['id']
        value=dict(input_value('packet'),source_refs=[ref]);intent=self.runtime.create(value)
        self.runtime.enqueue(intent['intent_id'],1);result=self.core.run_once()
        self.assertEqual(result['state'],'SUCCEEDED',result)
        self.assertEqual(self.read_db('SELECT raw FROM action_parts')[0]['raw'],b'fixture exact text')
        sync(self.store,'other',root);ref=search(self.store,'other','fixture')[0]['id']
        intent=self.runtime.create(dict(value,source_refs=[ref]));self.runtime.enqueue(intent['intent_id'],1)
        self.assertEqual(self.core.run_once()['state'],'BLOCKED')

    def test_frozen_prompt_keeps_goal_after_unknown_ack(self):
        self.browser.fail=True;intent,job,packet=self.send_job();self.core.run_once()
        prompt=json.loads(self.read_db('SELECT payload FROM action_attempt_prompts')[0]['payload'])
        self.assertEqual(prompt['criteria'],input_value('send')['criteria'])
        self.assertEqual(prompt['part_count'],1);self.assertEqual(prompt['intent_revision'],1)
        self.assertEqual(self.runtime.reconcile(prompt['attempt_id'])['state'],'MESSAGE_OBSERVED')

    def test_native_opt_in_preserves_existing_read_path(self):
        root=Path(self.temp.name);policy_path=root/'policy.json';profile_path=root/'profile.json'
        policy_path.write_text(json.dumps(self.policy))
        profile={'schema':'occ.native-durable-profile.v1','store':str(self.store),'policy_file':str(policy_path),
                 'namespaces':['code'],'repositories':{},'templates':{}}
        profile_path.write_text(json.dumps(profile))
        created=native_adapter.dispatch_desktop({'type':'durable.action','action':'CREATE','payload':input_value()},profile_path)
        self.assertTrue(created['ok'],created)
        self.assertEqual(created['result']['action']['state'],'COMPILED')
        stopped=native_adapter.dispatch_desktop({'type':'durable.action','action':'STOP','payload':{}},profile_path)
        self.assertTrue(stopped['ok'])
        del self.policy['actions'];policy_path.write_text(json.dumps(self.policy))
        refused=native_adapter.dispatch_desktop({'type':'durable.action','action':'CREATE','payload':input_value()},profile_path)
        self.assertFalse(refused['ok'])


if __name__=='__main__':unittest.main()
