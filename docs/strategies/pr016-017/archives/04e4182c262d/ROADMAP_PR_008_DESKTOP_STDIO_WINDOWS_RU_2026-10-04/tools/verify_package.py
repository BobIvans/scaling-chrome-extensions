"""Verify PR008 design bytes and fixture coherence, not desktop implementation.

Standard-library only. Schemas are parsed/shape checked; no general JSON Schema
validation claim. Real native/client/UI/Windows tests remain separate gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def check(condition,code):
    if not condition: raise ValueError(code)


def sha_file(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def load(root,name):
    return json.loads((root/name).read_text(encoding='utf-8'))


def strict_json(raw):
    def pairs(values):
        d={}
        for k,v in values:
            if k in d:raise ValueError('DUPLICATE_JSON_KEY')
            d[k]=v
        return d
    def reject(value):raise ValueError('NONFINITE_JSON')
    return json.loads(raw.decode('utf-8','strict'),object_pairs_hook=pairs,parse_constant=reject)


def verify(root):
    root=root.resolve()
    manifest=load(root,'MANIFEST.json')
    records=manifest['files'];names=[r['path'] for r in records]
    check(len(names)==len(set(names)),'DUPLICATE_MANIFEST_PATH')
    excluded={'MANIFEST.json','verification/PACKAGE_VALIDATION.json'}
    check(set(manifest['self_exclusions'])==excluded,'MANIFEST_EXCLUSIONS')
    for r in records:
        p=root/r['path']
        check(p.resolve().is_relative_to(root) and not p.is_symlink(),'UNSAFE_MANIFEST_PATH')
        check(p.is_file() and p.stat().st_size==r['bytes'],'MANIFEST_SIZE:'+r['path'])
        check(sha_file(p)==r['sha256'],'MANIFEST_HASH:'+r['path'])
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    check(actual-excluded==set(names),'MANIFEST_SET')
    json_count=0
    for p in root.rglob('*.json'):
        strict_json(p.read_bytes());json_count+=1
    for p in root.rglob('*.py'):
        # Parse/compile only. Never import or execute archived app/backend modules.
        compile(p.read_bytes(),str(p),'exec')
    prov=load(root,'provenance/SOURCES.json')
    for r in prov['source_copies']:
        check(sha_file(root/r['path'])==r['sha256'],'SOURCE_COPY:'+r['path'])
    tasks=load(root,'sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')['tasks']
    ids=[t['task_id'] for t in tasks]
    dispositions=load(root,'plan/ROADMAP_DISPOSITION.json')['tasks']
    check(len(ids)==len(set(ids))==160,'TASK_COUNT')
    check(set(ids)=={t['task_id'] for t in dispositions},'TASK_DISPOSITION_SET')
    check(all(t['closure_by_this_zip'] is False for t in dispositions),'FALSE_TASK_CLOSURE')
    check(load(root,'sources/roadmap_v5/catalogs/FEATURE_DEFINITION_AUDIT.json')['count']==164,'FEATURE_COUNT')
    registry=load(root,'coordination/PACKAGE_REGISTRY.json')['packages']
    check([r['package_id'] for r in registry]==[f'PR-{i:03d}' for i in range(1,9)],'REGISTRY_SEQUENCE')
    plan=load(root,'plan/PR_PLAN.json')
    check(sum(s['minutes'] for s in plan['steps'])==60 and len(plan['steps'])==6,'PLAN_BUDGET')
    cases=load(root,'plan/ACCEPTANCE_CASES.json')['cases']
    check(len(cases)==18 and all(c['status']=='NOT_RUN' for c in cases),'ACCEPTANCE_CLAIMS')
    receipt=load(root,'receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    check(receipt['implementation']=='NOT_RUN' and receipt['pr_url'] is None and receipt['windows_installed']=='NOT_RUN','FALSE_IMPLEMENTATION_CLAIM')
    check(load(root,'receipts/WINDOWS_DEVICE_TEMPLATE.json')['status']=='NOT_RUN','FALSE_WINDOWS_RECEIPT')
    transport=load(root,'contracts/DESKTOP_TRANSPORT_CONTRACT.json')
    check(transport['budgets']['global_repo_file_or_part_cap'] is None and transport['shell'] is False,'TRANSPORT_SCOPE')
    check(transport['desktop_allowlist']==['durable.info','durable.repo.list','durable.search','durable.context'],'READ_ALLOWLIST')
    for n in ['DESKTOP_CONFIG.schema.json','NATIVE_DESKTOP_RESULT.schema.json']:
        schema=load(root,'contracts/'+n)
        check(schema['$schema']=='https://json-schema.org/draft/2020-12/schema','SCHEMA_DIALECT')
    replies=[load(root,'fixtures/replies/'+n+'.json') for n in ['hello','search_utf8','selected_context','repo_list']]
    binding=replies[0]['adapter_context']
    largest=0
    for r in replies:
        check(r['schema']=='occ.desktop-stdio-result.v1' and r['ok'] is True and r['adapter_context']==binding,'VALID_REPLY_BINDING')
        check(r['result']['schema']=='occ.native-durable-result.v1' and r['result']['operation'] in transport['desktop_allowlist'],'VALID_REPLY_OPERATION')
        n=len(json.dumps(r,ensure_ascii=False,separators=(',',':')).encode())
        check(n<=192000,'VALID_REPLY_BUDGET');largest=max(largest,n)
    for r in load(root,'fixtures/REQUESTS.json')['requests']:
        check(len(json.dumps(r,ensure_ascii=False).encode())<=16000 and r['type'] in transport['desktop_allowlist'],'REQUEST_BUDGET_SCOPE')
    selected=replies[2]['result']['context']
    expected_sha=hashlib.sha256(json.dumps(selected['items'],ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
    check(selected['sha256']==expected_sha,'CONTEXT_OWNER_DIGEST')
    check(selected['bytes']==sum(len(i['text'].encode()) for i in selected['items']),'CONTEXT_BYTES')
    draft=load(root,'fixtures/draft/DRAFT_METADATA.json')
    raw=(root/'fixtures/draft/TASK_DRAFT.txt').read_bytes()
    check(hashlib.sha256(raw).hexdigest()==draft['file_sha256'] and len(raw)==draft['file_bytes'],'DRAFT_FILE_HASH')
    check(draft['context_sha256']==selected['sha256'] and draft['source_ids']==[i['id'] for i in selected['items']],'DRAFT_SOURCE_BINDING')
    check(draft['canonical_task_id'] is None and draft['corpus_total'] is None and draft['scope']=='SELECTED_ITEMS','DRAFT_SCOPE')
    fault_rejections=0
    for n in ['invalid_utf8','duplicate_keys','trailing_json','nonfinite']:
        try:strict_json((root/'fixtures/replies'/(n+'.bin')).read_bytes())
        except (UnicodeError,ValueError):fault_rejections+=1
        else:raise ValueError('FAULT_FIXTURE_WAS_VALID:'+n)
    fence=load(root,'fixtures/UI_FENCE_CASES.json')
    for c in fence['cases']:
        # Expected-data coherence only, not the implementation's fence logic.
        check(c['expected']==('APPLY' if c['event']==fence['current'] else 'DISCARD'),'FENCE_FIXTURE_EXPECTATION')
    mismatch=load(root,'fixtures/replies/profile_changed.json')
    check(mismatch['adapter_context']['profile_digest']!=binding['profile_digest'],'PROFILE_CHANGE_FIXTURE')
    check(load(root,'fixtures/replies/protocol_mismatch.json')['adapter_context']['protocol']!=binding['protocol'],'PROTOCOL_FAULT_FIXTURE')
    hello=replies[0]['result']['info']
    check(hello['backend_build_status']=='UNKNOWN_BUNDLE' and binding['backend_bundle_sha256'] is None,'FAKE_BUILD_PROOF')
    for href in re.findall(r'href="([^"]+)"',(root/'INDEX.html').read_text()):
        check('://' not in href and not href.startswith('/') and (root/href).is_file(),'OFFLINE_LINK:'+href)
    return {'schema':'occ.pr008-package-validation.v1','status':'PASS','package_id':'PR-008',
        'manifest_payload_files':len(records),'source_copies':len(prov['source_copies']),'json_files_parsed':json_count,
        'schema_check':'JSON parse and declared dialect only; not full JSON Schema validation',
        'roadmap_tasks_preserved':160,'feature_definitions_preserved':164,'plan_steps':6,'acceptance_cases_defined':18,
        'valid_synthetic_replies':4,'largest_synthetic_reply_bytes':largest,'invalid_wire_specimens_rejected':fault_rejections,
        'ui_fence_expected_cases':len(fence['cases']),'draft_expected_bytes':len(raw),
        'proof_scope':'design hashes/source preservation/expected-data coherence only',
        'app_tests':'NOT_RUN','windows_installed':'NOT_RUN','github_merge':'NOT_PERFORMED'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path,nargs='?',default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();result=verify(args.root)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
