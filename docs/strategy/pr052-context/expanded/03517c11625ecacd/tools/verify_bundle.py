#!/usr/bin/env python3
"""Independent artifact checker for the synthetic PR003 portable bundle.

No SCE modules, Git, network, worker, or studied repository code is executed.
Payload hashing/reconstruction is streamed; fixture metadata is kept in memory.
This tool is NOT the production exporter and does not exercise crash recovery.
"""
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote


def require(condition, code):
    if not condition:
        raise ValueError(code)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('NONFINITE_JSON')


def decode(text):
    return json.loads(text, object_pairs_hook=unique, parse_constant=reject_constant)


def read_json(path):
    return decode(path.read_text(encoding='utf-8'))


def rows(path):
    result = []
    with path.open('r', encoding='utf-8', newline='') as f:
        for line in f:
            require(line.endswith('\n') and bool(line.strip()), 'JSONL_LINE')
            result.append(decode(line))
    return result


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def safe_path(value):
    require(isinstance(value, str) and bool(value), 'OUTPUT_PATH_REQUIRED')
    p = PurePosixPath(value)
    require(not p.is_absolute() and '..' not in p.parts and '.' not in p.parts,
            'UNSAFE_OUTPUT_PATH')
    require(re.fullmatch(r'[A-Za-z0-9_./-]+', value) is not None
            and p.as_posix() == value, 'UNSAFE_OUTPUT_PATH')
    return p


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        require(tag not in {'script', 'iframe', 'object', 'embed', 'base'}, 'ACTIVE_OFFLINE_HTML')
        for key, value in attrs:
            require(not key.lower().startswith('on'), 'ACTIVE_OFFLINE_HTML')
            if key == 'id':
                require(value not in self.ids, 'DUPLICATE_HTML_ID')
                self.ids.add(value)
            if key in {'href', 'src'}:
                require(value is not None, 'EMPTY_LINK')
                self.links.append(value)


def verify_links(root):
    parsed = {}
    for path in root.rglob('*.html'):
        parser = Links()
        parser.feed(path.read_text(encoding='utf-8'))
        parser.close()
        parsed[path.resolve()] = parser
    count = 0
    for path, parser in parsed.items():
        for link in parser.links:
            target = urlsplit(link)
            require(not target.scheme and not target.netloc and not target.query,
                    'NONRELATIVE_OFFLINE_LINK')
            value = unquote(target.path)
            require(not value.startswith(('/', '\\')) and '\\' not in value,
                    'UNSAFE_OFFLINE_LINK')
            dest = (path.parent / value).resolve() if value else path
            require(dest.is_relative_to(root.resolve()) and dest.is_file(), 'BROKEN_OFFLINE_LINK')
            if target.fragment:
                require(dest in parsed and unquote(target.fragment) in parsed[dest].ids,
                        'BROKEN_OFFLINE_FRAGMENT')
            count += 1
    return count


