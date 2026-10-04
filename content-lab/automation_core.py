"""Deterministic local automation using Content Lab's existing SQLite store.

The operator policy owns paths, patches and test commands. Jobs never supply
shell commands, credentials or new permissions. No model, browser, push, merge,
signer or sender is invoked. A Git worktree is isolation of edits, not a sandbox
for untrusted executable code; register only reviewed patches/test profiles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

from content_lab import _database, _insert_item, _write_receipt, extract_file

NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
TOKEN_ENV = re.compile(r"^OCC_[A-Z0-9_]{1,59}$")
SUPPORTED = {".txt", ".md", ".json", ".csv", ".py", ".js", ".ts",
             ".yaml", ".yml", ".html", ".htm", ".srt", ".vtt"}
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED"}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def strict_int(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("INTEGER_LIMIT_REQUIRED")
    return value


def identifier(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError("IDENTIFIER_REQUIRED")
    return value


def load_json(path, limit=2_200_000):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("REGULAR_BOUNDED_JSON_REQUIRED")
    return json.loads(path.read_text(encoding="utf-8"))


def connection(store, *, configure=None):
    db = _database(store) if configure is None else _database(store, configure=configure)
    db.row_factory = sqlite3.Row
    try:
        return _initialize_connection(db)
    except BaseException:
        db.close()
        raise


def read_connection(store):
    """Open the existing owner without creating files, tables or migrations."""
    path = Path(store) / 'content.sqlite3'
    if path.is_symlink() or not path.is_file():
        raise ValueError('DESKTOP_SETUP_REQUIRED')
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        return db
    except BaseException:
        db.close()
        raise


def _initialize_connection(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sync_heads(
          namespace TEXT, source_key TEXT, item_id TEXT, raw_hash TEXT,
          generation TEXT, present INTEGER, PRIMARY KEY(namespace, source_key));
        CREATE TABLE IF NOT EXISTS sync_versions(
          namespace TEXT, source_key TEXT, item_id TEXT, observed REAL,
          PRIMARY KEY(namespace, source_key, item_id));
        CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY, task_key TEXT UNIQUE, payload TEXT,
          payload_hash TEXT, policy_hash TEXT, state TEXT, attempt INTEGER,
          max_attempts INTEGER, available REAL, lease_until REAL,
          lease_token TEXT, cancel_requested INTEGER, checkpoint TEXT,
          result TEXT, created REAL, updated REAL);
        CREATE TABLE IF NOT EXISTS job_events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT,
          state TEXT, detail TEXT, observed REAL);
    """)
    return db


