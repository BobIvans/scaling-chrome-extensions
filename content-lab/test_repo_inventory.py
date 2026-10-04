"""Real Git/SQLite and fault-boundary tests for the PR004 inventory owner."""
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from unittest import TestCase, mock

import repo_context as repo
import repo_inventory as inv

FIXTURES = Path(__file__).parent / 'fixtures/pr004'


class InventoryTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root, self.store = self.base / 'repo', self.base / 'store'
        self.root.mkdir()
        self.profile = {'root': str(self.root), 'namespace': 'code', 'source_roots': ['.'], 'exclusions': []}
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.oid = self.git('hash-object', '-w', '--stdin', data=b'x').strip()
        self.make_tree(45)

    def git(self, *args, data=None, stdin=None):
        return subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, '-C', str(self.root), *args],
                              input=data, stdin=stdin, capture_output=True, check=True).stdout

    def make_tree(self, count, *, padding=0):
        with tempfile.TemporaryFile() as source:
            for i in range(count):
                path = f'f{i:08d}_'.encode() + b'x' * padding + b'.py'
                source.write(b'100644 blob ' + self.oid + b'\t' + path + b'\0')
            source.seek(0)
            tree = self.git('mktree', '-z', stdin=source).strip()
        head = self.git('commit-tree', tree.decode(), data=b'inventory fixture\n').strip()
        self.git('update-ref', 'HEAD', head.decode())
        return head.decode(), tree.decode()

    def rows(self, table):
        db = repo.db_for(self.store)
        try:
            return [tuple(r) for r in db.execute('SELECT * FROM ' + table)]
        finally:
            db.close()

    def assert_unpublished(self):
        self.assertEqual(self.rows('repo_snapshots'), [])
        self.assertEqual(self.rows('repo_entries'), [])
        self.assertEqual(self.rows('repo_heads'), [])
        self.assertEqual(list(self.store.glob('.occ-inventory-*')), [])

    @contextmanager
    def tree_process(self, code, *, stdout_error=False):
        original = subprocess.Popen
        children = []

        def launch(argv, **kwargs):
            if 'ls-tree' not in argv:
                return original(argv, **kwargs)
            child = original([sys.executable, '-u', '-c', code], **kwargs)
            children.append(child)
            if stdout_error:
                pipe = child.stdout
                class BrokenPipe:
                    def read1(self, _size):
                        raise OSError('synthetic pipe read fault')
                    def close(self):
                        pipe.close()
                child.stdout = BrokenPipe()
            return child

        with mock.patch.object(inv.subprocess, 'Popen', side_effect=launch):
            yield children
        self.assertTrue(all(c.poll() is not None for c in children))
        self.assertFalse(any(t.name == 'occ-git-inventory-pipe' for t in threading.enumerate()))

    def record(self, name=b'fake.py', *, oid=None):
        return b'100644 blob ' + (oid or self.oid) + b'       1\t' + name + b'\0'

    def test_identity_atomic_inventory_and_reuse_preserve_capture(self):
        head = self.git('rev-parse', 'HEAD').decode().strip()
        tree = self.git('rev-parse', head + '^{tree}').decode().strip()
        receipt = inv.inventory(self.store, 'sce', self.profile)
        self.assertEqual(receipt['snapshotId'], repo.digest({'alias': 'sce', 'profile': self.profile, 'head': head, 'tree': tree}))
        self.assertEqual(receipt['total'], 45)
        self.assertFalse(receipt['captureComplete'])
        self.assertEqual(receipt['proofScope'], 'INVENTORY_ONLY_NO_CAPTURE_OR_EXPORT_PROOF')
        self.assertEqual(self.rows('repo_heads'), [])
        status = None
        while status is None or status['cursor'] < 45:
            status = repo.scan_page(self.store, 'code', receipt['snapshotId'], limit=20)
        self.assertEqual(status['counts'], {'INDEXED': 45})
        before = {t: self.rows(t) for t in ('repo_snapshots', 'repo_entries', 'repo_chunks', 'repo_heads')}
        reused = inv.inventory(self.store, 'sce', self.profile)
        self.assertTrue(reused['reused'])
        self.assertIsNone(reused['captureComplete'])
        self.assertEqual(before, {t: self.rows(t) for t in before})
        self.assertEqual(repo.start_scan(self.store, 'sce', self.profile), receipt['snapshotId'])

    def test_golden_one_byte_random_all_split_boundaries_and_exact_paths(self):
        raw = (FIXTURES / 'LS_TREE_OUTPUT.bin').read_bytes()
        expected = json.loads((FIXTURES / 'EXPECTED_ENTRIES.json').read_text())['entries']
        rng = random.Random(4)
        splits, offset = [], 0
        while offset < len(raw):
            n = rng.randint(1, 200)
            splits.append(raw[offset:offset + n])
            offset += n
        cases = [[bytes([b]) for b in raw], splits, [raw]]
        cases.extend([raw[:cut], raw[cut:]] for cut in range(len(raw) + 1))
        for blocks in cases:
            run = inv.Run(None)
            entries = [inv.parse_record(r, 40, self.profile) for r in inv.records(blocks, run)]
            self.assertEqual(len(entries), 55)
            for row, want in zip(entries, expected):
                self.assertEqual(row, tuple(want[k] for k in ('path', 'mode', 'kind', 'oid', 'size', 'state', 'reason'))
                                 + (base64.b64decode(want['path_b64']),))
            self.assertEqual(run.metrics['stdout_bytes'], 4074)

    def test_real_large_tree_above_32_mib_preserves_every_ordinal(self):
        head, tree = self.make_tree(160000, padding=210)
        metrics = {}
        receipt = inv.inventory(self.store, 'sce', self.profile, metrics=metrics)
        self.assertEqual(receipt['total'], 160000)
        self.assertEqual((receipt['repoSha'], receipt['treeSha']), (head, tree))
        self.assertEqual(metrics['stdout_bytes'], 45600000)
        self.assertGreater(metrics['stdout_bytes'], 32 * 1024 * 1024)
        self.assertLessEqual(metrics['max_batch_rows'], 256)
        self.assertLessEqual(metrics['max_batch_bytes'], 262144)
        db = repo.db_for(self.store)
        try:
            count, first, last = db.execute('SELECT count(*),min(ordinal),max(ordinal) FROM repo_entries').fetchone()
            self.assertEqual((count, first, last), (160000, 0, 159999))
            self.assertEqual(db.execute('SELECT path FROM repo_entries WHERE ordinal=159999').fetchone()[0],
                             'f00159999_' + 'x' * 210 + '.py')
        finally:
            db.close()
        self.assertEqual(list(self.store.glob('.occ-inventory-*')), [])

    def test_arbitrary_names_missing_size_links_and_protected_metadata(self):
        raw = (FIXTURES / 'LS_TREE_OUTPUT.bin').read_bytes()
        # Missing objects may produce Git's documented BAD size marker.
        raw += b'100644 blob ' + self.oid + b' BAD\tmissing.py\0'
        raw += self.record(b'long-' + b'x' * 900)
        with self.tree_process('import sys;sys.stdout.buffer.write(' + repr(raw) + ')'):
            receipt = inv.inventory(self.store, 'sce', self.profile)
        self.assertEqual(receipt['total'], 57)
        db = repo.db_for(self.store)
        try:
            rows = {r['path']: dict(r) for r in db.execute('SELECT * FROM repo_entries')}
            self.assertIn('folder/a\tb\nc.py', rows)
            self.assertEqual(rows['missing.py']['reason'], 'BLOB_SIZE_UNAVAILABLE')
            self.assertEqual(rows['source-link']['reason'], 'LINK_OR_SUBMODULE_METADATA_ONLY')
            self.assertEqual(rows['.env.local']['reason'], 'PROTECTED_NAME_OR_OPERATOR_EXCLUSION')
            self.assertEqual(rows['oversize.dat']['state'], 'PENDING')
            self.assertIn('git-path-hex:' + (b'long-' + b'x' * 900).hex(), rows)
            self.assertTrue(all(r['reason'] == 'UNSUPPORTED_PATH' for p, r in rows.items() if p.startswith('git-path-hex:')))
        finally:
            db.close()

    def test_malformed_empty_duplicate_oid_mode_size_and_eof_never_publish(self):
        good = self.record()
        faults = [b'\0', good[:-1], b'nonsense\tx\0',
                  good.replace(b'100644', b'100666'), good.replace(b'blob', b'commit'),
                  good.replace(self.oid, b'g' * 40), good.replace(self.oid, b'a' * 64),
                  good.replace(b'       1', b' -1'), good.replace(b'       1', b' -'),
                  good.replace(b'       1', b' 999999999999999999999999'), good + good]
        for raw in faults:
            with self.subTest(raw=raw[:80]), self.tree_process('import sys;sys.stdout.buffer.write(' + repr(raw) + ')'):
                with self.assertRaisesRegex(inv.InventoryError, 'STREAM_MALFORMED'):
                    inv.inventory(self.store, 'sce', self.profile)
            self.assert_unpublished()

    def test_record_guard_before_unbounded_pending_allocation(self):
        budget = inv.DEFAULT_BUDGET | {'max_record_bytes': 1024}
        with self.tree_process('import sys;sys.stdout.buffer.write(b"x"*100000)'):
            with self.assertRaisesRegex(inv.InventoryError, 'RECORD_LIMIT'):
                inv.inventory(self.store, 'sce', self.profile, budget=budget)
        self.assert_unpublished()

    def test_nonzero_child_after_valid_stream_and_reader_fault(self):
        for code, fault in [('import sys;sys.stdout.buffer.write(' + repr(self.record()) + ');sys.stdout.flush();sys.exit(7)', False),
                            ('import time;time.sleep(30)', True)]:
            with self.tree_process(code, stdout_error=fault):
                with self.assertRaisesRegex(inv.InventoryError, 'GIT_READ_FAILED'):
                    inv.inventory(self.store, 'sce', self.profile)
            self.assert_unpublished()

    def test_quiet_child_timeout_stops_and_reaps_in_cleanup_budget(self):
        start = time.monotonic()
        with self.tree_process('import time;time.sleep(30)'):
            with self.assertRaisesRegex(inv.InventoryError, 'TIMEOUT'):
                inv.inventory(self.store, 'sce', self.profile, budget=inv.DEFAULT_BUDGET | {'timeout_seconds': 1})
        self.assertLess(time.monotonic() - start, 7)
        self.assert_unpublished()

    def test_stderr_flood_is_bounded_and_valid_stderr_does_not_deadlock(self):
        metrics = {}
        with self.tree_process('import sys;sys.stderr.buffer.write(b"x"*2000000);sys.stderr.flush();sys.stdout.buffer.write(' + repr(self.record()) + ')'):
            with self.assertRaisesRegex(inv.InventoryError, 'STDERR_LIMIT'):
                inv.inventory(self.store, 'sce', self.profile, metrics=metrics)
        self.assertLessEqual(metrics['stderr_retained_bytes'], 8192)
        self.assert_unpublished()
        with self.tree_process('import sys;sys.stderr.buffer.write(b"x"*65536);sys.stderr.flush();sys.stdout.buffer.write(' + repr(self.record()) + ')'):
            self.assertEqual(inv.inventory(self.store, 'sce', self.profile)['total'], 1)

    def test_cancel_with_backpressure_and_fresh_restart(self):
        cancel, ticks = threading.Event(), [0]
        code = 'import sys\nfor n in range(1000000):\n sys.stdout.buffer.write(b"100644 blob ' + self.oid.decode() + ' 1\\tf%08d.py\\0"%n)\n'
        with self.tree_process(code) as children:
            def progress():
                if children:
                    ticks[0] += 1
                    if ticks[0] > 4:
                        cancel.set()
            with self.assertRaisesRegex(inv.InventoryError, 'CANCEL_REQUESTED'):
                inv.inventory(self.store, 'sce', self.profile, cancel=cancel, progress=progress)
        self.assert_unpublished()
        self.assertEqual(inv.inventory(self.store, 'sce', self.profile)['total'], 45)

    def test_stage_quota_and_disk_full_fault_preserve_previous_owner(self):
        receipt = inv.inventory(self.store, 'sce', self.profile)
        repo.scan_page(self.store, 'code', receipt['snapshotId'], limit=100)
        before = {t: self.rows(t) for t in ('repo_snapshots', 'repo_entries', 'repo_chunks', 'repo_heads')}
        self.make_tree(46)
        with self.assertRaisesRegex(inv.InventoryError, 'STAGE_LIMIT'):
            inv.inventory(self.store, 'sce', self.profile, budget=inv.DEFAULT_BUDGET | {'stage_max_bytes': 1048576})
        exc = sqlite3.OperationalError('synthetic disk full')
        exc.sqlite_errorcode = sqlite3.SQLITE_FULL
        with mock.patch.object(inv, 'publish', side_effect=exc):
            with self.assertRaisesRegex(inv.InventoryError, 'DISK_FULL'):
                inv.inventory(self.store, 'sce', self.profile)
        self.assertEqual(before, {t: self.rows(t) for t in before})
        self.assertEqual(list(self.store.glob('.occ-inventory-*')), [])

    def test_publication_abort_rolls_back_snapshot_and_entries(self):
        db = repo.db_for(self.store)
        db.executescript('CREATE TRIGGER abort_inventory BEFORE INSERT ON repo_entries WHEN NEW.ordinal=21 BEGIN SELECT RAISE(ABORT,"injected publication fault"); END;')
        db.close()
        with self.assertRaisesRegex(inv.InventoryError, 'STREAM_MALFORMED'):
            inv.inventory(self.store, 'sce', self.profile)
        self.assert_unpublished()

    def test_second_connection_sees_none_then_all(self):
        db = repo.db_for(self.store)
        observed = []
        try:
            def progress():
                observed.append(db.execute('SELECT count(*) FROM repo_snapshots').fetchone()[0])
                self.assertEqual(db.execute('SELECT count(*) FROM repo_entries').fetchone()[0], 0)
            receipt = inv.inventory(self.store, 'sce', self.profile, progress=progress)
            self.assertTrue(observed)
            self.assertEqual(set(observed), {0})
            self.assertEqual(db.execute('SELECT count(*) FROM repo_entries').fetchone()[0], 45)
            self.assertEqual(db.execute('SELECT cursor FROM repo_snapshots WHERE id=?', (receipt['snapshotId'],)).fetchone()[0], 0)
        finally:
            db.close()

    def test_head_drift_rollback_and_tree_resolution_uses_pinned_head(self):
        original = inv.publish
        observed = []
        original_launch = subprocess.Popen
        def launch(argv, **kwargs):
            observed.append(argv)
            return original_launch(argv, **kwargs)
        def drift(*args):
            self.make_tree(46)
            return original(*args)
        with mock.patch.object(inv, 'publish', side_effect=drift), mock.patch.object(inv.subprocess, 'Popen', side_effect=launch):
            with self.assertRaisesRegex(inv.InventoryError, 'SOURCE_DRIFT'):
                inv.inventory(self.store, 'sce', self.profile)
        self.assertTrue(any(a[-1].endswith('^{tree}') and a[-1] != 'HEAD^{tree}' for a in observed))
        self.assertTrue(all(a[-1] != 'HEAD' for a in observed if 'ls-tree' in a))
        self.assert_unpublished()

    def test_corrupt_existing_identity_is_not_silently_repaired(self):
        for mutation in ['DELETE FROM repo_entries WHERE ordinal=40',
                         'UPDATE repo_entries SET ordinal=60 WHERE ordinal=40',
                         'UPDATE repo_entries SET oid="' + 'a' * 40 + '" WHERE ordinal=40']:
            with self.subTest(mutation=mutation):
                receipt = inv.inventory(self.store, 'sce', self.profile)
                db = repo.db_for(self.store)
                with db:
                    db.execute(mutation)
                db.close()
                before = self.rows('repo_entries')
                with self.assertRaisesRegex(inv.InventoryError, 'CONTEXT_INCOMPLETE'):
                    inv.inventory(self.store, 'sce', self.profile)
                self.assertEqual(self.rows('repo_entries'), before)
                # Test-only explicit reset; production never repairs on read.
                db = repo.db_for(self.store)
                with db:
                    db.execute('DELETE FROM repo_entries')
                    db.execute('DELETE FROM repo_snapshots')
                db.close()

    def test_concurrent_writers_reuse_one_complete_identity(self):
        # Initialize schema before racing the two inventory publications.
        repo.db_for(self.store).close()
        original, barrier = inv.publish, threading.Barrier(2)
        results, errors = [], []
        def publish(*args):
            barrier.wait(timeout=10)
            return original(*args)
        def work():
            try:
                results.append(inv.inventory(self.store, 'sce', self.profile))
            except Exception as exc:
                errors.append(exc)
        with mock.patch.object(inv, 'publish', side_effect=publish):
            threads = [threading.Thread(target=work) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)
            self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(errors, [])
        self.assertEqual(sorted(r['reused'] for r in results), [False, True])
        self.assertEqual(len(self.rows('repo_snapshots')), 1)
        self.assertEqual(len(self.rows('repo_entries')), 45)

    def test_cli_scopes_and_default_has_no_total_stage_or_time_cap(self):
        policy = self.base / 'policy.json'
        policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'money_budget': 0, 'max_parallel': 1}))
        profile = self.base / 'profile.json'
        profile.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy), 'namespaces': ['code'], 'templates': {}, 'repositories': {'sce': self.profile}}))
        for alias, expected, code in [('sce', 'READY', 0), ('outside', 'FAILED', 2)]:
            result = subprocess.run([sys.executable, '-I', '-B', str(Path(inv.__file__)),
                                     '--operator-profile', str(profile), '--repository', alias], capture_output=True)
            receipt = json.loads(result.stdout)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertEqual(receipt['state'], expected)
            self.assertTrue(receipt['processStopped'])
        self.assertIsNone(inv.validate_budget(None)['timeout_seconds'])
        self.assertIsNone(inv.validate_budget(None)['stage_max_bytes'])
        for value in [inv.DEFAULT_BUDGET | {'extra': 1}, inv.DEFAULT_BUDGET | {'read_block_bytes': True},
                      inv.DEFAULT_BUDGET | {'stderr_retained_bytes': 65536, 'stderr_total_bytes': 1024}]:
            with self.assertRaisesRegex(inv.InventoryError, 'BUDGET_REQUIRED'):
                inv.validate_budget(value)
        with self.assertRaisesRegex(inv.InventoryError, 'OUTSIDE_SOURCE'):
            inv.inventory(self.root / 'store', 'sce', self.profile)
        with mock.patch.dict(os.environ, {'GIT_CONFIG_COUNT': '1', 'GIT_DIR': '/untrusted', 'GIT_CONFIG_KEY_0': 'core.hooksPath'}):
            self.assertNotIn('GIT_DIR', inv.git_environment())
            self.assertEqual(inv.git_environment()['GIT_NO_LAZY_FETCH'], '1')

    def test_empty_tree_and_sha256_object_format(self):
        self.make_tree(0)
        receipt = inv.inventory(self.store, 'sce', self.profile)
        self.assertEqual(receipt['total'], 0)
        self.assertTrue(inv.inventory(self.store, 'sce', self.profile)['reused'])
        root = self.base / 'sha256'
        root.mkdir()
        result = subprocess.run(['git', '-C', str(root), 'init', '-q', '--object-format=sha256'], capture_output=True)
        if result.returncode:
            self.skipTest('Installed Git lacks SHA256 object format')
        self.root = root
        self.git('config', 'user.name', 'Synthetic Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.oid = self.git('hash-object', '-w', '--stdin', data=b'x').strip()
        self.make_tree(2)
        profile = self.profile | {'root': str(root)}
        receipt = inv.inventory(self.store, 'sce', profile)
        self.assertEqual(len(receipt['repoSha']), 64)
        self.assertEqual(receipt['total'], 2)

    def test_sqlite_writer_busy_is_bounded_by_inventory_deadline(self):
        blocker = repo.db_for(self.store)
        blocker.execute('BEGIN IMMEDIATE')
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(inv.InventoryError, 'TIMEOUT|STORE_BUSY'):
                inv.inventory(self.store, 'sce', self.profile, budget=inv.DEFAULT_BUDGET | {'timeout_seconds': 1})
            self.assertLess(time.monotonic() - started, 3)
        finally:
            blocker.rollback()
            blocker.close()
        self.assert_unpublished()

    def test_scan_run_and_inventory_share_rollback_and_bounded_reader(self):
        original = inv.stage_inventory
        called = []
        def stage(*args):
            called.append(True)
            return original(*args)
        db = repo.db_for(self.store)
        db.executescript('CREATE TRIGGER abort_scan_intent BEFORE INSERT ON repo_scan_runs BEGIN SELECT RAISE(ABORT,"injected intent fault"); END;')
        db.close()
        with mock.patch.object(inv, 'stage_inventory', side_effect=stage):
            with self.assertRaises(sqlite3.IntegrityError):
                repo.scan_run(self.store, 'sce', self.profile, 'START', intentKey='a' * 32)
        self.assertTrue(called)
        self.assert_unpublished()
        self.assertEqual(self.rows('repo_scan_runs'), [])

    def test_actual_sqlite_full_during_publish_rolls_back_previous_head(self):
        receipt = inv.inventory(self.store, 'sce', self.profile)
        repo.scan_page(self.store, 'code', receipt['snapshotId'], limit=100)
        before = {t: self.rows(t) for t in ('repo_snapshots', 'repo_entries', 'repo_chunks', 'repo_heads')}
        self.make_tree(1000, padding=210)
        original = inv.Run.configure
        def configure(run, db):
            original(run, db)
            filename = db.execute('PRAGMA database_list').fetchone()[2]
            if filename == str(self.store / 'content.sqlite3'):
                pages = db.execute('PRAGMA page_count').fetchone()[0]
                db.execute('PRAGMA max_page_count=' + str(pages))
        with mock.patch.object(inv.Run, 'configure', new=configure):
            with self.assertRaisesRegex(inv.InventoryError, 'DISK_FULL'):
                inv.inventory(self.store, 'sce', self.profile)
        self.assertEqual(before, {t: self.rows(t) for t in before})
        self.assertEqual(list(self.store.glob('.occ-inventory-*')), [])
