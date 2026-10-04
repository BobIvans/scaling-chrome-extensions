"""PR004 package integrity/traceability and synthetic data only; no app imports."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re

from verify_stream_fixture import run as stream_fixture

ROOT=Path(__file__).resolve().parents[1]


def check(ok,reason):
    if not ok:
        raise ValueError(reason)


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid(value,schema):
    """Minimal stdlib validator for the constructs actually used in receipt schema."""
    if 'const' in schema and value != schema['const']:
        return False
    if 'enum' in schema and value not in schema['enum']:
        return False
    if 'type' in schema:
        t=schema['type']
        allowed=t if isinstance(t,list) else [t]
        kinds={'object':isinstance(value,dict),'string':isinstance(value,str),
               'integer':type(value) is int,'null':value is None,'boolean':type(value) is bool}
        if not any(kinds.get(k,False) for k in allowed):
            return False
    if isinstance(value,str):
        if 'pattern' in schema and re.search(schema['pattern'],value) is None:
            return False
        if len(value)<schema.get('minLength',0):
            return False
    if type(value) is int and (value<schema.get('minimum',value) or value>schema.get('maximum',value)):
        return False
    if isinstance(value,dict):
        props=schema.get('properties',{})
        if not set(schema.get('required',[])) <= set(value):
            return False
        if schema.get('additionalProperties') is False and set(value)-set(props):
            return False
        if any(not valid(v,props[k]) for k,v in value.items() if k in props):
            return False
    if 'allOf' in schema and not all(valid(value,s) for s in schema['allOf']):
        return False
    if 'if' in schema and valid(value,schema['if']) and 'then' in schema:
        return valid(value,schema['then'])
    return True


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths=[]

    def handle_starttag(self,tag,attrs):
        if tag=='a':
            self.paths += [v for k,v in attrs if k=='href']


def run():
    manifest=read('MANIFEST.json')
    rows=manifest['files']
    names=[r['path'] for r in rows]
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
    check(set(names)==actual and len(names)==len(set(names))==manifest['count'],'manifest member set')
    for row in rows:
        path=PurePosixPath(row['path'])
        check(not path.is_absolute() and '..' not in path.parts and '\\' not in row['path'],'unsafe package member')
        f=ROOT/row['path']
        check(not f.is_symlink() and f.stat().st_size==row['bytes'] and sha(f)==row['sha256'],'package hash '+row['path'])
    json_names=[n for n in names if n.endswith('.json')]
    for name in json_names:
        read(name)
    catalog=read('sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')['tasks']
    ids=[t['task_id'] for t in catalog]
    disposition=read('plan/ROADMAP_DISPOSITION.json')
    check(len(ids)==len(set(ids))==160,'roadmap tasks')
    check(ids==[t['source_task_id'] for t in disposition['tasks']],'disposition tasks')
    check(all(not t['task_closed'] for t in disposition['tasks']),'false task closure')
    for path,key,n in [('catalogs/FEATURE_DEFINITION_AUDIT.json','features',164),('goals/GOAL_REGISTER.json','goals',28),('audit/DECISION_REGISTER.json','decisions',24),('catalogs/MILESTONES_V5.json','milestones',10)]:
        check(len(read('sources/roadmap_v5/'+path)[key])==n,'registry '+path)
    plan=read('plan/PR_PLAN.json')
    check(plan['local_sequence']==4 and plan['source_task']=='LAYA4-003' and not plan['whole_task_closed'],'scope')
    check(not plan['application_code_changed'] and not plan['current_head_verified'] and not plan['previous_pr_implementation_verified'],'implementation overclaim')
    check(len(plan['tasks'])==6 and sum(t['budget_minutes'] for t in plan['tasks'])==60,'hour budget')
    seen=set()
    for t in plan['tasks']:
        check(set(t['depends_on'])<=seen and set(t['source_task_ids'])<=set(ids),'task dependencies')
        seen.add(t['id'])
    cases=read('plan/ACCEPTANCE_CASES.json')['cases']
    receipt=read('receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    check(len(cases)==16 and [c['criterion_id'] for c in cases]==[c['criterion_id'] for c in receipt['criterion_results']],'acceptance mapping')
    check(all(c['outcome']=='NOT_RUN' for c in cases+receipt['criterion_results']),'false runtime result')
    check(not receipt['whole_task_closed'] and receipt['state']=='NOT_IMPLEMENTED','receipt status')
    source=read('provenance/SOURCES.json')
    for row in source['preserved_files']:
        f=ROOT/row['package_path']
        check(f.stat().st_size==row['bytes'] and sha(f)==row['sha256'],'preserved source '+row['package_path'])
    source_map=read('provenance/ARCHIVED_SCE_SOURCE_MAP.json')
    for row in source_map['sources']:
        f=ROOT/'sources/archived_sce'/row['path']
        check(f.is_file() and f.stat().st_size==row['bytes'] and sha(f)==row['sha256'],'archived Git source '+row['path'])
        raw=f.read_bytes()
        check(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_oid'],'archived Git object identity '+row['path'])
    check(read('plan/SELECTED_SOURCE_TASK.json')==next(t for t in catalog if t['task_id']=='LAYA4-003'),'selected source task altered')
    status=read('coordination/PR_PACKAGE_STATUS.json')
    check([p['package'] for p in status['packages']]==['PR-001','PR-002','PR-003','PR-004'],'numbering')
    check(status['packages'][2]['status']=='USER_REPORTED_IN_PROGRESS_OTHER_CHAT' and not status['packages'][2]['artifact_received'],'PR003 overclaim')
    check(disposition['next_package']=='ZIP-005' and not status['automatic_other_chat_visibility'],'next scope')
    contract=read('contracts/INVENTORY_CONTRACT.json')
    check(not contract['new_native_endpoint'] and not contract['new_executor'] and not contract['new_metadata_owner'],'owner scope')
    examples=read('fixtures/CLI_RECEIPTS.json')
    schema=read('contracts/CLI_RECEIPT.schema.json')
    check(all(valid(v,schema) for v in examples['valid']),'valid receipt rejected')
    check(all(not valid(v,schema) for v in examples['invalid']),'invalid receipt accepted')
    budget=read('contracts/INVENTORY_BUDGET.example.json')
    budget_schema=read('contracts/INVENTORY_BUDGET.schema.json')
    check(valid(budget,budget_schema),'budget schema')
    check(not valid(budget|{'timeout_seconds':True},budget_schema) and not valid(budget|{'stage_max_bytes':0},budget_schema),'invalid budget accepted')
    check(budget['read_block_bytes']*budget['stdout_queue_blocks']<=1048576,'queue budget')
    check(budget['stderr_retained_bytes']<=budget['stderr_total_bytes'] and budget['timeout_seconds']>0,'lifecycle budget')
    for p in read('index.json')['read_order']+plan['read_order']:
        check((ROOT/p).is_file(),'missing read order '+p)
    parser=Links()
    parser.feed((ROOT/'INDEX.html').read_text())
    for p in parser.paths:
        check(not PurePosixPath(p).is_absolute() and '..' not in PurePosixPath(p).parts and (ROOT/p).is_file(),'offline link '+p)
    golden=stream_fixture()
    large=read('verification/LARGE_FIXTURE_GENERATION.json')
    check(large['entries']==160000 and large['stdout_bytes']>33554432 and large['above_legacy_32_mib'],'large fixture')
    check(not large['application_runtime_executed'],'fixture is not application proof')
    return {'status':'PASS','scope':'PR input integrity/traceability, receipt examples, generated Git fixture and fixture codec only',
            'manifest_files':len(names),'preserved_source_files':len(source['preserved_files']),
            'json_files':len(json_names),'preserved_tasks':160,'preserved_features':164,
            'build_tasks':6,'planned_build_minutes':60,'runtime_acceptance_cases':16,
            'runtime_cases_executed':False,'application_runtime_executed':False,
            'golden_entries':golden['entries'],'exhaustive_split_cuts':golden['exhaustive_two_block_cuts'],
            'malformed_streams_rejected':golden['malformed_streams_rejected'],
            'receipt_examples':len(examples['valid'])+len(examples['invalid']),
            'large_git_entries':large['entries'],'large_git_stdout_bytes':large['stdout_bytes'],
            'offline_links':len(parser.paths),'pr003_artifact_received':False}


if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
