"""Verify a planning ZIP; never mark future application acceptance as passed."""
from pathlib import Path
import hashlib, json, shutil, sys, tempfile
from verify_fidelity import compact, verify_fixture


def need(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def mutate_ledger(root,cid,fn):
    f=root/'fixtures/import_fidelity_golden'
    cases=load(f/'CASES.json');case=next(c for c in cases['cases'] if c['case_id']==cid)
    p=f/case['ledger_path'];obj=load(p);fn(obj);save(p,obj)
    captures=[json.loads(line) for line in (f/'CAPTURES.jsonl').read_text().splitlines()]
    next(c for c in captures if c['case_id']==cid)['payload_sha256']=hashlib.sha256(compact(obj)).hexdigest()
    (f/'CAPTURES.jsonl').write_bytes(b''.join(compact(c)+b'\n' for c in captures))


def node_ref(payload,node):return next(r for r in payload['nodes'] if r['node_id']==node)


def check_negatives(root):
    def raw_tamper(r):
        p=r/'fixtures/import_fidelity_golden/raw/F01.json';p.write_bytes(p.read_bytes()+b' ')
    def off_scope(r):
        p=r/'fixtures/import_fidelity_golden/CASES.json';v=load(p)
        next(c for c in v['cases'] if c['case_id']=='F07')['out_of_scope_unchanged']=['conv-b'];save(p,v)
    def source_identity(r):
        f=r/'fixtures/import_fidelity_golden';caps=[json.loads(x) for x in (f/'CAPTURES.jsonl').read_text().splitlines()]
        next(c for c in caps if c['case_id']=='F01')['source_version_id']='f'*64
        (f/'CAPTURES.jsonl').write_bytes(b''.join(compact(c)+b'\n' for c in caps))
        mutate_ledger(r,'F01',lambda v:v.update(source_version_id='f'*64))
    def unretain(r):
        f=r/'fixtures/import_fidelity_golden';caps=[json.loads(x) for x in (f/'CAPTURES.jsonl').read_text().splitlines()]
        next(c for c in caps if c['case_id']=='F11')['original_retained']=False
        (f/'CAPTURES.jsonl').write_bytes(b''.join(compact(c)+b'\n' for c in caps))
    mutations=[
      ('duplicate-node',lambda r:mutate_ledger(r,'F01',lambda v:v['nodes'].append(v['nodes'][0].copy()))),
      ('lost-alternative-branch',lambda r:mutate_ledger(r,'F01',lambda v:v.update(nodes=[n for n in v['nodes'] if n['node_id']!='a2']))),
      ('lost-structural-node',lambda r:mutate_ledger(r,'F01',lambda v:v.update(nodes=[n for n in v['nodes'] if n['node_id']!='root']))),
      ('pointer-is-payload-claim',lambda r:mutate_ledger(r,'F01',lambda v:v['attachments'][0].update(bytes_present=True))),
      ('invented-raw-byte-range',lambda r:mutate_ledger(r,'F01',lambda v:node_ref(v,'u1').update(exact_raw_byte_range=[0,12]))),
      ('false-remote-completeness',lambda r:mutate_ledger(r,'F01',lambda v:v.update(remote_completeness='COMPLETE'))),
      ('wrong-message-time',lambda r:mutate_ledger(r,'F01',lambda v:node_ref(v,'u1').update(message_create_time=1))),
      ('lost-topology-gap',lambda r:mutate_ledger(r,'F08',lambda v:v['topology_gaps'].pop())),
      ('selected-scope-mislabel',off_scope),
      ('original-byte-tamper',raw_tamper),
      ('consistent-wrong-source-id',source_identity),
      ('same-extraction-different-payload',lambda r:mutate_ledger(r,'F02',lambda v:v.update(extra_unstable_field='bad'))),
      ('captured-error-original-lost',unretain),
      ('wrong-legacy-item-id',lambda r:mutate_ledger(r,'F06',lambda v:node_ref(v,'u1')['legacy_text_ref'].update(item_id='a'*64))),
    ]
    rejected=[]
    with tempfile.TemporaryDirectory(prefix='pr009-mutants-') as tmp:
        for i,(name,fn) in enumerate(mutations):
            dest=Path(tmp)/str(i)
            shutil.copytree(root/'fixtures',dest/'fixtures');shutil.copytree(root/'contracts',dest/'contracts')
            shutil.copyfile(root/'INDEX.html',dest/'INDEX.html')
            # Root links are verified only after semantics; create referenced outer files.
            for rel in ['EXECUTE_THIS_PR_RU.txt','01_PR_009_IMPLEMENTATION_RU.md','03_PARALLEL_CHAT_NAVIGATION_RU.md',
                        'plan/ACCEPTANCE_CASES.json','sources/roadmap_v5/catalogs/ALL_TASKS_V5.json']:
                p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/rel,p)
            fn(dest)
            try:verify_fixture(dest)
            except (ValueError,KeyError,AssertionError) as e:rejected.append({'name':name,'status':'REJECTED','reason':str(e)})
            else:raise ValueError('mutation accepted: '+name)
    return rejected


