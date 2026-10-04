"""Verify PR002 input, metadata contracts and synthetic fixtures; no app imports."""
from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from verify_golden import run as verify_golden

ROOT = Path(__file__).resolve().parents[1]


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid(value, schema):
    # Standard-library subset covering all constructs in our request schema.
    if 'oneOf' in schema:
        return sum(valid(value,s) for s in schema['oneOf']) == 1
    if 'const' in schema and value != schema['const']:
        return False
    if 'type' in schema:
        t = schema['type']
        if not {'object':isinstance(value,dict), 'string':isinstance(value,str), 'integer':type(value) is int}.get(t,False):
            return False
    if isinstance(value,str) and 'pattern' in schema and re.search(schema['pattern'],value) is None:
        return False
    if type(value) is int and (value < schema.get('minimum',value) or value > schema.get('maximum',value)):
        return False
    if isinstance(value,dict):
        props = schema.get('properties',{})
        if not set(schema.get('required',[])) <= set(value):
            return False
        if schema.get('additionalProperties') is False and set(value)-set(props):
            return False
        if any(not valid(v,props[k]) for k,v in value.items() if k in props):
            return False
    return True


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self,tag,attrs):
        if tag=='a':
            self.paths += [v for k,v in attrs if k=='href']


def run():
    manifest = read('MANIFEST.json')
    names = [e['path'] for e in manifest['files']]
    check(len(names)==len(set(names)), 'duplicate manifest path')
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
    check(set(names)==actual, 'unlisted/missing package file')
    for item in manifest['files']:
        name = item['path']
        check(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and '\\' not in name, 'unsafe path')
        p = ROOT/name
        check(not p.is_symlink() and p.stat().st_size==item['bytes'] and sha(p)==item['sha256'], 'package hash: '+name)
    json_names = [n for n in names if n.endswith('.json')]
    for name in json_names:
        read(name)
    catalog = read('sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')['tasks']
    ids = [t.get('task_id',t.get('id')) for t in catalog]
    check(len(ids)==len(set(ids))==160, 'source task count')
    disposition = read('plan/ROADMAP_DISPOSITION.json')
    check(ids==[t['source_task_id'] for t in disposition['tasks']], 'lost/duplicated task')
    check(all(not t['task_closed'] for t in disposition['tasks']), 'task falsely closed')
    for path,key,count in [
        ('sources/roadmap_v5/catalogs/FEATURE_DEFINITION_AUDIT.json','features',164),
        ('sources/roadmap_v5/goals/GOAL_REGISTER.json','goals',28),
        ('sources/roadmap_v5/audit/DECISION_REGISTER.json','decisions',24),
        ('sources/roadmap_v5/catalogs/MILESTONES_V5.json','milestones',10),
    ]:
        check(len(read(path)[key])==count, 'registry count: '+path)
    plan = read('plan/PR_PLAN.json')
    check(not plan['application_code_changed'] and not plan['current_head_verified'] and not plan['previous_pr_implementation_verified'], 'false implementation claim')
    check(sum(t['budget_minutes'] for t in plan['tasks'])==60 and len(plan['tasks'])==6, 'task budget/count')
    seen = set()
    for t in plan['tasks']:
        check(set(t['depends_on']) <= seen and set(t['source_task_ids']) <= set(ids), 'build DAG/reference')
        seen.add(t['id'])
    acceptance = read('plan/ACCEPTANCE_CASES.json')['cases']
    receipt = read('receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    check(len(acceptance)==14, 'acceptance count')
    check([c['criterion_id'] for c in acceptance]==[c['criterion_id'] for c in receipt['criterion_results']], 'receipt criteria mismatch')
    check(all(c['outcome']=='NOT_RUN' for c in acceptance+receipt['criterion_results']), 'false runtime PASS')
    source = read('provenance/SOURCES.json')
    for item in source['preserved_files']:
        p = ROOT/item['package_path']
        check(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'], 'modified preserved source')
    api = read('fixtures/API_REQUESTS.json')
    schema = read('contracts/NATIVE_REQUEST.schema.json')
    check(all(valid(v,schema) for v in api['valid']), 'valid request rejected')
    check(all(not valid(v,schema) for v in api['invalid']), 'invalid request accepted')
    check(all(len(json.dumps(v,ensure_ascii=False).encode()) <= 16000 for v in api['valid']), 'example native input size')
    golden = verify_golden()
    entry_rows = [json.loads(l) for l in (ROOT/'fixtures/manifest_golden/REPO_MANIFEST.jsonl').read_text().splitlines()]
    part_rows = [json.loads(l) for l in (ROOT/'fixtures/manifest_golden/PARTS_INDEX.jsonl').read_text().splitlines()]
    max_frame = 0
    for action, rows, file_filter in [('ENTRIES',entry_rows,None),('PARTS',part_rows,None),('PARTS',[p for p in part_rows if p['file_ordinal']==4],4)]:
        for offset in range(0,len(rows),20):
            page = rows[offset:offset+20]
            payload = {'requestId':'f'*32, 'ok':True, 'durable':{'schema':'occ.native-durable-result.v1','operation':'durable.repo.manifest','manifest':{'batch_id':'a'*64,'scope':{'action':action,'fileOrdinal':file_filter},'total':len(rows),'rows':page,'nextOffset':offset+len(page) if offset+len(page)<len(rows) else None,'proof_scope':'RETURNED_ROWS_ONLY'}}}
            size = len(json.dumps(payload,ensure_ascii=False).encode())
            check(size<=32768, 'synthetic full frame budget')
            max_frame = max(max_frame,size)
    index = read('index.json')
    for path in index['read_order']+plan['read_order']:
        check((ROOT/path).is_file(), 'broken read path')
    parser = Links()
    parser.feed((ROOT/'INDEX.html').read_text())
    for path in parser.paths:
        check(not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and (ROOT/path).is_file(), 'broken offline link')
    return {'status':'PASS','scope':'PR input integrity, traceability, schema examples and synthetic golden data only',
            'manifest_files':len(names),'json_files':len(json_names),'preserved_source_files':len(source['preserved_files']),
            'preserved_tasks':160,'preserved_features':164,'build_tasks':6,'runtime_acceptance_cases':14,
            'runtime_cases_executed':False,'golden_entries':golden['entries'],'golden_parts':golden['parts'],
            'negative_mutations_rejected':golden['rejected_mutations'],'request_examples':len(api['valid'])+len(api['invalid']),
            'max_synthetic_native_frame_bytes':max_frame,'offline_links':len(parser.paths),'application_runtime_executed':False}


if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