def sync(store, namespace, root, *, max_files=100, max_bytes=25_000_000, progress=None):
    """Atomic head replacement; edited/deleted inputs retain historical versions."""
    identifier(namespace)
    strict_int(max_files, 1, 1000)
    strict_int(max_bytes, 1, 100_000_000)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("SOURCE_ROOT_REQUIRED")
    root = root.resolve()
    if store.resolve().is_relative_to(root):
        raise ValueError("STORE_MUST_BE_OUTSIDE_SOURCE")
    items, total, visited = [], 0, 0
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                         and d != "node_modules" and not (Path(folder) / d).is_symlink())
        for name in sorted(files):
            if progress:
                progress()
            visited += 1
            if visited > 10_000:
                raise ValueError("SCAN_ENTRY_BUDGET_EXCEEDED")
            path = Path(folder) / name
            if name.startswith(".") or path.suffix.lower() not in SUPPORTED:
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("SOURCE_PATH_BOUNDARY")
            before = path.stat()
            total += before.st_size
            if len(items) >= max_files or total > max_bytes:
                raise ValueError("SYNC_BUDGET_EXCEEDED")
            item = extract_file(path)
            after = path.stat()
            if path.is_symlink() or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError("SOURCE_CHANGED_DURING_READ")
            key = path.relative_to(root).as_posix()
            item.update(namespace=namespace, source_key=key)
            item["id"] = digest({"namespace": namespace, "source_key": key,
                                 "extraction_id": item["id"]})
            items.append(item)
    generation, inserted, unchanged, receipts = uuid.uuid4().hex, 0, 0, []
    db = connection(store)
    try:
        with db:
            for item in items:
                count, stored = _insert_item(db, item)
                inserted += count
                previous = db.execute("SELECT item_id FROM sync_heads WHERE namespace=? AND source_key=?",
                                      (namespace, item["source_key"])).fetchone()
                unchanged += int(previous is not None and previous[0] == item["id"])
                db.execute("INSERT OR IGNORE INTO sync_versions VALUES (?,?,?,?)",
                           (namespace, item["source_key"], item["id"], time.time()))
                db.execute("INSERT INTO sync_heads VALUES (?,?,?,?,?,1) ON CONFLICT(namespace,source_key) DO UPDATE SET item_id=excluded.item_id, raw_hash=excluded.raw_hash, generation=excluded.generation, present=1",
                           (namespace, item["source_key"], item["id"], item["input_sha256"], generation))
                receipts.append((item["id"], stored))
            db.execute("UPDATE sync_heads SET present=0 WHERE namespace=? AND generation<>?", (namespace, generation))
        missing = db.execute("SELECT count(*) FROM sync_heads WHERE namespace=? AND present=0", (namespace,)).fetchone()[0]
    finally:
        db.close()
    # JSON exports are a rebuildable projection; SQLite is the committed owner.
    for item_id, stored in receipts:
        _write_receipt(store, item_id, stored)
    return {"state": "SYNCED", "namespace": namespace, "files": len(items),
            "new_versions": inserted, "unchanged": unchanged, "missing": missing,
            "bytes": total, "model_calls": 0}


