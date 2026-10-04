"""V7 handoff on the merged SQLite/repo owners, using supplied V4/V5 contracts."""
import json

from automation_core import context_pack, digest
from context_review import db_for, get_session, import_review, load_session, strict_json
from occ_v4.protocol import bytes_hash
from occ_v5.context import make_chunk, make_task, choose_context, build_bundle, import_bound_review


def handoff(store, namespace, session_id, *, repo_profiles):
    status = get_session(store, namespace, session_id, details=True, repo_profiles=repo_profiles)
    if status['state'] not in {'EXPORTED', 'NEEDS_REVIEW'} or status['repo_binding']['state'] != 'VERIFIED':
        raise ValueError('HANDOFF_CURRENT_COMPLETE_CONTEXT_REQUIRED')
    meta = status.get('request_meta')
    if not isinstance(meta, dict) or not meta.get('acceptance'):
        raise ValueError('HANDOFF_GOAL_SCOPE_CRITERIA_REQUIRED')
    pack = context_pack(store, namespace, [r['item_id'] for r in status['sources']], max_bytes=48_000)
    chunks = []
    for item in pack['items']:
        if bytes_hash(item['text'].encode('utf-8')) != item['input_sha256']:
            raise ValueError('HANDOFF_SOURCE_BYTES_MISMATCH')
        chunks.append(make_chunk(item['id'], item['text'], project=namespace, namespace=namespace,
                      title=item['source_key'], kind='code', sensitivity='PRIVATE',
                      source_ref='canonical:' + item['id'], span='selected byte-exact fragment'))
    task = make_task(chunks, [c['chunk_id'] for c in chunks], goal=meta['goal'], project=namespace, budget=64_000, query='')
    # The immutable session ID binds goal, scope, acceptance and source revisions.
    task.update(task_id=session_id, namespace_allowlist=[namespace], desired_capability='repo.context.review',
                required_check_ids=['criterion-' + digest(c)[:24] for c in meta['acceptance']],
                owner_search='FOUND', known_handler='context_review')
    # Duplicate criteria carry the same requirement identity.
    task['required_check_ids'] = sorted(set(task['required_check_ids']))
    selection = choose_context(task, chunks)
    if selection['gaps']:
        raise ValueError('HANDOFF_CONTEXT_GAP')
    bundle = build_bundle(task, selection, document_limit=160_000)
    binding = {'schema': 'occ.handoff-binding.v7', 'session_id': session_id,
               'base_repo_sha': status['base_repo_sha'], 'snapshot_sha256': status['snapshot_sha256'],
               'scope_sha256': digest(meta), 'required_criteria': meta['acceptance'],
               'accepted_scope': meta['accepted_scope'], 'authority': 'DATA_ONLY'}
    bundle['binding_v7'] = binding
    bundle['rendered_txt'] = ('V7 HOST BINDING\n' + json.dumps(binding, ensure_ascii=False, indent=2) + '\n\n' + bundle['rendered_txt'])
    if len(bundle['rendered_txt'].encode('utf-8')) > 160_000:
        raise ValueError('HANDOFF_OUTPUT_LIMIT')
    bundle['rendered_txt_bytes'] = len(bundle['rendered_txt'].encode('utf-8'))
    # Recheck disk and authorized profile after compilation.
    current = get_session(store, namespace, session_id, repo_profiles=repo_profiles)
    if current['repo_binding']['state'] != 'VERIFIED' or current['state'] not in {'EXPORTED', 'NEEDS_REVIEW'}:
        raise ValueError('HANDOFF_CURRENT_COMPLETE_CONTEXT_REQUIRED')
    return bundle


def import_bound(store, namespace, session_id, value, *, repo_profiles):
    # Rebuild from current host-selected evidence, never from model-supplied policy.
    strict_json(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'))
    bundle = handoff(store, namespace, session_id, repo_profiles=repo_profiles)
    overlay = bundle['overlay']
    import_bound_review(value, bundle['request'], overlay, current_goal_epoch=overlay['goal_epoch'],
                        current_revisions=overlay['current_revisions'], current_task_digest=overlay['task_digest'])
    db = db_for(store)
    try:
        _, session = load_session(db, namespace, session_id)
    finally:
        db.close()
    claim = value['v4_review']
    source = session['sources'][0]
    canonical = {'schema': 'occ.review-result.v1', 'session_id': session_id,
                 'snapshot_sha256': session['snapshot_sha256'], 'sources': session['sources'],
                 'base_repo_sha': session['base_repo_sha'],
                 'coverage': {'reviewed': [], 'not_reviewed': [s['source_key'] for s in session['sources']],
                              'missing_dependencies': claim['need_ids']},
                 'findings': [{'finding_id': 'v5-claim', 'classification': 'PROPOSAL_ONLY', 'disposition': 'OPEN',
                    'source_key': source['source_key'], 'source_sha256': source['sha256'], 'criterion': claim['summary'][:500],
                    'evidence_refs': [{'kind': 'MODEL_CLAIM', 'sha256': digest(value)}], 'duplicate_of': None, 'supersedes': None}]}
    # Keep the complete bound claim in the same ledger, including claimed tests.
    db = db_for(store)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS review_bound_claims(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, payload TEXT NOT NULL)')
        with db:
            db.execute('INSERT OR IGNORE INTO review_bound_claims VALUES (?,?,?)', (digest(value), session_id, json.dumps(value, ensure_ascii=False)))
    finally:
        db.close()
    return import_review(store, namespace, canonical, repo_profiles=repo_profiles)
