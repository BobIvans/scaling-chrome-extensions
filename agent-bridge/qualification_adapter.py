#!/usr/bin/env python3
"""FAST-Q2 local CLI slice. No browser permissions, API keys or LLM writer.

Uses the existing installed FAST-Q1 capture/inspection owner. Laya is advisory.
The operator supplies checkout/output/SHA outside the model-controlled request.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import sys
from typing import Any
import unicodedata

REQUEST_SCHEMA = "occ.qualification-action.v1"
RECEIPT_SCHEMA = "occ.qualification-adapter-receipt.v1"
PHRASES = {
    "проверь готовность бота",
    "запусти qualification campaign",
    "run qualification",
    "check bot readiness",
}
ACTION_REGISTRY = {
    "qualify_and_report": {
        "handler": "flashloan-checks qualify-and-report inspect",
        "profile": "offline-inspection",
        "live_authorized": False,
        "market_run_performed": False,
    },
    "needs_context": {"handler": None},
}


def validate_request(request: Any) -> dict[str, Any]:
    required = {"schema_version", "request_id"}
    allowed = required | {"text", "action_id"}
    if (
        not isinstance(request, dict)
        or set(request) - allowed
        or not required <= set(request)
    ):
        raise ValueError("REQUEST_SCHEMA_INVALID")
    if request["schema_version"] != REQUEST_SCHEMA:
        raise ValueError("REQUEST_VERSION_INVALID")
    if not isinstance(request["request_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,80}", request["request_id"]
    ):
        raise ValueError("REQUEST_ID_INVALID")
    if "text" in request and (
        not isinstance(request["text"], str) or len(request["text"]) > 2000
    ):
        raise ValueError("REQUEST_TEXT_INVALID")
    if "action_id" in request and (
        not isinstance(request["action_id"], str)
        or request["action_id"] not in ACTION_REGISTRY
    ):
        raise ValueError("ACTION_UNREGISTERED")
    return request


def select_action(request: dict[str, Any]) -> str:
    if "action_id" in request:
        return request["action_id"]
    text = unicodedata.normalize("NFKC", request.get("text", "")).casefold().strip()
    return "qualify_and_report" if text in PHRASES else "needs_context"


def laya_proposal(text: str) -> dict[str, Any]:
    # Same Router contract as the existing OCC demo; no second inference service.
    try:
        from laya import Router

        questions = {
            "action": {
                "type": "choice",
                "instructions": "Предложи маршрут. Это не разрешение на выполнение.",
                "criteria": {
                    "qualify_and_report": "Проверить готовность бота и причины блокировки без отправки сделок",
                    "needs_context": "Неизвестный, неоднозначный запрос, новый код или live/trading действие",
                },
            }
        }
        prediction = Router().predict(text, questions, model="multilingual")
        answer = prediction["answers"]["action"]["choice"]
        if answer not in ACTION_REGISTRY:
            raise ValueError("MODEL_ACTION_UNREGISTERED")
        return {
            "state": "ADVISORY",
            "action_id": answer,
            "sdk_version": metadata.version("laya"),
            "model_inference_performed": True,
            "authorizes_execution": False,
        }
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        return {
            "state": "UNAVAILABLE",
            "error_type": type(exc).__name__,
            "model_inference_performed": False,
            "authorizes_execution": False,
        }


def validate_child(
    payload: Any, *, request_id: str, expected_sha: str, output_root: Path
) -> dict:
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != "pr189.command-result.v1"
    ):
        raise ValueError("CHILD_RESPONSE_SCHEMA_INVALID")
    if (
        payload.get("command") != "qualify-and-report"
        or payload.get("command_mode") != "inspect"
    ):
        raise ValueError("CHILD_COMMAND_MISMATCH")
    receipt = payload.get("details")
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version") != "fast-q1.qualification-receipt.v1"
    ):
        raise ValueError("CHILD_RECEIPT_SCHEMA_INVALID")
    expected = output_root.resolve() / request_id
    if (
        receipt.get("request_id") != request_id
        or receipt.get("git_sha") != expected_sha
        or receipt.get("run_directory") != str(expected)
    ):
        raise ValueError("CHILD_RECEIPT_BINDING_MISMATCH")
    if (
        receipt.get("qualified") is not False
        or receipt.get("live_authorized") is not False
        or receipt.get("market_run_performed") is not False
        or type(receipt.get("transactions_sent")) is not int
        or receipt["transactions_sent"] != 0
    ):
        raise ValueError("CHILD_SCOPE_VIOLATION")
    if receipt.get("execution_status") != "COMPLETE" or receipt.get(
        "domain_verdict"
    ) not in {"BLOCKED", "INSPECTED"}:
        raise ValueError("CHILD_RESULT_UNVERIFIED")
    return receipt


def _write(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _claim_request(request: dict, repo: Path, output: Path, sha: str, shadow: bool):
    absolute = output.absolute()
    if any(path.is_symlink() for path in (absolute, *absolute.parents)):
        raise ValueError("OUTPUT_SYMLINK_BLOCKED")
    output = absolute.resolve()
    if output == repo or output.is_relative_to(repo):
        raise ValueError("OUTPUT_MUST_BE_OUTSIDE_CHECKOUT")
    ledger = output / "adapter_requests"
    if ledger.is_symlink():
        raise ValueError("ADAPTER_LEDGER_SYMLINK_BLOCKED")
    ledger.mkdir(parents=True, exist_ok=True)
    run = ledger / request["request_id"]
    inputs = {
        "request": request,
        "repo_root": str(repo),
        "output_root": str(output),
        "expected_sha": sha,
        "laya_shadow": shadow,
    }
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    try:
        run.mkdir()
    except FileExistsError:
        if run.is_symlink():
            raise ValueError("ADAPTER_RUN_SYMLINK_BLOCKED")
        manifest_path = run / "request_manifest.json"
        receipt_path = run / "adapter_receipt.json"
        if manifest_path.is_symlink() or receipt_path.is_symlink():
            raise ValueError("ADAPTER_ARTIFACT_SYMLINK_BLOCKED")
        if not manifest_path.is_file():
            raise ValueError("ADAPTER_INCOMPLETE_RECONCILE_BEFORE_RETRY")
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or previous.get("input_digest") != digest:
            raise ValueError("ADAPTER_REQUEST_ID_INPUT_CONFLICT")
        if previous.get("state") != "COMPLETE" or not receipt_path.is_file():
            raise ValueError("ADAPTER_INCOMPLETE_RECONCILE_BEFORE_RETRY")
        data = receipt_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != previous.get("receipt_sha256"):
            raise ValueError("ADAPTER_RECEIPT_INTEGRITY_FAILED")
        return output, run, digest, {**json.loads(data), "reused": True}
    _write(run / "request_manifest.json", {"state": "RUNNING", "input_digest": digest})
    return output, run, digest, None


def _finish_request(run: Path, digest: str, receipt: dict) -> dict:
    path = run / "adapter_receipt.json"
    _write(path, receipt)
    _write(
        run / "request_manifest.json",
        {
            "state": "COMPLETE",
            "input_digest": digest,
            "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    )
    return receipt


def execute_request(
    request: Any,
    *,
    repo_root: Path,
    output_root: Path,
    expected_sha: str,
    laya_shadow: bool = False,
) -> dict[str, Any]:
    request = validate_request(request)
    if not re.fullmatch(r"[a-f0-9]{40}", expected_sha):
        raise ValueError("EXPECTED_SHA_INVALID")
    repo = repo_root.resolve(strict=True)
    output_root, run, digest, previous = _claim_request(
        request, repo, output_root, expected_sha, laya_shadow
    )
    if previous is not None:
        return previous
    action = select_action(request)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "request_id": request["request_id"],
        "request_sha256": hashlib.sha256(
            json.dumps(request, sort_keys=True).encode()
        ).hexdigest(),
        "action_id": action,
        "execution_status": "NOT_EXECUTED",
        "domain_verdict": "NEEDS_CONTEXT",
        "model_inference_performed": False,
        "reused": False,
        "live_authorized": False,
        "transactions_sent": 0,
    }
    if laya_shadow:
        proposal = laya_proposal(request.get("text", ""))
        receipt["laya_advisory"] = proposal
        receipt["model_inference_performed"] = proposal["model_inference_performed"]
    if action == "needs_context":
        return _finish_request(run, digest, receipt)
    try:
        from src.qualification_report import _capture

        script = Path(sys.executable).parent / (
            "flashloan-checks.exe" if sys.platform == "win32" else "flashloan-checks"
        )
        if not script.is_file():
            raise ValueError("INSTALLED_CHECKS_UNAVAILABLE")
        argv = [
            str(script),
            "qualify-and-report",
            "inspect",
            "--repo-root",
            str(repo),
            "--output-root",
            str(output_root.resolve()),
            "--request-id",
            request["request_id"],
            "--expected-sha",
            expected_sha,
            "--timeout-seconds",
            "20",
        ]
        captured = _capture(argv, repo, 110)
        if captured["error"] or captured["exit_code"] != 0:
            raise ValueError("CHILD_COMMAND_FAILED")
        child = validate_child(
            json.loads(captured["stdout"]),
            request_id=request["request_id"],
            expected_sha=expected_sha,
            output_root=output_root,
        )
        receipt.update(
            execution_status="COMPLETE",
            domain_verdict=child["domain_verdict"],
            qualification_receipt=child,
            child_exit_code=captured["exit_code"],
        )
    except (ImportError, OSError, ValueError, TypeError) as exc:
        receipt.update(
            execution_status="BLOCKED", domain_verdict="BLOCKED", reason_code=str(exc)
        )
    return _finish_request(run, digest, receipt)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--laya-shadow", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.request.stat().st_size > 16384:
            raise ValueError("REQUEST_SIZE_LIMIT")
        report = execute_request(
            json.loads(args.request.read_text(encoding="utf-8")),
            repo_root=args.repo_root,
            output_root=args.output_root,
            expected_sha=args.expected_sha,
            laya_shadow=args.laya_shadow,
        )
    except (OSError, ValueError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": RECEIPT_SCHEMA,
                    "execution_status": "BLOCKED",
                    "reason_code": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["execution_status"] == "COMPLETE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
