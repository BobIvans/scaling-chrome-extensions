#!/usr/bin/env python3
"""Verify the implementation-input package, not the future SCE exporter."""
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, unquote
from verify_bundle import verify, require, file_hash, read_json, rows, digest, Links, safe_path

ROOT = Path(__file__).resolve().parent.parent


def inventory(root):
    return {p.relative_to(root).as_posix() for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def refresh_output_manifest(root):
    records = []
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.name != 'EXPORT_MANIFEST.jsonl':
            records.append({'schema': 'occ.repo-archive-output.v1',
                            'path': p.relative_to(root).as_posix(),
                            'bytes': p.stat().st_size, 'sha256': file_hash(p)})
    (root / 'EXPORT_MANIFEST.jsonl').write_text(''.join(
        json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
        for r in records), encoding='utf-8')


def reseal_metadata(root):
    batch = read_json(root / 'BATCH.json')
    for r in batch['outputs']:
        path = root / r['path']
        r['bytes'], r['sha256'] = path.stat().st_size, file_hash(path)
    (root / 'BATCH.json').write_text(json.dumps(batch, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    bundle = read_json(root / 'BUNDLE.json')
    bundle['binding']['metadata_sha256'] = {n: file_hash(root / n) for n in bundle['binding']['metadata_sha256']}
    bundle['export_id'] = digest(bundle['binding'])
    (root / 'BUNDLE.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    refresh_output_manifest(root)


def write_rows(path, data):
    path.write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                            for x in data), encoding='utf-8')


def negative_mutations(source):
    outcomes = []
    specs = [
        ('payload-byte-change', 'OUTPUT_HASH'), ('payload-missing', 'OUTPUT_MISSING'),
        ('extra-output', 'OUTPUT_SET'), ('duplicate-output-record', 'OUTPUT_DUPLICATE_OR_SELF'),
        ('unsafe-output-path', 'UNSAFE_OUTPUT_PATH'), ('range-gap-with-valid-file-hashes', 'PART_RANGE'),
        ('wrong-batch-digest', 'BATCH_DIGEST'), ('broken-relative-link', 'BROKEN_OFFLINE_LINK'),
        ('gap-without-reason', 'GAP_REASON_REQUIRED'), ('duplicate-part-id', 'PART_DUPLICATE'),
        ('extra-gap-payload', 'PAYLOAD_SET'), ('active-offline-script', 'ACTIVE_OFFLINE_HTML'),
    ]
    with tempfile.TemporaryDirectory(prefix='pr003-fixture-negative-') as tmp:
        for name, expected in specs:
            target = Path(tmp) / name
            shutil.copytree(source, target)
            first = sorted((target / 'parts').glob('*.bin'))[0]
            if name == 'payload-byte-change':
                data = first.read_bytes()
                require(bool(data), 'NEGATIVE_FIXTURE_NONEMPTY_REQUIRED')
                first.write_bytes(bytes([data[0] ^ 1]) + data[1:])
            elif name == 'payload-missing':
                first.unlink()
            elif name == 'extra-output':
                (target / 'extra.txt').write_text('unlisted')
            elif name == 'duplicate-output-record':
                file = target / 'EXPORT_MANIFEST.jsonl'
                file.write_text(file.read_text() + file.read_text().splitlines()[0] + '\n', encoding='utf-8')
            elif name == 'unsafe-output-path':
                file = target / 'EXPORT_MANIFEST.jsonl'
                data = rows(file)
                data[0]['path'] = '../escape.bin'
                write_rows(file, data)
            elif name == 'range-gap-with-valid-file-hashes':
                file = target / 'PARTS_INDEX.jsonl'
                data = rows(file)
                data[0]['source_start'] += 1
                data[0]['source_end'] += 1
                write_rows(file, data)
                reseal_metadata(target)
            elif name == 'wrong-batch-digest':
                file = target / 'BATCH.json'
                data = read_json(file)
                data['binding']['repository'] = 'wrong-repo'
                file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                reseal_metadata(target)
            elif name == 'broken-relative-link':
                file = target / 'INDEX.html'
                file.write_text(file.read_text().replace('navigation/entries_0000.html', 'navigation/missing.html'), encoding='utf-8')
                refresh_output_manifest(target)
            elif name == 'gap-without-reason':
                file = target / 'REPO_MANIFEST.jsonl'
                data = rows(file)
                data[-1]['reason'] = None
                write_rows(file, data)
                reseal_metadata(target)
            elif name == 'duplicate-part-id':
                file = target / 'PARTS_INDEX.jsonl'
                data = rows(file)
                data[1]['part_id'] = data[0]['part_id']
                write_rows(file, data)
                reseal_metadata(target)
            elif name == 'extra-gap-payload':
                (target / 'parts' / ('f' * 64 + '.bin')).write_bytes(b'not allowed')
                refresh_output_manifest(target)
            elif name == 'active-offline-script':
                file = target / 'INDEX.html'
                file.write_text(file.read_text().replace('</body>', '<script>unsafe()</script></body>'), encoding='utf-8')
                refresh_output_manifest(target)
            try:
                verify(target)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                require(str(exc) == expected, 'UNEXPECTED_NEGATIVE_REJECTION:' + name + ':' + str(exc))
                outcomes.append({'mutation': name, 'expected': expected, 'status': 'REJECTED_AS_EXPECTED'})
            else:
                raise ValueError('NEGATIVE_ACCEPTED:' + name)
    return outcomes


def check_package():
    files = inventory(ROOT)
    manifest = read_json(ROOT / 'MANIFEST.json')
    listed = {r['path'] for r in manifest['files']}
    require(listed == files - {'MANIFEST.json'}, 'PACKAGE_FILE_SET')
    for row in manifest['files']:
        safe_path(row['path'])
        path = ROOT / row['path']
        require(path.stat().st_size == row['bytes'] and file_hash(path) == row['sha256'], 'PACKAGE_HASH:' + row['path'])
    json_count = 0
    for p in ROOT.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            if p.suffix == '.json':
                read_json(p)
                json_count += 1
            elif p.suffix == '.jsonl':
                rows(p)
                json_count += 1
    provenance = read_json(ROOT / 'provenance/SOURCES.json')
    for row in provenance['preserved_source_members']:
        p = ROOT / row['package_path']
        require(p.stat().st_size == row['bytes'] and file_hash(p) == row['sha256'], 'PRESERVATION_HASH')
    plan = read_json(ROOT / 'plan/PR_PLAN.json')
    require(sum(s['budget_minutes'] for s in plan['tasks']) == 60 and len(plan['tasks']) == 6, 'PLAN_TIME')
    require(plan['application_code_changed'] is False and plan['current_head_verified'] is False
            and plan['github_pr_url'] is None and plan['github_pr_number'] is None, 'UNOBSERVED_CLAIM')
    step_ids = {s['id'] for s in plan['tasks']}
    seen = set()
    for step in plan['tasks']:
        require(set(step['depends_on']) <= seen, 'STEP_DAG')
        require(step['status'] == 'NOT_STARTED', 'FALSE_STEP_DONE')
        seen.add(step['id'])
    source_tasks = read_json(ROOT / 'sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')['tasks']
    dispositions = read_json(ROOT / 'plan/ROADMAP_DISPOSITION.json')['tasks']
    require(len(source_tasks) == len(dispositions) == 160
            and {x['task_id'] for x in source_tasks} == {x['task_id'] for x in dispositions}, 'BACKLOG_COVERAGE')
    for name, field, count in [
        ('catalogs/FEATURE_DEFINITION_AUDIT.json', 'features', 164),
        ('goals/GOAL_REGISTER.json', 'goals', 28),
        ('audit/DECISION_REGISTER.json', 'decisions', 24),
        ('catalogs/MILESTONES_V5.json', 'milestones', 10),
    ]:
        catalog = read_json(ROOT / 'sources/roadmap_v5' / name)
        require(catalog['count'] == len(catalog[field]) == count, 'CATALOG_COUNT:' + name)
    acceptance = read_json(ROOT / 'plan/ACCEPTANCE_CASES.json')
    result = read_json(ROOT / 'receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    require(acceptance['count'] == len(acceptance['cases']) == len(result['cases']) == 16, 'CASE_COUNT')
    require(all(x['status'] == 'NOT_RUN' for x in acceptance['cases'] + result['cases']), 'FALSE_RUNTIME_PASS')
    require({x['id'] for x in acceptance['cases']} == {x['id'] for x in result['cases']}, 'RESULT_CASE_IDS')
    routing = read_json(ROOT / 'plan/CHAT_ROUTING.json')
    require(routing['is_automatic_sync'] is False and len(routing['chats']) == 3, 'CHAT_ROUTING')
    cli = read_json(ROOT / 'fixtures/CLI_REQUESTS.json')
    cli_schema = read_json(ROOT / 'contracts/CLI_REQUEST.schema.json')
    cli_checks = 'STRUCTURAL_CHECKS'
    try:
        import jsonschema
    except ImportError:
        def valid_cli(request):
            return (isinstance(request, dict)
                    and set(request) == set(cli_schema['required'])
                    and request.get('schema') == cli_schema['properties']['schema']['const']
                    and isinstance(request.get('action'), str)
                    and request['action'] in cli_schema['properties']['action']['enum']
                    and all(isinstance(request.get(k), str) and bool(request[k])
                            for k in ('profile', 'repository', 'manifest', 'output'))
                    and re.fullmatch(cli_schema['properties']['repository']['pattern'], request['repository']) is not None)
        require(all(valid_cli(x) for x in cli['valid']), 'VALID_CLI_REJECTED')
        require(all(not valid_cli(x['request']) for x in cli['invalid']), 'INVALID_CLI_ACCEPTED')
        cli_checks = 'STRICT_STRUCTURAL_VALID_AND_NEGATIVE_REQUESTS_CHECKED'
    else:
        jsonschema.Draft202012Validator.check_schema(cli_schema)
        validator = jsonschema.Draft202012Validator(cli_schema)
        for r in cli['valid']:
            validator.validate(r)
        for r in cli['invalid']:
            require(list(validator.iter_errors(r['request'])), 'INVALID_CLI_ACCEPTED')
        cli_checks = 'JSONSCHEMA_VALID_AND_NEGATIVE_REQUESTS_REJECTED'
    source = ROOT / 'fixtures/portable_bundle'
    proof = verify(source)
    zip_path = ROOT / 'fixtures/PORTABLE_CONTEXT.example.zip'
    receipt = read_json(ROOT / 'fixtures/PORTABLE_CONTEXT.example.receipt.json')
    require(file_hash(zip_path) == receipt['archive_sha256'], 'EXAMPLE_ZIP_HASH')
    require(file_hash(source / 'EXPORT_MANIFEST.jsonl') == receipt['output_manifest_sha256'], 'EXAMPLE_MANIFEST_HASH')
    require((ROOT / 'fixtures/PORTABLE_CONTEXT.example.zip.sha256').read_text().split()[0] == receipt['archive_sha256'], 'SIDECAR_HASH')
    with tempfile.TemporaryDirectory(prefix='pr003-portable-extract-') as temp:
        moved = Path(temp) / 'moved' / 'portable'
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            require(len(names) == len(set(names)) == receipt['member_count'], 'ZIP_MEMBER_COUNT')
            require(set(names) == inventory(source), 'ZIP_MEMBER_SET')
            for name in names:
                safe_path(name)
            require(z.testzip() is None, 'ZIP_CRC')
            z.extractall(moved)
        extracted = verify(moved)
        require(extracted == proof, 'EXTRACTION_PROOF_DIFFERENT')
    expected_sources = read_json(ROOT / 'fixtures/manifest_golden/SOURCE_EXPECTATIONS.json')['sources']
    parts = rows(source / 'PARTS_INDEX.jsonl')
    for row in expected_sources:
        source_path = ROOT / row['raw_path']
        require(source_path.stat().st_size == row['bytes'] and file_hash(source_path) == row['sha256'], 'RAW_GOLDEN_HASH')
        h, size = hashlib.sha256(), 0
        for part in parts:
            if part['file_ordinal'] == row['file_ordinal']:
                with (source / 'parts' / (part['part_id'] + '.bin')).open('rb') as f:
                    for block in iter(lambda: f.read(65536), b''):
                        h.update(block)
                        size += len(block)
        require(size == row['bytes'] and h.hexdigest() == row['sha256'], 'GOLDEN_SOURCE_RECONSTRUCTION')
    parser = Links()
    parser.feed((ROOT / 'INDEX.html').read_text())
    for link in parser.links:
        split = urlsplit(link)
        require(not split.scheme and not split.netloc, 'PACKAGE_REMOTE_LINK')
        require((ROOT / unquote(split.path)).is_file(), 'PACKAGE_BROKEN_LINK')
    negatives = negative_mutations(source)
    return {'status': 'PASS', 'scope': 'PACKAGE_AND_SYNTHETIC_ARTIFACT_ONLY',
            'package_files': len(files), 'json_jsonl_files_parsed': json_count,
            'preserved_files_verified': len(provenance['preserved_source_members']),
            'preserved_source_tasks': len(source_tasks), 'plan_steps': 6, 'planned_minutes': 60,
            'runtime_acceptance_cases': 16, 'runtime_acceptance_execution': 'NOT_RUN',
            'cli_schema': cli_checks, 'synthetic_bundle': proof, 'zip_extraction': 'PASS',
            'source_byte_comparison': 'PASS', 'negative_mutations': negatives,
            'application_code_changed': False, 'current_head_verified': False,
            'github_pr_created': False, 'remote_ci': 'NOT_RUN', 'windows_device': 'NOT_RUN',
            'actual_exporter_fault_recovery': 'NOT_RUN'}


if __name__ == '__main__':
    try:
        sys.dont_write_bytecode = True
        print(json.dumps(check_package(), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'FAIL', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
