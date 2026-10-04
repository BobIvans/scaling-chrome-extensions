"""PR007 input integrity/schema/labels only; no app imports or AST execution."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re

from verify_corpus import run as verify_corpus

ROOT=Path(__file__).resolve().parents[1]


def check(ok,reason):
    if not ok:
        raise ValueError(reason)


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid(value,schema):
    """Stdlib subset covering the constructs in the shipped schemas."""
    if 'oneOf' in schema and sum(valid(value,s) for s in schema['oneOf'])!=1:
        return False
    if 'const' in schema and value!=schema['const']:
        return False
    if 'enum' in schema and value not in schema['enum']:
        return False
    if 'type' in schema:
        types=schema['type'] if isinstance(schema['type'],list) else [schema['type']]
        kinds={'object':isinstance(value,dict),'string':isinstance(value,str),'integer':type(value) is int,
               'null':value is None,'boolean':type(value) is bool,'array':isinstance(value,list)}
        if not any(kinds.get(t,False) for t in types):
            return False
    if isinstance(value,str):
        if 'pattern' in schema and re.search(schema['pattern'],value) is None:
            return False
        if len(value)<schema.get('minLength',0):
            return False
    if type(value) is int and (value<schema.get('minimum',value) or value>schema.get('maximum',value)):
        return False
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',len(value)):
            return False
        if 'items' in schema and not all(valid(v,schema['items']) for v in value):
            return False
        if schema.get('uniqueItems') and len({json.dumps(v,sort_keys=True,ensure_ascii=False) for v in value})!=len(value):
            return False
    if isinstance(value,dict):
        props=schema.get('properties',{})
        if not set(schema.get('required',[]))<=set(value):
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


def adapter_outcome(example,schema):
    facts=example['facts']
    if facts is None:
        return 'ELIGIBILITY_FACTS_UNAVAILABLE'
    if not valid(facts,schema):
        return 'FACTS_SCHEMA_INVALID'
    if any(facts[k]!=v for k,v in example['binding'].items()):
        return 'FACTS_BINDING_STALE'
    if facts['raw_capture']=='CORRUPT' or facts['raw_integrity']=='FAIL':
        return 'RAW_CAPTURE_CORRUPT'
    if facts['text_eligibility']=='UNKNOWN':
        return 'ELIGIBILITY_FACTS_UNKNOWN'
    if facts['text_eligibility']!='ELIGIBLE' or facts['format_kind'] not in {'UTF8_TEXT_CANDIDATE','EMPTY'}:
        return 'TEXT_INELIGIBLE'
    if facts['disposition']!='INDEXED' or facts['raw_capture']!='RECORDED' or facts['kind']!='blob' or facts['mode']=='120000':
        return 'RAW_BYTES_UNAVAILABLE'
    if not example['independent_reconstruction_pass']:
        return 'RAW_PROOF_REQUIRED'
    return 'ALLOW_SYNTAX_ONLY'


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
    check(len(names)==len(set(names))==manifest['count'] and set(names)==actual,'manifest paths')
    for row in rows:
        path=PurePosixPath(row['path'])
        check(not path.is_absolute() and '..' not in path.parts and '\\' not in row['path'],'unsafe member')
        p=ROOT/row['path']
        check(not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'file hash '+row['path'])
    json_names=[n for n in names if n.endswith('.json')]
    for n in json_names:
        read(n)
    tasks=read('sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')['tasks']
    ids=[t['task_id'] for t in tasks]
    check(len(ids)==len(set(ids))==160,'task corpus')
    disp=read('plan/ROADMAP_DISPOSITION.json')
    check([t['source_task_id'] for t in disp['tasks']]==ids and all(not t['task_closed'] for t in disp['tasks']),'task retention/closure')
    for path,key,count in [('catalogs/FEATURE_DEFINITION_AUDIT.json','features',164),('goals/GOAL_REGISTER.json','goals',28),('audit/DECISION_REGISTER.json','decisions',24),('catalogs/MILESTONES_V5.json','milestones',10)]:
        check(len(read('sources/roadmap_v5/'+path)[key])==count,'registry '+path)
    selected=read('plan/SELECTED_SOURCE_TASKS.json')['tasks']
    check(selected==[t for t in tasks if t['task_id'] in ['LAYA4-005','LAYA4-006','LAYA4-007']],'source selected task mutation')
    plan=read('plan/PR_PLAN.json')
    check(plan['local_sequence']==7 and plan['parser_pin'] is None and not plan['parser_benchmark_run'],'package/proposed pin')
    check(not plan['whole_task_closed'] and not plan['application_code_changed'] and not plan['current_head_verified'],'implementation overclaim')
    check(plan['pr003_input_received'] and plan['pr005_artifact_received'] and plan['pr006_artifact_received'],'input receipts')
    check(len(plan['tasks'])==6 and sum(t['budget_minutes'] for t in plan['tasks'])==60,'hour plan')
    seen=set()
    for t in plan['tasks']:
        check(set(t['depends_on'])<=seen and set(t['source_task_ids'])<=set(ids),'plan DAG')
        seen.add(t['id'])
    cases=read('plan/ACCEPTANCE_CASES.json')['cases']
    receipt=read('receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    check(len(cases)==16 and [c['criterion_id'] for c in cases]==[c['criterion_id'] for c in receipt['criterion_results']],'case mapping')
    check(all(c['outcome']=='NOT_RUN' for c in cases+receipt['criterion_results']),'false runtime PASS')
    check(receipt['state']=='NOT_IMPLEMENTED' and not receipt['whole_task_closed'],'implementation status')
    check(receipt['corpus_metrics']['precision'] is None and receipt['corpus_metrics']['recall'] is None,'false qualification metrics')
    prov=read('provenance/SOURCES.json')
    for row in prov['preserved_files']:
        p=ROOT/row['package_path']
        check(p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'preserved bytes '+row['package_path'])
    source_map=read('provenance/ARCHIVED_SCE_SOURCE_MAP.json')
    for row in source_map['sources']:
        p=ROOT/'sources/archived_sce'/row['path']
        raw=p.read_bytes()
        check(sha(p)==row['sha256'] and len(raw)==row['bytes'],'source traceability')
        check(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_oid'],'Git source object proof')
    status=read('coordination/PR_PACKAGE_STATUS.json')
    check([p['package'] for p in status['packages']]==[f'PR-{i:03d}' for i in range(1,8)],'numbering')
    check(not status['automatic_other_chat_visibility'] and all(not p['implementation_verified'] for p in status['packages']),'coordination overclaim')
    check(disp['next_package']=='ZIP-008','next numbering')
    contract=read('contracts/RELATIONS_CONTRACT.json')
    check(not contract['raw_chunks_changed'] and not contract['default_capture_changed'] and not contract['new_native_endpoint'] and not contract['new_runtime'],'scope/owner')
    rows=[json.loads(x) for x in (ROOT/'fixtures/derived_golden/RELATIONS.jsonl').read_text().splitlines()]
    schema=read('contracts/RELATION.schema.json')
    check(all(valid(r,schema) for r in rows),'relation schema')
    examples=read('fixtures/RELATION_SCHEMA_EXAMPLES.json')
    check(all(valid(r,schema) for r in examples['valid']) and all(not valid(r,schema) for r in examples['invalid']),'relation examples')
    file_rows=[json.loads(x) for x in (ROOT/'fixtures/derived_golden/JS_ANALYSIS.jsonl').read_text().splitlines()]
    file_schema=read('contracts/JS_ANALYSIS.schema.json')
    check(len(file_rows)==200 and all(valid(r,file_schema) for r in file_rows),'analysis schema/count')
    budget=read('contracts/ANALYSIS_BUDGET.example.json')
    budget_schema=read('contracts/ANALYSIS_BUDGET.schema.json')
    check(valid(budget,budget_schema) and not valid(budget|{'file_bytes':True},budget_schema),'budget schema')
    check(budget['stderr_retained_bytes']<=budget['stderr_total_bytes'],'stderr relational budget')
    check(((budget['file_bytes']+2)//3)*4+4096<=budget['parser_input_frame_bytes'],'input frame budget')
    map5=read('contracts/PR005_ADAPTER_MAP.json')
    schema5=read('previous/PR_005_ENTRY_FACTS.schema.json')
    check(map5['facts_schema_sha256']==sha(ROOT/'previous/PR_005_ENTRY_FACTS.schema.json'),'eligibility schema pin')
    check(map5['classifier_version']=='utf8-controls-strict-lfs3.v1','classifier pin')
    adapter_cases=read('fixtures/PR005_ADAPTER_EXAMPLES.json')['examples']
    check(len(adapter_cases)==13 and all(adapter_outcome(e,schema5)==e['expected'] for e in adapter_cases),'PR005 adapter cases')
    map6=read('contracts/PR006_ADAPTER_MAP.json')
    contract6=read('previous/PR_006_GROUP_PLANNER_CONTRACT.json')
    check(map6['existing_topology_relations']==contract6['topology']['accepted_relations'],'PR006 policy drift')
    check(not map6['existing_consumer_accepts_js'] and not map6['overwrite_existing_relations'],'JS auto-integration overclaim')
    for p in read('index.json')['read_order']+plan['read_order']:
        check((ROOT/p).is_file(),'read-order link')
    parser=Links();parser.feed((ROOT/'INDEX.html').read_text())
    for p in parser.paths:
        check(not PurePosixPath(p).is_absolute() and '..' not in PurePosixPath(p).parts and (ROOT/p).is_file(),'offline link')
    corpus=verify_corpus()
    return {'status':'PASS','scope':'Input integrity, byte-preserved sources/contracts, synthetic labels/identity/schema/adapters only',
            'manifest_files':len(names),'preserved_source_files':len(prov['preserved_files']),'json_files':len(json_names),
            'preserved_tasks':160,'preserved_features':164,'build_tasks':6,'planned_build_minutes':60,
            'runtime_acceptance_cases':16,'runtime_cases_executed':False,'application_runtime_executed':False,
            'ast_adapter_executed':False,'parser_dependency_installed':False,'labelled_cases':200,'case_families':20,
            'labelled_relations':corpus['references'],'local_static_labels':corpus['local_static_labels'],
            'unresolved_labels':corpus['unresolved_labels'],'malformed_label_mutations_rejected':corpus['malformed_mutations_rejected'],
            'pr005_adapter_examples':len(adapter_cases),'pr005_input_received':True,'pr006_input_received':True,
            'existing_pr006_accepts_js':False,'relation_schema_examples':len(examples['valid'])+len(examples['invalid']),
            'offline_links':len(parser.paths),'qualified_precision':None,'qualified_recall':None,'independent_holdout':False}


if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
