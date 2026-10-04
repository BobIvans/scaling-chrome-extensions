"""Complete, bounded read views over repository snapshot and path history.

The older snapshot projection remains a small summary. These independent pages
are read from the canonical SQLite ledger and never materialize the corpus.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from pathlib import Path

from automation_core import identifier, read_connection, strict_int
import repo_context

MAX_PAGE = 50


def _encode(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def _decode(token, keys):
    if not isinstance(token, str) or len(token) > 4096 or not re.fullmatch(r'[A-Za-z0-9_-]+', token):
        raise ValueError('REPO_CURSOR_INVALID')
    try:
        raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
        value = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise ValueError('REPO_CURSOR_INVALID') from exc
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('REPO_CURSOR_INVALID')
    return value


def _limit(limit):
    strict_int(limit, 1, MAX_PAGE)
    return limit


def snapshots(store: Path, namespace: str, alias: str, profile: dict, *, limit=20, cursor=None):
    """Keyset page in (created,id) order; page size never caps history."""
    namespace = identifier(namespace)
    alias = identifier(alias)
    limit = _limit(limit)
    key = None
    if cursor is not None:
        key = _decode(cursor, {'v', 'namespace', 'alias', 'created', 'id'})
        if (key['v'] != 1 or key['namespace'] != namespace or key['alias'] != alias
                or type(key['created']) not in (int, float)
                or not isinstance(key['id'], str) or len(key['id']) != 64):
            raise ValueError('REPO_CURSOR_INVALID')
    db = read_connection(store)
    try:
        args = [namespace, alias]
        where = 'namespace=? AND alias=?'
        if key:
            where += ' AND (created,id)<(?,?)'
            args.extend((key['created'], key['id']))
        rows = [dict(r) for r in db.execute(
            'SELECT id AS snapshot_id,alias,head AS repo_sha,cursor,total,created,profile '
            'FROM repo_snapshots WHERE ' + where + ' ORDER BY created DESC,id DESC LIMIT ?',
            (*args, limit + 1))]
        page, more = rows[:limit], len(rows) > limit
        if any(json.loads(row['profile']) != profile for row in rows):
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        for row in page:
            del row['profile']
        end = page[-1] if page else None
        return {'schema': 'occ.repo-history-page.v1', 'namespace': namespace, 'alias': alias,
                'snapshots': page, 'next_cursor': _encode({'v': 1, 'namespace': namespace,
                    'alias': alias, 'created': end['created'], 'id': end['snapshot_id']}) if more else None,
                'eof': not more}
    finally:
        db.close()


def _base(db, head):
    return db.execute('SELECT * FROM repo_snapshots WHERE namespace=? AND alias=? '
                      'AND (created,id)<(?,?) AND cursor=total ORDER BY created DESC,id DESC LIMIT 1',
                      (head['namespace'], head['alias'], head['created'], head['id'])).fetchone()


def _require_complete(db, snap):
    if (snap['cursor'] != snap['total'] or
            db.execute('SELECT count(*) FROM repo_entries WHERE snapshot_id=?',
                       (snap['id'],)).fetchone()[0] != snap['total'] or
            db.execute("SELECT 1 FROM repo_entries WHERE snapshot_id=? AND state='PENDING' LIMIT 1",
                       (snap['id'],)).fetchone()):
        raise ValueError('REPO_SNAPSHOT_INCOMPLETE')


def delta(store: Path, namespace: str, alias: str, profile: dict, snapshot_id: str,
          *, limit=20, cursor=None, base_snapshot_id=None):
    """Page every added, deleted and modified path between pinned snapshots."""
    limit = _limit(limit)
    db = read_connection(store)
    try:
        head = repo_context.load_snapshot(db, namespace, snapshot_id)
        if head['alias'] != identifier(alias) or json.loads(head['profile']) != profile:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        _require_complete(db, head)
        base = (repo_context.load_snapshot(db, namespace, base_snapshot_id)
                if base_snapshot_id is not None else _base(db, head))
        if base is None:
            if cursor is not None:
                raise ValueError('REPO_CURSOR_INVALID')
            return {'schema': 'occ.repo-delta-page.v1', 'snapshot_id': snapshot_id,
                    'base_snapshot_id': None, 'base_repo_sha': None, 'changes': [],
                    'next_cursor': None, 'eof': True, 'scope': 'NO_PREVIOUS_COMPLETE_SNAPSHOT'}
        if base['alias'] != alias or json.loads(base['profile']) != profile:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        _require_complete(db, base)
        after = None
        if cursor is not None:
            key = _decode(cursor, {'v', 'head', 'base', 'path', 'kind'})
            if (key['v'] != 1 or key['head'] != snapshot_id or key['base'] != base['id']
                    or not isinstance(key['path'], str) or key['kind'] not in ('ADDED', 'DELETED', 'MODIFIED')):
                raise ValueError('REPO_CURSOR_INVALID')
            after = (key['path'], key['kind'])
        # This query only holds a bounded result set. The indexes on
        # (snapshot_id,path) already exist as the repo_entries primary key.
        sql = '''WITH changes AS (
          SELECT n.path AS path,'ADDED' AS kind,n.oid AS oid,n.mode AS mode,
                 NULL AS previous_oid,NULL AS previous_mode
            FROM repo_entries n LEFT JOIN repo_entries o
              ON o.snapshot_id=? AND o.path=n.path
           WHERE n.snapshot_id=? AND o.path IS NULL
          UNION ALL
          SELECT o.path AS path,'DELETED' AS kind,NULL AS oid,NULL AS mode,
                 o.oid AS previous_oid,o.mode AS previous_mode
            FROM repo_entries o LEFT JOIN repo_entries n
              ON n.snapshot_id=? AND n.path=o.path
           WHERE o.snapshot_id=? AND n.path IS NULL
          UNION ALL
          SELECT n.path AS path,'MODIFIED' AS kind,n.oid AS oid,n.mode AS mode,
                 o.oid AS previous_oid,o.mode AS previous_mode
            FROM repo_entries n JOIN repo_entries o
              ON o.snapshot_id=? AND o.path=n.path
           WHERE n.snapshot_id=? AND (n.oid!=o.oid OR n.mode!=o.mode)
        ) SELECT * FROM changes'''
        args = [base['id'], snapshot_id, snapshot_id, base['id'], base['id'], snapshot_id]
        if after:
            sql += ' WHERE (path,kind)>(?,?)'
            args.extend(after)
        sql += ' ORDER BY path,kind LIMIT ?'
        rows = [dict(r) for r in db.execute(sql, (*args, limit + 1))]
        page, more = rows[:limit], len(rows) > limit
        for row in page:
            if row['kind'] not in {'ADDED', 'DELETED'}:
                continue
            opposite = base['id'] if row['kind'] == 'ADDED' else snapshot_id
            oid = row['oid'] if row['kind'] == 'ADDED' else row['previous_oid']
            mode = row['mode'] if row['kind'] == 'ADDED' else row['previous_mode']
            # A unique exact OID/mode pair is evidence of a rename, while
            # duplicate content remains ambiguous and is never guessed.
            matches = db.execute('SELECT path FROM repo_entries WHERE snapshot_id=? '
                                 'AND oid=? AND mode=? AND path!=? ORDER BY path LIMIT 2',
                                 (opposite, oid, mode, row['path'])).fetchall()
            if len(matches) == 1:
                candidate = matches[0]['path']
                still_there = db.execute('SELECT 1 FROM repo_entries WHERE snapshot_id=? AND path=?',
                                         (snapshot_id if row['kind'] == 'ADDED' else base['id'], candidate)).fetchone()
                duplicate = db.execute('SELECT 1 FROM repo_entries WHERE snapshot_id=? '
                                       'AND oid=? AND mode=? AND path!=? LIMIT 1',
                                       (snapshot_id if row['kind'] == 'ADDED' else base['id'],
                                        oid, mode, row['path'])).fetchone()
                if still_there is None and duplicate is None:
                    row['rename_peer'] = candidate
        end = page[-1] if page else None
        return {'schema': 'occ.repo-delta-page.v1', 'snapshot_id': snapshot_id,
                'base_snapshot_id': base['id'], 'base_repo_sha': base['head'],
                'changes': page, 'next_cursor': _encode({'v': 1, 'head': snapshot_id,
                    'base': base['id'], 'path': end['path'], 'kind': end['kind']}) if more else None,
                'eof': not more, 'scope': 'PINNED_TREE_PATHS; dependent graph is separate'}
    finally:
        db.close()
