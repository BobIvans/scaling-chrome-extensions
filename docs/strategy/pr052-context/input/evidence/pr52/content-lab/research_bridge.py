"""Operator-pinned Studious replay through the existing Core process lifecycle.

SQLite jobs remain the SCE authority. Dataset and market logic belong to Studious.
Receipts prove local offline model work only, never live or device qualification.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re

SCRIPT = "scripts/run_research_qualification.py"
PROFILE_KEYS = {
    "schema",
    "root",
    "source_commit",
    "python",
    "handler_sha256",
    "dataset",
    "dataset_sha256",
    "config",
    "config_sha256",
    "output_root",
    "timeout_seconds",
}


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path):
    p = Path(path)
    if not p.is_file() or any(v.is_symlink() for v in (p, *p.parents)):
        raise ValueError("RESEARCH_REGULAR_FILE_REQUIRED")
    h = hashlib.sha256()
    with p.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path, limit=65536):
    p = Path(path)
    sha_file(p)
    if p.stat().st_size > limit:
        raise ValueError("RESEARCH_FRAME_BUDGET")

    def pairs(rows):
        out = {}
        for k, v in rows:
            if k in out:
                raise ValueError("RESEARCH_DUPLICATE_JSON_KEY")
            out[k] = v
        return out

    def bad(_):
        raise ValueError("RESEARCH_NONFINITE_JSON")

    return json.loads(p.read_bytes(), object_pairs_hook=pairs, parse_constant=bad)


def validate_profile(value):
    if (
        not isinstance(value, dict)
        or set(value) != PROFILE_KEYS
        or value["schema"] != "occ.research-profile.v1"
    ):
        raise ValueError("REGISTERED_RESEARCH_PROFILE_REQUIRED")
    for key, width in (
        ("source_commit", 40),
        ("handler_sha256", 64),
        ("dataset_sha256", 64),
        ("config_sha256", 64),
    ):
        if not isinstance(value[key], str) or not re.fullmatch(
            "[a-f0-9]{" + str(width) + "}", value[key]
        ):
            raise ValueError("RESEARCH_PINNED_IDENTITY_REQUIRED")
    for key in ("root", "python", "dataset", "config", "output_root"):
        text = value[key]
        if not isinstance(text, str) or "\0" in text or not Path(text).is_absolute():
            raise ValueError("RESEARCH_ABSOLUTE_OPERATOR_PATH_REQUIRED")
        p = Path(text)
        # Python may be the operator's normal venv executable symlink.
        if key != "python" and any(v.is_symlink() for v in (p, *p.parents)):
            raise ValueError("RESEARCH_SYMLINK_BLOCKED")
    root, output = Path(value["root"]).resolve(), Path(value["output_root"]).resolve()
    if not root.is_dir() or not Path(value["python"]).is_file():
        raise ValueError("RESEARCH_RUNTIME_REQUIRED")
    if (
        output == root
        or output.is_relative_to(root)
        or any(
            Path(value[k]).resolve().is_relative_to(output)
            for k in ("dataset", "config")
        )
    ):
        raise ValueError("RESEARCH_OUTPUT_BOUNDARY")
    if (
        type(value["timeout_seconds"]) is not int
        or not 1 <= value["timeout_seconds"] <= 600
    ):
        raise ValueError("RESEARCH_TIMEOUT_BUDGET_REQUIRED")
    for key in ("dataset", "config"):
        if sha_file(value[key]) != value[key + "_sha256"]:
            raise ValueError("RESEARCH_INPUT_DRIFT")
    if sha_file(root / SCRIPT) != value["handler_sha256"]:
        raise ValueError("RESEARCH_HANDLER_DRIFT")
    return value


def request_for(profile, job_id):
    if not isinstance(job_id, str) or not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise ValueError("RESEARCH_JOB_ID_REQUIRED")
    return {
        "schema": "studious.occ-research-request.v1",
        "run_id": job_id,
        **{
            k: profile[k]
            for k in (
                "source_commit",
                "dataset",
                "dataset_sha256",
                "config",
                "config_sha256",
                "output_root",
            )
        },
    }


def verify_receipt(profile, job_id):
    validate_profile(profile)
    request = request_for(profile, job_id)
    run = Path(profile["output_root"]) / job_id
    receipt = read_json(run / "receipt.json")
    manifest = read_json(run / "manifest.json")
    required = {
        "schema",
        "run_id",
        "request_sha256",
        "source_commit",
        "dataset_sha256",
        "config_sha256",
        "mode",
        "origin",
        "campaign_executed",
        "domain_status",
        "report",
        "trials_sha256",
        "live_enabled",
        "transactions_sent",
        "release_authorized",
        "receipt_sha256",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("RESEARCH_RECEIPT_SCHEMA")
    expected = digest(request)
    if (
        receipt["schema"] != "studious.occ-research-receipt.v1"
        or receipt["run_id"] != job_id
        or receipt["request_sha256"] != expected
        or any(
            receipt[k] != request[k]
            for k in ("source_commit", "dataset_sha256", "config_sha256")
        )
        or receipt["mode"] != "REPLAY"
        or receipt["origin"] != "OFFLINE_FIXTURE"
        or receipt["live_enabled"] is not False
        or type(receipt["transactions_sent"]) is not int
        or receipt["transactions_sent"] != 0
        or receipt["release_authorized"] is not False
        or digest({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        != receipt["receipt_sha256"]
        or manifest
        != {
            "state": "COMPLETE",
            "request_sha256": expected,
            "receipt_sha256": receipt["receipt_sha256"],
        }
    ):
        raise ValueError("RESEARCH_RECEIPT_BINDING_OR_EFFECTS")
    path = run / "trials.jsonl"
    actual = sha_file(path)
    report = receipt["report"]
    if not isinstance(report, dict) or any(
        type(report.get(k)) is not int or report[k] < 0
        for k in ("records", "handler_calls", "useful_calls", "transactions_sent")
    ):
        raise ValueError("RESEARCH_REPORT_INTEGER_COUNTS_REQUIRED")
    counts = Counter()
    records = calls = 0
    with path.open("rb") as stream:
        while raw := stream.readline(1024 * 1024 + 1):
            if len(raw) > 1024 * 1024:
                raise ValueError("RESEARCH_TRIAL_FRAME_BUDGET")
            trial = json.loads(raw)
            records += 1
            result = trial["result"]
            if (
                trial["ordinal"] != records
                or result["execution_right"] is not False
                or trial["origin"] != "OFFLINE_FIXTURE"
            ):
                raise ValueError("RESEARCH_TRIAL_SEQUENCE_OR_EFFECTS")
            status = result["status"]
            if status not in {
                "BLOCKED",
                "FAILED",
                "MODELED_CANDIDATE",
                "NO_CANDIDATE",
                "MODELED_MATCH",
                "NO_FEASIBLE_CLEARING",
            }:
                raise ValueError("RESEARCH_TRIAL_STATUS")
            counts[status] += 1
            if type(trial.get("handler_invoked")) is not bool:
                raise ValueError("RESEARCH_TRIAL_HANDLER_RECEIPT")
            calls += int(trial["handler_invoked"])
    if sha_file(path) != actual:
        raise ValueError("RESEARCH_TRIAL_ARTIFACT_CHANGED")
    useful = calls - counts.get("FAILED", 0)
    if (
        actual != receipt["trials_sha256"]
        or actual != report["decision_sha256"]
        or report["records"] != records
        or report["handler_calls"] != calls
        or report["useful_calls"] != useful
        or report["outcome_counts"] != dict(counts)
        or report["execution_right"] is not False
        or report["live_enabled"] is not False
        or type(report["transactions_sent"]) is not int
        or report["transactions_sent"] != 0
        or report["status"] != receipt["domain_status"]
        or receipt["campaign_executed"] is not (useful > 0)
    ):
        raise ValueError("RESEARCH_REPORT_TRIAL_MISMATCH")
    if (
        report["schema"] != "studious.occ-research-campaign.v1"
        or report["mode"] != "REPLAY"
        or report["origin"] != "OFFLINE_FIXTURE"
        or report["dataset_sha256"] != request["dataset_sha256"]
        or report["config_sha256"] != digest(read_json(profile["config"]))
        or report["campaign_executed"] is not (useful > 0)
        or type(report["pending"]) is not bool
    ):
        raise ValueError("RESEARCH_REPORT_INPUT_OR_MODE_MISMATCH")
    status = receipt["domain_status"]
    if status not in {"PARTIAL", "INVALID_CAMPAIGN", "MODEL_REPLAY_COMPLETED"}:
        raise ValueError("RESEARCH_DOMAIN_STATUS")
    if status == "MODEL_REPLAY_COMPLETED" and (
        useful == 0 or report["pending"] is not False
    ):
        raise ValueError("RESEARCH_EMPTY_OR_PARTIAL_CAMPAIGN")
    return {
        "domain_status": status,
        "receipt_sha256": receipt["receipt_sha256"],
        "dataset_sha256": receipt["dataset_sha256"],
        "config_sha256": receipt["config_sha256"],
        "source_commit": receipt["source_commit"],
        "trials_sha256": actual,
        "records": records,
        "handler_calls": calls,
        "useful_calls": useful,
        "outcome_counts": dict(counts),
        "verified_property": "frozen-offline-model-replay",
        "qualified": False,
        "live_enabled": False,
        "transactions_sent": 0,
        "release_authorized": False,
    }


def run(core, job):
    profile = validate_profile(
        core.policy["research"][job["payload"]["research_profile"]]
    )
    if Path(profile["output_root"]).resolve().is_relative_to(core.store.resolve()):
        raise ValueError("RESEARCH_OUTPUT_MUST_BE_OUTSIDE_STORE")
    requests = core.store / "research_requests"
    requests.mkdir(exist_ok=True)
    if requests.is_symlink():
        raise ValueError("RESEARCH_REQUEST_PATH_INVALID")
    request = request_for(profile, job["id"])
    path = requests / (job["id"] + ".json")
    # Exclusive immutable local intent precedes the subprocess effect.
    with path.open("xb") as output:
        output.write(canonical(request) + b"\n")
        output.flush()
        os.fsync(output.fileno())
    core.transition(job, "RUNNING", checkpoint={"request_sha256": digest(request)})
    process = core.command(
        job,
        [
            profile["python"],
            "-I",
            "-X",
            "utf8",
            str(Path(profile["root"]) / SCRIPT),
            "--request",
            str(path.resolve()),
        ],
        Path(profile["root"]),
        profile["timeout_seconds"],
    )
    if process["reason"] or process["exit_code"]:
        return "BLOCKED", {
            "reason": process["reason"] or "RESEARCH_COMMAND_FAILED",
            "process_exit_code": process["exit_code"],
            "qualified": False,
        }
    result = verify_receipt(profile, job["id"])
    result["process_exit_code"] = process["exit_code"]
    return (
        "SUCCEEDED"
        if result["domain_status"] == "MODEL_REPLAY_COMPLETED"
        else "BLOCKED"
    ), result


def jobs_page(store, policy, templates, *, offset=0, limit=20, snapshot=None):
    from automation_core import read_connection, digest as policy_digest, strict_int

    strict_int(offset, 0, 9_007_199_254_740_991)
    strict_int(limit, 1, 20)
    accepted = [v for v in templates.values() if v.get("kind") == "studious_research"]
    db = read_connection(store)
    try:
        db.execute("BEGIN")
        # Only scoped jobs; no policy, paths, lease tokens, command logs or sources.
        page = []
        total = 0
        hasher = hashlib.sha256()
        for row in db.execute(
            "SELECT * FROM jobs WHERE policy_hash=? ORDER BY id",
            (policy_digest(policy),),
        ):
            payload = json.loads(row["payload"])
            if payload not in accepted or row["payload_hash"] != policy_digest(payload):
                continue
            result = json.loads(row["result"]) if row["result"] else {}
            item = {
                "id": row["id"],
                "state": row["state"],
                "domain_status": result.get("domain_status"),
                "records": result.get("records", 0),
                "useful_calls": result.get("useful_calls", 0),
                "receipt_sha256": result.get("receipt_sha256"),
                "qualified": False,
            }
            hasher.update(canonical(item) + b"\n")
            if offset <= total < offset + limit:
                page.append(item)
            total += 1
        identity = hasher.hexdigest()
        if snapshot is not None and snapshot != identity:
            raise ValueError("RESEARCH_PAGE_SNAPSHOT_CHANGED")
        return {
            "schema": "occ.research-jobs-page.v1",
            "snapshot": identity,
            "offset": offset,
            "total": total,
            "items": page,
            "next_offset": offset + len(page) if offset + len(page) < total else None,
        }
    finally:
        db.close()
