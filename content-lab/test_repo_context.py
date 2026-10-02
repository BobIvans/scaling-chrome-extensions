import copy
import http.server
import itertools
import json
import re
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest import TestCase, mock

import automation_core as core
import context_review as review
import native_adapter
import repo_context as repo


class RepoContextTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkout = self.root / 'repo'
        self.checkout.mkdir()
        self.store = self.root / 'store'
        self.profile = {'root': str(self.checkout), 'namespace': 'code',
                        'source_roots': ['.', 'content-lab', 'agent-bridge'], 'exclusions': []}
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'core.autocrlf', 'false')

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.checkout), *args], capture_output=True, check=True)
        return result.stdout

    def put(self, path, raw):
        target = self.checkout / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-qm', 'fixture snapshot')

    def scan(self, limit=100):
        snapshot_id = repo.start_scan(self.store, 'sce', self.profile)
        while True:
            status = repo.scan_page(self.store, 'code', snapshot_id, limit=limit)
            if status['state'] == 'COMPLETE':
                return status

    def export(self, status, paths=None):
        return repo.export_request(self.store, 'code', status['snapshot_id'], paths or ['content-lab/main.py'],
                                   'Review current source', 'Selected static context', ['Prove the reported criterion'])

    def test_git_bytes_partition_including_bom_crlf_empty_binary_long_lines(self):
        sources = {'empty.txt': b'', 'utf8.py': b'\xef\xbb\xbf# comment\r\ndef f():\r\n    return 1\r\n',
                   'binary.bin': bytes(range(256)) * 32,
                   'huge.txt': ('Я👋' * 3000 + '\r\nTAIL').encode()}
        for path, raw in sources.items():
            self.put(path, raw)
        self.commit()
        status = self.scan()
        self.assertEqual(status['total'], len(sources))
        db = repo.db_for(self.store)
        try:
            for path, raw in sources.items():
                chunks = db.execute('SELECT * FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (status['snapshot_id'], path)).fetchall()
                self.assertEqual(b''.join(c['raw'] for c in chunks), raw)
                self.assertTrue(all(len(c['raw']) <= repo.CHUNK_BYTES for c in chunks))
                self.assertEqual(chunks[0]['byte_start'], 0)
                self.assertEqual(chunks[-1]['byte_end'], len(raw))
                self.assertEqual(db.execute('SELECT file_hash FROM repo_entries WHERE snapshot_id=? AND path=?', (status['snapshot_id'], path)).fetchone()[0], repo.sha(raw))
        finally:
            db.close()

    def test_2005_files_persisted_before_scan_and_restart_reaches_tail(self):
        for n in range(2005):
            self.put(f'{n:04}.py', b'x = 1\n')
        self.commit()
        snapshot_id = repo.start_scan(self.store, 'sce', self.profile)
        initial = repo.get_snapshot(self.store, 'code', snapshot_id)
        self.assertEqual(initial['accounted'], 2005)
        self.assertEqual(initial['counts'], {'PENDING': 2005})
        first = repo.scan_page(self.store, 'code', snapshot_id, limit=100)
        script = 'import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import repo_context as r;r.scan_page(Path(sys.argv[2]),"code",sys.argv[3],limit=100)'
        subprocess.run([sys.executable, '-I', '-c', script, str(Path(repo.__file__).parent), str(self.store), snapshot_id], check=True)
        self.assertEqual(repo.get_snapshot(self.store, 'code', snapshot_id)['cursor'], 200)
        final = self.scan()
        self.assertEqual(final['counts'], {'INDEXED': 2005})
        db = repo.db_for(self.store)
        self.assertIsNotNone(db.execute('SELECT item_id FROM repo_chunks WHERE snapshot_id=? AND path=?', (snapshot_id, '2004.py')).fetchone())
        db.close()
        self.assertEqual(first['cursor'], 100)

    def test_filename_policy_accounts_exclusions_without_wallet_false_positive(self):
        for path in ['wallet_logic.py', 'session_model.py', '.env', 'credentials.json', 'operator/private.md']:
            self.put(path, b'x = 1\n')
        self.profile['exclusions'] = ['operator']
        self.commit()
        status = self.scan()
        files = {f['path']: f for f in status['files']}
        self.assertEqual(status['accounted'], 5)
        self.assertEqual(files['wallet_logic.py']['state'], 'INDEXED')
        self.assertEqual(files['session_model.py']['state'], 'INDEXED')
        self.assertEqual(files['.env']['state'], 'EXCLUDED')
        db = repo.db_for(self.store)
        self.assertEqual(db.execute('SELECT count(*) FROM repo_chunks WHERE path=?', ('.env',)).fetchone()[0], 0)
        db.close()

    def test_scanner_never_imports_source_and_handles_errors_explicitly(self):
        sentinel = self.root / 'executed'
        self.put('evil.py', f'from pathlib import Path\nPath({str(sentinel)!r}).touch()\n'.encode())
        self.put('broken.py', b'def missing(\n')
        self.put('large.bin', b'x' * (repo.MAX_FILE + 1))
        self.commit()
        status = self.scan()
        self.assertFalse(sentinel.exists())
        self.assertEqual(status['counts'], {'ERROR': 1, 'INDEXED': 2})
        self.assertEqual(next(f for f in status['files'] if f['path'] == 'large.bin')['reason'], 'FILE_TOO_LARGE')

    def test_root_aware_dependencies_unresolved_and_scc_oracle(self):
        self.put('content-lab/main.py', b'import helper\nimport absent\n__import__("maybe")\n')
        self.put('content-lab/helper.py', b'x = 1\n')
        self.put('content-lab/test_main.py', b'pass\n')
        self.commit()
        status = self.scan()
        chosen = repo.selection(self.store, 'code', status['snapshot_id'], ['content-lab/main.py'])
        self.assertEqual(chosen['dependencies'], ['content-lab/helper.py'])
        self.assertIn('content-lab/test_main.py', chosen['relevant_tests'])
        self.assertEqual({x['status'] for x in chosen['missing_dependencies']}, {'EXTERNAL_OR_UNRESOLVED', 'DYNAMIC_UNRESOLVED'})
        self.put('agent-bridge/helper.py', b'x = 2\n')
        self.commit()
        chosen = repo.selection(self.store, 'code', self.scan()['snapshot_id'], ['content-lab/main.py'])
        self.assertEqual(chosen['dependencies'], [])
        self.assertIn('AMBIGUOUS', {x['status'] for x in chosen['missing_dependencies']})
        nodes = list('abcd')
        possible = [(a, b) for a in nodes for b in nodes if a != b]
        for mask in range(1 << len(possible)):
            edges = [{'from': a, 'to': b} for i, (a, b) in enumerate(possible) if mask & (1 << i)]
            reach = {(x, x) for x in nodes} | {(x['from'], x['to']) for x in edges}
            for k, a, b in itertools.product(nodes, repeat=3):
                if (a, k) in reach and (k, b) in reach:
                    reach.add((a, b))
            expected = {frozenset(b for b in nodes if (a, b) in reach and (b, a) in reach) for a in nodes}
            self.assertEqual({frozenset(g) for g in repo.components(nodes, edges)}, expected)

    def test_add_edit_delete_rename_invalidate_review_and_preserve_logical_ids(self):
        self.put('content-lab/main.py', b'import helper\ndef f():\n    return 1\n')
        self.put('content-lab/helper.py', b'value = 1\n')
        self.commit()
        first = self.scan()
        exported = self.export(first)
        session = exported['review']
        self.assertEqual(exported['document']['context']['sha256'], session['export_sha256'])
        self.assertEqual(session['repo_binding']['state'], 'VERIFIED')
        db = repo.db_for(self.store)
        old_ids = [r[0] for r in db.execute('SELECT logical_id FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (first['snapshot_id'], 'content-lab/main.py'))]
        db.close()
        # Dependency edits are stale even before Git commit or another scan.
        self.put('content-lab/helper.py', b'value = 2\n')
        status = review.get_session(self.store, 'code', session['session_id'])
        self.assertEqual(status['state'], 'STALE')
        self.assertIn('content-lab/helper.py', status['changed_dependencies'])
        (self.checkout / 'content-lab/helper.py').unlink()
        self.assertEqual(review.get_session(self.store, 'code', session['session_id'])['state'], 'NEEDS_CONTEXT')
        self.put('a_new.py', b'pass\n')
        self.git('mv', 'content-lab/main.py', 'content-lab/renamed.py')
        self.commit()
        second = self.scan()
        self.assertNotEqual(first['snapshot_id'], second['snapshot_id'])
        self.assertNotIn('content-lab/main.py', {f['path'] for f in second['files']})
        for item in exported['document']['context']['items']:
            with self.assertRaisesRegex(ValueError, 'STALE'):
                core.context_pack(self.store, 'code', [item['id']])
        # Lexically earlier additions never renumber existing logical fragments.
        self.put('content-lab/main.py', b'import helper\ndef f():\n    return 1\n')
        self.put('content-lab/helper.py', b'value = 1\n')
        self.commit()
        third = self.scan()
        db = repo.db_for(self.store)
        new_ids = [r[0] for r in db.execute('SELECT logical_id FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (third['snapshot_id'], 'content-lab/main.py'))]
        db.close()
        self.assertEqual(old_ids, new_ids)

    def test_client_sha_does_not_prove_git_binding_and_done_stays_open(self):
        self.put('content-lab/main.py', b'value = 1\n')
        self.commit()
        first = self.scan()
        exported = self.export(first)
        session = exported['review']
        ids = [s['item_id'] for s in session['sources']]
        with self.assertRaisesRegex(ValueError, 'SHA_MISMATCH'):
            review.create_session(self.store, 'code', ids, 'goal', 'a' * 40, repo_snapshot_id=first['snapshot_id'])
        unbound = review.create_session(self.store, 'code', ids, 'goal', first['repo_sha'])
        self.assertEqual(unbound['repo_binding']['state'], 'UNBOUND')
        result = copy.deepcopy(exported['document']['review_result_template'])
        result['coverage']['reviewed'] = [s['source_key'] for s in session['sources']]
        result['coverage']['not_reviewed'] = []
        result['findings'] = [{'finding_id': 'F001', 'classification': 'CODE_DEFECT', 'disposition': 'DONE',
                              'source_key': session['sources'][0]['source_key'], 'source_sha256': session['sources'][0]['sha256'],
                              'criterion': 'independent test evidence required', 'evidence_refs': [], 'duplicate_of': None, 'supersedes': None}]
        imported = review.import_review(self.store, 'code', result)
        self.assertFalse(imported['findings'][0]['closed'])
        self.assertEqual(review.import_review(self.store, 'code', result)['import_state'], 'UNCHANGED')
        detailed = review.get_session(self.store, 'code', session['session_id'], details=True)
        self.assertIn('criterion', detailed['finding_details'][0])
        self.put('another.py', b'pass\n')
        self.commit()
        self.assertIn('GIT_HEAD', review.get_session(self.store, 'code', session['session_id'])['changed_dependencies'])

    def test_drift_pending_rollback_and_budget_omissions_are_explicit(self):
        self.put('content-lab/main.py', b'x = 1\n' + b'# padding\n' * 9000)
        self.commit()
        snapshot_id = repo.start_scan(self.store, 'sce', self.profile)
        with self.assertRaisesRegex(ValueError, 'INCOMPLETE'):
            repo.selection(self.store, 'code', snapshot_id, ['content-lab/main.py'])
        original = repo.partition
        with mock.patch.object(repo, 'partition', side_effect=RuntimeError('interrupt')):
            with self.assertRaises(RuntimeError):
                repo.scan_page(self.store, 'code', snapshot_id)
        self.assertEqual(repo.get_snapshot(self.store, 'code', snapshot_id)['cursor'], 0)
        self.assertIsNotNone(original)
        status = self.scan()
        exported = self.export(status)
        self.assertTrue(exported['document']['selection']['omitted_sources'])
        self.assertEqual(exported['review']['state'], 'NEEDS_CONTEXT')
        self.assertLess(exported['token_upper_bound'], 300_000)
        self.put('new.py', b'pass\n')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'SOURCE_DRIFT'):
            repo.scan_page(self.store, 'code', snapshot_id)

    def test_native_profile_chooses_repo_paths_and_source_scope(self):
        self.put('content-lab/main.py', b'value = 1\n')
        self.commit()
        policy_path = self.root / 'policy.json'
        policy_path.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'money_budget': 0, 'max_parallel': 1}))
        profile_path = self.root / 'profile.json'
        profile_path.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy_path), 'namespaces': ['code'], 'templates': {}, 'repositories': {'sce': self.profile}}))
        dispatch = lambda request: native_adapter.dispatch(request, profile_path)
        self.assertEqual(dispatch({'type': 'durable.repo.list'})['repositories'], [{'repository': 'sce', 'namespace': 'code'}])
        with self.assertRaisesRegex(ValueError, 'SCHEMA'):
            dispatch({'type': 'durable.repo.scan', 'repository': 'sce', 'root': '/other'})
        with self.assertRaisesRegex(ValueError, 'OUTSIDE'):
            dispatch({'type': 'durable.repo.scan', 'repository': 'other'})
        status = dispatch({'type': 'durable.repo.scan', 'repository': 'sce'})['snapshot']
        exported = dispatch({'type': 'durable.repo.export', 'repository': 'sce', 'snapshotId': status['snapshot_id'],
                             'paths': ['content-lab/main.py'], 'goal': 'review', 'scope': 'source', 'acceptance': ['test criterion']})['export']
        self.assertEqual(exported['review']['repo_binding']['state'], 'VERIFIED')
        self.assertEqual(dispatch({'type': 'durable.review.get', 'namespace': 'code', 'sessionId': exported['review']['session_id'], 'includeContent': True})['review']['request_meta']['goal'], 'review')

    def test_namespace_and_path_boundaries(self):
        self.put('content-lab/main.py', b'pass\n')
        self.commit()
        status = self.scan()
        with self.assertRaisesRegex(ValueError, 'OUTSIDE'):
            repo.get_snapshot(self.store, 'private', status['snapshot_id'])
        for path in ['../outside', '/outside', 'a/../b', 'C:/outside', 'a\\b']:
            with self.assertRaises(ValueError):
                repo.selection(self.store, 'code', status['snapshot_id'], [path])

    def test_missing_inventory_and_corrupt_fragment_fail_completeness(self):
        self.put('content-lab/main.py', b'pass\n')
        self.put('other.py', b'pass\n')
        self.commit()
        status = self.scan()
        self.assertTrue(status['roundtrip']['all_tracked_bytes_exportable'])
        db = repo.db_for(self.store)
        with db:
            db.execute('UPDATE repo_chunks SET raw=? WHERE path=?', (b'wrong', 'other.py'))
        db.close()
        self.assertFalse(repo.get_snapshot(self.store, 'code', status['snapshot_id'])['roundtrip']['exact_for_indexed'])
        with self.assertRaisesRegex(ValueError, 'INCOMPLETE'):
            self.export(status)
        db = repo.db_for(self.store)
        with db:
            db.execute('DELETE FROM repo_entries WHERE path=?', ('other.py',))
        db.close()
        self.assertFalse(repo.get_snapshot(self.store, 'code', status['snapshot_id'])['inventory_complete'])

    def test_changed_text_and_revoked_repo_profile_do_not_verify(self):
        self.put('content-lab/main.py', b'pass\n')
        self.commit()
        exported = self.export(self.scan())
        session = exported['review']
        with mock.patch.object(repo, 'verify_binding') as verify:
            status = review.get_session(self.store, 'code', session['session_id'], repo_profiles={})
        verify.assert_not_called()
        self.assertIn('REPO_PROFILE_REVOKED', status['missing_dependencies'])
        db = core.connection(self.store)
        with db:
            item_id = session['sources'][0]['item_id']
            payload = json.loads(db.execute('SELECT payload FROM items WHERE id=?', (item_id,)).fetchone()[0])
            payload['text'] = 'tampered bytes'
            db.execute('UPDATE items SET payload=? WHERE id=?', (json.dumps(payload), item_id))
        db.close()
        self.assertEqual(review.get_session(self.store, 'code', session['session_id'])['state'], 'STALE')
        with self.assertRaisesRegex(ValueError, 'CONTEXT_CORRUPT'):
            self.export({'snapshot_id': exported['document']['selection']['binding']['snapshot_id']})

    def test_delta_reports_renames_deletions_and_affected_dependents(self):
        self.put('main.py', b'import helper\n')
        self.put('helper.py', b'value = 1\n')
        self.put('remove.py', b'pass\n')
        self.commit()
        before = self.scan()
        self.git('mv', 'helper.py', 'new.py')
        (self.checkout / 'remove.py').unlink()
        self.put('added.py', b'new_value = 999\n')
        self.commit()
        status = self.scan()
        self.assertEqual(status['changes']['base_repo_sha'], before['repo_sha'])
        self.assertEqual(status['changes']['paths']['renamed'], [{'from': 'helper.py', 'to': 'new.py'}])
        self.assertIn('remove.py', status['changes']['paths']['deleted'])
        self.assertIn('main.py', status['changes']['paths']['affected_dependents'])

    def test_staged_addition_changes_binding_without_changing_head(self):
        self.put('content-lab/main.py', b'pass\n')
        self.commit()
        exported = self.export(self.scan())
        self.put('new_module.py', b'pass\n')
        self.git('add', 'new_module.py')
        status = review.get_session(self.store, 'code', exported['review']['session_id'])
        self.assertEqual(status['state'], 'STALE')
        self.assertIn('GIT_INDEX', status['changed_dependencies'])
        self.assertEqual(status['repo_binding']['expected_repo_sha'], status['repo_binding']['observed_repo_sha'])

    def test_installer_file_set_runs_real_isolated_repo_adapter(self):
        self.put('main.py', b'pass\n')
        self.commit()
        lab = Path(repo.__file__).parent
        installer = (lab.parent / 'agent-bridge/Install.ps1').read_text()
        file_set = re.search(r'foreach\(\$occFile in @\((.*?)\)\)', installer).group(1)
        installed = self.root / 'installed/content-lab'
        installed.mkdir(parents=True)
        for name in re.findall(r"'([^']+)'", file_set):
            shutil.copyfile(lab / name, installed / name)
        policy_path = self.root / 'policy.json'
        policy_path.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'money_budget': 0, 'max_parallel': 1}))
        profile_path = self.root / 'profile.json'
        profile_path.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy_path), 'namespaces': ['code'], 'templates': {}, 'repositories': {'sce': self.profile}}))
        result = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(installed / 'native_adapter.py'),
                                 '--profile', str(profile_path)], input=b'{"type":"durable.repo.scan","repository":"sce"}', capture_output=True, check=True)
        output = json.loads(result.stdout)
        self.assertTrue(output['ok'], output)
        self.assertEqual(output['result']['snapshot']['state'], 'COMPLETE')
        self.assertTrue(output['result']['snapshot']['roundtrip']['exact_for_indexed'])

    def test_missing_promisor_blob_is_an_error_without_lazy_network_fetch(self):
        self.put('main.py', b'pass\n')
        self.commit()
        oid = self.git('rev-parse', 'HEAD:main.py').decode().strip()
        (self.checkout / '.git/objects' / oid[:2] / oid[2:]).unlink()
        requests = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_error(404)
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def close():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(close)
        self.git('config', 'remote.origin.url', f'http://127.0.0.1:{server.server_port}/fixture')
        self.git('config', 'remote.origin.promisor', 'true')
        self.git('config', 'remote.origin.partialclonefilter', 'blob:none')
        status = self.scan()
        self.assertEqual(status['counts'], {'ERROR': 1})
        self.assertFalse(status['roundtrip']['all_tracked_bytes_exportable'])
        self.assertEqual(requests, [])
