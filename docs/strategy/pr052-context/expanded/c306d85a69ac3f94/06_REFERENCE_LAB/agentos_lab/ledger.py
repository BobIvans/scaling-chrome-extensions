"""One SQLite commit for a verified local candidate; no external side effects.

The idempotency guarantee covers this database transaction ONLY. It does not
cover GitHub, shell processes, files, browser sessions or blockchain submission.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

class Conflict(RuntimeError):
    """Same operation ID was reused for a different intent."""

class StaleVersion(Conflict):
    """Target changed since the candidate was prepared."""

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

class CommitLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS targets (
                    name TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    receipt TEXT NOT NULL
                );
            """)

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        try:
            with con:
                yield con
        finally:
            con.close()

    def seed(self, target: str, payload: dict) -> None:
        if not target:
            raise ValueError("target is required")
        with self._connect() as con:
            con.execute("INSERT OR IGNORE INTO targets VALUES (?, 0, ?)",
                        (target, canonical(payload)))

    def read(self, target: str) -> tuple[int, dict]:
        with self._connect() as con:
            row = con.execute("SELECT revision, payload FROM targets WHERE name=?",
                              (target,)).fetchone()
        if row is None:
            raise KeyError(target)
        return row[0], json.loads(row[1])

    def commit(self, operation_id: str, target: str, expected_revision: int,
               payload: dict, *, verified: bool) -> dict:
        # 'verified' must come from trusted coordinator, not model output.
        # This flag is not a cryptographic proof or an isolation mechanism.
        if not verified:
            raise PermissionError("independent verifier has not accepted candidate")
        if not operation_id or not target or expected_revision < 0:
            raise ValueError("operation_id, target and nonnegative revision required")
        fingerprint = digest({"target": target, "revision": expected_revision,
                              "payload": payload})
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            prior = con.execute("SELECT fingerprint, receipt FROM operations WHERE operation_id=?",
                                (operation_id,)).fetchone()
            if prior:
                if prior[0] != fingerprint:
                    raise Conflict("idempotency key reused for different content or snapshot")
                return json.loads(prior[1])
            row = con.execute("SELECT revision FROM targets WHERE name=?", (target,)).fetchone()
            if row is None:
                raise KeyError(target)
            if row[0] != expected_revision:
                raise StaleVersion(f"expected {expected_revision}, observed {row[0]}")
            revision = expected_revision + 1
            receipt = {"operation_id": operation_id, "target": target,
                       "revision": revision, "payload_sha256": digest(payload),
                       "status": "LOCAL_SQLITE_COMMITTED", "external_actions": 0}
            con.execute("UPDATE targets SET revision=?, payload=? WHERE name=?",
                        (revision, canonical(payload), target))
            con.execute("INSERT INTO operations VALUES (?, ?, ?)",
                        (operation_id, fingerprint, canonical(receipt)))
        return receipt

    def operation_count(self) -> int:
        with self._connect() as con:
            return con.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
