"""Validate this specification package; does not exercise application handlers."""
import hashlib
import json
from pathlib import Path
import sys
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parent.parent
def get(path):
    return json.loads((root / path).read_text(encoding='utf-8'))

manifest = get('MANIFEST.json')
actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name != 'MANIFEST.json' and '__pycache__' not in p.parts}
listed = {x['path'] for x in manifest['files']}
assert actual == listed, ('file_set_mismatch', sorted(actual ^ listed))
for item in manifest['files']:
    p = root / item['path']
    assert p.stat().st_size == item['size_bytes'], item['path']
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'], item['path']

for path in root.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
for item in get('index.json')['entries']:
    assert (root / item['path']).is_file(), item

fixtures = get('corpus/SCHEMA_FIXTURE_INDEX.json')
for row in fixtures:
    schema = get(row['schema'])
    Draft202012Validator.check_schema(schema)
    valid = Draft202012Validator(schema).is_valid(get(row['path']))
    assert valid == row['expected_valid'], row

coverage = get('acceptance/CRITERION_COVERAGE.json')
case_ids = {c['case_id'] for c in get('acceptance/ACCEPTANCE_CASES.json')}
function_ids = {f['function_id'] for f in get('plan/FUNCTIONS.json')}
assert len({r['criterion_id'] for r in coverage}) == len(coverage)
assert all(r['status'] == 'OPEN_UNTIL_RUNTIME_EVIDENCE' for r in coverage)
expected = {}
for row in get('sources/SELECTED_TASKS.json'):
    expected.update({row['task_id']+'-AC'+str(i):text for i,text in enumerate(row['acceptance_criteria'],1)})
for row in get('sources/SELECTED_FEATURE_CARDS.json'):
    expected.update({row['id']+'-AC'+str(i):text for i,text in enumerate(row['acceptance'],1)})
for row in get('sources/SELECTED_DECISIONS.json'):
    expected.update({row['id']+'-AC'+str(i):text for i,text in enumerate(row['decision_acceptance'],1)})
for row in get('sources/SELECTED_GOALS.json'):
    expected.update(dict(zip(row['criterion_ids'], row['acceptance_criteria'])))
for row in get('plan/WORKSTREAMS.json'):
    expected.update({row['workstream_id']+'-AC'+str(i):text for i,text in enumerate(row['acceptance'],1)})
observed = {r['criterion_id']:r['criterion_exact'] for r in coverage}
assert observed == expected, 'original criterion text/completeness mismatch'
for row in coverage:
    assert row['verification_case_ids'] and set(row['verification_case_ids']) <= case_ids
    assert set(row['planned_change_function_ids']) <= function_ids
    assert row['owner_role'] and row['next_evidence'] and (root / row['source_path']).is_file()
for name,count in [('ALL_TASKS_V5.json',160),('FEATURE_DEFINITION_AUDIT.json',164)]:
    d=get('sources/numbered_roadmap/source_master/strategy_v5/catalogs/'+name)
    assert d['count']==count
assert get('plan/PR_PLAN.json')['target_final_code_pr_count']==1
assert get('plan/PR_PLAN.json')['merged_from']==[16,17]
assert get('plan/DEPENDENCIES.json')['external_package_prerequisites']==[13,14,15]
assert all(c['runtime_status']=='NOT_RUN' for c in get('acceptance/ACCEPTANCE_CASES.json'))
print(json.dumps({'package_validation':'PASS','files_verified':len(listed),'schema_fixtures_checked':len(fixtures),'original_criteria_checked':len(coverage),'runtime_tests':'NOT_RUN','device_qualification':'NOT_RUN'},ensure_ascii=False))
