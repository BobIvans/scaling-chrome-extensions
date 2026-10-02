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

# -I excludes the script directory. Import only this installed adapter's siblings.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from automation_core import (Core, context_pack, digest, enqueue, identifier,
                             load_json, search, strict_int, validate_job,
                             validate_policy)
from content_lab import apply_library_record

INPUT_BYTES = 16_000
OUTPUT_BYTES = 192_000
FIELDS = {
    "durable.search": ({"type", "namespace", "query"}, {"limit"}),
    "durable.context": ({"type", "namespace", "ids"}, {"maxBytes"}),
    "durable.enqueue": ({"type", "template", "taskKey"}, set()),
    "durable.get": ({"type", "jobId"}, set()),
    "durable.cancel": ({"type", "jobId"}, set()),
    "durable.record": ({"type", "mutation"}, set()),
}
JOB_ID = re.compile(r"^[0-9a-f]{32}$")
ITEM_ID = re.compile(r"^[0-9a-f]{64}$")


def operator_profile(path):
    profile = load_json(path)
    if not isinstance(profile, dict) or set(profile) != {"schema", "store", "policy_file", "namespaces", "templates"} or profile["schema"] != "occ.native-durable-profile.v1":
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
    return profile, policy


def summary(job):
    # Do not return policy/payload, worktree paths, lease tokens or test logs.
    result = {key: job[key] for key in ("id", "task_key", "state", "attempt", "max_attempts", "created", "updated")}
    result["cancel_requested"] = bool(job["cancel_requested"])
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
    profile, policy = operator_profile(profile_path)
    store, operation = Path(profile["store"]), request["type"]
    core = Core(store, policy)
    value = {"schema": "occ.native-durable-result.v1", "operation": operation}
    if operation in {"durable.search", "durable.context"}:
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
        value["job"] = enqueue(store, policy, request["taskKey"], profile["templates"][template])
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
        value = {"ok": True, "result": dispatch(json.loads(raw.decode("utf-8")), args.profile)}
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