def search(store, namespace, query, limit=10, *, read_only=False):
    identifier(namespace)
    strict_int(limit, 1, 50)
    if not isinstance(query, str) or len(query) > 1000:
        raise ValueError("BOUNDED_QUERY_REQUIRED")
    terms = re.findall(r"\w+", query, re.UNICODE)
    if not terms:
        raise ValueError("QUERY_TERMS_REQUIRED")
    match = " AND ".join('"' + term + '"' for term in terms)
    db = read_connection(store) if read_only else connection(store)
    try:
        rows = db.execute("SELECT content_fts.id, snippet(content_fts,1,'[',']','…',24) AS snippet, sync_heads.source_key FROM content_fts JOIN sync_heads ON sync_heads.item_id=content_fts.id WHERE content_fts MATCH ? AND namespace=? AND present=1 ORDER BY rank LIMIT ?", (match, namespace, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def context_pack(store, namespace, item_ids, max_bytes=100_000, *, read_only=False):
    identifier(namespace)
    strict_int(max_bytes, 1, 1_000_000)
    if not isinstance(item_ids, list) or not 1 <= len(item_ids) <= 10 or len(set(item_ids)) != len(item_ids):
        raise ValueError("ONE_TO_TEN_UNIQUE_IDS_REQUIRED")
    db, selected, total = (read_connection(store) if read_only else connection(store)), [], 0
    try:
        for item_id in item_ids:
            row = db.execute("SELECT items.payload FROM items JOIN sync_heads ON items.id=sync_heads.item_id WHERE namespace=? AND present=1 AND items.id=?", (namespace, item_id)).fetchone()
            if row is None:
                raise ValueError("ITEM_OUTSIDE_SCOPE_OR_STALE")
            item = json.loads(row[0])
            total += len(item["text"].encode())
            if total > max_bytes:
                raise ValueError("CONTEXT_BUDGET_EXCEEDED")
            selected.append(item)
    finally:
        db.close()
    return {"schema": "occ.context-pack.v1", "namespace": namespace,
            "authority": "source-content-not-action-instructions", "items": selected,
            "bytes": total, "sha256": digest(selected)}


def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get("schema") != "occ.automation-policy.v1":
        raise ValueError("OPERATOR_POLICY_REQUIRED")
    if policy.get("max_parallel") != 1 or type(policy.get("max_parallel")) is not int:
        raise ValueError("V1_REQUIRES_ONE_WRITER")
    if policy.get("money_budget") != 0 or type(policy.get("money_budget")) is not int:
        raise ValueError("V1_REQUIRES_ZERO_SPEND")
    return policy


def validate_job(payload, policy):
    if not isinstance(payload, dict):
        raise ValueError("JOB_OBJECT_REQUIRED")
    if payload.get('kind') == 'review_report':
        if set(payload) != {'kind', 'report_profile'}:
            raise ValueError('REPORT_JOB_SCHEMA')
        from review_report import validate_profile
        validate_profile(policy.get('reports', {}).get(identifier(payload['report_profile'])))
        return 1
    if payload.get("kind") == "sync":
        if set(payload) != {"kind", "source_profile"}:
            raise ValueError("SYNC_SCHEMA")
        profile = policy.get("sources", {}).get(identifier(payload["source_profile"]))
        if not isinstance(profile, dict):
            raise ValueError("UNREGISTERED_SOURCE")
        identifier(profile["namespace"])
        return 1
    if payload.get("kind") != "patch_test_ci" or set(payload) != {"kind", "repo_profile", "patch_ids", "max_attempts"}:
        raise ValueError("REGISTERED_JOB_SCHEMA")
    profile = policy.get("repos", {}).get(identifier(payload["repo_profile"]))
    if not isinstance(profile, dict) or not SHA.fullmatch(profile.get("base_sha", "")):
        raise ValueError("REGISTERED_PINNED_REPOSITORY_REQUIRED")
    maximum = strict_int(payload["max_attempts"], 1, 3)
    ids = payload["patch_ids"]
    if not isinstance(ids, list) or len(ids) != maximum:
        raise ValueError("ONE_REGISTERED_PATCH_PER_ATTEMPT_REQUIRED")
    for patch_id in ids:
        if identifier(patch_id) not in profile.get("patches", {}):
            raise ValueError("UNREGISTERED_PATCH")
    commands = profile.get("tests")
    if not isinstance(commands, list) or not 1 <= len(commands) <= 10:
        raise ValueError("REGISTERED_TESTS_REQUIRED")
    for argv in commands:
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and a and "\0" not in a for a in argv):
            raise ValueError("TEST_ARGV_REQUIRED")
    strict_int(profile.get("timeout_seconds", 60), 1, 300)
    if type(profile.get("git_autocrlf", False)) is not bool:
        raise ValueError("GIT_AUTOCRLF_BOOLEAN_REQUIRED")
    ci = profile.get("ci")
    if not isinstance(ci, dict) or not isinstance(ci.get("required_checks"), list) or not ci["required_checks"] or len(set(ci["required_checks"])) != len(ci["required_checks"]) or not all(isinstance(n, str) and n for n in ci["required_checks"]):
        raise ValueError("CI_SNAPSHOT_AND_REQUIRED_CHECKS_REQUIRED")
    if not isinstance(ci.get("snapshot_file"), str):
        raise ValueError("OPERATOR_CI_SNAPSHOT_REQUIRED")
    transport = ci.get("transport")
    if transport is not None:
        allowed = {"kind", "repository", "token_env", "timeout_seconds", "max_pages"}
        if (not isinstance(transport, dict) or set(transport) - allowed
                or transport.get("kind") != "github_check_runs_v1"
                or not isinstance(transport.get("repository"), str)
                or not GITHUB_REPOSITORY.fullmatch(transport["repository"])
                or not isinstance(transport.get("token_env"), str)
                or not TOKEN_ENV.fullmatch(transport["token_env"])):
            raise ValueError("CI_TRANSPORT_SCHEMA")
        if (not Path(ci["snapshot_file"]).is_absolute()
                or any(len(name) > 200 for name in ci["required_checks"])):
            raise ValueError("CI_TRANSPORT_SCHEMA")
        strict_int(transport.get("timeout_seconds", 15), 1, 30)
        strict_int(transport.get("max_pages", 10), 1, 10)
    strict_int(profile.get("retry_delay_seconds", 1), 0, 300)
    allowed = profile.get("allowed_paths")
    if not isinstance(allowed, list) or not allowed or not all(isinstance(p, str) and p and not p.startswith(("/", "\\")) and ".." not in Path(p).parts for p in allowed):
        raise ValueError("REGISTERED_RELATIVE_PATHS_REQUIRED")
    return maximum


def event(db, job_id, state, detail):
    db.execute("INSERT INTO job_events(job_id,state,detail,observed) VALUES (?,?,?,?)", (job_id, state, encoded(detail), time.time()))


def enqueue(store, policy, task_key, payload):
    validate_policy(policy)
    identifier(task_key)
    maximum = validate_job(payload, policy)
    db, job_id, now = connection(store), uuid.uuid4().hex, time.time()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM jobs WHERE task_key=?", (task_key,)).fetchone()
        if row:
            if row["payload_hash"] != digest(payload) or row["policy_hash"] != digest(policy):
                raise ValueError("TASK_KEY_CONTENT_CONFLICT")
            db.commit()
            return {"id": row["id"], "state": row["state"], "reused": True}
        if db.execute("SELECT count(*) FROM jobs WHERE state NOT IN ('SUCCEEDED','FAILED','CANCELLED','BLOCKED')").fetchone()[0] >= 1000:
            raise ValueError("QUEUE_LIMIT")
        db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,'QUEUED',0,?,?,0,NULL,0,'{}','{}',?,?)", (job_id, task_key, encoded(payload), digest(payload), digest(policy), maximum, now, now, now))
        event(db, job_id, "QUEUED", {"task_key": task_key})
        db.commit()
        return {"id": job_id, "state": "QUEUED", "reused": False}
    finally:
        db.close()


