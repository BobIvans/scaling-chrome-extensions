"""Byte-preserving toy vault, provenance, bounded handoff and explicit omissions.

Input is bytes already in memory. This demonstrates contracts, not a streaming
TB-scale importer, encryption, secret scanning, semantic parsing or AI labeling.
"""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .ledger import canonical

def byte_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def partitions(data: bytes, max_bytes: int) -> list[tuple[int, int]]:
    if max_bytes < 4:
        raise ValueError("chunk size must be >=4 to fit a UTF-8 code point")
    try:
        data.decode("utf-8")
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False
    if not data:
        return [(0, 0)]
    result, start = [], 0
    while start < len(data):
        end = min(start+max_bytes, len(data))
        if utf8:
            while end < len(data) and end > start and data[end] & 0xC0 == 0x80:
                end -= 1
        result.append((start, end))
        start = end
    return result

class Vault:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "catalog.sqlite3"
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY, uri TEXT NOT NULL,
                    object_sha TEXT NOT NULL, size INTEGER NOT NULL,
                    metadata TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    source_id TEXT, position INTEGER, start INTEGER, end INTEGER,
                    sha TEXT, text TEXT, PRIMARY KEY(source_id,position)
                );
            """)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.db, timeout=10)
        try:
            with con:
                yield con
        finally:
            con.close()

    def put(self, data: bytes, uri: str, metadata: dict | None = None,
            chunk_bytes: int = 4096) -> str:
        if not uri:
            raise ValueError("source URI required")
        # Validate before making any durable change.
        spans = partitions(data, chunk_bytes)
        object_sha = byte_hash(data)
        metadata = metadata or {}
        meta_text = canonical(metadata)
        # Revisions and URIs remain distinct even when payload bytes are shared.
        source_id = byte_hash(canonical([uri, object_sha, metadata]).encode())
        dest = self.objects / object_sha
        try:
            with dest.open("xb") as file:
                file.write(data)
        except FileExistsError:
            if byte_hash(dest.read_bytes()) != object_sha:
                raise ValueError("corrupt existing object")
        with self.connect() as con:
            existing = con.execute("SELECT source_id FROM sources WHERE source_id=?", (source_id,)).fetchone()
            if existing:
                return source_id
            con.execute("INSERT INTO sources VALUES (?,?,?,?,?)",
                        (source_id, uri, object_sha, len(data), meta_text))
            for position, (start, end) in enumerate(spans):
                block = data[start:end]
                try:
                    text = block.decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                con.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?)",
                            (source_id, position, start, end, byte_hash(block), text))
        return source_id

    def read(self, source_id: str) -> bytes:
        with self.connect() as con:
            row = con.execute("SELECT object_sha,size FROM sources WHERE source_id=?", (source_id,)).fetchone()
        if not row:
            raise KeyError(source_id)
        data = (self.objects / row[0]).read_bytes()
        if len(data) != row[1] or byte_hash(data) != row[0]:
            raise ValueError("source integrity failure")
        return data

    def records(self, source_id: str) -> list[dict]:
        data = self.read(source_id)
        with self.connect() as con:
            rows = con.execute("SELECT position,start,end,sha,text FROM chunks WHERE source_id=? ORDER BY position",
                               (source_id,)).fetchall()
        result, cursor = [], 0
        for position, start, end, sha, text in rows:
            if start != cursor or not start <= end <= len(data) or byte_hash(data[start:end]) != sha:
                raise ValueError("chunk integrity failure")
            try:
                expected_text = data[start:end].decode("utf-8")
            except UnicodeDecodeError:
                expected_text = None
            if text != expected_text:
                raise ValueError("normalized text does not match original bytes")
            result.append({"ref": f"{source_id}:{position}", "source_id": source_id,
                           "start": start, "end": end, "sha256": sha, "text": text})
            cursor = end
        if not rows or cursor != len(data):
            raise ValueError("incomplete partition")
        return result

    def compile_pack(self, source_ids: list[str], query: str, *, budget_bytes: int,
                     required_refs: tuple[str, ...] = (),
                     allow_cloud: bool = False) -> dict:
        if budget_bytes < 0:
            raise ValueError("negative evidence byte budget")
        terms = set(re.findall(r"\w+", query.casefold()))
        pool, omissions, unique = [], [], set()
        # No max-document count. This toy still scans all selected source chunks.
        for source_id in source_ids:
            if source_id in unique:
                continue
            unique.add(source_id)
            with self.connect() as con:
                row = con.execute("SELECT uri,metadata FROM sources WHERE source_id=?", (source_id,)).fetchone()
            if row is None:
                omissions.append({"source_id": source_id, "reason": "MISSING_SOURCE"})
                continue
            uri, rawmeta = row
            meta = json.loads(rawmeta)
            for block in self.records(source_id):
                block["uri"], block["metadata"] = uri, meta
                if allow_cloud and meta.get("privacy", "private") != "public":
                    omissions.append({"ref": block["ref"], "reason": "PRIVATE_SOURCE_NOT_CLOUD_APPROVED"})
                elif block["text"] is None:
                    omissions.append({"ref": block["ref"], "reason": "BINARY_NOT_TEXT"})
                else:
                    block["score"] = sum(t in block["text"].casefold() for t in terms)
                    pool.append(block)
        pool.sort(key=lambda x: (x["ref"] not in required_refs, -x["score"], x["ref"]))
        used, selected = 0, []
        for block in pool:
            size = len(block["text"].encode("utf-8"))
            if used + size <= budget_bytes:
                selected.append(block)
                used += size
            else:
                omissions.append({"ref": block["ref"], "reason": "EVIDENCE_BUDGET", "bytes": size})
        present = {x["ref"] for x in selected}
        missing_required = sorted(set(required_refs)-present)
        return {"schema": "agentos.context-pack/v0.2", "query": query,
                "status": "NEEDS_CONTEXT" if missing_required else "READY_FOR_REVIEW",
                "evidence_bytes": used, "evidence_budget_bytes": budget_bytes,
                "budget_note": "Evidence text only; NOT total serialized request or exact model tokens.",
                "sources_selected": len(unique), "evidence": selected,
                "omissions": omissions, "missing_required_refs": missing_required,
                "automatic_execution_authorized": False}
