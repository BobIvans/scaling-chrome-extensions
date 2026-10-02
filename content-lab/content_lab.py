"""Local content and optional CPU ASR experiments; never an action executor."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import tempfile
from typing import Any

SCHEMA = "occ.content-lab.item.v1"
MAX_TEXT_BYTES = 2_200_000
MAX_AUDIO_BYTES = 64 * 1024 * 1024
MAX_CHATGPT_EXPORT_BYTES = 64 * 1024 * 1024
MAX_CHATGPT_CONVERSATIONS = 1000
MAX_CHATGPT_MESSAGES = 100_000
MAX_CHATGPT_TEXT_BYTES = 64 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".yaml", ".yml"}
MODEL_FILES = ("model.bin", "config.json", "tokenizer.json", "preprocessor_config.json")
SOURCE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
NAMESPACE = re.compile(r"^[A-Za-z0-9_.:-]{1,90}$")
LIBRARY_STATUS = {"ORIGINAL", "EXTRACTED", "EMPTY", "UNSUPPORTED", "SELECTION",
                  "RAW_TEXT", "PARTIAL", "BEST_EFFORT"}


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_text(path: Path) -> tuple[str, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular input file required")
    with path.open("rb") as handle:
        raw = handle.read(MAX_TEXT_BYTES + 1)
    if len(raw) > MAX_TEXT_BYTES:
        raise ValueError("input exceeds text budget; no silent truncation")
    text = raw.decode("utf-8-sig")
    if "\0" in text:
        raise ValueError("binary or UTF-16 input unsupported")
    return text, hashlib.sha256(raw).hexdigest()


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key in ChatGPT export")
        value[key] = item
    return value


def _reject_json_constant(value):
    raise ValueError("non-finite JSON number in ChatGPT export")


def _read_chatgpt_export(path: Path) -> tuple[list, str, int]:
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".json":
        raise ValueError("regular local ChatGPT JSON export required")
    before = path.stat()
    with path.open("rb") as handle:
        raw = handle.read(MAX_CHATGPT_EXPORT_BYTES + 1)
    after = path.stat()
    if path.is_symlink() or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("ChatGPT export changed during read")
    if len(raw) > MAX_CHATGPT_EXPORT_BYTES:
        raise ValueError("ChatGPT export exceeds byte budget")
    try:
        source = raw.decode("utf-8-sig")
        value = json.loads(source, object_pairs_hook=_unique_object,
                           parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 ChatGPT JSON export") from exc
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CHATGPT_CONVERSATIONS:
        raise ValueError("bounded ChatGPT conversation array required")
    return value, hashlib.sha256(raw).hexdigest(), len(raw)


def _source_id(value, label):
    if not isinstance(value, str) or not SOURCE_ID.fullmatch(value):
        raise ValueError(f"stable ChatGPT {label} required")
    return value


def _source_time(value):
    if value is None:
        return None
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 <= value <= 253402300799):
        raise ValueError("finite ChatGPT source timestamp required")
    return float(value)


def _message_text(content):
    if not isinstance(content, dict):
        return None, 0, None
    kind = content.get("content_type")
    if kind is not None and (not isinstance(kind, str) or len(kind) > 100):
        raise ValueError("bounded ChatGPT content type required")
    parts = content.get("parts")
    accepted, skipped = [], 0
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, str):
                if part.strip():
                    accepted.append(part)
            else:
                skipped += 1
    elif isinstance(content.get("text"), str) and content["text"].strip():
        accepted.append(content["text"])
    else:
        return None, 1, kind
    text = "\n".join(accepted)
    return (text if text.strip() else None), (skipped if text.strip() else max(1, skipped)), kind


def parse_chatgpt_export(path: Path, namespace: str) -> dict:
    """Parse selected conversations into immutable message revisions.

    Only synthetic schema facts become code assumptions. User content remains
    local data and never grants action authority.
    """
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise ValueError("bounded ChatGPT namespace required")
    conversations, export_sha256, input_bytes = _read_chatgpt_export(path)
    scope = "chatgpt:" + namespace
    items, records, skipped_non_text, extracted_bytes = [], [], 0, 0
    seen_conversations, seen_messages = set(), set()
    for conversation in conversations:
        if not isinstance(conversation, dict):
            raise ValueError("ChatGPT conversation object required")
        conversation_id = _source_id(conversation.get("id"), "conversation id")
        if conversation_id in seen_conversations:
            raise ValueError("duplicate ChatGPT conversation id")
        seen_conversations.add(conversation_id)
        title = conversation.get("title")
        if title is not None and (not isinstance(title, str) or len(title) > 1000):
            raise ValueError("bounded ChatGPT conversation title required")
        mapping = conversation.get("mapping")
        if not isinstance(mapping, dict) or len(mapping) > MAX_CHATGPT_MESSAGES:
            raise ValueError("bounded ChatGPT mapping required")
        records.append({
            "conversation_id": conversation_id,
            "title": title,
            "create_time": _source_time(conversation.get("create_time")),
            "update_time": _source_time(conversation.get("update_time")),
            "current_node": (None if conversation.get("current_node") is None else
                             _source_id(conversation.get("current_node"), "current node")),
        })
        for node_id, node in mapping.items():
            node_id = _source_id(node_id, "node id")
            if not isinstance(node, dict):
                raise ValueError("ChatGPT mapping node object required")
            message = node.get("message")
            if message is None:
                continue
            if not isinstance(message, dict):
                raise ValueError("ChatGPT message object required")
            message_id = _source_id(message.get("id"), "message id")
            message_key = (conversation_id, message_id)
            if message_key in seen_messages:
                raise ValueError("duplicate ChatGPT message id in conversation")
            seen_messages.add(message_key)
            parent = node.get("parent")
            if parent is not None:
                parent = _source_id(parent, "parent node id")
            author = message.get("author")
            role = author.get("role") if isinstance(author, dict) else None
            if not isinstance(role, str) or not SOURCE_ID.fullmatch(role):
                raise ValueError("stable ChatGPT author role required")
            text, skipped, content_type = _message_text(message.get("content"))
            skipped_non_text += skipped
            if text is None:
                continue
            extracted_bytes += len(text.encode("utf-8"))
            if extracted_bytes > MAX_CHATGPT_TEXT_BYTES or len(text.encode("utf-8")) > MAX_TEXT_BYTES:
                raise ValueError("ChatGPT extracted text exceeds byte budget")
            source_key = f"chatgpt/{conversation_id}/{message_id}"
            revision_source = {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "node_id": node_id,
                "parent_node_id": parent,
                "role": role,
                "content_type": content_type,
                "text": text,
            }
            revision_sha256 = hashlib.sha256(
                json.dumps(revision_source, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
            ).hexdigest()
            item_id = hashlib.sha256(
                json.dumps({"namespace": scope, "source_key": source_key,
                            "revision_sha256": revision_sha256,
                            "extractor": "chatgpt-export.v1"},
                           sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            created = _source_time(message.get("create_time"))
            items.append({
                "schema_version": SCHEMA,
                "id": item_id,
                "input_file": path.name,
                "source_url": None,
                "input_sha256": revision_sha256,
                "export_sha256": export_sha256,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "kind": "chatgpt_message",
                "extractor": "chatgpt-export.v1",
                "text": text,
                "authority": "source-content-not-action-instructions",
                "completeness": "SELECTED_LOCAL_EXPORT_TEXT_ONLY",
                "asr_inference_performed": False,
                "network_fetch_performed": False,
                "namespace": scope,
                "source_key": source_key,
                "conversation_id": conversation_id,
                "conversation_title": title,
                "message_id": message_id,
                "node_id": node_id,
                "parent_node_id": parent,
                "author_role": role,
                "content_type": content_type,
                "source_created_at": created,
                "revision_sha256": revision_sha256,
                "created_at": (datetime.fromtimestamp(created, timezone.utc).isoformat()
                               if created is not None else None),
            })
            if len(items) > MAX_CHATGPT_MESSAGES:
                raise ValueError("ChatGPT message count exceeds budget")
    items.sort(key=lambda item: (item["conversation_id"], item["message_id"], item["id"]))
    records.sort(key=lambda item: item["conversation_id"])
    return {"namespace": scope, "export_sha256": export_sha256,
            "input_bytes": input_bytes, "conversations": records, "items": items,
            "skipped_non_text": skipped_non_text, "extracted_bytes": extracted_bytes}


class _HtmlText(HTMLParser):
    SKIP = {"head", "script", "style", "noscript", "template", "nav"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.hidden.append(tag)
        if not self.hidden and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.hidden:
            index = len(self.hidden) - 1 - self.hidden[::-1].index(tag)
            del self.hidden[index:]
        if not self.hidden and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_text(source: str) -> str:
    parser = _HtmlText()
    parser.feed(source)
    parser.close()
    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in "".join(parser.parts).splitlines()
    ]
    return "\n".join(line for line in lines if line)


def _seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) not in (2, 3):
        raise ValueError("invalid subtitle timestamp")
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def subtitle_segments(source: str) -> list[dict[str, Any]]:
    segments = []
    for block in re.split(r"\n\s*\n", source.replace("\r\n", "\n").strip()):
        lines = block.splitlines()
        if not lines or re.match(r"^(WEBVTT|NOTE|STYLE|REGION)(\s|$)", lines[0]):
            continue
        for index, line in enumerate(lines):
            match = re.match(r"^([0-9:. ,]+?)\s+-->\s+([0-9:.,]+)(?:\s.*)?$", line)
            if match:
                start, end = _seconds(match[1].strip()), _seconds(match[2])
                if not 0 <= start <= end:
                    raise ValueError("invalid subtitle interval")
                text = unescape(
                    re.sub(r"<[^>]+>", "", "\n".join(lines[index + 1 :]))
                ).strip()
                if text:
                    segments.append({"start": start, "end": end, "text": text})
                break
    if not segments:
        raise ValueError("no supported subtitle cues found")
    return segments


def _item(
    *,
    path: Path,
    input_sha256: str,
    text: str,
    kind: str,
    source_url: str | None,
    extractor: str,
    extra: dict | None = None,
) -> dict:
    if not text.strip() or len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("empty or oversized extracted text")
    item = {
        "schema_version": SCHEMA,
        "input_file": path.name,
        "source_url": source_url,
        "input_sha256": input_sha256,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "kind": kind,
        "extractor": extractor,
        "text": text,
        "authority": "source-content-not-action-instructions",
        "completeness": (
            "BEST_EFFORT" if kind in {"html", "asr"} else "EXTRACTED_LOCAL_FILE"
        ),
        "asr_inference_performed": False,
        "network_fetch_performed": False,
    }
    item.update(extra or {})
    identity = {
        key: item[key]
        for key in ("input_sha256", "text_sha256", "source_url", "kind", "extractor")
    }
    identity["model_files"] = item.get("model_files")
    identity["asr_settings"] = item.get("asr_settings")
    item["id"] = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()
    item["created_at"] = datetime.now(timezone.utc).isoformat()
    return item


def extract_file(path: Path, *, source_url: str | None = None) -> dict:
    source, digest = _read_text(path)
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return _item(
            path=path,
            input_sha256=digest,
            text=html_text(source),
            kind="html",
            source_url=source_url,
            extractor="stdlib-html.v1",
            extra={
                "warnings": [
                    "Static snapshot; hidden/unloaded DOM and attachments may be absent."
                ]
            },
        )
    if suffix in {".srt", ".vtt"}:
        segments = subtitle_segments(source)
        return _item(
            path=path,
            input_sha256=digest,
            text="\n".join(s["text"] for s in segments),
            kind="subtitles",
            source_url=source_url,
            extractor="srt-vtt.v1",
            extra={"segments": segments},
        )
    if suffix not in TEXT_SUFFIXES:
        raise ValueError("unsupported extension; export UTF-8 text, HTML or subtitles")
    return _item(
        path=path,
        input_sha256=digest,
        text=source,
        kind="text",
        source_url=source_url,
        extractor="utf8.v1",
    )


def transcribe_file(
    path: Path,
    model_dir: Path,
    *,
    source_url: str | None = None,
    language: str | None = "ru",
    threads: int = 4,
) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_AUDIO_BYTES:
        raise ValueError("regular audio file <= 64 MiB required")
    if not 1 <= threads <= 8:
        raise ValueError("threads must be between 1 and 8")
    if not model_dir.is_dir() or any(
        not (model_dir / name).is_file() for name in MODEL_FILES
    ):
        raise ValueError("complete local CTranslate2 Whisper model directory required")
    # Requiring tokenizer.json avoids faster-whisper's remote tokenizer fallback.
    # This backend is optional; the no-dependency ingestion/search path stays usable.
    from faster_whisper import WhisperModel

    model_files = {name: _digest_file(model_dir / name) for name in MODEL_FILES}
    input_sha256 = _digest_file(path)
    started = time.monotonic()
    model = WhisperModel(
        str(model_dir.resolve()),
        device="cpu",
        compute_type="int8",
        cpu_threads=threads,
        num_workers=1,
        local_files_only=True,
    )
    generated, info = model.transcribe(
        str(path.resolve()), language=language, beam_size=1, vad_filter=False
    )
    segments = [
        {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
        for s in generated
        if s.text.strip()
    ]
    elapsed = time.monotonic() - started
    return _item(
        path=path,
        input_sha256=input_sha256,
        text="\n".join(s["text"] for s in segments),
        kind="asr",
        source_url=source_url,
        extractor="faster-whisper-cpu-int8.v1",
        extra={
            "segments": segments,
            "asr_inference_performed": True,
            "language": info.language,
            "model_files": model_files,
            "asr_settings": {
                "requested_language": language,
                "cpu_threads": threads,
                "compute_type": "int8",
                "beam_size": 1,
                "vad_filter": False,
            },
            "elapsed_seconds": round(elapsed, 3),
            "audio_seconds": float(info.duration),
            "real_time_factor": elapsed / info.duration if info.duration else None,
            "warnings": [
                "Transcript is unverified. This synchronous ASR experiment has no hard time/memory sandbox."
            ],
        },
    )


def _database(store: Path) -> sqlite3.Connection:
    store.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(store / "content.sqlite3", timeout=10)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(id UNINDEXED, text)"
    )
    return connection


def _ensure_sync_tables(connection: sqlite3.Connection) -> None:
    """Use the durable Core head/version schema in the same SQLite owner."""
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS sync_heads(
          namespace TEXT, source_key TEXT, item_id TEXT, raw_hash TEXT,
          generation TEXT, present INTEGER, PRIMARY KEY(namespace, source_key));
        CREATE TABLE IF NOT EXISTS sync_versions(
          namespace TEXT, source_key TEXT, item_id TEXT, observed REAL,
          PRIMARY KEY(namespace, source_key, item_id));
        CREATE TABLE IF NOT EXISTS chatgpt_conversations(
          namespace TEXT, conversation_id TEXT, title TEXT,
          create_time REAL, update_time REAL, current_node TEXT,
          export_sha256 TEXT, generation TEXT, present INTEGER, updated REAL,
          PRIMARY KEY(namespace, conversation_id));
    """)


