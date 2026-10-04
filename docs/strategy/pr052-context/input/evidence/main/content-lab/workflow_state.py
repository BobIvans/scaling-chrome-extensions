"""Workflow metadata in the EXISTING Content Lab owner, never another runtime.

Fences guard local commits. Expired reservations/possible external effects require
reconciliation; their expiry is not proof that an old process has stopped.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid

import automation_core as core

SCHEMA_VERSION=1
SCHEMA = '''
CREATE TABLE IF NOT EXISTS workflow_schema_version(id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL);
INSERT OR IGNORE INTO workflow_schema_version VALUES (1,1);
CREATE TABLE IF NOT EXISTS workflow_records(
 kind TEXT, id TEXT, revision INTEGER NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS workflow_events(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, id TEXT,
 revision INTEGER, state TEXT, detail TEXT, observed REAL);
CREATE TABLE IF NOT EXISTS workflow_epochs(resource TEXT PRIMARY KEY, epoch INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS workflow_leases(
 resource TEXT, owner TEXT, mode TEXT, epoch INTEGER, expires REAL,
 PRIMARY KEY(resource,owner));
CREATE TABLE IF NOT EXISTS workflow_reservations(
 owner TEXT PRIMARY KEY, payload TEXT, state TEXT);
CREATE TABLE IF NOT EXISTS workflow_node_jobs(
 campaign TEXT, revision INTEGER, node TEXT, fingerprint TEXT,
 job_id TEXT NOT NULL UNIQUE, PRIMARY KEY(campaign,revision,node));
CREATE TABLE IF NOT EXISTS workflow_occurrences(
 id TEXT PRIMARY KEY, schedule TEXT, revision INTEGER, instant REAL,
 state TEXT, job_id TEXT, reason TEXT);
'''


def connect(store):
    db = core.connection(Path(store))
    try:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='workflow_schema_version'").fetchone()
        if exists and db.execute('SELECT version FROM workflow_schema_version WHERE id=1').fetchone()[0]!=SCHEMA_VERSION:
            raise ValueError('WORKFLOW_SCHEMA_VERSION_UNSUPPORTED')
        db.executescript(SCHEMA)
        return db
    except BaseException:
        db.close()
        raise


@contextmanager
def transaction(store):
    db = connect(store)
    try:
        db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    finally:
        db.close()


def get(db, kind, key):
    row = db.execute('SELECT revision,payload FROM workflow_records WHERE kind=? AND id=?',
                     (kind, key)).fetchone()
    return None if row is None else {'revision': row[0], 'value': json.loads(row[1])}


def put(db, kind, key, value, expected):
    old = get(db, kind, key)
    if (old['revision'] if old else 0) != expected:
        raise ValueError('WORKFLOW_REVISION_CONFLICT')
    revision = expected + 1
    db.execute('INSERT INTO workflow_records VALUES (?,?,?,?) ON CONFLICT(kind,id) '
               'DO UPDATE SET revision=excluded.revision,payload=excluded.payload',
               (kind, key, revision, core.encoded(value)))
    db.execute('INSERT INTO workflow_events(kind,id,revision,state,detail,observed) VALUES (?,?,?,?,?,?)',
               (kind, key, revision, value.get('state', 'RECORDED'), core.encoded(value), time.time()))
    return revision


def assert_job(db, job):
    row=db.execute('SELECT state,lease_token,lease_until,cancel_requested FROM jobs WHERE id=?',(job['id'],)).fetchone()
    if not row or row[0]!='RUNNING' or row[1]!=job['lease_token'] or row[2]<time.time() or row[3]:
        raise ValueError('WORKFLOW_JOB_FENCE_LOST')


def file_digest(path, progress=None):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            if progress:
                progress()
            h.update(raw)
    return h.hexdigest()


def checked_hash(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('WORKFLOW_HASH_REQUIRED')
    return value


def number(value, *, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError('WORKFLOW_FINITE_NUMBER_REQUIRED')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('WORKFLOW_INTEGER_REQUIRED')
    return value


def registered_file(path, sha256=None, progress=None):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('WORKFLOW_REGISTERED_REGULAR_FILE_REQUIRED')
    if sha256 is not None and file_digest(path, progress) != checked_hash(sha256):
        raise ValueError('WORKFLOW_SOURCE_DRIFT')
    return path


def canonical_resource(path):
    """Windows stat follows case/junction aliases; unknown paths conflict by scope."""
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('WORKFLOW_ABSOLUTE_RESOURCE_REQUIRED')
    try:
        value = path.stat()
        if not value.st_ino:
            raise OSError('unknown physical file identity')
        return {'id': f'file:{value.st_dev}:{value.st_ino}', 'known': True,
                'resolved': str(path.resolve())}
    except OSError:
        # Unknown physical identities cannot assert independent write scopes.
        return {'id': 'filesystem:unknown', 'known': False, 'resolved': None}


def resource_conflict(first, second):
    return first['id'] == second['id'] and (first['mode'] == 'WRITE' or second['mode'] == 'WRITE')


def acquire(db, owner, requests, capacity, demand, *, now, seconds=30):
    """Atomic resources + reservation. Caller owns BEGIN IMMEDIATE transaction."""
    core.identifier(owner)
    number(now); number(seconds, minimum=1)
    if len({r['id'] for r in requests}) != len(requests):
        raise ValueError('WORKFLOW_RESOURCE_ALIAS_CONFLICT')
    if any(r.get('mode') not in {'READ', 'WRITE'} or not isinstance(r.get('id'), str) or not r['id'] for r in requests):
        raise ValueError('WORKFLOW_RESOURCE_MODE')
    if db.execute('SELECT 1 FROM workflow_reservations WHERE owner=?', (owner,)).fetchone():
        raise ValueError('WORKFLOW_OWNER_ALREADY_RESERVED')
    for r in requests:
        rows = db.execute('SELECT owner,mode,expires FROM workflow_leases WHERE resource=?', (r['id'],)).fetchall()
        for row in rows:
            if row[2] < now:
                raise ValueError('WORKFLOW_EXPIRED_LEASE_RECONCILE')
            if r['mode'] == 'WRITE' or row[1] == 'WRITE':
                raise ValueError('WORKFLOW_RESOURCE_WAIT')
    reserved = {}
    for row in db.execute("SELECT payload FROM workflow_reservations WHERE state IN ('RESERVED','UNKNOWN')"):
        for k,v in json.loads(row[0]).items():
            reserved[k] = reserved.get(k, 0) + v
    for k,v in demand.items():
        number(v)
        if k not in capacity or capacity[k] is None:
            raise ValueError('WORKFLOW_CAPACITY_UNKNOWN')
        number(capacity[k])
        if reserved.get(k, 0) + v > capacity[k]:
            raise ValueError('WORKFLOW_BUDGET_WAIT')
    fences = []
    for r in sorted(requests, key=lambda x:x['id']):
        db.execute('INSERT INTO workflow_epochs VALUES (?,1) ON CONFLICT(resource) DO UPDATE SET epoch=epoch+1', (r['id'],))
        epoch = db.execute('SELECT epoch FROM workflow_epochs WHERE resource=?', (r['id'],)).fetchone()[0]
        db.execute('INSERT INTO workflow_leases VALUES (?,?,?,?,?)', (r['id'], owner, r['mode'], epoch, now+seconds))
        fences.append({'id':r['id'], 'epoch':epoch})
    db.execute("INSERT INTO workflow_reservations VALUES (?,?,'RESERVED')", (owner,core.encoded(demand)))
    return {'owner':owner,'fences':fences,'expires':now+seconds}


def check_fence(db, lease, now):
    for r in lease['fences']:
        row = db.execute('SELECT epoch,expires FROM workflow_leases WHERE resource=? AND owner=?', (r['id'],lease['owner'])).fetchone()
        if not row or row[0] != r['epoch'] or row[1] < now:
            raise ValueError('WORKFLOW_FENCE_LOST')
    if not db.execute("SELECT 1 FROM workflow_reservations WHERE owner=? AND state='RESERVED'", (lease['owner'],)).fetchone():
        raise ValueError('WORKFLOW_FENCE_LOST')


def release(db, lease, *, now, unknown=False):
    check_fence(db,lease,now)
    if unknown:
        db.execute("UPDATE workflow_reservations SET state='UNKNOWN' WHERE owner=?", (lease['owner'],))
    else:
        db.execute('DELETE FROM workflow_leases WHERE owner=?', (lease['owner'],))
        db.execute('DELETE FROM workflow_reservations WHERE owner=?', (lease['owner'],))


def reconcile_stopped(db, owner, *, process_stopped, effects_observed, now):
    if process_stopped is not True or effects_observed is not True:
        raise ValueError('WORKFLOW_STOP_AND_EFFECT_OBSERVATION_REQUIRED')
    if db.execute('SELECT 1 FROM workflow_leases WHERE owner=? AND expires>=?', (owner,now)).fetchone():
        raise ValueError('WORKFLOW_LEASE_STILL_ACTIVE')
    db.execute('DELETE FROM workflow_leases WHERE owner=?', (owner,))
    db.execute('DELETE FROM workflow_reservations WHERE owner=?', (owner,))


def begin_effect(db, operation_id, binding):
    current = get(db, 'effect', operation_id)
    if current:
        if current['value']['binding'] != binding:
            raise ValueError('WORKFLOW_EFFECT_BINDING_CONFLICT')
        return current
    put(db,'effect',operation_id,{'binding':binding,'state':'INTENT_RECORDED','evidence':[]},0)
    return get(db,'effect',operation_id)


def effect_transition(db, operation_id, state, expected, evidence):
    old = get(db,'effect',operation_id)
    if old is None:
        raise ValueError('WORKFLOW_EFFECT_NOT_FOUND')
    allowed={'INTENT_RECORDED':{'DISPATCHING','CANCELLED'},'DISPATCHING':{'OBSERVED','UNKNOWN_EFFECT'},
             'UNKNOWN_EFFECT':{'OBSERVED','NOT_APPLIED'},'NOT_APPLIED':{'DISPATCHING','CANCELLED'},
             'OBSERVED':set(),'CANCELLED':set()}
    if state not in allowed[old['value']['state']]:
        raise ValueError('WORKFLOW_EFFECT_TRANSITION')
    if state in {'OBSERVED','NOT_APPLIED'} and not evidence:
        raise ValueError('WORKFLOW_EFFECT_EVIDENCE_REQUIRED')
    value={**old['value'],'state':state,'evidence':list(evidence)}
    return put(db,'effect',operation_id,value,expected)
