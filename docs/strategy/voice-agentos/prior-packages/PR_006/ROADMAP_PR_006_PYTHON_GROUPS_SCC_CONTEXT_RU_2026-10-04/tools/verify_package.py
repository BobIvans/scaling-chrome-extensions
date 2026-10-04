#!/usr/bin/env python3
"""PR006 implementation-input integrity and independent fixture QA only."""
import json
import sys
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from verify_grouping import verify, need, read, rows, digest, file_hash, HTMLLinks

ROOT=Path(__file__).resolve().parent.parent


def inventory(root):
    return {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def put(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def write_rows(path, data):
    path.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in data),encoding='utf-8')


def reseal(root):
    groups=read(root/'GROUPS.json')
    policy=read(root/'POLICY.json')
    groups['binding']['eligibility_digest']=file_hash(root/'SOURCE_ELIGIBILITY.jsonl')
    groups['binding']['analysis_digest']=file_hash(root/'ANALYSIS.jsonl')
    groups['binding']['policy_digest']=digest(policy)
    groups['grouping_batch_id']=digest(groups['binding'])
    for item in groups['outputs']:
        path=root/item['path']
        item['bytes'],item['sha256']=path.stat().st_size,file_hash(path)
    put(root/'GROUPS.json',groups)


def resign_segments(root, data):
    policy=read(root/'POLICY.json')
    batch=read(root/'BATCH.json')
    for gid in {s['group_id'] for s in data}:
        local=sorted((s for s in data if s['group_id']==gid),key=lambda x:x['ordinal'])
        for s in local:
            s['group_part_id']=digest({'schema':'occ.repo-group-part.v1','group_id':gid,
                'chunk_logical_ids':[r['logical_id'] for r in s['raw_refs']],'policy_digest':digest(policy)})
            s['raw_reference_bytes']=sum(r['bytes'] for r in s['raw_refs'])
        for n,s in enumerate(local):
            s['previous']=local[n-1]['group_part_id'] if n else None
            s['next']=local[n+1]['group_part_id'] if n+1<len(local) else None
            s['revision']=digest({'group_part_id':s['group_part_id'],'base_batch_id':batch['batch_id'],
                                 'raw_refs':s['raw_refs'],'previous':s['previous'],'next':s['next']})


