"""Registered report writer; verifies current ledger and actual output bytes.

This adapts the unpublished Execute PRs report to the merged repo_context owner.
Reviews remain data. Only an operator policy selects an output directory.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from automation_core import context_pack, digest, identifier
from context_review import db_for, get_session, hash_value, load_session, strict_json
import repo_context

MAX_REPORT_BYTES = 192_000


def no_links(path):
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('REPORT_LINK_BOUNDARY')


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != {
            'namespace', 'session_id', 'review_id', 'output_root', 'repository', 'repository_profile'}:
        raise ValueError('REPORT_PROFILE_REQUIRED')
    identifier(profile['namespace'])
    identifier(profile['repository'])
    hash_value(profile['session_id'])
    hash_value(profile['review_id'])
    repo_context.validate_profile(profile['repository_profile'])
    if profile['repository_profile']['namespace'] != profile['namespace']:
        raise ValueError('REPORT_NAMESPACE_MISMATCH')
    root = profile['output_root']
    if not isinstance(root, str) or '\0' in root or not Path(root).is_absolute():
        raise ValueError('REPORT_OUTPUT_ROOT_REQUIRED')
    return profile


def expected_report(store, profile):
    validate_profile(profile)
    profiles = {profile['repository']: profile['repository_profile']}
    status = get_session(store, profile['namespace'], profile['session_id'], details=True, repo_profiles=profiles)
    if status['state'] != 'NEEDS_REVIEW' or status['repo_binding']['state'] != 'VERIFIED':
        raise ValueError('REPORT_CURRENT_COMPLETE_REVIEW_REQUIRED')
    if status['review_id'] != profile['review_id']:
        raise ValueError('REPORT_REVIEW_CHANGED')
    db = db_for(store)
    try:
        _, session = load_session(db, profile['namespace'], profile['session_id'])
        row = db.execute('SELECT * FROM review_results WHERE id=? AND session_id=?',
                         (profile['review_id'], profile['session_id'])).fetchone()
        if row is None:
            raise ValueError('REVIEW_RESULT_CORRUPT')
        review = strict_json(row['payload'].encode('utf-8'))
        if digest(review) != row['payload_hash'] or row['id'] != row['payload_hash']:
            raise ValueError('REVIEW_RESULT_CORRUPT')
    finally:
        db.close()
    if status.get('unaccounted_sources'):
        raise ValueError('REPORT_COVERAGE_INCOMPLETE')
    pack = context_pack(store, profile['namespace'], [r['item_id'] for r in status['sources']], max_bytes=48_000)
    report = {'schema': 'occ.verified-local-review-report.v1', 'session_id': profile['session_id'],
              'review_id': profile['review_id'], 'repo_sha': status['base_repo_sha'],
              'request': session.get('request_meta'), 'sources': pack, 'review': review,
              'authority': 'DATA_ONLY', 'findings_closed': False,
              'verified_property': 'report bytes only; review claims are unverified'}
    raw = ('OCC LOCAL REVIEW REPORT\n' + json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError('REPORT_OUTPUT_LIMIT')
    return raw


def output_path(store, profile):
    root = Path(profile['output_root'])
    no_links(root)
    if not root.is_dir():
        raise ValueError('REPORT_OUTPUT_ROOT_REQUIRED')
    root = root.resolve()
    source = Path(profile['repository_profile']['root']).resolve()
    store = Path(store).resolve()
    if any(root.is_relative_to(p) or p.is_relative_to(root) for p in (source, store)):
        raise ValueError('REPORT_OUTPUT_BOUNDARY')
    path = root / ('OCC_REVIEW_' + profile['session_id'] + '_' + profile['review_id'] + '.txt')
    no_links(path)
    return path


def verify_output(path, expected):
    no_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != len(expected):
        raise ValueError('REPORT_POSTCONDITION_FAILED')
    with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)), 'rb') as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(len(expected) + 1)
    no_links(path)
    after = path.stat()
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if signature(before) != signature(opened) or signature(before) != signature(after) or raw != expected:
        raise ValueError('REPORT_POSTCONDITION_FAILED')
    return {'state': 'SUCCESS_VERIFIED', 'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'filename': path.name, 'verified_property': 'LOCAL_REPORT_BYTES',
            'findings_closed': False, 'model_calls': 0, 'transactions_sent': 0}


def write_report(store, profile, *, progress=lambda: None):
    progress()
    expected = expected_report(store, profile)
    path = output_path(store, profile)
    progress()
    reused = path.exists()
    if not reused:
        # Exclusive create: partial files are reconciled, never overwritten.
        with path.open('xb') as stream:
            stream.write(expected)
            stream.flush()
            os.fsync(stream.fileno())
    progress()
    if expected_report(store, profile) != expected:
        raise ValueError('REPORT_CONTEXT_CHANGED')
    result = verify_output(path, expected)
    progress()
    return result | {'session_id': profile['session_id'], 'review_id': profile['review_id'], 'reused': reused}
