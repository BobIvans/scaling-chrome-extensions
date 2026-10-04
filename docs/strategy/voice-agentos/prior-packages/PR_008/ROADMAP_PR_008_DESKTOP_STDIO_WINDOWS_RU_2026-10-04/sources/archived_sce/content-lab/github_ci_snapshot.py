"""Authenticated, fail-closed GitHub check-runs transport for OCC CI snapshots.

The transport reads a registered repository and token environment variable from
the operator policy.  It never publishes commits or starts workers.  Its only
effect is an atomic replacement of the existing ``ci.snapshot_file``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener


API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
MAX_RESPONSE_BYTES = 2_000_000
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
TOKEN_ENV = re.compile(r"^OCC_[A-Z0-9_]{1,59}$")


class TransportBlocked(ValueError):
    """A stable public error code; never contains credentials or response text."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        return None


def _strict_int(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise TransportBlocked("CI_TRANSPORT_INTEGER_LIMIT")
    return value


def validate_transport(ci):
    transport = ci.get("transport") if isinstance(ci, dict) else None
    if not isinstance(transport, dict):
        raise TransportBlocked("CI_TRANSPORT_REQUIRED")
    allowed = {"kind", "repository", "token_env", "timeout_seconds", "max_pages"}
    if set(transport) - allowed or transport.get("kind") != "github_check_runs_v1":
        raise TransportBlocked("CI_TRANSPORT_SCHEMA")
    repository = transport.get("repository")
    token_env = transport.get("token_env")
    if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
        raise TransportBlocked("CI_REPOSITORY_REQUIRED")
    if not isinstance(token_env, str) or not TOKEN_ENV.fullmatch(token_env):
        raise TransportBlocked("CI_PRIVATE_TOKEN_ENV_REQUIRED")
    timeout = _strict_int(transport.get("timeout_seconds", 15), 1, 30)
    max_pages = _strict_int(transport.get("max_pages", 10), 1, 10)
    required = ci.get("required_checks")
    if (not isinstance(required, list) or not required or len(required) != len(set(required))
            or not all(isinstance(name, str) and 0 < len(name) <= 200 for name in required)):
        raise TransportBlocked("CI_REQUIRED_CHECKS_INVALID")
    snapshot_file = ci.get("snapshot_file")
    if not isinstance(snapshot_file, str) or not Path(snapshot_file).is_absolute():
        raise TransportBlocked("CI_ABSOLUTE_SNAPSHOT_FILE_REQUIRED")
    return {
        "repository": repository,
        "token_env": token_env,
        "timeout_seconds": timeout,
        "max_pages": max_pages,
        "required_checks": list(required),
        "snapshot_file": Path(snapshot_file),
    }


def _request_json(url, token, timeout):
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "User-Agent": "occ-ci-snapshot/1",
        "X-GitHub-Api-Version": API_VERSION,
    })
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            if response.geturl() != url:
                raise TransportBlocked("GITHUB_REDIRECT_BLOCKED")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise TransportBlocked("GITHUB_AUTH_FAILED") from None
        raise TransportBlocked("GITHUB_HTTP_ERROR") from None
    except (URLError, TimeoutError, OSError):
        raise TransportBlocked("GITHUB_NETWORK_ERROR") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise TransportBlocked("GITHUB_RESPONSE_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise TransportBlocked("GITHUB_RESPONSE_INVALID") from None
    if not isinstance(value, dict):
        raise TransportBlocked("GITHUB_RESPONSE_INVALID")
    return value


def _snapshot(head_sha, config, status, checks=(), reason=None):
    value = {
        "schema": "occ.ci-snapshot.v1",
        "origin": "authenticated_github_check_runs_v1",
        "repository": config["repository"],
        "head_sha": head_sha,
        "required_checks": config["required_checks"],
        "transport_status": status,
        "checks": list(checks),
    }
    if reason:
        value["transport_error"] = reason
    return value


def _atomic_write(path, value):
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir() or path.is_symlink():
        raise TransportBlocked("CI_SNAPSHOT_PATH_UNSAFE")
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False) + "\n"
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(dir=parent, prefix="." + path.name + ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            os.chmod(temporary, 0o600)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    except OSError:
        raise TransportBlocked("CI_SNAPSHOT_WRITE_FAILED") from None
    finally:
        if temporary:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def collect(config, head_sha, token, requester=_request_json):
    if not SHA.fullmatch(head_sha):
        raise TransportBlocked("EXACT_HEAD_SHA_REQUIRED")
    if not isinstance(token, str) or not token or len(token) > 4096 or "\n" in token or "\r" in token:
        raise TransportBlocked("GITHUB_TOKEN_MISSING")
    required = set(config["required_checks"])
    checks = []
    repository = quote(config["repository"], safe="/")
    for page in range(1, config["max_pages"] + 1):
        url = (f"{API_ROOT}/repos/{repository}/commits/{head_sha}/check-runs"
               f"?filter=all&per_page=100&page={page}")
        body = requester(url, token, config["timeout_seconds"])
        runs = body.get("check_runs")
        total = body.get("total_count")
        if (not isinstance(runs, list) or len(runs) > 100 or type(total) is not int
                or total < len(runs)):
            raise TransportBlocked("GITHUB_CHECK_RUNS_INVALID")
        for run in runs:
            if not isinstance(run, dict):
                continue
            name, run_id = run.get("name"), run.get("id")
            suite, app = run.get("check_suite"), run.get("app")
            if (name not in required or type(run_id) is not int or not isinstance(suite, dict)
                    or suite.get("head_sha") != head_sha or not isinstance(app, dict)
                    or app.get("slug") != "github-actions"):
                continue
            status, conclusion = run.get("status"), run.get("conclusion")
            if not isinstance(status, str) or not status or len(status) > 50:
                continue
            if conclusion is not None and (not isinstance(conclusion, str) or len(conclusion) > 50):
                continue
            checks.append({"name": name, "run_id": run_id, "head_sha": head_sha,
                           "status": status, "conclusion": conclusion})
        if len(runs) < 100 or total <= page * 100:
            break
    else:
        raise TransportBlocked("GITHUB_CHECK_RUN_PAGE_LIMIT")
    checks.sort(key=lambda item: (item["name"], item["run_id"],
                                  item["status"], str(item["conclusion"])))
    return _snapshot(head_sha, config, "OBSERVED", checks)


def refresh(policy, repo_profile, head_sha, *, environ=None, requester=_request_json):
    if not isinstance(policy, dict):
        raise TransportBlocked("POLICY_OBJECT_REQUIRED")
    repos = policy.get("repos")
    profile = repos.get(repo_profile) if isinstance(repos, dict) else None
    if not isinstance(profile, dict):
        raise TransportBlocked("REGISTERED_REPO_PROFILE_REQUIRED")
    config = validate_transport(profile.get("ci"))
    environment = os.environ if environ is None else environ
    token = environment.get(config["token_env"], "")
    try:
        snapshot = collect(config, head_sha, token, requester)
    except TransportBlocked as exc:
        if SHA.fullmatch(head_sha):
            _atomic_write(config["snapshot_file"],
                          _snapshot(head_sha, config, "BLOCKED", reason=str(exc)))
        raise
    _atomic_write(config["snapshot_file"], snapshot)
    return {"state": "DONE", "repository": config["repository"],
            "head_sha": head_sha, "snapshot_file": str(config["snapshot_file"]),
            "checks_observed": len(snapshot["checks"]), "required_checks": config["required_checks"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--repo-profile", required=True)
    parser.add_argument("--head-sha", required=True)
    args = parser.parse_args(argv)
    try:
        if args.policy.is_symlink() or not args.policy.is_file() or args.policy.stat().st_size > 2_200_000:
            raise TransportBlocked("REGULAR_BOUNDED_POLICY_REQUIRED")
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        result = refresh(policy, args.repo_profile, args.head_sha)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, KeyError, TypeError, json.JSONDecodeError, TransportBlocked) as exc:
        reason = str(exc) if isinstance(exc, TransportBlocked) else "CI_TRANSPORT_INPUT_INVALID"
        print(json.dumps({"state": "BLOCKED", "reason": reason}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
