"""Frozen, fully verified raw repository manifests in the existing SQLite scope.

Foreground CLI only. No source checkout, AI packet, or new source ledger.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from automation_core import digest, load_json
from native_adapter import operator_profile
import repo_context as repo
from repo_artifacts import (atomic_file, atomic_json, file_proof, json_bytes,
                            outside, process_lock, safe_path, sync_dir)

METADATA = ('BATCH.json', 'REPO_MANIFEST.jsonl', 'PARTS_INDEX.jsonl', 'VALIDATION.json')
PROOF_SCOPE = 'FULL_CAPTURED_SQLITE_SNAPSHOT_V1'
HEX = re.compile(r'[0-9a-f]{64}')


def operator_scope(profile_path, alias):
    profile, _ = operator_profile(safe_path(profile_path))
    source = profile.get('repositories', {}).get(alias)
    if source is None or source['namespace'] not in profile['namespaces']:
        raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
    store = safe_path(profile['store'], directory=True)
    safe_path(source['root'], directory=True)
    if store.is_relative_to(Path(source['root']).resolve()):
        raise ValueError('STORE_MUST_BE_OUTSIDE_SOURCE')
    return store, source


@contextmanager
def snapshot_view(store, source, alias, snapshot_id):
    database = safe_path(Path(store) / 'content.sqlite3')
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute('BEGIN')
        snap = repo.load_snapshot(db, source['namespace'], snapshot_id)
        if snap['alias'] != alias or json.loads(snap['profile']) != source:
            raise ValueError('PROFILE_CHANGED')
        # This proof is reusable only inside this immutable read transaction.
        snap['_raw_proof'] = validate_snapshot(db, snap)
        yield db, snap
    finally:
        db.close()


def validate_snapshot(db, snap):
    count, maximum = db.execute('SELECT count(*),max(ordinal) FROM repo_entries WHERE snapshot_id=?', (snap['id'],)).fetchone()
    pending = db.execute("SELECT count(*) FROM repo_entries WHERE snapshot_id=? AND state='PENDING'", (snap['id'],)).fetchone()[0]
    if (snap['cursor'] != snap['total'] or count != snap['total'] or pending
            or maximum != (count - 1 if count else None)):
        raise ValueError('MANIFEST_UNVERIFIED')
    if db.execute("SELECT 1 FROM repo_entries WHERE snapshot_id=? AND (ordinal<0 OR state NOT IN ('INDEXED','EXCLUDED','ERROR') OR (state!='INDEXED' AND reason IS NULL)) LIMIT 1", (snap['id'],)).fetchone():
        raise ValueError('MANIFEST_UNVERIFIED')
    proof = repo.verify_roundtrip_db(db, snap)
    if not proof['exact_for_indexed']:
        raise ValueError('PAYLOAD_HASH_MISMATCH')
    if db.execute('SELECT revision FROM repo_chunks WHERE snapshot_id=? GROUP BY revision HAVING count(*)!=1 LIMIT 1', (snap['id'],)).fetchone():
        raise ValueError('PART_ID_NOT_UNIQUE')
    return proof


def binding(snap, source):
    return {'schema': 'occ.repo-manifest-binding.v1', 'snapshot_id': snap['id'],
            'namespace': snap['namespace'], 'repository': snap['alias'],
            'repo_sha': snap['head'], 'tree_sha': snap['tree'],
            'profile_revision': digest(source), 'goal_revision': None,
            'grouping_policy': 'RAW_CHUNK_MAPPING_V1',
            'parser_policy': 'PRESERVED_ANALYSIS_KINDS_NO_NEW_PARSE',
            'historical_scanner_build': 'UNKNOWN',
            'export_policy': 'LOCAL_CAPTURED_CHUNK_METADATA_V1'}


def entry_rows(db, snap):
    query = '''SELECT e.*, (SELECT count(*) FROM repo_chunks c WHERE c.snapshot_id=e.snapshot_id AND c.path=e.path) AS chunk_count
               FROM repo_entries e WHERE e.snapshot_id=? ORDER BY e.ordinal'''
    for row in db.execute(query, (snap['id'],)):
        yield {'schema': 'occ.repo-entry-manifest.v1', 'snapshot_id': snap['id'],
               'ordinal': row['ordinal'], 'path': row['path'], 'mode': row['mode'],
               'git_type': row['kind'], 'git_oid': row['oid'], 'size': row['size'],
               'state': row['state'], 'reason': row['reason'], 'file_sha256': row['file_hash'],
               'parser': json.loads(row['analysis'] or '{}').get('parser'),
               'chunk_count': row['chunk_count'], 'part_locator': {'file_ordinal': row['ordinal']},
               'packet_coverage': 'NOT_BUILT'}


def part_rows(db, snap, *, raw=False, order='source'):
    ordering = 'e.ordinal,c.ordinal' if order == 'source' else 'c.revision'
    query = '''SELECT c.*,e.ordinal AS file_ordinal,e.file_hash FROM repo_chunks c
               JOIN repo_entries e ON e.snapshot_id=c.snapshot_id AND e.path=c.path
               WHERE c.snapshot_id=? AND e.state='INDEXED' ORDER BY ''' + ordering
    for row in db.execute(query, (snap['id'],)):
        if not HEX.fullmatch(row['revision']) or not HEX.fullmatch(row['logical_id']):
            raise ValueError('PART_ID_REQUIRED')
        try:
            row['raw'].decode('utf-8')
            text = True
        except UnicodeDecodeError:
            text = False
        value = {'schema': 'occ.repo-part-index.v1', 'snapshot_id': snap['id'],
                 'file_ordinal': row['file_ordinal'], 'path': row['path'],
                 'chunk_ordinal': row['ordinal'], 'part_id': row['revision'],
                 'logical_id': row['logical_id'], 'revision': row['revision'],
                 'source_start': row['byte_start'], 'source_end': row['byte_end'],
                 'bytes': len(row['raw']), 'sha256': repo.sha(row['raw']),
                 'file_sha256': row['file_hash'], 'text_eligible': text,
                 'dependency_status': 'NOT_GENERATED'}
        yield (value, row['raw']) if raw else value


def rows_proof(rows):
    size, hasher = 0, hashlib.sha256()
    for row in rows:
        encoded = json_bytes(row)
        size += len(encoded)
        hasher.update(encoded)
    return {'bytes': size, 'sha256': hasher.hexdigest()}


def validation(db, snap):
    proof = snap.get('_raw_proof') or repo.verify_roundtrip_db(db, snap)
    parts, size = db.execute('SELECT count(*),coalesce(sum(length(raw)),0) FROM repo_chunks WHERE snapshot_id=?', (snap['id'],)).fetchone()
    return {'schema': 'occ.repo-manifest-validation.v1', 'state': 'PASS',
            'proof_scope': PROOF_SCOPE, 'snapshot_id': snap['id'],
            'inventory_complete': True, 'raw_exact_for_indexed': True,
            'all_tracked_bytes_exportable': proof['all_tracked_bytes_exportable'],
            'entry_count': snap['total'], 'indexed_count': proof['indexed'],
            'gap_count': snap['total'] - proof['indexed'], 'part_count': parts,
            'captured_bytes': size, 'git_oid_verified': True,
            'ai_delivery': 'NOT_PERFORMED', 'ai_read': 'UNKNOWN',
            'dependencies': 'NOT_GENERATED'}


def batch_value(db, snap, source, outputs):
    proof = validation(db, snap)
    bind = binding(snap, source)
    value = {k: proof[k] for k in ('entry_count', 'indexed_count', 'gap_count', 'part_count',
                                  'captured_bytes', 'inventory_complete', 'raw_exact_for_indexed',
                                  'all_tracked_bytes_exportable', 'proof_scope')}
    value.update(schema='occ.repo-manifest-batch.v1', batch_id=digest(bind), binding=bind,
                 outputs=outputs, ai_packet='NOT_BUILT', dependencies='NOT_GENERATED')
    return value


def verify_manifest(db, snap, source, directory):
    directory = safe_path(directory, directory=True)
    outputs = []
    for name, rows in [('REPO_MANIFEST.jsonl', entry_rows(db, snap)), ('PARTS_INDEX.jsonl', part_rows(db, snap))]:
        expected = rows_proof(rows)
        if file_proof(directory / name) != expected:
            raise ValueError('MANIFEST_UNVERIFIED')
        outputs.append(dict(path=name, **expected))
    batch = load_json(directory / 'BATCH.json')
    if batch != batch_value(db, snap, source, outputs):
        raise ValueError('BATCH_BINDING_MISMATCH')
    if load_json(directory / 'VALIDATION.json') != validation(db, snap):
        raise ValueError('MANIFEST_UNVERIFIED')
    return batch


def write_manifest(store, alias, source, snapshot_id, output):
    output = outside(output, source['root'], store)
    output.parent.mkdir(parents=True, exist_ok=True)
    with process_lock(output.with_name('.' + output.name + '.lock')):
        with snapshot_view(store, source, alias, snapshot_id) as (db, snap):
            if output.exists():
                return verify_manifest(db, snap, source, output)
            staging = output.with_name('.' + output.name + '.partial')
            safe_path(staging, directory=True).mkdir(exist_ok=True, mode=0o700)
            outputs = []
            for name, rows in [('REPO_MANIFEST.jsonl', entry_rows(db, snap)), ('PARTS_INDEX.jsonl', part_rows(db, snap))]:
                with atomic_file(staging / name) as stream:
                    for row in rows:
                        stream.write(json_bytes(row))
                outputs.append(dict(path=name, **file_proof(staging / name)))
            atomic_json(staging / 'VALIDATION.json', validation(db, snap))
            atomic_json(staging / 'BATCH.json', batch_value(db, snap, source, outputs))
            result = verify_manifest(db, snap, source, staging)
            staging.rename(output)
            sync_dir(output.parent)
            return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        store, source = operator_scope(args.profile, args.repository)
        result = write_manifest(store, args.repository, source, args.snapshot, args.output)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'state': 'BLOCKED', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