def negative_mutations(source):
    outcomes=[]
    specs=[('duplicate-membership','MEMBERSHIP_DUPLICATE_OR_ORPHAN'),
           ('lost-primary-raw-ref','RAW_REFERENCE_SET'),('binary-as-text-code','WHOLE_SOURCE_ELIGIBILITY'),
           ('heuristic-as-topology','RELATION_TOPOLOGY_CLASS'),('wrong-segment-next','SEGMENT_CHAIN'),
           ('raw-reference-range-tamper','RAW_REFERENCE_BINDING'),('unstable-group-id','GROUP_ID'),
           ('lost-unresolved','UNRESOLVED_SET'),('broken-local-link','BROKEN_LINK'),
           ('raw-budget-overflow','RAW_SEGMENT_BUDGET'),('frame-budget-overflow','FRAME_SEGMENT_BUDGET'),
           ('source-byte-tamper','RAW_SOURCE_HASH')]
    with tempfile.TemporaryDirectory(prefix='pr006-golden-negative-') as tmp:
        for name,expected in specs:
            root=Path(tmp)/name
            shutil.copytree(source,root)
            if name=='duplicate-membership':
                p=root/'GROUP_MEMBERS.jsonl'; data=rows(p);data.append(dict(data[0]));write_rows(p,data)
            elif name=='lost-primary-raw-ref':
                p=root/'GROUP_PARTS.jsonl';data=rows(p)
                selected=next(s for s in data if len(s['raw_refs'])>1)
                selected['raw_refs'].pop()
                resign_segments(root,data);write_rows(p,data)
            elif name=='binary-as-text-code':
                p=root/'SOURCE_ELIGIBILITY.jsonl';data=rows(p)
                selected=next(x for x in data if x['path']=='binary_source.py')
                selected['text_exportable']=True;selected['code_analysis_eligible']=True;write_rows(p,data)
            elif name=='heuristic-as-topology':
                p=root/'RELATIONS.jsonl';data=rows(p)
                selected=next(x for x in data if x['relation_kind']=='HEURISTIC_TEST_CANDIDATE')
                selected['topology']=True
                selected['relation_id']=digest({k:v for k,v in selected.items() if k!='relation_id'})
                write_rows(p,data)
            elif name=='wrong-segment-next':
                p=root/'GROUP_PARTS.jsonl';data=rows(p)
                selected=next(s for s in data if s['next'] is not None)
                selected['next']=None
                selected['revision']=digest({'group_part_id':selected['group_part_id'],
                    'base_batch_id':read(root/'BATCH.json')['batch_id'],'raw_refs':selected['raw_refs'],
                    'previous':selected['previous'],'next':selected['next']})
                write_rows(p,data)
            elif name=='raw-reference-range-tamper':
                p=root/'GROUP_PARTS.jsonl';data=rows(p)
                data[0]['raw_refs'][0]['source_start']+=1;write_rows(p,data)
            elif name=='unstable-group-id':
                heads=rows(root/'GROUP_HEADS.jsonl');old=heads[0]['group_id'];new='0'*64
                selected=heads[0];selected['group_id']=new
                selected['members_locator']['group_id']=new;selected['relations_locator']['group_id']=new
                members=rows(root/'GROUP_MEMBERS.jsonl')
                for m in members:
                    if m['group_id']==old:m['group_id']=new
                segments=rows(root/'GROUP_PARTS.jsonl')
                for s in segments:
                    if s['group_id']==old:
                        s['group_id']=new;s['related_locator']['group_id']=new
                resign_segments(root,segments)
                write_rows(root/'GROUP_HEADS.jsonl',sorted(heads,key=lambda x:x['group_id']))
                write_rows(root/'GROUP_MEMBERS.jsonl',members)
                write_rows(root/'GROUP_PARTS.jsonl',segments)
            elif name=='lost-unresolved':
                p=root/'UNRESOLVED.jsonl';data=rows(p);data.pop();write_rows(p,data)
            elif name=='broken-local-link':
                p=root/'INDEX.html';p.write_text(p.read_text().replace('href="GROUPS.json"','href="NO_SUCH_FILE.json"'),encoding='utf-8')
            elif name=='raw-budget-overflow':
                p=root/'POLICY.json';data=read(p);data['raw_reference_bytes_per_segment']=1;put(p,data)
            elif name=='frame-budget-overflow':
                p=root/'POLICY.json';data=read(p);data['reference_frame_bytes']=10;put(p,data)
            elif name=='source-byte-tamper':
                item=next(s for s in read(root/'EXPECTED_ORACLE.json')['raw_sources'] if s['bytes']>0)
                p=root/'raw'/Path(item['raw_path']).name;data=p.read_bytes();p.write_bytes(bytes([data[0]^1])+data[1:])
            reseal(root)
            try:
                verify(root)
            except (ValueError,OSError,KeyError,TypeError) as exc:
                need(str(exc)==expected,'UNEXPECTED_NEGATIVE:'+name+':'+str(exc))
                outcomes.append({'mutation':name,'expected':expected,'status':'REJECTED_AS_EXPECTED'})
            else:
                raise ValueError('CORRUPTION_ACCEPTED:'+name)
    return outcomes


def validate_policy(policy,schema):
    need(set(policy)==set(schema['required']), 'POLICY_FIELDS')
    for key,spec in schema['properties'].items():
        value=policy[key]
        if 'const' in spec:
            need(json.dumps(value)==json.dumps(spec['const']), 'POLICY_CONST:'+key)
        elif spec['type']=='integer':
            need(type(value) is int and value>=spec['minimum'], 'POLICY_INTEGER:'+key)
        elif spec['type']=='boolean':
            need(type(value) is bool,'POLICY_BOOLEAN:'+key)
        elif spec['type']=='array':
            need(isinstance(value,list) and len(value)>=spec['minItems'] and all(isinstance(v,str) and len(v)>=spec['items']['minLength'] for v in value),'POLICY_ARRAY:'+key)


