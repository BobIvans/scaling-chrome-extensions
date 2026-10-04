#!/usr/bin/env python3
"""Verify package bytes, source criterion preservation and internal links; no runtime qualification."""
from pathlib import Path, PurePosixPath
import hashlib, json, sys, zipfile

def load(root, p): return json.loads((root/p).read_text(encoding='utf-8'))
def verify(root):
    m=load(root,'MANIFEST.json');errors=[]
    actual={str(p.relative_to(root)).replace('\\','/') for p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.json'}
    if actual != {x['path'] for x in m['files']}:errors.append('manifest file set differs')
    for item in m['files']:
        path=PurePosixPath(item['path'])
        if path.is_absolute() or '..' in path.parts: errors.append('unsafe manifest path');continue
        p=root/item['path']
        if not p.is_file(): errors.append('missing '+item['path']);continue
        raw=p.read_bytes()
        if len(raw)!=item['size_bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']: errors.append('digest '+item['path'])
        if p.suffix=='.json':
            try:json.loads(raw)
            except Exception:errors.append('invalid JSON '+item['path'])
    ledger=load(root,'coverage/CRITERION_LEDGER.json')['criteria']
    parents=load(root,'coverage/PARENT_RECORDS.json')['records']
    if len({r['criterion_id'] for r in ledger})!=len(ledger):errors.append('duplicate criterion IDs')
    specs=[('TASK','source/master/strategy_v5/catalogs/ALL_TASKS_V5.json','tasks','task_id','acceptance_criteria',160),
      ('FEATURE','source/master/catalogs/PRODUCT_FEATURES.json','features','id','acceptance',164),
      ('GOAL','source/master/strategy_v5/goals/GOAL_REGISTER.json','goals','goal_id','acceptance_criteria',28),
      ('DECISION','source/master/strategy_v5/audit/DECISION_REGISTER.json','decisions','id','decision_acceptance',24)]
    for kind,path,key,idkey,ackey,count in specs:
        rows=load(root,path)[key]
        if len(rows)!=count:errors.append(kind+' source count')
        expected={(r[idkey],n,t) for r in rows for n,t in enumerate(r.get(ackey,[]),1)}
        found={(r['record_id'],r['ordinal'],r['exact_text']) for r in ledger if r['record_kind']==kind}
        if expected!=found:errors.append(kind+' exact criteria mismatch')
        if {r[idkey] for r in rows}!={r['record_id'] for r in parents if r['record_kind']==kind}:errors.append(kind+' lost parent IDs')
    ws=[]
    for n in [20,21]:ws+=load(root,f'source/next_roadmap/briefs/PR_{n:03}.json')['workstreams']
    expected={(r['workstream_id'],n,t) for r in ws for n,t in enumerate(r['acceptance'],1)}
    found={(r['record_id'],r['ordinal'],r['exact_text']) for r in ledger if r['record_kind']=='WORKSTREAM'}
    if expected!=found:errors.append('workstream criteria mismatch')
    for r in ledger:
        if hashlib.sha256(r['exact_text'].encode()).hexdigest()!=r['text_sha256']:errors.append('criterion text hash')
        if r['status']!='OPEN' or r['evidence_refs']:errors.append('unexpected runtime claim')
        if r['source_owner']=='UNMAPPED':errors.append('unmapped owner')
    functions=load(root,'implementation/FUNCTION_CATALOG.json')['functions'];fun_ids={r['function_id'] for r in functions}
    cases=load(root,'qualification/TEST_CASES.json')['cases'];case_ids={r['case_id'] for r in cases}
    if len(fun_ids)!=len(functions) or len(case_ids)!=len(cases):errors.append('duplicate function/test ID')
    ws_ids={r['workstream_id'] for r in ws}
    for link in load(root,'coverage/WORKSTREAM_LINKS.json')['links']:
        if link['workstream_id'] not in ws_ids:errors.append('unknown WS link')
        if not set(link['function_ids'])<=fun_ids or not set(link['test_case_ids'])<=case_ids:errors.append('broken WS links')
    for p in (root/'workflows').glob('*.json'):
        w=json.loads(p.read_text());steps={r['step_id'] for r in w['steps']}
        for s in w['steps']:
            if s['semantic_function_id'] not in fun_ids or not set(s['depends_on'])<=steps:errors.append('broken workflow links')
            if s['registered_handler_ref'] is not None:errors.append('unexpected bound workflow')
    for item in load(root,'source/INPUTS.json'):
        if item['embedded_path']:
            p=root/item['embedded_path']
            if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:errors.append('original ZIP mismatch')
            with zipfile.ZipFile(p) as z:
                if z.testzip():errors.append('embedded ZIP CRC failure')
    return {'package_integrity':not errors,'errors':errors,'source_record_counts':{'tasks':160,'features':164,'goals':28,'decisions':24,'workstreams':8},
            'criterion_count':len(ledger),'proposed_function_count':len(functions),'planned_test_cases':len(cases),
            'runtime_qualification':'NOT_RUN','scope':'PACKAGE_BYTES_AND_SOURCE_CRITERIA_ONLY'}

if __name__=='__main__':
    result=verify(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['package_integrity'] else 1)
