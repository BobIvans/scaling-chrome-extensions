"""Registered workflow operations executed by the EXISTING serial Core.

Inputs are policy-owned profiles. Source/AI JSON cannot choose argv, paths,
release channel, scope, installation target or money. No GitHub write is made.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import time

import automation_core as core
import workflow_state as state

ACTIONS={'campaign_brief','github_merge_observe','brief','experiment','merge_observe','release_update'}


def validate_operation_job(payload,policy):
    if set(payload)!={'kind','operation_profile'} or payload['kind']!='workflow_operation':
        raise ValueError('WORKFLOW_OPERATION_SCHEMA')
    alias=core.identifier(payload['operation_profile'])
    profile=policy.get('workflow_operations',{}).get(alias)
    if not isinstance(profile,dict) or set(profile)!={'action','config'} or profile['action'] not in ACTIONS or not isinstance(profile['config'],dict):
        raise ValueError('WORKFLOW_REGISTERED_OPERATION_REQUIRED')
    if profile['action']=='campaign_brief':
        c=profile['config']
        if set(c)!={'campaign','planner_version','loop_id','limits'} or c['campaign'] not in policy.get('campaigns',{}):raise ValueError('WORKFLOW_CAMPAIGN_BRIEF_PROFILE')
        core.identifier(c['loop_id'])
        if not isinstance(c['limits'],dict) or set(c['limits'])!={'max_iterations','max_elapsed_seconds','max_transfers','no_progress_limit'}:raise ValueError('WORKFLOW_LOOP_LIMITS_REQUIRED')
        for v in c['limits'].values():state.integer(v,1)
    if profile['action']=='github_merge_observe':
        from workflow_github import validate_profile
        validate_profile(profile['config'])
    if profile['action']=='release_update':
        from release_updater import validate_profile
        validate_profile(profile['config'])
    if profile['action']=='experiment':
        c=profile['config']
        if set(c)!={'root','argv','timeout_seconds','input_file','input_sha256','criteria_ids','hypothesis_id'}:
            raise ValueError('WORKFLOW_EXPERIMENT_PROFILE')
        if not Path(c['root']).is_absolute() or not isinstance(c['argv'],list) or not c['argv'] or not all(isinstance(x,str) and x and '\0' not in x for x in c['argv']):
            raise ValueError('WORKFLOW_REGISTERED_ARGV_REQUIRED')
        core.strict_int(c['timeout_seconds'],1,300);state.checked_hash(c['input_sha256'])
    if profile['action']=='brief':
        c=profile['config']
        if set(c)!={'input_file','input_sha256','planner_version','max_iterations','no_progress_limit'}:
            raise ValueError('WORKFLOW_BRIEF_PROFILE')
        state.checked_hash(c['input_sha256']);state.integer(c['max_iterations'],1);state.integer(c['no_progress_limit'],1)
    if profile['action']=='merge_observe':
        c=profile['config']
        if set(c)!={'root','repository_id','remote_identity','target_ref','base_commit','proposal_commit','expected_tree','tests','timeout_seconds'}:
            raise ValueError('WORKFLOW_MERGE_PROFILE')
        if not Path(c['root']).is_absolute() or not re.fullmatch(r'refs/heads/[A-Za-z0-9_./-]+',c['target_ref']) or '..' in c['target_ref']:
            raise ValueError('WORKFLOW_PINNED_TARGET_REQUIRED')
        for k in ('base_commit','proposal_commit','expected_tree'):
            if not isinstance(c[k],str) or not core.SHA.fullmatch(c[k]):raise ValueError('WORKFLOW_EXACT_GIT_OBJECT_REQUIRED')
        if not isinstance(c['tests'],list) or not c['tests'] or not all(isinstance(argv,list) and argv and all(isinstance(x,str) and x and '\0' not in x for x in argv) for argv in c['tests']):
            raise ValueError('WORKFLOW_REGISTERED_ARGV_REQUIRED')
        core.strict_int(c['timeout_seconds'],1,300)
    return profile


def project_brief(data,config):
    if not isinstance(data,dict) or set(data)!={'goal_ids','criteria','claims','trials','gaps','evidence_delta'}:
        raise ValueError('WORKFLOW_BRIEF_INPUT_SCHEMA')
    if not all(isinstance(data[k],list) for k in ('goal_ids','criteria','claims','trials','gaps')):
        raise ValueError('WORKFLOW_BRIEF_INPUT_SCHEMA')
    claims=[];groups={}
    for c in data['claims']:
        if not isinstance(c,dict) or set(c)!={'id','text','source_ref','source_sha256','lineage','primary_source_ref'}:
            raise ValueError('WORKFLOW_CLAIM_SCHEMA')
        if not isinstance(c['lineage'],list):raise ValueError('WORKFLOW_CLAIM_LINEAGE')
        # Imported status cannot mark verification; even a hash is not proof of truth.
        primary=c['primary_source_ref'];source=c['source_ref'];h=c['source_sha256']
        valid=isinstance(primary,str) and primary and isinstance(source,str) and source and isinstance(h,str) and len(h)==64 and all(x in '0123456789abcdef' for x in h)
        group=core.digest([primary or 'UNKNOWN',h or 'UNKNOWN'])
        groups.setdefault(group,[]).append(c['id'])
        claims.append({**c,'provenance_state':'SOURCE_LINKED_UNVERIFIED' if valid else 'UNKNOWN','correlation_group':group})
    gaps=[]
    for g in data['gaps']:
        if not isinstance(g,dict) or set(g)!={'id','task_id','kind','owner','dependencies','acceptance','recovery','source_refs','priority','revisit_condition'}:
            raise ValueError('WORKFLOW_GAP_SCHEMA')
        if g['kind'] not in {'MISSING_CODE','MISSING_EVIDENCE','MISSING_RELEASE','MISSING_DEVICE_BINDING','MISSING_DATA','MISSING_ACCESS'}:
            raise ValueError('WORKFLOW_GAP_KIND')
        state.integer(g['priority'])
        if not all(isinstance(g[k],list) for k in ('dependencies','acceptance','recovery','source_refs')):
            raise ValueError('WORKFLOW_GAP_SCHEMA')
        gaps.append(g)
    gaps.sort(key=lambda x:(-x['priority'],x['id']))
    generation=core.digest([data,config['planner_version']])
    return {'schema':'occ.next-brief.v1','brief_id':generation,'state':'DRAFT_NOT_SENT',
            'goal_ids':data['goal_ids'],'criteria':data['criteria'],'task_ids':sorted(set(g['task_id'] for g in gaps)),
            'evidence_delta':data['evidence_delta'],'input_digest':core.digest(data),'planner_version':config['planner_version'],
            'claims':claims,'correlation_groups':groups,'negative_and_other_trials':data['trials'],
            'gaps':gaps,'selected_gap':gaps[0]['id'] if gaps else None,
            'rationale':'Highest configured gap priority; original criteria and negative results preserved.',
            'installed':'UNKNOWN','usable':False,'estimated_cost':'UNKNOWN','external_effects':0,
            'stop_conditions':{'max_iterations':config['max_iterations'],'no_progress_limit':config['no_progress_limit']}}


def build_brief(store,config,progress=None,*,job=None):
    path=state.registered_file(config['input_file'],config['input_sha256'],progress)
    raw=path.read_bytes()
    if __import__('hashlib').sha256(raw).hexdigest()!=config['input_sha256']:raise ValueError('WORKFLOW_SOURCE_DRIFT')
    data=json.loads(raw.decode('utf-8'));brief=project_brief(data,config)
    with state.transaction(store) as db:
        if job is not None:state.assert_job(db,job)
        old=state.get(db,'brief',brief['brief_id'])
        if old:return {**old['value'],'reused':True}
        state.put(db,'brief',brief['brief_id'],brief,0)
    return {**brief,'reused':False}


def run_experiment(owner,job,config):
    path=state.registered_file(config['input_file'],config['input_sha256'],lambda:owner.heartbeat(job))
    before=state.file_digest(path)
    result=owner.command(job,config['argv'],Path(config['root']),config['timeout_seconds'])
    if state.file_digest(path)!=before:raise ValueError('WORKFLOW_EXPERIMENT_INPUT_DRIFT')
    receipt={'schema':'occ.experiment-receipt.v1','hypothesis_id':config['hypothesis_id'],
             'criteria_ids':config['criteria_ids'],'input_digest':before,'template_digest':core.digest(config),
             'outcome':'NEGATIVE_OR_FAILED' if result['exit_code'] or result['reason'] else 'EXECUTED_NOT_INDEPENDENTLY_VERIFIED',
             'result':result,'qualified':False,'criterion_closure':False,'transactions_sent':0}
    with state.transaction(owner.store) as db:
        state.assert_job(db,job)
        state.put(db,'experiment',job['id'],receipt,0)
    return receipt


def observe_merge(owner,job,config):
    """Observe real local Git refs/tree; final tests run at the actual target SHA.

