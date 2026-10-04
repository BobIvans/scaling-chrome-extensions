import copy
import errno
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest import TestCase, mock

import automation_core as core
import native_adapter
import repo_context as repo
import repo_manifest as manifest
import test_repo_context


class RepoManifestTests(TestCase):
    # Reuse real Git/SQLite fixture helpers without inheriting the regression suite.
    setUp = test_repo_context.RepoContextTests.setUp
    git = test_repo_context.RepoContextTests.git
    put = test_repo_context.RepoContextTests.put
    commit = test_repo_context.RepoContextTests.commit
    scan = test_repo_context.RepoContextTests.scan

    def capture(self, sources=None):
        for path, raw in (sources or {'empty.txt': b'', 'main.txt': ('Я👋' * 16000).encode()}).items():
            self.put(path, raw)
        self.commit()
        self.status = self.scan()
        self.sid = self.status['snapshot_id']
        return self.status

    def publish(self, name='manifest'):
        output = self.root / name
        result = manifest.publish(self.store, 'code', self.sid, 'sce', self.profile, output)
        return output, result

    def page(self, action, **kwargs):
        return manifest.page(self.store, 'code', self.sid, 'sce', self.profile, action, **kwargs)

    def rows(self, action, **kwargs):
        offset, result = 0, []
        while True:
            page = self.page(action, offset=offset, **kwargs)
            self.assertLessEqual(manifest.native_frame_size(page), 32768)
            result.extend(page['rows'])
            if page['nextOffset'] is None:
                return result
            self.assertEqual(page['nextOffset'], offset + len(page['rows']))
            offset = page['nextOffset']

    def jsonl(self, output, name):
        return [json.loads(row) for row in (output / name).read_text(encoding='utf-8').splitlines()]

    def mutate(self, sql, args=()):
        db = repo.db_for(self.store)
        try:
            with db:
                db.execute(sql, args)
        finally:
            db.close()

    def profile_file(self):
        policy = self.root / 'policy.json'
        policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'max_parallel': 1, 'money_budget': 0}), encoding='utf-8')
        path = self.root / 'native-profile.json'
        path.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy), 'namespaces': ['code'], 'templates': {},
            'repositories': {'sce': self.profile}}), encoding='utf-8')
        return path

    def test_50_entry_inventory_every_part_and_both_lookup_directions(self):
        self.profile['exclusions'] = ['operator']
        sources = {f'src/{n:03}.txt': f'source {n}\n'.encode() for n in range(41)}
        sources.update({'empty.txt': b'', 'long.txt': ('Я👋' * 23000 + '\r\nTAIL').encode(),
                        'binary.bin': bytes(range(256)) * 32, 'bom.txt': b'\xef\xbb\xbfhi\r\n',
                        'text.txt': b'ordinary text\n', '.env': b'protected value',
                        'operator/private.txt': b'operator-private value'})
        for path, raw in sources.items():
            self.put(path, raw)
        self.commit()
        head = self.git('rev-parse', 'HEAD').decode().strip()
        blob = subprocess.run(['git', '-C', str(self.checkout), 'hash-object', '-w', '--stdin'], input=b'target', capture_output=True, check=True).stdout.decode().strip()
        self.git('update-index', '--add', '--cacheinfo', f'160000,{head},submodule')
        self.git('update-index', '--add', '--cacheinfo', f'120000,{blob},link')
        self.git('commit', '-qm', 'metadata-only objects')
        self.status = self.scan()
        self.sid = self.status['snapshot_id']
        self.assertEqual(self.status['total'], 50)
        self.assertEqual(self.status['counts'], {'INDEXED': 46, 'EXCLUDED': 4})
        output, _ = self.publish()
        entries = self.jsonl(output, 'REPO_MANIFEST.jsonl')
        parts = self.jsonl(output, 'PARTS_INDEX.jsonl')
        self.assertEqual(entries, self.rows('ENTRIES'))
        self.assertEqual(parts, self.rows('PARTS'))
        self.assertEqual(len(entries), 50)
        db = repo.db_for(self.store)
        try:
            original = list(db.execute('SELECT * FROM repo_entries WHERE snapshot_id=? ORDER BY ordinal', (self.sid,)))
            for entry, stored in zip(entries, original):
                for key, column in [('ordinal', 'ordinal'), ('path', 'path'), ('state', 'state'), ('reason', 'reason'), ('git_oid', 'oid'), ('mode', 'mode'), ('size', 'size')]:
                    self.assertEqual(entry[key], stored[column])
                source_parts = self.rows('PARTS', file_ordinal=entry['ordinal'])
                self.assertEqual(source_parts, [p for p in parts if p['file_ordinal'] == entry['ordinal']])
                if entry['state'] == 'INDEXED':
                    chunks = list(db.execute('SELECT * FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (self.sid, entry['path'])))
                    self.assertEqual(b''.join(c['raw'] for c in chunks), sources[entry['path']])
                    self.assertEqual([p['source_start'] for p in source_parts], [c['byte_start'] for c in chunks])
                    self.assertEqual([p['source_end'] for p in source_parts], [c['byte_end'] for c in chunks])
                    self.assertEqual([p['part_id'] for p in source_parts], [c['revision'] for c in chunks])
        finally:
            db.close()
        long = next(e for e in entries if e['path'] == 'long.txt')
        self.assertGreater(long['chunk_count'], 20)
        binary = next(e for e in entries if e['path'] == 'binary.bin')
        self.assertTrue(all(not p['text_eligible'] for p in self.rows('PARTS', file_ordinal=binary['ordinal'])))
        empty = next(p for p in parts if p['path'] == 'empty.txt')
        self.assertEqual((empty['source_start'], empty['source_end'], empty['sha256']), (0, 0, repo.sha(b'')))
        self.assertNotIn(b'protected value', (output / 'REPO_MANIFEST.jsonl').read_bytes())
        batch = json.loads((output / 'BATCH.json').read_text())
        self.assertFalse(batch['all_tracked_bytes_exportable'])

    def test_deterministic_binding_output_hashes_and_reuse(self):
        self.capture()
        first, result = self.publish('one')
        second, _ = self.publish('two')
        for name in manifest.ARTIFACTS:
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
        batch = json.loads((first / 'BATCH.json').read_text())
        self.assertEqual(batch['batch_id'], core.digest(batch['binding']))
        changed = copy.deepcopy(batch['binding'])
        changed['export_policy'] = 'NEXT_POLICY'
        self.assertNotEqual(core.digest(changed), result['batch_id'])
        for record in batch['outputs']:
            self.assertEqual(manifest.file_digest(first / record['path']), (record['bytes'], record['sha256']))
        self.assertTrue(self.publish('one')[1]['reused'])
        self.assertFalse(list(self.root.glob('.occ-manifest-*')))
        self.assertNotIn(str(self.checkout), (first / 'BATCH.json').read_text())
        self.assertNotIn(str(self.store), (first / 'BATCH.json').read_text())

    def test_info_and_page_do_not_claim_full_byte_or_ai_proof(self):
        self.capture()
        info, parts = self.page('INFO'), self.page('PARTS')
        self.assertEqual(info['global_validation'], 'NOT_RUN')
        self.assertIsNone(info['raw_exact_for_indexed'])
        self.assertEqual(parts['proof_scope'], 'RETURNED_PART_ROWS_ONLY_GLOBAL_NOT_RUN')
        self.assertEqual(parts['dependencies'], 'NOT_GENERATED')
        self.assertFalse(parts['ai_packet_included'])
        self.assertEqual(parts['ai_read'], 'UNKNOWN')
        self.assertTrue(all('raw' not in r for r in parts['rows']))
        self.assertEqual(info['binding']['goal_revision'], None)

    def test_pending_deleted_entry_and_noncontiguous_inventory_are_refused(self):
        self.put('a.txt', b'hello')
        self.commit()
        self.sid = repo.start_scan(self.store, 'sce', self.profile)
        with self.assertRaisesRegex(ValueError, 'CONTEXT_INCOMPLETE'):
            self.publish()
        repo.scan_page(self.store, 'code', self.sid)
        self.mutate('UPDATE repo_entries SET ordinal=5 WHERE snapshot_id=?', (self.sid,))
        with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
            self.publish()
        self.mutate('DELETE FROM repo_entries WHERE snapshot_id=?', (self.sid,))
        with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
            self.publish()
        self.assertFalse((self.root / 'manifest').exists())

    def test_ranges_raw_revisions_missing_orphan_and_duplicate_parts_fail(self):
        self.capture({'main.txt': b'a' * 16000})
        db = repo.db_for(self.store)
        original = list(db.execute('SELECT * FROM repo_chunks WHERE snapshot_id=? ORDER BY ordinal', (self.sid,)))
        db.close()
        mutations = [
            ("UPDATE repo_chunks SET byte_start=byte_start+1 WHERE ordinal=1", ()),
            ("UPDATE repo_chunks SET byte_start=byte_start-1 WHERE ordinal=1", ()),
            ("UPDATE repo_chunks SET raw=? WHERE ordinal=1", (b'x',)),
            ("UPDATE repo_chunks SET revision=? WHERE ordinal=1", ('0' * 64,)),
            ("UPDATE repo_chunks SET ordinal=99 WHERE ordinal=1", ()),
            ("DELETE FROM repo_chunks WHERE ordinal=1", ()),
            ("UPDATE repo_chunks SET path='orphan.txt' WHERE ordinal=1", ()),
            ("UPDATE repo_chunks SET revision=? WHERE ordinal=1", (original[0]['revision'],)),
            ("UPDATE repo_chunks SET raw=? WHERE ordinal=1", (b'b' * len(original[1]['raw']),)),
        ]
        for sql, args in mutations:
            with self.subTest(sql=sql):
                self.mutate(sql, args)
                with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
                    self.publish()
                self.assertFalse((self.root / 'manifest').exists())
                db = repo.db_for(self.store)
                with db:
                    db.execute('DELETE FROM repo_chunks WHERE snapshot_id=?', (self.sid,))
                    db.executemany('INSERT INTO repo_chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', [tuple(r) for r in original])
                db.close()

    def test_consistently_forged_raw_hash_revision_still_fails_original_git_oid(self):
        self.capture({'main.txt': b'original'})
        raw = b'forged!!'
        db = repo.db_for(self.store)
        chunk = db.execute('SELECT * FROM repo_chunks').fetchone()
        with db:
            db.execute('UPDATE repo_entries SET file_hash=?,size=?', (repo.sha(raw), len(raw)))
            db.execute('UPDATE repo_chunks SET raw=?,item_id=NULL,byte_end=?,revision=?',
                       (raw, len(raw), core.digest([chunk['logical_id'], repo.sha(raw), repo.sha(raw), 0, len(raw)])))
        db.close()
        with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
            self.publish()

    def test_text_item_tamper_and_nonindexed_raw_are_refused(self):
        self.capture({'main.txt': b'original'})
        db = repo.db_for(self.store)
        row = db.execute('SELECT * FROM items').fetchone()
        payload = json.loads(row['payload'])
        payload['text'] = 'changed'
        with db:
            db.execute('UPDATE items SET payload=? WHERE id=?', (json.dumps(payload), row['id']))
        db.close()
        with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
            self.page('PARTS')
        with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
            self.publish()
        self.mutate("UPDATE repo_entries SET state='EXCLUDED'")
        with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
            self.publish()

    def test_one_read_view_and_historical_bytes_never_read_git_or_worktree(self):
        self.capture({'main.txt': b'pinned'})
        self.put('main.txt', b'later HEAD')
        self.commit()
        original = manifest.Output.write
        changed = False

        def concurrent_write(out, value):
            nonlocal changed
            original(out, value)
            if not changed and out.path.name == 'REPO_MANIFEST.jsonl':
                changed = True
                self.mutate("UPDATE repo_entries SET file_hash=? WHERE snapshot_id=?", ('0' * 64, self.sid))

        with mock.patch.object(repo, 'git', side_effect=AssertionError('Git read forbidden')), mock.patch.object(repo, 'working_state', side_effect=AssertionError('Working tree read forbidden')), mock.patch.object(manifest.Output, 'write', concurrent_write):
            output, _ = self.publish()
        self.assertTrue(changed)
        self.assertEqual(self.jsonl(output, 'REPO_MANIFEST.jsonl')[0]['file_sha256'], repo.sha(b'pinned'))
        self.assertEqual(json.loads((output / 'BATCH.json').read_text())['binding']['repo_sha'], self.status['repo_sha'])

    def test_interrupt_disk_full_damaged_target_never_publish_or_overwrite(self):
        self.capture({'main.txt': b'original'})
        original = manifest.Output.write
        for fault in [KeyboardInterrupt(), OSError(errno.ENOSPC, 'full')]:
            for artifact in manifest.ARTIFACTS:
                def fail(out, value):
                    if out.path.name == artifact:
                        raise fault
                    return original(out, value)
                with self.subTest(fault=type(fault).__name__, artifact=artifact), mock.patch.object(manifest.Output, 'write', fail):
                    with self.assertRaises(type(fault)):
                        self.publish()
                self.assertFalse((self.root / 'manifest').exists())
                self.assertFalse(list(self.root.glob('.occ-manifest-*')))
        output, _ = self.publish()
        (output / 'PARTS_INDEX.jsonl').write_bytes(b'corruption')
        with self.assertRaisesRegex(ValueError, 'MANIFEST_OUTPUT_CORRUPT'):
            self.publish()
        self.assertEqual((output / 'PARTS_INDEX.jsonl').read_bytes(), b'corruption')

    def test_empty_tree_empty_file_and_escaped_portable_names(self):
        self.git('commit', '--allow-empty', '-qm', 'empty')
        self.status = self.scan()
        self.sid = self.status['snapshot_id']
        output, _ = self.publish('empty-tree')
        self.assertEqual((output / 'REPO_MANIFEST.jsonl').read_bytes(), b'')
        self.assertEqual((output / 'PARTS_INDEX.jsonl').read_bytes(), b'')
        self.assertEqual(self.rows('ENTRIES'), [])
        # Stage unusual paths directly so the fixture also runs on Windows.
        blob = subprocess.run(['git', '-C', str(self.checkout), 'hash-object', '-w', '--stdin'], input=b'hello', capture_output=True, check=True).stdout.decode().strip()
        path = 'РУ\tline\n"quote".txt'
        # Build the immutable tree directly: these Git names cannot be checked
        # out on Windows, and its index path validator correctly refuses them.
        tree_raw = b'100644 ' + path.encode('utf-8') + b'\0' + bytes.fromhex(blob)
        tree = subprocess.run(['git', '-C', str(self.checkout), 'hash-object', '-t', 'tree', '-w', '--stdin'], input=tree_raw, capture_output=True, check=True).stdout.decode().strip()
        commit = self.git('commit-tree', tree, '-m', 'escaped path').decode().strip()
        self.git('update-ref', 'HEAD', commit)
        self.status = self.scan()
        self.sid = self.status['snapshot_id']
        output, _ = self.publish('escaped')
        self.assertEqual(len((output / 'REPO_MANIFEST.jsonl').read_bytes().splitlines()), 1)
        self.assertEqual(self.jsonl(output, 'REPO_MANIFEST.jsonl')[0]['path'], path)

    def test_error_gap_preserves_original_metadata_and_missing_hash(self):
        self.capture({'main.txt': b'original'})
        self.mutate('DELETE FROM repo_chunks')
        self.mutate("UPDATE repo_entries SET state='ERROR',reason='BLOB_SIZE_UNAVAILABLE',file_hash=NULL")
        output, _ = self.publish()
        entry = self.jsonl(output, 'REPO_MANIFEST.jsonl')[0]
        self.assertEqual(entry['reason'], 'BLOB_SIZE_UNAVAILABLE')
        self.assertIsNone(entry['file_sha256'])
        self.assertEqual(entry['size'], len(b'original'))
        self.assertFalse(json.loads((output / 'BATCH.json').read_text())['all_tracked_bytes_exportable'])

    def test_byte_budget_continuation_row_envelope_failure_and_large_offset(self):
        self.capture({f'{n:02}.txt': b'hello' for n in range(30)})
        with mock.patch.object(manifest, 'PAGE_FRAME_BYTES', 3600):
            all_rows = self.rows('ENTRIES')
            self.assertEqual(len(all_rows), 30)
        with mock.patch.object(manifest, 'PAGE_FRAME_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'ROW_ENVELOPE_LIMIT'):
                self.page('ENTRIES')
        self.assertEqual(self.page('ENTRIES', offset=1_000_001)['rows'], [])
        self.assertIsNone(self.page('PARTS', offset=1_000_001)['nextOffset'])

    def test_strict_operator_scope_and_real_isolated_native_roundtrip(self):
        self.capture()
        profile_path = self.profile_file()
        base = {'type': 'durable.repo.manifest', 'repository': 'sce', 'snapshotId': self.sid, 'action': 'PARTS'}
        for extra in [{'output': str(self.root)}, {'root': str(self.checkout)}, {'fileOrdinal': True}, {'fileOrdinal': None}, {'limit': True}, {'action': 'EXECUTE'}, {'action': []}, {'repository': 'other'}, {'namespace': 'elsewhere'}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                native_adapter.dispatch({**base, **extra}, profile_path)
        for request in [{**base, 'action': 'INFO', 'offset': 0}, {**base, 'action': 'ENTRIES', 'fileOrdinal': 0}]:
            with self.assertRaisesRegex(ValueError, 'DURABLE_SCHEMA'):
                native_adapter.dispatch(request, profile_path)
        result = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(Path(native_adapter.__file__)), '--profile', str(profile_path)], input=json.dumps(base).encode(), capture_output=True, check=True)
        value = json.loads(result.stdout)
        self.assertTrue(value['ok'], value)
        self.assertEqual(value['result']['manifest']['rows'], self.page('PARTS')['rows'])
        self.assertLessEqual(len(result.stdout), 32768)
        outside = copy.deepcopy(self.profile)
        outside['namespace'] = 'private'
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SCOPE'):
            manifest.page(self.store, 'private', self.sid, 'sce', outside, 'INFO')
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_OPERATOR_SCOPE'):
            manifest.page(self.store, 'code', self.sid, 'else', self.profile, 'INFO')
        outside = copy.deepcopy(self.profile)
        outside['exclusions'] = ['new']
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_OPERATOR_SCOPE'):
            manifest.page(self.store, 'code', self.sid, 'sce', outside, 'INFO')
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SOURCE_AND_STORE'):
            manifest.publish(self.store, 'code', self.sid, 'sce', self.profile, self.checkout / 'bad-output')
        cli = subprocess.run([sys.executable, '-B', str(Path(manifest.__file__)), '--profile', str(profile_path), '--repository', 'sce', '--snapshot', self.sid, '--output', str(self.root / 'cli-output')], capture_output=True, check=True)
        self.assertEqual(json.loads(cli.stdout)['state'], 'PASS')
        scan_cli = subprocess.run([sys.executable, '-B', str(Path(repo.__file__)), '--profile', str(profile_path), '--repository', 'sce', '--snapshot', self.sid], capture_output=True, check=True)
        self.assertEqual(json.loads(scan_cli.stdout)['state'], 'COMPLETE')

    def test_streaming_large_utf8_binary_and_split_secret_marker(self):
        raw = ('Я👋' * 18000 + '\r\nTAIL').encode()
        binary = bytes(range(256)) * 400
        marker = b'-----BEGIN PRIVATE KEY-----'
        secret = b'x' * (64 * 1024 - 10) + marker + b'tail'
        field_secret = b'api_key' + b' ' * 70000 + b'=' + b' ' * 70000 + b'"abcdefghijklmnopq"'
        with mock.patch.object(repo, 'ANALYSIS_BYTES', 1024):
            self.capture({'long.txt': raw, 'binary.bin': binary, 'private.txt': secret, 'field.txt': field_secret})
        self.assertEqual(self.status['counts'], {'INDEXED': 2, 'EXCLUDED': 2})
        output, _ = self.publish()
        entries = self.jsonl(output, 'REPO_MANIFEST.jsonl')
        self.assertEqual(next(e for e in entries if e['path'] == 'long.txt')['parser'], 'UTF8_STREAM_NO_AST')
        db = repo.db_for(self.store)
        try:
            for path, original in [('long.txt', raw), ('binary.bin', binary)]:
                chunks = list(db.execute('SELECT * FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (self.sid, path)))
                self.assertEqual(b''.join(c['raw'] for c in chunks), original)
                self.assertTrue(all(len(c['raw']) <= repo.CHUNK_BYTES for c in chunks))
            self.assertFalse(db.execute("SELECT 1 FROM repo_chunks WHERE path='private.txt'").fetchone())
        finally:
            db.close()

    def test_tree_records_stream_past_former_32mib_limit(self):
        # Exercise the real streaming reader with >32 MiB of NUL records,
        # without building hundreds of thousands of physical files.
        class Source:
            def __init__(self):
                self.remaining = 33 * 1024 * 1024 // 512
            def read(self, _size):
                if not self.remaining:
                    return b''
                count = min(self.remaining, 128)
                self.remaining -= count
                return (b'x' * 511 + b'\0') * count
        from contextlib import contextmanager
        @contextmanager
        def source(*_args):
            yield Source()
        with mock.patch.object(repo, 'git_stream', source):
            total = sum(len(r) + 1 for r in repo.git_records(self.checkout, 'ls-tree'))
        self.assertEqual(total, 33 * 1024 * 1024)

    def test_old_file_size_error_is_retried_by_existing_scan_owner(self):
        self.capture({'main.txt': b'formerly rejected'})
        self.mutate('DELETE FROM repo_chunks')
        self.mutate("UPDATE repo_entries SET state='ERROR',reason='FILE_TOO_LARGE',file_hash=NULL")
        self.assertEqual(repo.start_scan(self.store, 'sce', self.profile), self.sid)
        pending = repo.get_snapshot(self.store, 'code', self.sid)
        self.assertEqual(pending['state'], 'PENDING')
        self.assertEqual(pending['cursor'], 0)
        self.assertEqual(repo.scan_page(self.store, 'code', self.sid)['counts'], {'INDEXED': 1})
        self.publish()
