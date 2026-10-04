"""Offline, stdlib qualification evidence evaluator. Never sends network traffic or transactions.
TRUE means only configured predicates passed on supplied machine artifacts. It is
not authentication of the artifact producer, a code audit or live authorization.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

SCHEMA = "web3-qualification/v1"
DIGEST = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
ADAPTERS = {"inventory_diff.v1", "junit_xml.v1", "economics_samples.v1", "observation_window.v1", "stop_latency.v1"}
REQUIRED_ROLES = {
    "inventory_diff.v1": {"expected_manifest", "observed_manifest"},
    "junit_xml.v1": {"test_results"},
    "economics_samples.v1": {"economics"},
    "observation_window.v1": {"observations"},
    "stop_latency.v1": {"stop_probes"},
}

class EvidenceError(ValueError):
    pass


def reject_constants(value):
    raise EvidenceError("Non-finite JSON number: " + value)


def unique_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise EvidenceError("Duplicate JSON key: " + key)
        obj[key] = value
    return obj


def json_loads(value):
    return json.loads(value, object_pairs_hook=unique_keys, parse_constant=reject_constants)


def read_json(path):
    return json_loads(Path(path).read_text(encoding="utf-8"))


def canonical_hash(obj):
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc(value):
    if not isinstance(value, str):
        raise EvidenceError("Timestamp must be an ISO string")
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise EvidenceError("Timestamp timezone missing")
    return stamp.astimezone(dt.timezone.utc)


def number(value, key, minimum=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EvidenceError(key + " must be a finite number, not a boolean")
    if integer and not isinstance(value, int):
        raise EvidenceError(key + " must be an integer")
    if minimum is not None and value < minimum:
        raise EvidenceError(key + " below minimum")
    return value


def text_value(value, key):
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(key + " must be non-empty text")
    return value


def local_path(root, relative):
    """Portable paths: refuse absolute, drive, backslash, traversal and symlinks.
    A caller must not concurrently mutate the evidence directory while evaluating.
    """
    if not isinstance(relative, str) or not relative or "\x00" in relative or "\\" in relative:
        raise EvidenceError("Unsafe artifact path")
    path = PurePosixPath(relative)
    if path.is_absolute() or PureWindowsPath(relative).drive or ".." in path.parts or ":" in relative:
        raise EvidenceError("Artifact path escapes evidence root")
    base = Path(root).resolve(strict=True)
    candidate = base.joinpath(*path.parts)
    for n in range(1, len(path.parts) + 1):
        if base.joinpath(*path.parts[:n]).is_symlink():
            raise EvidenceError("Symlink evidence path refused")
    candidate = candidate.resolve(strict=True)
    if not candidate.is_relative_to(base) or not candidate.is_file():
        raise EvidenceError("Artifact is not a regular contained file")
    return candidate


def rows(path):
    count = 0
    with Path(path).open(encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json_loads(line)
            if not isinstance(row, dict):
                raise EvidenceError(f"Line {lineno} is not an object")
            count += 1
            yield row
    if not count:
        raise EvidenceError("Empty observation artifact")


def validate_binding(binding):
    if not isinstance(binding, dict) or not REVISION.fullmatch(binding.get("repo_revision", "")):
        raise EvidenceError("Exact 40/64 hex repo_revision required")
    for key in ("config_sha256", "input_manifest_sha256", "environment_sha256"):
        if not DIGEST.fullmatch(binding.get(key, "")):
            raise EvidenceError(key + " requires sha256")
    for object_key, keys in {
        "network": ("family", "network_id", "genesis_hash"),
        "anchor": ("height", "hash", "finality"),
        "provider": ("id", "version"),
        "model": ("id", "revision"),
    }.items():
        obj = binding.get(object_key)
        if not isinstance(obj, dict):
            raise EvidenceError(object_key + " missing")
        for key in keys:
            text_value(obj.get(key), object_key + "." + key)
    if binding["network"]["family"] not in {"evm", "solana", "unknown", "offline_fixture"}:
        raise EvidenceError("Unknown network family")
    toolchain = binding.get("toolchain")
    if not isinstance(toolchain, dict) or not toolchain:
        raise EvidenceError("Exact toolchain versions required")
    for key, value in toolchain.items():
        text_value(value, "toolchain." + key)


def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise EvidenceError("Invalid plan schema")
    text_value(plan.get("campaign_id"), "campaign_id")
    if plan.get("live_authorized") is not False:
        raise EvidenceError("This offline evaluator requires live_authorized=false")
    validate_binding(plan.get("binding"))
    stages = plan.get("stages")
    if not isinstance(stages, list) or not stages:
        raise EvidenceError("Non-empty stages required")
    seen = set()
    for stage in stages:
        sid = text_value(stage.get("id"), "stage.id")
        if sid in seen:
            raise EvidenceError("Duplicate stage id")
        adapter = stage.get("adapter")
        if adapter not in ADAPTERS:
            raise EvidenceError("Unimplemented adapter: " + str(adapter))
        deps = stage.get("depends_on")
        if not isinstance(deps, list) or len(deps) != len(set(deps)) or any(d not in seen for d in deps):
            raise EvidenceError("Stages must be ordered DAG; dependency unknown/duplicate/cyclic")
        number(stage.get("max_age_seconds"), "max_age_seconds", 1)
        producer = stage.get("producer")
        if not isinstance(producer, dict):
            raise EvidenceError("Pinned producer required")
        for key in ("id", "version"):
            text_value(producer.get(key), "producer." + key)
        if not DIGEST.fullmatch(producer.get("binary_sha256", "")):
            raise EvidenceError("Pinned producer binary_sha256 required")
        c = stage.get("criteria")
        if not isinstance(c, dict):
            raise EvidenceError("criteria required")
        required = {
            "inventory_diff.v1": {"min_entries"},
            "junit_xml.v1": {"min_cases", "required_name_fragments"},
            "economics_samples.v1": {"min_samples", "min_accepted", "max_quote_age_ms", "min_net_minor", "accounting_unit"},
            "observation_window.v1": {"min_samples", "min_duration_seconds", "max_gap_seconds", "min_providers", "max_source_age_ms", "mode"},
            "stop_latency.v1": {"min_probes", "max_stop_latency_ms", "required_faults"},
        }[adapter]
        if set(c) != required:
            raise EvidenceError("Missing or unsupported criteria: " + adapter)
        for key in required:
            if key.startswith("min_") or key.startswith("max_"):
                minimum = 1 if key in {"min_entries", "min_cases", "min_samples", "min_probes", "min_providers"} else 0
                number(c[key], key, minimum if key != "min_net_minor" else None,
                       integer=key in {"min_entries", "min_cases", "min_samples", "min_accepted", "min_probes", "min_providers", "min_net_minor"})
        for key in ("required_name_fragments", "required_faults"):
            if key in c and (not isinstance(c[key], list) or not c[key] or any(not isinstance(i, str) or not i for i in c[key])):
                raise EvidenceError(key + " must name required coverage cases")
        if "accounting_unit" in c:
            text_value(c["accounting_unit"], "accounting_unit")
        if "mode" in c and c["mode"] not in {"REAL_MARKET_PAPER_OBSERVATION", "OFFLINE_REPLAY"}:
            raise EvidenceError("Observation mode must be exact")
        seen.add(sid)


def inventory(artifacts, c, binding):
    def index(role):
        result = {}
        for row in rows(artifacts[role]):
            path = text_value(row.get("path"), "entry path")
            ordinal = number(row.get("ordinal"), "ordinal", 0, integer=True)
            key = (path, ordinal)
            if key in result:
                raise EvidenceError("Duplicate path/ordinal in inventory")
            if not DIGEST.fullmatch(row.get("sha256", "")):
                raise EvidenceError("Invalid entry sha256")
            size = number(row.get("bytes"), "entry bytes", 0, integer=True)
            result[key] = (row["sha256"], size)
        return result
    expected, observed = index("expected_manifest"), index("observed_manifest")
    failures = []
    if len(expected) < c["min_entries"]:
        failures.append("Too few inventory entries")
    if expected != observed:
        failures.append("Inventory omissions, additions or byte/hash mismatches")
    return {"expected_entries": len(expected), "observed_entries": len(observed), "missing": len(set(expected)-set(observed)), "extra": len(set(observed)-set(expected))}, failures


def junit(artifacts, c, binding):
    data = artifacts["test_results"].read_bytes()
    declarations = data.upper().replace(b"\x00", b"")  # Also catch UTF-16/32 declarations.
    if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
        raise EvidenceError("DTD/entities refused")
    root = ET.fromstring(data)
    if root.tag not in {"testsuite", "testsuites"}:
        raise EvidenceError("Invalid JUnit root")
    cases = list(root.iter("testcase"))
    ids, failed, skipped = set(), 0, 0
    for case in cases:
        name = text_value(case.get("name"), "testcase.name")
        cls = text_value(case.get("classname"), "testcase.classname")
        if (cls, name) in ids:
            raise EvidenceError("Duplicate JUnit testcase identity")
        ids.add((cls, name))
        failed += bool(case.findall("failure") or case.findall("error") or case.get("status", "").lower() in {"failed", "error"})
        skipped += bool(case.findall("skipped") or case.get("status", "").lower() in {"notrun", "disabled", "skipped"} or case.get("result", "").lower() in {"suppressed", "skipped"})
    names = [cls + "." + name for cls, name in ids]
    missing = [q for q in c["required_name_fragments"] if not any(q in name for name in names)]
    failures = []
    if len(cases) - skipped < c["min_cases"]: failures.append("Insufficient executed testcases")
    suite_errors = sum(len(s.findall("error")) + len(s.findall("failure")) for s in root.iter("testsuite"))
    if failed or suite_errors: failures.append("Test failures or suite errors")
    for suite in root.iter():
        if suite.tag not in {"testsuite", "testsuites"}:
            continue
        descendants = list(suite.iter("testcase"))
        counters = {"tests": len(descendants),
                    "failures": sum(bool(case.findall("failure")) for case in descendants),
                    "errors": sum(bool(case.findall("error")) for case in descendants),
                    "skipped": sum(bool(case.findall("skipped")) for case in descendants)}
        for key, observed_count in counters.items():
            declared = suite.get(key)
            if declared is not None:
                if not declared.isdecimal():
                    raise EvidenceError("Non-integer JUnit aggregate counter: " + key)
                if int(declared) != observed_count:
                    if failed or suite_errors or skipped:
                        failures.append("JUnit aggregate counter disagrees with known failing/skipped testcase records: " + key)
                    else:
                        raise EvidenceError("JUnit aggregate counter disagrees with testcase records: " + key)
        if suite.get("disabled") is not None:
            if not suite.get("disabled").isdecimal():
                raise EvidenceError("Invalid JUnit disabled counter")
            if int(suite.get("disabled")):
                failures.append("Disabled testcases are not qualifying")
    if skipped: failures.append("Skipped testcases are not qualifying")
    if missing: failures.append("Required testcase coverage missing")
    return {"cases": len(cases), "failed": failed, "suite_errors": suite_errors, "skipped": skipped, "missing_name_fragments": missing}, failures


def economics(artifacts, c, binding):
    count, accepted, breaches, ids, minimum = 0, 0, [], set(), None
    for row in rows(artifacts["economics"]):
        sid = text_value(row.get("sample_id"), "sample_id")
        if sid in ids: raise EvidenceError("Duplicate economics sample")
        ids.add(sid)
        if row.get("accounting_unit") != c["accounting_unit"]:
            raise EvidenceError("Accounting units differ")
        # All terms must already be converted into the same explicitly declared
        # atomic accounting unit by the recorded adapter; no implicit floats.
        values = {k: number(row.get(k), k, 0, integer=True) for k in (
            "proceeds_minor", "principal_minor", "flash_fee_minor", "swap_fee_minor",
            "network_fee_minor", "slippage_reserve_minor", "other_cost_minor")}
        age = number(row.get("quote_age_ms"), "quote_age_ms", 0)
        decision = row.get("decision")
        if decision not in {"ACCEPT", "REJECT"}: raise EvidenceError("Unrecognized candidate decision")
        net = values["proceeds_minor"] - sum(v for k, v in values.items() if k != "proceeds_minor")
        count += 1
        if decision == "ACCEPT":
            accepted += 1
            minimum = net if minimum is None else min(minimum, net)
            if net < c["min_net_minor"] or age > c["max_quote_age_ms"]:
                breaches.append(sid)
    failures = []
    if count < c["min_samples"]: failures.append("Too few economic samples")
    if accepted < c["min_accepted"]: failures.append("Too few accepted candidates for this experiment")
    if breaches: failures.append("Accepted candidate violates net-cost or freshness predicate")
    return {"samples": count, "accepted": accepted, "minimum_accepted_net_minor": minimum, "breach_sample_ids": breaches}, failures


def observation(artifacts, c, binding):
    times, providers, seen, breaches = [], set(), set(), []
    for row in rows(artifacts["observations"]):
        sid = text_value(row.get("sample_id"), "sample_id")
        if sid in seen: raise EvidenceError("Duplicate observation sample")
        seen.add(sid)
        if row.get("mode") != c["mode"]:
            raise EvidenceError("Observation mode mismatch: replay is not market observation")
        if row.get("network_id") != binding["network"]["network_id"]:
            raise EvidenceError("Observation network mismatch")
        text_value(row.get("anchor_hash"), "observation anchor_hash")
        text_value(row.get("height"), "observation height")
        if row.get("finality") != binding["anchor"]["finality"]:
            raise EvidenceError("Observation finality policy mismatch")
        observed, source = utc(row.get("observed_at")), utc(row.get("source_at"))
        if times and observed < times[-1]: raise EvidenceError("Observation time went backwards")
        times.append(observed)
        providers.add(text_value(row.get("provider_id"), "provider_id"))
        source_age = (observed - source).total_seconds() * 1000
        if source_age < 0 or source_age > c["max_source_age_ms"]:
            breaches.append(sid)
        if number(row.get("signed_transactions"), "signed_transactions", 0, integer=True) != 0 or number(row.get("sent_transactions"), "sent_transactions", 0, integer=True) != 0:
            breaches.append(sid + ":paper_sent_or_signed")
    duration = (times[-1] - times[0]).total_seconds()
    gap = max(((b-a).total_seconds() for a,b in zip(times,times[1:])), default=0)
    failures = []
    if len(times) < c["min_samples"]: failures.append("Too few observation samples")
    if duration < c["min_duration_seconds"]: failures.append("Observation window too short")
    if gap > c["max_gap_seconds"]: failures.append("Observation gap exceeds budget")
    if len(providers) < c["min_providers"]: failures.append("Insufficient distinct provider identifiers")
    if breaches: failures.append("Source freshness or paper-only contract violated")
    return {"samples": len(times), "first_observed_at": times[0].isoformat(), "last_observed_at": times[-1].isoformat(), "duration_seconds": duration, "max_gap_seconds": gap, "provider_ids": sorted(providers), "breach_sample_ids": breaches}, failures


def stop_latency(artifacts, c, binding):
    latencies, faults, seen, dispatches = [], set(), set(), 0
    for row in rows(artifacts["stop_probes"]):
        sid = text_value(row.get("probe_id"), "probe_id")
        if sid in seen: raise EvidenceError("Duplicate stop probe")
        seen.add(sid)
        fault = text_value(row.get("fault"), "fault")
        trigger = number(row.get("trigger_monotonic_ns"), "trigger_monotonic_ns", 0, integer=True)
        stopped = number(row.get("blocked_monotonic_ns"), "blocked_monotonic_ns", trigger, integer=True)
        dispatches += number(row.get("forbidden_dispatches_after_trigger"), "forbidden_dispatches_after_trigger", 0, integer=True)
        latencies.append((stopped-trigger) / 1_000_000)
        faults.add(fault)
    missing = sorted(set(c["required_faults"])-faults)
    failures = []
    if len(latencies) < c["min_probes"]: failures.append("Insufficient stop probes")
    if max(latencies) > c["max_stop_latency_ms"]: failures.append("Stop latency exceeded")
    if dispatches: failures.append("Forbidden dispatch observed after trigger")
    if missing: failures.append("Required injected faults not covered")
    return {"probes": len(latencies), "max_stop_latency_ms": max(latencies), "forbidden_dispatches": dispatches, "missing_faults": missing}, failures


VALIDATORS = {"inventory_diff.v1": inventory, "junit_xml.v1": junit, "economics_samples.v1": economics,
              "observation_window.v1": observation, "stop_latency.v1": stop_latency}


def aggregate(states):
    for state in ("FALSE", "UNKNOWN", "NOT_RUN"):
        if state in states: return state
    return "TRUE"


def evaluate(plan, receipts, root, now=None):
    validate_plan(plan)
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None: raise EvidenceError("now requires timezone")
    plan_hash = canonical_hash(plan)
    candidates = {s["id"]: [] for s in plan["stages"]}
    unknown_receipts = []
    for receipt in receipts:
        if not isinstance(receipt, dict): raise EvidenceError("Receipt must be object")
        if receipt.get("stage_id") in candidates:
            candidates[receipt["stage_id"]].append(receipt)
        else:
            unknown_receipts.append(receipt.get("stage_id"))
    result = {"schema": SCHEMA + "/report", "evaluated_at": now.isoformat(), "campaign_id": plan["campaign_id"],
              "plan_sha256": plan_hash, "binding_sha256": canonical_hash(plan["binding"]), "stages": [],
              "ignored_unknown_stage_receipts": unknown_receipts,
              "live_authorized": False, "ready_for_live": False, "actual_bot_execution": "NOT_RUN",
              "producer_authenticity": "UNKNOWN", "attestation_authenticated": False, "external_chain_truth": "UNKNOWN",
              "trust_statement": "TRUE only verifies configured predicates on supplied artifacts; hashes do not prove producer honesty or chain truth."}
    by_id = {}
    for stage in plan["stages"]:
        sid = stage["id"]
        out = {"id": sid, "adapter": stage["adapter"], "own_status": "NOT_RUN", "status": "NOT_RUN", "reasons": [], "metrics": {}, "live_authorized": False}
        options = candidates[sid]
        if len(options) > 1:
            out.update(own_status="UNKNOWN", reasons=["Multiple receipts for same stage; select explicit campaign attempt"])
        elif len(options) == 1:
            receipt = options[0]
            try:
                if receipt.get("schema") != SCHEMA + "/receipt": raise EvidenceError("Receipt schema mismatch")
                if receipt.get("campaign_id") != plan["campaign_id"] or receipt.get("plan_sha256") != plan_hash:
                    raise EvidenceError("Receipt campaign/plan mismatch; invalidate previous evidence")
                if receipt.get("binding") != plan["binding"]:
                    raise EvidenceError("Repository/config/input/network/anchor/provider/model/toolchain binding differs")
                if receipt.get("adapter") != stage["adapter"]:
                    raise EvidenceError("Receipt adapter mismatch")
                if receipt.get("producer") != dict(stage["producer"], kind="machine_runner"):
                    raise EvidenceError("Unpinned producer; model text is not machine evidence")
                started, completed = utc(receipt.get("started_at")), utc(receipt.get("completed_at"))
                if completed < started or completed > now or started > now:
                    raise EvidenceError("Receipt time ordering invalid/future dated")
                if (now - completed).total_seconds() > stage["max_age_seconds"]:
                    raise EvidenceError("Receipt stale; recollect for current plan")
                process = receipt.get("process")
                if not isinstance(process, dict) or process.get("state") != "EXITED":
                    raise EvidenceError("No completed machine process")
                exit_code = number(process.get("exit_code"), "exit_code", integer=True)
                if exit_code != 0:
                    out.update(own_status="FALSE", reasons=["Runner process exited with nonzero status"])
                else:
                    artifact_records = receipt.get("artifacts")
                    if not isinstance(artifact_records, list): raise EvidenceError("artifacts must be array")
                    artifacts = {}
                    integrity_failure = []
                    for item in artifact_records:
                        role = text_value(item.get("role"), "artifact role")
                        if role in artifacts: raise EvidenceError("Duplicate artifact role")
                        path = local_path(root, item.get("path"))
                        size = number(item.get("bytes"), "artifact bytes", 0, integer=True)
                        digest = item.get("sha256", "")
                        if not DIGEST.fullmatch(digest): raise EvidenceError("Invalid artifact sha256")
                        if path.stat().st_size != size or file_hash(path) != digest:
                            integrity_failure.append(role)
                        artifacts[role] = path
                    if integrity_failure:
                        out.update(own_status="FALSE", reasons=["Artifact byte/hash mismatch: " + ",".join(integrity_failure)])
                    elif not REQUIRED_ROLES[stage["adapter"]].issubset(artifacts):
                        raise EvidenceError("Required machine artifact missing")
                    else:
                        metrics, failures = VALIDATORS[stage["adapter"]](artifacts, stage["criteria"], plan["binding"])
                        if stage["adapter"] == "observation_window.v1" and (utc(metrics["first_observed_at"]) < started or utc(metrics["last_observed_at"]) > completed):
                            raise EvidenceError("Observation timestamps outside recorded process window")
                        out.update(own_status="FALSE" if failures else "TRUE", metrics=metrics, reasons=failures)
            except (EvidenceError, ValueError, OSError, TypeError, KeyError, AttributeError, ET.ParseError) as exc:
                out.update(own_status="UNKNOWN", reasons=[str(exc)])
        else:
            out["reasons"].append("No explicit receipt supplied")
        deps = {dep: by_id[dep]["status"] for dep in stage["depends_on"]}
        out["dependencies"] = deps
        out["status"] = aggregate([out["own_status"], *deps.values()])
        out["eligible_for_next_stage"] = out["status"] == "TRUE"
        if any(s != "TRUE" for s in deps.values()):
            out["reasons"].append("Dependency evidence does not qualify")
        by_id[sid] = out
        result["stages"].append(out)
    result["configured_predicates"] = aggregate([s["status"] for s in result["stages"]])
    return result


def write_report(path, encoded, evidence_root, input_paths=()):
    """Publish a complete NEW report outside all input locations, without clobber.
    Hard-link publication is exclusive and atomic; unsupported filesystems fail safe.
    """
    destination = Path(path).resolve()
    evidence = Path(evidence_root).resolve()
    if destination.is_relative_to(evidence):
        raise EvidenceError("Report output must be outside read-only evidence root")
    if any(destination == Path(item).resolve() for item in input_paths):
        raise EvidenceError("Report output may not overwrite plan or receipt inputs")
    if destination.exists():
        raise EvidenceError("Report output already exists; choose a new filename")
    descriptor, temp_name = tempfile.mkstemp(prefix=".qualification-report-", dir=destination.parent)
    temporary = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Reviewed qualification plan JSON")
    parser.add_argument("--evidence-root", required=True, help="Read-only directory containing receipt artifacts")
    parser.add_argument("--receipt", action="append", default=[], help="Explicit receipt JSON path; may repeat")
    parser.add_argument("--now", help="ISO timestamp only for reproducible offline experiments")
    parser.add_argument("--output", help="Report JSON file; stdout if omitted")
    args = parser.parse_args()
    try:
        report = evaluate(read_json(args.plan), [read_json(p) for p in args.receipt], args.evidence_root, utc(args.now) if args.now else None)
        encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            write_report(args.output, encoded, args.evidence_root, [args.plan, *args.receipt])
        else:
            print(encoded, end="")
        return 0 if report["configured_predicates"] == "TRUE" else 2
    except (EvidenceError, ValueError, OSError, TypeError) as exc:
        print("Qualification input invalid: " + str(exc), file=sys.stderr)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
