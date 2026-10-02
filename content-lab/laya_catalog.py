"""Compile an existing OCC catalogue into advisory Laya JSON. No network or execution."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


QUESTIONS = {
    "review_route": {
        "type": "choice",
        "instructions": "Choose the team for reviewing this proposal. Do not infer implementation or permissions.",
        "criteria": {
            "sources": "Import, provenance, retrieval, documents",
            "runtime": "Queue, host, UI, voice, registered tools",
            "engineering": "Code, dependencies, CI, tests, evaluation",
            "web3": "Offline market and protocol evidence",
            "needs_context": "Insufficient information",
        },
    },
    "review_focus": {
        "type": "choice",
        "instructions": "Suggest the next review focus. Catalog proposals are not evidence of code gaps.",
        "criteria": {
            "source_coverage": "Check source identity and completeness",
            "owner_audit": "Locate implementation and overlapping PRs",
            "tests": "Check acceptance and regression evidence",
            "recovery": "Check replay, cancellation and failure recovery",
            "needs_context": "Missing information prevents a useful suggestion",
        },
    },
}


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def compile_catalog(catalog):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("items"), list):
        raise ValueError("CATALOG_OBJECT_WITH_ITEMS_REQUIRED")
    if not catalog["items"] or len(catalog["items"]) > 20_000:
        raise ValueError("CATALOG_COUNT_OUT_OF_BOUNDS")
    for field in ("candidate_count", "capability_count", "slices_per_capability"):
        if type(catalog.get(field)) is not int or catalog[field] < 1:
            raise ValueError("POSITIVE_INTEGER_REQUIRED:" + field)
    groups = defaultdict(list)
    seen = set()
    for item in catalog["items"]:
        if not isinstance(item, dict):
            raise ValueError("CANDIDATE_OBJECT_REQUIRED")
        cid, cap = item.get("candidate_id"), item.get("capability_id")
        if not isinstance(cid, str) or not re.fullmatch(r"CAND-[0-9]{4,6}", cid):
            raise ValueError("INVALID_CANDIDATE_ID")
        if cid in seen:
            raise ValueError("DUPLICATE_CANDIDATE_ID")
        if not isinstance(cap, str) or not re.fullmatch(r"CAP-[0-9]{3,5}", cap):
            raise ValueError("INVALID_CAPABILITY_ID")
        for field in ("function_key", "target_repository", "title_ru", "input_ru", "output_ru", "slice"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ValueError("MISSING_STRING_FIELD:" + field)
        acceptance = item.get("acceptance_criteria_ru")
        if not isinstance(acceptance, list) or not acceptance or not all(isinstance(x, str) for x in acceptance):
            raise ValueError("ACCEPTANCE_REQUIRED")
        seen.add(cid)
        groups[cap].append(item)
    if len(seen) != catalog.get("candidate_count") or len(groups) != catalog.get("capability_count"):
        raise ValueError("DECLARED_COUNTS_MISMATCH")
    index, requests = [], {}
    for cap, cards in sorted(groups.items()):
        if len({x["function_key"] for x in cards}) != 1 or len({x["target_repository"] for x in cards}) != 1:
            raise ValueError("CAPABILITY_IDENTITY_CONFLICT")
        first = cards[0]
        slices = [x.get("slice") for x in cards]
        if len(slices) != catalog.get("slices_per_capability") or len(set(slices)) != len(slices):
            raise ValueError("SLICE_COUNT_OR_DUPLICATE_ERROR")
        ids = [x["candidate_id"] for x in cards]
        body = {
            "model": "multilingual",
            "max_len": 8192,
            "state": {
                "capability_id": cap,
                "function_key": first["function_key"],
                "title_ru": first["title_ru"].rsplit(" — ", 1)[0],
                "repository": first["target_repository"],
                "input_ru": first["input_ru"],
                "output_ru": first["output_ru"],
                "function_acceptance_ru": first["acceptance_criteria_ru"][0],
                "proposed_engineering_slices": slices,
                "evidence_status": "CATALOG_PROPOSAL_ONLY; CURRENT_OWNER_AND_ALL_SLICE_EVIDENCE_NOT_VERIFIED",
            },
            "questions": QUESTIONS,
        }
        if len(json.dumps(body["state"], ensure_ascii=False)) > 50_000:
            raise ValueError("STATE_EXCEEDS_INSPECTED_SERVER_CHAR_LIMIT")
        requests[cap] = body
        index.append({
            "capability_id": cap,
            "function_key": first["function_key"],
            "title_ru": body["state"]["title_ru"],
            "target_repository": first["target_repository"],
            "priority": first.get("priority"),
            "candidate_ids": ids,
            "candidate_count": len(ids),
            "request_file": "laya_requests/" + cap + ".json",
            "candidate_records": "SOURCE_CATALOG.json#/items",
            "disposition": "REQUIRES_CURRENT_OWNER_AND_ACCEPTANCE_AUDIT",
            "can_enqueue_code_change": False,
            "github_pr_number": None,
            "related_pr_rule": "A related PR does not close every engineering slice.",
        })
    return index, requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.catalog.is_symlink() or not args.catalog.is_file() or args.catalog.stat().st_size > 16_000_000:
        raise ValueError("REGULAR_BOUNDED_CATALOG_REQUIRED")
    raw = args.catalog.read_bytes()
    if len(raw) > 16_000_000:
        raise ValueError("CATALOG_TOO_LARGE")
    catalog = json.loads(raw)
    index, requests = compile_catalog(catalog)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "laya_requests").mkdir()
    (args.out / "SOURCE_CATALOG.json").write_bytes(raw)
    for cap, body in requests.items():
        (args.out / "laya_requests" / (cap + ".json")).write_text(encode(body), encoding="utf-8")
    manifest = {
        "schema": "occ.laya-catalog-review-package.v1",
        "source_catalog_sha256": hashlib.sha256(raw).hexdigest(),
        "candidate_count": len(catalog["items"]),
        "capability_count": len(index),
        "native_laya_request_count": len(requests),
        "transport": {"method": "POST", "endpoint": "/v1/systemone", "base_url_example": "http://127.0.0.1:8000"},
        "single_request_endpoint_reason": "Inspected Laya batch handler does not forward max_len; single handler does.",
        "inference_performed": False,
        "tokenizer_fit_verified": False,
        "runtime_compatibility": "REQUEST_SHAPE_CHECKED_AGAINST_SOURCE; MODEL_AND_SERVER_NOT_RUN",
        "execution_queue_compatible": False,
        "scope": "Advisory routing requests and existing candidate index; not native job requests or prepared patches",
        "original_candidate_records_preserved_byte_for_byte": True,
        "code_changes_enqueued": 0,
        "pull_requests_created": 0,
        "pull_requests_merged": 0,
        "rules_ru": [
            "20 инженерных срезов одной функции не требуют 20 отдельных PR.",
            "Результат Laya направляет проверку; не подтверждает code gap, merge или разрешение.",
            "Перед изменением кода нужны актуальный owner, проверка пересекающихся PR и критерии результата.",
            "Уже существующий dispatcher и очередь сохраняют владение выполнением.",
        ],
        "capabilities": index,
    }
    (args.out / "OCC_LAYA_CATALOG_INDEX_RU.json").write_text(encode(manifest), encoding="utf-8")
    print(json.dumps({"candidates": len(catalog["items"]), "capabilities": len(index), "requests": len(requests), "model_calls": 0}))


if __name__ == "__main__":
    main()
