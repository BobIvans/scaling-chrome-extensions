"""Stream a pinned Git inventory to the existing Content Lab SQLite owner.

No total file/output/duration ceiling by default. Optional operator deadlines
and stage quotas fail explicitly, never return a truncated successful ledger.
Source files/configuration are data; no checkout, filters, hooks or lazy fetch.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import errno
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

# Also works when the installed operator invokes Python in isolated mode.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_context as repo
from automation_core import digest, identifier, load_json

DEFAULT_BUDGET = {
    'schema': 'occ.repo-inventory-budget.v1',
    'read_block_bytes': 65536, 'stdout_queue_blocks': 8,
    'max_record_bytes': 65536, 'insert_batch_rows': 256,
    'insert_batch_bytes': 262144, 'stderr_total_bytes': 65536,
    'stderr_retained_bytes': 8192, 'timeout_seconds': None,
    'cleanup_timeout_seconds': 5, 'stage_max_bytes': None,
    'stage_cache_bytes': 2097152, 'sqlite_busy_timeout_ms': 1000,
    'target_peak_rss_bytes': 67108864, 'target_rss_growth_bytes': 16777216,
}
BUFFER_RANGES = {
    'read_block_bytes': (1024, 65536), 'stdout_queue_blocks': (1, 16),
    'max_record_bytes': (1024, 65536), 'insert_batch_rows': (1, 256),
    'insert_batch_bytes': (262144, 262144),
    'stderr_total_bytes': (1024, 1048576), 'stderr_retained_bytes': (0, 65536),
    'cleanup_timeout_seconds': (1, 30), 'stage_cache_bytes': (65536, 16777216),
    'sqlite_busy_timeout_ms': (0, 5000),
    'target_peak_rss_bytes': (1048576, 1073741824),
    'target_rss_growth_bytes': (0, 1073741824),
}
MODES = {'100644': 'blob', '100755': 'blob', '120000': 'blob', '160000': 'commit'}
ENTRY_COLUMNS = 'ordinal,path,mode,kind,oid,size,state,reason'


class InventoryError(ValueError):
    def __init__(self, reason, *, process_stopped=True):
        super().__init__(reason)
        self.process_stopped = process_stopped


def validate_budget(value):
    if value is None:
        return dict(DEFAULT_BUDGET)
    if (not isinstance(value, dict) or set(value) != set(DEFAULT_BUDGET)
            or value.get('schema') != DEFAULT_BUDGET['schema']):
        raise InventoryError('REPO_INVENTORY_BUDGET_REQUIRED')
    for key, (low, high) in BUFFER_RANGES.items():
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise InventoryError('REPO_INVENTORY_BUDGET_REQUIRED')
    for key, low in [('timeout_seconds', 1), ('stage_max_bytes', 1048576)]:
        if value[key] is not None and (type(value[key]) is not int or value[key] < low):
            raise InventoryError('REPO_INVENTORY_BUDGET_REQUIRED')
    if (value['stderr_retained_bytes'] > value['stderr_total_bytes']
            or value['read_block_bytes'] * value['stdout_queue_blocks'] > 1048576):
        raise InventoryError('REPO_INVENTORY_BUDGET_REQUIRED')
    return dict(value)


class Run:
    def __init__(self, budget, progress=None, cancel=None, metrics=None):
        self.budget = validate_budget(budget)
        self.started = time.monotonic()
        duration = self.budget['timeout_seconds']
        self.deadline = self.started + duration if duration is not None else None
        self.progress, self.cancel = progress, cancel
        self.sql_error = None
        self.metrics = metrics if metrics is not None else {}
        self.metrics.update(stdout_bytes=0, stderr_bytes=0, stderr_retained_bytes=0,
                            stage_peak_bytes=0, max_batch_rows=0, max_batch_bytes=0)

    def check(self):
        if self.cancel is not None and self.cancel.is_set():
            raise InventoryError('CANCEL_REQUESTED')
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise InventoryError('REPO_INVENTORY_TIMEOUT')
        if self.progress is not None:
            self.progress()

    def sqlite_progress(self):
        try:
            self.check()
            return 0
        except BaseException as exc:
            self.sql_error = exc
            return 1

    def configure(self, db):
        self.check()
        wait = self.budget['sqlite_busy_timeout_ms']
        if self.deadline is not None:
            wait = min(wait, max(0, int((self.deadline - time.monotonic()) * 1000)))
        db.execute('PRAGMA busy_timeout=' + str(wait))
        db.execute('PRAGMA cache_size=-' + str(max(64, self.budget['stage_cache_bytes'] // 1024)))
        db.execute('PRAGMA temp_store=FILE')
        db.set_progress_handler(self.sqlite_progress, 1000)

    def disk_check(self, directory, *, reserve=0):
        self.check()
        total = sum(p.stat().st_size for p in directory.iterdir() if p.is_file())
        self.metrics['stage_peak_bytes'] = max(self.metrics['stage_peak_bytes'], total)
        limit = self.budget['stage_max_bytes']
        if limit is not None and total + reserve > limit:
            raise InventoryError('REPO_INVENTORY_STAGE_LIMIT')

    def sqlite_error(self, exc):
        if self.sql_error is not None:
            raise self.sql_error from exc
        self.check()
        code = getattr(exc, 'sqlite_errorcode', 0) & 255
        if code == sqlite3.SQLITE_FULL:
            raise InventoryError('REPO_INVENTORY_DISK_FULL') from exc
        if code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
            raise InventoryError('REPO_INVENTORY_STORE_BUSY') from exc
        if isinstance(exc, sqlite3.IntegrityError):
            raise InventoryError('REPO_INVENTORY_STREAM_MALFORMED') from exc
        raise InventoryError('REPO_INVENTORY_STORE_FAILED') from exc


def git_environment():
    env = {k: v for k, v in os.environ.items()
           if k in {'PATH', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'}}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
               GIT_OPTIONAL_LOCKS='0', LC_ALL='C')
    return env


class GitStream:
    """Two independent pipe drains, bounded stdout queue and stderr tail."""
    def __init__(self, root, args, run):
        self.run = run
        self.stop = threading.Event()
        self.done = [threading.Event(), threading.Event()]
        self.blocks = queue.Queue(maxsize=run.budget['stdout_queue_blocks'])
        self.errors = []
        self.stderr_bytes, self.stderr_tail = 0, b''
        self.threads = []
        options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        run.check()
        try:
            self.child = subprocess.Popen(
                ['git', '-c', 'core.fsmonitor=false', '-C', str(root), *args],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=git_environment(),
                shell=False, **options)
        except OSError as exc:
            raise InventoryError('REPO_UNAVAILABLE') from exc
        try:
            for i, stream in enumerate((self.child.stdout, self.child.stderr)):
                thread = threading.Thread(target=self.drain, args=(i, stream),
                                          name='occ-git-inventory-pipe', daemon=True)
                self.threads.append(thread)
                thread.start()
        except BaseException:
            self.close()
            raise

    def drain(self, index, stream):
        try:
            while not self.stop.is_set():
                raw = stream.read1(self.run.budget['read_block_bytes'])
                if not raw:
                    break
                if index == 0:
                    while not self.stop.is_set():
                        try:
                            self.blocks.put(raw, timeout=.05)
                            break
                        except queue.Full:
                            pass
                else:
                    self.stderr_bytes += len(raw)
                    retained = self.run.budget['stderr_retained_bytes']
                    self.stderr_tail = (self.stderr_tail + raw)[-retained:] if retained else b''
                    if self.run.metrics['stderr_bytes'] + self.stderr_bytes > self.run.budget['stderr_total_bytes']:
                        self.errors.append('REPO_INVENTORY_STDERR_LIMIT')
                        break
        except BaseException:
            if not self.stop.is_set():
                self.errors.append('REPO_GIT_READ_FAILED')
        finally:
            try:
                stream.close()
            except BaseException:
                self.errors.append('REPO_GIT_READ_FAILED')
            finally:
                self.done[index].set()

    def __iter__(self):
        while True:
            self.run.check()
            if self.errors:
                raise InventoryError(self.errors[0])
            try:
                raw = self.blocks.get(timeout=.05)
            except queue.Empty:
                if all(e.is_set() for e in self.done) and self.child.poll() is not None:
                    if self.errors:
                        raise InventoryError(self.errors[0])
                    if self.child.returncode:
                        raise InventoryError('REPO_GIT_READ_FAILED')
                    break
                continue
            yield raw

    def close(self):
        self.stop.set()
        until = time.monotonic() + self.run.budget['cleanup_timeout_seconds']
        if self.child.poll() is None or not all(e.is_set() for e in self.done):
            if os.name == 'nt':
                # Only the still-owned active child PID. Never reclaim old PIDs.
                if self.child.poll() is None:
                    taskkill = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/taskkill.exe'
                    if taskkill.is_file():
                        try:
                            subprocess.run([str(taskkill), '/PID', str(self.child.pid), '/T', '/F'],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           timeout=max(.01, until - time.monotonic()), shell=False)
                        except (OSError, subprocess.TimeoutExpired):
                            pass
                    if self.child.poll() is None:
                        self.child.kill()
            else:
                try:
                    os.killpg(self.child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        try:
            self.child.wait(timeout=max(.01, until - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
        for thread in self.threads:
            if thread.ident is not None:
                thread.join(timeout=max(0, until - time.monotonic()))
        self.run.metrics['stderr_bytes'] += self.stderr_bytes
        self.run.metrics['stderr_retained_bytes'] = max(
            self.run.metrics['stderr_retained_bytes'], len(self.stderr_tail))
        if self.child.poll() is None or any(t.is_alive() for t in self.threads):
            raise InventoryError('PROCESS_STOP_UNCONFIRMED', process_stopped=False)


@contextmanager
def stream(root, args, run):
    reader = GitStream(root, args, run)
    try:
        yield iter(reader)
    finally:
        reader.close()


def control(root, run, *args):
    raw = bytearray()
    with stream(root, args, run) as blocks:
        for part in blocks:
            if len(raw) + len(part) > 65536:
                raise InventoryError('REPO_GIT_OUTPUT_LIMIT')
            raw.extend(part)
    return bytes(raw)


def records(blocks, run):
    pending = bytearray()
    for raw in blocks:
        run.metrics['stdout_bytes'] += len(raw)
        offset = 0
        while offset < len(raw):
            end = raw.find(b'\0', offset)
            tail = len(raw) if end == -1 else end
            if len(pending) + tail - offset > run.budget['max_record_bytes']:
                raise InventoryError('REPO_INVENTORY_RECORD_LIMIT')
            pending.extend(raw[offset:tail])
            if end == -1:
                break
            if not pending:
                raise InventoryError('REPO_INVENTORY_STREAM_MALFORMED')
            yield bytes(pending)
            pending.clear()
            offset = end + 1
    if pending:
        raise InventoryError('REPO_INVENTORY_STREAM_MALFORMED')


def parse_record(raw, width, profile):
    try:
        header, raw_path = raw.split(b'\t', 1)
        mode, kind, oid, token = header.decode('ascii').split()
        if (not raw_path or b'\0' in raw_path or MODES.get(mode) != kind
                or not re.fullmatch('[0-9a-f]{' + str(width) + '}', oid)):
            raise ValueError()
        if kind != 'blob':
            if token != '-':
                raise ValueError()
            size = None
        elif token == 'BAD':
            size = None
        elif re.fullmatch(r'[0-9]+', token) and len(token) <= 19 and int(token) <= 9223372036854775807:
            size = int(token)
        else:
            raise ValueError()
    except (UnicodeDecodeError, ValueError) as exc:
        raise InventoryError('REPO_INVENTORY_STREAM_MALFORMED') from exc
    try:
        path = repo.source_path(raw_path.decode('utf-8'))
        state, reason = 'PENDING', None
    except (UnicodeDecodeError, ValueError):
        path, state, reason = 'git-path-hex:' + raw_path.hex(), 'EXCLUDED', 'UNSUPPORTED_PATH'
    if kind != 'blob' or mode == '120000':
        state, reason = 'EXCLUDED', 'LINK_OR_SUBMODULE_METADATA_ONLY'
    elif repo.SECRET_NAME.search(path) or any(path == p or path.startswith(p + '/') for p in profile['exclusions']):
        state, reason = 'EXCLUDED', 'PROTECTED_NAME_OR_OPERATOR_EXCLUSION'
    elif size is None:
        state, reason = 'ERROR', 'BLOB_SIZE_UNAVAILABLE'
    return (path, mode, kind, oid, size, state, reason, raw_path)


def stage_inventory(root, head, width, profile, directory, run):
    stage_path = directory / 'inventory.sqlite3'
    stage = sqlite3.connect(stage_path)
    try:
        run.configure(stage)
        stage.execute('PRAGMA journal_mode=DELETE')
        if run.budget['stage_max_bytes'] is not None:
            pages = run.budget['stage_max_bytes'] // stage.execute('PRAGMA page_size').fetchone()[0]
            stage.execute('PRAGMA max_page_count=' + str(pages))
        stage.execute('CREATE TABLE entries(ordinal INTEGER PRIMARY KEY,path TEXT UNIQUE NOT NULL,mode TEXT,kind TEXT,oid TEXT,size INTEGER,state TEXT,reason TEXT,raw_path BLOB,record BLOB)')
        total, batch_size, batch = 0, 0, []
        stream_hash = hashlib.sha256()

        def flush():
            nonlocal batch_size
            if not batch:
                return
            # Include the bounded rollback journal/cache reserve before writes.
            run.disk_check(directory, reserve=batch_size * 2 + run.budget['stage_cache_bytes'])
            with stage:
                stage.executemany('INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?)', batch)
                run.disk_check(directory)
            run.metrics['max_batch_rows'] = max(run.metrics['max_batch_rows'], len(batch))
            run.metrics['max_batch_bytes'] = max(run.metrics['max_batch_bytes'], batch_size)
            batch.clear()
            batch_size = 0
            run.disk_check(directory)

        with stream(root, ['ls-tree', '-r', '-z', '-l', '--full-tree', head], run) as blocks:
            for raw in records(blocks, run):
                entry = parse_record(raw, width, profile)
                byte_size = len(raw) + len(entry[-1]) + len(entry[0].encode('utf-8')) + 256
                if byte_size > run.budget['insert_batch_bytes']:
                    raise InventoryError('REPO_INVENTORY_RECORD_LIMIT')
                if batch and (len(batch) >= run.budget['insert_batch_rows']
                              or batch_size + byte_size > run.budget['insert_batch_bytes']):
                    flush()
                batch.append((total, *entry, raw))
                batch_size += byte_size
                stream_hash.update(raw + b'\0')
                total += 1
        flush()
        # Independent bounded readback verifies the staged projection, bytes,
        # continuous ordinals, and exact original NUL stream digest.
        proof, seen = hashlib.sha256(), 0
        for row in stage.execute('SELECT * FROM entries ORDER BY ordinal'):
            run.check()
            if row[0] != seen or tuple(row[1:9]) != parse_record(row[9], width, profile):
                raise InventoryError('CONTEXT_INCOMPLETE')
            proof.update(row[9] + b'\0')
            seen += 1
        if seen != total or proof.digest() != stream_hash.digest():
            raise InventoryError('CONTEXT_INCOMPLETE')
        run.metrics['stdout_sha256'] = stream_hash.hexdigest()
        run.disk_check(directory)
        return stage_path, total
    finally:
        stage.close()


def valid_existing(db, stage, snap, alias, profile, head, tree, total, run):
    try:
        existing_profile = json.loads(snap['profile'])
    except (TypeError, ValueError) as exc:
        raise InventoryError('CONTEXT_INCOMPLETE') from exc
    if (snap['namespace'] != profile['namespace'] or snap['alias'] != alias
            or existing_profile != profile or snap['head'] != head
            or snap['tree'] != tree or snap['total'] != total
            or type(snap['cursor']) is not int or not 0 <= snap['cursor'] <= total):
        raise InventoryError('CONTEXT_INCOMPLETE')
    count, first, last = db.execute(
        'SELECT count(*),min(ordinal),max(ordinal) FROM repo_entries WHERE snapshot_id=?', (snap['id'],)).fetchone()
    if count != total or (total and (first != 0 or last != total - 1)):
        raise InventoryError('CONTEXT_INCOMPLETE')
    observed = db.execute('SELECT ordinal,path,mode,kind,oid,size,state FROM repo_entries WHERE snapshot_id=? ORDER BY ordinal', (snap['id'],))
    expected = stage.execute('SELECT ordinal,path,mode,kind,oid,size FROM entries ORDER BY ordinal')
    for entry, reference in zip(observed, expected):
        run.check()
        if tuple(entry[:6]) != tuple(reference) or entry[6] not in {'PENDING', 'INDEXED', 'ERROR', 'EXCLUDED'}:
            raise InventoryError('CONTEXT_INCOMPLETE')


def publish(store, alias, profile, root, head, tree, stage_path, total, run, existing_db=None):
    snapshot_id = digest({'alias': alias, 'profile': profile, 'head': head, 'tree': tree})
    owned = existing_db is None
    db = repo.db_for(store, configure=run.configure) if owned else existing_db
    stage = None
    try:
        stage = sqlite3.connect(stage_path)
        run.configure(stage)
        if not owned and not db.in_transaction:
            raise InventoryError('REPO_INVENTORY_TRANSACTION_REQUIRED')
        with db if owned else nullcontext(db):
            if owned:
                db.execute('BEGIN IMMEDIATE')
            run.check()
            if control(root, run, 'rev-parse', 'HEAD').decode('ascii').strip() != head:
                raise InventoryError('SOURCE_DRIFT')
            existing = db.execute('SELECT * FROM repo_snapshots WHERE id=?', (snapshot_id,)).fetchone()
            reused = existing is not None
            if reused:
                valid_existing(db, stage, existing, alias, profile, head, tree, total, run)
            else:
                db.execute('INSERT INTO repo_snapshots VALUES (?,?,?,?,?,?,?,?,?)',
                           (snapshot_id, profile['namespace'], alias, json.dumps(profile),
                            head, tree, 0, total, time.time()))
                # Reading the private stage in bounded batches also supports
                # PR001's existing transaction: scan intent + inventory commit
                # together, with no second writer or attached-file lifetime.
                batch, byte_size = [], 0
                def flush():
                    if batch:
                        run.check()
                        db.executemany('INSERT INTO repo_entries(snapshot_id,' + ENTRY_COLUMNS + ') VALUES (?,?,?,?,?,?,?,?,?)', batch)
                        batch.clear()
                for row in stage.execute('SELECT ' + ENTRY_COLUMNS + ' FROM entries ORDER BY ordinal'):
                    size = len(row[1].encode('utf-8')) + 256
                    if batch and (len(batch) >= run.budget['insert_batch_rows'] or byte_size + size > run.budget['insert_batch_bytes']):
                        flush()
                        byte_size = 0
                    batch.append((snapshot_id, *row))
                    byte_size += size
                flush()
                valid_existing(db, stage, db.execute('SELECT * FROM repo_snapshots WHERE id=?', (snapshot_id,)).fetchone(),
                               alias, profile, head, tree, total, run)
            run.check()
            if control(root, run, 'rev-parse', 'HEAD').decode('ascii').strip() != head:
                raise InventoryError('SOURCE_DRIFT')
            # Deadline/cancellation interrupts must not interfere with rollback.
            run.check()
            if owned:
                db.set_progress_handler(None, 0)
        return {'schema': 'occ.repo-inventory-receipt.v1', 'state': 'READY',
                'repository': alias, 'namespace': profile['namespace'], 'snapshotId': snapshot_id,
                'repoSha': head, 'treeSha': tree, 'total': total, 'inventoryComplete': True,
                'captureComplete': None if reused else False, 'reused': reused,
                'reason': None, 'processStopped': True,
                'proofScope': 'INVENTORY_ONLY_NO_CAPTURE_OR_EXPORT_PROOF'}
    except BaseException:
        if owned:
            db.set_progress_handler(None, 0)
            db.rollback()
        raise
    finally:
        if stage is not None:
            stage.close()
        if owned:
            db.close()


def inventory(store, alias, profile, *, budget=None, progress=None, cancel=None, metrics=None, _db=None):
    run = Run(budget, progress, cancel, metrics)
    directory = None
    keep_stage = False
    try:
        identifier(alias)
        profile = repo.validate_profile(profile)
        store = Path(store)
        root = repo.check_root(profile, read=lambda root, *args: control(root, run, *args))
        if store.resolve().is_relative_to(root):
            raise InventoryError('STORE_MUST_BE_OUTSIDE_SOURCE')
        if any(p.is_symlink() for p in (store, *store.parents)):
            raise InventoryError('STORE_SYMLINK_FORBIDDEN')
        if (store / 'content.sqlite3').is_symlink():
            raise InventoryError('STORE_SYMLINK_FORBIDDEN')
        head = control(root, run, 'rev-parse', 'HEAD').decode('ascii').strip()
        tree = control(root, run, 'rev-parse', head + '^{tree}').decode('ascii').strip()
        object_format = control(root, run, 'rev-parse', '--show-object-format').decode('ascii').strip()
        width = {'sha1': 40, 'sha256': 64}.get(object_format)
        if width is None or any(not re.fullmatch('[0-9a-f]{' + str(width) + '}', oid) for oid in (head, tree)):
            raise InventoryError('REPO_GIT_READ_FAILED')
        store.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix='.occ-inventory-', dir=store))
        stage_path, total = stage_inventory(root, head, width, profile, directory, run)
        return publish(store, alias, profile, root, head, tree, stage_path, total, run, _db)
    except InventoryError as exc:
        keep_stage = not exc.process_stopped
        raise
    except sqlite3.Error as exc:
        run.sqlite_error(exc)
    except OSError as exc:
        reason = 'REPO_INVENTORY_DISK_FULL' if exc.errno in {errno.ENOSPC, errno.EDQUOT} else 'REPO_INVENTORY_IO_FAILED'
        raise InventoryError(reason) from exc
    finally:
        run.metrics['duration_seconds'] = time.monotonic() - run.started
        if directory is not None and not keep_stage:
            shutil.rmtree(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator-profile', required=True, type=Path)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--budget', type=Path, help='Optional resource JSON; null stage/time limits mean no corpus ceiling')
    args = parser.parse_args(argv)
    receipt = {'schema': 'occ.repo-inventory-receipt.v1', 'state': 'FAILED',
               'repository': 'unknown', 'namespace': 'unknown',
               'snapshotId': None, 'repoSha': None, 'treeSha': None, 'total': None,
               'inventoryComplete': False, 'captureComplete': None, 'reused': False,
               'reason': None, 'processStopped': True,
               'proofScope': 'INVENTORY_ONLY_NO_CAPTURE_OR_EXPORT_PROOF'}
    try:
        if not args.operator_profile.is_absolute() or (args.budget and not args.budget.is_absolute()):
            raise InventoryError('DURABLE_ABSOLUTE_OPERATOR_PATH_REQUIRED')
        from native_adapter import operator_profile
        operator, _policy = operator_profile(args.operator_profile)
        alias = identifier(args.repository)
        receipt['repository'] = alias
        if alias not in operator.get('repositories', {}):
            raise InventoryError('REPO_OUTSIDE_OPERATOR_SCOPE')
        profile = operator['repositories'][alias]
        receipt['namespace'] = profile['namespace']
        receipt = inventory(Path(operator['store']), alias, profile,
                            budget=load_json(args.budget) if args.budget else None)
    except KeyboardInterrupt:
        receipt.update(state='CANCELLED', reason='CANCEL_REQUESTED')
    except (ValueError, OSError) as exc:
        reason = str(exc)
        receipt['reason'] = reason if re.fullmatch(r'[A-Z_]{1,100}', reason) else 'REPO_INVENTORY_IO_FAILED'
        receipt['processStopped'] = getattr(exc, 'process_stopped', True)
        if not receipt['processStopped']:
            receipt['state'] = 'BLOCKED'
        elif receipt['reason'] == 'CANCEL_REQUESTED':
            receipt['state'] = 'CANCELLED'
    print(json.dumps(receipt, separators=(',', ':'), allow_nan=False))
    return 0 if receipt['state'] == 'READY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
