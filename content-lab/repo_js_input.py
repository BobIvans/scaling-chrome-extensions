"""Validate PR005 facts and captured bytes without changing their owner."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3

from automation_core import digest
import repo_context as repo
import repo_manifest
from repo_artifacts import oid_hasher, safe_path

EXTENSIONS = frozenset({'.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.mts', '.cts'})
FACT_SCHEMA = json.loads((Path(__file__).parent / 'js-contracts/ELIGIBILITY.schema.json').read_text('utf8'))


def installed_fact_owner():
    """Only load the trusted application's PR005 owner, never cwd/PYTHONPATH."""
    path = Path(__file__).resolve().parent / 'source_eligibility.py'
    if not path.exists():
        return None
    path = safe_path(path)
    spec = importlib.util.spec_from_file_location('_occ_js_pr005_owner', path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    if (owner.SCHEMA != 'occ.format-eligibility.v1' or owner.CLASSIFIER_VERSION != 'utf8-controls-strict-lfs3.v1'
            or owner.WIRE_FIELDS != set(FACT_SCHEMA['properties'])):
        raise ValueError('ELIGIBILITY_OWNER_VERSION_MISMATCH')
    return owner


FACT_OWNER, FACT_OWNER_ERROR = None, None
try:
    FACT_OWNER = installed_fact_owner()
except ValueError as exc:
    FACT_OWNER_ERROR = str(exc)


def extension(path):
    # Git paths are case sensitive, including their suffixes.
    return Path(path).suffix


def schema_valid(value, schema):
    """The shipped PR005 record schema uses this small JSON Schema subset only."""
    types = {'string': lambda x: isinstance(x, str), 'object': lambda x: isinstance(x, dict),
             'array': lambda x: isinstance(x, list), 'null': lambda x: x is None}
    kind = schema.get('type')
    if kind is not None and not any(types[k](value) for k in (kind if isinstance(kind, list) else [kind])):
        return False
    if 'const' in schema and value != schema['const'] or 'enum' in schema and value not in schema['enum']:
        return False
    if isinstance(value, str) and 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
        return False
    if isinstance(value, dict):
        if not set(schema.get('required', [])).issubset(value):
            return False
        if schema.get('additionalProperties') is False and set(value) - set(schema.get('properties', {})):
            return False
        if any(not schema_valid(v, schema['properties'][k]) for k, v in value.items() if k in schema.get('properties', {})):
            return False
    if isinstance(value, list):
        if schema.get('uniqueItems') and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            return False
        if 'items' in schema and any(not schema_valid(x, schema['items']) for x in value):
            return False
    if 'oneOf' in schema and sum(schema_valid(value, s) for s in schema['oneOf']) != 1:
        return False
    return True


def eligibility(db, snap, entry, legacy=False):
    if FACT_OWNER_ERROR:
        return FACT_OWNER_ERROR
    try:
        analysis = json.loads(entry['analysis'] or '{}')
        if not isinstance(analysis, dict):
            raise ValueError()
    except (ValueError, TypeError):
        return 'ELIGIBILITY_FACTS_INVALID'
    facts = analysis.get('format_eligibility')
    if facts is None:
        if not legacy:
            return 'ELIGIBILITY_FACTS_UNAVAILABLE'
        if entry['state'] != 'INDEXED' or entry['kind'] != 'blob' or entry['mode'] not in {'100644', '100755'}:
            return 'RAW_BYTES_UNAVAILABLE'
        bad = db.execute('SELECT 1 FROM repo_chunks WHERE snapshot_id=? AND path=? AND item_id IS NULL LIMIT 1',
                         (snap['id'], entry['path'])).fetchone()
        return 'LEGACY_TEXT_NOT_ELIGIBLE' if bad and entry['size'] else None
    if not isinstance(facts, dict):
        return 'ELIGIBILITY_FACTS_INVALID'
    if facts.get('schema') != 'occ.format-eligibility.v1' or facts.get('classifier_version') != 'utf8-controls-strict-lfs3.v1':
        return 'ELIGIBILITY_VERSION_MISMATCH'
    # PR005 storage adds a private _binding receipt. Its public projection is
    # the schema contract; do not confuse the two or strip unknown metadata.
    wire = {key: value for key, value in facts.items() if key != '_binding'}
    if not schema_valid(wire, FACT_SCHEMA):
        return 'ELIGIBILITY_FACTS_INVALID'
    bound = {'snapshot_id': snap['id'], 'ordinal': str(entry['ordinal']), 'path': entry['path'],
             'mode': entry['mode'], 'kind': entry['kind'], 'git_oid': entry['oid'],
             'git_size': None if entry['size'] is None else str(entry['size']),
             'disposition': entry['state'], 'legacy_reason': entry['reason'], 'file_sha256': entry['file_hash']}
    if any(wire[key] != value for key, value in bound.items()):
        return 'ELIGIBILITY_BINDING_MISMATCH'
    if FACT_OWNER is not None:
        if FACT_OWNER.facts_status(snap['id'], entry) != 'SUPPORTED':
            return 'ELIGIBILITY_FACTS_INVALID'
        facts = FACT_OWNER.project_facts(snap['id'], entry)
        if not schema_valid(facts, FACT_SCHEMA) or facts != wire:
            return 'ELIGIBILITY_FACTS_INVALID'
    elif '_binding' in facts:
        return 'ELIGIBILITY_OWNER_UNAVAILABLE'
    if facts['raw_integrity'] == 'FAIL' or facts['raw_capture'] == 'CORRUPT':
        return 'RAW_INTEGRITY_FAIL'
    if (entry['state'] != 'INDEXED' or entry['kind'] != 'blob'
            or entry['mode'] not in {'100644', '100755'} or facts['raw_capture'] != 'RECORDED'):
        return 'RAW_BYTES_UNAVAILABLE'
    if facts['text_eligibility'] != 'ELIGIBLE' or facts['format_kind'] not in {'UTF8_TEXT_CANDIDATE', 'EMPTY'}:
        return 'TEXT_NOT_ELIGIBLE' if facts['text_eligibility'] != 'UNKNOWN' else 'ELIGIBILITY_UNKNOWN'
    return None


@contextmanager
def read_snapshot(store, source, alias, snapshot_id, control):
    database = safe_path(Path(store) / 'content.sqlite3')
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    previous = repo._progress_callback
    repo._progress_callback = control.pulse
    try:
        db.set_progress_handler(lambda: (control.pulse() or 0), 10000)
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        snap = repo.load_snapshot(db, source['namespace'], snapshot_id)
        if snap['alias'] != alias or json.loads(snap['profile']) != source:
            raise ValueError('PROFILE_CHANGED')
        if snap['id'] != digest({'alias': alias, 'profile': source, 'head': snap['head'], 'tree': snap['tree']}):
            raise ValueError('SNAPSHOT_BINDING_MISMATCH')
        inventory = repo_manifest.inventory(db, snap)
        proof = repo.verify_roundtrip_db(db, snap)
        if not proof['exact_for_indexed']:
            raise ValueError('RAW_INTEGRITY_FAIL')
        snap['inventory_proof'], snap['raw_proof'] = inventory, proof
        yield db, snap
    except sqlite3.OperationalError as exc:
        if control.reason:
            raise ValueError(control.reason) from exc
        raise
    finally:
        repo._progress_callback = previous
        db.close()


def reconstruct(db, snap, entry, limit, control):
    if type(entry['size']) is not int or entry['size'] < 0:
        raise ValueError('RAW_INTEGRITY_FAIL')
    if entry['size'] > limit:
        return None, 'FILE_PARSE_BUDGET'
    raw, position, count = bytearray(), 0, 0
    git_hash = oid_hasher(entry['oid'], entry['size'])
    for chunk in db.execute('SELECT * FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal',
                            (snap['id'], entry['path'])):
        control.pulse()
        part = chunk['raw']
        if (not isinstance(part, bytes) or chunk['ordinal'] != count or chunk['byte_start'] != position
                or chunk['byte_end'] != position + len(part) or chunk['byte_end'] > entry['size']
                or len(raw) + len(part) > limit or entry['size'] and not part
                or chunk['revision'] != digest([chunk['logical_id'], entry['file_hash'], repo.sha(part),
                                                chunk['byte_start'], chunk['byte_end']])):
            raise ValueError('RAW_INTEGRITY_FAIL')
        raw.extend(part); git_hash.update(part)
        count, position = count + 1, chunk['byte_end']
    if not count or position != entry['size'] or repo.sha(raw) != entry['file_hash'] or git_hash.hexdigest() != entry['oid']:
        raise ValueError('RAW_INTEGRITY_FAIL')
    try:
        raw.decode('utf8')
    except UnicodeDecodeError:
        return None, 'CAPTURE_NOT_UTF8'
    return bytes(raw), None


def snapshot_digest(db, snap, control):
    """Streaming cache binding includes the complete manifest and eligibility facts."""
    hasher = hashlib.sha256()
    for row in db.execute('SELECT * FROM repo_entries WHERE snapshot_id=? ORDER BY path COLLATE BINARY', (snap['id'],)):
        control.pulse()
        # working_state is observational and cannot influence captured syntax.
        data = {key: row[key] for key in row.keys() if key != 'working_state'}
        hasher.update(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8'))
        hasher.update(b'\n')
    return hasher.hexdigest()
