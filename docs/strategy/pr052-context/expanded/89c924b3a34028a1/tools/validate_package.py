#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime,timezone
root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
def read(p):return json.loads((root/p).read_text(encoding='utf-8'))
manifest=read('MANIFEST.json')
for r in manifest['files']:
 p=root/r['path'];assert p.is_file(),r['path'];assert p.stat().st_size==r['size_bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
for p in root.rglob('*.json'):json.loads(p.read_text(encoding='utf-8'))
selected=read('sources/SELECTED_45_TASKS.json')['tasks'];tasks={t['task_id']:t for t in selected}
expected=set(read('sources/briefs/PR_018.json')['source_task_ids']+read('sources/briefs/PR_019.json')['source_task_ids'])
assert len(expected)==45 and set(tasks)==expected
ledger=read('coverage/CRITERION_LEDGER.json')['criteria']
assert len({r['criterion_id'] for r in ledger})==len(ledger)
for tid,t in tasks.items():
 got=[r['original_text'] for r in ledger if r['task_id']==tid]
 assert got==t['acceptance_criteria'],tid
 assert all(r['status']=='OPEN' and r['owner_role'] and r['next_evidence'] and not r['receipt_refs'] for r in ledger if r['task_id']==tid)
for key,filename,idkey,count in [('feature_ids','FEATURES','feature_id',29),('goal_ids','GOALS','goal_id',9),('decision_ids','DECISIONS','id',3)]:
 wanted=set(read('sources/briefs/PR_018.json')[key]+read('sources/briefs/PR_019.json')[key]);data=read('coverage/SELECTED_'+filename+'.json');rows=data[filename.lower()]
 assert len(wanted)==count and {r[idkey] for r in rows}==wanted
external=read('sources/EXTERNAL_TASK_DEPENDENCIES.json')['tasks'];deps={t['task_id'] for t in external}
assert {d for t in tasks.values() for d in t['dependencies'] if d not in expected}==deps
funcs=read('implementation/FUNCTION_CATALOG.json')['functions'];assert {r['source_task_id'] for r in funcs}==expected and len(funcs)==45
extra=read('coverage/FEATURE_GOAL_DECISION_WS_LEDGER.json')['criteria']
assert len({x['criterion_id'] for x in extra})==len(extra)
assert all(x['status']=='OPEN' and x['owner_role'] and x['next_evidence'] for x in extra)
spec=read('schemas/records.schema.json')
for item in read('examples/RECORDS.json')['records']:
 s=spec['$defs'][item['kind']];r=item['record'];assert set(r)==set(s['required'])
 for k,v in r.items():
  rule=s['properties'][k];typ=rule['type']
  assert {'string':lambda:isinstance(v,str),'integer':lambda:isinstance(v,int) and not isinstance(v,bool),'array':lambda:isinstance(v,list) and all(isinstance(x,str) for x in v)}[typ]()
  if 'minimum' in rule:assert v>=rule['minimum']
  if 'enum' in rule:assert v in rule['enum']
  if 'const' in rule:assert v==rule['const']
scenarios=read('fixtures/SCENARIOS.json')['scenarios'];caseids={s['case_id'] for s in scenarios};assert len(caseids)==len(scenarios)
assert all(s['execution_status']=='NOT_RUN' for s in scenarios)
for r in ledger:assert set(r['suggested_test_refs'])<=caseids
# These values only validate documented time fixtures; they are not scheduler tests.
z=ZoneInfo('Europe/Riga');local=datetime(2026,10,25,3,30)
a=local.replace(tzinfo=z,fold=0).astimezone(timezone.utc);b=local.replace(tzinfo=z,fold=1).astimezone(timezone.utc)
assert a!=b and (b-a).total_seconds()==3600
missing=datetime(2026,3,29,3,30,tzinfo=z)
assert missing.astimezone(timezone.utc).astimezone(z).replace(tzinfo=None)!=missing.replace(tzinfo=None)
# The optional external validator checks DTO examples against draft JSON Schema.
try:
 import jsonschema
except ImportError:
 schema_check='NOT_RUN_JSONSCHEMA_UNAVAILABLE'
else:
 schema=read('schemas/records.schema.json');jsonschema.Draft202012Validator.check_schema(schema)
 for r in read('examples/RECORDS.json')['records']:jsonschema.validate(r,schema)
 schema_check='PASS'
print(json.dumps({'package_integrity':'PASS','source_tasks':len(tasks),'source_criteria':len(ledger),'scenario_designs':len(scenarios),'features':29,'goals':9,'decisions':3,'dto_field_validation':'PASS','full_jsonschema_validator':schema_check,'timezone_fixture_values':'PASS','application_tests':'NOT_RUN','device_qualification':'NOT_RUN'},ensure_ascii=False))