def check():
    files=inventory(ROOT)
    manifest=read(ROOT/'MANIFEST.json')
    listed={x['path'] for x in manifest['files']}
    need(len(listed)==len(manifest['files']) and listed==files-{'MANIFEST.json'},'PACKAGE_FILE_SET')
    for item in manifest['files']:
        p=ROOT/item['path']
        need(p.stat().st_size==item['bytes'] and file_hash(p)==item['sha256'],'PACKAGE_HASH:'+item['path'])
    parsed=0
    for p in ROOT.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            if p.suffix=='.json':read(p);parsed+=1
            elif p.suffix=='.jsonl':rows(p);parsed+=1
    provenance=read(ROOT/'provenance/SOURCES.json')
    for item in provenance['preserved_source_members']:
        p=ROOT/item['package_path']
        need(p.stat().st_size==item['bytes'] and file_hash(p)==item['sha256'],'PRESERVATION_HASH')
    source_tasks=read(ROOT/'sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')['tasks']
    dispositions=read(ROOT/'plan/ROADMAP_DISPOSITION.json')['tasks']
    need(len(source_tasks)==len(dispositions)==160 and {x['task_id'] for x in source_tasks}=={x['task_id'] for x in dispositions},'TASK_COVERAGE')
    for name,field,count in [('catalogs/FEATURE_DEFINITION_AUDIT.json','features',164),('goals/GOAL_REGISTER.json','goals',28),
                             ('audit/DECISION_REGISTER.json','decisions',24),('catalogs/MILESTONES_V5.json','milestones',10)]:
        data=read(ROOT/'sources/roadmap_v5'/name)
        need(data['count']==len(data[field])==count,'CATALOG_COUNT')
    plan=read(ROOT/'plan/PR_PLAN.json')
    need(len(plan['tasks'])==6 and sum(t['budget_minutes'] for t in plan['tasks'])==60,'PLAN_TIME')
    seen=set()
    for task in plan['tasks']:
        need(set(task['depends_on'])<=seen and task['status']=='NOT_STARTED','PLAN_DAG_STATE')
        seen.add(task['id'])
    need(plan['current_head_verified'] is False and plan['application_code_changed'] is False
         and plan['pr005_exact_schema_observed'] is False and plan['github_pr_url'] is None,'UNOBSERVED_CLAIM')
    acceptance=read(ROOT/'plan/ACCEPTANCE_CASES.json')
    result=read(ROOT/'receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    need(acceptance['count']==len(acceptance['cases'])==len(result['cases'])==18,'CASE_COUNT')
    need(all(c['status']=='NOT_RUN' for c in acceptance['cases']+result['cases']),'FALSE_RUNTIME_PASS')
    need({c['id'] for c in acceptance['cases']}=={c['id'] for c in result['cases']},'CASE_TEMPLATE_IDS')
    adapter=read(ROOT/'contracts/PR005_ADAPTER_MAP_REQUIRED.json')
    need(adapter['pr005_exact_schema_observed'] is False and adapter['actual_schema'] is None
         and all(v['actual_fields'] is None for v in adapter['required_semantics']),'GUESSED_PR005_SCHEMA')
    routing=read(ROOT/'plan/CHAT_ROUTING.json')
    need(routing['is_automatic_sync'] is False and len(routing['entries'])==6,'CHAT_ROUTING')
    policy=read(ROOT/'contracts/GROUP_POLICY.example.json')
    schema=read(ROOT/'contracts/GROUP_POLICY.schema.json')
    validate_policy(policy,schema)
    need(policy==read(ROOT/'fixtures/grouping_golden/POLICY.json'),'FIXTURE_POLICY')
    parser=HTMLLinks();parser.feed((ROOT/'INDEX.html').read_text());parser.close()
    for link in parser.links:
        url=urlsplit(link)
        need(not url.scheme and not url.netloc and (ROOT/url.path).is_file(),'PACKAGE_LINK')
    proof=verify(ROOT/'fixtures/grouping_golden')
    need(proof['entry_count']==70 and proof['raw_part_count']==106 and proof['cycle_segments']==40,'GOLDEN_COUNTS')
    negatives=negative_mutations(ROOT/'fixtures/grouping_golden')
    return {'status':'PASS','scope':'PACKAGE_AND_SYNTHETIC_GROUP_DATA_ONLY','package_files':len(files),
            'json_jsonl_files_parsed':parsed,'preserved_files_verified':len(provenance['preserved_source_members']),
            'source_tasks_preserved':160,'plan_steps':6,'estimated_minutes':60,'runtime_cases':18,'runtime_cases_execution':'NOT_RUN',
            'pr005_exact_schema':'NOT_OBSERVED','policy_validation':'STRICT_STRUCTURAL_CHECK_PASS',
            'fixture':proof,'negative_mutations':negatives,'application_code_changed':False,
            'current_head_verified':False,'github_pr_created':False,'remote_ci':'NOT_RUN','windows':'NOT_RUN'}


if __name__=='__main__':
    try:
        print(json.dumps(check(),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'FAIL','reason':str(exc)},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)
