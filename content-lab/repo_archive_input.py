"""Archive adapter for the installed PR-002 manifest owner; no second format."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile

from automation_core import digest, load_json
from native_adapter import operator_profile
import repo_context as repo
import repo_manifest as owner
from repo_artifacts import file_proof, outside, safe_path

METADATA = ('BATCH.json', 'REPO_MANIFEST.jsonl', 'PARTS_INDEX.jsonl', 'VALIDATION.json')


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
        if snap['id'] != digest({'alias': alias, 'profile': source, 'head': snap['head'], 'tree': snap['tree']}):
            raise ValueError('BATCH_BINDING_MISMATCH')
        validate_snapshot(db, snap)
        yield db, snap
    finally:
        db.close()


def validate_snapshot(db, snap):
    try:
        owner.inventory(db, snap)
    except ValueError as exc:
        raise ValueError('MANIFEST_UNVERIFIED') from exc
    proof = repo.verify_roundtrip_db(db, snap)
    if not proof['exact_for_indexed']:
        raise ValueError('PAYLOAD_HASH_MISMATCH')
    return proof


def entry_rows(db, snap):
    for row in owner.entries(db, snap['id']):
        yield owner.entry_record(row)


def part_rows(db, snap, *, raw=False, order='source'):
    ordering = 'e.ordinal,c.ordinal' if order == 'source' else 'c.revision'
    query = '''SELECT c.*,e.ordinal AS file_ordinal,e.file_hash,e.size FROM repo_chunks c
               JOIN repo_entries e ON e.snapshot_id=c.snapshot_id AND e.path=c.path
               WHERE c.snapshot_id=? AND e.state='INDEXED' ORDER BY ''' + ordering
    for row in db.execute(query, (snap['id'],)):
        entry = {'ordinal': row['file_ordinal'], 'path': row['path'],
                 'size': row['size'], 'file_hash': row['file_hash']}
        value = owner.part_record(db, snap, entry, row)
        yield (value, row['raw']) if raw else value


def normalized_batch(directory):
    batch = load_json(Path(directory) / 'BATCH.json')
    proof = load_json(Path(directory) / 'VALIDATION.json')
    # This field is an internal adapter convenience, never rewritten to BATCH.
    return dict(batch, captured_bytes=proof['raw_bytes'])


def verify_manifest(db, snap, source, directory):
    directory = safe_path(directory, directory=True)
    expected = snap.get('_manifest_expected')
    if expected is None:
        # Reuse the actual owner's full projection/proof. The temporary files
        # are bounded-memory derivable metadata, not a new source database.
        with tempfile.TemporaryDirectory(prefix='occ-archive-proof-') as temp:
            stage = Path(temp)
            owner.write_projection(db, snap, stage)
            expected = {name: file_proof(stage / name) for name in METADATA}
            batch = normalized_batch(stage)
        snap['_manifest_expected'], snap['_manifest_batch'] = expected, batch
    for name in METADATA:
        if file_proof(directory / name) != expected[name]:
            raise ValueError('BATCH_BINDING_MISMATCH' if name == 'BATCH.json' else 'MANIFEST_UNVERIFIED')
    return dict(snap['_manifest_batch'])


def write_manifest(store, alias, source, snapshot_id, output):
    output = outside(output, source['root'], store)
    owner.publish(store, source['namespace'], snapshot_id, alias, source, output)
    return normalized_batch(output)
