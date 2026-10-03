"""RND-PR-03 portable-library lineage adapter.

This module deliberately reuses Content Lab's ``content.sqlite3`` and FTS
projection.  Portable records are untrusted DATA_ONLY evidence: importing or
searching them never invokes a command, browser, model, or external service.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import time
from typing import Any, Iterable

from content_lab import MAX_TEXT_BYTES, NAMESPACE, _database, _insert_item


SCHEMA = "occ.rnd-pr03.lineage.v1"
STAGE_SCHEMA = "occ.pc-library-record.v1"
BACKUP_SCHEMA = "occ.rnd-pr03.backup.v1"
MAX_STAGE_RECORDS = 100_000
MAX_BACKUP_BYTES = 64 * 1024 * 1024
HEX = set("0123456789abcdef")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - HEX:
        raise ValueError(f"ARCHIVE_{label}_SHA256_REQUIRED")
    return value


def _name(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"ARCHIVE_{label}_REQUIRED")
    return value


def _relative(value: Any, label: str) -> str:
    text = _name(value, label)
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or text == ".":
        raise ValueError(f"ARCHIVE_{label}_BOUNDARY")
    return text


def _ensure_tables(connection: sqlite3.Connection) -> None:
    """Install lineage metadata beside the pre-existing item/FTS owner."""
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS archive_captures(
          capture_id TEXT PRIMARY KEY, namespace TEXT NOT NULL,
          source_profile TEXT NOT NULL, source_hash TEXT NOT NULL,
          coverage TEXT NOT NULL, observed REAL NOT NULL, record_count INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS archive_items(
          logical_item_id TEXT PRIMARY KEY, namespace TEXT NOT NULL,
          source_profile TEXT NOT NULL, source_path TEXT NOT NULL,
          member_path TEXT NOT NULL, first_seen REAL NOT NULL,
          UNIQUE(namespace, source_profile, source_path, member_path));
        CREATE TABLE IF NOT EXISTS archive_versions(
          version_id TEXT PRIMARY KEY, logical_item_id TEXT NOT NULL,
          previous_version_id TEXT, item_id TEXT NOT NULL, text_sha256 TEXT NOT NULL,
          source_file_sha256 TEXT NOT NULL, member_path TEXT NOT NULL,
          extractor TEXT NOT NULL, capture_completeness TEXT NOT NULL,
          tags TEXT NOT NULL, observed REAL NOT NULL,
          FOREIGN KEY(logical_item_id) REFERENCES archive_items(logical_item_id));
        CREATE TABLE IF NOT EXISTS archive_heads(
          logical_item_id TEXT PRIMARY KEY, version_id TEXT, tombstone INTEGER NOT NULL,
          removal_evidence_sha256 TEXT, coverage TEXT NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS archive_import_receipts(
          import_key TEXT PRIMARY KEY, capture_id TEXT NOT NULL, state TEXT NOT NULL,
          committed_at REAL NOT NULL, summary TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS archive_repo_evidence(
          snapshot_id TEXT PRIMARY KEY, repository TEXT NOT NULL, repo_sha TEXT NOT NULL,
          kind TEXT NOT NULL, payload TEXT NOT NULL, observed REAL NOT NULL);
    """)


def _load_stage(stage: Path) -> list[dict[str, Any]]:
    index = stage / "INDEX.jsonl"
    if stage.is_symlink() or not stage.is_dir() or not index.is_file() or index.is_symlink():
        raise ValueError("ARCHIVE_STAGE_INDEX_REQUIRED")
    raw = index.read_bytes()
    if len(raw) > MAX_BACKUP_BYTES:
        raise ValueError("ARCHIVE_STAGE_INDEX_LIMIT")
    records = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("ARCHIVE_STAGE_JSON") from exc
        records.append(_validate_stage_record(stage, record))
        if len(records) > MAX_STAGE_RECORDS:
            raise ValueError("ARCHIVE_STAGE_RECORD_LIMIT")
    if not records:
        raise ValueError("ARCHIVE_STAGE_EMPTY")
    return records


