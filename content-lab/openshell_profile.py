"""Fail-closed static review for the OCC OpenShell provider profile.

This module does not install, start, attach, or call OpenShell.  It verifies the
small provider-profile subset approved for the F-26 OpenAI Responses adapter and
emits a secret-free qualification result.  Runtime qualification remains a
separate operator action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REVIEW_SCHEMA = "occ.openshell-profile-review.v1"
RESULT_SCHEMA = "occ.openshell-profile-review-result.v1"
PROFILE_ID = "occ-openai-responses"
PROVIDER_NAME = "occ-openai"
NATIVE_BASE_URL = "https://api.openai.com/v1"
NATIVE_REQUEST_URL = "https://api.openai.com/v1/responses"
ENDPOINT = {"host": "api.openai.com", "port": 443,
            "path": "/v1/responses", "protocol": "rest"}
BINARY = "/opt/occ/bin/python3"
PLATFORM = "windows-wsl2-docker-desktop-x86_64"
SUPPORT_STATUS = "EXPERIMENTAL_NOT_RUNTIME_QUALIFIED"


class ProfileBlocked(ValueError):
    """Stable validation failure; messages never contain profile values."""


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_profile(profile):
    expected = {"id", "display_name", "description", "category",
                "inference_capable", "credentials", "discovery", "endpoints",
                "binaries"}
    if not isinstance(profile, dict) or set(profile) != expected:
        raise ProfileBlocked("OPENSHELL_PROFILE_SCHEMA")
    if (profile.get("id") != PROFILE_ID
            or profile.get("category") != "inference"
            or profile.get("inference_capable") is not True
            or not isinstance(profile.get("display_name"), str)
            or not profile["display_name"]
            or not isinstance(profile.get("description"), str)
            or not profile["description"]):
        raise ProfileBlocked("OPENSHELL_PROFILE_IDENTITY")

    credentials = profile.get("credentials")
    required_credential = {"name": "api_key", "env_vars": ["OPENAI_API_KEY"],
                           "required": True, "auth_style": "bearer"}
    if credentials != [required_credential]:
        raise ProfileBlocked("OPENSHELL_CREDENTIAL_DECLARATION")
    if profile.get("discovery") != {"credentials": ["api_key"]}:
        raise ProfileBlocked("OPENSHELL_CREDENTIAL_DISCOVERY")

    expected_endpoint = {**ENDPOINT, "enforcement": "enforce",
                         "allow_uninspected_credentials": False,
                         "rules": [{"allow": {"method": "POST",
                                               "path": "/v1/responses"}}]}
    if profile.get("endpoints") != [expected_endpoint]:
        raise ProfileBlocked("OPENSHELL_NATIVE_ENDPOINT_BINDING")
    if profile.get("binaries") != [BINARY]:
        raise ProfileBlocked("OPENSHELL_BINARY_BINDING")
    return profile


def _validate_review(review):
    expected = {"schema", "reviewed_openshell_version", "platform",
                "support_status", "runtime_smoke", "profile_id",
                "provider_name", "native_base_url", "native_request_url",
                "endpoint", "binaries", "provider_attachment_required",
                "provider_api_budget"}
    if (not isinstance(review, dict) or set(review) != expected
            or review.get("schema") != REVIEW_SCHEMA):
        raise ProfileBlocked("OPENSHELL_REVIEW_SCHEMA")
    version = review.get("reviewed_openshell_version")
    if (not isinstance(version, str) or not version.startswith("0.1.")
            or len(version) > 20):
        raise ProfileBlocked("OPENSHELL_REVIEW_VERSION")
    if (review.get("platform") != PLATFORM
            or review.get("support_status") != SUPPORT_STATUS
            or review.get("runtime_smoke") != "NOT_RUN"):
        raise ProfileBlocked("OPENSHELL_WSL2_STATUS_REQUIRED")
    if (review.get("profile_id") != PROFILE_ID
            or review.get("provider_name") != PROVIDER_NAME
            or review.get("native_base_url") != NATIVE_BASE_URL
            or review.get("native_request_url") != NATIVE_REQUEST_URL
            or review.get("endpoint") != ENDPOINT):
        raise ProfileBlocked("OPENSHELL_REVIEW_ENDPOINT_MISMATCH")
    if review.get("binaries") != [BINARY]:
        raise ProfileBlocked("OPENSHELL_REVIEW_BINARY_MISMATCH")
    if review.get("provider_attachment_required") is not True:
        raise ProfileBlocked("OPENSHELL_PROVIDER_ATTACHMENT_REQUIRED")
    if review.get("provider_api_budget") != 0:
        raise ProfileBlocked("OPENSHELL_ZERO_PROVIDER_BUDGET_REQUIRED")
    return review


def qualify(profile, review):
    profile = _validate_profile(profile)
    review = _validate_review(review)
    return {
        "schema": RESULT_SCHEMA,
        "state": "STATICALLY_REVIEWED_RUNTIME_UNQUALIFIED",
        "runnable": False,
        "profile_id": PROFILE_ID,
        "provider_name": PROVIDER_NAME,
        "profile_sha256": _digest(profile),
        "endpoint_binding": {**ENDPOINT, "request_url": NATIVE_REQUEST_URL},
        "binary_binding": BINARY,
        "provider_attachment_required": True,
        "platform": PLATFORM,
        "support_status": SUPPORT_STATUS,
        "runtime_smoke": "NOT_RUN",
        "provider_api_budget": 0,
    }


def _load(path, code):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ProfileBlocked(code) from None
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = qualify(_load(args.profile, "OPENSHELL_PROFILE_READ"),
                         _load(args.review, "OPENSHELL_REVIEW_READ"))
        output = {"ok": True, "result": result}
    except ProfileBlocked as exc:
        output = {"ok": False, "error": str(exc)}
    print(json.dumps(output, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0 if output["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
