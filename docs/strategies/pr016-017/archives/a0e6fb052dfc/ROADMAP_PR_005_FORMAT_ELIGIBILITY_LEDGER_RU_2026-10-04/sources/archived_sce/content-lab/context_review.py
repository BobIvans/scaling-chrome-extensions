"""Immutable review metadata in Content Lab's existing store; no action grants.

Reviews are untrusted claims. A DONE disposition never closes a finding. Source
heads are checked from the canonical store on every read, including after restart.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time

from automation_core import connection, context_pack, digest, identifier, strict_int

MAX_BYTES = 128_000
HASH = re.compile(r'^[0-9a-f]{64}$')
SHA = re.compile(r'^[0-9a-f]{40}$')
CLASSES = {'CODE_DEFECT', 'MISSING_EVIDENCE', 'ENVIRONMENT_BLOCKER', 'PROPOSAL_ONLY'}


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('REVIEW_SCHEMA')


def hash_value(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError('REVIEW_HASH_REQUIRED')
    return value


def bounded_text(value, maximum=2000):
    if not isinstance(value, str) or '\0' in value or len(value.encode('utf-8')) > maximum:
        raise ValueError('REVIEW_BOUNDED_TEXT_REQUIRED')
    return value


def strict_json(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError('REVIEW_INPUT_LIMIT')
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('REVIEW_DUPLICATE_KEY')
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError('REVIEW_NONFINITE_NUMBER')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)


def db_for(store):
    db = connection(store)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS review_sessions(
          id TEXT PRIMARY KEY, namespace TEXT NOT NULL, payload TEXT NOT NULL,
          payload_hash TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS review_results(
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL, payload TEXT NOT NULL,
          payload_hash TEXT NOT NULL, supersedes TEXT, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS review_heads(
          session_id TEXT PRIMARY KEY, review_id TEXT NOT NULL);
    ''')
    return db


def create_session(store, namespace, ids, goal, base_repo_sha=None, *,
                   repo_snapshot_id=None, request_meta=None, repo_binding=None):
    identifier(namespace)
    bounded_text(goal, 8000)
    if base_repo_sha is not None and (not isinstance(base_repo_sha, str) or not SHA.fullmatch(base_repo_sha)):
        raise ValueError('REVIEW_BASE_SHA_REQUIRED')
    # Use the canonical export owner. Identity ignores order of a selected set.
    pack = context_pack(store, namespace, sorted(ids), max_bytes=48_000)
    refs = sorted(({'source_key': item['source_key'], 'item_id': item['id'],
                    'sha256': item['input_sha256']} for item in pack['items']),
                  key=lambda ref: ref['source_key'])
    payload = {'schema': 'occ.review-session.v1', 'namespace': namespace,
               'snapshot_sha256': digest(refs), 'sources': refs,
               'goal_sha256': hashlib.sha256(goal.encode('utf-8')).hexdigest(),
               'export_bundle_id': pack['sha256'], 'export_sha256': pack['sha256'],
               'base_repo_sha': base_repo_sha, 'evidence_refs': []}
    if repo_snapshot_id is not None:
        from repo_context import bind_ids, verify_binding
        binding = repo_binding or bind_ids(store, namespace, repo_snapshot_id, ids)
        verified = verify_binding(store, binding)
        if verified['state'] != 'VERIFIED':
            raise ValueError('SOURCE_DRIFT')
        if base_repo_sha is not None and base_repo_sha != binding['repo_sha']:
            raise ValueError('REVIEW_REPO_SHA_MISMATCH')
        payload.update(base_repo_sha=binding['repo_sha'], repo_binding=binding)
    if request_meta is not None:
        payload['request_meta'] = request_meta
    strict_json(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    session_id = digest(payload)
    db = db_for(store)
    try:
        with db:
            db.execute('INSERT OR IGNORE INTO review_sessions VALUES (?,?,?,?,?)',
                       (session_id, namespace, json.dumps(payload, ensure_ascii=False), session_id, time.time()))
    finally:
        db.close()
    return get_session(store, namespace, session_id)


def load_session(db, namespace, session_id):
    identifier(namespace)
    hash_value(session_id)
    row = db.execute('SELECT * FROM review_sessions WHERE id=? AND namespace=?',
                     (session_id, namespace)).fetchone()
    if row is None:
        raise ValueError('REVIEW_SESSION_OUTSIDE_SCOPE')
    payload = strict_json(row['payload'].encode('utf-8'))
    if digest(payload) != row['payload_hash'] or row['payload_hash'] != session_id:
        raise ValueError('REVIEW_SESSION_CORRUPT')
    return row, payload


def binding_state(db, payload):
    missing, changed = [], []
    for ref in payload['sources']:
        row = db.execute('SELECT item_id,raw_hash,present FROM sync_heads WHERE namespace=? AND source_key=?',
                         (payload['namespace'], ref['source_key'])).fetchone()
        if row is None or not row['present']:
            missing.append(ref['source_key'])
        elif row['item_id'] != ref['item_id'] or row['raw_hash'] != ref['sha256']:
            changed.append(ref['source_key'])
        else:
            item = db.execute('SELECT payload FROM items WHERE id=?', (ref['item_id'],)).fetchone()
            if item is None:
                missing.append(ref['source_key'])
            else:
                source = strict_json(item['payload'].encode('utf-8'))
                if (source.get('input_sha256') != ref['sha256'] or
                        'repo_binding' in payload and
                        hashlib.sha256(source.get('text', '').encode('utf-8')).hexdigest() != ref['sha256']):
                    changed.append(ref['source_key'])
    return ('NEEDS_CONTEXT' if missing else 'STALE' if changed else 'EXPORTED'), missing, changed


def get_session(store, namespace, session_id, *, details=False, repo_profiles=None):
    db = db_for(store)
    try:
        row, payload = load_session(db, namespace, session_id)
        state, missing, changed = binding_state(db, payload)
        repo_state = {'state': 'UNBOUND', 'source_bytes_verified': False}
        if 'repo_binding' in payload:
            from repo_context import verify_binding, db_for as repo_db, load_snapshot
            authorized = True
            if repo_profiles is not None:
                context_db = repo_db(store)
                try:
                    snap = load_snapshot(context_db, namespace, payload['repo_binding']['snapshot_id'])
                    authorized = repo_profiles.get(snap['alias']) == json.loads(snap['profile'])
                finally:
                    context_db.close()
            repo_state = (verify_binding(store, payload['repo_binding']) if authorized else
                          {'state': 'NEEDS_CONTEXT', 'missing': ['REPO_PROFILE_REVOKED'], 'changed': [], 'source_bytes_verified': False})
            missing += repo_state['missing']
            changed += repo_state['changed']
            if missing:
                state = 'NEEDS_CONTEXT'
            elif changed:
                state = 'STALE'
        head = db.execute('SELECT review_id FROM review_heads WHERE session_id=?', (session_id,)).fetchone()
        result = {'schema': 'occ.review-status.v1', 'session_id': session_id,
                  'namespace': namespace, 'snapshot_sha256': payload['snapshot_sha256'],
                  'sources': payload['sources'], 'goal_sha256': payload['goal_sha256'],
                  'export_bundle_id': payload['export_bundle_id'], 'export_sha256': payload['export_sha256'],
                  'base_repo_sha': payload['base_repo_sha'], 'created': row['created'],
                  'state': state, 'missing_dependencies': missing, 'changed_dependencies': changed,
                  'review_id': head['review_id'] if head else None,
                  'authority': 'DATA_ONLY', 'execution_authorized': False,
                  'dispatch_allowed': False, 'approvals_restored': False, 'timers_restored': False}
        result['repo_binding'] = repo_state
        if details:
            result['request_meta'] = payload.get('request_meta')
        if head:
            review = db.execute('SELECT * FROM review_results WHERE id=? AND session_id=?',
                                (head['review_id'], session_id)).fetchone()
            if review is None:
                raise ValueError('REVIEW_RESULT_CORRUPT')
            data = strict_json(review['payload'].encode('utf-8'))
            if digest(data) != review['payload_hash'] or review['id'] != review['payload_hash']:
                raise ValueError('REVIEW_RESULT_CORRUPT')
            if state == 'EXPORTED':
                result['state'] = 'NEEDS_CONTEXT' if data['coverage']['missing_dependencies'] else 'NEEDS_REVIEW'
            result['supersedes'] = review['supersedes']
            result['findings'] = [{'finding_id': f['finding_id'], 'classification': f['classification'],
                                  'state': 'STATIC_CANDIDATE' if f['classification'] == 'CODE_DEFECT' else 'NEEDS_REVIEW',
                                  'closed': False, 'evidence_verified': False} for f in data['findings']]
            if details:
                result['coverage'] = data['coverage']
                result['finding_details'] = data['findings']
                covered = set(data['coverage']['reviewed'] + data['coverage']['not_reviewed'])
                result['unaccounted_sources'] = [s['source_key'] for s in payload['sources'] if s['source_key'] not in covered]
        if payload.get('request_meta', {}).get('selection', {}).get('coverage') == 'PARTIAL' and result['state'] in {'EXPORTED', 'NEEDS_REVIEW'}:
            result['state'] = 'NEEDS_CONTEXT'
        result['next_step'] = ('RESCAN_AND_EXPORT' if result['state'] in {'STALE', 'NEEDS_CONTEXT'} else
                               'VERIFY_CRITERION_EVIDENCE' if head else 'IMPORT_REVIEW')
        return result
    finally:
        db.close()


def list_sessions(store, namespace, limit=20, *, repo_profiles=None):
    identifier(namespace)
    strict_int(limit, 1, 20)
    db = db_for(store)
    try:
        ids = [r[0] for r in db.execute('SELECT id FROM review_sessions WHERE namespace=? ORDER BY created DESC,id LIMIT ?',
                                      (namespace, limit))]
    finally:
        db.close()
    return [get_session(store, namespace, session_id, repo_profiles=repo_profiles) for session_id in ids]


def validate_review(value):
    # Bound the object path as well as the file/native transport path.
    strict_json(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'))
    exact(value, {'schema', 'session_id', 'snapshot_sha256', 'sources', 'base_repo_sha', 'coverage', 'findings'})
    if value['schema'] != 'occ.review-result.v1':
        raise ValueError('REVIEW_SCHEMA')
    hash_value(value['session_id'])
    hash_value(value['snapshot_sha256'])
    if not isinstance(value['sources'], list) or not 1 <= len(value['sources']) <= 10:
        raise ValueError('REVIEW_SOURCE_LIMIT')
    for ref in value['sources']:
        exact(ref, {'source_key', 'item_id', 'sha256'})
        bounded_text(ref['source_key'], 1000)
        hash_value(ref['item_id'])
        hash_value(ref['sha256'])
    exact(value['coverage'], {'reviewed', 'not_reviewed', 'missing_dependencies'})
    for refs in value['coverage'].values():
        if not isinstance(refs, list) or len(refs) > 50:
            raise ValueError('REVIEW_COVERAGE_LIMIT')
        for ref in refs:
            bounded_text(ref, 1000)
    covered = value['coverage']['reviewed'] + value['coverage']['not_reviewed']
    if len(covered) != len(set(covered)) or any(key not in {ref['source_key'] for ref in value['sources']} for key in covered):
        raise ValueError('REVIEW_COVERAGE_BINDING')
    if not isinstance(value['findings'], list) or len(value['findings']) > 50:
        raise ValueError('REVIEW_FINDINGS_LIMIT')
    finding_ids = set()
    for finding in value['findings']:
        exact(finding, {'finding_id', 'classification', 'disposition', 'source_key',
                        'source_sha256', 'criterion', 'evidence_refs', 'duplicate_of', 'supersedes'})
        identifier(finding['finding_id'])
        if finding['finding_id'] in finding_ids:
            raise ValueError('REVIEW_DUPLICATE_FINDING')
        finding_ids.add(finding['finding_id'])
        if finding['classification'] not in CLASSES or finding['disposition'] not in {'OPEN', 'STATIC_CANDIDATE', 'DONE'}:
            raise ValueError('REVIEW_FINDING_CLASS')
        bounded_text(finding['criterion'])
        if not any(ref['source_key'] == finding['source_key'] and ref['sha256'] == finding['source_sha256'] for ref in value['sources']):
            raise ValueError('REVIEW_FINDING_SOURCE_BINDING')
        if not isinstance(finding['evidence_refs'], list) or len(finding['evidence_refs']) > 10:
            raise ValueError('REVIEW_EVIDENCE_LIMIT')
        for ref in finding['evidence_refs']:
            exact(ref, {'kind', 'sha256'})
            if ref['kind'] not in {'TEST_RECEIPT', 'EXACT_SOURCE_REVIEW', 'DEVICE_RECEIPT', 'MODEL_CLAIM'}:
                raise ValueError('REVIEW_EVIDENCE_KIND')
            hash_value(ref['sha256'])
        for field in ('duplicate_of', 'supersedes'):
            if finding[field] is not None:
                identifier(finding[field])
    return value


def import_review(store, namespace, value, *, repo_profiles=None):
    value = validate_review(value)
    db = db_for(store)
    review_id = digest(value)
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            _, session = load_session(db, namespace, value['session_id'])
            for field in ('snapshot_sha256', 'sources', 'base_repo_sha'):
                if value[field] != session[field]:
                    raise ValueError('REVIEW_BINDING_MISMATCH')
            prior = db.execute('SELECT review_id FROM review_heads WHERE session_id=?', (value['session_id'],)).fetchone()
            existing = db.execute('SELECT id FROM review_results WHERE id=?', (review_id,)).fetchone()
            if existing is None:
                db.execute('INSERT INTO review_results VALUES (?,?,?,?,?,?)',
                           (review_id, value['session_id'], json.dumps(value, ensure_ascii=False), review_id,
                            prior['review_id'] if prior else None, time.time()))
                db.execute('INSERT INTO review_heads VALUES (?,?) ON CONFLICT(session_id) DO UPDATE SET review_id=excluded.review_id',
                           (value['session_id'], review_id))
            # Old replay does not roll the current head backwards.
    finally:
        db.close()
    result = get_session(store, namespace, value['session_id'], repo_profiles=repo_profiles)
    result.update(imported_review_id=review_id, duplicate_of=review_id if existing else None,
                  import_state='UNCHANGED' if existing else 'IMPORTED')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--namespace', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create')
    create.add_argument('--ids', required=True, nargs='+')
    create.add_argument('--goal', required=True)
    create.add_argument('--base-repo-sha')
    sub.add_parser('list')
    get = sub.add_parser('get')
    get.add_argument('--session-id', required=True)
    load = sub.add_parser('import')
    load.add_argument('--file', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'create':
            result = create_session(args.store, args.namespace, args.ids, args.goal, args.base_repo_sha)
        elif args.command == 'list':
            result = list_sessions(args.store, args.namespace)
        elif args.command == 'get':
            result = get_session(args.store, args.namespace, args.session_id)
        else:
            if args.file.is_symlink() or not args.file.is_file():
                raise ValueError('REVIEW_FILE_REQUIRED')
            with args.file.open('rb') as stream:
                value = strict_json(stream.read(MAX_BYTES + 1))
            result = import_review(args.store, args.namespace, value)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, sqlite3.Error) as exc:
        print(json.dumps({'state': 'BLOCKED', 'error_type': type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
