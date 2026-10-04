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
import stat
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
MAX_CHATGPT_ATTACHMENTS = 100_000
MAX_CHATGPT_NODES = 100_000
MAX_CHATGPT_LEDGER_BYTES = 64 * 1024 * 1024
MAX_CHATGPT_INSPECT_BYTES = 1_000_000
FIDELITY_EXTRACTOR_VERSION = "chatgpt-json-fidelity.v1"
MAX_ATTACHMENT_POINTER_BYTES = 4096
TEXT_SUFFIXES = {".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".yaml", ".yml"}
MODEL_FILES = ("model.bin", "config.json", "tokenizer.json", "preprocessor_config.json")
SOURCE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
NAMESPACE = re.compile(r"^[A-Za-z0-9_.:-]{1,90}$")
LIBRARY_STATUS = {"ORIGINAL", "EXTRACTED", "EMPTY", "UNSUPPORTED", "SELECTION",
                  "RAW_TEXT", "PARTIAL", "BEST_EFFORT"}
ATTACHMENT_CONTENT_TYPES = {
    "image_asset_pointer", "audio_asset_pointer", "file_asset_pointer"
}


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


def _capture_chatgpt_export(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".json":
        raise ValueError("regular local ChatGPT JSON export required")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("regular local ChatGPT JSON export required")
        if before.st_size > MAX_CHATGPT_EXPORT_BYTES:
            raise ValueError("ChatGPT export exceeds byte budget")
        raw = handle.read(MAX_CHATGPT_EXPORT_BYTES + 1)
        after = os.fstat(handle.fileno())
    current = path.lstat()
    if (not stat.S_ISREG(current.st_mode) or
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
             before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
             after.st_ctime_ns) or
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
            (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) or
            len(raw) != before.st_size):
        raise ValueError("ChatGPT export changed during read")
    if len(raw) > MAX_CHATGPT_EXPORT_BYTES:
        raise ValueError("ChatGPT export exceeds byte budget")
    return raw


def _decode_chatgpt_export(raw: bytes) -> tuple[list, str, int]:
    try:
        source = raw.decode("utf-8-sig")
        value = json.loads(source, object_pairs_hook=_unique_object,
                           parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 ChatGPT JSON export") from exc
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CHATGPT_CONVERSATIONS:
        raise ValueError("bounded ChatGPT conversation array required")
    return value, hashlib.sha256(raw).hexdigest(), len(raw)


def _read_chatgpt_export(path: Path) -> tuple[list, str, int]:
    return _decode_chatgpt_export(_capture_chatgpt_export(path))


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


def _attachment_inventory(content, *, scope, conversation_id, message_id):
    """Describe non-text parts without dereferencing their asset pointers."""
    if not isinstance(content, dict):
        return []
    parts = content.get("parts")
    if isinstance(parts, list):
        candidates = [(index, part) for index, part in enumerate(parts)
                      if not isinstance(part, str)]
    elif content.get("content_type") not in (None, "text", "multimodal_text"):
        candidates = [(0, content)]
    else:
        candidates = []
    inventory = []
    for part_index, part in candidates:
        value = part if isinstance(part, dict) else {}
        content_type = value.get("content_type")
        pointer = value.get("asset_pointer")
        if content_type in ATTACHMENT_CONTENT_TYPES:
            if pointer is None or pointer == "":
                state, pointer = "MISSING", None
            elif (not isinstance(pointer, str)
                  or len(pointer.encode("utf-8")) > MAX_ATTACHMENT_POINTER_BYTES):
                state, pointer = "UNSUPPORTED", None
            else:
                state = "PRESENT"
        else:
            state, pointer = "UNSUPPORTED", None
        if not isinstance(content_type, str) or not content_type or len(content_type) > 100:
            content_type = "unknown"
            state = "UNSUPPORTED"
        declared_hash = value.get("sha256", value.get("content_sha256"))
        if declared_hash is None:
            declared_hash_status, declared_hash = "ABSENT", None
        elif isinstance(declared_hash, str) and re.fullmatch(r"[0-9a-f]{64}", declared_hash):
            declared_hash_status = "VALID"
        else:
            declared_hash_status, declared_hash = "INVALID", None
        source_key = (
            f"chatgpt/{conversation_id}/{message_id}/attachment/{part_index}"
        )
        record = {
            "schema": "occ.attachment-inventory.v1",
            "namespace": scope,
            "source_key": source_key,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "part_index": part_index,
            "content_type": content_type,
            "state": state,
            "asset_pointer": pointer,
            "pointer_sha256": (hashlib.sha256(pointer.encode("utf-8")).hexdigest()
                               if pointer is not None else None),
            "declared_content_sha256": declared_hash,
            "declared_hash_status": declared_hash_status,
            "rights_status": "UNVERIFIED",
            "retrieval_allowed": False,
            "bytes_present": False,
            "network_fetch_performed": False,
            "authority": "source-metadata-not-action-instructions",
        }
        hash_source = json.dumps(record, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False).encode("utf-8")
        record["metadata_sha256"] = hashlib.sha256(hash_source).hexdigest()
        inventory.append(record)
    return inventory


def parse_chatgpt_export(path: Path, namespace: str, *, raw: bytes | None = None,
                         decoded: tuple | None = None) -> dict:
    """Parse selected conversations into immutable message revisions.

    Only synthetic schema facts become code assumptions. User content remains
    local data and never grants action authority.
    """
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise ValueError("bounded ChatGPT namespace required")
    conversations, export_sha256, input_bytes = (decoded if decoded is not None else
        (_read_chatgpt_export(path) if raw is None else _decode_chatgpt_export(raw)))
    scope = "chatgpt:" + namespace
    items, records, attachments, skipped_non_text, extracted_bytes = [], [], [], 0, 0
    seen_conversations, seen_messages, node_count = set(), set(), 0
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
        node_count += len(mapping)
        if node_count > MAX_CHATGPT_NODES:
            raise ValueError("ChatGPT total mapping nodes exceed budget")
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
            attachments.extend(_attachment_inventory(
                message.get("content"), scope=scope,
                conversation_id=conversation_id, message_id=message_id,
            ))
            if len(attachments) > MAX_CHATGPT_ATTACHMENTS:
                raise ValueError("ChatGPT attachment count exceeds budget")
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
    attachments.sort(key=lambda item: item["source_key"])
    return {"namespace": scope, "export_sha256": export_sha256,
            "input_bytes": input_bytes, "conversations": records, "items": items,
            "attachments": attachments,
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


def _database(store: Path, *, configure=None) -> sqlite3.Connection:
    store.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(store / "content.sqlite3", timeout=10)
    try:
        if configure is not None:
            configure(connection)
        connection.execute("PRAGMA journal_mode=WAL")
        if configure is None:
            connection.execute("PRAGMA busy_timeout=10000")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(id UNINDEXED, text)"
        )
    except BaseException:
        connection.close()
        raise
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
        CREATE TABLE IF NOT EXISTS attachment_versions(
          namespace TEXT, source_key TEXT, metadata_sha256 TEXT,
          payload TEXT, observed REAL,
          PRIMARY KEY(namespace, source_key, metadata_sha256));
        CREATE TABLE IF NOT EXISTS attachment_heads(
          namespace TEXT, source_key TEXT, metadata_sha256 TEXT,
          generation TEXT, present INTEGER, updated REAL,
          PRIMARY KEY(namespace, source_key));
    """)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _stable_id(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _ensure_import_tables(connection: sqlite3.Connection) -> None:
    """Add original and extraction history to the existing Content Lab database."""
    _ensure_sync_tables(connection)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS import_raw_blobs(
          sha256 TEXT PRIMARY KEY, byte_count INTEGER NOT NULL,
          raw BLOB NOT NULL CHECK(typeof(raw)='blob' AND length(raw)=byte_count));
        CREATE TABLE IF NOT EXISTS import_source_versions(
          namespace TEXT NOT NULL, source_key TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
          source_version_id TEXT NOT NULL UNIQUE, first_observed_at REAL NOT NULL,
          PRIMARY KEY(namespace,source_key,raw_sha256),
          FOREIGN KEY(raw_sha256) REFERENCES import_raw_blobs(sha256));
        CREATE TABLE IF NOT EXISTS import_origins(
          origin_id TEXT PRIMARY KEY, namespace TEXT NOT NULL, source_key TEXT NOT NULL,
          raw_sha256 TEXT NOT NULL, origin_locator TEXT NOT NULL,
          scope_policy TEXT NOT NULL, first_observed_at REAL NOT NULL,
          FOREIGN KEY(namespace,source_key,raw_sha256)
            REFERENCES import_source_versions(namespace,source_key,raw_sha256));
        CREATE TABLE IF NOT EXISTS import_extractions(
          namespace TEXT NOT NULL, source_key TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
          extractor_key TEXT NOT NULL, extraction_id TEXT NOT NULL UNIQUE,
          payload_sha256 TEXT NOT NULL, payload BLOB NOT NULL,
          disposition TEXT NOT NULL, first_observed_at REAL NOT NULL,
          PRIMARY KEY(namespace,source_key,raw_sha256,extractor_key),
          FOREIGN KEY(namespace,source_key,raw_sha256)
            REFERENCES import_source_versions(namespace,source_key,raw_sha256));
        CREATE TABLE IF NOT EXISTS import_node_ledger(
          extraction_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
          conversation_id TEXT NOT NULL, node_id TEXT NOT NULL, payload BLOB NOT NULL,
          payload_sha256 TEXT NOT NULL,
          PRIMARY KEY(extraction_id,ordinal),
          UNIQUE(extraction_id,conversation_id,node_id),
          FOREIGN KEY(extraction_id) REFERENCES import_extractions(extraction_id));
        CREATE TABLE IF NOT EXISTS import_absences(
          extraction_id TEXT NOT NULL, kind TEXT NOT NULL, source_key TEXT NOT NULL,
          reason TEXT NOT NULL, PRIMARY KEY(extraction_id,kind,source_key),
          FOREIGN KEY(extraction_id) REFERENCES import_extractions(extraction_id));
        CREATE TABLE IF NOT EXISTS import_source_heads(
          namespace TEXT NOT NULL, source_key TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
          extractor_key TEXT NOT NULL, last_observed_at REAL NOT NULL,
          PRIMARY KEY(namespace,source_key),
          FOREIGN KEY(namespace,source_key,raw_sha256,extractor_key)
            REFERENCES import_extractions(namespace,source_key,raw_sha256,extractor_key));
    """)


def _pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _node_ledger(conversations: list) -> tuple[list[tuple[str, str, bytes]], dict]:
    rows, gap_counts, encoded_bytes, child_refs = [], {}, 0, 0
    ledger_hash = hashlib.sha256()
    for index, conversation in enumerate(conversations):
        mapping, cid = conversation["mapping"], conversation["id"]
        nodes = {}
        for node_id, node in mapping.items():
            _source_id(node_id, "node id")
            if not isinstance(node, dict):
                raise ValueError("ChatGPT mapping node object required")
            parent = node.get("parent")
            if parent is not None:
                _source_id(parent, "parent node id")
            children = node.get("children", [])
            if not isinstance(children, list):
                raise ValueError("ChatGPT declared children array required")
            child_refs += len(children)
            if child_refs > MAX_CHATGPT_NODES:
                raise ValueError("ChatGPT total child references exceed budget")
            for child in children:
                _source_id(child, "child node id")
            nodes[node_id] = (parent, children)
        cycles, visited = set(), set()
        for start in nodes:
            if start in visited:
                continue
            chain, offsets, cursor = [], {}, start
            while cursor in nodes and cursor not in visited and cursor not in offsets:
                offsets[cursor] = len(chain)
                chain.append(cursor)
                cursor = nodes[cursor][0]
            if cursor in offsets:
                cycles.update(chain[offsets[cursor]:])
            visited.update(chain)
        current = conversation.get("current_node")
        if current is not None and current not in nodes:
            gap_counts["CURRENT_NODE_MISSING"] = gap_counts.get("CURRENT_NODE_MISSING", 0) + 1
        for node_id, node in mapping.items():
            parent, children = nodes[node_id]
            gaps = []
            if parent is not None:
                if parent not in nodes:
                    gaps.append("MISSING_PARENT")
                elif node_id not in nodes[parent][1]:
                    gaps.append("PARENT_CHILD_MISMATCH")
            for child in children:
                if child not in nodes:
                    gaps.append("MISSING_CHILD")
                elif nodes[child][0] != node_id:
                    gaps.append("CHILD_PARENT_MISMATCH")
            if node_id in cycles:
                gaps.append("PARENT_CYCLE")
            message = node.get("message")
            if message is None:
                state, message_id, role, source_time, content_type, author_name = (
                    "STRUCTURAL_NODE", None, None, None, None, None)
            else:
                if not isinstance(message, dict):
                    raise ValueError("ChatGPT message object required")
                message_id = _source_id(message.get("id"), "message id")
                author = message.get("author")
                role = author.get("role") if isinstance(author, dict) else None
                author_name = author.get("name") if isinstance(author, dict) else None
                source_time = _source_time(message.get("create_time"))
                content = message.get("content")
                text, _, content_type = _message_text(content)
                state = ("TEXT_EXTRACTED" if text is not None else
                         "NON_TEXT_ONLY" if _attachment_inventory(
                             content, scope="chatgpt:ledger", conversation_id=cid,
                             message_id=message_id) else "EMPTY_CONTENT")
            record = {
                "conversation_id": cid, "node_id": node_id,
                "json_pointer": f"/{index}/mapping/{_pointer(node_id)}",
                "declared_node_id": node.get("id"),
                "parent_node_id": parent, "declared_children": children,
                "message_id": message_id, "message_pointer": (
                    f"/{index}/mapping/{_pointer(node_id)}/message" if message is not None else None),
                "author_role_declared": role, "author_name_declared": author_name,
                "source_message_time": source_time, "content_type": content_type,
                "state": state, "topology_gaps": sorted(set(gaps)),
                "remote_completeness": "UNKNOWN",
            }
            encoded = _canonical_bytes(record)
            encoded_bytes += len(encoded)
            if encoded_bytes > MAX_CHATGPT_LEDGER_BYTES:
                raise ValueError("ChatGPT node ledger exceeds byte budget")
            ledger_hash.update(len(encoded).to_bytes(8, "big"))
            ledger_hash.update(encoded)
            for gap in gaps:
                gap_counts[gap] = gap_counts.get(gap, 0) + 1
            rows.append((cid, node_id, encoded))
    return rows, {"observed_nodes": len(rows), "ledger_bytes": encoded_bytes,
                  "ledger_sha256": ledger_hash.hexdigest(),
                  "topology_gaps": gap_counts, "remote_completeness": "UNKNOWN"}


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


def _import_identity(namespace: str, source_key: str, raw_sha256: str):
    extractor_key = _stable_id({"fidelity": FIDELITY_EXTRACTOR_VERSION,
                                "text": "chatgpt-export.v1",
                                "attachments": "occ.attachment-inventory.v1",
                                "policy": "selected-local-json.v1"})
    version_id = _stable_id({"namespace": namespace, "source_key": source_key,
                             "raw_sha256": raw_sha256})
    extraction_id = _stable_id({"source_version_id": version_id,
                                "extractor_key": extractor_key})
    return version_id, extractor_key, extraction_id


def _store_import_envelope(connection, *, raw, scope, source_key, path,
                           summary, disposition, rows, observed):
    raw_hash = hashlib.sha256(raw).hexdigest()
    version_id, extractor_key, extraction_id = _import_identity(scope, source_key, raw_hash)
    payload = _canonical_bytes(summary)
    previous = connection.execute(
        "SELECT raw,byte_count FROM import_raw_blobs WHERE sha256=?", (raw_hash,)
    ).fetchone()
    if previous is not None and (previous[0] != raw or previous[1] != len(raw)):
        raise ValueError("IMPORT_RAW_BLOB_INTEGRITY")
    connection.execute("INSERT OR IGNORE INTO import_raw_blobs VALUES (?,?,?)",
                       (raw_hash, len(raw), sqlite3.Binary(raw)))
    connection.execute("INSERT OR IGNORE INTO import_source_versions VALUES (?,?,?,?,?)",
                       (scope, source_key, raw_hash, version_id, observed))
    locator = os.path.abspath(path)
    origin_id = _stable_id({"source_version_id": version_id, "locator": locator})
    connection.execute("INSERT OR IGNORE INTO import_origins VALUES (?,?,?,?,?,?,?)",
                       (origin_id, scope, source_key, raw_hash, locator,
                        "SELECTED_LOCAL_JSON", observed))
    existing = connection.execute(
        "SELECT payload_sha256,payload,disposition FROM import_extractions "
        "WHERE extraction_id=?", (extraction_id,),
    ).fetchone()
    payload_hash = hashlib.sha256(payload).hexdigest()
    if existing is not None and existing != (payload_hash, payload, disposition):
        raise ValueError("IMPORT_EXTRACTION_INTEGRITY")
    connection.execute(
        "INSERT OR IGNORE INTO import_extractions VALUES (?,?,?,?,?,?,?,?,?)",
        (scope, source_key, raw_hash, extractor_key, extraction_id,
         payload_hash, sqlite3.Binary(payload), disposition, observed),
    )
    if existing is None:
        connection.executemany(
            "INSERT INTO import_node_ledger VALUES (?,?,?,?,?,?)",
            ((extraction_id, ordinal, cid, node_id, sqlite3.Binary(record),
              hashlib.sha256(record).hexdigest())
             for ordinal, (cid, node_id, record) in enumerate(rows)),
        )
    elif connection.execute("SELECT count(*) FROM import_node_ledger WHERE extraction_id=?",
                            (extraction_id,)).fetchone()[0] != len(rows):
        raise ValueError("IMPORT_NODE_LEDGER_INTEGRITY")
    connection.execute(
        "INSERT INTO import_source_heads VALUES (?,?,?,?,?) "
        "ON CONFLICT(namespace,source_key) DO UPDATE SET "
        "raw_sha256=excluded.raw_sha256,extractor_key=excluded.extractor_key,"
        "last_observed_at=excluded.last_observed_at",
        (scope, source_key, raw_hash, extractor_key, observed),
    )
    return version_id, extraction_id, raw_hash


def import_chatgpt_export(store: Path, path: Path, namespace: str,
                          *, source_key: str | None = None) -> dict:
    """Capture one selected JSON, then atomically advance only observed chat heads."""
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise ValueError("bounded ChatGPT namespace required")
    raw = _capture_chatgpt_export(path)  # Read the chosen regular file once.
    scope = "chatgpt:" + namespace
    if source_key is None:
        source_key = "file:" + hashlib.sha256(
            os.path.abspath(path).encode("utf-8")).hexdigest()
    _source_id(source_key, "source key")
    parsed, rows, summary, error_code = None, [], None, None
    try:
        decoded = _decode_chatgpt_export(raw)
        parsed = parse_chatgpt_export(path, namespace, decoded=decoded)
        rows, summary = _node_ledger(decoded[0])
        summary.update({"selected_conversations": [r["conversation_id"] for r in
                         parsed["conversations"]], "messages": len(parsed["items"]),
                        "attachments": len(parsed["attachments"])})
    except (ValueError, UnicodeError, RecursionError) as exc:
        error_code = ("ERROR_LEDGER_BUDGET" if "ledger exceeds byte budget" in str(exc)
                      else "ERROR_NODE_BUDGET" if "nodes exceed budget" in str(exc)
                      else "ERROR_INVALID_SELECTED_EXPORT")
        summary = {"error_code": error_code, "remote_completeness": "UNKNOWN"}
        rows = []
    disposition = ("ERROR" if error_code else
                   "PARTIAL_TOPOLOGY" if summary["topology_gaps"] else
                   "LOCAL_NODES_ACCOUNTED")
    generation = os.urandom(16).hex()
    observed, inserted, unchanged, receipts = time.time(), 0, 0, []
    attachment_inserted, attachment_unchanged = 0, 0
    try:
        connection = _database(store)
    except (OSError, sqlite3.Error) as exc:
        return {"state": "IMPORT_STORAGE_ERROR", "reason_code": type(exc).__name__,
                "original_retained": False, "derived_heads_changed": False}
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        _ensure_import_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        version_id, extraction_id, raw_hash = _store_import_envelope(
            connection, raw=raw, scope=scope, source_key=source_key, path=path,
            summary=summary, disposition=disposition, rows=rows, observed=observed)
        if error_code:
            connection.commit()
            return {"state": "ORIGINAL_RETAINED_EXTRACTION_ERROR", "reason_code": error_code,
                    "original_retained": True, "derived_heads_changed": False,
                    "namespace": scope, "source_version_id": version_id,
                    "extraction_id": extraction_id, "export_sha256": raw_hash}
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
        for attachment in parsed["attachments"]:
            payload = json.dumps(attachment, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False)
            previous = connection.execute(
                "SELECT metadata_sha256 FROM attachment_heads "
                "WHERE namespace=? AND source_key=?",
                (parsed["namespace"], attachment["source_key"]),
            ).fetchone()
            attachment_unchanged += int(
                previous is not None and previous[0] == attachment["metadata_sha256"]
            )
            attachment_inserted += connection.execute(
                "INSERT OR IGNORE INTO attachment_versions VALUES (?,?,?,?,?)",
                (parsed["namespace"], attachment["source_key"],
                 attachment["metadata_sha256"], payload, observed),
            ).rowcount
            connection.execute(
                "INSERT INTO attachment_heads VALUES (?,?,?,?,1,?) "
                "ON CONFLICT(namespace,source_key) DO UPDATE SET "
                "metadata_sha256=excluded.metadata_sha256,"
                "generation=excluded.generation,present=1,updated=excluded.updated",
                (parsed["namespace"], attachment["source_key"],
                 attachment["metadata_sha256"], generation, observed),
            )
        missing, removed_attachments, missing_conversations = 0, 0, 0
        for record in parsed["conversations"]:
            prefix = f"chatgpt/{record['conversation_id']}/"
            for table, kind in (("sync_heads", "message"),
                                ("attachment_heads", "attachment")):
                absent = connection.execute(
                    f"SELECT source_key FROM {table} WHERE namespace=? AND present=1 "
                    "AND substr(source_key,1,length(?))=? AND generation<>?",
                    (scope, prefix, prefix, generation),
                ).fetchall()
                connection.executemany(
                    "INSERT OR IGNORE INTO import_absences VALUES (?,?,?,?)",
                    ((extraction_id, kind, key, "NOT_OBSERVED_IN_SELECTED_EXPORT")
                     for (key,) in absent),
                )
                connection.execute(
                    f"UPDATE {table} SET present=0 WHERE namespace=? AND present=1 "
                    "AND substr(source_key,1,length(?))=? AND generation<>?",
                    (scope, prefix, prefix, generation),
                )
                if kind == "message":
                    missing += len(absent)
                else:
                    removed_attachments += len(absent)
        connection.commit()
    except (OSError, sqlite3.Error) as exc:
        connection.rollback()
        return {"state": "IMPORT_STORAGE_ERROR", "reason_code": type(exc).__name__,
                "original_retained": False, "derived_heads_changed": False}
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
    receipt_warning = False
    for item_id, stored in receipts:
        try:
            _write_receipt(store, item_id, stored)
        except OSError:
            receipt_warning = True
    attachment_states = {state: 0 for state in ("PRESENT", "MISSING", "UNSUPPORTED")}
    for attachment in parsed["attachments"]:
        attachment_states[attachment["state"]] += 1
    return {
        "state": ("COMMITTED_WITH_RECEIPT_WARNING" if receipt_warning else
                  "IMPORTED_CHATGPT_EXPORT"),
        "original_retained": True,
        "source_version_id": version_id,
        "extraction_id": extraction_id,
        "fidelity_disposition": disposition,
        "observed_nodes": summary["observed_nodes"],
        "topology_gaps": summary["topology_gaps"],
        "namespace": parsed["namespace"],
        "conversations": len(parsed["conversations"]),
        "messages": len(parsed["items"]),
        "new_versions": inserted,
        "unchanged": unchanged,
        "missing": missing,
        "missing_conversations": missing_conversations,
        "attachments": len(parsed["attachments"]),
        "new_attachment_versions": attachment_inserted,
        "unchanged_attachments": attachment_unchanged,
        "removed_attachments": removed_attachments,
        "attachment_states": attachment_states,
        "skipped_non_text": parsed["skipped_non_text"],
        "input_bytes": parsed["input_bytes"],
        "extracted_bytes": parsed["extracted_bytes"],
        "export_sha256": parsed["export_sha256"],
        "model_calls": 0,
        "network_fetches": 0,
    }


def _import_read_connection(store: Path) -> sqlite3.Connection:
    database = store / "content.sqlite3"
    if not database.is_file():
        raise ValueError("IMPORT_VERSION_NOT_FOUND")
    return sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)


