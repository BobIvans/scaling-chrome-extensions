#!/usr/bin/env python3
"""Fail-closed OCC native adapter for studious-pancake qualification inspection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence

REQUEST_SCHEMA = "occ.native-qualification-request.v1"
PROFILE_SCHEMA = "occ.native-qualification-profile.v1"
RESULT_SCHEMA = "occ.native-qualification-result.v1"
BOT_REQUEST_SCHEMA = "occ.qualification-action.v1"
BOT_PROFILE_SCHEMA = "studious-pancake.occ-qualification-profile.v1"
BOT_RECEIPT_SCHEMA = "studious-pancake.occ-memory-qualification-receipt.v1"
OCC_REPOSITORY = "BobIvans/scaling-chrome-extensions"
ACTION_ID = "qualify_and_report"
MAX_REQUEST_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 512 * 1024
MAX_SOURCE_REFS = 32
MAX_TIMEOUT_SECONDS = 30
_ALLOWED_TEXT = {
    "проверь готовность бота",
    "проверь квалификацию бота",
    "check bot readiness",
    "qualify and report",
}
_REQUEST_FIELDS = {"schema", "task_id", "text", "source_refs"}
_PROFILE_FIELDS = {
    "schema",
    "occ_repo_root",
    "expected_occ_sha",
    "occ_base_sha",
    "bot_python",
    "bot_bridge_script",
    "bot_repo_root",
    "bot_output_root",
    "expected_bot_sha",
    "timeout_seconds",
}
_SOURCE_REF_FIELDS = {"source_id", "version", "sha256"}
_SAFE_ENV_NAMES = (
    "PATH",
    "SystemRoot",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def parse_json_bytes(raw: bytes) -> Any:
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("REQUEST_SIZE_LIMIT")
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=lambda _value: (_ for _ in ()).throw(
            ValueError("NON_FINITE_JSON_NUMBER")
        ),
    )


def read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError("PROFILE_FILE_INVALID")
    if path.stat().st_size > MAX_REQUEST_BYTES:
        raise ValueError("PROFILE_SIZE_LIMIT")
    return parse_json_bytes(path.read_bytes())


def _source_ref(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict) or set(raw) != _SOURCE_REF_FIELDS:
        raise ValueError("SOURCE_REF_FIELDS_INVALID")
    source_id = raw.get("source_id")
    version = raw.get("version")
    sha256 = raw.get("sha256")
    for value in (source_id, version):
        if not isinstance(value, str) or not 1 <= len(value) <= 160:
            raise ValueError("SOURCE_REF_IDENTIFIER_INVALID")
        if any(ord(char) < 32 for char in value):
            raise ValueError("SOURCE_REF_IDENTIFIER_INVALID")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("SOURCE_REF_SHA256_INVALID")
    return {"source_id": source_id, "version": version, "sha256": sha256}


def validate_request(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != _REQUEST_FIELDS:
        raise ValueError("REQUEST_FIELDS_INVALID")
    if raw.get("schema") != REQUEST_SCHEMA:
        raise ValueError("REQUEST_SCHEMA_UNSUPPORTED")
    task_id = raw.get("task_id")
    if not isinstance(task_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", task_id
    ):
        raise ValueError("TASK_ID_INVALID")
    text = raw.get("text")
    if not isinstance(text, str) or not 1 <= len(text) <= 256:
        raise ValueError("COMMAND_TEXT_INVALID")
    if " ".join(text.strip().split()).casefold() not in _ALLOWED_TEXT:
        raise ValueError("COMMAND_INTENT_NOT_ADMITTED")
    refs = raw.get("source_refs")
    if not isinstance(refs, list) or len(refs) > MAX_SOURCE_REFS:
        raise ValueError("SOURCE_REFS_INVALID")
    normalized = [_source_ref(item) for item in refs]
    if len({digest(item) for item in normalized}) != len(normalized):
        raise ValueError("SOURCE_REFS_DUPLICATE")
    return {**raw, "source_refs": normalized}


def _absolute_path(value: object, code: str) -> Path:
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError(code)
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(code)
    return path


def validate_profile(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != _PROFILE_FIELDS:
        raise ValueError("PROFILE_FIELDS_INVALID")
    if raw.get("schema") != PROFILE_SCHEMA:
        raise ValueError("PROFILE_SCHEMA_UNSUPPORTED")
    for field in ("expected_occ_sha", "occ_base_sha", "expected_bot_sha"):
        if not isinstance(raw.get(field), str) or not re.fullmatch(
            r"[0-9a-f]{40}", raw[field]
        ):
            raise ValueError("PROFILE_SHA_INVALID")
    timeout = raw.get("timeout_seconds")
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
        raise ValueError("PROFILE_TIMEOUT_INVALID")
    for field in (
        "occ_repo_root",
        "bot_python",
        "bot_bridge_script",
        "bot_repo_root",
        "bot_output_root",
    ):
        _absolute_path(raw.get(field), "PROFILE_PATH_INVALID")
    return dict(raw)


def _safe_env(source: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if source is None else source
    env = {key: source[key] for key in _SAFE_ENV_NAMES if key in source}
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    return env


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        env=_safe_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=15,
        shell=False,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("OCC_SOURCE_IDENTITY_UNAVAILABLE")
    return result.stdout.strip()


def verify_profile_paths(profile: Mapping[str, Any]) -> dict[str, Path | str | int]:
    occ_root = _absolute_path(profile["occ_repo_root"], "PROFILE_PATH_INVALID").resolve(
        strict=True
    )
    bot_root = _absolute_path(profile["bot_repo_root"], "PROFILE_PATH_INVALID").resolve(
        strict=True
    )
    bot_python = _absolute_path(profile["bot_python"], "PROFILE_PATH_INVALID").resolve(
        strict=True
    )
    bot_script = _absolute_path(
        profile["bot_bridge_script"], "PROFILE_PATH_INVALID"
    ).resolve(strict=True)
    expected_script = (bot_root / "scripts" / "run_occ_memory_qualification.py").resolve()
    if bot_script != expected_script:
        raise ValueError("BOT_BRIDGE_SCRIPT_NOT_CANONICAL")
    if not bot_python.is_file() or not bot_script.is_file():
        raise ValueError("BOT_EXECUTION_PATH_UNAVAILABLE")

    raw_output = _absolute_path(
        profile["bot_output_root"], "PROFILE_PATH_INVALID"
    ).absolute()
    if any(path.is_symlink() for path in (raw_output, *raw_output.parents)):
        raise ValueError("OUTPUT_SYMLINK_BLOCKED")
    output = raw_output.resolve()
    if output == occ_root or output.is_relative_to(occ_root):
        raise ValueError("OUTPUT_INSIDE_OCC_CHECKOUT")
    if output == bot_root or output.is_relative_to(bot_root):
        raise ValueError("OUTPUT_INSIDE_BOT_CHECKOUT")

    return {
        "occ_root": occ_root,
        "bot_root": bot_root,
        "bot_python": bot_python,
        "bot_script": bot_script,
        "output": output,
        "timeout_seconds": int(profile["timeout_seconds"]),
    }


def verify_occ_checkout(root: Path, expected_sha: str) -> str:
    if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("OCC_PROJECT_ROOT_MISMATCH")
    observed = _git(root, "rev-parse", "HEAD")
    if observed != expected_sha:
        raise ValueError("OCC_SOURCE_SHA_MISMATCH")
    if _git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("OCC_SOURCE_TREE_DIRTY")
    return observed


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)


def _claim(output: Path, request: Mapping[str, Any], profile: Mapping[str, Any]):
    output.mkdir(parents=True, exist_ok=True)
    ledger = output / "occ_adapter_requests"
    if ledger.is_symlink():
        raise ValueError("ADAPTER_LEDGER_SYMLINK_BLOCKED")
    ledger.mkdir(exist_ok=True)
    run = ledger / str(request["task_id"])
    input_digest = digest({"request": request, "profile": profile})
    try:
        run.mkdir()
    except FileExistsError:
        if run.is_symlink() or not run.is_dir():
            raise ValueError("ADAPTER_RUN_PATH_INVALID") from None
        manifest_path = run / "manifest.json"
        receipt_path = run / "receipt.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ValueError("ADAPTER_INCOMPLETE_RECONCILE_BEFORE_RETRY") from None
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict) or manifest.get("input_digest") != input_digest:
            raise ValueError("ADAPTER_REQUEST_ID_INPUT_CONFLICT") from None
        if manifest.get("state") != "COMPLETE" or not receipt_path.is_file():
            raise ValueError("ADAPTER_INCOMPLETE_RECONCILE_BEFORE_RETRY") from None
        receipt = read_json(receipt_path)
        if not isinstance(receipt, dict):
            raise ValueError("ADAPTER_RECEIPT_INVALID") from None
        claimed = receipt.get("receipt_sha256")
        unsigned = {
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }
        if claimed != digest(unsigned) or claimed != manifest.get("receipt_sha256"):
            raise ValueError("ADAPTER_RECEIPT_INTEGRITY_FAILED") from None
        return run, input_digest, {**receipt, "replayed": True}
    _write_json(
        run / "manifest.json",
        {"state": "RUNNING", "input_digest": input_digest},
    )
    return run, input_digest, None


def _invoke_bot_bridge(
    *,
    bot_python: Path,
    bot_script: Path,
    bot_request_path: Path,
    bot_profile_path: Path,
    timeout_seconds: int,
) -> tuple[int, dict[str, Any]]:
    timeout = min(210, timeout_seconds * 6 + 30)
    completed = subprocess.run(
        [
            str(bot_python),
            "-I",
            "-X",
            "utf8",
            str(bot_script),
            "--request",
            str(bot_request_path),
            "--operator-profile",
            str(bot_profile_path),
        ],
        env=_safe_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout,
        shell=False,
        check=False,
    )
    if len(completed.stdout) + len(completed.stderr) > MAX_OUTPUT_BYTES:
        raise ValueError("BOT_BRIDGE_OUTPUT_LIMIT")
    if completed.returncode not in (0, 3):
        raise ValueError("BOT_BRIDGE_PROCESS_FAILED")
    try:
        payload = parse_json_bytes(completed.stdout)
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("BOT_BRIDGE_RESPONSE_INVALID") from exc
    if not isinstance(payload, dict):
        raise ValueError("BOT_BRIDGE_RESPONSE_INVALID")
    return completed.returncode, payload


def _validate_bot_result(
    payload: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    profile: Mapping[str, Any],
    observed_occ_sha: str,
) -> dict[str, Any]:
    receipt = payload.get("receipt")
    if type(payload.get("replayed")) is not bool or not isinstance(receipt, dict):
        raise ValueError("BOT_BRIDGE_RESPONSE_SCHEMA_INVALID")
    if receipt.get("schema_version") != BOT_RECEIPT_SCHEMA:
        raise ValueError("BOT_RECEIPT_SCHEMA_INVALID")
    if receipt.get("request_id") != request["task_id"]:
        raise ValueError("BOT_RECEIPT_REQUEST_ID_MISMATCH")
    if receipt.get("action_id") != ACTION_ID:
        raise ValueError("BOT_RECEIPT_ACTION_MISMATCH")
    if receipt.get("source_refs") != request["source_refs"]:
        raise ValueError("BOT_RECEIPT_SOURCE_REFS_MISMATCH")
    occ = receipt.get("occ")
    bot = receipt.get("bot")
    if not isinstance(occ, dict) or not isinstance(bot, dict):
        raise ValueError("BOT_RECEIPT_PROVENANCE_INVALID")
    if (
        occ.get("repository") != OCC_REPOSITORY
        or occ.get("base_sha") != profile["occ_base_sha"]
        or occ.get("head_sha") != observed_occ_sha
    ):
        raise ValueError("BOT_RECEIPT_OCC_PROVENANCE_MISMATCH")
    if (
        bot.get("expected_sha") != profile["expected_bot_sha"]
        or bot.get("observed_sha") != profile["expected_bot_sha"]
    ):
        raise ValueError("BOT_RECEIPT_SOURCE_SHA_MISMATCH")
    if receipt.get("domain_verdict") not in {"BLOCKED", "PAPER_PASS"}:
        raise ValueError("BOT_RECEIPT_DOMAIN_INVALID")
    if not isinstance(receipt.get("reason_codes"), list) or not all(
        isinstance(item, str) for item in receipt["reason_codes"]
    ):
        raise ValueError("BOT_RECEIPT_REASON_CODES_INVALID")
    if (
        receipt.get("qualified") is not False
        or receipt.get("release_authorized") is not False
        or receipt.get("live_authorized") is not False
        or receipt.get("transactions_sent") != 0
    ):
        raise ValueError("BOT_RECEIPT_AUTHORITY_BOUNDARY_INVALID")
    return dict(receipt)


def execute_request(
    raw_request: object,
    raw_profile: object,
    *,
    invoke: Callable[..., tuple[int, dict[str, Any]]] = _invoke_bot_bridge,
    verify_checkout: Callable[[Path, str], str] = verify_occ_checkout,
) -> dict[str, Any]:
    request = validate_request(raw_request)
    profile = validate_profile(raw_profile)
    paths = verify_profile_paths(profile)
    observed_occ_sha = verify_checkout(
        paths["occ_root"], str(profile["expected_occ_sha"])
    )
    run, input_digest, previous = _claim(paths["output"], request, profile)
    if previous is not None:
        return previous

    bot_request = {
        "schema_version": BOT_REQUEST_SCHEMA,
        "request_id": request["task_id"],
        "action_id": ACTION_ID,
        "text": request["text"],
    }
    bot_profile = {
        "schema_version": BOT_PROFILE_SCHEMA,
        "repo_root": str(paths["bot_root"]),
        "output_root": str(paths["output"]),
        "expected_bot_sha": profile["expected_bot_sha"],
        "timeout_seconds": profile["timeout_seconds"],
        "occ_repository": OCC_REPOSITORY,
        "occ_base_sha": profile["occ_base_sha"],
        "occ_head_sha": observed_occ_sha,
        "source_refs": request["source_refs"],
    }
    bot_request_path = run / "bot-request.json"
    bot_profile_path = run / "bot-operator-profile.json"
    _write_json(bot_request_path, bot_request)
    _write_json(bot_profile_path, bot_profile)

    try:
        child_exit_code, payload = invoke(
            bot_python=paths["bot_python"],
            bot_script=paths["bot_script"],
            bot_request_path=bot_request_path,
            bot_profile_path=bot_profile_path,
            timeout_seconds=int(paths["timeout_seconds"]),
        )
        bot_receipt = _validate_bot_result(
            payload,
            request=request,
            profile=profile,
            observed_occ_sha=observed_occ_sha,
        )
    except Exception:
        _write_json(
            run / "manifest.json",
            {"state": "RECONCILIATION_REQUIRED", "input_digest": input_digest},
        )
        raise

    result = {
        "schema": RESULT_SCHEMA,
        "request_id": request["task_id"],
        "action_id": ACTION_ID,
        "domain_verdict": bot_receipt["domain_verdict"],
        "reason_codes": bot_receipt["reason_codes"],
        "next_blocker": bot_receipt.get("next_blocker"),
        "source_refs": request["source_refs"],
        "occ_sha": observed_occ_sha,
        "bot_sha": profile["expected_bot_sha"],
        "bot_receipt_sha256": bot_receipt.get("receipt_sha256"),
        "child_exit_code": child_exit_code,
        "qualified": False,
        "release_authorized": False,
        "live_authorized": False,
        "transactions_sent": 0,
        "replayed": False,
    }
    result["receipt_sha256"] = digest(result)
    _write_json(run / "receipt.json", result)
    _write_json(
        run / "manifest.json",
        {
            "state": "COMPLETE",
            "input_digest": input_digest,
            "receipt_sha256": result["receipt_sha256"],
        },
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        request = parse_json_bytes(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
        result = execute_request(request, read_json(args.profile))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print(json.dumps({"ok": False, "error": "QUALIFICATION_REQUEST_FAILED"}))
        return 2
    print(
        json.dumps(
            {"ok": True, "result": result},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
