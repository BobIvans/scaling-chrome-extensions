"""Criterion preservation and evidence reconciliation in the canonical SCE store.

Text claims, DEFERRED and artifact existence cannot close a semantic criterion.
Verified replay evidence is retained as a fact; broad V5 acceptance remains OPEN.
"""

from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from automation_core import connection, read_connection, identifier, encoded
from research_bridge import digest, sha_file, read_json, verify_receipt

STATUSES = {"OPEN", "NOT_RUN", "FAIL", "BLOCKED", "DEFERRED", "CONFLICT"}


def initialize(db):
    db.executescript("""
      CREATE TABLE IF NOT EXISTS qualification_catalogs(
        id TEXT PRIMARY KEY, payload TEXT NOT NULL, imported REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS qualification_criteria(
        catalog_id TEXT NOT NULL, criterion_id TEXT NOT NULL, payload TEXT NOT NULL,
        PRIMARY KEY(catalog_id, criterion_id));
      CREATE TABLE IF NOT EXISTS qualification_claims(
        id TEXT PRIMARY KEY, catalog_id TEXT NOT NULL, criterion_id TEXT NOT NULL,
        status TEXT NOT NULL, property TEXT NOT NULL, scope TEXT NOT NULL,
        evidence TEXT NOT NULL, observed REAL NOT NULL);
    """)


def import_catalog(store, path, expected_sha256):
    if sha_file(path) != expected_sha256:
        raise ValueError("QUALIFICATION_CATALOG_DRIFT")
    raw = read_json(path, limit=20_000_000)
    if raw.get("schema") != "proposed.criterion-ledger.v1" or not isinstance(
        raw.get("criteria"), list
    ):
        raise ValueError("QUALIFICATION_CATALOG_SCHEMA")
    ids = set()
    for row in raw["criteria"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("criterion_id"), str)
            or row["criterion_id"] in ids
            or not isinstance(row.get("exact_text"), str)
            or hashlib.sha256(row["exact_text"].encode("utf-8")).hexdigest()
            != row.get("text_sha256")
            or row.get("status") != "OPEN"
            or row.get("mandatory_in_source_catalog") is not True
        ):
            raise ValueError("QUALIFICATION_CRITERION_ID_TEXT_OR_STATUS")
        ids.add(row["criterion_id"])
    if len(ids) != raw.get("criterion_count") or not ids:
        raise ValueError("QUALIFICATION_CATALOG_INCOMPLETE")
    if sha_file(path) != expected_sha256:
        raise ValueError("QUALIFICATION_CATALOG_DRIFT")
    db = connection(store)
    try:
        initialize(db)
        with db:
            old = db.execute(
                "SELECT payload FROM qualification_catalogs WHERE id=?",
                (expected_sha256,),
            ).fetchone()
            if old is not None and json.loads(old[0]) != raw:
                raise ValueError("QUALIFICATION_CATALOG_CONFLICT")
            db.execute(
                "INSERT OR IGNORE INTO qualification_catalogs VALUES (?,?,?)",
                (expected_sha256, encoded(raw), time.time()),
            )
            for row in raw["criteria"]:
                db.execute(
                    "INSERT OR IGNORE INTO qualification_criteria VALUES (?,?,?)",
                    (expected_sha256, row["criterion_id"], encoded(row)),
                )
        return {
            "catalog_sha256": expected_sha256,
            "criteria": len(ids),
            "status": "OPEN",
            "reused": old is not None,
        }
    finally:
        db.close()


