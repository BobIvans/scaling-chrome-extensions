"""Check synthetic golden manifests and negative cases; no application imports."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / 'fixtures/manifest_golden'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def validate(entries, parts, raw_by_ordinal, batch, expected):
    snapshot = batch['binding']['snapshot_id']
    check(batch['batch_id'] == digest(batch['binding']), 'batch binding digest')
    check(len(entries) == expected['entry_count'], 'entry count')
    check([e['ordinal'] for e in entries] == list(range(len(entries))), 'entry ordinal set')
    check(len({e['path'] for e in entries}) == len(entries), 'entry path uniqueness')
    check(len(parts) == expected['part_count'], 'part count')
    check(len({p['part_id'] for p in parts}) == len(parts), 'part identity uniqueness')
    check([(p['file_ordinal'], p['chunk_ordinal']) for p in parts] == sorted((p['file_ordinal'], p['chunk_ordinal']) for p in parts), 'part ordering')
    indexed, gaps, by_file = 0, 0, {}
    for part in parts:
        check(part['snapshot_id'] == snapshot, 'mixed snapshot part')
        check(part['dependency_status'] == 'NOT_GENERATED', 'invented dependency coverage')
        ordinal = part['file_ordinal']
        check(type(ordinal) is int and 0 <= ordinal < len(entries), 'orphan part')
        check(entries[ordinal]['state'] == 'INDEXED', 'part for gap source')
        by_file.setdefault(ordinal, []).append(part)
    source_expected = {e['file_ordinal']: e for e in expected['sources']}
    for entry in entries:
        ordinal = entry['ordinal']
        check(entry['snapshot_id'] == snapshot, 'mixed snapshot entry')
        check(entry['packet_coverage'] == 'NOT_BUILT', 'invented packet coverage')
        check(entry['part_locator'] == {'file_ordinal': ordinal}, 'source locator')
        chunks = by_file.get(ordinal, [])
        check(entry['chunk_count'] == len(chunks), 'file chunk count')
        if entry['state'] != 'INDEXED':
            gaps += 1
            check(entry['state'] in {'EXCLUDED', 'ERROR'}, 'nonterminal source')
            check(bool(entry['reason']) and not chunks and entry['file_sha256'] is None, 'gap disposition')
            continue
        indexed += 1
        check(ordinal in raw_by_ordinal and ordinal in source_expected, 'missing raw source')
        raw = raw_by_ordinal[ordinal]
        raw_sha = hashlib.sha256(raw).hexdigest()
        check(entry['path'] == source_expected[ordinal]['path'], 'source path mapping')
        check(len(raw) == entry['size'] == source_expected[ordinal]['bytes'], 'source byte size')
        check(raw_sha == entry['file_sha256'] == source_expected[ordinal]['sha256'], 'source file hash')
        git_blob = b'blob ' + str(len(raw)).encode() + b'\0' + raw
        git_oid = hashlib.sha1(git_blob).hexdigest() if len(entry['git_oid']) == 40 else hashlib.sha256(git_blob).hexdigest()
        check(entry['git_oid'] == git_oid, 'Git blob OID')
        check([p['chunk_ordinal'] for p in chunks] == list(range(len(chunks))), 'chunk ordinal set')
        check(bool(chunks), 'missing chunks for indexed source')
        cursor, assembled = 0, hashlib.sha256()
        for part in chunks:
            start, end = part['source_start'], part['source_end']
            check(type(start) is int and type(end) is int, 'range type')
            check(start == cursor and 0 <= start <= end <= len(raw), 'range gap/overlap')
            check(end > start or (not raw and len(chunks) == 1 and start == end == 0), 'zero-length nonempty source chunk')
            piece = raw[start:end]
            piece_sha = hashlib.sha256(piece).hexdigest()
            check(part['path'] == entry['path'] and part['file_sha256'] == raw_sha, 'part-to-source link')
            check(part['bytes'] == end-start == len(piece), 'part byte size')
            check(part['sha256'] == piece_sha, 'part content hash')
            revision = digest([part['logical_id'], raw_sha, piece_sha, start, end])
            check(part['revision'] == part['part_id'] == revision, 'part revision')
            try:
                piece.decode('utf-8')
                text_eligible = True
            except UnicodeDecodeError:
                text_eligible = False
            check(part['text_eligible'] is text_eligible, 'part text eligibility')
            assembled.update(piece)
            cursor = end
        check(cursor == len(raw) and assembled.hexdigest() == raw_sha, 'byte reconstruction')
    check(indexed == expected['indexed_count'] and gaps == expected['gap_count'], 'source outcome counts')
    check(batch['all_tracked_bytes_exportable'] is False and gaps > 0, 'gap coverage claim')
    return {'indexed_sources': indexed, 'gaps': gaps, 'parts': len(parts)}


def run():
    entries = read_rows(GOLD/'REPO_MANIFEST.jsonl')
    parts = read_rows(GOLD/'PARTS_INDEX.jsonl')
    batch = json.loads((GOLD/'BATCH.example.json').read_text())
    expected = json.loads((GOLD/'SOURCE_EXPECTATIONS.json').read_text())
    raws = {s['file_ordinal']: (ROOT/s['raw_path']).read_bytes() for s in expected['sources']}
    for output in batch['outputs']:
        data = (GOLD/output['path']).read_bytes()
        check(len(data) == output['bytes'] and hashlib.sha256(data).hexdigest() == output['sha256'], 'golden output hash')
    positive = validate(entries, parts, raws, batch, expected)
    check(expected['large_source_part_count'] > 20, 'missing multi-page source')
    check(len(entries) > 20, 'missing multi-page entries')
    # Demonstrate rejection of distinct data failures. Mutations stay in memory.
    mutations = [
        ('deleted-entry', lambda e,p,r: e.pop()),
        ('duplicate-part', lambda e,p,r: p.append(copy.deepcopy(p[0]))),
        ('missing-part', lambda e,p,r: p.pop(5)),
        ('overlap', lambda e,p,r: p[6].__setitem__('source_start', p[6]['source_start']-1)),
        ('range-gap', lambda e,p,r: p[6].__setitem__('source_start', p[6]['source_start']+1)),
        ('wrong-content-hash', lambda e,p,r: p[0].__setitem__('sha256', '0'*64)),
        ('stale-revision', lambda e,p,r: p[0].__setitem__('revision', '0'*64)),
        ('mixed-snapshot', lambda e,p,r: p[0].__setitem__('snapshot_id', 'f'*64)),
        ('corrupt-raw', lambda e,p,r: r.__setitem__(0, b'X'+r[0][1:])),
        ('wrong-source-link', lambda e,p,r: p[0].__setitem__('path', 'other.txt')),
    ]
    rejected = []
    for name, mutation in mutations:
        e, p, r = copy.deepcopy(entries), copy.deepcopy(parts), dict(raws)
        mutation(e,p,r)
        try:
            validate(e,p,r,batch,expected)
        except ValueError as exc:
            rejected.append({'case':name, 'reason':str(exc)})
        else:
            raise ValueError('Mutation accepted: '+name)
    # Query pagination oracle: offsets are relative to the selected scope.
    for selected in [entries, parts, [p for p in parts if p['file_ordinal']==4]]:
        rebuilt = [row for offset in range(0,len(selected),20) for row in selected[offset:offset+20]]
        check(rebuilt == selected, 'golden pagination tail')
    return {'status':'PASS', 'scope':'Synthetic golden data/negative mutations only', **positive,
            'entries':len(entries), 'rejected_mutations':len(rejected), 'mutation_results':rejected,
            'application_runtime_executed':False}


if __name__ == '__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
