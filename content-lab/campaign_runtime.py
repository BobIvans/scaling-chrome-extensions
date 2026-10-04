"""Immutable campaign DAG over existing Core jobs, events and resource owners.

The planner only admits registered templates. It never creates worker processes,
changes max_parallel, interprets source instructions or promotes AI claims.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

import automation_core as core
import workflow_state as state


def load_manifest(policy, alias):
    core.identifier(alias)
    profile=policy.get('campaigns',{}).get(alias)
    if not isinstance(profile,dict) or set(profile)-{'manifest_file','manifest_sha256','templates','inputs','capacity','lease_seconds'}:
        raise ValueError('CAMPAIGN_REGISTERED_PROFILE_REQUIRED')
    path=state.registered_file(profile['manifest_file'],profile['manifest_sha256'])
    # Operator-bound manifest, no arbitrary total node/file ceiling.
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(manifest,dict) or set(manifest)!={'schema','campaign_id','revision','goal_ids','criteria','nodes','limits'} or manifest['schema']!='occ.campaign.v1':
        raise ValueError('CAMPAIGN_MANIFEST_SCHEMA')
    core.identifier(manifest['campaign_id']);state.integer(manifest['revision'],1)
    limits=manifest['limits']
    if not isinstance(limits,dict) or set(limits)!={'max_elapsed_seconds','max_iterations','no_progress_limit','max_transfers'}:
        raise ValueError('CAMPAIGN_LIMITS_REQUIRED')
    for v in limits.values():state.integer(v,1)
    if not isinstance(manifest['goal_ids'],list) or not manifest['goal_ids'] or not all(isinstance(x,str) and x for x in manifest['goal_ids']):
        raise ValueError('CAMPAIGN_GOAL_IDS_REQUIRED')
    if not isinstance(manifest['criteria'],list) or not all(isinstance(x,dict) and set(x)=={'id','text'} and isinstance(x['text'],str) for x in manifest['criteria']):
        raise ValueError('CAMPAIGN_CRITERIA_REQUIRED')
    if len({c['id'] for c in manifest['criteria']})!=len(manifest['criteria']):
        raise ValueError('CAMPAIGN_CRITERION_ID_CONFLICT')
    nodes=manifest['nodes']
    if not isinstance(nodes,list) or not nodes:
        raise ValueError('CAMPAIGN_NODES_REQUIRED')
    index={}
    for n in nodes:
        if not isinstance(n,dict) or set(n)!={'id','template','needs','inputs','resources','demand'}:
            raise ValueError('CAMPAIGN_NODE_SCHEMA')
        core.identifier(n['id']);core.identifier(n['template'])
        if n['id'] in index:raise ValueError('CAMPAIGN_DUPLICATE_NODE')
        if not isinstance(n['needs'],list) or not isinstance(n['inputs'],list) or not isinstance(n['resources'],list) or not isinstance(n['demand'],dict):
            raise ValueError('CAMPAIGN_NODE_FIELDS')
        if not all(isinstance(x,str) and x for x in n['needs']+n['inputs']):raise ValueError('CAMPAIGN_NODE_FIELDS')
        payload=profile.get('templates',{}).get(n['template']);core.validate_job(payload,policy)
        if set(n['inputs'])-profile.get('inputs',{}).keys():raise ValueError('CAMPAIGN_UNREGISTERED_INPUT')
        for i in n['inputs']:
            p=profile['inputs'][i];state.checked_hash(p['sha256'])
            if not Path(p['file']).is_absolute():raise ValueError('CAMPAIGN_INPUT_PATH')
        for r in n['resources']:
            if not isinstance(r,dict) or set(r)!={'id','mode'} or r['mode'] not in {'READ','WRITE'}:
                raise ValueError('CAMPAIGN_RESOURCE_SCHEMA')
        for value in n['demand'].values():state.number(value)
        index[n['id']]=n
    # Iterative Kahn traversal: scalable past Python recursion depth.
    indegree={i:0 for i in index};children={i:[] for i in index}
    for n in nodes:
        if len(n['needs'])!=len(set(n['needs'])) or any(x not in index for x in n['needs']):raise ValueError('CAMPAIGN_UNKNOWN_DEPENDENCY')
        for parent in n['needs']:indegree[n['id']]+=1;children[parent].append(n['id'])
    ready=[k for k,v in indegree.items() if v==0];count=0
    while ready:
        i=ready.pop();count+=1
        for child in children[i]:
            indegree[child]-=1
            if indegree[child]==0:ready.append(child)
    if count!=len(nodes):raise ValueError('CAMPAIGN_CYCLE')
    return profile,manifest


def node_fingerprint(n,profile,policy):
    payload=profile['templates'][n['template']]
    # Manifest edits do not invalidate independent result consumers. Bind the
    # selected registered operation plus global grant/admission policy only.
    global_policy={k:v for k,v in policy.items() if k not in {'campaigns','sources','repos','reports','workflow_operations','research'}}
    registry={'sync':'sources','patch_test_ci':'repos','review_report':'reports','workflow_operation':'workflow_operations','studious_research':'research'}[payload['kind']]
    ref=payload.get('source_profile',payload.get('repo_profile',payload.get('report_profile',payload.get('operation_profile',payload.get('research_profile')))))
    selected_policy=policy.get(registry,{}).get(ref)
    return core.digest([n,payload,{k:profile['inputs'][k] for k in n['inputs']},global_policy,selected_policy])


def _identity(alias,manifest):
    return alias+':'+manifest['campaign_id']


def _node_key(key,rev,node):
    return core.digest([key,rev,node])


def _retire_terminal_leases(db,key):
    """Canonical terminal jobs release reservations; running/unknown jobs retain them."""
    rows=db.execute('SELECT n.revision,n.node,j.state FROM workflow_node_jobs n JOIN jobs j ON j.id=n.job_id WHERE n.campaign=?',(key,)).fetchall()
    for row in rows:
        if row['state'] not in core.TERMINAL:continue
        lease_key=_node_key(key,row['revision'],row['node']);record=state.get(db,'node_lease',lease_key)
        if not record or record['value']['state']!='RESERVED':continue
        owner=record['value']['lease']['owner']
        db.execute('DELETE FROM workflow_leases WHERE owner=?',(owner,))
        db.execute('DELETE FROM workflow_reservations WHERE owner=?',(owner,))
        state.put(db,'node_lease',lease_key,{**record['value'],'state':'RELEASED'},record['revision'])


def _observe_nodes(db,key,manifest):
    rows={r['node']:r for r in db.execute('SELECT n.*,j.state AS job_state,j.cancel_requested,j.lease_until FROM workflow_node_jobs n JOIN jobs j ON j.id=n.job_id WHERE campaign=? AND revision=?',(key,manifest['revision']))}
    values={}
    for n in manifest['nodes']:
        row=rows.get(n['id'])
        reused=state.get(db,'reused_node',_node_key(key,manifest['revision'],n['id']))
        if reused:
            prior=db.execute('SELECT state,cancel_requested FROM jobs WHERE id=?',(reused['value']['job_id'],)).fetchone()
            if prior and prior[0]=='SUCCEEDED':
                rows[n['id']]={'node':n['id'],'job_id':reused['value']['job_id'],'job_state':'SUCCEEDED','cancel_requested':prior[1],'reused':True}
                values[n['id']]='SUCCEEDED'
                continue
        values[n['id']]='WAITING' if row is None else ('UNKNOWN_EFFECT' if row['job_state']=='NEEDS_RECONCILIATION' or row['job_state']=='RUNNING' and row['lease_until']<time.time() else row['job_state'])
    return rows,values


def advance(store,policy,alias,*,now=None):
    profile,m=load_manifest(policy,alias);key=_identity(alias,m);now=time.time() if now is None else state.number(now)
    with state.transaction(store) as db:
        old=state.get(db,'campaign',key)
        record=old['value'] if old else {'alias':alias,'manifest':m,'policy_hash':core.digest(policy),'state':'ACTIVE','started':now,'admissions':0}
        expected=old['revision'] if old else 0
        if record['manifest']!=m or record['policy_hash']!=core.digest(policy):
            # Explicit refresh() handles revisions and selective reuse.
            raise ValueError('CAMPAIGN_BINDING_CHANGED')
        _retire_terminal_leases(db,key)
        if record['state'] in {'CANCELLED','DEFERRED','SUCCEEDED','PAUSED'}:
            return {'state':record['state'],'admitted':[]}
        rows,values=_observe_nodes(db,key,m)
        unknown=[k for k,v in values.items() if v=='UNKNOWN_EFFECT']
        if now-record['started']>=m['limits']['max_elapsed_seconds']:
            state.put(db,'campaign',key,{**record,'state':'DEFERRED','reason':'CAMPAIGN_DEADLINE','unknown_nodes':unknown},expected)
            return {'state':'DEFERRED','admitted':[]}
        admitted=[];blockers={}
        for n in m['nodes']:
            row=rows.get(n['id'])
            if record['admissions']+len(admitted)>=m['limits']['max_transfers'] and row is None:
                blockers[n['id']]='TRANSFER_BUDGET';continue
            if row is not None:
                if isinstance(row,dict) and row.get('reused',False):
                    continue
                continue
            if any(values[parent]!='SUCCEEDED' for parent in n['needs']):
                blockers[n['id']]='DEPENDENCY_WAIT';continue
            if unknown:
                blockers[n['id']]='RECONCILIATION_REQUIRED';continue
            try:
                for i in n['inputs']:
                    p=profile['inputs'][i];state.registered_file(p['file'],p['sha256'])
                owner='node:'+_node_key(key,m['revision'],n['id'])
                # SAVEPOINT ensures failed admission leaves no partial reservations.
                db.execute('SAVEPOINT admission')
                lease=state.acquire(db,owner,n['resources'],profile.get('capacity',{}),n['demand'],now=now,seconds=profile.get('lease_seconds',300))
                job=core.enqueue_in_transaction(db,policy,owner,profile['templates'][n['template']])
                db.execute('INSERT INTO workflow_node_jobs VALUES (?,?,?,?,?)',(key,m['revision'],n['id'],node_fingerprint(n,profile,policy),job['id']))
                state.put(db,'node_lease',_node_key(key,m['revision'],n['id']),{'state':'RESERVED','lease':lease,'inputs':[profile['inputs'][i] for i in n['inputs']]},0)
                db.execute('RELEASE admission');admitted.append(job['id']);values[n['id']]='QUEUED'
            except ValueError as exc:
                if db.in_transaction:
                    # Savepoint is optional when preflight failed before admission.
                    try:
                        db.execute('ROLLBACK TO admission');db.execute('RELEASE admission')
                    except __import__('sqlite3').OperationalError:
                        pass
                blockers[n['id']]=str(exc)
        record={**record,'state':'SUCCEEDED' if all(v=='SUCCEEDED' for v in values.values()) else 'ACTIVE',
                'blockers':blockers,'admissions':record['admissions']+len(admitted)}
        state.put(db,'campaign',key,record,expected)
        return {'state':record['state'],'admitted':admitted,'blockers':blockers,'worker_started':False}


def inspect(store,policy,alias,*,offset=0,limit=20):
    profile,m=load_manifest(policy,alias);key=_identity(alias,m)
    state.integer(offset);core.strict_int(limit,1,100)
    with state.transaction(store) as db:
        record=state.get(db,'campaign',key);_,values=_observe_nodes(db,key,m)
        page=m['nodes'][offset:offset+limit]
        blockers=record['value'].get('blockers',{}) if record else {}
        return {'campaign_id':m['campaign_id'],'revision':m['revision'],'state':record['value']['state'] if record else 'PROPOSED',
                'goal_ids':m['goal_ids'],'total':len(m['nodes']),'offset':offset,'next_offset':offset+len(page) if offset+len(page)<len(m['nodes']) else None,
                'nodes':[{'id':n['id'],'state':values[n['id']],'reason':blockers.get(n['id'])} for n in page],'manifest_digest':core.digest(m),'policy_digest':core.digest(policy)}


def cancel(store,policy,alias):
    """Local STOP does not need a valid input manifest or a current execution grant."""
    core.identifier(alias)
    with state.transaction(store) as db:
        records=[(r[0],r[1],json.loads(r[2])) for r in db.execute("SELECT id,revision,payload FROM workflow_records WHERE kind='campaign'")]
        matched=[r for r in records if r[2].get('alias')==alias]
        if not matched:raise ValueError('CAMPAIGN_NOT_STARTED')
        for key,revision,value in matched:
            for row in db.execute('SELECT job_id FROM workflow_node_jobs WHERE campaign=?',(key,)):
                job=db.execute('SELECT state FROM jobs WHERE id=?',(row[0],)).fetchone()
                if job and job[0] not in core.TERMINAL:
                    target=job[0] if job[0] in {'RUNNING','NEEDS_RECONCILIATION'} else 'CANCELLED'
                    db.execute('UPDATE jobs SET state=?,cancel_requested=1 WHERE id=?',(target,row[0]))
                    core.event(db,row[0],target,{'campaign_stop':key})
            _retire_terminal_leases(db,key)
            state.put(db,'campaign',key,{**value,'state':'CANCELLED'},revision)
        return {'state':'CANCELLED','cancel_requested':True}


def set_admission(store,policy,alias,paused):
    _,m=load_manifest(policy,alias);key=_identity(alias,m)
    with state.transaction(store) as db:
        old=state.get(db,'campaign',key)
        if old is None:raise ValueError('CAMPAIGN_NOT_STARTED')
        if old['value']['manifest']!=m or old['value']['policy_hash']!=core.digest(policy):raise ValueError('CAMPAIGN_BINDING_CHANGED')
        if old['value']['state'] not in {'ACTIVE','PAUSED'}:raise ValueError('CAMPAIGN_TERMINAL_INTENT')
        value={**old['value'],'state':'PAUSED' if paused else 'ACTIVE'}
        state.put(db,'campaign',key,value,old['revision'])
        return {'state':value['state'],'already_admitted_jobs_may_finish':True}


def refresh(store,old_policy,new_policy,alias):
    old_profile,old_manifest=load_manifest(old_policy,alias);profile,m=load_manifest(new_policy,alias)
    key=_identity(alias,m)
    if m['campaign_id']!=old_manifest['campaign_id'] or m['revision']!=old_manifest['revision']+1:
        raise ValueError('CAMPAIGN_REVISION_SEQUENCE')
    with state.transaction(store) as db:
        old=state.get(db,'campaign',key)
        if old is None or old['value']['manifest']!=old_manifest:raise ValueError('CAMPAIGN_PREDECESSOR_REQUIRED')
        if old['value']['state']=='CANCELLED':raise ValueError('CAMPAIGN_CANCELLED_INTENT')
        rows,values=_observe_nodes(db,key,old_manifest)
        if any(v in {'QUEUED','RUNNING','RETRY_READY','WAITING_CI','UNKNOWN_EFFECT'} for v in values.values()):
            raise ValueError('CAMPAIGN_ACTIVE_OR_UNKNOWN_EFFECT')
        _retire_terminal_leases(db,key)
        old_nodes={n['id']:n for n in old_manifest['nodes']};reused=set()
        # Evaluate dependencies topologically without recursive graph traversal.
        remaining=list(m['nodes'])
        while remaining:
            ready=[n for n in remaining if all(p in reused or p not in old_nodes or p not in {x['id'] for x in remaining} for p in n['needs'])]
            if not ready:ready=[remaining[0]]  # invalidated predecessor need not block traversal
            for n in ready:
                prior=old_nodes.get(n['id']);row=rows.get(n['id'])
                identical=prior is not None and node_fingerprint(prior,old_profile,old_policy)==node_fingerprint(n,profile,new_policy) and all(p in reused for p in n['needs'])
                # Grants/policy changes conservatively invalidate result reuse.
                if identical and values.get(n['id'])=='SUCCEEDED':
                    for i in n['inputs']:state.registered_file(profile['inputs'][i]['file'],profile['inputs'][i]['sha256'])
                    # One job may have many result consumers; mapping uses a receipt
                    # reference, not a duplicate job/effect.
                    state.put(db,'reused_node',_node_key(key,m['revision'],n['id']),{'state':'SUCCEEDED','job_id':row['job_id'],'fingerprint':node_fingerprint(n,profile,new_policy)},0)
                    reused.add(n['id'])
                remaining.remove(n)
        state.put(db,'campaign',key,{'alias':alias,'manifest':m,'policy_hash':core.digest(new_policy),'state':'ACTIVE','started':time.time(),'admissions':0,'reused_nodes':sorted(reused)},old['revision'])
        return {'state':'ACTIVE','reused_nodes':sorted(reused),'invalidated_nodes':sorted(set(n['id'] for n in m['nodes'])-reused)}


def worker_guard(store,job_id,*,now=None,job=None):
    """Called by existing Core at every heartbeat; fences never bypass its lease."""
    now=time.time() if now is None else now
    with state.transaction(store) as db:
        row=db.execute('SELECT campaign,revision,node FROM workflow_node_jobs WHERE job_id=?',(job_id,)).fetchone()
        if not row:return
        if job is not None:state.assert_job(db,job)
        campaign=state.get(db,'campaign',row[0])
        if not campaign or campaign['value']['state'] in {'CANCELLED','DEFERRED'} or now-campaign['value']['started']>=campaign['value']['manifest']['limits']['max_elapsed_seconds']:
            raise ValueError('CAMPAIGN_DEADLINE_OR_STOP')
        job=db.execute('SELECT attempt FROM jobs WHERE id=?',(job_id,)).fetchone()
        if job[0]>campaign['value']['manifest']['limits']['max_iterations']:
            raise ValueError('CAMPAIGN_ATTEMPT_BUDGET')
        record=state.get(db,'node_lease',_node_key(row[0],row[1],row[2]))
        if record is None or record['value']['state']!='RESERVED':raise ValueError('WORKFLOW_FENCE_LOST')
        for p in record['value']['inputs']:state.registered_file(p['file'],p['sha256'])
        lease=record['value']['lease'];state.check_fence(db,lease,now)
        db.execute('UPDATE workflow_leases SET expires=? WHERE owner=?',(now+300,lease['owner']))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',type=Path);p.add_argument('--store',type=Path)
    p.add_argument('action',choices=('advance','inspect','cancel','pause','resume'));p.add_argument('--campaign',required=True)
    p.add_argument('--offset',type=int,default=0);p.add_argument('--limit',type=int,default=20)
    a=p.parse_args(argv)
    try:
        if a.store is not None:
            if a.action!='cancel' or a.profile is not None or not a.store.is_absolute():raise ValueError('CAMPAIGN_LOCAL_STOP_ONLY')
            print(core.encoded(cancel(a.store,{},a.campaign)));return 0
        if a.profile is None:raise ValueError('CAMPAIGN_PROFILE_REQUIRED')
        from native_adapter import operator_profile
        profile,policy=operator_profile(a.profile)
        if a.campaign not in profile.get('campaigns',[]):raise ValueError('CAMPAIGN_OUTSIDE_OPERATOR_SCOPE')
        if a.action=='inspect':result=inspect(profile['store'],policy,a.campaign,offset=a.offset,limit=a.limit)
        elif a.action in {'pause','resume'}:result=set_admission(profile['store'],policy,a.campaign,a.action=='pause')
        else:result=globals()[a.action](profile['store'],policy,a.campaign)
        print(core.encoded(result));return 0
    except (OSError,ValueError,KeyError,TypeError):
        print(core.encoded({'state':'BLOCKED','reason':'CAMPAIGN_OPERATION_BLOCKED'}));return 2

if __name__=='__main__':sys.exit(main())