def inspect_chatgpt_import(store: Path, version_id: str, extraction_id: str,
                           *, offset: int = 0, limit: int = 50) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", version_id) or not re.fullmatch(
            r"[0-9a-f]{64}", extraction_id):
        raise ValueError("IMPORT_VERSION_NOT_FOUND")
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("IMPORT_PAGE_BOUNDARY")
    connection = _import_read_connection(store)
    try:
        row = connection.execute(
            "SELECT v.namespace,v.source_key,v.raw_sha256,b.byte_count,"
            "e.extractor_key,e.payload_sha256,e.payload,e.disposition "
            "FROM import_source_versions v "
            "JOIN import_raw_blobs b ON b.sha256=v.raw_sha256 "
            "JOIN import_extractions e ON (e.namespace,e.source_key,e.raw_sha256)="
            "(v.namespace,v.source_key,v.raw_sha256) "
            "WHERE v.source_version_id=? AND e.extraction_id=?",
            (version_id, extraction_id),
        ).fetchone()
        if row is None:
            raise ValueError("IMPORT_VERSION_NOT_FOUND")
        scope, key, raw_hash, count, extractor, payload_hash, payload, disposition = row
        if (_stable_id({"namespace": scope, "source_key": key,
                        "raw_sha256": raw_hash}) != version_id or
                _stable_id({"source_version_id": version_id,
                            "extractor_key": extractor}) != extraction_id or
                hashlib.sha256(payload).hexdigest() != payload_hash):
            raise ValueError("IMPORT_VERSION_INTEGRITY")
        nodes, page_bytes = [], 0
        for cid, node_id, raw, digest in connection.execute(
                "SELECT conversation_id,node_id,payload,payload_sha256 FROM import_node_ledger "
                "WHERE extraction_id=? ORDER BY ordinal LIMIT ? OFFSET ?",
                (extraction_id, limit, offset)):
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("IMPORT_NODE_LEDGER_INTEGRITY")
            if page_bytes + len(raw) > MAX_CHATGPT_INSPECT_BYTES:
                if nodes:
                    break
                nodes.append({"conversation_id": cid, "node_id": node_id,
                              "metadata_omitted": True, "metadata_bytes": len(raw),
                              "payload_sha256": digest})
            else:
                nodes.append(json.loads(raw))
                page_bytes += len(raw)
        total = json.loads(payload)["observed_nodes"] if disposition != "ERROR" else 0
        return {"source_version_id": version_id, "extraction_id": extraction_id,
                "namespace": scope, "source_key": key, "raw_sha256": raw_hash,
                "byte_count": count, "extractor_key": extractor,
                "disposition": disposition, "summary": json.loads(payload),
                "nodes": nodes, "offset": offset, "limit": limit,
                "next_offset": offset + len(nodes) if offset + len(nodes) < total else None}
    finally:
        connection.close()


