"""Versioned context services in the existing Content Lab SQLite owner.

Parts/pages bound working memory, never total source, corpus or packet size.
Captured raw bytes and immutable share bytes live inside content.sqlite3; no
second library, executor, model, credentials or network transport is created.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import time

from automation_core import connection, read_connection, identifier, strict_int
from content_lab import _insert_item

PART_BYTES = 8192
PAGE_BYTES = 48_000
HASH = re.compile(r'^[0-9a-f]{64}$')
MAX_INT = 9_007_199_254_740_991


def encoded(value):
    """Versioned Python JSON wire, deliberately not advertised as RFC 8785."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(encoded(value))


def exact(value, required, optional=()):
    if (not isinstance(value, dict) or not set(required) <= set(value)
            or set(value) - set(required) - set(optional)):
        raise ValueError('CONTEXT_SCHEMA')


def hash_id(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError('CONTEXT_HASH_REQUIRED')
    return value


def text(value, maximum=8000):
    if not isinstance(value, str) or not value or '\0' in value or len(value.encode()) > maximum:
        raise ValueError('CONTEXT_TEXT_REQUIRED')
    return value


def strict_json(raw, limit=PAGE_BYTES):
    if not isinstance(raw, bytes) or len(raw) > limit:
        raise ValueError('CONTEXT_FRAME_LIMIT')
    def pairs(xs):
        out = {}
        for k, v in xs:
            if k in out:
                raise ValueError('CONTEXT_DUPLICATE_KEY')
            out[k] = v
        return out
    def nonfinite(_v):
        raise ValueError('CONTEXT_NONFINITE')
    def finite(value):
        result=float(value)
        if not math.isfinite(result):raise ValueError('CONTEXT_NONFINITE')
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite,parse_float=finite)


