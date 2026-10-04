#!/usr/bin/env python3
"""Local-only intake staging, NOT a bot runtime, canonical journal or AI agent.

Python 3.10+. No network, shell, model, wallet or transaction functions.
Only files explicitly placed in workspace/inbox and an optional --repo are read.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import random
import sqlite3
import stat
import sys
from datetime import datetime, timezone
import zipfile
import xml.etree.ElementTree as ET

from content_lab import _database

MAX_FILE = 4 * 1024 * 1024
MAX_SCAN = 2000
MAX_CHANGED = 8
MAX_TOTAL = 36 * 1024 * 1024
TEXT = {'.txt', '.md', '.json', '.jsonl', '.srt', '.vtt', '.csv', '.py',
        '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.yaml', '.yml'}
IMAGES = {'.png', '.jpg', '.jpeg', '.webp'}
AUDIO = {'.mp3', '.wav', '.m4a', '.ogg', '.opus', '.mp4'}
ALLOWED = TEXT | IMAGES | AUDIO | {'.docx', '.pdf', '.html'}
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist', 'build', '.ssh', '.aws'}
TOPICS = {
    'occ': ('occ', 'agent relay', 'context aggregator'),
    'voice': ('voice', 'голос', 'transcrib', 'расшифров'),
    'laya': ('laya', 'convai'),
    'solana': ('solana', 'jito', 'jupiter', 'flashloan'),
    'qualification': ('qualification', 'квалификац', 'paper', 'replay'),
    'development': ('pull request', 'pytest', 'tech debt', 'техдолг'),
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def excluded(path: Path) -> bool:
    """Deny common credentials and local link/reparse points; not a secret scanner."""
    name = path.name.lower()
    if name.startswith('.') or any(x in name for x in ('secret', 'credential', 'wallet', 'id_rsa', 'private_key', 'session')):
        return True
    try:
        st = path.lstat()
        return path.is_symlink() or bool(getattr(st, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024))
    except OSError:
        return True


def enumerate_files(root: Path) -> tuple[list[Path], bool]:
    files: list[Path] = []
    visited = 0
    for current, dirs, names in os.walk(root, followlinks=False):
        visited += len(dirs)
        if visited > MAX_SCAN:
            return files, True
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not excluded(Path(current) / d))
        for name in sorted(names):
            visited += 1
            if visited > MAX_SCAN:
                return files, True
            path = Path(current) / name
            if excluded(path) or path.suffix.lower() not in ALLOWED:
                continue
            try:
                path.resolve().relative_to(root)
            except (ValueError, OSError):
                continue
            if path.is_file():
                files.append(path)
    return files, False


def text_from_file(path: Path, data: bytes) -> tuple[str | None, str]:
    suffix = path.suffix.lower()
    if suffix in IMAGES:
        return None, 'NEEDS_VISION'
    if suffix in AUDIO:
        return None, 'NEEDS_TRANSCRIPTION'
    if suffix in {'.pdf', '.html'}:
        return None, 'NEEDS_DOCUMENT_PARSER'
    if suffix == '.docx':
        try:
            from io import BytesIO
            with zipfile.ZipFile(BytesIO(data)) as archive:
                info = archive.getinfo('word/document.xml')
                if info.file_size > MAX_FILE:
                    return None, 'DOCUMENT_XML_TOO_LARGE'
                xml = archive.read(info)
                if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
                    return None, 'UNSAFE_XML_REJECTED'
                tree = ET.fromstring(xml)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                return '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in tree.findall('.//w:p', ns)), 'TEXT_EXTRACTED_MAIN_BODY_ONLY'
        except (zipfile.BadZipFile, KeyError, ET.ParseError, RuntimeError, OSError):
            return None, 'DOCUMENT_PARSE_ERROR'
    try:
        return data.decode('utf-8-sig'), 'TEXT_EXTRACTED'
    except UnicodeDecodeError:
        return None, 'NEEDS_ENCODING_REVIEW'


def python_summary(text: str) -> dict:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return {'status': 'AST_PARSE_FAILED'}
    counts = {'functions': 0, 'classes': 0, 'bare_except': 0, 'eval_exec_calls': 0}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            counts['functions'] += 1
        elif isinstance(node, ast.ClassDef):
            counts['classes'] += 1
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            counts['bare_except'] += 1
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'eval', 'exec'}:
            counts['eval_exec_calls'] += 1
    return {'status': 'STATIC_HEURISTICS_ONLY', **counts, 'bug_proven': False}


def inspect(path: Path, root: Path, label: str) -> dict:
    before = path.stat()
    if before.st_size > MAX_FILE:
        return {'source': label, 'path': path.relative_to(root).as_posix(), 'status': 'FILE_TOO_LARGE', 'bytes': before.st_size}
    if excluded(path):
        raise ValueError('LINK_OR_PROTECTED_FILE')
    path.resolve().relative_to(root)
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE + 1)
    after = path.stat()
    if len(data) > MAX_FILE or (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise ValueError('FILE_CHANGED_DURING_READ')
    text, status = text_from_file(path, data)
    lower = text.lower() if text is not None else ''
    out = {
        'source': label, 'path': path.relative_to(root).as_posix(),
        'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
        'mtime_ns': after.st_mtime_ns, 'status': status,
        'topics': [topic for topic, terms in TOPICS.items() if any(t in lower for t in terms)],
        'text_characters': len(text) if text is not None else None,
        'raw_text_persisted': False, 'source_instructions_executed': False,
    }
    if path.suffix.lower() == '.py' and text is not None:
        out['python'] = python_summary(text)
    return out


def validate_workspace(workspace: Path) -> Path:
    workspace = workspace.expanduser().absolute()
    for path in (workspace, *workspace.parents):
        if path.is_symlink() or (path.exists() and excluded_link(path)):
            raise ValueError('WORKSPACE_LINK_REJECTED')
    for name in ('inbox', 'reports', 'content.sqlite3', 'content.sqlite3-wal',
                 'content.sqlite3-shm', 'PAUSED'):
        path = workspace / name
        if path.is_symlink() or (path.exists() and excluded_link(path)):
            raise ValueError('WORKSPACE_LINK_REJECTED')
    if (workspace / 'reports' / 'latest.json').is_symlink() or (workspace / 'reports' / 'latest.md').is_symlink():
        raise ValueError('REPORT_LINK_REJECTED')
    return workspace.resolve()


def excluded_link(path: Path) -> bool:
    st = path.lstat()
    return bool(getattr(st, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024))


def initialize(workspace: Path) -> None:
    workspace = validate_workspace(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / 'inbox').mkdir(exist_ok=True)
    (workspace / 'reports').mkdir(exist_ok=True)
    db = _database(workspace)
    db.execute('CREATE TABLE IF NOT EXISTS occ_intake_items (key TEXT PRIMARY KEY, source TEXT NOT NULL, relpath TEXT NOT NULL, mtime INTEGER NOT NULL, size INTEGER NOT NULL, sha TEXT, observed TEXT NOT NULL, record TEXT NOT NULL)')
    db.commit()
    db.close()


def run_once(workspace: Path, repo: Path | None = None) -> dict:
    workspace = validate_workspace(workspace)
    roots = [('inbox', workspace / 'inbox')]
    if repo is not None:
        repo = repo.expanduser().absolute()
        if any(p.is_symlink() or (p.exists() and excluded_link(p)) for p in (repo, *repo.parents)):
            raise ValueError('REPOSITORY_LINK_REJECTED')
        repo = repo.resolve()
        if not repo.is_dir():
            raise ValueError('REPOSITORY_DIRECTORY_NOT_FOUND')
        if workspace == repo or workspace.is_relative_to(repo) or repo.is_relative_to(workspace):
            raise ValueError('WORKSPACE_AND_REPO_MUST_NOT_OVERLAP')
        roots.append(('repo', repo))
    initialize(workspace)
    if (workspace / 'PAUSED').exists():
        return {'status': 'PAUSED', 'time': utcnow(), 'execution_performed': False}
    db = _database(workspace)
    try:
        db.execute('BEGIN IMMEDIATE')  # one local intake writer; not a trading lock
        old = {r[0]: r for r in db.execute('SELECT key,source,relpath,mtime,size,sha,observed,record FROM occ_intake_items')}
        candidates = []
        coverage = []
        for label, root in roots:
            paths, partial = enumerate_files(root)
            coverage.append({'source': label, 'discovered': len(paths), 'scan_truncated': partial})
            for path in paths:
                st = path.stat()
                key = str(path)
                prior = old.get(key)
                if prior is None or (st.st_mtime_ns, st.st_size) != (prior[3], prior[4]):
                    candidates.append((0 if prior is None else 1, st.st_mtime_ns, key, label, root, path))
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))
        items, errors = [], []
        bytes_read = 0
        for _, _, key, label, root, path in candidates[:MAX_CHANGED]:
            if bytes_read + min(path.stat().st_size, MAX_FILE) > MAX_TOTAL:
                break
            try:
                rec = inspect(path, root, label)
                bytes_read += min(rec['bytes'], MAX_FILE)
                prior = old.get(key)
                duplicate = db.execute('SELECT source,relpath FROM occ_intake_items WHERE sha = ? AND key != ? LIMIT 1', (rec.get('sha256'), key)).fetchone()
                if duplicate:
                    rec['duplicate_of'] = {'source': duplicate[0], 'path': duplicate[1]}
                st = path.stat()
                if 'mtime_ns' in rec and (st.st_mtime_ns, st.st_size) != (rec['mtime_ns'], rec['bytes']):
                    raise ValueError('FILE_CHANGED_BEFORE_INDEX_COMMIT')
                db.execute('INSERT OR REPLACE INTO occ_intake_items VALUES (?,?,?,?,?,?,?,?)', (key, label, rec['path'], st.st_mtime_ns, st.st_size, rec.get('sha256'), utcnow(), json.dumps(rec, ensure_ascii=False)))
                if prior is None or rec.get('sha256') is None or rec.get('sha256') != prior[5]:
                    items.append(rec)
            except (ValueError, OSError) as exc:
                errors.append({'source': label, 'path': path.relative_to(root).as_posix(), 'status': type(exc).__name__})
        # One old item from the *known* index; never pretend uniform selection over all Library.
        random_review = None
        pool = sorted(old)
        if pool:
            seed = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H')
            chosen = random.Random(seed).choice(pool)
            row = old[chosen]
            roots_by_label = dict(roots)
            root = roots_by_label.get(row[1])
            path = Path(chosen)
            try:
                if root is not None and path.is_file() and not excluded(path):
                    path.resolve().relative_to(root)
                    st = path.stat()
                    if (st.st_mtime_ns, st.st_size) == (row[3], row[4]):
                        random_review = inspect(path, root, row[1])
            except (OSError, ValueError):
                pass
        result = {
            'schema_version': 'occ-intake-report.v1', 'authority': 'DATA_ONLY',
            'action_authority': False, 'dispatch_allowed': False, 'status': 'LOCAL_INTAKE_COMPLETE',
            'observed_at': utcnow(), 'scope': 'EXPLICIT_LOCAL_STAGING_ONLY',
            'coverage': coverage, 'new_or_changed': items, 'random_old_review': random_review,
            'pending_candidates': max(0, len(candidates) - MAX_CHANGED), 'errors': errors,
            'external_connections_used': [], 'paid_api_calls': 0, 'market_campaign_executed': False,
            'repository_code_executed': False, 'source_commit_verified': False,
            'limits': {'max_changed': MAX_CHANGED, 'max_discovered_per_root': MAX_SCAN, 'max_file_bytes': MAX_FILE},
            'limitations': ['Metadata-triggered change detection; unchanged metadata can hide changes.',
                            'DOCX main-body paragraphs only; PDF/HTML/images/audio need separate parsers.',
                            'Filename exclusions are not complete secret detection. Do not put credentials in inbox.',
                            'Static counts and keyword tags are not semantic review or qualification.'],
        }
        db.commit()
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        report = workspace / 'reports' / f'{stamp}.json'
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        (workspace / 'reports' / 'latest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = ['# Локальный OCC intake', '', f"Время UTC: {result['observed_at']}",
                 f'Новых/изменённых файлов: {len(items)}. Ожидают: {result["pending_candidates"]}.',
                 'Это индексирование и простые статические признаки, не запуск бота или LLM.', '']
        for rec in items:
            lines.append(f'- {rec["source"]}/{rec["path"]}: {rec["status"]}; темы: {", ".join(rec.get("topics", [])) or "не определены"}.')
        if random_review:
            lines.extend(['', f'Старый материал для повторного просмотра: {random_review["source"]}/{random_review["path"]}.'])
        (workspace / 'reports' / 'latest.md').write_text('\n'.join(lines), encoding='utf-8')
        return result
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'once', 'pause', 'resume'])
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--repo', type=Path, help='Optional explicit local repo; static file reads only.')
    args = parser.parse_args()
    try:
        workspace = validate_workspace(args.workspace)
        if args.command != 'once':
            initialize(workspace)
        if args.command == 'init':
            result = {'status': 'INITIALIZED', 'workspace': str(workspace)}
        elif args.command == 'pause':
            (workspace / 'PAUSED').write_text(utcnow(), encoding='utf-8')
            result = {'status': 'PAUSED'}
        elif args.command == 'resume':
            (workspace / 'PAUSED').unlink(missing_ok=True)
            result = {'status': 'RESUMED'}
        else:
            result = run_once(workspace, args.repo)
        print(json.dumps({'status': result['status'], 'new_or_changed': len(result.get('new_or_changed', [])), 'market_campaign_executed': False}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({'status': 'BLOCKED', 'error_type': type(exc).__name__}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
