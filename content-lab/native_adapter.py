"""Typed, opt-in Native Messaging access to the existing durable store.

Only a reviewed local operator profile chooses paths, namespaces and job
templates. This adapter never claims a job or starts a worker/test/AI process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time

# -I excludes the script directory. Import only this installed adapter's siblings.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from automation_core import (Core, context_pack, digest, enqueue, identifier,
                             load_json, search, strict_int, validate_job,
                             validate_policy, read_connection)
from content_lab import apply_library_record
from context_review import create_session, get_session, import_review, list_sessions, strict_json
import repo_context

INPUT_BYTES = 16_000
OUTPUT_BYTES = 192_000
FIELDS = {
    "durable.action": ({"type", "action", "payload"}, set()),
    "durable.library": ({"type", "namespace", "action", "arguments"}, {"operationId"}),
    "durable.goal": ({"type", "action", "arguments"}, set()),
    "durable.effect": ({"type", "action", "arguments"}, set()),
    "durable.stop": ({"type", "requestId"}, set()),
    "durable.control.resume": ({"type", "expectedEpoch"}, set()),
    'durable.campaign.inspect': ({'type','campaign'}, {'offset','limit'}),
    'durable.campaign.advance': ({'type','campaign'}, set()),
    'durable.campaign.pause': ({'type','campaign'}, set()),
    'durable.campaign.resume': ({'type','campaign'}, set()),
    'durable.campaign.cancel': ({'type','campaign'}, set()),
    "durable.info": ({"type"}, set()),
    "durable.search": ({"type", "namespace", "query"}, {"limit"}),
    "durable.context": ({"type", "namespace", "ids"}, {"maxBytes"}),
    "durable.enqueue": ({"type", "template", "taskKey"}, set()),
    "durable.get": ({"type", "jobId"}, set()),
    "durable.cancel": ({"type", "jobId"}, set()),
    "durable.record": ({"type", "mutation"}, set()),
    "durable.review.create": ({"type", "namespace", "ids", "goal"}, {"baseRepoSha", "repoSnapshotId"}),
    "durable.review.import": ({"type", "namespace", "review"}, set()),
    "durable.review.list": ({"type", "namespace"}, {"limit"}),
    "durable.review.get": ({"type", "namespace", "sessionId"}, {"includeContent"}),
    "durable.review.report": ({"type", "namespace", "sessionId", "template", "taskKey"}, set()),
    "durable.review.handoff": ({"type", "namespace", "sessionId"}, set()),
    "durable.review.importBound": ({"type", "namespace", "sessionId", "review"}, set()),
    "durable.repo.list": ({"type"}, set()),
    "durable.repo.history": ({"type", "repository"}, {"limit", "cursor"}),
    "durable.repo.delta": ({"type", "repository", "snapshotId"}, {"limit", "cursor", "baseSnapshotId"}),
    "durable.repo.scan": ({"type", "repository"}, {"snapshotId"}),
    "durable.repo.scanRun": ({"type", "repository", "action"}, {"intentKey", "runId", "expectedCursor", "expectedRevision"}),
    "durable.repo.get": ({"type", "repository", "snapshotId"}, {"offset"}),
    "durable.repo.manifest": ({"type", "repository", "snapshotId", "action"}, {"offset", "limit", "fileOrdinal"}),
    "durable.repo.coverage": ({"type", "repository", "snapshotId", "action"}, {"query", "limit", "cursor"}),
    "durable.repo.export": ({"type", "repository", "snapshotId", "paths", "goal", "scope", "acceptance"}, {"maxBytes", "sourceOffset"}),
}
JOB_ID = re.compile(r"^[0-9a-f]{32}$")
ITEM_ID = re.compile(r"^[0-9a-f]{64}$")
DESKTOP_PROTOCOL = 'occ.desktop-stdio.v1'
DESKTOP_READS = frozenset({'durable.info', 'durable.get', 'durable.repo.list', 'durable.search',
                           'durable.context', 'durable.repo.manifest',
                           'durable.repo.history', 'durable.repo.delta'})
DESKTOP_SCAN = 'durable.repo.scanRun'


def adapter_context(profile, policy):
    """Bind the reply to the exact loaded objects used by the dispatcher."""
    root = Path(profile['store']).resolve()
    database = root / 'content.sqlite3'
    identity = {'store': str(root), 'database': None}
    if database.is_file():
        stat = database.stat()
        identity['database'] = [stat.st_dev, stat.st_ino]
    return {'protocol': DESKTOP_PROTOCOL, 'profile_digest': digest([profile, policy]),
            'store_identity': digest(identity),
            'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'backend_bundle_sha256': (__import__('context_runtime').build_digest() if profile.get('context_service') else None)}


def ready_store(store, *, manifest=False):
    """Inspect existing schema through a read-only connection, never initialize."""
    columns = {'items': {'id', 'payload'}, 'content_fts': {'id', 'text'},
               'sync_heads': {'namespace', 'source_key', 'item_id', 'present'}}
    if manifest:
        columns.update({'repo_snapshots': {'id', 'namespace', 'alias', 'profile', 'head', 'tree', 'cursor', 'total'},
                        'repo_entries': {'snapshot_id', 'ordinal', 'path', 'mode', 'kind', 'oid', 'size', 'state', 'reason', 'file_hash', 'analysis'},
                        'repo_chunks': {'snapshot_id', 'path', 'ordinal', 'revision', 'raw', 'item_id', 'logical_id', 'byte_start', 'byte_end'}})
    try:
        db = read_connection(store)
        try:
            return all(required.issubset({r['name'] for r in db.execute('PRAGMA table_info(' + table + ')')})
                       for table, required in columns.items())
        finally:
            db.close()
    except (OSError, ValueError, sqlite3.Error):
        return False


def ready_scan_store(store):
    if not ready_store(store, manifest=True):
        return False
    try:
        db = read_connection(store)
        try:
            objects = {row['name'] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','trigger','index')")}
            required = {'repo_scan_runs', 'repo_entry_counts', 'repo_count_migration',
                        'repo_heads', 'repo_count_insert', 'repo_count_delete',
                        'repo_count_update', 'repo_active_scan'}
            return required <= objects and bool(db.execute(
                'SELECT 1 FROM repo_count_migration WHERE id=1').fetchone())
        finally:
            db.close()
    except (OSError, ValueError, sqlite3.Error):
        return False


def info(profile, policy):
    store = Path(profile['store'])
    repo_reads = {'durable.repo.manifest', 'durable.repo.history', 'durable.repo.delta'}
    capabilities = sorted((DESKTOP_READS - repo_reads) & FIELDS.keys())
    if policy.get('actions', {}).get('enabled') is True:
        from action_intent import registry
        registry(policy['actions'])
        capabilities.extend(['durable.action','durable.goal','durable.effect'])
    if 'durable.repo.manifest' in FIELDS and ready_store(store, manifest=True):
        import repo_manifest
        if callable(getattr(repo_manifest, 'page', None)):
            capabilities.append('durable.repo.manifest')
            capabilities.extend(sorted({'durable.repo.history', 'durable.repo.delta'} & FIELDS.keys()))
            if profile.get('desktop_scan_enabled') is True and ready_scan_store(store):
                capabilities.append(DESKTOP_SCAN)
    if profile.get('context_service'):
        capabilities.extend(['durable.library','durable.stop','durable.control.resume'])
    return {'protocol': DESKTOP_PROTOCOL, 'native_input_bytes': INPUT_BYTES,
            'native_combined_output_bytes': OUTPUT_BYTES,
            'native_timeout_ms': 120_000 if DESKTOP_SCAN in capabilities else 10_000,
            'capabilities': capabilities, 'namespaces': list(profile['namespaces']),
            'store_path': str(store.resolve()), 'store_ready': ready_store(store),
            'backend_build_status': 'UNKNOWN_BUNDLE', 'migration_performed': False}


def operator_profile(path):
    profile = load_json(path)
    required = {"schema", "store", "policy_file", "namespaces", "templates"}
    if not isinstance(profile, dict) or not required.issubset(profile) or set(profile) - required - {'repositories', 'campaigns', 'desktop_scan_enabled', 'context_service'} or profile["schema"] != "occ.native-durable-profile.v1":
        raise ValueError("DURABLE_OPERATOR_PROFILE_REQUIRED")
    if type(profile.get('desktop_scan_enabled', False)) is not bool:
        raise ValueError('DURABLE_OPERATOR_PROFILE_REQUIRED')
    for field in ("store", "policy_file"):
        value = profile[field]
        if not isinstance(value, str) or "\0" in value or not Path(value).is_absolute():
            raise ValueError("DURABLE_ABSOLUTE_OPERATOR_PATH_REQUIRED")
    namespaces = profile["namespaces"]
    if not isinstance(namespaces, list) or not 1 <= len(namespaces) <= 100 or not all(isinstance(value, str) for value in namespaces) or len(set(namespaces)) != len(namespaces):
        raise ValueError("DURABLE_NAMESPACES_REQUIRED")
    for namespace in namespaces:
        identifier(namespace)
    templates = profile["templates"]
    if not isinstance(templates, dict) or len(templates) > 100:
        raise ValueError("DURABLE_TEMPLATES_REQUIRED")
    policy = validate_policy(load_json(Path(profile["policy_file"])))
    if policy.get('actions', {}).get('enabled') is True:
        from action_intent import registry
        configured = registry(policy['actions'])
        if not set(configured['namespaces']) <= set(namespaces):
            raise ValueError('ACTION_NAMESPACE_OUTSIDE_SCOPE')
        if any(profile.get('repositories', {}).get(k) != v for k, v in configured['repositories'].items()):
            raise ValueError('ACTION_REPO_OUTSIDE_SCOPE')
    for name, payload in templates.items():
        identifier(name)
        validate_job(payload, policy)
    repositories = profile.get('repositories', {})
    if not isinstance(repositories, dict):
        raise ValueError('REPO_OPERATOR_PROFILE_REQUIRED')
    for alias, source in repositories.items():
        identifier(alias)
        repo_context.validate_profile(source)
        if source['namespace'] not in namespaces:
            raise ValueError('DURABLE_NAMESPACE_OUTSIDE_SCOPE')
    for payload in templates.values():
        if payload.get('kind') == 'review_report':
            report = policy['reports'][payload['report_profile']]
            if (report['namespace'] not in namespaces
                    or repositories.get(report['repository']) != report['repository_profile']):
                raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
    if 'context_service' in profile:
        import context_runtime
        c=context_runtime.config(policy,profile['context_service'])
        if c['namespace'] not in namespaces:raise ValueError('DURABLE_NAMESPACE_OUTSIDE_SCOPE')
    campaigns=profile.get('campaigns',[])
    if not isinstance(campaigns,list) or len(campaigns)!=len(set(campaigns)) or not all(isinstance(x,str) and x in policy.get('campaigns',{}) for x in campaigns):
        raise ValueError('CAMPAIGN_OUTSIDE_OPERATOR_SCOPE')
    return profile, policy


def summary(job):
    # Do not return policy/payload, worktree paths, lease tokens or test logs.
    result = {key: job[key] for key in ("id", "task_key", "state", "attempt", "max_attempts", "created", "updated")}
    result["cancel_requested"] = bool(job["cancel_requested"])
    # Make failures/output visible without exposing paths, policy or source text.
    receipt = job.get('result', {})
    result['outcome'] = {}
    reason = receipt.get('reason')
    if isinstance(reason, str):
        result['outcome']['reason'] = reason if re.fullmatch(r'[A-Z_]{1,100}', reason) else 'LOCAL_OPERATION_BLOCKED'
    if job['payload'].get('kind') == 'review_report':
        allowed = ('state', 'sha256', 'bytes', 'filename', 'verified_property', 'findings_closed', 'reused')
        result['outcome'].update({k: receipt[k] for k in allowed if k in receipt})
    if job['payload'].get('kind') == 'workflow_operation':
        allowed=('state','source_commit','result_commit','result_tree','artifact_digest',
                 'device_qualified','usable','brief_id','loop_state','loop_stop_reason','scope')
        result['outcome'].update({k:receipt[k] for k in allowed if k in receipt})
    result['next_step'] = ('RUN_REGISTERED_LOCAL_WORKER' if job['state'] in {'QUEUED', 'RETRY_READY'} else
                           'RECONCILE_AFTER_PROCESS_STOP_CHECK' if job['state'] == 'NEEDS_RECONCILIATION' else
                           'CHECK_OUTPUT_RECEIPT' if job['state'] == 'SUCCEEDED' else
                           'INSPECT_BLOCKER' if job['state'] in {'FAILED', 'BLOCKED'} else job['state'])
    return result


def scoped_job(core, profile, policy, job_id):
    if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
        raise ValueError("DURABLE_JOB_ID_REQUIRED")
    job = core.get(job_id)
    payload=job["payload"]
    registered=any(payload == template for template in profile["templates"].values())
    action_read=(payload.get("kind")=="action_plan" and policy.get("actions",{}).get("enabled") is True)
    if action_read:
        validate_job(payload,policy)
    if job["policy_hash"] != digest(policy) or job["payload_hash"] != digest(payload) or not (registered or action_read):
        raise ValueError("DURABLE_JOB_OUTSIDE_SCOPE")
    return job


def validate_request(request):
    if not isinstance(request, dict) or not isinstance(request.get('type'), str) or request['type'] not in FIELDS:
        raise ValueError("DURABLE_SCHEMA")
    required, optional = FIELDS[request["type"]]
    if not required.issubset(request) or set(request) - required - optional:
        raise ValueError("DURABLE_SCHEMA")
    if request['type']=='durable.goal':
        if request['action'] not in {'CREATE','INSPECT','REVISE','PLAN','ADMIT','PROGRESS','CHECKPOINT','LIST'} or not isinstance(request['arguments'],dict):
            raise ValueError('DURABLE_SCHEMA')
    if request['type']=='durable.effect':
        if request['action'] not in {'BEGIN','INSPECT','TRANSITION'} or not isinstance(request['arguments'],dict):
            raise ValueError('DURABLE_SCHEMA')
    if request['type'].startswith('durable.campaign.'):
        identifier(request['campaign'])
        if 'offset' in request:strict_int(request['offset'],0,9_007_199_254_740_991)
        if 'limit' in request:strict_int(request['limit'],1,100)
    if request['type'] == 'durable.repo.manifest':
        action = request['action']
        if (not isinstance(action, str) or action not in {'INFO', 'ENTRIES', 'PARTS'}
                or action == 'INFO' and set(request) != required
                or action != 'PARTS' and 'fileOrdinal' in request):
            raise ValueError('DURABLE_SCHEMA')
        if 'fileOrdinal' in request:
            strict_int(request['fileOrdinal'], 0, 9_007_199_254_740_991)
    if request['type'] == 'durable.repo.coverage':
        from repo_coverage import validate_request as validate_coverage_request
        fields = {'query', 'limit', 'cursor'}
        if request['action'] == 'PAGE' and not fields.issubset(request):
            raise ValueError('DURABLE_SCHEMA')
        validate_coverage_request(request['action'], query=request.get('query'), limit=request.get('limit'),
                                  cursor=request.get('cursor'), page_fields=bool(fields.intersection(request)))
    return request


def dispatch(request, profile_path):
    validate_request(request)
    profile, policy = operator_profile(profile_path)
    return dispatch_loaded(request, profile, policy)


def dispatch_loaded(request, profile, policy, *, desktop=False):
    validate_request(request)
    store, operation = Path(profile["store"]), request["type"]
    value = {"schema": "occ.native-durable-result.v1", "operation": operation}
    if desktop and operation not in DESKTOP_READS and not (
            operation in {'durable.action','durable.goal','durable.effect'} or
            (operation == DESKTOP_SCAN and DESKTOP_SCAN in info(profile, policy)['capabilities']) or
            (profile.get('context_service') and operation in {'durable.library','durable.stop','durable.control.resume'})):
        raise ValueError('DESKTOP_READ_ONLY')
    if operation == 'durable.action':
        value['action'] = Core(store, policy).actions.handle(request['action'], request['payload'])
        return value
    if operation == 'durable.goal':
        import goal_runtime as goals
        action=request['action'];args=request['arguments']
        if action=='CREATE':result=goals.create(store,args['spec'],goal_id=args.get('goal_id'))
        elif action=='INSPECT':result=goals.inspect(store,args['goal_id'])
        elif action=='REVISE':result=goals.revise(store,args['goal_id'],args['expected_revision'],args['spec'])
        elif action=='PLAN':result=goals.plan(store,args['goal_id'],args['expected_revision'],args['h2'],args['h1'],args['decision'])
        elif action=='ADMIT':result=goals.admit(store,args['goal_id'],args['expected_revision'],args['candidate_id'])
        elif action=='PROGRESS':result=goals.progress(store,args['goal_id'],args['expected_revision'],args['delta'])
        elif action=='CHECKPOINT':result=goals.checkpoint(store,args['goal_id'],args['expected_revision'],args['runtime'],goal_state=args.get('state'))
        elif action=='LIST':result=goals.list_goals(store,args.get('offset',0),args.get('limit',50))
        else:raise ValueError('GOAL_ACTION_UNAVAILABLE')
        value['goal']=result
        return value
    if operation == 'durable.effect':
        import workflow_state as ws
        action=request['action'];args=request['arguments']
        if action=='BEGIN':
            with ws.transaction(store) as db:result=ws.begin_effect(db,args['operation_id'],args['binding'])
        elif action=='INSPECT':
            with ws.transaction(store) as db:
                row=ws.get(db,'effect',args['operation_id'])
                if row is None:raise ValueError('WORKFLOW_EFFECT_NOT_FOUND')
                result=row
        elif action=='TRANSITION':
            with ws.transaction(store) as db:result={'revision':ws.effect_transition(db,args['operation_id'],args['state'],args['expected_revision'],args['evidence'])}
            with ws.transaction(store) as db:result['value']=ws.get(db,'effect',args['operation_id'])['value']
        else:raise ValueError('WORKFLOW_EFFECT_ACTION')
        value['effect']=result
        return value
    if operation in {'durable.library','durable.stop','durable.control.resume'}:
        import context_runtime as runtime
        service=profile.get('context_service')
        if service is None:raise ValueError('CONTEXT_SERVICE_NOT_CONFIGURED')
        c=runtime.config(policy,service)
        if operation=='durable.stop':result=Core(store,policy).stop(request['requestId'])
        elif operation=='durable.control.resume':result=Core(store,policy).resume_control(request['expectedEpoch'])
        else:
            if request['namespace']!=c['namespace']:raise ValueError('DURABLE_NAMESPACE_OUTSIDE_SCOPE')
            action=request['action'];args=request['arguments']
            if action in runtime.READS:
                if 'operationId' in request:raise ValueError('DURABLE_SCHEMA')
                result=runtime.query(store,policy,service,action,args)
            else:
                result=runtime.submit(store,policy,service,action,args,request.get('operationId'))
        value['library']={'schema':'occ.context-service-result.v1','namespace':c['namespace'],
                          'action':request.get('action',operation),'data':result,'authority':'DATA_ONLY'}
        return value
    if operation.startswith('durable.campaign.'):
        from campaign_runtime import inspect, advance, cancel, set_admission
        alias=identifier(request['campaign'])
        if alias not in profile.get('campaigns',[]):raise ValueError('CAMPAIGN_OUTSIDE_OPERATOR_SCOPE')
        if operation=='durable.campaign.inspect':
            value['campaign']=inspect(store,policy,alias,offset=request.get('offset',0),limit=request.get('limit',20))
        elif operation in {'durable.campaign.pause','durable.campaign.resume'}:
            value['campaign']=set_admission(store,policy,alias,operation.endswith('pause'))
        else:
            value['campaign']=(advance if operation.endswith('advance') else cancel)(store,policy,alias)
        return value
    if operation == 'durable.repo.coverage':
        # This operation must not initialize the writer/Core/schema owners.
        from repo_coverage import query
        alias = identifier(request['repository'])
        source = profile.get('repositories', {}).get(alias)
        if source is None:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        coverage = query(store, source['namespace'], request['snapshotId'], alias, source, request['action'],
                         **{k: request[k] for k in ('query', 'limit', 'cursor') if k in request})
        value['coverage'] = coverage
        return value
    if operation == 'durable.info':
        value['info'] = info(profile, policy)
        return value
    if desktop and not ready_store(store, manifest=operation in {
            'durable.repo.manifest', 'durable.repo.history', 'durable.repo.delta', DESKTOP_SCAN}):
        raise ValueError('DESKTOP_SETUP_REQUIRED')
    if operation in {'durable.repo.history', 'durable.repo.delta'}:
        import repo_history
        alias = identifier(request['repository'])
        source = profile.get('repositories', {}).get(alias)
        if source is None:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        options = {k: request[k] for k in ('limit', 'cursor') if k in request}
        if operation == 'durable.repo.history':
            value['page'] = repo_history.snapshots(store, source['namespace'], alias, source, **options)
        else:
            value['page'] = repo_history.delta(store, source['namespace'], alias, source,
                                               request['snapshotId'], base_snapshot_id=request.get('baseSnapshotId'),
                                               **options)
        return value
    core = None if desktop else Core(store, policy)
    if operation.startswith('durable.repo.'):
        repositories = profile.get('repositories', {})
        if operation == 'durable.repo.list':
            value['repositories'] = [{'repository': alias, 'namespace': p['namespace']}
                                     for alias, p in repositories.items()]
        else:
            alias = identifier(request['repository'])
            if alias not in repositories:
                raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
            source = repositories[alias]
            namespace = source['namespace']
            if operation == 'durable.repo.scanRun':
                fields = {k: v for k, v in request.items() if k not in {'type', 'repository', 'action'}}
                value['scan_run'] = repo_context.scan_run(store, alias, source, request['action'], **fields)
                return value
            snapshot_id = request.get('snapshotId')
            if operation == 'durable.repo.scan' and snapshot_id is None:
                snapshot_id = repo_context.start_scan(store, alias, source)
            db = read_connection(store) if desktop else repo_context.db_for(store)
            try:
                snapshot = repo_context.load_snapshot(db, namespace, snapshot_id)
                if snapshot['alias'] != alias or json.loads(snapshot['profile']) != source:
                    raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
            finally:
                db.close()
            if operation == 'durable.repo.scan':
                value['snapshot'] = repo_context.scan_page(store, namespace, snapshot_id)
            elif operation == 'durable.repo.get':
                value['snapshot'] = repo_context.get_snapshot(store, namespace, snapshot_id, offset=request.get('offset', 0))
            elif operation == 'durable.repo.manifest':
                import repo_manifest
                value['manifest'] = repo_manifest.page(store, namespace, snapshot_id, alias, source,
                    request['action'], offset=request.get('offset', 0), limit=request.get('limit', 20),
                    file_ordinal=request.get('fileOrdinal'), read_only=desktop)
            else:
                value['export'] = repo_context.export_request(store, namespace, snapshot_id, request['paths'],
                    request['goal'], request['scope'], request['acceptance'], request.get('maxBytes', 24_000), request.get('sourceOffset', 0))
    elif operation.startswith('durable.review.'):
        namespace = identifier(request['namespace'])
        if namespace not in profile['namespaces']:
            raise ValueError('DURABLE_NAMESPACE_OUTSIDE_SCOPE')
        if operation == 'durable.review.create':
            ids = request['ids']
            if not isinstance(ids, list) or not 1 <= len(ids) <= 10 or not all(isinstance(item_id, str) and ITEM_ID.fullmatch(item_id) for item_id in ids):
                raise ValueError('DURABLE_ITEM_IDS_REQUIRED')
            snapshot_id = request.get('repoSnapshotId')
            if snapshot_id is not None:
                db = repo_context.db_for(store)
                try:
                    snap = repo_context.load_snapshot(db, namespace, snapshot_id)
                    if json.loads(snap['profile']) != profile.get('repositories', {}).get(snap['alias']):
                        raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
                finally:
                    db.close()
            value['review'] = create_session(store, namespace, ids, request['goal'], request.get('baseRepoSha'), repo_snapshot_id=snapshot_id)
        elif operation == 'durable.review.import':
            value['review'] = import_review(store, namespace, request['review'], repo_profiles=profile.get('repositories', {}))
        elif operation == 'durable.review.list':
            value['reviews'] = list_sessions(store, namespace, request.get('limit', 20), repo_profiles=profile.get('repositories', {}))
        elif operation in {'durable.review.handoff', 'durable.review.importBound'}:
            from context_handoff import handoff, import_bound
            if operation == 'durable.review.handoff':
                bundle = handoff(store, namespace, request['sessionId'], repo_profiles=profile.get('repositories', {}))
                # Return one document; repeated JSON sources exceed native bounds.
                value['handoff'] = {k: bundle[k] for k in ('rendered_txt', 'rendered_txt_bytes', 'review_template', 'binding_v7')}
            else:
                value['review'] = import_bound(store, namespace, request['sessionId'], request['review'], repo_profiles=profile.get('repositories', {}))
        elif operation == 'durable.review.report':
            template = identifier(request['template'])
            payload = profile['templates'].get(template)
            if not isinstance(payload, dict) or payload.get('kind') != 'review_report':
                raise ValueError('DURABLE_REPORT_TEMPLATE_REQUIRED')
            registered = policy['reports'][payload['report_profile']]
            if registered['namespace'] != namespace or registered['session_id'] != request['sessionId']:
                raise ValueError('DURABLE_REPORT_SESSION_MISMATCH')
            if profile.get('repositories', {}).get(registered['repository']) != registered['repository_profile']:
                raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
            from review_report import expected_report
            expected_report(store, registered)
            job = enqueue(store, policy, request['taskKey'], payload)
            value['job'] = summary(scoped_job(core, profile, policy, job['id']))
        else:
            details = request.get('includeContent', False)
            if type(details) is not bool:
                raise ValueError('DURABLE_SCHEMA')
            value['review'] = get_session(store, namespace, request['sessionId'], details=details, repo_profiles=profile.get('repositories', {}))
    elif operation in {"durable.search", "durable.context"}:
        namespace = identifier(request["namespace"])
        if namespace not in profile["namespaces"]:
            raise ValueError("DURABLE_NAMESPACE_OUTSIDE_SCOPE")
        if operation == "durable.search":
            value["items"] = search(store, namespace, request["query"], strict_int(request.get("limit", 10), 1, 20), read_only=desktop)
        else:
            ids = request["ids"]
            if not isinstance(ids, list) or not 1 <= len(ids) <= 10 or not all(isinstance(item_id, str) and ITEM_ID.fullmatch(item_id) for item_id in ids):
                raise ValueError("DURABLE_ITEM_IDS_REQUIRED")
            value["context"] = context_pack(store, namespace, ids, strict_int(request.get("maxBytes", 48_000), 1, 48_000), read_only=desktop)
    elif operation == "durable.record":
        mutation = request["mutation"]
        namespace = mutation.get("namespace") if isinstance(mutation, dict) else None
        if namespace not in profile["namespaces"]:
            raise ValueError("DURABLE_NAMESPACE_OUTSIDE_SCOPE")
        value["record"] = apply_library_record(store, mutation)
    elif operation == "durable.enqueue":
        template = identifier(request["template"])
        if template not in profile["templates"]:
            raise ValueError("DURABLE_TEMPLATE_OUTSIDE_SCOPE")
        registered = enqueue(store, policy, request["taskKey"], profile["templates"][template])
        value['job'] = summary(scoped_job(core, profile, policy, registered['id'])) | {'reused': registered['reused']}
    else:
        job = scoped_job(core, profile, policy, request["jobId"])
        if operation == "durable.cancel":
            core.cancel(job["id"])
            job = scoped_job(core, profile, policy, job["id"])
        value["job"] = summary(job)
    return value


def dispatch_desktop(request, profile_path):
    """A single loaded profile/policy supplies both reply binding and dispatch."""
    context = None
    try:
        validate_request(request)
        if request['type'] not in DESKTOP_READS | {'durable.action','durable.goal','durable.effect','durable.library','durable.stop','durable.control.resume', DESKTOP_SCAN}:
            raise ValueError('DESKTOP_READ_ONLY')
        profile, policy = operator_profile(profile_path)
        if request['type'] not in DESKTOP_READS and not (
                (request['type'] in {'durable.action','durable.goal','durable.effect'} and request['type'] in info(profile, policy)['capabilities']) or
                (request['type'] == DESKTOP_SCAN and DESKTOP_SCAN in info(profile, policy)['capabilities']) or
                (profile.get('context_service') and request['type'] in {'durable.library','durable.stop','durable.control.resume'})):
            raise ValueError('DESKTOP_READ_ONLY')
        context = adapter_context(profile, policy)
        result = dispatch_loaded(request, profile, policy, desktop=True)
        return {'schema': 'occ.desktop-stdio-result.v1', 'ok': True,
                'adapter_context': context, 'result': result}
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        return {'schema': 'occ.desktop-stdio-result.v1', 'ok': False,
                'adapter_context': context, 'error': error_code(exc)}


def error_code(exc):
    message = str(exc)
    return message if re.fullmatch(r'[A-Z_]{1,100}', message) else 'DURABLE_OPERATION_FAILED'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument('--desktop-stdio', action='store_true')
    args = parser.parse_args(argv)
    try:
        if not args.profile.is_absolute():
            raise ValueError("DURABLE_ABSOLUTE_OPERATOR_PATH_REQUIRED")
        raw = sys.stdin.buffer.read(INPUT_BYTES + 1)
        if len(raw) > INPUT_BYTES:
            raise ValueError("DURABLE_INPUT_LIMIT")
        request = strict_json(raw)
        if isinstance(request, dict) and isinstance(request.get('type'), str) and request['type'].startswith('durable.repo.'):
            last = [0.0]
            def progress():
                now = time.monotonic()
                if now - last[0] >= 1:
                    sys.stderr.buffer.write(b'OCC_SCAN_PROGRESS\n')
                    sys.stderr.buffer.flush()
                    last[0] = now
            repo_context._progress_callback = progress
        value = (dispatch_desktop(request, args.profile) if args.desktop_stdio else
                 {"ok": True, "result": dispatch(request, args.profile)})
        output = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(output) > OUTPUT_BYTES:
            raise ValueError("DURABLE_OUTPUT_LIMIT")
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        value = {'ok': False, 'error': error_code(exc)}
        if args.desktop_stdio:
            value.update(schema='occ.desktop-stdio-result.v1', adapter_context=None)
        output = json.dumps(value).encode('utf-8')
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