def _validate_stage_record(stage: Path, record: Any) -> dict[str, Any]:
    required = {"schema", "id", "source_path", "source_file_sha256", "member_path",
                "text_sha256", "bytes_utf8", "capture_completeness", "extractor",
                "tags", "labels", "authority", "ingested_at"}
    if not isinstance(record, dict) or set(record) != required or record.get("schema") != STAGE_SCHEMA:
        raise ValueError("ARCHIVE_STAGE_SCHEMA")
    text_hash = _hex(record["text_sha256"], "TEXT")
    if record["id"] != text_hash:
        raise ValueError("ARCHIVE_STAGE_ID_IS_NOT_TEXT_HASH")
    source_hash = _hex(record["source_file_sha256"], "SOURCE")
    source_path = _name(record["source_path"], "SOURCE_PATH", 4096)
    member = _relative(record["member_path"], "MEMBER_PATH")
    if record["authority"] != "DATA_ONLY":
        raise ValueError("ARCHIVE_STAGE_AUTHORITY")
    if record["capture_completeness"] not in {"SOURCE_COMPLETE", "PARTIAL_CAPTURE"}:
        raise ValueError("ARCHIVE_STAGE_COVERAGE")
    if type(record["bytes_utf8"]) is not int or not 1 <= record["bytes_utf8"] <= MAX_TEXT_BYTES:
        raise ValueError("ARCHIVE_STAGE_TEXT_LIMIT")
    if not isinstance(record["tags"], list) or not isinstance(record["labels"], list):
        raise ValueError("ARCHIVE_STAGE_TAGS")
    text_path = stage / "texts" / f"{text_hash}.txt"
    if text_path.is_symlink() or not text_path.is_file() or not text_path.resolve().is_relative_to(stage.resolve()):
        raise ValueError("ARCHIVE_STAGE_TEXT_REQUIRED")
    text = text_path.read_bytes()
    if len(text) != record["bytes_utf8"] or hashlib.sha256(text).hexdigest() != text_hash:
        raise ValueError("ARCHIVE_STAGE_TEXT_HASH")
    try:
        decoded = text.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("ARCHIVE_STAGE_UTF8") from exc
    if not decoded.strip():
        raise ValueError("ARCHIVE_STAGE_EMPTY_TEXT")
    return {**record, "source_path": source_path, "member_path": member, "text": decoded,
            "source_file_sha256": source_hash, "text_sha256": text_hash}


def _logical_id(namespace: str, profile: str, source_path: str, member: str) -> str:
    return _digest({"namespace": namespace, "source_profile": profile,
                    "source_path": source_path, "member_path": member})


def _capture_id(namespace: str, profile: str, records: Iterable[dict[str, Any]], coverage: str) -> str:
    fingerprints = sorted((record["source_file_sha256"], record["member_path"],
                           record["text_sha256"]) for record in records)
    return _digest({"namespace": namespace, "source_profile": profile,
                    "coverage": coverage, "records": fingerprints})