def verify(root):
    root = Path(root).resolve()
    require(root.is_dir(), 'BUNDLE_DIRECTORY_REQUIRED')
    for p in root.rglob('*'):
        require(not p.is_symlink(), 'OUTPUT_SYMLINK')
    manifest = rows(root / 'EXPORT_MANIFEST.jsonl')
    listed, last = set(), ''
    for row in manifest:
        require(row['schema'] == 'occ.repo-archive-output.v1', 'OUTPUT_ROW_SCHEMA')
        name = row['path']
        safe_path(name)
        require(name != 'EXPORT_MANIFEST.jsonl' and name not in listed, 'OUTPUT_DUPLICATE_OR_SELF')
        require(name > last, 'OUTPUT_ORDER')
        listed.add(name)
        last = name
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'OUTPUT_MISSING')
        require(type(row['bytes']) is int and row['bytes'] >= 0 and path.stat().st_size == row['bytes'], 'OUTPUT_SIZE')
        require(file_hash(path) == row['sha256'], 'OUTPUT_HASH')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    require(actual == listed | {'EXPORT_MANIFEST.jsonl'}, 'OUTPUT_SET')
    bundle = read_json(root / 'BUNDLE.json')
    batch = read_json(root / 'BATCH.json')
    proof = read_json(root / 'VALIDATION.json')
    require(bundle['schema'] == 'occ.repo-archive-bundle.v1', 'BUNDLE_SCHEMA')
    require(batch['schema'] == 'occ.repo-manifest-batch.v1', 'BATCH_SCHEMA')
    require(digest(batch['binding']) == batch['batch_id'], 'BATCH_DIGEST')
    require(bundle['batch_id'] == batch['batch_id'] == bundle['binding']['batch_id'], 'BATCH_IDENTITY')
    require(bundle['snapshot_id'] == batch['binding']['snapshot_id'], 'SNAPSHOT_IDENTITY')
    for name, value in bundle['binding']['metadata_sha256'].items():
        safe_path(name)
        require(file_hash(root / name) == value, 'METADATA_HASH')
    require(set(bundle['binding']['metadata_sha256']) == {'BATCH.json', 'REPO_MANIFEST.jsonl', 'PARTS_INDEX.jsonl', 'VALIDATION.json'}, 'METADATA_SET')
    require(digest(bundle['binding']) == bundle['export_id'], 'EXPORT_DIGEST')
    for out in batch['outputs']:
        safe_path(out['path'])
        require((root / out['path']).stat().st_size == out['bytes']
                and file_hash(root / out['path']) == out['sha256'], 'PR002_OUTPUT_HASH')
    require(bundle['output_manifest_self_record'] == 'EXCLUDED_EXPLICITLY', 'MANIFEST_SELF_RULE')
    entries = rows(root / 'REPO_MANIFEST.jsonl')
    parts = rows(root / 'PARTS_INDEX.jsonl')
    require([r['ordinal'] for r in entries] == list(range(len(entries))), 'ENTRY_ORDER')
    require(len({r['path'] for r in entries}) == len(entries), 'ENTRY_PATH_DUPLICATE')
    by_ordinal = {row['ordinal']: row for row in entries}
    grouped, part_ids, last_key = {}, set(), None
    for row in entries:
        require(row['schema'] == 'occ.repo-entry-manifest.v1'
                and row['snapshot_id'] == bundle['snapshot_id'], 'ENTRY_SCHEMA_BINDING')
        require(row['state'] != 'PENDING', 'PENDING_ENTRY')
        if row['state'] != 'INDEXED':
            require(row['reason'] and row['chunk_count'] == 0, 'GAP_REASON_REQUIRED')
    for part in parts:
        require(part['schema'] == 'occ.repo-part-index.v1', 'PART_SCHEMA')
        part_id = part['part_id']
        require(re.fullmatch(r'[0-9a-f]{64}', part_id) is not None, 'PART_ID')
        require(part_id not in part_ids, 'PART_DUPLICATE')
        part_ids.add(part_id)
        key = (part['file_ordinal'], part['chunk_ordinal'])
        require(last_key is None or key > last_key, 'PART_ORDER')
        last_key = key
        entry = by_ordinal.get(part['file_ordinal'])
        require(entry is not None and entry['state'] == 'INDEXED', 'ORPHAN_OR_GAP_PART')
        require(part['snapshot_id'] == entry['snapshot_id']
                and part['path'] == entry['path'] and part['file_sha256'] == entry['file_sha256'], 'PART_BINDING')
        grouped.setdefault(part['file_ordinal'], []).append(part)
    payload_paths = {'parts/' + x + '.bin' for x in part_ids}
    require({n for n in listed if n.startswith('parts/')} == payload_paths, 'PAYLOAD_SET')
    indexed, gaps, raw_bytes = 0, 0, 0
    for entry in entries:
        if entry['state'] != 'INDEXED':
            gaps += 1
            continue
        indexed += 1
        fp = grouped.get(entry['ordinal'], [])
        require(len(fp) == entry['chunk_count'] and bool(fp), 'CHUNK_COUNT')
        require(type(entry['size']) is int and entry['size'] >= 0, 'SOURCE_SIZE')
        oid = entry['git_oid']
        require(re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', oid) is not None, 'GIT_OID_FORMAT')
        source_hash = hashlib.sha256()
        git_hash = hashlib.sha1() if len(oid) == 40 else hashlib.sha256()
        git_hash.update(b'blob ' + str(entry['size']).encode('ascii') + b'\0')
        cursor = 0
        for number, part in enumerate(fp):
            require(part['chunk_ordinal'] == number and part['source_start'] == cursor, 'PART_RANGE')
            size = part['source_end'] - part['source_start']
            require(type(part['bytes']) is int and size == part['bytes']
                    and size >= 0 and (size > 0 or entry['size'] == 0 and len(fp) == 1), 'PART_RANGE')
            payload = root / 'parts' / (part['part_id'] + '.bin')
            part_hash = hashlib.sha256()
            seen = 0
            with payload.open('rb') as f:
                for block in iter(lambda: f.read(65536), b''):
                    part_hash.update(block)
                    source_hash.update(block)
                    git_hash.update(block)
                    seen += len(block)
            require(seen == size and part_hash.hexdigest() == part['sha256'], 'PAYLOAD_BYTES_HASH')
            expected_revision = digest([part['logical_id'], entry['file_sha256'], part['sha256'], part['source_start'], part['source_end']])
            require(part['revision'] == part['part_id'] == expected_revision, 'PART_REVISION')
            cursor = part['source_end']
            raw_bytes += seen
        require(cursor == entry['size'] and source_hash.hexdigest() == entry['file_sha256'], 'SOURCE_RECONSTRUCTION')
        require(git_hash.hexdigest() == oid, 'SOURCE_GIT_OID')
    for obj in (batch, bundle, proof):
        require(obj['entry_count'] == len(entries) and obj['indexed_count'] == indexed
                and obj['gap_count'] == gaps and obj['part_count'] == len(parts), 'COUNTS')
        require(obj['inventory_complete'] is True
                and obj['all_tracked_bytes_exportable'] is (gaps == 0), 'COVERAGE_CLAIM')
    require(proof['status'] == 'PASS' and proof['raw_exact_for_indexed'] is True, 'PROOF')
    require(bundle['captured_export_complete'] is True and bundle['ai_delivery'] == 'NOT_PERFORMED', 'EXPORT_CLAIM')
    link_count = verify_links(root)
    return {'status': 'PASS', 'scope': bundle['proof_scope'], 'entry_count': len(entries),
            'indexed_count': indexed, 'gap_count': gaps, 'part_count': len(parts),
            'raw_bytes': raw_bytes, 'output_files': len(actual), 'relative_links': link_count,
            'application_runtime_tests': 'NOT_RUN', 'fault_recovery_tests': 'NOT_RUN', 'windows': 'NOT_RUN'}


if __name__ == '__main__':
    try:
        require(len(sys.argv) == 2, 'USAGE_VERIFY_BUNDLE_DIRECTORY')
        print(json.dumps(verify(Path(sys.argv[1])), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'FAIL', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
