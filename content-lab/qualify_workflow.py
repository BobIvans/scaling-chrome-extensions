"""Offline replay of actual canonical jobs in a NEW isolated directory.

No providers, token use, production installation or implicit publish. A negative
experiment is deliberately retained in the next draft. Run from a Git checkout.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import automation_core as core
import campaign_runtime as campaign
import release_updater as updater
import workflow_state as state


def replay(destination):
    root=Path(destination)
    if not root.is_absolute():raise ValueError('REPLAY_ABSOLUTE_NEW_DIRECTORY_REQUIRED')
    root.mkdir(parents=True,exist_ok=False)
    source=root/'source';source.mkdir();note=source/'note.txt';note.write_text('Original qualification input.\n',encoding='utf-8')
    store=root/'store';target=root/'isolated-installation';target.mkdir()
    checkout=Path(__file__).resolve().parents[1]
    git=lambda ref:subprocess.check_output(['git','rev-parse',ref],cwd=checkout,text=True).strip()
    commit,tree=git('HEAD'),git('HEAD^{tree}')
    asset=root/'candidate.zip'
    with zipfile.ZipFile(asset,'w') as z:z.writestr('feature.txt',note.read_bytes())
    binding={'source_commit':commit,'source_tree':tree,'asset_sha256':state.file_digest(asset),'data_schema_version':0,
             'files':{'feature.txt':{'bytes':note.stat().st_size,'sha256':state.file_digest(note)}},
             'capabilities':{},'build_provenance':{'origin':'OFFLINE_OPERATOR_FIXTURE','independent_producer_proof':False}}
    binding_file=root/'binding.json';binding_file.write_text(core.encoded(binding),encoding='utf-8')
    sync={'kind':'sync','source_profile':'notes'}
    operation=lambda alias:{'kind':'workflow_operation','operation_profile':alias}
    limits={'max_iterations':3,'max_elapsed_seconds':300,'max_transfers':10,'no_progress_limit':2}
    node=lambda name,template,needs:{'id':name,'template':template,'needs':needs,'inputs':['note'],
                                   'resources':[{'id':'qualification-store','mode':'WRITE'}],'demand':{'cpu':1}}
    manifest={'schema':'occ.campaign.v1','campaign_id':'offline-qualification','revision':1,'goal_ids':['GOAL5-20'],
              'criteria':[{'id':'retain-negative-trial','text':'Retain a failed trial without claiming qualification.'}],
              'nodes':[node('collect','collect',[]),node('negative-trial','trial',['collect']),
                       node('stage','stage',['negative-trial']),node('next-brief','brief',['stage'])],'limits':limits}
    manifest_file=root/'campaign.json';manifest_file.write_text(core.encoded(manifest),encoding='utf-8')
    policy={'schema':'occ.automation-policy.v1','max_parallel':1,'money_budget':0,'repos':{},
            'sources':{'notes':{'root':str(source),'namespace':'notes'}},
            'workflow_operations':{
              'trial':{'action':'experiment','config':{'root':str(source),'argv':[sys.executable,'-B','-c','raise SystemExit(2)'],
                       'timeout_seconds':5,'input_file':str(note),'input_sha256':state.file_digest(note),
                       'criteria_ids':['retain-negative-trial'],'hypothesis_id':'negative-fixture'}},
              'stage':{'action':'release_update','config':{'mode':'STAGE_ONLY','root':str(target),'device_id':'test-device','installation_id':'test-installation',
                       'asset_file':str(asset),'asset_sha256':binding['asset_sha256'],'binding_file':str(binding_file),'binding_sha256':state.file_digest(binding_file),
                       'source_commit':commit,'source_tree':tree,'tests':[[sys.executable,'-B','-c',"from pathlib import Path; assert Path('feature.txt').is_file()"]],'timeout_seconds':5}},
              'brief':{'action':'campaign_brief','config':{'campaign':'offline','planner_version':'v1','loop_id':'offline-loop','limits':limits}}},
            'campaigns':{'offline':{'manifest_file':str(manifest_file),'manifest_sha256':state.file_digest(manifest_file),
                       'templates':{'collect':sync,'trial':operation('trial'),'stage':operation('stage'),'brief':operation('brief')},
                       'inputs':{'note':{'file':str(note),'sha256':state.file_digest(note)}},'capacity':{'cpu':1},'lease_seconds':300}}}
    policy_file=root/'policy.json';policy_file.write_text(core.encoded(policy),encoding='utf-8')
    profile={'schema':'occ.native-durable-profile.v1','store':str(store),'policy_file':str(policy_file),
             'namespaces':['notes'],'templates':{'collect':sync},'campaigns':['offline']}
    (root/'profile.json').write_text(core.encoded(profile),encoding='utf-8')
    jobs=[]
    for _ in range(len(manifest['nodes'])+1):
        admitted=campaign.advance(store,policy,'offline')
        if admitted['state']=='SUCCEEDED':break
        for _ in admitted['admitted']:
            result=core.Core(store,policy).run_once();jobs.append(result)
            if result['state']!='SUCCEEDED':raise ValueError('REPLAY_JOB_FAILED')
    view=campaign.inspect(store,policy,'offline')
    if view['state']!='SUCCEEDED' or (target/'active.json').exists():raise ValueError('REPLAY_UNEXPECTED_EFFECT')
    draft=jobs[-1]['result']
    if draft['state']!='DRAFT_NOT_SENT' or draft['usable'] or not any(x['outcome']=='NEGATIVE_OR_FAILED' for x in draft['negative_and_other_trials']):
        raise ValueError('REPLAY_NEGATIVE_RESULT_LOST')
    receipt={'schema':'occ.workflow-replay.v1','scope':'ISOLATED_OFFLINE_FIXTURE','source_commit':commit,'source_tree':tree,
             'campaign':view,'job_ids':[j['id'] for j in jobs],'job_states':[j['state'] for j in jobs],
             'negative_trials':draft['negative_and_other_trials'],'brief_id':draft['brief_id'],'installed':False,
             'usable':False,'device_qualified':False,'external_transfers':0,'canonical_database_count':len(list(store.glob('*.sqlite3')))}
    if receipt['canonical_database_count']!=1:raise ValueError('REPLAY_COMPETING_DATABASE')
    (root/'REPLAY_RECEIPT.json').write_text(core.encoded(receipt)+'\n',encoding='utf-8')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:print(core.encoded(replay(args.output)));return 0
    except (OSError,ValueError,subprocess.SubprocessError):
        print(core.encoded({'state':'BLOCKED','reason':'OFFLINE_REPLAY_FAILED'}));return 2

if __name__=='__main__':sys.exit(main())