def read_chatgpt_original(store: Path, version_id: str, output: Path,
                          *, overwrite: bool = False) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", version_id):
        raise ValueError("IMPORT_VERSION_NOT_FOUND")
    connection = _import_read_connection(store)
    try:
        row = connection.execute(
            "SELECT v.namespace,v.source_key,v.raw_sha256,b.byte_count,b.raw "
            "FROM import_source_versions v JOIN import_raw_blobs b "
            "ON b.sha256=v.raw_sha256 WHERE v.source_version_id=?", (version_id,)
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("IMPORT_VERSION_NOT_FOUND")
    scope, key, raw_hash, count, raw = row
    if (_import_identity(scope, key, raw_hash)[0] != version_id or
            len(raw) != count or hashlib.sha256(raw).hexdigest() != raw_hash):
        raise ValueError("IMPORT_ORIGINAL_INTEGRITY")
    if output.is_symlink() or (output.exists() and not overwrite):
        raise ValueError("IMPORT_DESTINATION_EXISTS")
    with tempfile.NamedTemporaryFile(mode="wb", dir=output.parent,
                                     prefix=".chatgpt-original-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            view = memoryview(raw)
            for position in range(0, len(view), 1024 * 1024):
                handle.write(view[position:position + 1024 * 1024])
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        if output.is_symlink() or (output.exists() and not overwrite):
            raise ValueError("IMPORT_DESTINATION_EXISTS")
        if _digest_file(temporary) != raw_hash:
            raise ValueError("IMPORT_ORIGINAL_INTEGRITY")
        if overwrite:
            os.replace(temporary, output)
        else:
            os.link(temporary, output)  # Atomic exclusive create; never replace a race winner.
    finally:
        temporary.unlink(missing_ok=True)
    return {"state": "ORIGINAL_WRITTEN", "source_version_id": version_id,
            "sha256": raw_hash, "byte_count": count, "output": str(output.resolve())}


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
    chatgpt.add_argument("--source-key")
    inspection = commands.add_parser("inspect-chatgpt")
    inspection.add_argument("--store", required=True, type=Path)
    inspection.add_argument("--version-id", required=True)
    inspection.add_argument("--extraction-id", required=True)
    inspection.add_argument("--offset", type=int, default=0)
    inspection.add_argument("--limit", type=int, default=50)
    original = commands.add_parser("read-chatgpt-original")
    original.add_argument("--store", required=True, type=Path)
    original.add_argument("--version-id", required=True)
    original.add_argument("--output", required=True, type=Path)
    original.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "search":
            result = {
                "state": "searched",
                "matches": search(args.store, args.query, limit=args.limit),
            }
        elif args.command == "ingest-chatgpt":
            result = import_chatgpt_export(args.store, args.file, args.namespace,
                                           source_key=args.source_key)
        elif args.command == "inspect-chatgpt":
            result = inspect_chatgpt_import(args.store, args.version_id,
                                            args.extraction_id, offset=args.offset,
                                            limit=args.limit)
        elif args.command == "read-chatgpt-original":
            result = read_chatgpt_original(args.store, args.version_id,
                                           args.output, overwrite=args.overwrite)
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