def db_for(store):
    db = connection(Path(store))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='context_schema'").fetchone():
        if [r[0] for r in db.execute('SELECT version FROM context_schema')]!=[1]:
            db.close();raise ValueError('UNSUPPORTED_CONTEXT_SCHEMA')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS context_schema(version INTEGER PRIMARY KEY);
      INSERT OR IGNORE INTO context_schema VALUES(1);
      CREATE TABLE IF NOT EXISTS context_sources(
        namespace TEXT, source_key TEXT, revision TEXT PRIMARY KEY,
        raw_hash TEXT, bytes INTEGER, kind TEXT, observed REAL, complete INTEGER);
      CREATE INDEX IF NOT EXISTS context_source_scope
        ON context_sources(namespace,source_key,observed,revision);
      CREATE TABLE IF NOT EXISTS context_source_heads(
        namespace TEXT, source_key TEXT, revision TEXT,
        PRIMARY KEY(namespace,source_key));
      CREATE TABLE IF NOT EXISTS context_raw_parts(
        revision TEXT, ordinal INTEGER, start INTEGER, end INTEGER,
        sha256 TEXT, raw BLOB, item_id TEXT,
        PRIMARY KEY(revision,ordinal));
      CREATE INDEX IF NOT EXISTS context_part_ranges ON context_raw_parts(revision,start,end);
      CREATE TABLE IF NOT EXISTS context_intents(
        namespace TEXT, operation_id TEXT, kind TEXT, input_digest TEXT,
        state TEXT, result TEXT, PRIMARY KEY(namespace,operation_id));
      CREATE TABLE IF NOT EXISTS context_intent_fences(
        namespace TEXT, operation_id TEXT, epoch INTEGER, PRIMARY KEY(namespace,operation_id));
      CREATE TABLE IF NOT EXISTS context_events(
        namespace TEXT, event_id TEXT, kind TEXT, payload TEXT, payload_hash TEXT,
        observed REAL, PRIMARY KEY(namespace,event_id));
      CREATE TABLE IF NOT EXISTS context_tombstones(
        namespace TEXT, source_key TEXT, epoch INTEGER, event_id TEXT,
        PRIMARY KEY(namespace,source_key));
      CREATE TABLE IF NOT EXISTS context_annotations(
        namespace TEXT, revision TEXT, event_id TEXT, payload TEXT,
        PRIMARY KEY(namespace,revision,event_id));
      CREATE TABLE IF NOT EXISTS context_packets(
        namespace TEXT, id TEXT, kind TEXT, parent TEXT, payload TEXT,
        payload_hash TEXT, created REAL, PRIMARY KEY(namespace,id));
      CREATE TABLE IF NOT EXISTS context_packet_parts(
        namespace TEXT, packet_id TEXT, ordinal INTEGER, source_ref TEXT,
        raw BLOB, sha256 TEXT, PRIMARY KEY(namespace,packet_id,ordinal));
      CREATE TABLE IF NOT EXISTS context_claims(
        namespace TEXT, result_id TEXT, packet_id TEXT, payload TEXT,
        payload_hash TEXT, state TEXT, PRIMARY KEY(namespace,result_id));
    ''')
    if [r[0] for r in db.execute('SELECT version FROM context_schema')] != [1]:
        db.close()
        raise ValueError('UNSUPPORTED_CONTEXT_SCHEMA')
    return db


@contextmanager
def view(store, *, write=False):
    db = db_for(store) if write else read_connection(Path(store))
    try:
        yield db
        if write:
            db.commit()
    except BaseException:
        if write:
            db.rollback()
        raise
    finally:
        db.close()


def begin_intent(db, namespace, operation_id, kind, payload):
    identifier(namespace); identifier(operation_id)
    h = digest([kind, payload])
    row = db.execute('SELECT * FROM context_intents WHERE namespace=? AND operation_id=?',
                     (namespace, operation_id)).fetchone()
    if row:
        if row['input_digest'] != h or row['kind'] != kind:
            raise ValueError('IDEMPOTENCY_CONFLICT')
        if row['state'] != 'COMPLETED':
            raise ValueError('INTENT_RECONCILIATION_REQUIRED')
        return strict_json(row['result'].encode())
    epoch=db.execute('SELECT epoch FROM core_control WHERE singleton=1').fetchone()[0]
    db.execute('INSERT INTO context_intent_fences VALUES (?,?,?)',(namespace,operation_id,epoch))
    db.execute('INSERT INTO context_intents VALUES (?,?,?,?,?,?)',
               (namespace, operation_id, kind, h, 'PERSISTED', '{}'))
    return None


def finish_intent(db, namespace, operation_id, result):
    ensure_running(db,operation_id,namespace)
    db.execute("UPDATE context_intents SET state='COMPLETED',result=? WHERE namespace=? AND operation_id=?",
               (encoded(result).decode(), namespace, operation_id))
    return result


def intent_status(store, namespace, operation_id):
    identifier(namespace); identifier(operation_id)
    with view(store) as db:
        row = db.execute('SELECT kind,input_digest,state,result FROM context_intents WHERE namespace=? AND operation_id=?',
                         (namespace, operation_id)).fetchone()
        if row is None:
            return {'state': 'NOT_FOUND', 'operation_id': operation_id}
        return {'operation_id': operation_id, 'kind': row['kind'],
                'state': row['state'], 'input_digest': row['input_digest'],
                'result': strict_json(row['result'].encode())}


def record_event(db, namespace, kind, payload):
    raw = encoded(payload).decode(); eid = digest([namespace, kind, payload])
    db.execute('INSERT OR IGNORE INTO context_events VALUES (?,?,?,?,?,?)',
               (namespace, eid, kind, raw, sha(raw.encode()), time.time()))
    return eid


def ensure_running(db,operation_id=None,namespace=None):
    row = db.execute('SELECT stopped,epoch FROM core_control WHERE singleton=1').fetchone()
    if row is not None and row[0]:raise ValueError('CORE_STOPPED')
    if operation_id is not None:
        fence=db.execute('SELECT epoch FROM context_intent_fences WHERE namespace=? AND operation_id=?',(namespace,operation_id)).fetchone()
        if fence is None or fence[0]!=row[1]:raise ValueError('STOP_EPOCH_CHANGED')


def import_file(store, namespace, source_key, path, operation_id, *, progress=None):
    """Stream a reviewed local file. Publish heads only after a verified EOF.

    Resuming a CAPTURING logical operation is safe: only local immutable parts
    exist, the previous head is untouched, and a re-read must match file hash.
    """
    identifier(namespace); identifier(source_key); identifier(operation_id)
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('REGULAR_SOURCE_REQUIRED')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    revision = digest(['capture-v1', namespace, source_key, operation_id])
    intent_input = {'source_key': source_key, 'path': str(path)}
    with view(store, write=True) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM context_intents WHERE namespace=? AND operation_id=?',
                         (namespace, operation_id)).fetchone()
        if row and row['input_digest'] != digest(['capture', intent_input]):
            raise ValueError('IDEMPOTENCY_CONFLICT')
        if row and row['state'] == 'COMPLETED':
            return strict_json(row['result'].encode())
        if not row:
            begin_intent(db, namespace, operation_id, 'capture', intent_input)
        ensure_running(db,operation_id,namespace)
        db.execute('INSERT OR IGNORE INTO context_sources VALUES (?,?,?,?,?,?,?,0)',
                   (namespace, source_key, revision, None, 0, 'CAPTURED_RAW', time.time()))
    hasher = hashlib.sha256(); offset = 0; ordinal = 0
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('REGULAR_SOURCE_REQUIRED')
        while True:
            if progress:
                progress()
            raw = stream.read(PART_BYTES)
            if not raw:
                break
            hasher.update(raw)
            with view(store, write=True) as db:
                db.execute('BEGIN IMMEDIATE'); ensure_running(db,operation_id,namespace)
                old = db.execute('SELECT sha256,raw FROM context_raw_parts WHERE revision=? AND ordinal=?',
                                 (revision, ordinal)).fetchone()
                if old and (old[0] != sha(raw) or old[1] != raw):
                    raise ValueError('SOURCE_DRIFT')
                item_id = None
                try:
                    decoded = raw.decode('utf-8')
                    if '\0' in decoded:
                        raise UnicodeError()
                    item_id = digest([revision, ordinal, sha(raw)])
                    item = {'schema': 'occ.content-lab.item.v1', 'id': item_id,
                            'namespace': namespace, 'source_key': f'context:{source_key}:{ordinal}',
                            'text': decoded, 'input_sha256': sha(raw),
                            'authority': 'source-content-not-action-instructions',
                            'asr_inference_performed': False}
                    _insert_item(db, item)
                except UnicodeError:
                    pass  # Exact raw remains readable; binary/split UTF-8 is explicit.
                db.execute('INSERT OR IGNORE INTO context_raw_parts VALUES (?,?,?,?,?,?,?)',
                           (revision, ordinal, offset, offset + len(raw), sha(raw), sqlite3.Binary(raw), item_id))
            offset += len(raw); ordinal += 1
        after = os.fstat(stream.fileno())
    current = path.lstat()
    attrs = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    path_attrs = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
    # Windows can expose different ctime meanings through fstat and pathname
    # stat. Compare ctime only between handles; never weaken the byte oracle.
    if (any(getattr(before, a) != getattr(after, a) for a in attrs)
            or any(getattr(after, a) != getattr(current, a) for a in path_attrs)
            or offset != before.st_size):
        raise ValueError('SOURCE_DRIFT')
    verified_hash=hashlib.sha256()
    with os.fdopen(os.open(path,flags),'rb') as verification:
        verification_before=os.fstat(verification.fileno())
        for raw in iter(lambda:verification.read(PART_BYTES),b''):
            if progress:progress()
            verified_hash.update(raw)
        verification_after=os.fstat(verification.fileno())
    if (any(getattr(after,a)!=getattr(verification_before,a) for a in attrs)
            or any(getattr(verification_before,a)!=getattr(verification_after,a) for a in attrs)
            or verified_hash.hexdigest()!=hasher.hexdigest()):
        raise ValueError('SOURCE_DRIFT')
    with view(store, write=True) as db:
        db.execute('BEGIN IMMEDIATE'); ensure_running(db,operation_id,namespace)
        if db.execute('SELECT 1 FROM context_tombstones WHERE namespace=? AND source_key=?',
                      (namespace, source_key)).fetchone():
            raise ValueError('SOURCE_TOMBSTONED')
        old_parts = db.execute('SELECT count(*) FROM context_raw_parts WHERE revision=?', (revision,)).fetchone()[0]
        if old_parts != ordinal:
            raise ValueError('SOURCE_DRIFT')
        db.execute('UPDATE context_sources SET raw_hash=?,bytes=?,complete=1 WHERE revision=?',
                   (hasher.hexdigest(), offset, revision))
        db.execute('INSERT INTO context_source_heads VALUES (?,?,?) ON CONFLICT(namespace,source_key) DO UPDATE SET revision=excluded.revision',
                   (namespace, source_key, revision))
        # Reuse canonical heads/versions for existing browser search.
        db.execute('UPDATE sync_heads SET present=0 WHERE namespace=? AND source_key LIKE ? ESCAPE \'!\'',
                   (namespace, 'context:' + source_key.replace('!', '!!').replace('_', '!_').replace('%', '!%') + ':%'))
        for r in db.execute('SELECT * FROM context_raw_parts WHERE revision=? ORDER BY ordinal', (revision,)):
            if r['item_id']:
                key = f"context:{source_key}:{r['ordinal']}"
                db.execute('INSERT OR IGNORE INTO sync_versions VALUES (?,?,?,?)',
                           (namespace, key, r['item_id'], time.time()))
                db.execute('INSERT INTO sync_heads VALUES (?,?,?,?,?,1) ON CONFLICT(namespace,source_key) DO UPDATE SET item_id=excluded.item_id,raw_hash=excluded.raw_hash,generation=excluded.generation,present=1',
                           (namespace, key, r['item_id'], r['sha256'], revision))
        record_event(db, namespace, 'SOURCE_CAPTURED', {'source_key': source_key, 'revision': revision, 'raw_hash': hasher.hexdigest()})
        result = {'state': 'CAPTURED', 'namespace': namespace, 'source_key': source_key,
                  'revision': revision, 'sha256': hasher.hexdigest(), 'bytes': offset,
                  'parts': ordinal, 'raw_exact': True, 'operation_id': operation_id}
        return finish_intent(db, namespace, operation_id, result)


def source_ref(store, namespace, revision, start=0, end=None):
    identifier(namespace); hash_id(revision)
    with view(store) as db:
        row = db.execute('SELECT * FROM context_sources WHERE namespace=? AND revision=? AND complete=1',
                         (namespace, revision)).fetchone()
        if row is None:
            raise ValueError('MISSING_SOURCE')
        end = row['bytes'] if end is None else end
        strict_int(start, 0, MAX_INT); strict_int(end, start, row['bytes'])
        return {'namespace': namespace, 'source_key': row['source_key'], 'revision': revision,
                'sha256': row['raw_hash'], 'start': start, 'end': end, 'offset_space': 'RAW_BYTES'}


def validate_ref(db, namespace, ref, *, allow_deleted=False):
    exact(ref, {'namespace', 'source_key', 'revision', 'sha256', 'start', 'end', 'offset_space'})
    if ref['namespace'] != namespace or ref['offset_space'] not in {'RAW_BYTES', 'ITEM_TEXT_UTF8'}:
        raise ValueError('OUT_OF_SCOPE')
    hash_id(ref['revision']); hash_id(ref['sha256']); text(ref['source_key'],16_000)
    if ref['offset_space'] == 'ITEM_TEXT_UTF8':
        row = db.execute('SELECT payload FROM items WHERE id=?', (ref['revision'],)).fetchone()
        if row is None:
            raise ValueError('MISSING_SOURCE')
        item = json.loads(row[0])
        if item.get('namespace') != namespace or item.get('source_key') != ref['source_key']:
            raise ValueError('OUT_OF_SCOPE')
        raw = item['text'].encode()
        if sha(raw) != ref['sha256']:
            raise ValueError('SOURCE_DRIFT')
        total = len(raw)
        key = ref['source_key']
        if not allow_deleted and db.execute("SELECT 1 FROM sqlite_master WHERE name='library_record_heads'").fetchone():
            deleted=db.execute('SELECT tombstone FROM library_record_heads WHERE namespace=? AND source_key=?',(namespace,key)).fetchone()
            if deleted and deleted[0]:raise ValueError('SOURCE_TOMBSTONED')
    else:
        row = db.execute('SELECT * FROM context_sources WHERE namespace=? AND revision=? AND complete=1',
                         (namespace, ref['revision'])).fetchone()
        if row is None:
            raise ValueError('MISSING_SOURCE')
        if row['raw_hash'] != ref['sha256'] or row['source_key'] != ref['source_key']:
            raise ValueError('SOURCE_DRIFT')
        total = row['bytes']; key = row['source_key']
    strict_int(ref['start'], 0, total); strict_int(ref['end'], ref['start'], total)
    if not allow_deleted and db.execute('SELECT 1 FROM context_tombstones WHERE namespace=? AND source_key=?',
                                       (namespace, key)).fetchone():
        raise ValueError('SOURCE_TOMBSTONED')
    return total


def iter_span(db, namespace, ref, *, chunk_bytes=PART_BYTES, allow_deleted=False):
    validate_ref(db, namespace, ref, allow_deleted=allow_deleted)
    strict_int(chunk_bytes, 1, PART_BYTES)
    if ref['offset_space'] == 'ITEM_TEXT_UTF8':
        item = json.loads(db.execute('SELECT payload FROM items WHERE id=?', (ref['revision'],)).fetchone()[0])
        raw = item['text'].encode()[ref['start']:ref['end']]
        for i in range(0, len(raw), chunk_bytes):
            yield ref['start'] + i, raw[i:i + chunk_bytes]
        return
    cursor = ref['start']
    for r in db.execute('SELECT * FROM context_raw_parts WHERE revision=? AND end>? AND start<? ORDER BY ordinal',
                        (ref['revision'], ref['start'], ref['end'])):
        raw = r['raw']
        if sha(raw) != r['sha256'] or r['end'] - r['start'] != len(raw):
            raise ValueError('SOURCE_CORRUPT')
        start, end = max(ref['start'], r['start']), min(ref['end'], r['end'])
        if start != cursor:
            raise ValueError('SOURCE_CORRUPT')
        raw = raw[start - r['start']:end - r['start']]
        for i in range(0, len(raw), chunk_bytes):
            yield start + i, raw[i:i + chunk_bytes]
        cursor = end
    if cursor != ref['end']:
        raise ValueError('SOURCE_CORRUPT')


def read_span(store, namespace, ref):
    if ref.get('end', 0) - ref.get('start', 0) > PART_BYTES:
        raise ValueError('RANGE_PAGE_REQUIRED')
    with view(store) as db:
        raw = b''.join(r for _offset, r in iter_span(db, namespace, ref))
    return {'source_ref': ref, 'sha256': sha(raw), 'bytes': len(raw),
            'base64': base64.b64encode(raw).decode(), 'text': raw.decode('utf-8', errors='replace'),
            'text_decode': 'UTF8_PREVIEW_REPLACEMENT_POSSIBLE', 'authority': 'DATA_ONLY'}


def annotate(store, namespace, ref, annotation, operation_id):
    exact(annotation, {'project', 'valid_from', 'valid_until', 'supersedes', 'conflict_group', 'note'}, {'labels'})
    text(annotation['project'], 100); text(annotation['note'])
    labels=annotation.get('labels',[])
    if not isinstance(labels,list) or len(labels)>40 or len(set(labels))!=len(labels):
        raise ValueError('CONTEXT_LABELS_REQUIRED')
    for label in labels:
        text(label,100)
    for k in ('valid_from', 'valid_until'):
        if annotation[k] is not None:
            strict_int(annotation[k], 0, MAX_INT)
    if (annotation['valid_from'] is not None and annotation['valid_until'] is not None
            and annotation['valid_until'] <= annotation['valid_from']):
        raise ValueError('INVALID_TIME_INTERVAL')
    for k in ('supersedes', 'conflict_group'):
        if annotation[k] is not None:
            text(annotation[k], 100)
    with view(store, write=True) as db:
        db.execute('BEGIN IMMEDIATE')
        old = begin_intent(db, namespace, operation_id, 'annotation', [ref, annotation])
        if old is not None:
            return old
        validate_ref(db, namespace, ref)
        eid = record_event(db, namespace, 'ANNOTATION', {'ref': ref, 'annotation': annotation})
        db.execute('INSERT OR IGNORE INTO context_annotations VALUES (?,?,?,?)',
                   (namespace, ref['revision'], eid, encoded(annotation).decode()))
        return finish_intent(db, namespace, operation_id, {'state': 'ANNOTATED', 'event_id': eid})


def search_sources(store, namespace, query='', *, offset=0, limit=20, as_of=None,
                   project=None, labels=None, history=False):
    identifier(namespace); strict_int(offset, 0, MAX_INT); strict_int(limit, 1, 100)
    if not isinstance(query, str) or len(query.encode()) > 1000 or type(history) is not bool:
        raise ValueError('CONTEXT_QUERY_REQUIRED')
    if as_of is not None:
        strict_int(as_of, 0, MAX_INT)
    if project is not None:
        text(project, 100)
    if labels is not None:
        if not isinstance(labels,list) or len(labels)>20 or len(set(labels))!=len(labels):
            raise ValueError('CONTEXT_LABEL_FILTER')
        for label in labels:text(label,100)
    rows=[]; seen=0; more=False
    with view(store) as db:
        # Namespace/tombstones/time BEFORE excerpts/ranking; deterministic pagination.
        # An explicit label filter is revision-addressable metadata, so it may
        # intentionally surface a tagged historical revision even when history=False.
        cursor = db.execute('''SELECT s.* FROM context_sources s
            LEFT JOIN context_source_heads h ON s.namespace=h.namespace AND s.source_key=h.source_key
            WHERE s.namespace=? AND s.complete=1
              AND NOT EXISTS (SELECT 1 FROM context_tombstones t WHERE t.namespace=s.namespace AND t.source_key=s.source_key)
              AND (? OR ? IS NOT NULL OR ? OR h.revision=s.revision)
            ORDER BY s.source_key,s.observed DESC,s.revision''',
            (namespace, int(history), as_of, int(labels is not None)))
        temporal_seen=set()
        for row in cursor:
            annrow=db.execute('''SELECT a.payload FROM context_annotations a JOIN context_events e
                ON a.namespace=e.namespace AND a.event_id=e.event_id
                WHERE a.namespace=? AND a.revision=? ORDER BY e.observed DESC,e.event_id DESC LIMIT 1''',
                              (namespace,row['revision'])).fetchone()
            ann=json.loads(annrow[0]) if annrow else {}
            if project is not None and ann.get('project') != project:
                continue
            if labels is not None and not set(labels) <= set(ann.get('labels') or []):
                continue
            if as_of is not None:
                start=ann.get('valid_from') if ann.get('valid_from') is not None else row['observed']
                end=ann.get('valid_until')
                if as_of < start or end is not None and as_of >= end:
                    continue
                if not history and row['source_key'] in temporal_seen:
                    continue
                temporal_seen.add(row['source_key'])
            match=None
            if query in {row['source_key'],row['revision'],''}:
                match=(0,0,'ID_OR_PATH' if query else 'FILTER')
            else:
                needle=query.encode(); carry=b''; carry_start=0
                for part in db.execute('SELECT start,raw,sha256 FROM context_raw_parts WHERE revision=? ORDER BY ordinal', (row['revision'],)):
                    if sha(part['raw']) != part['sha256']:
                        raise ValueError('SOURCE_CORRUPT')
                    data=carry+part['raw']; at=data.lower().find(needle.lower())
                    if at >= 0:
                        match=(carry_start+at,carry_start+at+len(needle),'EXACT_QUOTE');break
                    keep=min(len(data),max(0,len(needle)-1));carry=data[-keep:] if keep else b''
                    carry_start=part['start']+len(part['raw'])-keep
            if match is None:
                continue
            if seen < offset:
                seen+=1;continue
            if len(rows)>=limit:
                more=True;break
            start,end,reason=match
            # Empty query preview reads a bounded start, precise quote has its exact span.
            end=min(row['bytes'], max(end,start+min(256,row['bytes']-start))) if not query else end
            ref={'namespace':namespace,'source_key':row['source_key'],'revision':row['revision'],
                 'sha256':row['raw_hash'],'start':start,'end':end,'offset_space':'RAW_BYTES'}
            preview=b''.join(b for _off,b in iter_span(db,namespace,ref))[:256].decode('utf-8',errors='replace')
            item={'source_ref':ref,'total_bytes':row['bytes'],'why_selected':reason,
                  'snippet':preview,'annotation':ann,'historical':row['revision'] != db.execute(
                      'SELECT revision FROM context_source_heads WHERE namespace=? AND source_key=?',
                      (namespace,row['source_key'])).fetchone()[0]}
            if len(encoded({'rows':rows+[item]}))>PAGE_BYTES:
                if not rows:raise ValueError('ROW_PAGE_LIMIT')
                more=True;break
            rows.append(item);seen+=1
    groups={}
    for row in rows:
        group=row['annotation'].get('conflict_group')
        if group:groups.setdefault(group,[]).append(row['source_ref']['revision'])
    return {'schema':'occ.context-search.v1','namespace':namespace,'rows':rows,'offset':offset,
            'next_offset':offset+len(rows) if more else None,
            'conflict_sets':{g:rs for g,rs in groups.items() if len(rs)>1},
            'state':'MATCHES' if rows else 'NO_MATCH','scope_applied_before_preview':True,
            'corpus_limit':None,'model_read':'UNKNOWN'}


def deletion_impact(store,namespace,source_key):
    identifier(namespace);identifier(source_key)
    with view(store) as db:
        versions=db.execute('SELECT count(*) FROM context_sources WHERE namespace=? AND source_key=?',(namespace,source_key)).fetchone()[0]
        affected=set()
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='context_packet_sources'").fetchone():
            for row in db.execute('SELECT packet_id,ref FROM context_packet_sources WHERE namespace=?',(namespace,)):
                if json.loads(row['ref'])['source_key']==source_key:affected.add(row['packet_id'])
        affected=len(affected)
    return {'source_key':source_key,'versions':versions,'dependent_packets':affected,
            'raw_retention':'PRESERVED_UNTIL_EXPLICIT_PHYSICAL_PURGE','backup_copies':'EXTERNAL_UNKNOWN',
            'external_copies_deletion':'NOT_CLAIMED'}


def tombstone(store,namespace,source_key,operation_id):
    identifier(namespace);identifier(source_key)
    with view(store,write=True) as db:
        db.execute('BEGIN IMMEDIATE')
        old=begin_intent(db,namespace,operation_id,'tombstone',{'source_key':source_key})
        if old is not None:return old
        epoch=db.execute('SELECT coalesce(max(epoch),0)+1 FROM context_tombstones').fetchone()[0]
        eid=record_event(db,namespace,'TOMBSTONE',{'source_key':source_key,'epoch':epoch})
        db.execute('INSERT INTO context_tombstones VALUES (?,?,?,?) ON CONFLICT(namespace,source_key) DO UPDATE SET epoch=excluded.epoch,event_id=excluded.event_id', (namespace,source_key,epoch,eid))
        pattern='context:'+source_key.replace('!','!!').replace('_','!_').replace('%','!%')+':%'
        db.execute("UPDATE sync_heads SET present=0 WHERE namespace=? AND (source_key=? OR source_key LIKE ? ESCAPE '!')",(namespace,source_key,pattern))
        return finish_intent(db,namespace,operation_id,{'state':'TOMBSTONED','epoch':epoch,'event_id':eid})