No stale CI/operator JSON or textual merged claim can replace this observation.
Remote GitHub PR evidence remains separate from local target evidence.
"""
    root=Path(config['root']);git=lambda *a:owner.git(job,root,*a)
    remote=git('remote','get-url','origin')
    if remote!=config['remote_identity']:raise ValueError('WORKFLOW_REPOSITORY_IDENTITY_CHANGED')
    result=git('rev-parse','--verify',config['target_ref']+'^{commit}')
    tree=git('rev-parse',result+'^{tree}')
    base=config['base_commit'];proposal=config['proposal_commit']
    if git('rev-parse',proposal+'^{tree}')!=config['expected_tree']:
        raise ValueError('WORKFLOW_PROPOSAL_TREE_CHANGED')
    reach=owner.command(job,['git','merge-base','--is-ancestor',base,result],root,30)
    if reach['exit_code']:raise ValueError('WORKFLOW_BASE_NOT_REACHABLE')
    paths=git('diff','--no-renames','--name-only','-z',base,proposal).split('\0')
    paths=[x for x in paths if x]
    if not paths:raise ValueError('WORKFLOW_NO_PROPOSED_CHANGE')
    for path in paths:
        # Compare paths/modes/blobs, including deletes; no patch-id shortcut.
        if git('ls-tree','-z',proposal,'--',path)!=git('ls-tree','-z',result,'--',path):
            raise ValueError('WORKFLOW_RESULT_MAPPING_OR_REVERT_GAP')
    worktree=owner.store.resolve()/'worktrees'/('verify-'+job['id'])
    worktree.parent.mkdir(exist_ok=True)
    git('worktree','add','--detach',str(worktree),result)
    checks=[]
    try:
        for argv in config['tests']:
            r=owner.command(job,argv,worktree,config['timeout_seconds']);checks.append(r)
            if r['exit_code'] or r['reason']:raise ValueError('WORKFLOW_FINAL_TREE_TEST_FAILED')
        if owner.git(job,worktree,'status','--porcelain'):raise ValueError('TEST_MUTATED_WORKTREE')
        if git('rev-parse','--verify',config['target_ref']+'^{commit}')!=result:
            raise ValueError('WORKFLOW_TARGET_DRIFT')
    finally:
        # If cancelled/lease lost, do not start an unfenced Git metadata mutation.
        owner.git(job,root,'worktree','remove','--force',str(worktree))
    receipt={'schema':'occ.merge-observation.v1','repository_id':config['repository_id'],
             'origin':'OBSERVED_LOCAL_GIT','base_commit':base,'proposal_commit':proposal,'target_ref':config['target_ref'],
             'result_commit':result,'result_tree':tree,'mapping_paths':paths,'tests':checks,
             'state':'LOCAL_TARGET_VERIFIED','remote_pr_state':'NOT_OBSERVED','ci':'NOT_OBSERVED','installed':False,'usable':False}
    with state.transaction(owner.store) as db:
        state.assert_job(db,job)
        state.put(db,'merge_observation',job['id'],receipt,0)
    return receipt


def bounded_loop(store,key,config,progress_digest,*,unknown_effect=False,now=None):
    """Persist progress/stop taxonomy; never auto-dispatch another effect."""
    required={'max_iterations','max_elapsed_seconds','max_transfers','no_progress_limit'}
    if set(config)!=required:raise ValueError('WORKFLOW_LOOP_LIMITS_REQUIRED')
    for v in config.values():state.integer(v,1)
    now=time.time() if now is None else state.number(now)
    with state.transaction(store) as db:
        old=state.get(db,'loop',key)
        value=old['value'] if old else {'state':'ACTIVE','started':now,'iterations':0,'no_progress':0,'transfers':0,'progress':None,'config':config}
        if value['config']!=config:raise ValueError('WORKFLOW_LOOP_LIMIT_DRIFT')
        if value['state']!='ACTIVE':return value
        count=value['no_progress']+1 if value['progress']==progress_digest else 0
        reason=('UNKNOWN_EFFECT' if unknown_effect else 'TIME_BUDGET' if now-value['started']>=config['max_elapsed_seconds'] else
                'ITERATION_BUDGET' if value['iterations']>=config['max_iterations'] else
                'TRANSFER_BUDGET' if value['transfers']>=config['max_transfers'] else
                'NO_PROGRESS' if count>=config['no_progress_limit'] else None)
        value={**value,'state':'DEFERRED' if reason else 'ACTIVE','reason':reason,
               'iterations':value['iterations']+(0 if reason else 1),'no_progress':count,'progress':progress_digest}
        state.put(db,'loop',key,value,old['revision'] if old else 0)
        return value


def execute_operation(owner,job):
    profile=validate_operation_job(job['payload'],owner.policy);action=profile['action'];config=profile['config']
    owner.heartbeat(job)
    if action=='campaign_brief':return campaign_brief(owner,job,config)
    if action=='brief':return build_brief(owner.store,config,lambda:owner.heartbeat(job),job=job)
    if action=='experiment':return run_experiment(owner,job,config)
    if action=='merge_observe':return observe_merge(owner,job,config)
    if action=='github_merge_observe':
        from workflow_github import observe
        return observe(owner,job,config)
    from release_updater import update
    return update(owner,job,config)


def campaign_brief(owner,job,config):
    """Prepare the next draft from ACTUAL canonical node/trial receipts.