class Cancelled(Exception):
    pass


class Core:
    def __init__(self, store, policy):
        self.store, self.policy = Path(store), validate_policy(policy)

    def get(self, job_id):
        db = connection(self.store)
        try:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise ValueError("JOB_NOT_FOUND")
            result = dict(row)
            for key in ("payload", "checkpoint", "result"):
                result[key] = json.loads(result[key])
            return result
        finally:
            db.close()

    def cancel(self, job_id):
        db = connection(self.store)
        try:
            with db:
                row = db.execute("SELECT state FROM jobs WHERE id=?", (job_id,)).fetchone()
                if not row:
                    raise ValueError("JOB_NOT_FOUND")
                if row[0] in TERMINAL:
                    return {"state": row[0]}
                state = row[0] if row[0] in {"RUNNING", "NEEDS_RECONCILIATION"} else "CANCELLED"
                db.execute("UPDATE jobs SET cancel_requested=1,state=?,updated=? WHERE id=?", (state, time.time(), job_id))
                event(db, job_id, state, {"cancel_requested": True})
                return {"state": state}
        finally:
            db.close()

    def abandon_orphan(self, job_id, process_stopped):
        if process_stopped is not True:
            raise ValueError("OPERATOR_PROCESS_STOP_CONFIRMATION_REQUIRED")
        db = connection(self.store)
        try:
            with db:
                changed = db.execute("UPDATE jobs SET state='BLOCKED',result=?,updated=? WHERE id=? AND state='NEEDS_RECONCILIATION'",
                                     (encoded({"reason": "OPERATOR_ABANDONED_AFTER_PROCESS_STOP_CHECK"}), time.time(), job_id)).rowcount
                if not changed:
                    raise ValueError("ORPHAN_RECONCILIATION_STATE_REQUIRED")
                event(db, job_id, "BLOCKED", {"operator_verified_process_stopped": True})
            return {"state": "BLOCKED", "id": job_id}
        finally:
            db.close()

    def claim(self):
        db, now = connection(self.store), time.time()
        try:
            db.execute("BEGIN IMMEDIATE")
            for row in db.execute("SELECT id FROM jobs WHERE state='RUNNING' AND lease_until<?", (now,)).fetchall():
                db.execute("UPDATE jobs SET state='NEEDS_RECONCILIATION',lease_token=NULL,updated=? WHERE id=?", (now, row[0]))
                event(db, row[0], "NEEDS_RECONCILIATION", {"reason": "expired_lease_unknown_process_outcome"})
            # An orphan may still run. Do not overlap it with a new writer.
            if db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','NEEDS_RECONCILIATION') LIMIT 1").fetchone():
                db.commit()
                return None
            row = db.execute("SELECT * FROM jobs WHERE state IN ('QUEUED','RETRY_READY') AND available<=? ORDER BY created,id LIMIT 1", (now,)).fetchone()
            if not row:
                db.commit()
                return None
            if row["policy_hash"] != digest(self.policy):
                db.execute("UPDATE jobs SET state='BLOCKED',result=?,updated=? WHERE id=?", (encoded({"reason": "POLICY_CHANGED"}), now, row["id"]))
                event(db, row["id"], "BLOCKED", {"reason": "POLICY_CHANGED"})
                db.commit()
                return None
            token = uuid.uuid4().hex
            db.execute("UPDATE jobs SET state='RUNNING',attempt=attempt+1,lease_token=?,lease_until=?,updated=? WHERE id=?", (token, now + 30, now, row["id"]))
            event(db, row["id"], "RUNNING", {"attempt": row["attempt"] + 1})
            db.commit()
            return self.get(row["id"])
        finally:
            db.close()

    def reconcile_report(self, job_id, process_stopped):
        # Explicit operator check is required: a lost lease may still write.
        if process_stopped is not True:
            raise ValueError('OPERATOR_PROCESS_STOP_CONFIRMATION_REQUIRED')
        from review_report import expected_report, output_path, verify_output
        db = connection(self.store)
        try:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None or row['state'] != 'NEEDS_RECONCILIATION':
                raise ValueError('ORPHAN_RECONCILIATION_STATE_REQUIRED')
            payload = json.loads(row['payload'])
            if (row['policy_hash'] != digest(self.policy) or row['payload_hash'] != digest(payload)
                    or payload.get('kind') != 'review_report'):
                raise ValueError('REPORT_RECONCILIATION_SCOPE')
            validate_job(payload, self.policy)
            profile = self.policy['reports'][payload['report_profile']]
            try:
                expected = expected_report(self.store, profile)
                result = verify_output(output_path(self.store, profile), expected)
                state = 'SUCCEEDED'
            except (OSError, ValueError) as exc:
                code = str(exc)
                result = {'reason': code if re.fullmatch(r'[A-Z_]{1,100}', code) else 'REPORT_OUTPUT_UNAVAILABLE'}
                state = 'BLOCKED'
            if row['cancel_requested']:
                state = 'CANCELLED'
            db.execute('UPDATE jobs SET state=?,result=?,updated=? WHERE id=?',
                       (state, encoded(result), time.time(), job_id))
            event(db, job_id, state, result | {'operator_verified_process_stopped': True})
            db.commit()
        finally:
            db.close()
        return self.get(job_id)

    def heartbeat(self, job):
        db = connection(self.store)
        try:
            with db:
                row = db.execute("SELECT cancel_requested,state,lease_token FROM jobs WHERE id=?", (job["id"],)).fetchone()
                if not row or row[0] or row[1] != "RUNNING" or row[2] != job["lease_token"]:
                    raise Cancelled()
                db.execute("UPDATE jobs SET lease_until=? WHERE id=?", (time.time() + 30, job["id"]))
        finally:
            db.close()

    def transition(self, job, state, *, result=None, checkpoint=None, delay=0):
        db = connection(self.store)
        try:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone()
            if current["lease_token"] != job["lease_token"]:
                raise ValueError("LEASE_LOST")
            if current["cancel_requested"] and state != "RUNNING":
                state = "CANCELLED"
            db.execute("UPDATE jobs SET state=?,result=?,checkpoint=?,available=?,updated=? WHERE id=?",
                       (state, encoded(result or {}), encoded(checkpoint if checkpoint is not None else json.loads(current["checkpoint"])), time.time() + delay, time.time(), job["id"]))
            event(db, job["id"], state, result or checkpoint or {})
            db.commit()
        finally:
            db.close()

    def command(self, job, argv, cwd, timeout):
        self.heartbeat(job)
        # Do not inherit API keys, desktop IPC, agent credentials or Git hooks.
        env = {key: value for key, value in os.environ.items()
               if key in {"PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL"}}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0", PYTHONNOUSERSITE="1")
        started, stopped = time.monotonic(), None
        with tempfile.TemporaryFile() as output:
            kwargs = {"start_new_session": True} if os.name != "nt" else {}
            process = subprocess.Popen(argv, cwd=cwd, env=env, shell=False,
                                       stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, **kwargs)
            try:
                while process.poll() is None:
                    self.heartbeat(job)
                    if time.monotonic() - started > timeout:
                        stopped = "COMMAND_TIMEOUT"
                        break
                    if os.fstat(output.fileno()).st_size > 128_000:
                        stopped = "COMMAND_OUTPUT_LIMIT"
                        break
                    time.sleep(0.05)
            finally:
                if process.poll() is None:
                    if os.name == "nt":
                        subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    process.wait(timeout=5)
            output.seek(0)
            raw = output.read(128_001)
        if len(raw) > 128_000:
            stopped = "COMMAND_OUTPUT_LIMIT"
        return {"argv": argv, "exit_code": process.returncode,
                "reason": stopped, "output": raw[:128_000].decode("utf-8", errors="replace"),
                "output_truncated": len(raw) > 128_000,
                "seconds": round(time.monotonic() - started, 3)}

    def git(self, job, repo, *args):
        profile = self.policy.get("repos", {}).get(job["payload"].get("repo_profile"), {})
        autocrlf = "true" if profile.get("git_autocrlf", False) else "false"
        argv = ["git", "-c", "core.hooksPath=" + os.devnull,
                "-c", "core.autocrlf=" + autocrlf,
                "-c", "commit.gpgSign=false", "-c", "user.name=OCC Automation",
                "-c", "user.email=occ-local@invalid", *args]
        result = self.command(job, argv, repo, 30)
        if result["reason"] or result["exit_code"]:
            raise ValueError("GIT_OPERATION_FAILED: " + result["output"][:500])
        return result["output"].rstrip("\r\n")

    def patch_test(self, job):
        payload = job["payload"]
        profile = self.policy["repos"][payload["repo_profile"]]
        repo = Path(profile["root"]).resolve()
        if self.git(job, repo, "rev-parse", "HEAD") != profile["base_sha"]:
            raise ValueError("REPOSITORY_BASE_CHANGED")
        if self.git(job, repo, "status", "--porcelain"):
            raise ValueError("CLEAN_OPERATOR_CHECKOUT_REQUIRED")
        patch = profile["patches"][payload["patch_ids"][job["attempt"] - 1]]
        patch_path = Path(patch["file"])
        if patch_path.is_symlink() or not patch_path.is_file() or patch_path.stat().st_size > 1_000_000:
            raise ValueError("BOUNDED_PATCH_REQUIRED")
        raw = patch_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != patch["sha256"]:
            raise ValueError("PATCH_HASH_CHANGED")
        patch_text = raw.decode("utf-8")
        if any(term in patch_text for term in ("GIT binary patch", "new file mode 120000", "new file mode 160000", "old mode", "new mode", "rename from", "rename to")):
            raise ValueError("UNSUPPORTED_PATCH_KIND")
        worktrees = self.store.resolve() / "worktrees"
        worktrees.mkdir(exist_ok=True)
        worktree = worktrees / (job["id"] + "-" + str(job["attempt"]))
        self.git(job, repo, "worktree", "add", "--detach", str(worktree), profile["base_sha"])
        # Apply the verified bytes, not a mutable policy path.
        with tempfile.NamedTemporaryFile(dir=worktrees, delete=False) as handle:
            frozen_patch = Path(handle.name)
            handle.write(raw)
        try:
            self.git(job, worktree, "apply", "--index", "--check", str(frozen_patch))
            self.git(job, worktree, "apply", "--index", str(frozen_patch))
        finally:
            frozen_patch.unlink(missing_ok=True)
        changes = self.git(job, worktree, "status", "--porcelain", "-z", "--untracked-files=all")
        if not changes:
            raise ValueError("EMPTY_PATCH")
        allowed = profile.get("allowed_paths", [])
        for record in changes.split("\0"):
            if not record:
                continue
            name = record[3:]
            if not any(name == prefix or name.startswith(prefix.rstrip("/") + "/") for prefix in allowed):
                raise ValueError("PATCH_OUTSIDE_REGISTERED_PATHS")
        self.git(job, worktree, "add", "--all")
        self.git(job, worktree, "commit", "-m", "OCC local task " + job["id"] + " attempt " + str(job["attempt"]))
        head = self.git(job, worktree, "rev-parse", "HEAD")
        checkpoint = {"worktree": str(worktree), "head_sha": head,
                      "patch_sha256": patch["sha256"], "base_sha": profile["base_sha"]}
        self.transition(job, "RUNNING", checkpoint=checkpoint)
        results = []
        for argv in profile["tests"]:
            result = self.command(job, argv, worktree, profile.get("timeout_seconds", 60))
            results.append(result)
            if result["reason"] or result["exit_code"]:
                state = "RETRY_READY" if job["attempt"] < job["max_attempts"] else "FAILED"
                self.transition(job, state, checkpoint=checkpoint, result={"reason": "TEST_FAILED", "tests": results}, delay=profile.get("retry_delay_seconds", 1))
                return
        if self.git(job, worktree, "status", "--porcelain"):
            raise ValueError("TEST_MUTATED_WORKTREE")
        checkpoint["tests"] = results
        self.transition(job, "WAITING_CI", checkpoint=checkpoint,
                        result={"local_tests": "PASSED", "publication": "NOT_PERFORMED", "ci": "NOT_OBSERVED"})

    def poll_ci(self):
        db = connection(self.store)
        try:
            rows = db.execute("SELECT * FROM jobs WHERE state='WAITING_CI'").fetchall()
        finally:
            db.close()
        observed = []
        for raw_row in rows:
            job = self.get(raw_row["id"])
            if job["policy_hash"] != digest(self.policy):
                continue
            profile = self.policy["repos"][job["payload"]["repo_profile"]]
            ci = profile["ci"]
            try:
                snapshot = load_json(Path(ci["snapshot_file"]))
                if snapshot.get("schema") != "occ.ci-snapshot.v1" or snapshot.get("head_sha") != job["checkpoint"]["head_sha"]:
                    continue
                origin = snapshot.get("origin")
                if origin == "operator_github_actions_export":
                    evidence_origin = "operator_snapshot_not_independently_authenticated"
                elif origin == "authenticated_github_check_runs_v1":
                    transport = ci.get("transport")
                    if (not isinstance(transport, dict)
                            or snapshot.get("repository") != transport.get("repository")
                            or snapshot.get("required_checks") != ci["required_checks"]
                            or snapshot.get("transport_status") != "OBSERVED"):
                        continue
                    evidence_origin = "authenticated_github_check_runs_v1"
                else:
                    continue
                checks = snapshot.get("checks")
                if not isinstance(checks, list):
                    continue
                latest = {}
                ambiguous = False
                for check in checks:
                    if not isinstance(check, dict) or check.get("head_sha") != snapshot["head_sha"] or type(check.get("run_id")) is not int:
                        continue
                    name = check.get("name")
                    if name in latest and check["run_id"] == latest[name]["run_id"] and check != latest[name]:
                        ambiguous = True
                    if isinstance(name, str) and (name not in latest or check["run_id"] > latest[name]["run_id"]):
                        latest[name] = check
                selected = [latest.get(name) for name in ci["required_checks"]]
                if ambiguous or any(not check or check.get("status") != "completed" for check in selected):
                    continue
                if all(check.get("conclusion") == "success" for check in selected):
                    state = "SUCCEEDED"
                else:
                    state = "RETRY_READY" if job["attempt"] < job["max_attempts"] else "FAILED"
                # CAS prevents cancellation / another observation being overwritten.
                db = connection(self.store)
                try:
                    with db:
                        result = {"local_tests": "PASSED", "ci": state,
                                  "ci_snapshot_sha256": digest(snapshot),
                                  "evidence_origin": evidence_origin,
                                  "model_calls": 0, "transactions_sent": 0}
                        changed = db.execute("UPDATE jobs SET state=?,result=?,available=?,updated=? WHERE id=? AND state='WAITING_CI' AND cancel_requested=0",
                                             (state, encoded(result), time.time() + profile.get("retry_delay_seconds", 1), time.time(), job["id"])).rowcount
                        if changed:
                            event(db, job["id"], state, result)
                            observed.append({"id": job["id"], "state": state})
                finally:
                    db.close()
            except (OSError, ValueError, KeyError, TypeError):
                # Absent/malformed CI never creates success or blind retry.
                continue
        return observed

    def run_once(self):
        observed = self.poll_ci()
        job = self.claim()
        if not job:
            return {"state": "IDLE", "ci_observations": observed}
        try:
            if job["payload"]["kind"] == "sync":
                profile = self.policy["sources"][job["payload"]["source_profile"]]
                self.heartbeat(job)
                result = sync(self.store, profile["namespace"], Path(profile["root"]),
                              max_files=profile.get("max_files", 100), max_bytes=profile.get("max_bytes", 25_000_000),
                              progress=lambda: self.heartbeat(job))
                self.transition(job, "SUCCEEDED", result=result)
            elif job['payload']['kind'] == 'review_report':
                from review_report import write_report
                result = write_report(self.store, self.policy['reports'][job['payload']['report_profile']],
                                      progress=lambda: self.heartbeat(job))
                self.transition(job, 'SUCCEEDED', result=result)
            else:
                self.patch_test(job)
        except Cancelled:
            if self.get(job["id"])["lease_token"] == job["lease_token"]:
                self.transition(job, "CANCELLED", result={"reason": "CANCEL_REQUESTED"})
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as exc:
            if self.get(job["id"])["lease_token"] == job["lease_token"]:
                self.transition(job, "BLOCKED", result={"reason": str(exc)[:1000], "error_type": type(exc).__name__})
        return self.get(job["id"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("sync")
    scan.add_argument("--namespace", required=True)
    scan.add_argument("--root", required=True, type=Path)
    lookup = commands.add_parser("search")
    lookup.add_argument("--namespace", required=True)
    lookup.add_argument("--query", required=True)
    pack = commands.add_parser("context")
    pack.add_argument("--namespace", required=True)
    pack.add_argument("--id", action="append", required=True)
    for name in ("enqueue", "work", "get", "cancel", "abandon-orphan", "reconcile-report"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--policy", required=True, type=Path)
        if name in {"get", "cancel", "abandon-orphan", "reconcile-report"}:
            cmd.add_argument("--id", required=True)
        if name in {"abandon-orphan", "reconcile-report"}:
            cmd.add_argument("--process-stopped", required=True, action="store_true")
        if name == "enqueue":
            cmd.add_argument("--task-key", required=True)
            cmd.add_argument("--job", required=True, type=Path)
    commands.add_parser("jobs")
    args = parser.parse_args(argv)
    try:
        if args.command == "sync":
            result = sync(args.store, args.namespace, args.root)
        elif args.command == "search":
            result = search(args.store, args.namespace, args.query)
        elif args.command == "context":
            result = context_pack(args.store, args.namespace, args.id)
        elif args.command == "jobs":
            db = connection(args.store)
            try:
                result = [dict(row) for row in db.execute("SELECT id,task_key,state,attempt,max_attempts,updated FROM jobs ORDER BY created")]
            finally:
                db.close()
        else:
            policy = validate_policy(load_json(args.policy))
            core = Core(args.store, policy)
            if args.command == "enqueue":
                result = enqueue(args.store, policy, args.task_key, load_json(args.job))
            elif args.command == "work":
                result = core.run_once()
            elif args.command == "get":
                result = core.get(args.id)
            elif args.command == "abandon-orphan":
                result = core.abandon_orphan(args.id, args.process_stopped)
            elif args.command == 'reconcile-report':
                result = core.reconcile_report(args.id, args.process_stopped)
            else:
                result = core.cancel(args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(encoded({"state": "BLOCKED", "reason": str(exc)[:1000], "error_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