def record_claim(
    store, catalog_id, criterion_id, *, status, property_name, scope, evidence
):
    # Manual claims are dispositions, not proofs. Applicable evidence has exact scope.
    if (
        status not in STATUSES
        or not isinstance(scope, dict)
        or set(scope) != {"build", "config", "dataset", "environment"}
    ):
        raise ValueError("QUALIFICATION_CLAIM_STATUS_OR_SCOPE")
    if not all(isinstance(v, str) and v for v in scope.values()):
        raise ValueError("QUALIFICATION_CLAIM_EXACT_SCOPE_REQUIRED")
    identifier(property_name)
    if not isinstance(evidence, dict):
        raise ValueError("QUALIFICATION_CLAIM_EVIDENCE")
    payload = {
        "catalog": catalog_id,
        "criterion": criterion_id,
        "status": status,
        "property": property_name,
        "scope": scope,
        "evidence": evidence,
    }
    claim = digest(payload)
    db = connection(store)
    try:
        initialize(db)
        with db:
            if not db.execute(
                "SELECT 1 FROM qualification_criteria WHERE catalog_id=? AND criterion_id=?",
                (catalog_id, criterion_id),
            ).fetchone():
                raise ValueError("QUALIFICATION_UNKNOWN_CRITERION")
            db.execute(
                "INSERT OR IGNORE INTO qualification_claims VALUES (?,?,?,?,?,?,?,?)",
                (
                    claim,
                    catalog_id,
                    criterion_id,
                    status,
                    property_name,
                    encoded(scope),
                    encoded(evidence),
                    time.time(),
                ),
            )
        return claim
    finally:
        db.close()


def record_replay_fact(store, catalog_id, criterion_id, profile, job_id, environment):
    receipt = verify_receipt(profile, job_id)
    if receipt["domain_status"] != "MODEL_REPLAY_COMPLETED":
        raise ValueError("QUALIFICATION_REPLAY_INCOMPLETE")
    # The verifier checks offline execution. It cannot verify the semantics of
    # an arbitrary V5 criterion, Windows installation, real acquisition or profit.
    return record_claim(
        store,
        catalog_id,
        criterion_id,
        status="OPEN",
        property_name="frozen-offline-model-replay",
        scope={
            "build": receipt["source_commit"],
            "config": receipt["config_sha256"],
            "dataset": receipt["dataset_sha256"],
            "environment": environment,
        },
        evidence={
            "verified_property": receipt["verified_property"],
            "receipt_sha256": receipt["receipt_sha256"],
            "criterion_semantics_verified": False,
            "qualified": False,
        },
    )


def reconcile(store, catalog_id, scope):
    if not isinstance(scope, dict) or set(scope) != {
        "build",
        "config",
        "dataset",
        "environment",
    }:
        raise ValueError("QUALIFICATION_CURRENT_SCOPE_REQUIRED")
    db = read_connection(store)
    try:
        db.execute("BEGIN")
        catalog = db.execute(
            "SELECT payload FROM qualification_catalogs WHERE id=?", (catalog_id,)
        ).fetchone()
        if catalog is None:
            raise ValueError("QUALIFICATION_UNKNOWN_CATALOG")
        source = json.loads(catalog[0])
        out = []
        counts = Counter()
        for row in db.execute(
            "SELECT * FROM qualification_criteria WHERE catalog_id=? ORDER BY criterion_id",
            (catalog_id,),
        ):
            item = json.loads(row["payload"])
            claims = []
            stale = 0
            for claim in db.execute(
                "SELECT * FROM qualification_claims WHERE catalog_id=? AND criterion_id=? ORDER BY id",
                (catalog_id, row["criterion_id"]),
            ):
                if json.loads(claim["scope"]) != scope:
                    stale += 1
                    continue
                claims.append(dict(claim))
            dispositions = {c["status"] for c in claims}
            properties = {}
            for claim in claims:
                properties.setdefault(claim["property"], set()).add(
                    digest(json.loads(claim["evidence"]))
                )
            contradictory = any(len(values) > 1 for values in properties.values())
            status = (
                "CONFLICT"
                if len(dispositions) > 1 or contradictory
                else next(iter(dispositions), "OPEN")
            )
            item.update(
                status=status,
                applicable_claim_ids=[c["id"] for c in claims],
                stale_claims=stale,
                delivered=None,
                installed=None,
                usable=None,
            )
            out.append(item)
            counts[status] += 1
        if len(out) != source["criterion_count"]:
            raise ValueError("QUALIFICATION_CANONICAL_ROWS_INCOMPLETE")
        return {
            "schema": "occ.product-reconciliation.v1",
            "catalog_sha256": catalog_id,
            "scope": scope,
            "criteria": out,
            "counts": dict(counts),
            "total": len(out),
            "qualified": False,
            "reason": "SEMANTIC_CRITERION_VERIFIERS_AND_APPLICABLE_DEVICE_RECEIPTS_REQUIRED",
        }
    finally:
        db.close()