def import_portable_stage(store: Path, stage: Path, namespace: str, source_profile: str,
                          *, coverage: str = "PARTIAL", removals: list[dict[str, str]] | None = None,
                          interrupt_after: int | None = None) -> dict[str, Any]:
    """Atomically import a staging directory, retaining every prior version.

    ``coverage`` intentionally never turns absence into a tombstone.  Deletion
    requires a caller-supplied SHA-256 removal evidence record for one logical
    item.  ``interrupt_after`` is test-only fault injection; rollback makes the
    same import safely resumable.
    """
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise ValueError("ARCHIVE_NAMESPACE_REQUIRED")
    source_profile = _name(source_profile, "SOURCE_PROFILE", 100)
    if coverage not in {"PARTIAL", "VERIFIED_RANGE", "SOURCE_COMPLETE", "UNKNOWN"}:
        raise ValueError("ARCHIVE_COVERAGE")
    if interrupt_after is not None and (type(interrupt_after) is not int or interrupt_after < 1):
        raise ValueError("ARCHIVE_INTERRUPT_LIMIT")
    records = _load_stage(stage)
    capture_id = _capture_id(namespace, source_profile, records, coverage)
    import_key = _digest({"capture_id": capture_id, "removals": removals or []})
    observed = time.time()
    connection = _database(store)
    inserted = unchanged = tombstones = 0
    try:
        _ensure_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        prior = connection.execute("SELECT summary FROM archive_import_receipts WHERE import_key=?", (import_key,)).fetchone()
        if prior is not None:
            connection.commit()
            return {**json.loads(prior[0]), "state": "UNCHANGED"}
        connection.execute("INSERT OR IGNORE INTO archive_captures VALUES (?,?,?,?,?,?,?)",
                           (capture_id, namespace, source_profile, _digest(records), coverage, observed, len(records)))
        for index, record in enumerate(records, 1):
            logical_id = _logical_id(namespace, source_profile, record["source_path"], record["member_path"])
            connection.execute("INSERT OR IGNORE INTO archive_items VALUES (?,?,?,?,?,?)",
                               (logical_id, namespace, source_profile, record["source_path"], record["member_path"], observed))
            head = connection.execute("SELECT version_id FROM archive_heads WHERE logical_item_id=?", (logical_id,)).fetchone()
            version_id = _digest({"logical_item_id": logical_id, "text_sha256": record["text_sha256"],
                                  "extractor": record["extractor"]})
            if head is not None and head[0] == version_id:
                unchanged += 1
            else:
                item = {"schema": SCHEMA, "id": version_id, "namespace": namespace,
                        "source_key": record["member_path"], "text": record["text"],
                        "input_sha256": record["source_file_sha256"], "text_sha256": record["text_sha256"],
                        "authority": "source-content-not-action-instructions", "capture_completeness": record["capture_completeness"],
                        "source_locator": record["member_path"], "tags": record["tags"], "extractor": record["extractor"]}
                _insert_item(connection, item)
                connection.execute("INSERT OR IGNORE INTO archive_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                   (version_id, logical_id, None if head is None else head[0], version_id,
                                    record["text_sha256"], record["source_file_sha256"], record["member_path"],
                                    record["extractor"], record["capture_completeness"], _json(record["tags"]), observed))
                connection.execute("INSERT INTO archive_heads VALUES (?,?,?,?,?,?) ON CONFLICT(logical_item_id) DO UPDATE SET version_id=excluded.version_id,tombstone=0,removal_evidence_sha256=NULL,coverage=excluded.coverage,updated=excluded.updated",
                                   (logical_id, version_id, 0, None, coverage, observed))
                inserted += 1
            if interrupt_after is not None and index == interrupt_after:
                raise RuntimeError("ARCHIVE_TEST_INTERRUPT")
        for removal in removals or []:
            if not isinstance(removal, dict) or set(removal) != {"source_path", "member_path", "evidence_sha256"}:
                raise ValueError("ARCHIVE_REMOVAL_SCHEMA")
            logical_id = _logical_id(namespace, source_profile, _name(removal["source_path"], "SOURCE_PATH", 4096),
                                     _relative(removal["member_path"], "MEMBER_PATH"))
            if connection.execute("SELECT 1 FROM archive_items WHERE logical_item_id=?", (logical_id,)).fetchone() is None:
                raise ValueError("ARCHIVE_REMOVAL_UNKNOWN_ITEM")
            evidence = _hex(removal["evidence_sha256"], "REMOVAL_EVIDENCE")
            current = connection.execute("SELECT version_id,tombstone FROM archive_heads WHERE logical_item_id=?", (logical_id,)).fetchone()
            if not current[1]:
                connection.execute("UPDATE archive_heads SET tombstone=1,removal_evidence_sha256=?,coverage=?,updated=? WHERE logical_item_id=?",
                                   (evidence, coverage, observed, logical_id))
                tombstones += 1
        summary = {"schema": SCHEMA, "state": "IMPORTED", "capture_id": capture_id,
                   "namespace": namespace, "source_profile": source_profile, "coverage": coverage,
                   "records": len(records), "new_versions": inserted, "unchanged": unchanged,
                   "tombstones": tombstones, "model_calls": 0, "network_fetches": 0}
        connection.execute("INSERT INTO archive_import_receipts VALUES (?,?,?,?,?)",
                           (import_key, capture_id, "COMMITTED", observed, _json(summary)))
        connection.commit()
        return summary
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def search_lineage(store: Path, namespace: str, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise ValueError("ARCHIVE_NAMESPACE_REQUIRED")
    if not isinstance(query, str) or not query.strip() or len(query) > 1000 or not 1 <= limit <= 50:
        raise ValueError("ARCHIVE_SEARCH_SCHEMA")
    connection = _database(store)
    try:
        _ensure_tables(connection)
        rows = connection.execute("""
          SELECT h.logical_item_id,h.version_id,v.text_sha256,v.source_file_sha256,v.member_path,
                 v.capture_completeness,h.coverage,snippet(content_fts,1,'[',']','…',24)
          FROM archive_heads h JOIN archive_versions v ON v.version_id=h.version_id
          JOIN content_fts ON content_fts.id=v.item_id
          JOIN archive_items i ON i.logical_item_id=h.logical_item_id
          WHERE i.namespace=? AND h.tombstone=0 AND content_fts MATCH ? ORDER BY rank LIMIT ?
        """, (namespace, query, limit)).fetchall()
        return [{"logical_item_id": row[0], "version_id": row[1], "text_sha256": row[2],
                 "source_file_sha256": row[3], "source_locator": row[4],
                 "capture_completeness": row[5], "coverage": row[6], "snippet": row[7],
                 "authority": "source-content-not-action-instructions"} for row in rows]
    finally:
        connection.close()


def import_repo_evidence(store: Path, repository: str, repo_sha: str, kind: str, payload: dict[str, Any]) -> dict[str, str]:
    """Store a pinned derived repo observation; it never grants execution authority."""
    repository = _name(repository, "REPOSITORY", 200)
    repo_sha = _hex(repo_sha, "REPOSITORY") if len(repo_sha) == 64 else _name(repo_sha, "REPOSITORY_SHA", 64)
    if kind not in {"FUNCTION_CATALOG", "STATIC_FINDINGS", "CONTEXT_CHUNK"} or not isinstance(payload, dict):
        raise ValueError("ARCHIVE_REPO_EVIDENCE_SCHEMA")
    snapshot_id = _digest({"repository": repository, "repo_sha": repo_sha, "kind": kind, "payload": payload})
    connection = _database(store)
    try:
        _ensure_tables(connection)
        with connection:
            connection.execute("INSERT OR IGNORE INTO archive_repo_evidence VALUES (?,?,?,?,?,?)",
                               (snapshot_id, repository, repo_sha, kind, _json({**payload, "authority": "SOURCE_ONLY" if kind != "STATIC_FINDINGS" else "STATIC_CANDIDATE"}), time.time()))
    finally:
        connection.close()
    return {"snapshot_id": snapshot_id, "authority": "SOURCE_ONLY" if kind != "STATIC_FINDINGS" else "STATIC_CANDIDATE"}


def backup_lineage(store: Path) -> dict[str, Any]:
    connection = _database(store)
    try:
        _ensure_tables(connection)
        connection.row_factory = sqlite3.Row
        tables = ("archive_captures", "archive_items", "archive_versions", "archive_heads", "archive_import_receipts", "archive_repo_evidence")
        data = {table: [dict(row) for row in connection.execute(f"SELECT * FROM {table}").fetchall()] for table in tables}
        ids = sorted({row["item_id"] for row in data["archive_versions"]})
        payloads = {item_id: connection.execute("SELECT payload FROM items WHERE id=?", (item_id,)).fetchone()[0] for item_id in ids}
        body = {"schema": BACKUP_SCHEMA, "tables": data, "items": payloads}
        return {**body, "sha256": _digest(body)}
    finally:
        connection.close()


def restore_lineage(store: Path, backup: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(backup, dict) or backup.get("schema") != BACKUP_SCHEMA or not isinstance(backup.get("tables"), dict) or not isinstance(backup.get("items"), dict):
        raise ValueError("ARCHIVE_BACKUP_SCHEMA")
    claimed = backup.get("sha256")
    body = {"schema": backup["schema"], "tables": backup["tables"], "items": backup["items"]}
    if claimed != _digest(body) or len(_json(backup).encode("utf-8")) > MAX_BACKUP_BYTES:
        raise ValueError("ARCHIVE_BACKUP_INTEGRITY")
    tables = ("archive_captures", "archive_items", "archive_versions", "archive_heads", "archive_import_receipts", "archive_repo_evidence")
    if set(backup["tables"]) != set(tables):
        raise ValueError("ARCHIVE_BACKUP_TABLES")
    connection = _database(store)
    try:
        _ensure_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        for table in tables:
            connection.execute(f"DELETE FROM {table}")
        for item_id, raw in backup["items"].items():
            item = json.loads(raw)
            if item.get("id") != item_id or item.get("authority") != "source-content-not-action-instructions":
                raise ValueError("ARCHIVE_BACKUP_ITEM")
            _insert_item(connection, item)
        for table in tables:
            rows = backup["tables"][table]
            if not isinstance(rows, list):
                raise ValueError("ARCHIVE_BACKUP_TABLE")
            if rows:
                columns = list(rows[0])
                if any(not isinstance(row, dict) or list(row) != columns for row in rows):
                    raise ValueError("ARCHIVE_BACKUP_ROW")
                connection.executemany(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                                       [[row[column] for column in columns] for row in rows])
        connection.commit()
        return {"state": "RESTORED", "sha256": claimed,
                "versions": len(backup["tables"]["archive_versions"]),
                "heads": len(backup["tables"]["archive_heads"])}
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
