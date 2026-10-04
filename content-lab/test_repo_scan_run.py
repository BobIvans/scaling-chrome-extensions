"""Whole-repository lifecycle, real Git/SQLite, native restart and scale tests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import repo_context as repo
import native_adapter
import test_repo_context as fixtures


class RepoScanRunTests(unittest.TestCase):
    setUp = fixtures.RepoContextTests.setUp
    git = fixtures.RepoContextTests.git
    put = fixtures.RepoContextTests.put
    commit = fixtures.RepoContextTests.commit

    def corpus(self):
        source = Path(__file__).parent / 'fixtures/full-repo-scan'
        for path in source.rglob('*'):
            if path.is_file():
                self.put(path.relative_to(source).as_posix(), path.read_bytes())
        self.commit()
        return {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*') if p.is_file()}

    def start(self, key='1' * 32):
        return repo.scan_run(self.store, 'sce', self.profile, 'START', intentKey=key)

    def act(self, run, action, **fields):
        if action != 'STATUS':
            fields.setdefault('expectedRevision', run['run_revision'])
        if action == 'STEP':
            fields.setdefault('expectedCursor', run['cursor'])
        return repo.scan_run(self.store, 'sce', self.profile, action, runId=run['run_id'], **fields)

    def finish(self, run):
        cursors = []
        while run['state'] == 'RUNNING':
            run = self.act(run, 'STEP')
            cursors.append(run['cursor'])
        self.assertEqual(run['state'], 'COMPLETE', run)
        return run, cursors

    def native_profile(self):
        policy = self.root / 'policy.json'
        policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'money_budget': 0, 'max_parallel': 1}))
        path = self.root / 'profile.json'
        path.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy), 'namespaces': ['code'], 'templates': {}, 'repositories': {'sce': self.profile}}))
        return path

    def native(self, action, **fields):
        result = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(Path(native_adapter.__file__)),
                                 '--profile', str(self.native_profile())],
                                input=json.dumps({'type': 'durable.repo.scanRun', 'repository': 'sce', 'action': action, **fields}).encode(),
                                capture_output=True, check=True)
        self.assertLessEqual(len(result.stdout), native_adapter.OUTPUT_BYTES)
        output = json.loads(result.stdout)
        self.assertTrue(output['ok'], output)
        return output['result']['scan_run']

    def test_45_file_corpus_three_commits_and_exact_tail(self):
        sources = self.corpus()
        run = self.start()
        self.assertEqual((run['ledger_entries'], run['processed'], run['pending']), (45, 0, 45))
        run, cursors = self.finish(run)
        self.assertEqual(cursors, [20, 40, 45])
        self.assertTrue(run['exact_for_indexed'])
        self.assertTrue(run['all_tracked_bytes_exportable'])
        self.assertEqual(run['ai_delivery'], 'NOT_PERFORMED')
        db = repo.db_for(self.store)
        try:
            for path, raw in sources.items():
                chunks = db.execute('SELECT raw FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (run['snapshot_id'], path))
                self.assertEqual(b''.join(c['raw'] for c in chunks), raw)
            self.assertEqual(db.execute('SELECT count(*) FROM repo_scan_runs').fetchone()[0], 1)
        finally:
            db.close()

    def test_start_and_lost_step_reply_are_idempotent(self):
        self.corpus()
        run = self.start()
        self.assertEqual(self.start()['run_id'], run['run_id'])
        with self.assertRaisesRegex(ValueError, 'ACTIVE_SCAN_EXISTS'):
            self.start('2' * 32)
        saved = self.act(run, 'STEP')
        replay = self.act(run, 'STEP')
        self.assertEqual(replay['cursor'], 20)
        db = repo.db_for(self.store)
        count = db.execute('SELECT count(*) FROM repo_chunks').fetchone()[0]
        db.close()
        self.act(run, 'STEP')
        db = repo.db_for(self.store)
        self.assertEqual(db.execute('SELECT count(*) FROM repo_chunks').fetchone()[0], count)
        db.close()
        with self.assertRaisesRegex(ValueError, 'CURSOR_AHEAD'):
            self.act(saved, 'STEP', expectedCursor=21)

    def test_precommit_crash_rolls_back_chunks_items_and_cursor(self):
        self.corpus()
        run = self.start()
        insert = repo._insert_item
        def fault(db, item):
            insert(db, item)
            raise RuntimeError('Injected process crash before commit')
        with mock.patch.object(repo, '_insert_item', side_effect=fault):
            with self.assertRaisesRegex(RuntimeError, 'Injected'):
                self.act(run, 'STEP')
        db = repo.db_for(self.store)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM repo_chunks').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM items').fetchone()[0], 0)
        finally:
            db.close()
        # Kill a real process after writing a source item inside the open page.
        script = "import os,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import repo_context as r;original=r._insert_item\ndef crash(db,item):\n original(db,item);os._exit(19)\nr._insert_item=crash;r.scan_run(Path(sys.argv[2]),'sce',__import__('json').loads(sys.argv[3]),'STEP',runId=sys.argv[4],expectedCursor=0,expectedRevision=0)"
        died = subprocess.run([sys.executable, '-I', '-c', script, str(Path(repo.__file__).parent), str(self.store), json.dumps(self.profile), run['run_id']], capture_output=True)
        self.assertEqual(died.returncode, 19, died.stderr)
        db = repo.db_for(self.store)
        self.assertEqual(db.execute('SELECT count(*) FROM items').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT count(*) FROM repo_chunks').fetchone()[0], 0)
        db.close()
        self.assertEqual(self.native('STATUS', runId=run['run_id'])['cursor'], 0)
        committed = self.native('STEP', runId=run['run_id'], expectedRevision=0, expectedCursor=0)
        self.assertEqual(committed['cursor'], 20)
        self.assertEqual(self.native('STATUS', runId=run['run_id'])['cursor'], 20)
        self.assertEqual(self.native('STEP', runId=run['run_id'], expectedRevision=0, expectedCursor=0)['cursor'], 20)

    def test_pause_reopen_explicit_continue_and_stale_unpause(self):
        self.corpus()
        first = self.act(self.start(), 'STEP')
        paused = self.act(first, 'PAUSE')
        self.assertEqual(self.act(first, 'PAUSE')['run_revision'], 1)
        restored = self.native('STATUS', runId=paused['run_id'])
        self.assertEqual((restored['state'], restored['cursor']), ('PAUSED', 20))
        self.assertEqual(self.act(restored, 'STEP')['cursor'], 20)
        with self.assertRaisesRegex(ValueError, 'SCAN_REVISION_STALE'):
            self.act(first, 'CONTINUE')
        resumed = self.act(restored, 'CONTINUE')
        self.assertEqual(resumed['run_revision'], 2)
        self.assertEqual(self.act(resumed, 'CONTINUE')['run_revision'], 2)
        self.assertEqual(self.finish(resumed)[1], [40, 45])

    def test_cancel_tombstone_replay_and_new_explicit_intent(self):
        self.corpus()
        first = self.act(self.start(), 'STEP')
        cancelled = self.act(first, 'CANCEL')
        self.assertEqual(self.act(first, 'CANCEL')['run_revision'], cancelled['run_revision'])
        self.assertEqual(self.native('START', intentKey='1' * 32)['state'], 'CANCELLED')
        self.assertEqual(self.act(first, 'CONTINUE')['state'], 'CANCELLED')
        self.assertEqual(self.act(first, 'STEP')['cursor'], 20)
        new = self.start('2' * 32)
        self.assertNotEqual(new['run_id'], cancelled['run_id'])
        self.assertEqual(new['snapshot_id'], cancelled['snapshot_id'])
        self.assertEqual(new['cursor'], 20)
        self.assertEqual(self.finish(new)[0]['cursor'], 45)
        self.assertEqual(self.act(cancelled, 'STATUS')['state'], 'CANCELLED')

    def test_source_drift_and_profile_scope_preserve_previous_page(self):
        self.corpus()
        first = self.act(self.start(), 'STEP')
        self.put('new.txt', b'new commit\n')
        self.commit()
        blocked = self.act(first, 'STEP')
        self.assertEqual((blocked['state'], blocked['reason'], blocked['cursor']), ('BLOCKED', 'SOURCE_DRIFT', 20))
        self.assertEqual(self.act(blocked, 'CONTINUE')['state'], 'BLOCKED')
        changed = dict(self.profile, exclusions=['files'])
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_OPERATOR_SCOPE'):
            repo.scan_run(self.store, 'sce', changed, 'STATUS', runId=first['run_id'])
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SCOPE'):
            repo.scan_run(self.store, 'sce', dict(self.profile, namespace='other'), 'STEP',
                          runId=first['run_id'], expectedCursor=20, expectedRevision=0)
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SCOPE'):
            repo.scan_run(self.store, 'other', self.profile, 'STATUS', runId=first['run_id'])

    def test_legacy_database_records_survive_additive_schema_and_reopen(self):
        self.corpus()
        sid = repo.start_scan(self.store, 'sce', self.profile)
        repo.scan_page(self.store, 'code', sid)
        db = repo.db_for(self.store)
        before = db.execute('SELECT count(*) FROM items').fetchone()[0]
        db.execute('DROP TABLE repo_scan_runs')
        for name in ['repo_count_insert', 'repo_count_delete', 'repo_count_update']:
            db.execute('DROP TRIGGER ' + name)
        db.execute('DROP TABLE repo_entry_counts')
        db.execute('DROP TABLE repo_count_migration')
        db.close()
        resumed = self.start()
        self.assertEqual(resumed['cursor'], 20)
        self.finish(resumed)
        db = repo.db_for(self.store)
        self.assertGreaterEqual(db.execute('SELECT count(*) FROM items').fetchone()[0], before)
        db.close()
        status = repo.get_snapshot(self.store, 'code', sid)
        self.assertEqual(status['state'], 'COMPLETE')
        exported = repo.export_request(self.store, 'code', sid, ['files/entry_000.txt'], 'Review', 'Selected source', ['Exact bytes'])
        self.assertEqual(exported['document']['context']['items'][0]['text'].encode(), (Path(__file__).parent / 'fixtures/full-repo-scan/files/entry_000.txt').read_bytes())
        self.assertEqual(self.native('STATUS')['state'], 'COMPLETE')

    def test_strict_native_actions_scope_and_no_caller_paths(self):
        self.corpus()
        profile = self.native_profile()
        base = {'type': 'durable.repo.scanRun', 'repository': 'sce', 'action': 'START', 'intentKey': 'a' * 32}
        run = native_adapter.dispatch(base, profile)['scan_run']
        for patch in [{'root': '/caller'}, {'expectedCursor': 0}, {'action': 'NONE'}, {'intentKey': 'bad'}]:
            with self.assertRaises(ValueError):
                native_adapter.dispatch(dict(base, **patch), profile)
        for bad in [True, -1, 1.5, repo.SAFE_INTEGER + 1]:
            with self.assertRaises(ValueError):
                native_adapter.dispatch({'type': base['type'], 'repository': 'sce', 'action': 'STEP',
                    'runId': run['run_id'], 'expectedCursor': bad, 'expectedRevision': 0}, profile)
        # Kill a real process after writing a source item inside the open page.
        script = "import os,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import repo_context as r;original=r._insert_item\ndef crash(db,item):\n original(db,item);os._exit(19)\nr._insert_item=crash;r.scan_run(Path(sys.argv[2]),'sce',__import__('json').loads(sys.argv[3]),'STEP',runId=sys.argv[4],expectedCursor=0,expectedRevision=0)"
        died = subprocess.run([sys.executable, '-I', '-c', script, str(Path(repo.__file__).parent), str(self.store), json.dumps(self.profile), run['run_id']], capture_output=True)
        self.assertEqual(died.returncode, 19, died.stderr)
        db = repo.db_for(self.store)
        self.assertEqual(db.execute('SELECT count(*) FROM items').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT count(*) FROM repo_chunks').fetchone()[0], 0)
        db.close()
        self.assertEqual(self.native('STATUS', runId=run['run_id'])['cursor'], 0)

    def test_empty_and_already_completed_snapshot_do_not_step(self):
        self.git('commit', '--allow-empty', '-qm', 'empty')
        empty = self.start()
        self.assertEqual((empty['state'], empty['total'], empty['cursor']), ('COMPLETE', 0, 0))
        self.assertTrue(empty['all_tracked_bytes_exportable'])
        db = repo.db_for(self.store)
        self.assertEqual(db.execute('SELECT snapshot_id FROM repo_heads').fetchone()[0], empty['snapshot_id'])
        db.close()
        self.put('file.txt', b'complete\n')
        self.commit()
        completed = self.finish(self.start('2' * 32))[0]
        again = self.start('3' * 32)
        self.assertEqual(again['state'], 'COMPLETE')
        self.assertEqual(again['snapshot_id'], completed['snapshot_id'])

    def test_read_gaps_and_metadata_do_not_claim_all_bytes_or_ai(self):
        self.put('a.txt', b'first\n')
        self.put('.env', b'private\n')
        self.put('binary.bin', bytes(range(256)))
        self.commit()
        self.git('update-index', '--add', '--cacheinfo', '120000', self.git('rev-parse', 'HEAD:a.txt').decode().strip(), 'link')
        self.git('commit', '-qm', 'link metadata')
        run = self.start()
        real = repo.git_stream
        def read_failure(root, *args):
            if args[:2] == ('cat-file', 'blob'):
                raise ValueError('REPO_GIT_READ_FAILED')
            yield from real(root, *args)
        with mock.patch.object(repo, 'git_stream', side_effect=read_failure):
            final = self.finish(run)[0]
        self.assertTrue(final['inventory_complete'])
        self.assertTrue(final['exact_for_indexed'])
        self.assertEqual((final['errors'], final['excluded']), (2, 2))
        self.assertFalse(final['all_tracked_bytes_exportable'])
        self.assertEqual(final['ai_delivery'], 'NOT_PERFORMED')

    def test_missing_ledger_blocks_completion(self):
        self.corpus()
        run = self.start()
        db = repo.db_for(self.store)
        with db:
            db.execute('DELETE FROM repo_entries WHERE ordinal=44')
        db.close()
        blocked = self.act(run, 'STEP')
        self.assertEqual((blocked['state'], blocked['reason'], blocked['cursor']), ('BLOCKED', 'CONTEXT_INCOMPLETE', 0))
        self.assertFalse(blocked['inventory_complete'])

    def test_ordinal_integrity_counter_projection_and_source_store_boundary(self):
        self.corpus()
        with self.assertRaisesRegex(ValueError, 'STORE_MUST_BE_OUTSIDE_SOURCE'):
            repo.scan_run(self.checkout / 'forbidden-store', 'sce', self.profile, 'START', intentKey='f' * 32)
        self.assertFalse((self.checkout / 'forbidden-store').exists())
        run = self.act(self.start(), 'STEP')
        db = repo.db_for(self.store)
        try:
            actual = dict(db.execute('SELECT state,count(*) FROM repo_entries GROUP BY state'))
            self.assertEqual(repo.entry_counts_db(db, run['snapshot_id']), actual)
            with db:
                db.execute('UPDATE repo_entries SET ordinal=100 WHERE ordinal=44')
        finally:
            db.close()
        blocked = self.act(run, 'STEP')
        self.assertEqual((blocked['state'], blocked['reason'], blocked['cursor']), ('BLOCKED', 'CONTEXT_INCOMPLETE', 20))
        # Offset is a page cursor, never a one-million-files repository cap.
        self.assertEqual(repo.get_snapshot(self.store, 'code', run['snapshot_id'], offset=1000001)['files'], [])

    def test_streaming_large_utf8_binary_and_split_secret_with_full_roundtrip(self):
        text = ('Я👋' * 1500000).encode() + b'\r\nFINAL_TAIL\n'
        binary = bytes(range(256)) * 40000
        secret = b' ' * (repo.STREAM_BYTES - 2) + b'api_key = "' + b'x' * (repo.STREAM_BYTES * 2) + b'"\n'
        self.put('large.txt', text)
        self.put('binary.bin', binary)
        self.put('secret.txt', secret)
        self.commit()
        run = self.finish(self.start())[0]
        self.assertEqual((run['indexed'], run['excluded'], run['errors']), (2, 1, 0))
        self.assertTrue(run['exact_for_indexed'])
        db = repo.db_for(self.store)
        try:
            for name, raw in [('large.txt', text), ('binary.bin', binary)]:
                hasher, total = hashlib.sha256(), 0
                for chunk in db.execute('SELECT raw FROM repo_chunks WHERE path=? ORDER BY ordinal', (name,)):
                    hasher.update(chunk['raw'])
                    total += len(chunk['raw'])
                    self.assertLessEqual(len(chunk['raw']), repo.CHUNK_BYTES)
                    if name == 'large.txt':
                        chunk['raw'].decode('utf-8')
                self.assertEqual(total, len(raw))
                self.assertEqual(hasher.digest(), hashlib.sha256(raw).digest())
            self.assertEqual(db.execute("SELECT count(*) FROM repo_chunks WHERE path='secret.txt'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM repo_chunks WHERE path='binary.bin' AND item_id IS NOT NULL").fetchone()[0], 0)
        finally:
            db.close()

    def test_tree_larger_than_previous_32_mib_cap_has_complete_inventory(self):
        count = 125000
        process = subprocess.Popen(['git', '-C', str(self.checkout), 'fast-import', '--quiet'], stdin=subprocess.PIPE,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        process.stdin.write(b'blob\nmark :1\ndata 2\nx\n\ncommit refs/heads/large\ncommitter Fixture <fixture@example.invalid> 1 +0000\ndata 5\nlarge\n')
        for i in range(count):
            name = f'file_{i:06}_' + 'x' * 230 + '.txt'
            process.stdin.write(f'M 100644 :1 {name}\n'.encode())
        process.stdin.write(b'\ndone\n')
        process.stdin.close()
        errors = process.stderr.read()
        process.stderr.close()
        self.assertEqual(process.wait(), 0, errors)
        self.git('symbolic-ref', 'HEAD', 'refs/heads/large')
        tree_bytes = sum(len(record) + 1 for record in repo.git_records(self.checkout, 'ls-tree', '-r', '-z', '-l', '--full-tree', 'HEAD'))
        self.assertGreater(tree_bytes, 32 * 1024 * 1024)
        print(f'SCALE_EVIDENCE files={count} git_tree_output_bytes={tree_bytes}', flush=True)
        run = self.native('START', intentKey='f' * 32)
        self.assertEqual((run['total'], run['ledger_entries'], run['pending']), (count, count, count))
        self.assertEqual(run['processed'], 0)
        self.assertEqual(self.native('CANCEL', runId=run['run_id'], expectedRevision=0)['state'], 'CANCELLED')


if __name__ == '__main__':
    unittest.main()