def verify(root):
    root=Path(root)
    manifest=load(root/'MANIFEST.json')
    need(manifest['self_record']=='EXCLUDED_EXPLICITLY','self manifest')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=root/'MANIFEST.json'}
    declared={row['path'] for row in manifest['files']}
    need(actual==declared and len(declared)==len(manifest['files']),'outer file coverage')
    for row in manifest['files']:
        p=root/row['path'];need(p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'outer hash '+row['path'])
    for p in root.rglob('*.json'):
        if 'raw' not in p.parts:load(p)
    prov=load(root/'provenance/SOURCES.json')
    for row in prov['preserved_source_members']:
        p=root/row['package_path'];need(sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],'source preservation')
    cat=load(root/'sources/roadmap_v5/catalogs/ALL_TASKS_V5.json');dis=load(root/'plan/ROADMAP_DISPOSITION.json')
    source_ids={t['task_id'] for t in cat['tasks']}
    need(cat['count']==len(source_ids)==160,'160 tasks')
    need({t['task_id'] for t in dis['tasks']}==source_ids and len(dis['tasks'])==160,'disposition coverage')
    need(all(not t['broad_task_closed'] and t['implementation_status']=='NOT_IMPLEMENTED_BY_PACKAGE' for t in dis['tasks']),'false completion')
    plan=load(root/'plan/PR_PLAN.json');seen=set()
    need(plan['estimate_minutes']==sum(t['budget_minutes'] for t in plan['tasks'])==60,'one hour plan')
    need(len(plan['tasks'])==6 and plan['application_code_changed'] is False and plan['actual_base_sha'] is None,'plan status')
    for t in plan['tasks']:
        need(set(t['depends_on']).issubset(seen) and t['status']=='NOT_STARTED','task dependency');seen.add(t['id'])
    cases=load(root/'plan/ACCEPTANCE_CASES.json')['cases']
    need(len(cases)==20 and len({c['id'] for c in cases})==20 and all(c['status']=='NOT_RUN' and not c['evidence'] for c in cases),'runtime tests claim')
    contract=load(root/'contracts/IMPORT_FIDELITY_CONTRACT.json')
    need(contract['pr008_exact_contract_observed'] is False and not contract['new_database'] and not contract['new_native_command'],'parallel scope')
    need(contract['attachment_payloads_present'] is False and contract['remote_branch_completeness']=='UNKNOWN','scope truth')
    fixture=verify_fixture(root)
    negative=check_negatives(root)
    return {'status':'PASS','scope':'PACKAGE_SYNTHETIC_DATA_AND_DRAFT_SQL_ONLY',
            'preserved_source_files':len(prov['preserved_source_members']),'source_tasks':160,
            'six_step_minutes':60,'runtime_acceptance_cases':20,'fixture':fixture,
            'negative_mutations':negative,'application_tests':'NOT_RUN','current_head_verified':False,
            'github_pr':None,'windows_device':'NOT_RUN','remote_completeness':'UNKNOWN'}


if __name__=='__main__':
    print(json.dumps(verify(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
