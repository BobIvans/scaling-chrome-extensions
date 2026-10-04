import json,hashlib,pathlib,sys,html.parser,urllib.parse,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads((root/p).read_text(encoding='utf8'))
def digest(data):return hashlib.sha256(data).hexdigest()
checks=[]
def check(name,cond):
 if not cond:raise AssertionError(name)
 checks.append(name)
manifest=read('MANIFEST.json')
for row in manifest['files']:
 p=root/row['path'];check('hash:'+row['path'],p.is_file() and p.stat().st_size==row['size'] and digest(p.read_bytes())==row['sha256'])
actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
check('all-files-manifested',actual=={r['path'] for r in manifest['files']})
plan=read('plan/PR_PLAN.json');check('one-combined-pr',plan['target_code_pr_count']==1 and set(plan['aliases'])=={'ROADMAP-PR-010','ROADMAP-PR-011'})
ws=read('plan/WORKSTREAMS.json');check('six-workstreams',set(w['workstream_id'] for w in ws)=={'WS-001','WS-007','WS-008','WS-012','WS-004','WS-005'})
for key,field in [('source_task_ids','task_ids'),('feature_ids','feature_ids'),('goal_ids','goal_ids'),('decision_ids','decision_ids')]:
 check('original-scope-union:'+key,set(x for w in ws for x in w[key])==set(plan[field]))
coverage=read('coverage/CRITERION_COVERAGE.json');cases=read('acceptance/ACCEPTANCE_CASES.json');ids={c['case_id'] for c in cases}
check('unique-criterion-ids',len(coverage)==len({c['criterion_id'] for c in coverage}))
check('unique-case-ids',len(cases)==len(ids))
expected=[]
canonical_sources={
 'TASKS':('sources/roadmap_010_021/source_master/strategy_v5/catalogs/ALL_TASKS_V5.json','tasks','task_id'),
 'FEATURE_ORIGINAL_CARDS':('sources/PRODUCT_FEATURES_ALL_164.json','features','id'),
 'GOALS':('sources/master_strategy_v5/goals/GOAL_REGISTER.json','goals','goal_id'),
 'DECISIONS':('sources/master_strategy_v5/audit/DECISION_REGISTER.json','decisions','id')}
for file,key,accept,keyprefix in [('TASKS','task_id','acceptance_criteria','task'),('FEATURE_ORIGINAL_CARDS','id','acceptance','feature'),('GOALS','goal_id','acceptance_criteria','goal'),('DECISIONS','id','decision_acceptance','decision')]:
 source_path,list_key,source_key=canonical_sources[file]
 canonical={entity[source_key]:entity for entity in read(source_path)[list_key]}
 for entity in read('sources/selected/'+file+'.json'):
  check('selected-criterion-source:'+entity[key],entity[accept]==canonical[entity[key]][accept])
  expected.extend((entity[key]+'-AC'+str(i),t) for i,t in enumerate(entity[accept],1))
for w in ws:expected.extend((w['workstream_id']+'-AC'+str(i),t) for i,t in enumerate(w['acceptance'],1))
check('all-original-criteria-exact',dict(expected)=={c['criterion_id']:c['original_criterion'] for c in coverage})
for row in coverage:
 check('criterion-binding:'+row['criterion_id'],digest(row['original_criterion'].encode())==row['criterion_revision_sha256'])
 check('criterion-cases:'+row['criterion_id'],bool(row['acceptance_case_ids']) and all(x in ids for x in row['acceptance_case_ids']))
 check('criterion-owner-gap:'+row['criterion_id'],bool(row['owner_role'] and row['next_evidence'] and row['downstream_gate']))
 check('criterion-runtime-open:'+row['criterion_id'],row['status']=='OPEN_NOT_REVERIFIED' and not row['current_evidence_refs'])
for c in cases:
 check('fixture:'+c['case_id'],(root/c['fixture']).exists())
 check('runtime-not-run:'+c['case_id'],c['runtime_outcome']=='NOT_RUN')
