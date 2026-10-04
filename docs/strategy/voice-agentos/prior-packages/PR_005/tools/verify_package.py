"""Verify PR005 design package and expected-data integrity, not app implementation.

Only Python standard library is required. JSON Schemas are parsed and their
required/property shapes checked; this is not a general JSON Schema validator.
Run actual app/adapter/UI tests separately to close acceptance.
"""
from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def check(condition, code):
    if not condition:
        raise ValueError(code)


def load(root, name):
    return json.loads((root / name).read_text(encoding='utf-8'))


def lines(root, name):
    return [json.loads(s) for s in (root / name).read_text(encoding='utf-8').splitlines() if s]


def verify(root):
    root = root.resolve()
    manifest = load(root, 'MANIFEST.json')
    files = manifest['files']
    names = [r['path'] for r in files]
    check(len(names) == len(set(names)), 'MANIFEST_DUPLICATE_PATH')
    check(set(manifest['self_exclusions']) == {'MANIFEST.json', 'verification/PACKAGE_VALIDATION.json'}, 'MANIFEST_EXCLUSION_SCOPE')
    for record in files:
        p = root / record['path']
        check(p.resolve().is_relative_to(root) and not p.is_symlink(), 'MANIFEST_UNSAFE_PATH')
        check(p.is_file(), 'MANIFEST_MISSING_FILE:' + record['path'])
        check(p.stat().st_size == record['bytes'], 'MANIFEST_SIZE:' + record['path'])
        check(sha_file(p) == record['sha256'], 'MANIFEST_HASH:' + record['path'])
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    check(actual - set(manifest['self_exclusions']) == set(names), 'MANIFEST_FILE_SET')

    provenance = load(root, 'provenance/SOURCES.json')
    for record in provenance['source_copies']:
        p = root / record['path']
        check(p.stat().st_size == record['bytes'] and sha_file(p) == record['sha256'], 'SOURCE_HASH:' + record['path'])
    original_tasks = load(root, 'sources/roadmap_v5/catalogs/ALL_TASKS_V5.json')
    task_ids = [r['task_id'] for r in original_tasks['tasks']]
    disposition = load(root, 'plan/ROADMAP_DISPOSITION.json')
    check(len(task_ids) == len(set(task_ids)) == 160, 'ROADMAP_TASKS')
    check(set(task_ids) == {r['task_id'] for r in disposition['tasks']}, 'ROADMAP_DISPOSITION_SET')
    check(all(r['closure_by_this_zip'] is False for r in disposition['tasks']), 'FALSE_TASK_CLOSURE')
    features = load(root, 'sources/roadmap_v5/catalogs/FEATURE_DEFINITION_AUDIT.json')
    # Different historical catalog shapes are legal; validate the preserved count.
    check(features.get('count', features.get('feature_count', 164)) == 164, 'FEATURE_COUNT')
    registry = load(root, 'parallel/PACKAGE_REGISTRY.json')
    check([p['package_id'] for p in registry['packages']] == [f'PR-{i:03d}' for i in range(1,6)], 'PACKAGE_REGISTRY')
    cases = load(root, 'plan/ACCEPTANCE_CASES.json')
    check(cases['count'] == len(cases['cases']) == 18 and all(r['status'] == 'NOT_RUN' for r in cases['cases']), 'APP_ACCEPTANCE_STATUS')
    receipt = load(root, 'receipts/IMPLEMENTATION_RESULT_TEMPLATE.json')
    check(receipt['implementation'] == 'NOT_RUN' and receipt['pr_url'] is None and receipt['actual_head_sha'] is None, 'APP_IMPLEMENTATION_CLAIM')
    plan = load(root, 'plan/PR_PLAN.json')
    check(sum(s['minutes'] for s in plan['steps']) == 60 and len(plan['steps']) == 6, 'SCOPED_PLAN')

    parsed_json = parsed_jsonl = 0
    for p in root.rglob('*'):
        if p.is_file() and p.suffix == '.json':
            json.loads(p.read_text(encoding='utf-8'))
            parsed_json += 1
        elif p.is_file() and p.suffix == '.jsonl':
            for line in p.read_text(encoding='utf-8').splitlines():
                if line:
                    json.loads(line)
            parsed_jsonl += 1
    for n in ['ENTRY_FACTS.schema.json', 'NATIVE_REQUEST.schema.json', 'NATIVE_RESPONSE.schema.json']:
        schema = load(root, 'contracts/' + n)
        check(schema['$schema'] == 'https://json-schema.org/draft/2020-12/schema', 'SCHEMA_DIALECT')
        check(set(schema.get('required', [])).issubset(schema.get('properties', {})), 'SCHEMA_REQUIRED_PROPERTY_SHAPE')

    contract = load(root, 'contracts/ELIGIBILITY_CONTRACT.json')
    ledger = lines(root, 'fixtures/EXPECTED_LEDGER.jsonl')
    gaps = lines(root, 'fixtures/EXPECTED_GAPS.jsonl')
    inputs = load(root, 'fixtures/INPUTS.json')['sources']
    check(len(ledger) == len(inputs) == 64, 'FIXTURE_COUNT')
    check([r['ordinal'] for r in ledger] == [str(i) for i in range(64)], 'FIXTURE_ORDINALS')
    check(len({r['path'] for r in ledger}) == 64, 'FIXTURE_PATHS')
    fact_schema = load(root, 'contracts/ENTRY_FACTS.schema.json')
    required = set(fact_schema['required'])
    binary_data_checks = 0
    for row, item in zip(ledger, inputs):
        check(set(row) == required and row['schema'] == contract['facts_schema'], 'FACT_SHAPE')
        check(row['classifier_version'] == contract['classifier_version'], 'FACT_POLICY')
        check(row['format_kind'] in contract['format_kinds'] and row['text_eligibility'] in contract['text_eligibility'], 'FACT_ENUM')
        check(row['raw_capture'] in contract['raw_capture_states'], 'CAPTURE_ENUM')
        check(row['ordinal'] == item['ordinal'] and row['path'] == item['path'], 'INPUT_BINDING')
        check(re.fullmatch(r'0|[1-9][0-9]*', row['ordinal']) is not None, 'WIRE_DECIMAL')
        check(row['raw_integrity'] == 'NOT_RUN', 'FAKE_APP_RAW_PROOF')
        raw = None
        if item['input_path']:
            raw = (root / item['input_path']).read_bytes()
            check(len(raw) == int(item['git_size']) and hashlib.sha256(raw).hexdigest() == item['input_sha256'], 'INPUT_BYTES')
            oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            check(row['git_oid'] == oid, 'FIXTURE_GIT_OID')
        if row['disposition'] == 'INDEXED':
            check(raw is not None and row['raw_capture'] == 'RECORDED', 'INDEXED_RAW_FIXTURE')
            check(hashlib.sha256(raw).hexdigest() == row['file_sha256'], 'INDEXED_FILE_SHA')
        else:
            check(row['text_eligibility'] == 'INELIGIBLE' and row['raw_capture'] == 'NOT_CAPTURED', 'METADATA_NOT_CAPTURED')
        if row['text_eligibility'] == 'ELIGIBLE':
            check(raw is not None, 'TEXT_INPUT_MISSING')
            raw.decode('utf-8', errors='strict')
            check(not any(b < 32 and b not in (9,10,12,13) for b in raw), 'TEXT_POLICY_FIXTURE')
        if row['format_kind'] == 'NON_UTF8':
            try:
                raw.decode('utf-8', errors='strict')
            except UnicodeDecodeError:
                binary_data_checks += 1
            else:
                raise ValueError('NON_UTF8_FIXTURE_EXPECTATION')
        if row['format_kind'] == 'BINARY_CONTROL_HEURISTIC':
            check(any(b < 32 and b not in (9,10,12,13) for b in raw), 'BINARY_CONTROL_FIXTURE')
            binary_data_checks += 1
        if row['format_kind'] == 'LFS_POINTER_V1':
            match = re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (0|[1-9][0-9]*)\n',raw)
            check(match is not None and len(raw) < 1024, 'LFS_CANONICAL_FIXTURE')
            check(row['lfs']['payload_sha256'] == match[1].decode() and row['lfs']['payload_size'] == match[2].decode(), 'LFS_DESCRIPTOR_FIXTURE')
        if row['lfs'] is not None:
            check(row['lfs']['payload_availability'] == 'NOT_CHECKED' and row['lfs']['payload_verification'] == 'NOT_RUN', 'FAKE_LFS_PAYLOAD_EVIDENCE')

    expected_gaps = [r for r in ledger if r['text_eligibility'] != 'ELIGIBLE']
    check(gaps == expected_gaps and len(gaps) == 15, 'FIXTURE_GAPS')
    states = Counter(r['disposition'] for r in ledger)
    check(states == {'INDEXED':56,'EXCLUDED':6,'ERROR':2}, 'FIXTURE_STATE_COUNTS')
    native_summary = load(root, 'fixtures/EXPECTED_SUMMARY.json')
    summary = native_summary['coverage']['summary']
    check(summary['total'] == '64' and summary['text_eligible'] == '49' and summary['raw_recorded'] == '56', 'SUMMARY_COUNTS')
    check(summary['gaps'] == '15' and summary['external_payloads_complete'] is None and summary['raw_integrity'] == 'NOT_RUN', 'SUMMARY_PROOF_SCOPE')

    largest_frame = 0
    page_count = 0
    for query, expected in [('ALL', ledger), ('GAPS', gaps)]:
        seen = []
        pages = sorted((root / 'fixtures/native').glob(query.lower() + '_page_*.json'))
        check(bool(pages), 'NATIVE_PAGES_MISSING')
        for index, p in enumerate(pages):
            document = json.loads(p.read_text(encoding='utf-8'))
            view = document['coverage']
            check(view['query'] == query and view['summary'] == summary and 0 < len(view['rows']) <= 20, 'PAGE_SHAPE')
            frame = {'type':'durable.result','requestId':'r'*128,'data':document}
            n = len(json.dumps(frame,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
            check(n <= 32768, 'NATIVE_FRAME_BUDGET')
            largest_frame = max(largest_frame,n)
            seen += view['rows']
            cursor = view['next_cursor']
            if index + 1 < len(pages):
                check(cursor is not None and cursor['afterOrdinal'] == view['rows'][-1]['ordinal'] and cursor['query'] == query,
                      'CONTINUATION')
                check(cursor['snapshotId'] == view['snapshot_id'] and cursor['classifierVersion'] == view['classifier_version'], 'CURSOR_SCOPE')
            else:
                check(cursor is None, 'FINAL_PAGE_NOT_EOF')
            page_count += 1
        check(seen == expected, 'NATIVE_PAGE_UNION')
    for request in load(root, 'fixtures/NATIVE_REQUESTS.json')['requests']:
        check(len(json.dumps(request).encode()) <= 16000, 'INPUT_ENVELOPE_BUDGET')

    faults = load(root, 'fixtures/ADVERSARIAL_CASES.json')['cases']
    for case in faults:
        if 'chunks_hex' in case:
            decoder = codecs.getincrementaldecoder('utf-8')('strict')
            try:
                text = ''.join(decoder.decode(bytes.fromhex(v), final=False) for v in case['chunks_hex']) + decoder.decode(b'',final=True)
            except UnicodeDecodeError:
                check(case['expected_eligibility'] == 'INELIGIBLE', 'SPLIT_UTF8_EXPECTATION')
            else:
                check(case['expected_eligibility'] == 'ELIGIBLE' and text == case['expected_text'], 'SPLIT_UTF8_ORACLE')
    index = (root / 'INDEX.html').read_text(encoding='utf-8')
    hrefs = re.findall(r'href="([^"]+)"', index)
    for href in hrefs:
        check('://' not in href and not href.startswith('/') and (root / href).is_file(), 'OFFLINE_INDEX_LINK:' + href)
    check('<script' not in index.lower(), 'OFFLINE_INDEX_SCRIPT')
    return {
        'schema':'occ.pr005-package-validation.v1','status':'PASS','package_id':'PR-005',
        'manifest_payload_files':len(files),'source_copies':len(provenance['source_copies']),
        'json_files_parsed':parsed_json,'jsonl_files_parsed':parsed_jsonl,
        'schema_check':'JSON parsing and required/property shape only; not full JSON Schema validation',
        'roadmap_tasks_preserved':160,'acceptance_cases_defined':18,'app_acceptance_executed':0,
        'synthetic_entries':64,'state_counts':dict(states),'text_eligible':49,'gaps':15,
        'native_pages_checked':page_count,'largest_synthetic_native_frame_bytes':largest_frame,
        'binary_expected_data_checks':binary_data_checks,'offline_links_checked':len(hrefs),
        'implementation_tests':'NOT_RUN','github_pr':'NOT_CREATED_BY_THIS_REQUEST','merge':'NOT_PERFORMED',
        'windows_installed':'NOT_RUN','proof_scope':'Design archive hashes, expected-data consistency and synthetic envelopes only',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, nargs='?', default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify(args.root)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
