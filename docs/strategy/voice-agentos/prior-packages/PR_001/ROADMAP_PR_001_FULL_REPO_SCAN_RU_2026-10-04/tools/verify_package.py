"""Verify this PR-input's integrity and contracts, without executing app code.

Uses only the standard library. The schema checker supports the exact JSON
Schema constructs used by this package; it is not a general JSON Schema engine.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def validate_schema(value, schema):
    if 'oneOf' in schema:
        return sum(validate_schema(value, branch) for branch in schema['oneOf']) == 1
    if 'const' in schema and value != schema['const']:
        return False
    if 'enum' in schema and value not in schema['enum']:
        return False
    types = schema.get('type')
    if types:
        tests = {
            'object': isinstance(value, dict),
            'string': isinstance(value, str),
            'integer': isinstance(value, int) and not isinstance(value, bool),
            'boolean': isinstance(value, bool),
            'null': value is None,
        }
        allowed = [types] if isinstance(types, str) else types
        if not any(tests.get(t, False) for t in allowed):
            return False
    if isinstance(value, str) and 'pattern' in schema:
        if re.search(schema['pattern'], value) is None:
            return False
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            return False
    if isinstance(value, dict):
        if not set(schema.get('required', [])) <= set(value):
            return False
        properties = schema.get('properties', {})
        if schema.get('additionalProperties') is False and set(value) - set(properties):
            return False
        if any(not validate_schema(v, properties[k]) for k, v in value.items() if k in properties):
            return False
    return True


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.paths += [value for key, value in attrs if key == 'href']


def safe_member(path):
    p = PurePosixPath(path)
    return bool(path) and not p.is_absolute() and '..' not in p.parts and '\\' not in path


def main():
    manifest = read_json('MANIFEST.json')
    paths = [entry['path'] for entry in manifest['files']]
    check(len(paths) == len(set(paths)), 'Duplicate manifest paths')
    check(all(safe_member(p) for p in paths), 'Unsafe manifest path')
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
              if p.is_file() and p.name != 'MANIFEST.json'
              and '__pycache__' not in p.parts}
    check(set(paths) == actual, 'Missing or unlisted files')
    for entry in manifest['files']:
        p = ROOT / entry['path']
        check(not p.is_symlink(), 'Symlink in package: ' + entry['path'])
        check(p.stat().st_size == entry['bytes'], 'Size mismatch: ' + entry['path'])
        check(digest_file(p) == entry['sha256'], 'Hash mismatch: ' + entry['path'])

    json_files = [p for p in actual if p.endswith('.json')]
    for path in json_files:
        read_json(path)

    source = read_json('sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')['tasks']
    source_ids = [t.get('task_id', t.get('id')) for t in source]
    disposition = read_json('plan/ROADMAP_DISPOSITION.json')
    covered = [t['source_task_id'] for t in disposition['tasks']]
    check(len(source_ids) == 160 and len(set(source_ids)) == 160, 'Task catalog count/id failure')
    check(covered == source_ids, 'Roadmap task omitted/reordered/duplicated')
    check(all(not t['task_closed'] for t in disposition['tasks']), 'Task marked done by package')
    for p in disposition['follow_up_packages']:
        check(set(p['source_task_ids']) <= set(source_ids), 'Unknown follow-up task reference')
    registries = [
        ('sources/roadmap_v5/catalogs/FEATURE_DEFINITION_AUDIT.json', 'features', 164),
        ('sources/roadmap_v5/goals/GOAL_REGISTER.json', 'goals', 28),
        ('sources/roadmap_v5/audit/DECISION_REGISTER.json', 'decisions', 24),
        ('sources/roadmap_v5/catalogs/MILESTONES_V5.json', 'milestones', 10),
    ]
    for path, key, expected in registries:
        check(len(read_json(path)[key]) == expected, 'Registry count mismatch: ' + path)

    plan = read_json('plan/PR_PLAN.json')
    check(sum(t['budget_minutes'] for t in plan['tasks']) == 60, 'Session budget mismatch')
    visited = set()
    for task in plan['tasks']:
        check(set(task['depends_on']) <= visited, 'Broken/cyclic task order')
        check(set(task['source_task_ids']) <= set(source_ids), 'Unknown source task in build plan')
        visited.add(task['id'])
    check(len(visited) == 6, 'Build task count mismatch')
    check(not plan['application_code_changed'] and not plan['current_head_verified'], 'False runtime/current-head claim')

    criteria = read_json('plan/ACCEPTANCE_CASES.json')['cases']
    receipt = read_json('receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    check(len(criteria) == 12, 'Acceptance case count mismatch')
    check([c['criterion_id'] for c in criteria] == [c['criterion_id'] for c in receipt['criterion_results']], 'Receipt criteria mismatch')
    check(all(c['outcome'] == 'NOT_RUN' for c in criteria + receipt['criterion_results']), 'False execution claim')

    contract = read_json('contracts/SCAN_RUN_CONTRACT.json')
    requests = read_json('fixtures/API_REQUESTS.json')
    schema = read_json('contracts/SCAN_RUN_REQUEST.schema.json')
    check(len(schema['oneOf']) == len(contract['actions']) == 6, 'API action count mismatch')
    for request in requests['valid']:
        check(validate_schema(request, schema), 'Valid request rejected')
        check(len(json.dumps(request, ensure_ascii=False).encode()) < 16000, 'Oversized example request')
    for request in requests['invalid']:
        check(not validate_schema(request, schema), 'Invalid request accepted')
    projection = read_json('fixtures/RUN_PROJECTION.example.json')
    check(validate_schema(projection, read_json('contracts/SCAN_RUN.schema.json')), 'Projection schema failure')
    check(projection['processed'] == projection['total'] - projection['pending'], 'Progress count mismatch')
    check(sum(projection['counts'].values()) == projection['total'], 'Disposition count mismatch')
    check(projection['processed'] == 20 and projection['ledger_entries'] == 45, 'PENDING/processed example regression')

    fixture = read_json('fixtures/TREE_EXPECTATIONS.json')
    check(len(fixture['files']) == fixture['file_count'] == 45, 'Fixture count mismatch')
    fixture_paths = {e['path'] for e in fixture['files']}
    actual_fixture = {p.relative_to(ROOT / 'fixtures/repo').as_posix() for p in (ROOT / 'fixtures/repo').rglob('*') if p.is_file()}
    check(fixture_paths == actual_fixture, 'Fixture corpus omission')
    for entry in fixture['files']:
        p = ROOT / 'fixtures/repo' / entry['path']
        check(p.stat().st_size == entry['bytes'] and digest_file(p) == entry['sha256'], 'Fixture source hash mismatch')

    provenance = read_json('provenance/SOURCE_ARCHIVE.json')
    for entry in provenance['preserved_source_members']:
        p = ROOT / entry['package_path']
        check(p.stat().st_size == entry['bytes'] and digest_file(p) == entry['sha256'], 'Preserved source changed')
    index = read_json('index.json')
    for path in index['read_order'] + list(plan['artifact_paths'].values()):
        check(safe_member(path) and (ROOT / path).is_file(), 'Unresolved instruction path: ' + path)
    parser = Links()
    parser.feed((ROOT / 'INDEX.html').read_text(encoding='utf-8'))
    for path in parser.paths:
        check(safe_member(path) and (ROOT / path).is_file(), 'Broken offline index link: ' + path)

    print(json.dumps({
        'status': 'PASS', 'scope': 'PR-input package integrity, contracts and traceability only',
        'manifest_files': len(paths), 'json_files': len(json_files),
        'preserved_tasks': 160, 'preserved_features': 164, 'build_tasks': 6,
        'runtime_acceptance_cases': 12, 'runtime_acceptance_executed': False,
        'fixture_files': 45, 'request_examples_checked': len(requests['valid']) + len(requests['invalid']),
        'preserved_source_members': len(provenance['preserved_source_members']),
        'offline_links': len(parser.paths), 'application_code_executed': False,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'FAIL', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
