"""Deterministic captured-repository metadata, using the existing SQLite owner.

Only the explicit operator CLI publishes files. Native pages are read-only and
never confuse a checked part page with a full captured-byte proof.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from automation_core import digest, strict_int
import repo_context as repo

PAGE_FRAME_BYTES = 32_768
MAX_OFFSET = 9_007_199_254_740_991  # Native JSON integer interoperability, not a corpus cap.
HASH = re.compile(r'^[0-9a-f]{64}$')
ARTIFACTS = ('REPO_MANIFEST.jsonl', 'PARTS_INDEX.jsonl', 'VALIDATION.json', 'BATCH.json')


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


@contextmanager
def read_view(store, namespace, snapshot_id, alias, profile):
    db = repo.db_for(Path(store))
    try:
        db.execute('BEGIN')
        snap = repo.load_snapshot(db, namespace, snapshot_id)
        if snap['alias'] != alias or json.loads(snap['profile']) != profile:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        if snap['id'] != digest({'alias': snap['alias'], 'profile': profile, 'head': snap['head'], 'tree': snap['tree']}):
            raise ValueError('CONTEXT_CORRUPT')
        yield db, snap
    finally:
        db.rollback()
        db.close()


def inventory(db, snap):
    sid = snap['id']
    counts = dict(db.execute('SELECT state,count(*) FROM repo_entries WHERE snapshot_id=? GROUP BY state', (sid,)))
    if snap['cursor'] != snap['total'] or counts.get('PENDING'):
        raise ValueError('CONTEXT_INCOMPLETE')
    bounds = db.execute('SELECT count(*),min(ordinal),max(ordinal) FROM repo_entries WHERE snapshot_id=?', (sid,)).fetchone()
    if (bounds[0] != snap['total'] or set(counts) - {'INDEXED', 'EXCLUDED', 'ERROR'}
            or bounds[0] and (bounds[1] != 0 or bounds[2] != bounds[0] - 1)):
        raise ValueError('CONTEXT_CORRUPT')
    orphan = db.execute('''SELECT 1 FROM repo_chunks c LEFT JOIN repo_entries e
        ON c.snapshot_id=e.snapshot_id AND c.path=e.path
        WHERE c.snapshot_id=? AND (e.path IS NULL OR e.state!='INDEXED') LIMIT 1''', (sid,)).fetchone()
    if orphan:
        raise ValueError('CONTEXT_CORRUPT')
    parts, distinct_parts = db.execute('SELECT count(*),count(DISTINCT revision) FROM repo_chunks WHERE snapshot_id=?', (sid,)).fetchone()
    if parts != distinct_parts:
        raise ValueError('CONTEXT_CORRUPT')
    return {'entry_count': bounds[0], 'indexed_count': counts.get('INDEXED', 0),
            'gap_count': bounds[0] - counts.get('INDEXED', 0), 'part_count': parts,
            'counts': counts}


def batch_binding(snap):
    return {'schema': 'occ.repo-manifest-binding.v1', 'snapshot_id': snap['id'],
            'namespace': snap['namespace'], 'repository': snap['alias'],
            'repo_sha': snap['head'], 'tree_sha': snap['tree'],
            'profile_revision': digest(json.loads(snap['profile'])), 'goal_revision': None,
            'grouping_policy': 'RAW_CHUNK_MAPPING_V1',
            'parser_policy': 'PRESERVED_ANALYSIS_KINDS_NO_NEW_PARSE',
            'historical_scanner_build': 'UNKNOWN',
            'export_policy': 'LOCAL_CAPTURED_CHUNK_METADATA_V1'}


def entries(db, sid):
    return db.execute('''SELECT e.*, (SELECT count(*) FROM repo_chunks c
        WHERE c.snapshot_id=e.snapshot_id AND c.path=e.path) AS chunk_count
        FROM repo_entries e WHERE e.snapshot_id=? ORDER BY e.ordinal''', (sid,))


def entry_record(row):
    try:
        analysis = json.loads(row['analysis'] or '{}')
    except (ValueError, TypeError) as exc:
        raise ValueError('CONTEXT_CORRUPT') from exc
    if not isinstance(analysis, dict):
        raise ValueError('CONTEXT_CORRUPT')
    return {'schema': 'occ.repo-entry-manifest.v1', 'snapshot_id': row['snapshot_id'],
            'ordinal': row['ordinal'], 'path': row['path'], 'mode': row['mode'],
            'git_type': row['kind'], 'git_oid': row['oid'], 'size': row['size'],
            'state': row['state'], 'reason': row['reason'], 'file_sha256': row['file_hash'],
            'parser': analysis.get('parser'), 'chunk_count': row['chunk_count'],
            'part_locator': {'file_ordinal': row['ordinal']}, 'packet_coverage': 'NOT_BUILT'}


def part_record(db, snap, entry, chunk):
    raw = chunk['raw']
    if (not isinstance(raw, bytes) or not isinstance(chunk['logical_id'], str)
            or not HASH.fullmatch(chunk['logical_id'])
            or any(type(v) is not int for v in (chunk['ordinal'], chunk['byte_start'], chunk['byte_end'], entry['size']))
            or entry['size'] < 0 or chunk['ordinal'] < 0
            or not HASH.fullmatch(entry['file_hash'] or '')
            or chunk['byte_start'] < 0 or chunk['byte_end'] > entry['size']
            or chunk['byte_end'] - chunk['byte_start'] != len(raw)
            or entry['size'] > 0 and not raw
            or chunk['revision'] != digest([chunk['logical_id'], entry['file_hash'],
                                             repo.sha(raw), chunk['byte_start'], chunk['byte_end']])):
        raise ValueError('CONTEXT_CORRUPT')
    text_eligible = chunk['item_id'] is not None
    if text_eligible:
        repo.verify_source_item(db, chunk)
        item = json.loads(db.execute('SELECT payload FROM items WHERE id=?', (chunk['item_id'],)).fetchone()[0])
        required = {'id': digest([snap['id'], chunk['revision']]), 'namespace': snap['namespace'],
                    'schema_version': 'occ.git-source.v1', 'repo_sha': snap['head'],
                    'source_key': 'git:' + snap['alias'] + ':' + chunk['logical_id'],
                    'path': entry['path'], 'file_sha256': entry['file_hash'],
                    'logical_id': chunk['logical_id'], 'revision': chunk['revision'],
                    'byte_start': chunk['byte_start'], 'byte_end': chunk['byte_end']}
        if chunk['item_id'] != required['id'] or any(item.get(k) != v for k, v in required.items()):
            raise ValueError('CONTEXT_CORRUPT')
    return {'schema': 'occ.repo-part-index.v1', 'snapshot_id': snap['id'],
            'file_ordinal': entry['ordinal'], 'path': entry['path'], 'chunk_ordinal': chunk['ordinal'],
            'part_id': chunk['revision'], 'logical_id': chunk['logical_id'], 'revision': chunk['revision'],
            'source_start': chunk['byte_start'], 'source_end': chunk['byte_end'], 'bytes': len(raw),
            'sha256': repo.sha(raw), 'file_sha256': entry['file_hash'], 'text_eligible': text_eligible,
            'dependency_status': 'NOT_GENERATED'}


def metadata_info(snap, counts):
    binding = batch_binding(snap)
    return {'schema': 'occ.repo-manifest-view.v1', 'batch_id': digest(binding), 'binding': binding,
            **counts, 'index_complete': True, 'inventory_complete': True,
            'raw_exact_for_indexed': None, 'text_exportable': None,
            'all_tracked_bytes_exportable': False if counts['gap_count'] else None,
            'global_validation': 'NOT_RUN', 'ai_packet': 'NOT_BUILT', 'ai_packet_included': False,
            'ai_delivery': 'NOT_PERFORMED', 'ai_read': 'UNKNOWN', 'dependencies': 'NOT_GENERATED',
            'authority': 'DATA_ONLY', 'execution_authorized': False}


def native_frame_size(value):
    # Includes both Python adapter and JobHost/NativeClient envelopes. Reserve
    # enough space for the bridge's bounded request ID (UUIDs in NativeClient).
    result = {'schema': 'occ.native-durable-result.v1', 'operation': 'durable.repo.manifest', 'manifest': value}
    frames = ({'ok': True, 'result': result},
              {'ok': True, 'requestId': 'x' * 128, 'durable': result})
    return max(len(json.dumps(f, ensure_ascii=False, allow_nan=False).encode('utf-8')) for f in frames)


def page(store, namespace, sid, alias, profile, action, *, offset=0, limit=20, file_ordinal=None):
    if action not in {'INFO', 'ENTRIES', 'PARTS'}:
        raise ValueError('DURABLE_SCHEMA')
    strict_int(offset, 0, MAX_OFFSET)
    strict_int(limit, 1, 20)
    if file_ordinal is not None:
        strict_int(file_ordinal, 0, MAX_OFFSET)
        if action != 'PARTS':
            raise ValueError('DURABLE_SCHEMA')
    with read_view(store, namespace, sid, alias, profile) as (db, snap):
        value = metadata_info(snap, inventory(db, snap))
        value.update(scope={'action': action, 'file_ordinal': file_ordinal}, rows=[], offset=offset,
                     total=0, nextOffset=None, proof_scope='METADATA_ONLY_GLOBAL_NOT_RUN')
        if action == 'INFO':
            return value
        if action == 'ENTRIES':
            value['total'] = value['entry_count']
            cursor = db.execute('''SELECT e.*, (SELECT count(*) FROM repo_chunks c
                WHERE c.snapshot_id=e.snapshot_id AND c.path=e.path) AS chunk_count
                FROM repo_entries e WHERE e.snapshot_id=? ORDER BY e.ordinal LIMIT ? OFFSET ?''', (sid, limit, offset))
        else:
            where, params = 'c.snapshot_id=?', [sid]
            if file_ordinal is not None:
                if not db.execute('SELECT 1 FROM repo_entries WHERE snapshot_id=? AND ordinal=?', (sid, file_ordinal)).fetchone():
                    raise ValueError('REPO_PATH_OUTSIDE_SNAPSHOT')
                where += ' AND e.ordinal=?'
                params.append(file_ordinal)
            value['total'] = db.execute('SELECT count(*) FROM repo_chunks c JOIN repo_entries e ON c.snapshot_id=e.snapshot_id AND c.path=e.path WHERE ' + where, params).fetchone()[0]
            cursor = db.execute('''SELECT c.*,e.ordinal AS file_ordinal,e.size,e.file_hash
                FROM repo_chunks c JOIN repo_entries e ON c.snapshot_id=e.snapshot_id AND c.path=e.path
                WHERE ''' + where + ' ORDER BY e.ordinal,c.ordinal LIMIT ? OFFSET ?', (*params, limit, offset))
            value['proof_scope'] = 'RETURNED_PART_ROWS_ONLY_GLOBAL_NOT_RUN'
        for row in cursor:
            record = entry_record(row) if action == 'ENTRIES' else part_record(db, snap,
                {'ordinal': row['file_ordinal'], 'path': row['path'], 'size': row['size'], 'file_hash': row['file_hash']}, row)
            value['rows'].append(record)
            value['nextOffset'] = offset + len(value['rows']) if offset + len(value['rows']) < value['total'] else None
            if native_frame_size(value) > PAGE_FRAME_BYTES:
                value['rows'].pop()
                if not value['rows']:
                    raise ValueError('ROW_ENVELOPE_LIMIT')
                break
        value['nextOffset'] = offset + len(value['rows']) if offset + len(value['rows']) < value['total'] else None
        if native_frame_size(value) > PAGE_FRAME_BYTES:
            raise ValueError('ROW_ENVELOPE_LIMIT')
        return value


class Output:
    def __init__(self, path):
        self.path, self.hasher, self.bytes = path, hashlib.sha256(), 0
        self.stream = path.open('xb')

    def write(self, value):
        raw = canonical(value)
        self.stream.write(raw)
        self.hasher.update(raw)
        self.bytes += len(raw)

    def finish(self):
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()
        return {'path': self.path.name, 'bytes': self.bytes, 'sha256': self.hasher.hexdigest()}


def write_projection(db, snap, stage):
    counts = inventory(db, snap)
    binding = batch_binding(snap)
    manifest, parts = Output(stage / ARTIFACTS[0]), None
    part_count = raw_bytes = text_parts = 0
    try:
        parts = Output(stage / ARTIFACTS[1])
        for entry in entries(db, snap['id']):
            repo.pulse()
            manifest.write(entry_record(entry))
            if entry['state'] != 'INDEXED':
                continue
            oid = entry['oid']
            if (entry['kind'] != 'blob' or entry['mode'] not in {'100644', '100755'}
                    or not isinstance(entry['size'], int) or entry['size'] < 0
                    or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', oid)):
                raise ValueError('CONTEXT_CORRUPT')
            hasher = hashlib.sha256()
            blob = hashlib.new('sha1' if len(oid) == 40 else 'sha256')
            blob.update(b'blob ' + str(entry['size']).encode('ascii') + b'\0')
            end = chunk_count = 0
            for chunk in db.execute('SELECT * FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (snap['id'], entry['path'])):
                repo.pulse()
                if chunk['ordinal'] != chunk_count or chunk['byte_start'] != end:
                    raise ValueError('CONTEXT_CORRUPT')
                record = part_record(db, snap, entry, chunk)
                parts.write(record)
                hasher.update(chunk['raw'])
                blob.update(chunk['raw'])
                end = chunk['byte_end']
                chunk_count += 1
                raw_bytes += len(chunk['raw'])
                text_parts += int(record['text_eligible'])
            if (not chunk_count or entry['size'] == 0 and chunk_count != 1
                    or end != entry['size'] or hasher.hexdigest() != entry['file_hash']
                    or blob.hexdigest() != oid):
                raise ValueError('CONTEXT_CORRUPT')
            part_count += chunk_count
        if part_count != counts['part_count']:
            raise ValueError('CONTEXT_CORRUPT')
        outputs = [manifest.finish(), parts.finish()]
    finally:
        manifest.stream.close()
        if parts is not None:
            parts.stream.close()
    validation = {'schema': 'occ.repo-manifest-validation.v1', 'batch_id': digest(binding),
                  'state': 'PASS', 'proof_scope': 'ALL_INDEXED_CAPTURED_BYTES_AND_GIT_BLOB_OIDS',
                  **counts, 'raw_bytes': raw_bytes, 'text_part_count': text_parts,
                  'index_complete': True, 'raw_exact_for_indexed': True,
                  'text_exportable': text_parts == part_count,
                  'all_tracked_bytes_exportable': counts['gap_count'] == 0,
                  'outputs': outputs, 'device': 'NOT_RUN', 'head_freshness': 'NOT_CHECKED'}
    out = Output(stage / 'VALIDATION.json')
    try:
        out.write(validation)
        outputs = [*outputs, out.finish()]
    finally:
        out.stream.close()
    batch = {'schema': 'occ.repo-manifest-batch.v1', 'batch_id': digest(binding), 'binding': binding,
             **counts, 'inventory_complete': True, 'raw_exact_for_indexed': True,
             'all_tracked_bytes_exportable': counts['gap_count'] == 0,
             'text_exportable': text_parts == part_count, 'global_validation': 'PASS',
             'proof_scope': validation['proof_scope'], 'ai_packet': 'NOT_BUILT',
             'dependencies': 'NOT_GENERATED', 'outputs': outputs}
    out = Output(stage / 'BATCH.json')  # A success binding is always written last.
    try:
        out.write(batch)
        out.finish()
    finally:
        out.stream.close()
    return batch


def file_digest(path):
    h, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(64 * 1024), b''):
            h.update(raw)
            size += len(raw)
    return size, h.hexdigest()


def same_output(output, stage):
    if (output.is_symlink() or not output.is_dir()
            or set(p.name for p in output.iterdir()) != set(ARTIFACTS)):
        raise ValueError('MANIFEST_OUTPUT_CORRUPT')
    for name in ARTIFACTS:
        path = output / name
        if path.is_symlink() or not path.is_file() or file_digest(path) != file_digest(stage / name):
            raise ValueError('MANIFEST_OUTPUT_CORRUPT')


def publish(store, namespace, sid, alias, profile, output):
    output = Path(output)
    if not output.is_absolute() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError('MANIFEST_OPERATOR_OUTPUT_REQUIRED')
    if output.resolve().is_relative_to(Path(profile['root']).resolve()) or output.resolve().is_relative_to(Path(store).resolve()):
        raise ValueError('MANIFEST_OUTPUT_MUST_BE_OUTSIDE_SOURCE_AND_STORE')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.occ-manifest-', dir=output.parent))
    try:
        with read_view(store, namespace, sid, alias, profile) as (db, snap):
            batch = write_projection(db, snap, stage)
        reused = output.exists()
        if reused:
            same_output(output, stage)
        else:
            stage.rename(output)
        return {'batch_id': batch['batch_id'], 'state': 'PASS', 'reused': reused}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        from native_adapter import operator_profile
        if not args.profile.is_absolute():
            raise ValueError('DURABLE_ABSOLUTE_OPERATOR_PATH_REQUIRED')
        profile, _ = operator_profile(args.profile)
        source = profile.get('repositories', {}).get(args.repository)
        if source is None:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        result = publish(Path(profile['store']), source['namespace'], args.snapshot,
                         args.repository, source, args.output)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        code = str(exc) if re.fullmatch(r'[A-Z_]{1,100}', str(exc)) else 'MANIFEST_OPERATION_FAILED'
        print(json.dumps({'state': 'FAILED', 'error': code}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