def validate_shape(schema,value):
 # Dependency-free validator for the explicitly used schema subset, not a general Draft implementation.
 if 'anyOf' in schema:
  for alternative in schema['anyOf']:
   try:validate_shape(alternative,value);return
   except AssertionError:pass
  raise AssertionError('anyOf')
 if 'const' in schema:assert value==schema['const']
 if 'enum' in schema:assert value in schema['enum']
 kind=schema.get('type')
 if kind=='null':assert value is None
 elif kind=='string':
  import re
  assert isinstance(value,str)
  assert len(value)>=schema.get('minLength',0)
  if 'pattern' in schema:assert re.search(schema['pattern'],value)
 elif kind=='integer':
  assert isinstance(value,int) and not isinstance(value,bool)
  assert value>=schema.get('minimum',value)
 elif kind=='boolean':assert isinstance(value,bool)
 elif kind=='array':
  assert isinstance(value,list)
  for item in value:validate_shape(schema['items'],item)
 elif kind=='object':
  assert isinstance(value,dict)
  assert set(schema.get('required',[]))<=set(value)
  if schema.get('additionalProperties') is False:assert set(value)<=set(schema.get('properties',{}))
  for k,v in value.items():
   if k in schema.get('properties',{}):validate_shape(schema['properties'][k],v)
def check_schema_subset(schema):
 allowed={'$schema','$id','type','properties','required','additionalProperties','items','anyOf','const','enum','minimum','minLength','pattern'}
 assert set(schema)<=allowed
 if 'properties' in schema:
  assert set(schema.get('required',[]))<=set(schema['properties'])
  for sub in schema['properties'].values():check_schema_subset(sub)
 if 'items' in schema:check_schema_subset(schema['items'])
 for sub in schema.get('anyOf',[]):check_schema_subset(sub)
for schema in (root/'contracts/schemas').glob('*.schema.json'):
 doc=json.loads(schema.read_text());check_schema_subset(doc)
 example=read('contracts/examples/'+schema.name.replace('.schema',''))
 validate_shape(doc,example);check('schema-subset-example:'+schema.name,True)
address=read('contracts/examples/source_address.json');raw=(root/'fixtures/normal/source_utf8_bom_crlf.txt').read_bytes()
check('raw-golden-hash',digest(raw)==address['raw_sha256'] and len(raw)==address['raw_size'])
quote=raw[address['start']:address['end']]
check('golden-range-hash',digest(quote)==address['range_sha256'] and quote.decode()=='моя идея')
check('raw-bom-crlf-emoji',raw.startswith(b'\xef\xbb\xbf') and b'\r\n' in raw and '😀'.encode() in raw)
cp=(root/'fixtures/normal/source_cp1251.txt').read_bytes();check('cp1251-golden',cp.decode('cp1251')=='Привет, мир\r\nТочная идея\r\n')
ptr=(root/'fixtures/normal/lfs_pointer.txt').read_text();payload=(root/'fixtures/normal/lfs_payload.bin').read_bytes()
check('lfs-golden',digest(payload) in ptr and 'size '+str(len(payload)) in ptr)
with zipfile.ZipFile(root/'fixtures/fault/duplicate_names_archive.zip') as z:
 entries=z.infolist();check('duplicate-member-ordinals',len(entries)==2 and entries[0].filename==entries[1].filename and z.read(entries[0])!=z.read(entries[1]))
with zipfile.ZipFile(root/'inputs/ORIGINAL_ROADMAP_010_021.zip') as z:check('original-roadmap-crc',z.testzip() is None)
for path,count,key in [('sources/roadmap_010_021/coverage/ALL_160_TASKS_TO_PR.json',160,None),('sources/PRODUCT_FEATURES_ALL_164.json',164,'features'),('sources/master_strategy_v5/goals/GOAL_REGISTER.json',28,'goals'),('sources/master_strategy_v5/audit/DECISION_REGISTER.json',24,'decisions')]:
 data=read(path);check('full-backlog:'+path,len(data[key] if key else data)==count)
class Links(html.parser.HTMLParser):
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k=='href' and v and not v.startswith(('https:','http:','#')):
    p=urllib.parse.unquote(v.split('#',1)[0]);check('offline-link:'+p,(root/p).exists())
Links().feed((root/'INDEX.html').read_text(encoding='utf8'))
dag=read('plan/REVISED_DELIVERY_DAG.json');seen={1,2,3,4,5,6,7,8,9}
for wave in dag['waves']:
 for node in wave:
  r=next(n for n in dag['nodes'] if n['package']==node);check('dag:'+str(node),set(r['requires'])<=seen)
 seen.update(wave)
check('no-app-implementation-claim',not read('provenance/SOURCES.json')['application_code_modified'])
print(json.dumps({'outcome':'PASS','checks':len(checks),'criteria':len(coverage),'cases':len(cases),'scope':'PACKAGE_INTEGRITY_AND_DESIGN_COVERAGE_ONLY','application_tests':'NOT_RUN','device_tests':'NOT_RUN'},ensure_ascii=False,indent=2))
