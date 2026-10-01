"""Budget-gated Hugging Face Inference Providers chat adapter.

Only registry-pinned model:provider routes are accepted.  The adapter does not
discover models, select a cheaper/faster route, or fall back after quota errors.
The backend token is read only after a new atomic budget reservation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import provider_budget as budget


API_URL = "https://router.huggingface.co/v1/chat/completions"
PROFILE_SCHEMA = "occ.hf-chat-profile.v1"
REQUEST_SCHEMA = "occ.hf-chat-request.v1"
RESULT_SCHEMA = "occ.hf-chat-result.v1"
ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
ROUTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}:[a-z0-9][a-z0-9-]{0,39}$")
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
COMPLETION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,200}$")
FORBIDDEN_ROUTING = {"fastest", "cheapest", "auto"}


class AdapterBlocked(ValueError):
    """Stable public failure code; never contains token or provider error text."""


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
    expected = {"schema", "api_token_env", "models", "timeout_seconds",
                "max_response_bytes"}
    if (not isinstance(profile, dict) or set(profile) != expected
            or profile.get("schema") != PROFILE_SCHEMA):
        raise AdapterBlocked("HF_PROFILE_SCHEMA")
    if profile.get("api_token_env") != "OCC_HF_TOKEN":
        raise AdapterBlocked("HF_BACKEND_TOKEN_ENV_REQUIRED")
    entries = profile.get("models")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
        raise AdapterBlocked("HF_MODEL_REGISTRY_REQUIRED")
    registry = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"alias", "route", "response_model"}:
            raise AdapterBlocked("HF_MODEL_REGISTRY_SCHEMA")
        alias, route, response_model = (entry.get("alias"), entry.get("route"),
                                        entry.get("response_model"))
        if not isinstance(alias, str) or not ALIAS.fullmatch(alias) or alias in registry:
            raise AdapterBlocked("HF_MODEL_ALIAS_REQUIRED")
        if not isinstance(route, str) or not ROUTE.fullmatch(route):
            raise AdapterBlocked("HF_EXACT_PROVIDER_ROUTE_REQUIRED")
        base, provider = route.rsplit(":", 1)
        if provider in FORBIDDEN_ROUTING:
            raise AdapterBlocked("HF_FALLBACK_ROUTING_FORBIDDEN")
        if (not isinstance(response_model, str) or not MODEL.fullmatch(response_model)
                or response_model != base):
            raise AdapterBlocked("HF_RESPONSE_MODEL_BINDING_REQUIRED")
        registry[alias] = {"route": route, "response_model": response_model,
                           "provider": provider}
    return {
        "registry": registry,
        "api_token_env": "OCC_HF_TOKEN",
        "timeout_seconds": _strict_int(profile.get("timeout_seconds"), 1, 60,
                                       "HF_TIMEOUT_LIMIT"),
        "max_response_bytes": _strict_int(profile.get("max_response_bytes"),
                                          1, 2_000_000,
                                          "HF_RESPONSE_BYTE_LIMIT"),
    }


def build_request(profile, request):
    config = validate_profile(profile)
    expected = {"schema", "model_alias", "messages", "max_tokens", "stream"}
    if (not isinstance(request, dict) or set(request) != expected
            or request.get("schema") != REQUEST_SCHEMA):
        raise AdapterBlocked("HF_REQUEST_SCHEMA")
    if request.get("stream") is not False:
        raise AdapterBlocked("HF_STREAM_FALSE_REQUIRED")
    selected = config["registry"].get(request.get("model_alias"))
    if selected is None:
        raise AdapterBlocked("HF_UNREGISTERED_MODEL_ALIAS")
    messages = request.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 50:
        raise AdapterBlocked("HF_MESSAGES_REQUIRED")
    normalized, total = [], 0
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or message.get("role") not in {"system", "user", "assistant"}):
            raise AdapterBlocked("HF_MESSAGE_SCHEMA")
        content = _bounded_text(message.get("content"), 50_000,
                                "HF_MESSAGE_CONTENT_REQUIRED")
        total += len(content.encode("utf-8"))
        if total > 100_000:
            raise AdapterBlocked("HF_MESSAGES_BYTE_LIMIT")
        normalized.append({"role": message["role"], "content": content})
    body = {"model": selected["route"], "messages": normalized,
            "max_tokens": _strict_int(request.get("max_tokens"), 1, 100_000,
                                      "HF_OUTPUT_TOKEN_LIMIT"),
            "stream": False}
    return config, selected, body


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
            raise AdapterBlocked("HF_RESPONSE_TOO_LARGE")


def _https_post(url, headers, payload, timeout, max_bytes, cancelled):
    if url != API_URL:
        raise AdapterBlocked("HF_ENDPOINT_NOT_PINNED")
    if _cancelled(cancelled):
        raise TransportCancelled(request_sent=False)
    request = Request(url, data=payload, headers=headers, method="POST")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            if response.geturl() != API_URL:
                raise AdapterBlocked("HF_REDIRECT_BLOCKED")
            return response.status, dict(response.headers.items()), _read_bounded(
                response, max_bytes, cancelled)
    except HTTPError as exc:
        try:
            raw = _read_bounded(exc, max_bytes, cancelled)
        finally:
            exc.close()
        return exc.code, dict(exc.headers.items()), raw
    except (TransportCancelled, AdapterBlocked):
        raise
    except (URLError, TimeoutError, OSError):
        raise TransportUnknown() from None


def _json_object(raw, code):
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AdapterBlocked(code) from None
    if not isinstance(value, dict):
        raise AdapterBlocked(code)
    return value


def _completion(value, expected_model):
    allowed = {"id", "object", "created", "model", "choices", "usage",
               "system_fingerprint", "service_tier"}
    if set(value) - allowed:
        raise AdapterBlocked("HF_RESPONSE_SCHEMA")
    if (not isinstance(value.get("id"), str)
            or not COMPLETION_ID.fullmatch(value["id"])
            or value.get("object") != "chat.completion"
            or value.get("model") != expected_model):
        raise AdapterBlocked("HF_RESPONSE_SCHEMA")
    choices, usage = value.get("choices"), value.get("usage")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(usage, dict):
        raise AdapterBlocked("HF_RESPONSE_SCHEMA")
    choice = choices[0]
    if (not isinstance(choice, dict) or set(choice) - {"index", "message", "finish_reason", "logprobs"}
            or choice.get("index") != 0 or not isinstance(choice.get("message"), dict)):
        raise AdapterBlocked("HF_CHOICE_SCHEMA")
    message = choice["message"]
    if (set(message) - {"role", "content", "reasoning_content", "tool_calls"}
            or message.get("role") != "assistant" or message.get("tool_calls") not in {None}):
        raise AdapterBlocked("HF_MESSAGE_RESPONSE_SCHEMA")
    content = _bounded_text(message.get("content"), 200_000,
                            "HF_OUTPUT_TEXT_REQUIRED", allow_empty=True)
    counts = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        counts[key] = _strict_int(usage.get(key), 0, 10_000_000,
                                  "HF_USAGE_SCHEMA")
    if counts["prompt_tokens"] + counts["completion_tokens"] != counts["total_tokens"]:
        raise AdapterBlocked("HF_USAGE_SCHEMA")
    return {"completion_id": value["id"], "model": expected_model,
            "output_text": content, "usage": counts}


def _error_kind(status, value):
    error = value.get("error")
    if isinstance(error, str):
        error_type, error_code = None, None
    elif isinstance(error, dict):
        error_type, error_code = error.get("type"), error.get("code")
        for item in (error_type, error_code):
            if item is not None and (not isinstance(item, str) or len(item) > 100):
                raise AdapterBlocked("HF_ERROR_SCHEMA")
    else:
        raise AdapterBlocked("HF_ERROR_SCHEMA")
    if status == 401:
        return "AUTHENTICATION_FAILED"
    if status in {402, 429}:
        return "HF_QUOTA_OR_RATE_LIMIT_STOP"
    raise AdapterBlocked("HF_UNHANDLED_HTTP_STATUS")


def execute(profile, request, *, store, budget_plan, op_key,
            reserve_microunits, environ=None, cancelled=lambda: False,
            transport=_https_post):
    """Perform at most one registry-pinned call and never fall back or retry."""
    config, selected, body = build_request(profile, request)
    if _cancelled(cancelled):
        return {"schema": RESULT_SCHEMA, "state": "CANCELLED", "request_sent": False,
                "budget": None, "fallback_attempted": False,
                "action_authority": False}
    reservation = budget.reserve_budget(store, budget_plan, op_key,
                                        reserve_microunits)
    reservation_id = reservation["reservation_id"]
    if reservation.get("reused"):
        quarantined = (budget.mark_budget_unknown(store, reservation_id)
                       if reservation["state"] == "RESERVED" else reservation)
        return {"schema": RESULT_SCHEMA, "state": "NEEDS_RECONCILIATION",
                "reason": "RESERVATION_REPLAY_BLOCKED", "request_sent": None,
                "budget": quarantined, "fallback_attempted": False,
                "action_authority": False}
    environment = os.environ if environ is None else environ
    token = environment.get(config["api_token_env"], "")
    if (not isinstance(token, str) or not token or len(token) > 4096
            or "\n" in token or "\r" in token):
        released = budget.release_budget(store, reservation_id,
                                         request_not_sent=True)
        return {"schema": RESULT_SCHEMA, "state": "BLOCKED",
                "reason": "HF_TOKEN_MISSING", "request_sent": False,
                "budget": released, "fallback_attempted": False,
                "action_authority": False}
    if _cancelled(cancelled):
        released = budget.release_budget(store, reservation_id,
                                         request_not_sent=True)
        return {"schema": RESULT_SCHEMA, "state": "CANCELLED",
                "request_sent": False, "budget": released,
                "fallback_attempted": False, "action_authority": False}
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    headers = {"Authorization": "Bearer " + token,
               "Content-Type": "application/json",
               "User-Agent": "occ-hf-chat/1"}
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
                "fallback_attempted": False, "action_authority": False}
    except (TransportUnknown, AdapterBlocked):
        budget.mark_budget_unknown(store, reservation_id)
        raise
    except Exception:
        budget.mark_budget_unknown(store, reservation_id)
        raise AdapterBlocked("HF_TRANSPORT_FAILED") from None
    if (type(status) is not int or not 100 <= status <= 599
            or not isinstance(response_headers, dict) or not isinstance(raw, bytes)
            or len(raw) > config["max_response_bytes"]):
        budget.mark_budget_unknown(store, reservation_id)
        raise AdapterBlocked("HF_TRANSPORT_CONTRACT")
    receipt_hash = hashlib.sha256(str(status).encode() + b"\0" + raw).hexdigest()
    try:
        value = _json_object(raw, "HF_RESPONSE_JSON_INVALID")
    except AdapterBlocked:
        budget.mark_budget_unknown(store, reservation_id)
        raise
    if status in {401, 402, 429}:
        try:
            reason = _error_kind(status, value)
        except AdapterBlocked:
            budget.mark_budget_unknown(store, reservation_id)
            raise
        settled = budget.settle_budget(store, reservation_id, 0, receipt_hash)
        return {"schema": RESULT_SCHEMA, "state": "BLOCKED", "reason": reason,
                "http_status": status, "retryable": False, "request_sent": True,
                "budget": settled, "fallback_attempted": False,
                "action_authority": False}
    if not 200 <= status < 300:
        budget.mark_budget_unknown(store, reservation_id)
        raise AdapterBlocked("HF_UNHANDLED_HTTP_STATUS")
    try:
        parsed = _completion(value, selected["response_model"])
    except AdapterBlocked:
        budget.mark_budget_unknown(store, reservation_id)
        raise
    quarantined = budget.mark_budget_unknown(store, reservation_id)
    return {"schema": RESULT_SCHEMA, "state": "DONE_REQUIRES_COST_RECONCILIATION",
            **parsed, "provider": selected["provider"],
            "provider_receipt_sha256": receipt_hash, "request_sent": True,
            "budget": quarantined, "fallback_attempted": False,
            "action_authority": False}
