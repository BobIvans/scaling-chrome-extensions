"""Immutable local originals shared by future importers in Content Lab's SQLite owner.

Capture is deliberately separate from extraction. A complete raw object can be
referenced by many stable origins and observations without copying its bytes.
Incomplete staging rows never become current versions or search results.
"""
from __future__ import annotations

import hashlib
import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from automation_core import connection, digest, identifier, read_connection, strict_int

PART_BYTES = 64 * 1024
PAGE = 50
HEX = re.compile(r'[0-9a-f]{64}\Z')
INTENT = re.compile(r'[0-9a-f]{32}\Z')
KINDS = {'FILE', 'MEDIA'}


def _schema(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS source_origins(
        namespace TEXT NOT NULL, source_id TEXT NOT NULL, kind TEXT NOT NULL,
        source_key TEXT NOT NULL, origin TEXT NOT NULL, created REAL NOT NULL,
        PRIMARY KEY(namespace,source_id), UNIQUE(namespace,kind,source_key));
      CREATE TABLE IF NOT EXISTS source_aliases(
        namespace TEXT NOT NULL, source_id TEXT NOT NULL, origin TEXT NOT NULL,
        first_observed REAL NOT NULL, PRIMARY KEY(namespace,source_id,origin));
      CREATE TABLE IF NOT EXISTS source_raw_objects(
        namespace TEXT NOT NULL, raw_sha TEXT NOT NULL, encoding TEXT NOT NULL,
        size INTEGER NOT NULL, parts INTEGER NOT NULL, state TEXT NOT NULL,
        created REAL NOT NULL, PRIMARY KEY(namespace,raw_sha,encoding));
      CREATE TABLE IF NOT EXISTS source_raw_parts(
        namespace TEXT NOT NULL, raw_sha TEXT NOT NULL, encoding TEXT NOT NULL,
        ordinal INTEGER NOT NULL, byte_start INTEGER NOT NULL, byte_end INTEGER NOT NULL,
        part_sha TEXT NOT NULL, raw BLOB NOT NULL,
        PRIMARY KEY(namespace,raw_sha,encoding,ordinal));
      CREATE TABLE IF NOT EXISTS source_versions(
        namespace TEXT NOT NULL, source_id TEXT NOT NULL, version_id TEXT NOT NULL,
        raw_sha TEXT NOT NULL, encoding TEXT NOT NULL, scope TEXT NOT NULL,
        created REAL NOT NULL, PRIMARY KEY(namespace,version_id));
      CREATE INDEX IF NOT EXISTS source_versions_by_origin
        ON source_versions(namespace,source_id,created DESC,version_id DESC);
      CREATE TABLE IF NOT EXISTS source_observations(
        namespace TEXT NOT NULL, observation_id TEXT NOT NULL, source_id TEXT NOT NULL,
        version_id TEXT NOT NULL, intent_key TEXT NOT NULL, retrieved_at REAL NOT NULL,
        provenance TEXT NOT NULL, state TEXT NOT NULL,
        PRIMARY KEY(namespace,observation_id), UNIQUE(namespace,source_id,intent_key));
      CREATE TABLE IF NOT EXISTS source_heads(
        namespace TEXT NOT NULL, source_id TEXT NOT NULL, version_id TEXT NOT NULL,
        PRIMARY KEY(namespace,source_id));
      CREATE TABLE IF NOT EXISTS source_ledger_migrations(id INTEGER PRIMARY KEY);
    ''')
    columns = {r['name'] for r in db.execute('PRAGMA table_info(source_origins)')}
    if 'source_key' not in columns:
        with db:
            db.execute('ALTER TABLE source_origins ADD COLUMN source_key TEXT')
    if not db.execute('SELECT 1 FROM source_ledger_migrations WHERE id=1').fetchone():
        with db:
            db.execute('UPDATE source_origins SET source_key=origin WHERE source_key IS NULL')
            db.execute('''INSERT OR IGNORE INTO source_aliases
                SELECT namespace,source_id,origin,created FROM source_origins''')
            db.execute('INSERT OR IGNORE INTO source_ledger_migrations VALUES (1)')
    db.execute('CREATE UNIQUE INDEX IF NOT EXISTS source_origin_keys ON source_origins(namespace,kind,source_key)')


def _db(store):
    db = connection(store)
    try:
        _schema(db)
        return db
    except BaseException:
        db.close()
        raise


def _object(value, budget=16_000):
    if not isinstance(value, dict):
        raise ValueError('SOURCE_SCOPE_REQUIRED')
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':'))
        if len(raw.encode('utf-8')) > budget:
            raise ValueError('SOURCE_SCOPE_REQUIRED')
    except (TypeError, UnicodeError, ValueError) as exc:
        raise ValueError('SOURCE_SCOPE_REQUIRED') from exc
    return raw


def _result(db, namespace, source_id, intent_key):
    row = db.execute('''SELECT o.observation_id,o.source_id,o.version_id,o.retrieved_at,
        v.raw_sha,v.encoding,r.size,r.parts
        FROM source_observations o JOIN source_versions v
          ON v.namespace=o.namespace AND v.version_id=o.version_id
        JOIN source_raw_objects r ON r.namespace=v.namespace AND r.raw_sha=v.raw_sha
          AND r.encoding=v.encoding
        WHERE o.namespace=? AND o.source_id=? AND o.intent_key=?''',
        (namespace, source_id, intent_key)).fetchone()
    if row is None:
        return None
    if db.execute('''SELECT state FROM source_raw_objects WHERE namespace=? AND raw_sha=?
                   AND encoding=?''', (namespace, row['raw_sha'], row['encoding'])).fetchone()[0] != 'COMPLETE':
        raise ValueError('SOURCE_RAW_CORRUPT')
    return {'schema': 'occ.source-capture.v1', **dict(row), 'state': 'COMPLETE'}


def capture_file(store: Path, namespace: str, kind: str, path: Path, intent_key: str,
                 *, source_key: str | None = None, scope: dict | None = None, progress=None):
    """Resume 64 KiB stages; publish a version and observation only after EOF.

    The intent is replayable after a lost response. A different intent observing
    identical bytes adds an observation, reusing the immutable raw object.
    """
    namespace = identifier(namespace)
    if kind not in KINDS or not isinstance(intent_key, str) or not INTENT.fullmatch(intent_key):
        raise ValueError('SOURCE_CAPTURE_REQUEST_REQUIRED')
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('SOURCE_REGULAR_FILE_REQUIRED')
    if (not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents))
            or not path.is_file() or path.resolve().is_relative_to(Path(store).resolve())):
        raise ValueError('SOURCE_REGULAR_FILE_REQUIRED')
    origin = path.as_uri()
    if source_key is None:
        source_key = origin
    if (not isinstance(source_key, str) or not source_key or '\0' in source_key
            or len(source_key.encode('utf-8')) > 1000):
        raise ValueError('SOURCE_KEY_REQUIRED')
    source_id = digest([namespace, kind, source_key])
    scope_raw = _object(scope or {'representation': 'ORIGINAL'})
    db = _db(store)
    try:
        replay = _result(db, namespace, source_id, intent_key)
        if replay:
            return dict(replay, reused=True)
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('SOURCE_REGULAR_FILE_REQUIRED')
            fingerprint = (before.st_dev, before.st_ino, before.st_size,
                           before.st_mtime_ns, before.st_ctime_ns)
            hasher = hashlib.sha256()
            while block := stream.read(PART_BYTES):
                hasher.update(block)
                if progress:
                    progress()
            if fingerprint != _stat(stream):
                raise ValueError('SOURCE_DRIFT')
            raw_sha = hasher.hexdigest()
            count = (before.st_size + PART_BYTES - 1) // PART_BYTES
            version_id = digest([source_id, raw_sha, 'bytes', scope_raw])
            observation_id = digest([namespace, source_id, intent_key])
            with db:
                db.execute('INSERT OR IGNORE INTO source_raw_objects VALUES (?,?,?,?,?,?,?)',
                           (namespace, raw_sha, 'bytes', before.st_size, count, 'STAGING', time.time()))
                obj = db.execute('SELECT * FROM source_raw_objects WHERE namespace=? AND raw_sha=? AND encoding=?',
                                 (namespace, raw_sha, 'bytes')).fetchone()
                if (obj['size'], obj['parts']) != (before.st_size, count):
                    raise ValueError('SOURCE_RAW_CORRUPT')
            stream.seek(0)
            verified = hashlib.sha256()
            ordinal = 0
            while block := stream.read(PART_BYTES):
                verified.update(block)
                start = ordinal * PART_BYTES
                part_sha = hashlib.sha256(block).hexdigest()
                with db:
                    db.execute('INSERT OR IGNORE INTO source_raw_parts VALUES (?,?,?,?,?,?,?,?)',
                               (namespace, raw_sha, 'bytes', ordinal, start, start + len(block),
                                part_sha, block))
                    saved = db.execute('''SELECT byte_start,byte_end,part_sha,raw FROM source_raw_parts
                        WHERE namespace=? AND raw_sha=? AND encoding=? AND ordinal=?''',
                        (namespace, raw_sha, 'bytes', ordinal)).fetchone()
                    if ((saved['byte_start'], saved['byte_end'], saved['part_sha']) !=
                            (start, start + len(block), part_sha) or saved['raw'] != block):
                        raise ValueError('SOURCE_RAW_CORRUPT')
                ordinal += 1
                if progress:
                    progress()
            if (verified.hexdigest() != raw_sha or ordinal != count or fingerprint != _stat(stream)
                    or fingerprint != _path_stat(path)):
                raise ValueError('SOURCE_DRIFT')
            with db:
                row = db.execute('''SELECT count(*) AS n,coalesce(sum(length(raw)),0) AS size
                    FROM source_raw_parts WHERE namespace=? AND raw_sha=? AND encoding=?''',
                    (namespace, raw_sha, 'bytes')).fetchone()
                if (row['n'], row['size']) != (count, before.st_size):
                    raise ValueError('SOURCE_RAW_CORRUPT')
                db.execute('''UPDATE source_raw_objects SET state='COMPLETE'
                    WHERE namespace=? AND raw_sha=? AND encoding=?''', (namespace, raw_sha, 'bytes'))
                db.execute('''INSERT OR IGNORE INTO source_origins
                    (namespace,source_id,kind,source_key,origin,created) VALUES (?,?,?,?,?,?)''',
                           (namespace, source_id, kind, source_key, origin, time.time()))
                db.execute('INSERT OR IGNORE INTO source_aliases VALUES (?,?,?,?)',
                           (namespace, source_id, origin, time.time()))
                db.execute('INSERT OR IGNORE INTO source_versions VALUES (?,?,?,?,?,?,?)',
                           (namespace, source_id, version_id, raw_sha, 'bytes', scope_raw, time.time()))
                db.execute('INSERT INTO source_observations VALUES (?,?,?,?,?,?,?,?)',
                           (namespace, observation_id, source_id, version_id, intent_key,
                            time.time(), _object({'origin': origin, 'method': 'LOCAL_FILE'}),
                            'COMPLETE_AT_EOF'))
                db.execute('''INSERT INTO source_heads VALUES (?,?,?) ON CONFLICT(namespace,source_id)
                    DO UPDATE SET version_id=excluded.version_id''',
                    (namespace, source_id, version_id))
            return dict(_result(db, namespace, source_id, intent_key), reused=False)
    except sqlite3.IntegrityError as exc:
        # A replay with another payload must never overwrite the first intent.
        raise ValueError('SOURCE_INTENT_CONFLICT') from exc
    finally:
        db.close()


def _stat(stream):
    value = os.fstat(stream.fileno())
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _path_stat(path):
    value = path.lstat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def versions(store: Path, namespace: str, source_id: str, *, after=None, limit=20):
    identifier(namespace)
    if not isinstance(source_id, str) or not HEX.fullmatch(source_id):
        raise ValueError('SOURCE_ID_REQUIRED')
    strict_int(limit, 1, PAGE)
    if after is not None and (not isinstance(after, str) or not HEX.fullmatch(after)):
        raise ValueError('SOURCE_CURSOR_INVALID')
    db = read_connection(store)
    try:
        origin = db.execute('SELECT 1 FROM source_origins WHERE namespace=? AND source_id=?',
                            (namespace, source_id)).fetchone()
        if origin is None:
            raise ValueError('SOURCE_OUTSIDE_SCOPE')
        anchor = db.execute('SELECT created,version_id FROM source_versions WHERE namespace=? AND source_id=? AND version_id=?',
                            (namespace, source_id, after)).fetchone() if after else None
        if after and anchor is None:
            raise ValueError('SOURCE_CURSOR_INVALID')
        sql = 'SELECT version_id,raw_sha,encoding,scope,created FROM source_versions WHERE namespace=? AND source_id=?'
        args = [namespace, source_id]
        if anchor:
            sql += ' AND (created,version_id)<(?,?)'
            args.extend((anchor['created'], after))
        rows = [dict(r) for r in db.execute(sql + ' ORDER BY created DESC,version_id DESC LIMIT ?',
                                           (*args, limit + 1))]
        page = rows[:limit]
        return {'schema': 'occ.source-version-page.v1', 'source_id': source_id,
                'versions': page, 'next_cursor': page[-1]['version_id'] if len(rows) > limit else None,
                'eof': len(rows) <= limit}
    finally:
        db.close()


def raw_parts(store: Path, namespace: str, version_id: str, *, after=-1, limit=20):
    """Return bounded part metadata; callers fetch raw bytes by ordinal."""
    identifier(namespace)
    if not isinstance(version_id, str) or not HEX.fullmatch(version_id):
        raise ValueError('SOURCE_VERSION_REQUIRED')
    strict_int(after, -1, 9_007_199_254_740_991)
    strict_int(limit, 1, PAGE)
    db = read_connection(store)
    try:
        version = db.execute('''SELECT v.raw_sha,v.encoding,r.size,r.parts,r.state FROM source_versions v
            JOIN source_raw_objects r ON r.namespace=v.namespace AND r.raw_sha=v.raw_sha
              AND r.encoding=v.encoding WHERE v.namespace=? AND v.version_id=?''',
            (namespace, version_id)).fetchone()
        if version is None:
            raise ValueError('SOURCE_OUTSIDE_SCOPE')
        if version['state'] != 'COMPLETE':
            raise ValueError('SOURCE_RAW_CORRUPT')
        rows = [dict(r) for r in db.execute('''SELECT ordinal,byte_start,byte_end,part_sha
            FROM source_raw_parts WHERE namespace=? AND raw_sha=? AND encoding=? AND ordinal>?
            ORDER BY ordinal LIMIT ?''', (namespace, version['raw_sha'], version['encoding'], after,
                                          limit + 1))]
        page = rows[:limit]
        return {'schema': 'occ.source-parts-page.v1', 'version_id': version_id,
                'raw_sha': version['raw_sha'], 'size': version['size'], 'total': version['parts'],
                'parts': page, 'next_cursor': page[-1]['ordinal'] if len(rows) > limit else None,
                'eof': len(rows) <= limit}
    finally:
        db.close()


def read_part(store: Path, namespace: str, version_id: str, ordinal: int):
    strict_int(ordinal, 0, 9_007_199_254_740_991)
    page = raw_parts(store, namespace, version_id, after=ordinal - 1, limit=1)
    if not page['parts'] or page['parts'][0]['ordinal'] != ordinal:
        raise ValueError('SOURCE_PART_OUTSIDE_SCOPE')
    db = read_connection(store)
    try:
        row = db.execute('''SELECT p.raw FROM source_raw_parts p JOIN source_versions v
            ON v.namespace=p.namespace AND v.raw_sha=p.raw_sha AND v.encoding=p.encoding
            WHERE v.namespace=? AND v.version_id=? AND p.ordinal=?''',
            (namespace, version_id, ordinal)).fetchone()
        raw = row['raw']
        if hashlib.sha256(raw).hexdigest() != page['parts'][0]['part_sha']:
            raise ValueError('SOURCE_RAW_CORRUPT')
        return raw
    finally:
        db.close()


def _page_cursor(base_id, head_id, ordinal):
    raw = json.dumps([1, base_id, head_id, ordinal], separators=(',', ':')).encode('ascii')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def _read_page_cursor(value, base_id, head_id):
    if (not isinstance(value, str) or len(value) > 4096 or
            not re.fullmatch(r'[A-Za-z0-9_-]+', value)):
        raise ValueError('SOURCE_CURSOR_INVALID')
    try:
        raw = base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)
        decoded = json.loads(raw)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise ValueError('SOURCE_CURSOR_INVALID') from exc
    if (not isinstance(decoded, list) or len(decoded) != 4 or decoded[:3] !=
            [1, base_id, head_id] or type(decoded[3]) is not int or decoded[3] < 0):
        raise ValueError('SOURCE_CURSOR_INVALID')
    return decoded[3]


def delta_parts(store: Path, namespace: str, base_version_id: str,
                head_version_id: str, *, cursor=None, limit=20):
    """Exact fixed-size byte ranges, not a semantic edit or fuzzy rename diff."""
    identifier(namespace)
    if any(not isinstance(v, str) or not HEX.fullmatch(v)
           for v in (base_version_id, head_version_id)):
        raise ValueError('SOURCE_VERSION_REQUIRED')
    strict_int(limit, 1, PAGE)
    after = _read_page_cursor(cursor, base_version_id, head_version_id) if cursor else -1
    db = read_connection(store)
    try:
        versions_by_id = {}
        for version_id in (base_version_id, head_version_id):
            row = db.execute('''SELECT v.source_id,v.raw_sha,v.encoding,v.scope,r.state
                FROM source_versions v JOIN source_raw_objects r
                ON r.namespace=v.namespace AND r.raw_sha=v.raw_sha AND r.encoding=v.encoding
                WHERE v.namespace=? AND v.version_id=?''', (namespace, version_id)).fetchone()
            if row is None:
                raise ValueError('SOURCE_OUTSIDE_SCOPE')
            if row['state'] != 'COMPLETE':
                raise ValueError('SOURCE_RAW_CORRUPT')
            versions_by_id[version_id] = row
        base, head = versions_by_id[base_version_id], versions_by_id[head_version_id]
        if base['source_id'] != head['source_id'] or base['scope'] != head['scope']:
            raise ValueError('SOURCE_SCOPE_MISMATCH')
        if base['raw_sha'] == head['raw_sha']:
            return {'schema': 'occ.source-delta-page.v1', 'base_version_id': base_version_id,
                    'head_version_id': head_version_id, 'changes': [], 'next_cursor': None,
                    'eof': True, 'scope': 'FIXED_64K_BYTE_PARTS'}
        sql = '''WITH keys AS (
            SELECT ordinal FROM source_raw_parts WHERE namespace=? AND raw_sha=? AND encoding=?
            UNION SELECT ordinal FROM source_raw_parts WHERE namespace=? AND raw_sha=? AND encoding=?
        ) SELECT k.ordinal,b.byte_start AS base_start,b.byte_end AS base_end,
            b.part_sha AS base_sha,h.byte_start AS head_start,h.byte_end AS head_end,
            h.part_sha AS head_sha FROM keys k
            LEFT JOIN source_raw_parts b ON b.namespace=? AND b.raw_sha=? AND b.encoding=?
                AND b.ordinal=k.ordinal
            LEFT JOIN source_raw_parts h ON h.namespace=? AND h.raw_sha=? AND h.encoding=?
                AND h.ordinal=k.ordinal
            WHERE k.ordinal>? AND b.part_sha IS NOT h.part_sha
            ORDER BY k.ordinal LIMIT ?'''
        args = (namespace, base['raw_sha'], base['encoding'],
                namespace, head['raw_sha'], head['encoding'],
                namespace, base['raw_sha'], base['encoding'],
                namespace, head['raw_sha'], head['encoding'], after, limit + 1)
        rows = [dict(r) for r in db.execute(sql, args)]
        page = rows[:limit]
        for row in page:
            row['kind'] = ('ADDED' if row['base_sha'] is None else
                           'DELETED' if row['head_sha'] is None else 'REPLACED')
        return {'schema': 'occ.source-delta-page.v1', 'base_version_id': base_version_id,
                'head_version_id': head_version_id, 'changes': page,
                'next_cursor': _page_cursor(base_version_id, head_version_id,
                                            page[-1]['ordinal']) if len(rows) > limit else None,
                'eof': len(rows) <= limit, 'scope': 'FIXED_64K_BYTE_PARTS'}
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Capture immutable local originals')
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--kind', choices=sorted(KINDS), required=True)
    parser.add_argument('--path', type=Path, required=True)
    parser.add_argument('--source-key', help='Stable operator-chosen identity across local path renames')
    parser.add_argument('--intent-key', required=True)
    args = parser.parse_args(argv)
    result = capture_file(args.store, args.namespace, args.kind, args.path,
                          args.intent_key, source_key=args.source_key)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
