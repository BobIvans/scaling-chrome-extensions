"""Typed, opt-in Native Messaging access to the existing durable store.

Only a reviewed local operator profile chooses paths, namespaces and job
templates. This adapter never claims a job or starts a worker/test/AI process.
"""
from __future__ import annotations

import argparse
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
                             validate_policy)
from content_lab import apply_library_record
from context_review import create_session, get_session, import_review, list_sessions, strict_json
import repo_context

INPUT_BYTES = 16_000
OUTPUT_BYTES = 192_000
FIELDS = {
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
    "durable.repo.scan": ({"type", "repository"}, {"snapshotId"}),
    "durable.repo.scanRun": ({"type", "repository", "action"}, {"intentKey", "runId", "expectedCursor", "expectedRevision"}),
    "durable.repo.get": ({"type", "repository", "snapshotId"}, {"offset"}),
    "durable.repo.manifest": ({"type", "repository", "snapshotId", "action"}, {"offset", "limit", "fileOrdinal"}),
    "durable.repo.coverage": ({"type", "repository", "snapshotId", "action"}, {"query", "limit", "cursor"}),
    "durable.repo.export": ({"type", "repository", "snapshotId", "paths", "goal", "scope", "acceptance"}, {"maxBytes", "sourceOffset"}),
}
JOB_ID = re.compile(r"^[0-9a-f]{32}$")
ITEM_ID = re.compile(r"^[0-9a-f]{64}$")


def operator_profile(path):
    profile = load_json(path)
    required = {"schema", "store", "policy_file", "namespaces", "templates"}
    if not isinstance(profile, dict) or not required.issubset(profile) or set(profile) - required - {'repositories'} or profile["schema"] != "occ.native-durable-profile.v1":
        raise ValueError("DURABLE_OPERATOR_PROFILE_REQUIRED")
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
    for name, payload in templates.items():
        identifier(name)
        validate_job(payload, policy)
    repositories = profile.get('repositories', {})
    if not isinstance(repositories, dict) or len(repositories) > 20:
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
    result['next_step'] = ('RUN_REGISTERED_LOCAL_WORKER' if job['state'] in {'QUEUED', 'RETRY_READY'} else
                           'RECONCILE_AFTER_PROCESS_STOP_CHECK' if job['state'] == 'NEEDS_RECONCILIATION' else
                           'CHECK_OUTPUT_RECEIPT' if job['state'] == 'SUCCEEDED' else
                           'INSPECT_BLOCKER' if job['state'] in {'FAILED', 'BLOCKED'} else job['state'])
    return result


def scoped_job(core, profile, policy, job_id):
    if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
        raise ValueError("DURABLE_JOB_ID_REQUIRED")
    job = core.get(job_id)
    if job["policy_hash"] != digest(policy) or job["payload_hash"] != digest(job["payload"]) or not any(job["payload"] == template for template in profile["templates"].values()):
        raise ValueError("DURABLE_JOB_OUTSIDE_SCOPE")
    return job


def dispatch(request, profile_path):
    if not isinstance(request, dict) or request.get("type") not in FIELDS:
        raise ValueError("DURABLE_SCHEMA")
    required, optional = FIELDS[request["type"]]
    if not required.issubset(request) or set(request) - required - optional:
        raise ValueError("DURABLE_SCHEMA")
    if request['type'] == 'durable.repo.manifest':
        action = request['action']
        if (not isinstance(action, str) or action not in {'INFO', 'ENTRIES', 'PARTS'}
                or action == 'INFO' and set(request) != required
                or action != 'PARTS' and 'fileOrdinal' in request):
            raise ValueError('DURABLE_SCHEMA')
        if 'fileOrdinal' in request:
            strict_int(request['fileOrdinal'], 0, 9_007_199_254_740_991)
    if request['type'] == 'durable.repo.coverage':
        from repo_coverage import validate_request
        fields = {'query', 'limit', 'cursor'}
        if request['action'] == 'PAGE' and not fields.issubset(request):
            raise ValueError('DURABLE_SCHEMA')
        validate_request(request['action'], query=request.get('query'), limit=request.get('limit'),
                         cursor=request.get('cursor'), page_fields=bool(fields.intersection(request)))
    profile, policy = operator_profile(profile_path)
    store, operation = Path(profile["store"]), request["type"]
    if operation == 'durable.repo.coverage':
        # This operation must not initialize the writer/Core/schema owners.
        from repo_coverage import query
        alias = identifier(request['repository'])
        source = profile.get('repositories', {}).get(alias)
        if source is None:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        coverage = query(store, source['namespace'], request['snapshotId'], alias, source, request['action'],
                         **{k: request[k] for k in ('query', 'limit', 'cursor') if k in request})
        return {'schema': 'occ.native-durable-result.v1', 'operation': operation, 'coverage': coverage}
    core = Core(store, policy)
    value = {"schema": "occ.native-durable-result.v1", "operation": operation}
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
            db = repo_context.db_for(store)
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
                    file_ordinal=request.get('fileOrdinal'))
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
            value["items"] = search(store, namespace, request["query"], strict_int(request.get("limit", 10), 1, 20))
        else:
            ids = request["ids"]
            if not isinstance(ids, list) or not 1 <= len(ids) <= 10 or not all(isinstance(item_id, str) and ITEM_ID.fullmatch(item_id) for item_id in ids):
                raise ValueError("DURABLE_ITEM_IDS_REQUIRED")
            value["context"] = context_pack(store, namespace, ids, strict_int(request.get("maxBytes", 48_000), 1, 48_000))
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
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
        value = {"ok": True, "result": dispatch(request, args.profile)}
        output = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(output) > OUTPUT_BYTES:
            raise ValueError("DURABLE_OUTPUT_LIMIT")
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        message = str(exc)
        code = message if re.fullmatch(r"[A-Z_]{1,100}", message) else "DURABLE_OPERATION_FAILED"
        output = json.dumps({"ok": False, "error": code}).encode("utf-8")
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