def _ensure_library_record_tables(connection: sqlite3.Connection) -> None:
    """CAS metadata for Chrome records; items/FTS remain the text owner."""
    _ensure_sync_tables(connection)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS library_record_versions(
          namespace TEXT, source_key TEXT, revision INTEGER,
          parent_revision INTEGER, tombstone INTEGER, item_id TEXT,
          mutation_hash TEXT, provenance TEXT, observed REAL,
          PRIMARY KEY(namespace, source_key, revision));
        CREATE TABLE IF NOT EXISTS library_record_heads(
          namespace TEXT, source_key TEXT, revision INTEGER,
          tombstone INTEGER, item_id TEXT, mutation_hash TEXT, updated REAL,
          PRIMARY KEY(namespace, source_key));
    """)


def _library_timestamp(value, *, nullable=False):
    if nullable and value is None:
        return None
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("LIBRARY_PROVENANCE_SCHEMA")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("LIBRARY_PROVENANCE_SCHEMA") from exc
    return value


def _validate_library_mutation(value: dict) -> tuple[dict, str]:
    fields = {"schema", "namespace", "sourceKey", "revision", "parentRevision",
              "tombstone", "provenance", "content"}
    if (not isinstance(value, dict) or set(value) != fields
            or value.get("schema") != "occ.library-record.v1"):
        raise ValueError("LIBRARY_RECORD_SCHEMA")
    namespace, source_key = value["namespace"], value["sourceKey"]
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise ValueError("LIBRARY_RECORD_NAMESPACE")
    if not isinstance(source_key, str) or not SOURCE_ID.fullmatch(source_key):
        raise ValueError("LIBRARY_RECORD_SOURCE_KEY")
    revision, parent = value["revision"], value["parentRevision"]
    if (type(revision) is not int or not 1 <= revision <= 2_147_483_647
            or (parent is not None and (type(parent) is not int or parent < 1))):
        raise ValueError("LIBRARY_RECORD_REVISION")
    if type(value["tombstone"]) is not bool:
        raise ValueError("LIBRARY_RECORD_SCHEMA")
    provenance = value["provenance"]
    provenance_fields = {"source", "savedAt", "capturedAt", "status", "warnings",
                         "project", "session"}
    if not isinstance(provenance, dict) or set(provenance) != provenance_fields:
        raise ValueError("LIBRARY_PROVENANCE_SCHEMA")
    for field in ("source", "project", "session"):
        if not isinstance(provenance[field], str) or len(provenance[field]) > 1000:
            raise ValueError("LIBRARY_PROVENANCE_SCHEMA")
    if provenance["status"] not in LIBRARY_STATUS:
        raise ValueError("LIBRARY_PROVENANCE_SCHEMA")
    warnings = provenance["warnings"]
    if (not isinstance(warnings, list) or len(warnings) > 100
            or any(not isinstance(item, str) or len(item) > 1000 for item in warnings)):
        raise ValueError("LIBRARY_PROVENANCE_SCHEMA")
    _library_timestamp(provenance["savedAt"])
    _library_timestamp(provenance["capturedAt"], nullable=True)
    content = value["content"]
    if value["tombstone"]:
        if content is not None:
            raise ValueError("LIBRARY_TOMBSTONE_CONTENT")
    else:
        if (not isinstance(content, dict) or set(content) != {"name", "text", "sha256"}
                or not isinstance(content["name"], str) or len(content["name"]) > 1000
                or not isinstance(content["text"], str)
                or len(content["text"].encode("utf-8")) > 8000
                or not re.fullmatch(r"[0-9a-f]{64}", content["sha256"])):
            raise ValueError("LIBRARY_CONTENT_SCHEMA")
        if hashlib.sha256(content["text"].encode("utf-8")).hexdigest() != content["sha256"]:
            raise ValueError("LIBRARY_CONTENT_HASH")
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                     allow_nan=False)
    return value, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def apply_library_record(store: Path, mutation: dict) -> dict:
    """Apply one explicitly selected Chrome record with revision CAS semantics."""
    mutation, mutation_hash = _validate_library_mutation(mutation)
    namespace, source_key = mutation["namespace"], mutation["sourceKey"]
    revision, parent = mutation["revision"], mutation["parentRevision"]
    observed, item_id, stored = time.time(), None, None
    connection = _database(store)
    try:
        _ensure_library_record_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        prior_version = connection.execute(
            "SELECT mutation_hash,item_id,tombstone FROM library_record_versions "
            "WHERE namespace=? AND source_key=? AND revision=?",
            (namespace, source_key, revision),
        ).fetchone()
        if prior_version is not None:
            if prior_version[0] != mutation_hash:
                raise ValueError("LIBRARY_REVISION_CONTENT_CONFLICT")
            connection.commit()
            return {"state": "UNCHANGED", "namespace": namespace,
                    "sourceKey": source_key, "revision": revision,
                    "tombstone": bool(prior_version[2]), "itemId": prior_version[1]}
        head = connection.execute(
            "SELECT revision,item_id FROM library_record_heads "
            "WHERE namespace=? AND source_key=?", (namespace, source_key),
        ).fetchone()
        expected_parent = None if head is None else head[0]
        expected_revision = 1 if head is None else head[0] + 1
        if parent != expected_parent or revision != expected_revision:
            raise ValueError("LIBRARY_STALE_RECORD_CONFLICT")
        provenance_raw = json.dumps(mutation["provenance"], ensure_ascii=False,
                                    sort_keys=True, separators=(",", ":"))
        if not mutation["tombstone"]:
            content = mutation["content"]
            item_id = mutation_hash
            item = {
                "schema": SCHEMA, "id": item_id, "namespace": namespace,
                "source_key": source_key, "text": content["text"],
                "name": content["name"], "input_sha256": content["sha256"],
                "revision": revision, "parent_revision": parent,
                "provenance": mutation["provenance"],
                "authority": "source-content-not-action-instructions",
                "asr_inference_performed": False,
            }
            _, stored = _insert_item(connection, item)
            connection.execute(
                "INSERT OR IGNORE INTO sync_versions VALUES (?,?,?,?)",
                (namespace, source_key, item_id, observed),
            )
        head_item_id = item_id if item_id is not None else head[1]
        connection.execute(
            "INSERT INTO library_record_versions VALUES (?,?,?,?,?,?,?,?,?)",
            (namespace, source_key, revision, parent, int(mutation["tombstone"]),
             head_item_id, mutation_hash, provenance_raw, observed),
        )
        connection.execute(
            "INSERT INTO library_record_heads VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(namespace,source_key) DO UPDATE SET "
            "revision=excluded.revision,tombstone=excluded.tombstone,"
            "item_id=excluded.item_id,mutation_hash=excluded.mutation_hash,updated=excluded.updated",
            (namespace, source_key, revision, int(mutation["tombstone"]),
             head_item_id, mutation_hash, observed),
        )
        connection.execute(
            "INSERT INTO sync_heads VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(namespace,source_key) DO UPDATE SET "
            "item_id=excluded.item_id,raw_hash=excluded.raw_hash,"
            "generation=excluded.generation,present=excluded.present",
            (namespace, source_key, head_item_id, mutation_hash,
             f"chrome-record:{revision}", int(not mutation["tombstone"])),
        )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
    if stored is not None:
        _write_receipt(store, item_id, stored)
    return {"state": "APPLIED", "namespace": namespace, "sourceKey": source_key,
            "revision": revision, "tombstone": mutation["tombstone"],
            "itemId": head_item_id}


def _insert_item(connection: sqlite3.Connection, item: dict) -> tuple[int, str]:
    """Shared transaction primitive for ingestion and durable synchronization."""
    raw = json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False)
    inserted = connection.execute(
        "INSERT OR IGNORE INTO items VALUES (?, ?)", (item["id"], raw)
    ).rowcount
    if inserted:
        connection.execute(
            "INSERT INTO content_fts VALUES (?, ?)", (item["id"], item["text"])
        )
    stored = connection.execute(
        "SELECT payload FROM items WHERE id=?", (item["id"],)
    ).fetchone()[0]
    return inserted, stored


def _write_receipt(store: Path, item_id: str, stored: str) -> Path:
    items_dir = store / "items"
    items_dir.mkdir(exist_ok=True)
    target = items_dir / f"{item_id}.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=items_dir, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(stored + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def save_item(store: Path, item: dict) -> dict:
    connection = _database(store)
    try:
        with connection:
            inserted, stored = _insert_item(connection, item)
    finally:
        connection.close()
    target = _write_receipt(store, item["id"], stored)
    return {
        "state": "imported" if inserted else "deduplicated",
        "id": item["id"],
        "artifact": str(target.resolve()),
        "sha256": _digest_file(target),
        "asr_inference_performed": item["asr_inference_performed"],
    }


def import_chatgpt_export(store: Path, path: Path, namespace: str) -> dict:
    """Atomically advance current message heads while retaining revision history."""
    parsed = parse_chatgpt_export(path, namespace)
    generation = os.urandom(16).hex()
    observed, inserted, unchanged, receipts = time.time(), 0, 0, []
    connection = _database(store)
    try:
        _ensure_sync_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        for record in parsed["conversations"]:
            connection.execute(
                "INSERT INTO chatgpt_conversations VALUES (?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(namespace,conversation_id) DO UPDATE SET "
                "title=excluded.title,create_time=excluded.create_time,"
                "update_time=excluded.update_time,current_node=excluded.current_node,"
                "export_sha256=excluded.export_sha256,generation=excluded.generation,"
                "present=1,updated=excluded.updated",
                (parsed["namespace"], record["conversation_id"], record["title"],
                 record["create_time"], record["update_time"], record["current_node"],
                 parsed["export_sha256"], generation, 1, observed),
            )
        for item in parsed["items"]:
            count, stored = _insert_item(connection, item)
            inserted += count
            previous = connection.execute(
                "SELECT item_id FROM sync_heads WHERE namespace=? AND source_key=?",
                (parsed["namespace"], item["source_key"]),
            ).fetchone()
            unchanged += int(previous is not None and previous[0] == item["id"])
            connection.execute(
                "INSERT OR IGNORE INTO sync_versions VALUES (?,?,?,?)",
                (parsed["namespace"], item["source_key"], item["id"], observed),
            )
            connection.execute(
                "INSERT INTO sync_heads VALUES (?,?,?,?,?,1) "
                "ON CONFLICT(namespace,source_key) DO UPDATE SET "
                "item_id=excluded.item_id,raw_hash=excluded.raw_hash,"
                "generation=excluded.generation,present=1",
                (parsed["namespace"], item["source_key"], item["id"],
                 item["revision_sha256"], generation),
            )
            receipts.append((item["id"], stored))
        connection.execute(
            "UPDATE sync_heads SET present=0 WHERE namespace=? AND generation<>?",
            (parsed["namespace"], generation),
        )
        connection.execute(
            "UPDATE chatgpt_conversations SET present=0 WHERE namespace=? AND generation<>?",
            (parsed["namespace"], generation),
        )
        missing = connection.execute(
            "SELECT count(*) FROM sync_heads WHERE namespace=? AND present=0",
            (parsed["namespace"],),
        ).fetchone()[0]
        missing_conversations = connection.execute(
            "SELECT count(*) FROM chatgpt_conversations WHERE namespace=? AND present=0",
            (parsed["namespace"],),
        ).fetchone()[0]
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
    for item_id, stored in receipts:
        _write_receipt(store, item_id, stored)
    return {
        "state": "IMPORTED_CHATGPT_EXPORT",
        "namespace": parsed["namespace"],
        "conversations": len(parsed["conversations"]),
        "messages": len(parsed["items"]),
        "new_versions": inserted,
        "unchanged": unchanged,
        "missing": missing,
        "missing_conversations": missing_conversations,
        "skipped_non_text": parsed["skipped_non_text"],
        "input_bytes": parsed["input_bytes"],
        "extracted_bytes": parsed["extracted_bytes"],
        "export_sha256": parsed["export_sha256"],
        "model_calls": 0,
        "network_fetches": 0,
    }


def search(store: Path, query: str, *, limit: int = 5) -> list[dict]:
    if not 1 <= limit <= 50:
        raise ValueError("search limit must be between 1 and 50")
    connection = _database(store)
    try:
        rows = connection.execute(
            "SELECT content_fts.id, snippet(content_fts,1,'[',']','…',24), items.payload "
            "FROM content_fts JOIN items ON items.id=content_fts.id "
            "WHERE content_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [
            {
                "id": row[0],
                "snippet": row[1],
                "source_url": json.loads(row[2])["source_url"],
                "input_file": json.loads(row[2])["input_file"],
            }
            for row in rows
        ]
    finally:
        connection.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("ingest", "transcribe"):
        command = commands.add_parser(name)
        command.add_argument("--file", required=True, type=Path)
        command.add_argument("--store", required=True, type=Path)
        command.add_argument("--source-url", default=None)
        if name == "transcribe":
            command.add_argument("--model-dir", required=True, type=Path)
            command.add_argument("--language", default="ru")
            command.add_argument("--threads", type=int, default=4)
    lookup = commands.add_parser("search")
    lookup.add_argument("--store", required=True, type=Path)
    lookup.add_argument("--query", required=True)
    lookup.add_argument("--limit", type=int, default=5)
    chatgpt = commands.add_parser("ingest-chatgpt")
    chatgpt.add_argument("--file", required=True, type=Path)
    chatgpt.add_argument("--store", required=True, type=Path)
    chatgpt.add_argument("--namespace", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "search":
            result = {
                "state": "searched",
                "matches": search(args.store, args.query, limit=args.limit),
            }
        elif args.command == "ingest-chatgpt":
            result = import_chatgpt_export(args.store, args.file, args.namespace)
        else:
            item = (
                extract_file(args.file, source_url=args.source_url)
                if args.command == "ingest"
                else transcribe_file(
                    args.file,
                    args.model_dir,
                    source_url=args.source_url,
                    language=None if args.language == "auto" else args.language,
                    threads=args.threads,
                )
            )
            result = save_item(args.store, item)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ImportError, RuntimeError, sqlite3.Error) as exc:
        print(
            json.dumps(
                {
                    "state": "error",
                    "reason_code": "CONTENT_LAB_INPUT_OR_BACKEND_ERROR",
                    "error_type": type(exc).__name__,
                }
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