Green execution is not criterion closure. Failed trials, missing installation
and unknown effects stay in the goal ledger. No provider or UI send is started.
"""
    from campaign_runtime import load_manifest, _identity
    profile,manifest=load_manifest(owner.policy,config['campaign'])
    key=_identity(config['campaign'],manifest)
    trials=[];gaps=[];unknown=False
    with state.transaction(owner.store) as db:
        state.assert_job(db,job)
        campaign=state.get(db,'campaign',key)
        rows=db.execute('SELECT n.node,j.id,j.state,j.result FROM workflow_node_jobs n JOIN jobs j ON n.job_id=j.id WHERE n.campaign=? AND n.revision=? ORDER BY n.node',(key,manifest['revision']))
        for row in rows:
            if row['id']==job['id']:continue
            result=json.loads(row['result']);trial={'node_id':row['node'],'job_id':row['id'],'job_state':row['state'],'result_digest':core.digest(result),'outcome':result.get('outcome',result.get('state','UNKNOWN'))}
            trials.append(trial)
            unknown=unknown or row['state']=='NEEDS_RECONCILIATION'
            if row['state']!='SUCCEEDED' or result.get('device_qualified') is False or result.get('qualified') is False:
                kind='MISSING_DEVICE_BINDING' if result.get('device_qualified') is False else 'MISSING_EVIDENCE'
                gaps.append({'id':'node-gap:'+row['node'],'task_id':row['node'],'kind':kind,'owner':'campaign criterion/device owner','dependencies':[],'acceptance':['Criterion-specific evidence for immutable input and exact build/device where required.'],'recovery':['Reconcile unknown effects before a new attempt.'],'source_refs':['job:'+row['id']],'priority':10,'revisit_condition':'new independently observed evidence'})
        if not campaign:
            gaps.append({'id':'not-started','task_id':manifest['campaign_id'],'kind':'MISSING_EVIDENCE','owner':'Core campaign owner','dependencies':[],'acceptance':['Observe registered campaign inputs and results.'],'recovery':['Preserve original manifest.'],'source_refs':['manifest:'+core.digest(manifest)],'priority':20,'revisit_condition':'campaign receipts'})
    # Frozen original criteria are retained even if all jobs completed. A separate
    # registered criterion verifier must later attach scope-matched closure proof.
    for criterion in manifest['criteria']:
        gaps.append({'id':'criterion-gap:'+criterion['id'],'task_id':criterion['id'],'kind':'MISSING_EVIDENCE','owner':'independent criterion verifier','dependencies':[],'acceptance':[criterion['text']],'recovery':['Retain original criterion until verified.'],'source_refs':['manifest:'+core.digest(manifest)],'priority':5,'revisit_condition':'criterion-specific receipt'})
    data={'goal_ids':manifest['goal_ids'],'criteria':manifest['criteria'],'claims':[], 'trials':trials,'gaps':gaps,
          'evidence_delta':core.digest([manifest,trials,campaign])}
    loop=bounded_loop(owner.store,config['loop_id'],config['limits'],data['evidence_delta'],unknown_effect=unknown)
    brief=project_brief(data,{'planner_version':config['planner_version'],'max_iterations':config['limits']['max_iterations'],'no_progress_limit':config['limits']['no_progress_limit']})
    brief['loop_state']=loop['state'];brief['loop_stop_reason']=loop['reason']
    with state.transaction(owner.store) as db:
        state.assert_job(db,job)
        old=state.get(db,'brief',brief['brief_id'])
        if not old:state.put(db,'brief',brief['brief_id'],brief,0)
        else:brief=old['value']
    return {**brief,'reused':old is not None,'loop_state':loop['state'],'loop_stop_reason':loop['reason']}
