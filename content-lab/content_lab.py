"""Local content and optional CPU ASR experiments; never an action executor."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any

SCHEMA = "occ.content-lab.item.v1"
MAX_TEXT_BYTES = 2_200_000
MAX_AUDIO_BYTES = 64 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".yaml", ".yml"}
MODEL_FILES = ("model.bin", "config.json", "tokenizer.json", "preprocessor_config.json")


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
    connection.execute(
        "CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(id UNINDEXED, text)"
    )
    return connection


def save_item(store: Path, item: dict) -> dict:
    raw = json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False)
    connection = _database(store)
    try:
        with connection:
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
    finally:
        connection.close()
    items_dir = store / "items"
    items_dir.mkdir(exist_ok=True)
    target = items_dir / f"{item['id']}.json"
    target.write_text(stored + "\n", encoding="utf-8")
    return {
        "state": "imported" if inserted else "deduplicated",
        "id": item["id"],
        "artifact": str(target.resolve()),
        "sha256": _digest_file(target),
        "asr_inference_performed": item["asr_inference_performed"],
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
    args = parser.parse_args(argv)
    try:
        if args.command == "search":
            result = {
                "state": "searched",
                "matches": search(args.store, args.query, limit=args.limit),
            }
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
