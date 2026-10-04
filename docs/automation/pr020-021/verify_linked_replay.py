#!/usr/bin/env python3
"""Real pinned two-repository offline integration; output is model evidence only."""

from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

SCE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SCE / "content-lab"))
sys.path.insert(0, str(SCE))
import automation_core as core
import research_bridge as bridge
import product_qualification as qualification
from desktop.client import Connection, DesktopClient, PROTOCOL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studious", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    args = parser.parse_args()
    owner = args.studious.resolve()
    work = args.work_dir.resolve()
    if work.exists() or work.is_relative_to(owner) or work.is_relative_to(SCE):
        raise ValueError("EXCLUSIVE_EXTERNAL_WORK_DIR_REQUIRED")
    subprocess.run(
        ["git", "-C", str(owner), "diff", "--exit-code"],
        check=True,
        capture_output=True,
    )
    actual = (
        subprocess.check_output(["git", "-C", str(owner), "rev-parse", "HEAD"])
        .decode()
        .strip()
    )
    if actual != args.source_commit:
        raise ValueError("PINNED_OWNER_COMMIT_REQUIRED")
    sce_commit = (
        subprocess.check_output(["git", "-C", str(SCE), "rev-parse", "HEAD"])
        .decode()
        .strip()
    )
    if subprocess.check_output(
        ["git", "-C", str(SCE), "status", "--porcelain"]
    ).strip():
        raise ValueError("CLEAN_SCE_CHECKOUT_REQUIRED")
    work.mkdir(parents=True)
    # Use shipped fixture constructors; the actual command executes in -I child.
    sys.path.insert(0, str(owner))
    sys.path.insert(0, str(owner / "tests/market_data_evolution"))
    from test_occ_research_qualification import route, record, config, economics
    from src.mechanism_discovery.intent_graph import ClearingIntent

    payloads = {
        "circular_triangular": route(),
        "liquidation_swap": {
            "route": route(),
            "eligible_at_ns": 1,
            "oracle_available_at_ns": 1,
            "collateral_available_at_ns": 1,
            "actor_eligible": True,
        },
        "peg_wrapper": {
            "route": route(),
            "redemption_right": True,
            "redemption_delay_ns": 0,
            "liquidity_atoms": 1000,
        },
        "intent_clearing": {
            "intents": [
                asdict(ClearingIntent("left", "A", "B", 10, 10, 0, 100)),
                asdict(ClearingIntent("right", "B", "A", 10, 10, 0, 100)),
            ],
            "lot_sizes": [["A", 1], ["B", 1]],
        },
        "capital_timeline": {
            "strategy": "cross_chain",
            "capital_atoms": 1000,
            "economics": economics(),
            "stages": [
                {
                    "available_at_ns": 1,
                    "start_ns": 10,
                    "end_ns": 20,
                    "locked_atoms": 1000,
                    "cashflow_atoms": 100,
                    "settled": True,
                    "hedge_assumption": "offline fixture",
                }
            ],
        },
    }
    source_ledger = SCE / "docs/automation/pr020-021/CRITERION_LEDGER.json"
    ledger_sha = bridge.sha_file(source_ledger)
    holdout = work / "holdout.json"
    holdout.write_bytes(
        bridge.canonical(
            {"origin": "OFFLINE_FIXTURE", "partition": "BOUND_ONLY_NOT_EVALUATED"}
        )
    )
    profiles = {}
    templates = {}
    for pack, payload in payloads.items():
        data = work / (pack + ".jsonl")
        rows = [record(payload, i) for i in range(45)]
        rows.extend(
            [record(payload, 100, available=11), record({"invalid": True}, 101)]
        )
        data.write_bytes(b"".join(bridge.canonical(row) + b"\n" for row in rows))
        cfg = config(pack)
        cfg["criteria_sha256"] = ledger_sha
        cfg["holdout_sha256"] = bridge.sha_file(holdout)
        cfgfile = work / (pack + ".config.json")
        cfgfile.write_bytes(bridge.canonical(cfg))
        profiles[pack] = {
            "schema": "occ.research-profile.v1",
            "root": str(owner),
            "source_commit": actual,
            "python": str(args.python.absolute()),
            "handler_sha256": bridge.sha_file(owner / bridge.SCRIPT),
            "dataset": str(data),
            "dataset_sha256": bridge.sha_file(data),
            "config": str(cfgfile),
            "config_sha256": bridge.sha_file(cfgfile),
            "output_root": str(work / "runs"),
            "timeout_seconds": 120,
        }
        templates[pack] = {"kind": "studious_research", "research_profile": pack}
    policy = {
        "schema": "occ.automation-policy.v1",
        "max_parallel": 1,
        "money_budget": 0,
        "research": profiles,
    }
    store = work / "store"
    worker = core.Core(store, policy)
    # Fixture-only diagnostics: production receipts deliberately omit child output.
    last_command = {}
    original_command = worker.command

    def observed_command(*args):
        process = original_command(*args)
        last_command.clear()
        last_command.update({key: process.get(key) for key in ("exit_code", "reason", "output")})
        return process

    worker.command = observed_command
    jobs = []
    metrics = []
    for pack in payloads:
        for repeat in range(2):
            job = core.enqueue(store, policy, f"{pack}-{repeat}", templates[pack])
            start = time.monotonic_ns()
            result = worker.run_once()
            elapsed = time.monotonic_ns() - start
            if result["id"] != job["id"] or result["state"] != "SUCCEEDED":
                raise AssertionError({"job": result, "offline_fixture_child": last_command})
            receipt = result["result"]
            if (
                receipt["records"] != 47
                or receipt["useful_calls"] != 45
                or receipt["handler_calls"] != 46
                or receipt["qualified"] is not False
            ):
                raise AssertionError(receipt)
            if (
                receipt["outcome_counts"].get("FAILED") != 1
                or receipt["outcome_counts"].get("BLOCKED") != 1
            ):
                raise AssertionError(receipt)
            jobs.append(
                {"pack": pack, "repeat": repeat, "job_id": job["id"], **receipt}
            )
            metrics.append(
                {
                    "pack": pack,
                    "elapsed_ns": elapsed,
                    "records": receipt["records"],
                    "handler_calls": receipt["handler_calls"],
                }
            )
        if jobs[-1]["trials_sha256"] != jobs[-2]["trials_sha256"]:
            raise AssertionError("REPLAY_DIVERGED")
    # Installed sibling layout from the shipped Windows installer, exercised -I.
    installed = work / "installed/content-lab"
    installed.mkdir(parents=True)
    installer = (SCE / "agent-bridge/Install.ps1").read_text(encoding="utf-8")
    files = re.search(r"foreach\(\$occFile in @\((.*?)\)\)", installer).group(1)
    for name in re.findall(r"'([^']+)'", files):
        shutil.copyfile(SCE / "content-lab" / name, installed / name)
    for package in ("occ_v4", "occ_v5", "js-parser", "js-contracts"):
        shutil.copytree(
            SCE / "content-lab" / package,
            installed / package,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    policyfile = work / "policy.json"
    policyfile.write_text(core.encoded(policy), encoding="utf-8")
    profilefile = work / "profile.json"
    profilefile.write_text(
        core.encoded(
            {
                "schema": "occ.native-durable-profile.v1",
                "store": str(store),
                "policy_file": str(policyfile),
                "namespaces": ["research"],
                "templates": templates,
            }
        ),
        encoding="utf-8",
    )
    adapter = installed / "native_adapter.py"
    connection = Connection.from_dict(
        {
            "schema": "occ.desktop-connection.v1",
            "protocol": PROTOCOL,
            "python_path": str(args.python.absolute()),
            "adapter_path": str(adapter),
            "expected_adapter_sha256": bridge.sha_file(adapter),
            "profile_path": str(profilefile),
            "preferred_namespace": "research",
        }
    )
    client = DesktopClient(connection)
    try:
        client.handshake()
        page = client.request({"type": "durable.research.jobs", "limit": 20})["result"][
            "research"
        ]
        if page["total"] != 10 or len(page["items"]) != 10:
            raise AssertionError(page)
    finally:
        client.close()
    qualification.import_catalog(store, source_ledger, ledger_sha)
    scope = {
        "build": actual,
        "config": profiles["circular_triangular"]["config_sha256"],
        "dataset": profiles["circular_triangular"]["dataset_sha256"],
        "environment": sys.platform + "-offline-model",
    }
    report = qualification.reconcile(store, ledger_sha, scope)
    if report["total"] != 1133 or report["counts"] != {"OPEN": 1133}:
        raise AssertionError("FALSE_CRITERION_CLOSURE")
    if (
        subprocess.check_output(["git", "-C", str(SCE), "rev-parse", "HEAD"])
        .decode()
        .strip()
        != sce_commit
        or subprocess.check_output(
            ["git", "-C", str(SCE), "status", "--porcelain"]
        ).strip()
    ):
        raise ValueError("SCE_SOURCE_DRIFT")
    summary = {
        "schema": "occ.linked-replay-validation.v1",
        "status": "OFFLINE_INTEGRATION_PASS",
        "studious_commit": actual,
        "sce_commit": sce_commit,
        "origin": "OFFLINE_FIXTURE",
        "packs": len(payloads),
        "campaigns": len(jobs),
        "records": sum(j["records"] for j in jobs),
        "useful_calls": sum(j["useful_calls"] for j in jobs),
        "exact_repeat_pairs": 5,
        "installed_sibling_transport": "PASS",
        "desktop_read_jobs": page["total"],
        "criterion_count": report["total"],
        "criterion_status_counts": report["counts"],
        "qualified": False,
        "live_enabled": False,
        "transactions_sent": 0,
        "windows_dell_installed": "NOT_RUN",
        "limitations": [
            "Offline model integration only",
            "Holdout partition bound but not evaluated",
            "No market usefulness benchmark or real acquisition",
        ],
        "jobs": jobs,
        "timings": metrics,
    }
    (work / "validation.json").write_bytes(bridge.canonical(summary) + b"\n")
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k not in {"jobs", "timings"}},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