def benchmark(config, attempts):
    """All started attempts cost the frozen baseline, including failures/cancels.

    This arithmetic is a model evaluator, not an attestation of supplied metrics.
    """
    if not isinstance(config, dict) or set(config) != {
        "baseline_sha256",
        "candidate_sha256",
        "dataset_sha256",
        "criteria_sha256",
    }:
        raise ValueError("BENCHMARK_FROZEN_COMPARISON_REQUIRED")
    if any(
        not isinstance(v, str)
        or len(v) != 64
        or any(c not in "0123456789abcdef" for c in v)
        for v in config.values()
    ):
        raise ValueError("BENCHMARK_SHA256_REQUIRED")
    totals = {
        k: {"attempts": 0, "cost_atoms": 0, "elapsed_ns": 0, "useful_outputs": 0}
        for k in ("baseline", "candidate")
    }
    ids = set()
    for row in attempts:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "variant",
            "status",
            "cost_atoms",
            "elapsed_ns",
            "useful_outputs",
            "dataset_sha256",
            "criteria_sha256",
            "build_sha256",
        }:
            raise ValueError("BENCHMARK_ATTEMPT_SCHEMA")
        if row["id"] in ids or row["variant"] not in totals:
            raise ValueError("BENCHMARK_ATTEMPT_ID_OR_VARIANT")
        ids.add(row["id"])
        if (
            row["dataset_sha256"] != config["dataset_sha256"]
            or row["criteria_sha256"] != config["criteria_sha256"]
            or row["build_sha256"] != config[row["variant"] + "_sha256"]
        ):
            raise ValueError("BENCHMARK_COMPARISON_DRIFT")
        if row["status"] not in {"SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED"}:
            raise ValueError("BENCHMARK_ATTEMPT_STATUS")
        for key in ("cost_atoms", "elapsed_ns", "useful_outputs"):
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError("BENCHMARK_INTEGER_METRICS_REQUIRED")
        if row["status"] != "SUCCEEDED" and row["useful_outputs"] != 0:
            raise ValueError("BENCHMARK_FAILED_ATTEMPT_NOT_USEFUL")
        total = totals[row["variant"]]
        total["attempts"] += 1
        for key in ("cost_atoms", "elapsed_ns", "useful_outputs"):
            total[key] += row[key]
    for total in totals.values():
        total["cost_per_useful_output"] = (
            None
            if not total["useful_outputs"]
            else {
                "numerator": total["cost_atoms"],
                "denominator": total["useful_outputs"],
            }
        )
        total["time_per_useful_output"] = (
            None
            if not total["useful_outputs"]
            else {
                "numerator": total["elapsed_ns"],
                "denominator": total["useful_outputs"],
            }
        )
    return {
        "schema": "occ.usefulness-comparison.v1",
        "frozen": config,
        "totals": totals,
        "status": (
            "NO_USEFUL_COMPARISON"
            if any(t["useful_outputs"] == 0 for t in totals.values())
            else "MODEL_METRICS_COMPUTED"
        ),
        "qualified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    cmd = commands.add_parser("import")
    cmd.add_argument("--catalog", required=True, type=Path)
    cmd.add_argument("--sha256", required=True)
    cmd = commands.add_parser("reconcile")
    cmd.add_argument("--catalog-sha256", required=True)
    cmd.add_argument("--scope", required=True, type=Path)
    cmd.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "import":
        result = import_catalog(args.store, args.catalog, args.sha256)
    else:
        result = reconcile(args.store, args.catalog_sha256, read_json(args.scope))
        with args.output.open("x", encoding="utf-8") as out:
            out.write(encoded(result) + "\n")
        result = {k: v for k, v in result.items() if k != "criteria"}
    print(encoded(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
