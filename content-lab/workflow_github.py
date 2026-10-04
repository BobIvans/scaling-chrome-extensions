"""Policy-bound authenticated GitHub GET observer, reusing existing CI transport.

Git fetch uses the registered remote without inheriting credentials; private
repositories require operator-prefetched objects. No remote refs are written.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
from urllib.parse import quote

import automation_core as core
import github_ci_snapshot as ci
import workflow_state as state

FIELDS={'root','repository','remote_identity','base_ref','base_commit','head_commit','proposal_tree',
        'pr_number','token_env','required_checks','tests','timeout_seconds','max_pages'}


def validate_profile(c):
    if not isinstance(c,dict) or set(c)!=FIELDS:raise ValueError('GITHUB_WORKFLOW_PROFILE')
    if not isinstance(c['repository'],str) or not ci.REPOSITORY.fullmatch(c['repository']):raise ValueError('GITHUB_WORKFLOW_REPOSITORY')
    if not isinstance(c['token_env'],str) or not ci.TOKEN_ENV.fullmatch(c['token_env']):raise ValueError('GITHUB_WORKFLOW_TOKEN_ENV')
    if not isinstance(c['base_ref'],str) or not re.fullmatch(r'[A-Za-z0-9_./-]+',c['base_ref']) or '..' in c['base_ref']:raise ValueError('GITHUB_WORKFLOW_REF')
    if not isinstance(c['root'],str) or not Path(c['root']).is_absolute() or c['remote_identity']!='https://github.com/'+c['repository']+'.git':raise ValueError('GITHUB_WORKFLOW_REMOTE')
    state.integer(c['pr_number'],1);core.strict_int(c['timeout_seconds'],1,30);core.strict_int(c['max_pages'],1,10)
    for k in ('base_commit','head_commit','proposal_tree'):
        if not isinstance(c[k],str) or not ci.SHA.fullmatch(c[k]):raise ValueError('GITHUB_WORKFLOW_EXACT_REVISION')
    if not isinstance(c['required_checks'],list) or not c['required_checks'] or not all(isinstance(x,str) and x for x in c['required_checks']):raise ValueError('GITHUB_WORKFLOW_REQUIRED_CHECKS')
    if not isinstance(c['tests'],list) or not c['tests'] or not all(isinstance(a,list) and a and all(isinstance(x,str) and x and '\0' not in x for x in a) for a in c['tests']):raise ValueError('GITHUB_WORKFLOW_REGISTERED_TESTS')
    return c


def collect_metadata(c,token,requester=ci._request_json):
    validate_profile(c)
    if not isinstance(token,str) or not token or '\n' in token or '\r' in token:raise ValueError('GITHUB_TOKEN_MISSING')
    root=ci.API_ROOT+'/repos/'+quote(c['repository'],safe='/')
    pr=requester(root+'/pulls/'+str(c['pr_number']),token,c['timeout_seconds'])
    if not isinstance(pr,dict):raise ValueError('GITHUB_MERGE_NOT_CONFIRMED_OR_DRIFT')
    head=pr.get('head');base=pr.get('base')
    if not isinstance(head,dict) or not isinstance(base,dict) or not isinstance(base.get('repo'),dict) or pr.get('merged') is not True or not pr.get('merged_at') or head.get('sha')!=c['head_commit'] or base.get('ref')!=c['base_ref'] or base['repo'].get('full_name')!=c['repository']:
        raise ValueError('GITHUB_MERGE_NOT_CONFIRMED_OR_DRIFT')
    merge=pr.get('merge_commit_sha')
    if not isinstance(merge,str) or not ci.SHA.fullmatch(merge):raise ValueError('GITHUB_MERGE_COMMIT_MISSING')
    ref=requester(root+'/git/ref/heads/'+quote(c['base_ref'],safe='/'),token,c['timeout_seconds'])
    current=ref.get('object',{}).get('sha') if isinstance(ref,dict) and isinstance(ref.get('object'),dict) else None
    if not isinstance(current,str) or not ci.SHA.fullmatch(current):raise ValueError('GITHUB_CURRENT_REF_REQUIRED')
    config={'repository':c['repository'],'timeout_seconds':c['timeout_seconds'],'max_pages':c['max_pages'],'required_checks':c['required_checks']}
    snapshot=ci.collect(config,current,token,requester=requester)
    latest={}
    for check in snapshot.get('checks',[]):
        name=check['name'];prior=latest.get(name)
        if prior and prior['run_id']==check['run_id'] and prior!=check:
            raise ValueError('GITHUB_FINAL_REVISION_CI_AMBIGUOUS')
        if prior is None or check['run_id']>prior['run_id']:latest[name]=check
    selected=[latest.get(name) for name in c['required_checks']]
    if snapshot.get('transport_status')!='OBSERVED' or any(x is None or x['status']!='completed' or x['conclusion']!='success' or x['head_sha']!=current for x in selected):
        raise ValueError('GITHUB_FINAL_REVISION_CI_REQUIRED')
    return {'pr_number':c['pr_number'],'repository':c['repository'],'head_commit':c['head_commit'],'merge_commit':merge,'result_commit':current,'ci_snapshot_digest':core.digest(snapshot),'ci_snapshot':snapshot}


def observe(owner,job,c):
    from workflow_runtime import observe_merge
    metadata=collect_metadata(c,os.environ.get(c['token_env'],''))
    owner.heartbeat(job)
    # Only the registered remote and exact authenticated result object are read.
    root=Path(c['root']);git=lambda *a:owner.git(job,root,*a)
    if git('remote','get-url','origin')!=c['remote_identity']:raise ValueError('WORKFLOW_REPOSITORY_IDENTITY_CHANGED')
    existing=owner.command(job,['git','cat-file','-e',metadata['result_commit']+'^{commit}'],root,30)
    if existing['exit_code']:
        git('fetch','--quiet','--no-tags','--no-recurse-submodules',c['remote_identity'],metadata['result_commit'])
    reachable=owner.command(job,['git','merge-base','--is-ancestor',metadata['merge_commit'],metadata['result_commit']],root,30)
    if reachable['exit_code']:raise ValueError('GITHUB_MERGE_NOT_REACHABLE')
    local_ref='refs/heads/occ-observed-'+job['id']
    git('update-ref',local_ref,metadata['result_commit'],'0'*40)
    local={'root':c['root'],'repository_id':c['repository'],'remote_identity':c['remote_identity'],'target_ref':local_ref,
           'base_commit':c['base_commit'],'proposal_commit':c['head_commit'],'expected_tree':c['proposal_tree'],'tests':c['tests'],'timeout_seconds':c['timeout_seconds']}
    result=observe_merge(owner,job,local)
    # Fresh ref observation prevents a post-observation revert being called current.
    token=os.environ.get(c['token_env'],'');url=ci.API_ROOT+'/repos/'+quote(c['repository'],safe='/')+'/git/ref/heads/'+quote(c['base_ref'],safe='/')
    fresh=ci._request_json(url,token,c['timeout_seconds'])
    if not isinstance(fresh,dict) or not isinstance(fresh.get('object'),dict) or fresh['object'].get('sha')!=metadata['result_commit']:raise ValueError('GITHUB_TARGET_DRIFT')
    receipt={**result,**metadata,'origin':'AUTHENTICATED_GITHUB_AND_LOCAL_GIT','state':'MERGE_VERIFIED','ci':'EXACT_RESULT_REVISION_VERIFIED','installed':False,'usable':False}
    with state.transaction(owner.store) as db:
        state.assert_job(db,job);state.put(db,'github_merge_observation',job['id'],receipt,0)
    return receipt
