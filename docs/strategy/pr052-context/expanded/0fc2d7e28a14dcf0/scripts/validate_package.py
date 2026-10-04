from pathlib import Path
import json,hashlib,re,sys,copy
root=Path(__file__).resolve().parents[1]
def read(p):return json.loads((root/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(schema,v,path='$'):
    t=schema.get('type')
    matches={'object':isinstance(v,dict),'array':isinstance(v,list),'string':isinstance(v,str),'integer':type(v) is int,'boolean':type(v) is bool}
    if t and not matches[t]:raise ValueError(path+': type '+str(t))
    if 'enum' in schema and v not in schema['enum']:raise ValueError(path+': enum')
    if t=='object':
        for k in schema.get('required',[]):
            if k not in v:raise ValueError(path+': missing '+k)
        ps=schema.get('properties',{})
        if schema.get('additionalProperties') is False and set(v)-set(ps):raise ValueError(path+': extra keys')
        for k,x in v.items():
            if k in ps:check(ps[k],x,path+'.'+k)
    if t=='array':
        if len(v)<schema.get('minItems',0):raise ValueError(path+': minItems')
        for i,x in enumerate(v):check(schema['items'],x,path+f'[{i}]')
    if t=='string':
        if len(v)<schema.get('minLength',0):raise ValueError(path+': minLength')
        if 'pattern' in schema and re.search(schema['pattern'],v) is None:raise ValueError(path+': pattern')
    if t=='integer' and not schema.get('minimum',v)<=v<=schema.get('maximum',v):raise ValueError(path+': bounds')

def main():
    manifest=read('MANIFEST.json'); paths=[e['path'] for e in manifest['files']]
    assert len(paths)==len(set(paths))
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert actual-set(manifest['excluded_self_referential_paths'])==set(paths),'manifest completeness'
    for e in manifest['files']:
        p=root/e['path'];assert p.is_file() and p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path']
    for e in read('provenance/SOURCE_PRESERVATION.json'):assert sha(root/e['package_path'])==e['original_sha256']
    plan=read('PR_PLAN.json');selected=read('coverage/COUNTS.json');cases=read('acceptance/ACCEPTANCE_CASES.json');cov=read('coverage/CRITERION_COVERAGE.json')
    originals={
      'task':('sources/selected/TASKS.json','task_id','acceptance_criteria'),
      'feature':('sources/selected/FEATURES.json','id','acceptance'),
      'decision':('sources/selected/DECISIONS.json','id','decision_acceptance'),
      'goal':('sources/selected/GOALS.json','goal_id','acceptance_criteria'),
      'workstream':('WORKSTREAMS.json','workstream_id','acceptance')}
    expected={}
    for kind,(p,idkey,ac) in originals.items():
        for r in read(p):
            for i,x in enumerate(r[ac],1):expected[(kind,f'{r[idkey]}-AC{i}')]=x
    assert len(cov)==len(expected)==selected['individual_original_criteria']
    assert len({c['criterion_id'] for c in cov})==len(cov)
    caseids={c['case_id'] for c in cases}
    for c in cov:
        assert expected[(c['source_kind'],c['criterion_id'])]==c['original_criterion_exact']
        assert c['acceptance_case_ids'] and set(c['acceptance_case_ids'])<=caseids
        assert c['status']=='OPEN_NOT_IMPLEMENTED'
    for f in read('plan/FUNCTIONS_TO_IMPLEMENT.json'):assert set(f['acceptance_case_ids'])<=caseids
    assert all(c['status']=='NOT_RUN' for c in cases)
    idx=read('fixtures/raw/INDEX.json')
    for e in idx:assert sha(root/e['artifact_path'])==e['sha256']
    scale=read('fixtures/scale/1001_parts.json');data=(root/scale['source_path']).read_bytes();offset=0
    for part in scale['parts']:
        assert part['start']==offset and part['end']>offset
        assert hashlib.sha256(data[part['start']:part['end']]).hexdigest()==part['sha256'];offset=part['end']
    assert len(scale['parts'])==1001 and offset==len(data)==scale['total_bytes'] and sha(root/scale['source_path'])==scale['full_sha256']
    schema_count=0;negative_count=0
    for p in (root/'contracts').glob('*.schema.json'):
        s=json.loads(p.read_text());name=p.name.removesuffix('.schema.json');v=read('fixtures/contracts/'+name+'.json');check(s,v)
        bad=copy.deepcopy(v);bad['__unexpected']='deny'
        try:check(s,bad)
        except ValueError:negative_count+=1
        else:raise AssertionError('unknown field accepted '+name)
        schema_count+=1
    for link in read('index.json')['reading_order']:assert (root/link).is_file(),link
    tasks=read('sources/master_v5/catalogs/ALL_TASKS_V5.json')['tasks'];feats=read('sources/master_v5/catalogs/PRODUCT_FEATURES.json')['features']
    assert len(tasks)==160 and len(feats)==164
    allids={x['task_id'] for x in tasks}
    assert all(set(x['dependencies'])<=allids for x in tasks)
    print(json.dumps({'status':'PASS','scope':'PACKAGE_STRUCTURAL_ONLY','manifest_files':len(paths),'source_files_byte_preserved':len(read('provenance/SOURCE_PRESERVATION.json')),'individual_criteria_preserved':len(cov),'schema_examples_valid':schema_count,'unexpected_field_examples_rejected':negative_count,'scale_fixture_parts_verified':1001,'backlog_tasks':len(tasks),'backlog_features':len(feats),'runtime_tests':'NOT_RUN','device_tests':'NOT_RUN'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
