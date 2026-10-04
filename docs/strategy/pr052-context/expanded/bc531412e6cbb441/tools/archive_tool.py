#!/usr/bin/env python3
"""Portable, local-only repository/folder evidence archive. Python 3.10+.

This is an offline export artifact format, NOT a replacement for SCE's durable DB.
No model calls, uploads, shell execution of source code, or file-count ceilings.
Regular-file originals stay byte-exact; links are never followed. See README.
"""
from __future__ import annotations
import argparse
import ast
import base64
import codecs
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import BinaryIO, Iterator

BLOCK = 1024 * 1024
SCHEMA = "occ.portable-archive.v1"
SECRET_NAME = re.compile(r"(^|/)(\.env($|\.)|id_rsa$|id_ed25519$|credentials\.json$|keypair\.json$)|\.(pem|p12|pfx|key)$", re.I)


def js(value: object) -> str:
    # ASCII escaping preserves even POSIX surrogate-escaped names in valid JSON.
    return json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False)


def dump(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(js(value) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(BLOCK), b""):
            h.update(data)
    return h.hexdigest()


def safe_child(root: Path, relative: str) -> Path:
    """Reject traversal and symlinked archive objects; archives are untrusted."""
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or "\\" in relative or ":" in relative:
        raise ValueError("UNSAFE_ARCHIVE_REFERENCE")
    target = root / p
    if any(x.is_symlink() for x in [target, *target.parents] if x != root.parent):
        raise ValueError("ARCHIVE_SYMLINK_BLOCKED")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("ARCHIVE_PATH_ESCAPE")
    return target


def object_path(root: Path, digest: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("INVALID_OBJECT_DIGEST")
    return safe_child(root, f"objects/{digest[:2]}/{digest}")


def raw_path_fields(raw: bytes) -> dict:
    return {"path": raw.decode("utf-8", "backslashreplace"),
            "path_bytes_b64": base64.b64encode(raw).decode("ascii")}


def put_stream(root: Path, stream: BinaryIO, expected_size: int | None = None) -> dict:
    """Bounded RAM, no per-file cap. Atomic CAS object publication."""
    tmpdir = safe_child(root, "temporary")
    tmpdir.mkdir(exist_ok=True)
    fd, name = tempfile.mkstemp(dir=tmpdir, prefix="object-")
    tmp = Path(name)
    h, n, utf8 = hashlib.sha256(), 0, True
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    prefix = bytearray()
    try:
        with os.fdopen(fd, "wb") as out:
            for block in iter(lambda: stream.read(BLOCK), b""):
                out.write(block)
                h.update(block)
                n += len(block)
                if len(prefix) < 200:
                    prefix.extend(block[:200 - len(prefix)])
                if utf8:
                    try:
                        decoder.decode(block)
                        if b"\x00" in block:
                            utf8 = False
                    except UnicodeDecodeError:
                        utf8 = False
            out.flush()
            os.fsync(out.fileno())
        if utf8:
            try:
                decoder.decode(b"", final=True)
            except UnicodeDecodeError:
                utf8 = False
        if expected_size is not None and expected_size != n:
            raise ValueError("SOURCE_SIZE_CHANGED")
        digest = h.hexdigest()
        target = object_path(root, digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and hash_file(target) == digest:
            tmp.unlink()
        else:
            os.replace(tmp, target)
        return {"sha256": digest, "size": n, "utf8_text": utf8,
                "object": target.relative_to(root).as_posix(),
                "lfs_pointer": bytes(prefix).startswith(b"version https://git-lfs.github.com/spec/v1\n")}
    finally:
        tmp.unlink(missing_ok=True)


def check_output(source: Path, out: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("SOURCE_MUST_BE_A_REGULAR_DIRECTORY")
    if out.resolve() == source.resolve() or out.resolve().is_relative_to(source.resolve()):
        raise ValueError("OUTPUT_MUST_BE_OUTSIDE_SOURCE")
    # Stop following existing directory symlinks in output ancestry.
    for p in [out, *out.parents]:
        if p.is_symlink():
            raise ValueError("OUTPUT_SYMLINK_BLOCKED")
    out.mkdir(parents=True, exist_ok=True)


def folder_entries(source: Path) -> Iterator[tuple[dict, Path | None]]:
    """Enumerate every directory entry, including dotfiles. Do not follow links."""
    pending = [source]
    while pending:
        parent = pending.pop()
        try:
            with os.scandir(parent) as listing:
                for e in listing:
                    p = Path(e.path)
                    rel = os.fsencode(os.path.relpath(p, source))
                    if os.sep == "\\":
                        rel = rel.replace(b"\\", b"/")
                    row = raw_path_fields(rel)
                    try:
                        s = e.stat(follow_symlinks=False)
                        row.update(mode=oct(stat.S_IMODE(s.st_mode)))
                        reparse = bool(getattr(s, "st_file_attributes", 0) & 0x400)
                        if stat.S_ISLNK(s.st_mode) or reparse:
                            row.update(kind="link", status="METADATA_ONLY", reason="LINK_NOT_FOLLOWED")
                            try:
                                target = os.readlink(p)
                                row["target_bytes_b64"] = base64.b64encode(os.fsencode(target)).decode("ascii")
                            except OSError as ex:
                                row["target_read_error"] = str(ex)
                            yield row, None
                        elif stat.S_ISDIR(s.st_mode):
                            row.update(kind="directory", status="METADATA_ONLY")
                            yield row, None
                            pending.append(p)
                        elif stat.S_ISREG(s.st_mode):
                            row.update(kind="file", status="PENDING")
                            yield row, p
                        else:
                            row.update(kind="special", status="METADATA_ONLY", reason="SPECIAL_FILE_NOT_READ")
                            yield row, None
                    except OSError as ex:
                        row.update(kind="unknown", status="ERROR", reason=str(ex))
                        yield row, None
        except OSError as ex:
            rel = os.fsencode(os.path.relpath(parent, source))
            yield {**raw_path_fields(rel), "kind": "directory", "status": "ERROR",
                   "reason": "ENUMERATION_FAILED: " + str(ex)}, None


def git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in
           {"PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME"}}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    return env


def git_args(source: Path, *args: str) -> list[str]:
    return ["git", "-c", "core.fsmonitor=false", "-C", str(source), *args]


def nul_records(stream: BinaryIO) -> Iterator[bytes]:
    pending = b""
    for block in iter(lambda: stream.read(65536), b""):
        pending += block
        parts = pending.split(b"\0")
        yield from parts[:-1]
        pending = parts[-1]
    if pending:
        raise ValueError("INCOMPLETE_GIT_TREE_RECORD")


def git_entries(source: Path, commit: str) -> Iterator[dict]:
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(git_args(source, "ls-tree", "-r", "-t", "-l", "-z", "--full-tree", commit),
                                stdout=subprocess.PIPE, stderr=err, env=git_env(), shell=False)
        try:
            assert proc.stdout is not None
            for record in nul_records(proc.stdout):
                meta, raw_path = record.split(b"\t", 1)
                mode, kind, oid, size = meta.split()
                yield {**raw_path_fields(raw_path), "mode": mode.decode(),
                       "git_kind": kind.decode(), "git_oid": oid.decode(),
                       "git_size": int(size) if size != b"-" else None}
            if proc.wait() != 0:
                raise ValueError("GIT_TREE_ENUMERATION_FAILED")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if proc.stdout is not None:
                proc.stdout.close()


def manifest_rows(out: Path) -> Iterator[dict]:
    with (out / "manifest.jsonl").open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def collect(source: Path, out: Path, git_ref: str | None = None) -> dict:
    source, out = source.absolute(), out.absolute()
    check_output(source, out)
    # Exclusive writer; stale lock deliberately requires operator reconciliation.
    lock = out / ".writer.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    started = time.time()
    commit = None
    counts = {"entries": 0, "stored_files": 0, "bytes": 0, "errors": 0,
              "metadata_only": 0, "possible_secret_names": 0, "lfs_pointers": 0}
    manifest_tmp = out / "manifest.pending.jsonl"
    try:
        if git_ref is not None:
            if git_ref != "HEAD" and not re.fullmatch(r"[0-9a-fA-F]{40}", git_ref):
                raise ValueError("REF_MUST_BE_HEAD_OR_FULL_SHA")
            commit = subprocess.check_output(git_args(source, "rev-parse", "--verify", "--end-of-options", git_ref + "^{commit}"),
                                             env=git_env(), timeout=30).decode().strip()
        dump(out / "in_progress.json", {"schema": SCHEMA, "source": str(source), "started": started,
                                        "state": "SCANNING", "commit": commit})
        with manifest_tmp.open("w", encoding="utf-8", newline="\n") as manifest:
            def emit(row: dict) -> None:
                row["ordinal"] = counts["entries"]
                row["possible_secret_name"] = bool(SECRET_NAME.search(row["path"]))
                counts["entries"] += 1
                counts["possible_secret_names"] += int(row["possible_secret_name"])
                if row["status"] == "STORED":
                    counts["stored_files"] += 1
                    counts["bytes"] += row["size"]
                    counts["lfs_pointers"] += int(row["lfs_pointer"])
                elif row["status"] == "ERROR":
                    counts["errors"] += 1
                else:
                    counts["metadata_only"] += 1
                manifest.write(js(row) + "\n")
                if counts["entries"] % 100 == 0:
                    manifest.flush()
                    print(js({"progress": counts}), flush=True)
            if commit:
                for row in git_entries(source, commit):
                    if row["git_kind"] != "blob":
                        row.update(kind="directory" if row["git_kind"] == "tree" else "submodule",
                                   status="METADATA_ONLY", reason="GIT_TREE_OR_GITLINK_ONLY")
                    else:
                        row["kind"] = "git_symlink_blob" if row["mode"] == "120000" else "file"
                        try:
                            with tempfile.TemporaryFile() as err:
                                proc = subprocess.Popen(git_args(source, "cat-file", "blob", row["git_oid"]),
                                                        stdout=subprocess.PIPE, stderr=err, env=git_env(), shell=False)
                                try:
                                    assert proc.stdout is not None
                                    stored = put_stream(out, proc.stdout, row["git_size"])
                                    if proc.wait() != 0:
                                        raise ValueError("GIT_BLOB_READ_FAILED")
                                    row.update(stored, status="STORED")
                                finally:
                                    if proc.poll() is None:
                                        proc.kill(); proc.wait()
                                    if proc.stdout is not None:
                                        proc.stdout.close()
                        except (OSError, ValueError) as ex:
                            row.update(status="ERROR", reason=str(ex))
                    emit(row)
            else:
                for row, p in folder_entries(source):
                    if p is not None:
                        try:
                            before = p.lstat()
                            # O_NOFOLLOW protects POSIX final component; ancestor races need a filesystem snapshot.
                            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
                            fno = os.open(p, flags)
                            with os.fdopen(fno, "rb") as stream:
                                opened = os.fstat(stream.fileno())
                                if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                                    raise ValueError("SOURCE_REPLACED_DURING_OPEN")
                                stored = put_stream(out, stream, before.st_size)
                                after_fd = os.fstat(stream.fileno())
                            after = p.lstat()
                            identity = lambda s: (s.st_size, s.st_mtime_ns, s.st_ino, s.st_dev)
                            if identity(before) != identity(after) or identity(before) != identity(after_fd):
                                raise ValueError("SOURCE_CHANGED_DURING_READ")
                            row.update(stored, status="STORED", mtime_ns=before.st_mtime_ns)
                        except (OSError, ValueError) as ex:
                            row.update(status="ERROR", reason=str(ex))
                    emit(row)
            manifest.flush(); os.fsync(manifest.fileno())
        os.replace(manifest_tmp, out / "manifest.jsonl")
        receipt = {"schema": SCHEMA, "state": "COMPLETE" if counts["errors"] == 0 else "INCOMPLETE",
                   "source": str(source), "scope": "PINNED_GIT_TREE" if commit else "FOLDER_NONATOMIC",
                   "commit": commit, "counts": counts, "manifest_sha256": hash_file(out / "manifest.jsonl"),
                   "started": started, "finished": time.time(), "share_state": "PRIVATE_UNREVIEWED",
                   "semantic_review_complete": False, "external_link_targets_included": False,
                   "lfs_payloads_resolved": False, "submodule_contents_included": False,
                   "git_history_included": False, "browser_or_chat_account_access": False,
                   "resume_semantics": "Fresh enumeration; reuse verified content-addressed originals. Not a frozen live-folder snapshot."}
        dump(out / "receipt.json", receipt)
        (out / "in_progress.json").unlink(missing_ok=True)
        return receipt
    except BaseException as ex:
        dump(out / "in_progress.json", {"schema": SCHEMA, "state": "INTERRUPTED", "commit": commit,
                                        "error_type": type(ex).__name__, "counts_so_far": counts})
        raise
    finally:
        lock.unlink(missing_ok=True)


def verify(out: Path) -> dict:
    errors = []
    receipt = json.loads((out / "receipt.json").read_text(encoding="utf-8"))
    if (out / "in_progress.json").exists():
        errors.append("UNFINISHED_NEW_SCAN")
    if hash_file(out / "manifest.jsonl") != receipt["manifest_sha256"]:
        errors.append("MANIFEST_DIGEST_MISMATCH")
    entries = 0
    for row in manifest_rows(out):
        if row.get("ordinal") != entries:
            errors.append("ORDINAL_SEQUENCE_MISMATCH")
        entries += 1
        if row["status"] == "ERROR":
            errors.append("SOURCE_ERROR:" + row["path"])
        if row["status"] != "STORED":
            continue
        try:
            obj = object_path(out, row["sha256"])
            if row["object"] != obj.relative_to(out).as_posix():
                raise ValueError("OBJECT_REFERENCE_MISMATCH")
            if obj.stat().st_size != row["size"] or hash_file(obj) != row["sha256"]:
                errors.append("OBJECT_MISMATCH:" + row["path"])
        except (OSError, ValueError) as ex:
            errors.append("OBJECT_ERROR:" + row["path"] + ":" + str(ex))
    if entries != receipt["counts"]["entries"]:
        errors.append("ENTRY_COUNT_MISMATCH")
    return {"schema": "occ.archive-verification.v1", "state": "VERIFIED" if not errors else "FAILED",
            "entries_checked": entries, "errors": errors,
            "authenticity_note": "Hashes detect integrity changes; this is not a signed proof of source authenticity."}


def text_fragments(path: Path, block_bytes: int) -> Iterator[bytes]:
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    produced = False
    with path.open("rb") as f:
        for raw in iter(lambda: f.read(block_bytes), b""):
            text = decoder.decode(raw)
            if text:
                produced = True
                yield text.encode("utf-8")
        final = decoder.decode(b"", final=True)
        if final:
            produced = True
            yield final.encode("utf-8")
    if not produced:
        yield b""


def export_text(out: Path, dest: Path, chunk_bytes: int = 262144) -> dict:
    if chunk_bytes < 4:
        raise ValueError("CHUNK_BYTES_MUST_BE_AT_LEAST_FOUR")
    checked = verify(out)
    if checked["state"] != "VERIFIED":
        raise ValueError("ARCHIVE_MUST_VERIFY_BEFORE_EXPORT")
    dest = dest.absolute()
    if dest.exists() and any(dest.iterdir()):
        raise ValueError("EXPORT_DIRECTORY_MUST_BE_NEW_OR_EMPTY")
    dest.mkdir(parents=True, exist_ok=True)
    n, text_files, binary_files, text_bytes = 0, 0, 0, 0
    with (dest / "chunks.jsonl").open("w", encoding="utf-8") as index, \
         (dest / "coverage.jsonl").open("w", encoding="utf-8") as coverage, \
         (dest / "ALL_TEXT.txt").open("wb") as all_text:
        for row in manifest_rows(out):
            if row["status"] != "STORED" or not row["utf8_text"]:
                coverage.write(js({"ordinal": row["ordinal"], "path": row["path"],
                                   "text_status": "METADATA_ONLY" if row["status"] != "STORED" else "RAW_BINARY_OR_NON_UTF8_PRESERVED",
                                   "sha256": row.get("sha256")}) + "\n")
                binary_files += int(row["status"] == "STORED")
                continue
            text_files += 1
            offset, line = 0, 1
            for raw in text_fragments(object_path(out, row["sha256"]), chunk_bytes):
                n += 1
                name = f"part-{n:07d}.txt"
                fragment = {"source_ordinal": row["ordinal"], "path": row["path"],
                            "path_bytes_b64": row["path_bytes_b64"], "source_sha256": row["sha256"],
                            "source_byte_start": offset, "source_byte_end": offset + len(raw),
                            "start_line": line, "end_line": line + raw.count(b"\n"),
                            "chunk_sha256": hashlib.sha256(raw).hexdigest(), "file": name}
                header = ("\n===== SOURCE FRAGMENT " + js(fragment) + " =====\n").encode("utf-8")
                fragment["payload_byte_start"] = len(header)
                fragment["payload_bytes"] = len(raw)
                with (dest / name).open("wb") as f:
                    f.write(header); f.write(raw); f.write(b"\n===== END FRAGMENT =====\n")
                all_text.write(header); all_text.write(raw); all_text.write(b"\n===== END FRAGMENT =====\n")
                index.write(js(fragment) + "\n")
                offset += len(raw); line += raw.count(b"\n"); text_bytes += len(raw)
            coverage.write(js({"ordinal": row["ordinal"], "path": row["path"], "text_status": "FULL_UTF8",
                               "sha256": row["sha256"], "bytes": offset}) + "\n")
    result = {"schema": "occ.full-text-export.v1", "parts": n, "text_files": text_files,
              "non_utf8_or_binary_files": binary_files, "text_bytes": text_bytes,
              "source_manifest_sha256": hash_file(out / "manifest.jsonl"),
              "chunks_sha256": hash_file(dest / "chunks.jsonl"),
              "all_text_sha256": hash_file(dest / "ALL_TEXT.txt"),
              "silent_truncation": False, "token_count": None,
              "note": "Byte-sized presentation fragments, NOT token-sized model prompts. Binary originals remain in source archive."}
    dump(dest / "export_receipt.json", result)
    return result


def verify_text(out: Path, dest: Path) -> dict:
    expected = {r["ordinal"]: r for r in manifest_rows(out) if r["status"] == "STORED" and r["utf8_text"]}
    progress: dict[int, tuple[object, int]] = {}
    errors = []
    if verify(out)["state"] != "VERIFIED":
        errors.append("SOURCE_ARCHIVE_NOT_VERIFIED")
    receipt = json.loads((dest / "export_receipt.json").read_text())
    if hash_file(out / "manifest.jsonl") != receipt["source_manifest_sha256"]:
        errors.append("SOURCE_MANIFEST_CHANGED")
    if hash_file(dest / "chunks.jsonl") != receipt["chunks_sha256"]:
        errors.append("CHUNKS_INDEX_CHANGED")
    if hash_file(dest / "ALL_TEXT.txt") != receipt["all_text_sha256"]:
        errors.append("ALL_TEXT_CHANGED")
    with (dest / "chunks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            ordinal = item["source_ordinal"]
            if ordinal not in expected:
                errors.append("UNEXPECTED_SOURCE"); continue
            if item["path_bytes_b64"] != expected[ordinal]["path_bytes_b64"] or item["source_sha256"] != expected[ordinal]["sha256"]:
                errors.append("FRAGMENT_SOURCE_BINDING_MISMATCH")
            h, offset = progress.setdefault(ordinal, (hashlib.sha256(), 0))
            if offset != item["source_byte_start"]:
                errors.append("GAP_OR_OVERLAP")
            with safe_child(dest, item["file"]).open("rb") as part:
                part.seek(item["payload_byte_start"])
                raw = part.read(item["payload_bytes"])
            if len(raw) != item["payload_bytes"] or hashlib.sha256(raw).hexdigest() != item["chunk_sha256"]:
                errors.append("FRAGMENT_MISMATCH")
            h.update(raw)
            progress[ordinal] = (h, offset + len(raw))
    for ordinal, row in expected.items():
        h, n = progress.get(ordinal, (hashlib.sha256(), -1))
        if n != row["size"] or h.hexdigest() != row["sha256"]:
            errors.append("SOURCE_RECONSTRUCTION_MISMATCH:" + row["path"])
    return {"state": "VERIFIED" if not errors else "FAILED", "text_files_reconstructed": len(expected), "errors": errors}


def catalog(out: Path, dest: Path) -> dict:
    """Static inventory only. Signals are not confirmed bugs; never import code."""
    if verify(out)["state"] != "VERIFIED":
        raise ValueError("ARCHIVE_NOT_VERIFIED")
    dest.mkdir(parents=True, exist_ok=True)
    counts = {"python_files": 0, "symbols": 0, "command_candidates": 0, "signals": 0, "parse_errors": 0}
    with (dest / "symbols.jsonl").open("w", encoding="utf-8") as symbols, \
         (dest / "commands.jsonl").open("w", encoding="utf-8") as commands, \
         (dest / "signals.jsonl").open("w", encoding="utf-8") as signals:
        def signal(row: dict, kind: str, line: int, detail: str) -> None:
            counts["signals"] += 1
            signals.write(js({"path": row["path"], "sha256": row["sha256"], "line": line,
                              "kind": kind, "detail": detail, "verdict": "REVIEW_REQUIRED_NOT_PROVEN_BUG"}) + "\n")
        for row in manifest_rows(out):
            if row["status"] != "STORED" or not row["utf8_text"]:
                continue
            path = row["path"]
            if not (path.endswith(".py") or path.rsplit("/", 1)[-1] == "package.json"):
                continue
            raw = object_path(out, row["sha256"]).read_bytes()
            try:
                if path.endswith(".py"):
                    counts["python_files"] += 1
                    tree = ast.parse(raw, filename=path)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            counts["symbols"] += 1
                            symbols.write(js({"path": path, "sha256": row["sha256"], "name": node.name,
                                              "kind": type(node).__name__, "line": node.lineno,
                                              "end_line": getattr(node, "end_lineno", node.lineno)}) + "\n")
                        if isinstance(node, ast.ExceptHandler) and node.type is None:
                            signal(row, "BARE_EXCEPT", node.lineno, "May intentionally catch BaseException; inspect scope.")
                        if isinstance(node, ast.ExceptHandler) and node.body and all(isinstance(x, ast.Pass) for x in node.body):
                            signal(row, "EXCEPTION_PASS", node.lineno, "Swallowed exception; evidence and intended fallback required.")
                        if isinstance(node, ast.Call):
                            fname = ast.unparse(node.func)
                            if fname in {"eval", "exec"}:
                                signal(row, "DYNAMIC_EVAL", node.lineno, "Inspect trust boundary; static presence alone is not an exploit.")
                            if any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords):
                                signal(row, "SHELL_TRUE", node.lineno, "Trace command provenance and input escaping.")
                            if fname.endswith(".add_argument"):
                                counts["command_candidates"] += 1
                                commands.write(js({"path": path, "sha256": row["sha256"], "line": node.lineno,
                                                   "kind": "argparse_definition", "expression": ast.unparse(node),
                                                   "execution_status": "NOT_AUTHORIZED_NOT_RUN"}) + "\n")
                    for number, text in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
                        if re.search(r"\b(TODO|FIXME|HACK)\b", text):
                            signal(row, "COMMENT_MARKER", number, text.strip())
                else:
                    value = json.loads(raw)
                    for name, command in value.get("scripts", {}).items():
                        counts["command_candidates"] += 1
                        commands.write(js({"path": path, "sha256": row["sha256"], "kind": "package_script",
                                           "name": name, "command": command, "execution_status": "NOT_AUTHORIZED_NOT_RUN"}) + "\n")
            except (ValueError, SyntaxError, UnicodeError, MemoryError, RecursionError) as ex:
                counts["parse_errors"] += 1
                signal(row, "PARSER_ERROR", 0, type(ex).__name__ + ": " + str(ex))
    result = {"schema": "occ.static-catalog.v1", **counts, "exhaustive_runtime_command_discovery": False,
              "supported": ["Python AST symbols and argparse definitions", "package.json scripts"],
              "not_implemented": ["runtime plugins", "complete call graph", "Click/Typer command resolution", "shell/Makefile/CI semantic analysis"],
              "source_code_executed": False}
    dump(dest / "catalog_receipt.json", result)
    return result


def chats(source: Path, out: Path) -> dict:
    """Preserve full source JSON plus EVERY mapping node, including inactive branches.

JSON parsing is in-memory; a MemoryError leaves original.json intact and no COMPLETE
receipt. It is not a zero-memory streaming parser. No attachment bytes are invented.
"""
    if out.resolve() == source.resolve() or source.resolve().is_relative_to(out.resolve()):
        raise ValueError("CHAT_OUTPUT_MUST_NOT_CONTAIN_INPUT")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("CHAT_OUTPUT_MUST_BE_EMPTY")
    shutil.copyfile(source, out / "original.json")
    digest = hash_file(out / "original.json")
    dump(out / "import_status.json", {"state": "RAW_PRESERVED_PARSING_PENDING", "sha256": digest})
    with (out / "original.json").open(encoding="utf-8-sig") as f:
        def no_duplicates(pairs):
            result = {}
            for key, val in pairs:
                if key in result:
                    raise ValueError("DUPLICATE_JSON_KEY_RAW_PRESERVED")
                result[key] = val
            return result
        value = json.load(f, object_pairs_hook=no_duplicates)
    conversations = value if isinstance(value, list) else value.get("conversations", [value])
    total = 0
    with (out / "nodes.jsonl").open("w", encoding="utf-8") as nodes, \
         (out / "conversations.jsonl").open("w", encoding="utf-8") as metadata:
        for ordinal, conversation in enumerate(conversations):
            if not isinstance(conversation, dict):
                raise ValueError("CONVERSATION_OBJECT_REQUIRED")
            mapping = conversation.get("mapping")
            if not isinstance(mapping, dict):
                raise ValueError("UNSUPPORTED_EXPORT_SHAPE_RAW_IS_PRESERVED")
            metadata.write(js({"ordinal": ordinal, "metadata": {k: v for k, v in conversation.items() if k != "mapping"}}) + "\n")
            for node_id, node in mapping.items():
                nodes.write(js({"conversation_ordinal": ordinal, "conversation_id": conversation.get("id"),
                                "node_id": node_id, "node": node}) + "\n")
                total += 1
    result = {"schema": "occ.chat-import.v1", "state": "COMPLETE", "conversations": len(conversations),
              "nodes": total, "original_sha256": digest, "all_mapping_branches_preserved": True,
              "remote_or_missing_attachment_bytes_fetched": False, "account_history_completeness_known": False}
    dump(out / "import_status.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for mode in ("folder", "git"):
        p = sub.add_parser(mode)
        p.add_argument("--source", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        if mode == "git":
            p.add_argument("--ref", default="HEAD")
    for mode in ("verify", "text", "verify-text", "catalog"):
        p = sub.add_parser(mode)
        p.add_argument("--archive", type=Path, required=True)
        if mode != "verify":
            p.add_argument("--out", type=Path, required=True)
        if mode == "text":
            p.add_argument("--chunk-bytes", type=int, default=262144)
    p = sub.add_parser("chats")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    try:
        if a.command in {"folder", "git"}:
            result = collect(a.source, a.out, a.ref if a.command == "git" else None)
        elif a.command == "verify": result = verify(a.archive)
        elif a.command == "text": result = export_text(a.archive, a.out, a.chunk_bytes)
        elif a.command == "verify-text": result = verify_text(a.archive, a.out)
        elif a.command == "catalog": result = catalog(a.archive, a.out)
        else: result = chats(a.input, a.out)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("state") not in {"FAILED", "INCOMPLETE"} else 3
    except (OSError, ValueError, subprocess.SubprocessError, KeyError) as ex:
        print(js({"state": "ERROR", "error": type(ex).__name__, "detail": str(ex)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
