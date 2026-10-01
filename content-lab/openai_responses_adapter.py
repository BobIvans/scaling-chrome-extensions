"""Budget-gated backend adapter for the OpenAI Responses API.

The API key is read only inside this backend after a new atomic reservation.
No browser/native-host message accepts a key or endpoint.  Successful provider
responses remain budget-quarantined until their actual cost is reconciled.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import provider_budget as budget


API_URL = "https://api.openai.com/v1/responses"
PROFILE_SCHEMA = "occ.openai-responses-profile.v1"
REQUEST_SCHEMA = "occ.openai-responses-request.v1"
RESULT_SCHEMA = "occ.openai-responses-result.v1"
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
RESPONSE_ID = re.compile(r"^resp_[A-Za-z0-9_-]{1,200}$")
MAX_INPUT_BYTES = 100_000
MAX_INSTRUCTIONS_BYTES = 20_000


class AdapterBlocked(ValueError):
    """Stable public failure code; never includes credentials or provider text."""


class TransportCancelled(Exception):
    def __init__(self, *, request_sent):
        super().__init__("transport cancelled")
        self.request_sent = request_sent


class TransportUnknown(Exception):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        return None


def _strict_int(value, low, high, code):
    if type(value) is not int or not low <= value <= high:
        raise AdapterBlocked(code)
    return value


def _bounded_text(value, maximum, code, *, allow_empty=False):
    if (not isinstance(value, str) or "\0" in value
            or (not allow_empty and not value)
            or len(value.encode("utf-8")) > maximum):
        raise AdapterBlocked(code)
    return value


def validate_profile(profile):
    expected = {"schema", "model", "api_key_env", "timeout_seconds",
                "max_response_bytes"}
    if (not isinstance(profile, dict) or set(profile) != expected
            or profile.get("schema") != PROFILE_SCHEMA):
        raise AdapterBlocked("OPENAI_PROFILE_SCHEMA")
    model = profile.get("model")
    if not isinstance(model, str) or not MODEL.fullmatch(model):
        raise AdapterBlocked("OPENAI_MODEL_REQUIRED")
    if profile.get("api_key_env") != "OCC_OPENAI_API_KEY":
        raise AdapterBlocked("OPENAI_BACKEND_KEY_ENV_REQUIRED")
    return {
        "model": model,
        "api_key_env": "OCC_OPENAI_API_KEY",
        "timeout_seconds": _strict_int(profile.get("timeout_seconds"), 1, 60,
                                       "OPENAI_TIMEOUT_LIMIT"),
        "max_response_bytes": _strict_int(profile.get("max_response_bytes"),
                                          1, 2_000_000,
                                          "OPENAI_RESPONSE_BYTE_LIMIT"),
    }


def build_request(profile, request):
    config = validate_profile(profile)
    expected = {"schema", "input", "instructions", "max_output_tokens", "store"}
    if (not isinstance(request, dict) or set(request) != expected
            or request.get("schema") != REQUEST_SCHEMA):
        raise AdapterBlocked("OPENAI_REQUEST_SCHEMA")
    if request.get("store") is not False:
        raise AdapterBlocked("OPENAI_STORE_FALSE_REQUIRED")
    payload = {
        "model": config["model"],
        "input": _bounded_text(request.get("input"), MAX_INPUT_BYTES,
                               "OPENAI_INPUT_REQUIRED"),
        "instructions": _bounded_text(request.get("instructions"),
                                      MAX_INSTRUCTIONS_BYTES,
                                      "OPENAI_INSTRUCTIONS_REQUIRED"),
        "max_output_tokens": _strict_int(request.get("max_output_tokens"),
                                         1, 100_000,
                                         "OPENAI_OUTPUT_TOKEN_LIMIT"),
        "store": False,
    }
    return config, payload


def _cancelled(check):
    try:
        return check() is True
    except Exception:
        raise AdapterBlocked("CANCEL_CHECK_FAILED") from None


def _read_bounded(response, maximum, cancelled, *, request_sent=True):
    blocks, total = [], 0
    while True:
        if _cancelled(cancelled):
            raise TransportCancelled(request_sent=request_sent)
        block = response.read(min(65_536, maximum + 1 - total))
        if not block:
            return b"".join(blocks)
        blocks.append(block)
        total += len(block)
        if total > maximum:
            raise AdapterBlocked("OPENAI_RESPONSE_TOO_LARGE")


def _https_post(url, headers, payload, timeout, max_bytes, cancelled):
    if url != API_URL:
        raise AdapterBlocked("OPENAI_ENDPOINT_NOT_PINNED")
    if _cancelled(cancelled):
        raise TransportCancelled(request_sent=False)
    request = Request(url, data=payload, headers=headers, method="POST")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            if response.geturl() != API_URL:
                raise AdapterBlocked("OPENAI_REDIRECT_BLOCKED")
            raw = _read_bounded(response, max_bytes, cancelled)
            return response.status, dict(response.headers.items()), raw
    except HTTPError as exc:
        try:
            raw = _read_bounded(exc, max_bytes, cancelled)
        finally:
            exc.close()
        return exc.code, dict(exc.headers.items()), raw
    except TransportCancelled:
        raise
    except AdapterBlocked:
        raise
    except (URLError, TimeoutError, OSError):
        raise TransportUnknown() from None


def _json(raw, code):
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AdapterBlocked(code) from None
    if not isinstance(value, dict):
        raise AdapterBlocked(code)
    return value


def _response(value, expected_model):
    if (set(value) - {"id", "object", "created_at", "status", "model", "output",
                      "usage", "error", "incomplete_details", "metadata",
                      "parallel_tool_calls", "temperature", "tool_choice", "tools",
                      "top_p", "max_output_tokens", "previous_response_id",
                      "reasoning", "service_tier", "store", "text", "truncation",
                      "user", "background", "billing", "completed_at", "prompt",
                      "safety_identifier"}):
        raise AdapterBlocked("OPENAI_RESPONSE_SCHEMA")
    response_id = value.get("id")
    if (not isinstance(response_id, str) or not RESPONSE_ID.fullmatch(response_id)
            or value.get("object") != "response" or value.get("status") != "completed"
            or value.get("model") != expected_model):
        raise AdapterBlocked("OPENAI_RESPONSE_SCHEMA")
    output = value.get("output")
    usage = value.get("usage")
    if not isinstance(output, list) or len(output) > 100 or not isinstance(usage, dict):
        raise AdapterBlocked("OPENAI_RESPONSE_SCHEMA")
    counts = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        counts[key] = _strict_int(usage.get(key), 0, 10_000_000,
                                  "OPENAI_USAGE_SCHEMA")
    if counts["input_tokens"] + counts["output_tokens"] != counts["total_tokens"]:
        raise AdapterBlocked("OPENAI_USAGE_SCHEMA")
    texts = []
    for item in output:
        if not isinstance(item, dict) or len(json.dumps(item, ensure_ascii=False).encode()) > 200_000:
            raise AdapterBlocked("OPENAI_OUTPUT_SCHEMA")
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list) or len(content) > 100:
            raise AdapterBlocked("OPENAI_OUTPUT_SCHEMA")
        for part in content:
            if not isinstance(part, dict):
                raise AdapterBlocked("OPENAI_OUTPUT_SCHEMA")
            if part.get("type") == "output_text":
                texts.append(_bounded_text(part.get("text"), 200_000,
                                           "OPENAI_OUTPUT_SCHEMA", allow_empty=True))
    if not texts or sum(len(text.encode("utf-8")) for text in texts) > 200_000:
        raise AdapterBlocked("OPENAI_OUTPUT_TEXT_REQUIRED")
    return {"response_id": response_id, "model": expected_model,
            "output_text": "".join(texts), "usage": counts}


def _provider_error(status, value, headers):
    error = value.get("error")
    if not isinstance(error, dict):
        raise AdapterBlocked("OPENAI_ERROR_SCHEMA")
    error_type = error.get("type")
    error_code = error.get("code")
    if error_type is not None and (not isinstance(error_type, str) or len(error_type) > 100):
        raise AdapterBlocked("OPENAI_ERROR_SCHEMA")
    if error_code is not None and (not isinstance(error_code, str) or len(error_code) > 100):
        raise AdapterBlocked("OPENAI_ERROR_SCHEMA")
    if status == 401:
        return "AUTHENTICATION_FAILED", False, None
    if status == 429:
        retry_after = None
        for key, value in headers.items():
            if key.lower() == "retry-after" and isinstance(value, str):
                try:
                    parsed = int(value)
                except ValueError:
                    parsed = None
                if parsed is not None and 0 <= parsed <= 3600:
                    retry_after = parsed
        permanent = error_code in {
            "credit_balance_exhausted", "organization_spend_limit_exceeded",
            "project_spend_limit_exceeded", "organization_usage_limit_exceeded",
        }
        return "RATE_OR_QUOTA_LIMITED", not permanent, retry_after
    raise AdapterBlocked("OPENAI_UNHANDLED_HTTP_STATUS")


def execute(profile, request, *, store, budget_plan, op_key,
            reserve_microunits, environ=None, cancelled=lambda: False,
            transport=_https_post):
    """Perform at most one budget-gated call; never retries automatically."""
    config, body = build_request(profile, request)
    if _cancelled(cancelled):
        return {"schema": RESULT_SCHEMA, "state": "CANCELLED", "request_sent": False,
                "budget": None, "action_authority": False}
    reservation = budget.reserve_budget(store, budget_plan, op_key,
                                        reserve_microunits)
    reservation_id = reservation["reservation_id"]
    if reservation.get("reused"):
        quarantined = (budget.mark_budget_unknown(store, reservation_id)
                       if reservation["state"] == "RESERVED" else reservation)
        return {"schema": RESULT_SCHEMA, "state": "NEEDS_RECONCILIATION",
                "reason": "RESERVATION_REPLAY_BLOCKED", "request_sent": None,
                "budget": quarantined, "action_authority": False}
    environment = os.environ if environ is None else environ
    key = environment.get(config["api_key_env"], "")
    if (not isinstance(key, str) or not key or len(key) > 4096
            or "\n" in key or "\r" in key):
        released = budget.release_budget(store, reservation_id,
                                         request_not_sent=True)
        return {"schema": RESULT_SCHEMA, "state": "BLOCKED",
                "reason": "OPENAI_API_KEY_MISSING", "request_sent": False,
                "budget": released, "action_authority": False}
    if _cancelled(cancelled):
        released = budget.release_budget(store, reservation_id,
                                         request_not_sent=True)
        return {"schema": RESULT_SCHEMA, "state": "CANCELLED",
                "request_sent": False, "budget": released,
                "action_authority": False}
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    headers = {"Authorization": "Bearer " + key,
               "Content-Type": "application/json",
               "User-Agent": "occ-openai-responses/1"}
    try:
        status, response_headers, raw = transport(
            API_URL, headers, payload, config["timeout_seconds"],
            config["max_response_bytes"], cancelled)
    except TransportCancelled as exc:
        receipt = (budget.mark_budget_unknown(store, reservation_id)
                   if exc.request_sent else budget.release_budget(
                       store, reservation_id, request_not_sent=True))
        return {"schema": RESULT_SCHEMA, "state": "CANCELLED",
                "request_sent": exc.request_sent, "budget": receipt,
                "action_authority": False}
    except (TransportUnknown, AdapterBlocked):
        budget.mark_budget_unknown(store, reservation_id)
        raise
    except Exception:
        budget.mark_budget_unknown(store, reservation_id)
        raise AdapterBlocked("OPENAI_TRANSPORT_FAILED") from None
    if (type(status) is not int or not 100 <= status <= 599
            or not isinstance(response_headers, dict)
            or not isinstance(raw, bytes)
            or len(raw) > config["max_response_bytes"]):
        budget.mark_budget_unknown(store, reservation_id)
        raise AdapterBlocked("OPENAI_TRANSPORT_CONTRACT")
    receipt_hash = hashlib.sha256(
        str(status).encode() + b"\0" + raw).hexdigest()
    try:
        value = _json(raw, "OPENAI_RESPONSE_JSON_INVALID")
    except AdapterBlocked:
        budget.mark_budget_unknown(store, reservation_id)
        raise
    if status in {401, 429}:
        try:
            reason, retryable, retry_after = _provider_error(status, value,
                                                            response_headers)
        except AdapterBlocked:
            budget.mark_budget_unknown(store, reservation_id)
            raise
        settled = budget.settle_budget(store, reservation_id, 0, receipt_hash)
        return {"schema": RESULT_SCHEMA, "state": "BLOCKED", "reason": reason,
                "http_status": status, "retryable": retryable,
                "retry_after_seconds": retry_after, "request_sent": True,
                "budget": settled, "action_authority": False}
    if not 200 <= status < 300:
        budget.mark_budget_unknown(store, reservation_id)
        raise AdapterBlocked("OPENAI_UNHANDLED_HTTP_STATUS")
    try:
        parsed = _response(value, config["model"])
    except AdapterBlocked:
        budget.mark_budget_unknown(store, reservation_id)
        raise
    quarantined = budget.mark_budget_unknown(store, reservation_id)
    return {"schema": RESULT_SCHEMA, "state": "DONE_REQUIRES_COST_RECONCILIATION",
            **parsed, "provider_receipt_sha256": receipt_hash,
            "request_sent": True, "budget": quarantined,
            "action_authority": False}
