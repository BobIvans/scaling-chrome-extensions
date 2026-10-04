import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'content-lab'))
from desktop.client import (Connection, DesktopClient, DesktopError, environment,
                            PROTOCOL, sha_file, strict_json, validate_context, validate_reply)
from desktop.draft import save_draft, save_manifest
from desktop.package import FILES, make_manifest, stage_shell, uninstall, verify
from desktop.preflight import check
from desktop.state import Fence
import automation_core as core
import native_adapter as native
import repo_context as repo
import content_lab

FIXTURES = Path(__file__).parent / 'fixtures'
FAKE = Path(__file__).parent / 'fake_adapter.py'


class WireTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='desktop-wire-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / 'profile.json'
        self.scenario('hello')
        self.connection = Connection.from_dict({'schema': 'occ.desktop-connection.v1',
            'protocol': PROTOCOL, 'python_path': sys.executable, 'adapter_path': str(FAKE),
            'profile_path': str(self.profile), 'expected_adapter_sha256': sha_file(FAKE),
            'preferred_namespace': 'code'})
        self.client = DesktopClient(self.connection)
        self.addCleanup(self.client.close)
        self.client.handshake()

    def scenario(self, value):
        self.profile.write_text(json.dumps({'scenario': value}), encoding='utf-8')

    def test_segmented_utf8_reply_and_exact_owner_context_digest(self):
        self.scenario('search')
        items = self.client.request({'type': 'durable.search', 'namespace': 'code', 'query': 'контекст'})['result']['items']
        self.scenario('context')
        result = self.client.request({'type': 'durable.context', 'namespace': 'code', 'ids': [i['id'] for i in items]})
        context = result['result']['context']
        fixture = json.loads((FIXTURES / 'selected_context.json').read_bytes())
        self.assertEqual(context, fixture['result']['context'])
        self.assertTrue(context['items'][0]['text'].endswith('\r\n'))
        self.assertTrue(context['items'][1]['text'].startswith('\ufeff'))
        self.assertTrue(self.client.last_stats['child_reaped'])
        self.assertTrue(self.client.last_stats['pipes_closed'])
        self.assertTrue(self.client.last_stats['io_threads_stopped'])

    def test_json_encoding_and_framing_faults_are_typed(self):
        cases = {'invalid_utf8': 'DESKTOP_UTF8', 'duplicate_keys': 'DESKTOP_DUPLICATE_KEY',
                 'nonfinite': 'DESKTOP_NONFINITE', 'trailing_json': 'DESKTOP_JSON',
                 'unknown_field': 'DESKTOP_SCHEMA', 'protocol_mismatch': 'DESKTOP_PROTOCOL_UNAVAILABLE',
                 'operation_mismatch': 'DESKTOP_OPERATION_MISMATCH',
                 'setup_required': 'DESKTOP_SETUP_REQUIRED', 'nonzero': 'DESKTOP_PROTOCOL_UNAVAILABLE'}
        for scenario, code in cases.items():
            with self.subTest(scenario=scenario):
                self.scenario(scenario)
                with self.assertRaisesRegex(DesktopError, '^' + code + '$'):
                    self.client.request({'type': 'durable.info'})
                self.assertTrue(self.client.last_stats['child_reaped'])
        for raw in (b'{"x":1e999}', b'{"x":Infinity}'):
            with self.assertRaisesRegex(DesktopError, 'DESKTOP_NONFINITE'):
                strict_json(raw)

    def test_profile_and_context_tampering_are_rejected(self):
        fixture = json.loads((FIXTURES / 'selected_context.json').read_bytes())
        request = {'type': 'durable.context', 'namespace': 'code',
                   'ids': [i['id'] for i in fixture['result']['context']['items']]}
        self.scenario('profile_changed')
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_PROFILE_CHANGED'):
            self.client.request(request)
        self.assertIsNone(self.client.identity)
        self.scenario('hello')
        self.client.handshake()
        self.scenario('tampered_context')
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_CONTEXT_DIGEST'):
            self.client.request(request)

    def test_combined_budget_drains_both_pipes_and_never_logs_raw_stderr(self):
        for scenario in ('stdout_flood', 'stderr_flood', 'combined_flood'):
            with self.subTest(scenario=scenario):
                self.scenario(scenario)
                with self.assertRaisesRegex(DesktopError, 'DESKTOP_OUTPUT_LIMIT'):
                    self.client.request({'type': 'durable.info'})
                self.assertTrue(self.client.last_stats['io_threads_stopped'])
                self.assertLessEqual(self.client.last_stats['stderr_retained_bytes'], 4096)
        self.scenario('stderr_small')
        self.client.request({'type': 'durable.info'})
        self.assertNotIn('PRIVATE_FIXTURE', json.dumps(self.client.last_stats))

    def test_timeout_cancel_and_one_inflight_read_are_reaped(self):
        self.scenario('timeout')
        self.client.info['native_timeout_ms'] = 80
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_TIMEOUT'):
            self.client.request({'type': 'durable.search', 'namespace': 'code', 'query': 'read'})
        self.assertTrue(self.client.last_stats['child_reaped'])
        self.client.info['native_timeout_ms'] = 1000
        errors = []
        def read():
            try:
                self.client.request({'type': 'durable.search', 'namespace': 'code', 'query': 'read'})
            except DesktopError as exc:
                errors.append(exc.code)
        worker = threading.Thread(target=read)
        worker.start()
        deadline = time.monotonic() + 2
        while not self.client.busy and time.monotonic() < deadline:
            time.sleep(0.005)
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_BUSY'):
            self.client.request({'type': 'durable.info'})
        self.client.close()
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, ['DESKTOP_CANCELLED'])
        self.assertTrue(self.client.last_stats['pipes_closed'])
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_CLOSED'):
            self.client.request({'type': 'durable.info'})

    def test_reject_mutations_and_untrusted_argv_before_spawn(self):
        for request in ({'type': 'durable.enqueue', 'template': 'x', 'taskKey': 'x'},
                        {'type': 'durable.search', 'namespace': 'code', 'query': 'x', 'argv': ['evil']},
                        {'type': 'durable.context', 'namespace': 'code', 'ids': ['a' * 64], 'maxBytes': True},
                        {'type': 'durable.info', 'sql': 'select 1'}, {'type': []}):
            with mock.patch('desktop.client.subprocess.Popen') as spawn, self.assertRaises(DesktopError):
                self.client.request(request)
            spawn.assert_not_called()
        value = self.connection.as_dict()
        for patch in ({'python_path': 'python'}, {'adapter_path': str(FAKE) + '\0'}, {'extra': 1}):
            with self.assertRaises(DesktopError):
                Connection.from_dict({**value, **patch})
        with mock.patch.dict(os.environ, {'SECRET_PROVIDER_TOKEN': 'not inherited'}):
            self.assertNotIn('SECRET_PROVIDER_TOKEN', environment())
        self.assertEqual(self.connection.argv()[-3:], ['--profile', str(self.profile), '--desktop-stdio'])

    def test_generation_fences_all_lifecycle_changes(self):
        fence = Fence()
        fence.invalidate(namespace='code', identity=self.client.identity)
        ticket = fence.begin('durable.search')
        self.assertTrue(fence.accepts(ticket))
        for event in ('edit', 'namespace', 'reconnect', 'close'):
            with self.subTest(event=event):
                ticket = fence.begin('durable.search')
                if event == 'close':
                    fence.close()
                else:
                    fence.invalidate(namespace='other' if event == 'namespace' else None,
                                     reconnect=event == 'reconnect')
                self.assertFalse(fence.accepts(ticket))


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='desktop-owner-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'Данные with spaces'
        self.root.mkdir()
        self.store = self.root / 'existing corpus'
        self.source = self.root / 'источники source'
        self.source.mkdir()
        (self.source / 'note.txt').write_bytes('needle Привет\r\nExact source'.encode('utf-8'))
        core.sync(self.store, 'code', self.source)
        self.policy = self.root / 'policy.json'
        self.policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'max_parallel': 1,
                                          'money_budget': 0}), encoding='utf-8')
        self.profile = self.root / 'native-profile.json'
        self.profile.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1',
            'store': str(self.store), 'policy_file': str(self.policy), 'namespaces': ['code'],
            'templates': {}}), encoding='utf-8')
        self.adapter = ROOT / 'content-lab' / 'native_adapter.py'
        self.connection = Connection.from_dict({'schema': 'occ.desktop-connection.v1', 'protocol': PROTOCOL,
            'python_path': sys.executable, 'adapter_path': str(self.adapter), 'profile_path': str(self.profile),
            'expected_adapter_sha256': sha_file(self.adapter), 'preferred_namespace': 'code'})
        self.client = DesktopClient(self.connection)
        self.addCleanup(self.client.close)
        self.client.handshake()

    def selected(self):
        items = self.client.request({'type': 'durable.search', 'namespace': 'code', 'query': 'needle'})['result']['items']
        request = {'type': 'durable.context', 'namespace': 'code', 'ids': [i['id'] for i in items]}
        return request, self.client.request(request)['result']['context']

    def test_browser_and_desktop_share_dtos_without_corpus_or_schema_mutation(self):
        request, context = self.selected()
        before = sha_file(self.store / 'content.sqlite3')
        db = core.read_connection(self.store)
        schema = db.execute('SELECT sql FROM sqlite_master ORDER BY name').fetchall()
        db.close()
        for request in ({'type': 'durable.info'}, {'type': 'durable.repo.list'},
                        {'type': 'durable.search', 'namespace': 'code', 'query': 'needle'}, request):
            desktop = self.client.request(request)['result']
            browser = native.dispatch(request, self.profile)
            self.assertEqual(desktop, browser)
        self.assertEqual(before, sha_file(self.store / 'content.sqlite3'))
        db = core.read_connection(self.store)
        self.assertEqual(schema, db.execute('SELECT sql FROM sqlite_master ORDER BY name').fetchall())
        with self.assertRaises(sqlite3.OperationalError):
            db.execute('DELETE FROM items')
        db.close()
        self.assertEqual(context['items'][0]['text'], 'needle Привет\r\nExact source')

    def test_missing_and_unready_store_never_creates_or_migrates(self):
        profile = json.loads(self.profile.read_bytes())
        missing = self.root / 'missing store'
        profile['store'] = str(missing)
        self.profile.write_text(json.dumps(profile), encoding='utf-8')
        value = native.dispatch_desktop({'type': 'durable.info'}, self.profile)
        self.assertFalse(value['result']['info']['store_ready'])
        self.assertFalse(missing.exists())
        failure = native.dispatch_desktop({'type': 'durable.search', 'namespace': 'code', 'query': 'needle'}, self.profile)
        self.assertEqual(failure['error'], 'DESKTOP_SETUP_REQUIRED')
        self.assertFalse(missing.exists())
        missing.mkdir()
        db = sqlite3.connect(missing / 'content.sqlite3')
        db.execute('CREATE TABLE sentinel(value)')
        db.close()
        before = sha_file(missing / 'content.sqlite3')
        self.assertFalse(native.dispatch_desktop({'type': 'durable.repo.list'}, self.profile)['ok'])
        self.assertEqual(before, sha_file(missing / 'content.sqlite3'))

    def test_profile_is_loaded_once_and_actual_binding_invalidates_old_handshake(self):
        request = {'type': 'durable.search', 'namespace': 'code', 'query': 'needle'}
        original = native.operator_profile
        with mock.patch.object(native, 'operator_profile', wraps=original) as load:
            reply = native.dispatch_desktop(request, self.profile)
            load.assert_called_once_with(self.profile)
        self.assertEqual(reply['adapter_context'], self.client.identity)
        profile = json.loads(self.profile.read_bytes())
        profile['namespaces'].append('other')
        self.profile.write_text(json.dumps(profile), encoding='utf-8')
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_PROFILE_CHANGED'):
            self.client.request(request)
        self.assertIsNone(self.client.identity)
        self.client.handshake()
        self.assertIn('other', self.client.info['namespaces'])
        with mock.patch.object(native, 'operator_profile') as load:
            reply = native.dispatch_desktop({'type': 'durable.enqueue', 'template': 'x', 'taskKey': 'x'}, self.profile)
            self.assertEqual(reply['error'], 'DESKTOP_READ_ONLY')
            load.assert_not_called()

    def test_stale_item_stays_rejected_by_actual_owner(self):
        request, _context = self.selected()
        (self.source / 'note.txt').write_text('needle changed', encoding='utf-8')
        core.sync(self.store, 'code', self.source)
        with self.assertRaisesRegex(DesktopError, 'ITEM_OUTSIDE_SCOPE_OR_STALE'):
            self.client.request(request)

    def test_current_main_chatgpt_original_fidelity_projects_through_same_read_owner(self):
        source = ROOT / 'content-lab/fixtures/import_fidelity_golden/raw/F01.json'
        receipt = content_lab.import_chatgpt_export(self.store, source, 'code', source_key='desktop-fixture')
        self.assertTrue(receipt['original_retained'])
        profile = json.loads(self.profile.read_bytes())
        profile['namespaces'].append('chatgpt:code')
        self.profile.write_text(json.dumps(profile), encoding='utf-8')
        self.client.handshake()
        parsed = content_lab.parse_chatgpt_export(source, 'code')
        ids = [item['id'] for item in parsed['items']][:10]
        before = sha_file(self.store / 'content.sqlite3')
        request = {'type': 'durable.context', 'namespace': 'chatgpt:code', 'ids': ids}
        value = self.client.request(request)['result']['context']
        self.assertEqual(value, core.context_pack(self.store, 'chatgpt:code', ids, read_only=True))
        self.assertEqual(before, sha_file(self.store / 'content.sqlite3'))
        self.assertTrue(all(item['extractor'] == 'chatgpt-export.v1' for item in value['items']))

    def test_preflight_repeated_launch_same_store_and_isolated_cli(self):
        report = check(self.connection)
        self.assertTrue(report['info']['store_ready'])
        self.assertEqual(report['adapter_context'], self.client.identity)
        self.assertTrue(report['transport']['child_reaped'])
        self.assertEqual(report['windows_installed'], 'NOT_RUN')
        config = self.root / 'connection.json'
        config.write_text(json.dumps(self.connection.as_dict()), encoding='utf-8')
        result = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(ROOT / 'desktop' / 'preflight.py'),
            '--config', str(config)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout)['result']['adapter_context'], report['adapter_context'])

    def test_atomic_draft_preserves_exact_items_and_separate_hashes(self):
        _request, context = self.selected()
        output = self.root / 'document draft'
        result = save_draft(output, context, self.client.identity, 'Goal', 'Scope', 'Prove bytes')
        metadata = json.loads((output / 'DRAFT_METADATA.json').read_bytes())
        self.assertEqual(metadata, result)
        self.assertEqual(metadata['scope'], 'SELECTED_ITEMS')
        self.assertIsNone(metadata['canonical_task_id'])
        self.assertEqual(metadata['context'], context)
        self.assertEqual(metadata['draft_file_sha256'], sha_file(output / 'TASK_DRAFT.txt'))
        self.assertNotEqual(metadata['draft_file_sha256'], metadata['owner_context_sha256'])
        self.assertIn(context['items'][0]['text'].encode('utf-8'), (output / 'TASK_DRAFT.txt').read_bytes())
        before = (output / 'TASK_DRAFT.txt').read_bytes()
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_OUTPUT_CONFLICT'):
            save_draft(output, context, self.client.identity, 'New', 'Scope', 'Criteria')
        self.assertEqual((output / 'TASK_DRAFT.txt').read_bytes(), before)

    def test_disk_full_no_false_publication_or_corpus_change(self):
        _request, context = self.selected()
        before = sha_file(self.store / 'content.sqlite3')
        output = self.root / 'failed-draft'
        with mock.patch('desktop.draft.write_verified', side_effect=OSError(errno.ENOSPC, 'disk full')):
            with self.assertRaisesRegex(DesktopError, 'DESKTOP_OUTPUT_FAILED'):
                save_draft(output, context, self.client.identity, 'Goal', 'Scope', 'Criteria')
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob('.failed-draft.*')))
        self.assertEqual(before, sha_file(self.store / 'content.sqlite3'))

    def test_verified_uninstall_preserves_corpus_backend_profile_and_browser_read(self):
        shell = self.root / 'Desktop v1 shell'
        shell.mkdir()
        for name in FILES:
            shutil.copyfile(ROOT / 'desktop' / name, shell / name)
        (shell / 'OWNED_FILES.json').write_text(json.dumps(make_manifest(shell, '9fbadef' + '0' * 33)), encoding='utf-8')
        config = shell / 'connection.json'
        config.write_text(json.dumps(self.connection.as_dict()), encoding='utf-8')
        sentinel = self.store / 'corpus-sentinel.txt'
        sentinel.write_text('retain', encoding='utf-8')
        output = self.root / 'operator output'
        output.mkdir()
        (output / 'TASK_DRAFT.txt').write_text('earlier', encoding='utf-8')
        result = uninstall(shell)
        self.assertTrue(result['external_roots_retained'])
        self.assertTrue(self.adapter.exists())
        self.assertTrue(self.profile.exists())
        self.assertEqual(sentinel.read_text(), 'retain')
        self.assertEqual((output / 'TASK_DRAFT.txt').read_text(), 'earlier')
        self.assertTrue(native.dispatch({'type': 'durable.search', 'namespace': 'code', 'query': 'needle'}, self.profile)['items'])
        self.assertEqual(list(shell.iterdir()), [])

    def test_package_prevalidation_retains_unknown_files_and_tampered_shell(self):
        shell = self.root / 'shell'
        shell.mkdir()
        for name in FILES:
            shutil.copyfile(ROOT / 'desktop' / name, shell / name)
        (shell / 'OWNED_FILES.json').write_text(json.dumps(make_manifest(shell, '0' * 40)), encoding='utf-8')
        (shell / 'connection.json').write_text(json.dumps(self.connection.as_dict()), encoding='utf-8')
        unknown = shell / 'output-sentinel.txt'
        unknown.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_UNKNOWN_OWNED_PATH'):
            uninstall(shell)
        self.assertTrue((shell / 'app.py').is_file())
        unknown.unlink()
        with (shell / 'app.py').open('ab') as stream:
            stream.write(b'\nchanged')
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_PACKAGE_CHANGED'):
            verify(shell)

    def test_stage_shell_excludes_tests_and_detects_destination_race(self):
        shell = self.root / 'source shell'
        shell.mkdir()
        for name in FILES:
            shutil.copyfile(ROOT / 'desktop' / name, shell / name)
        (shell / 'OWNED_FILES.json').write_text(json.dumps(make_manifest(shell, '0' * 40)), encoding='utf-8')
        (shell / 'unowned-tests').mkdir()
        output = self.root / 'staged shell'
        stage_shell(shell, output)
        self.assertEqual({p.name for p in output.iterdir()}, set(FILES) | {'OWNED_FILES.json'})
        verify(output)
        from desktop import draft
        original = draft.rename_new
        raced = self.root / 'raced'
        def race(source, destination):
            destination.mkdir()
            original(source, destination)
        with mock.patch('desktop.draft.rename_new', side_effect=race):
            with self.assertRaisesRegex(DesktopError, 'DESKTOP_OUTPUT_CONFLICT'):
                stage_shell(shell, raced)
        self.assertTrue(raced.is_dir())
        self.assertEqual(list(raced.iterdir()), [])


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='desktop-manifest-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkout = self.root / 'repo'
        self.checkout.mkdir()
        self.store = self.root / 'store'
        git = ['git', '-C', str(self.checkout), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@invalid',
               '-c', 'core.autocrlf=false', '-c', 'commit.gpgSign=false']
        subprocess.run([*git, 'init', '-q'], check=True)
        for index in range(75):
            (self.checkout / f'{index:03}.txt').write_bytes(('needle Я\r\n' * 3).encode('utf-8'))
        (self.checkout / 'binary.bin').write_bytes(bytes(range(256)))
        subprocess.run([*git, 'add', '-A'], check=True)
        subprocess.run([*git, 'commit', '-qm', 'fixture'], check=True)
        source = {'root': str(self.checkout), 'namespace': 'code', 'source_roots': ['.'], 'exclusions': []}
        self.sid = repo.start_scan(self.store, 'sce', source)
        while repo.scan_page(self.store, 'code', self.sid, limit=100)['state'] != 'COMPLETE':
            pass
        policy = self.root / 'policy.json'
        policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'max_parallel': 1, 'money_budget': 0}), encoding='utf-8')
        self.profile = self.root / 'profile.json'
        self.profile.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy), 'namespaces': ['code'], 'templates': {}, 'repositories': {'sce': source}}), encoding='utf-8')
        adapter = ROOT / 'content-lab' / 'native_adapter.py'
        connection = Connection.from_dict({'schema': 'occ.desktop-connection.v1', 'protocol': PROTOCOL,
            'python_path': sys.executable, 'adapter_path': str(adapter), 'profile_path': str(self.profile),
            'expected_adapter_sha256': sha_file(adapter), 'preferred_namespace': 'code'})
        self.client = DesktopClient(connection)
        self.addCleanup(self.client.close)
        self.client.handshake()

    def test_all_76_files_and_parts_stream_to_eof_with_readonly_owner(self):
        self.assertIn('durable.repo.manifest', self.client.info['capabilities'])
        before = sha_file(self.store / 'content.sqlite3')
        output = self.root / 'full manifest'
        result = save_manifest(output, self.client, 'sce', self.sid)
        rows = [json.loads(line) for line in (output / 'REPO_MANIFEST.jsonl').read_bytes().splitlines()]
        self.assertEqual(len(rows), 76)
        self.assertEqual([r['ordinal'] for r in rows], list(range(76)))
        self.assertEqual(result['rows'], 76)
        self.assertIsNone(result['global_repo_file_or_part_cap'])
        self.assertFalse(result['source_bytes_included'])
        part_output = self.root / 'parts'
        result = save_manifest(part_output, self.client, 'sce', self.sid, 'PARTS')
        parts = [json.loads(line) for line in (part_output / 'PARTS_INDEX.jsonl').read_bytes().splitlines()]
        self.assertEqual(result['rows'], len(parts))
        self.assertGreater(len(parts), 20)
        self.assertEqual(before, sha_file(self.store / 'content.sqlite3'))
        request = {'type': 'durable.repo.manifest', 'repository': 'sce', 'snapshotId': self.sid, 'action': 'INFO'}
        self.assertEqual(self.client.request(request)['result'], native.dispatch(request, self.profile))

    def test_current_main_source_classifier_and_readonly_gate_are_preserved(self):
        from source_eligibility import CLASSIFIER_VERSION
        request = {'type': 'durable.search', 'namespace': 'code', 'query': 'needle', 'limit': 1}
        hit = self.client.request(request)['result']['items'][0]
        context_request = {'type': 'durable.context', 'namespace': 'code', 'ids': [hit['id']]}
        value = self.client.request(context_request)['result']['context']
        self.assertEqual(value['source_classifier_version'], CLASSIFIER_VERSION)
        self.assertEqual(value, core.context_pack(self.store, 'code', [hit['id']], read_only=True))
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_CLASSIFIER_UNAVAILABLE'):
            validate_context(dict(value, source_classifier_version='future'), context_request)
        # A legacy source without current format facts remains excluded by the
        # shared owner, even if its historical text item is still retained.
        db = repo.db_for(self.store)
        try:
            with db:
                db.execute("UPDATE repo_entries SET analysis=json_remove(analysis,'$.format_eligibility') "
                           "WHERE snapshot_id=? AND path=?", (self.sid, value['items'][0]['path']))
        finally:
            db.close()
        before = sha_file(self.store / 'content.sqlite3')
        with self.assertRaisesRegex(DesktopError, 'FORMAT_BACKFILL_REQUIRED'):
            self.client.request(context_request)
        hits = self.client.request(request)['result']['items']
        self.assertTrue(hits)
        self.assertNotIn(hit['id'], [item['id'] for item in hits])
        self.assertEqual(before, sha_file(self.store / 'content.sqlite3'))
        reply = native.dispatch_desktop({'type': 'durable.repo.coverage', 'repository': 'sce',
                                         'snapshotId': self.sid, 'action': 'SUMMARY'}, self.profile)
        self.assertEqual(reply['error'], 'DESKTOP_READ_ONLY')

    def test_manifest_cancel_rolls_back_projection_and_cursor_fault_fails(self):
        cancelled = threading.Event()
        output = self.root / 'cancelled'
        def progress(_count, _total):
            cancelled.set()
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_CANCELLED'):
            save_manifest(output, self.client, 'sce', self.sid, cancel=cancelled, progress=progress)
        self.assertFalse(output.exists())
        request = {'type': 'durable.repo.manifest', 'repository': 'sce', 'snapshotId': self.sid,
                   'action': 'ENTRIES', 'offset': 0, 'limit': 20}
        reply = self.client.request(request)
        reply['result']['manifest']['nextOffset'] = 0
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_MANIFEST_CURSOR'):
            validate_reply(json.dumps(reply).encode(), request,
                           self.client.connection.expected_adapter_sha256, self.client.identity)


class ResearchReadSchemaTests(unittest.TestCase):
    def test_complete_pages_and_snapshot_type_fences(self):
        from desktop.client import validate_research, validate_request
        import copy
        request={'type':'durable.research.jobs','offset':20,'limit':20,'snapshot':'a'*64}
        row={'id':'b'*32,'state':'SUCCEEDED','domain_status':'MODEL_REPLAY_COMPLETED',
             'records':47,'useful_calls':45,'receipt_sha256':'c'*64,'qualified':False}
        page={'schema':'occ.research-jobs-page.v1','snapshot':'a'*64,'offset':20,
              'total':21,'items':[row],'next_offset':None}
        validate_request(request);validate_research(page,request)
        for mutation in ('snapshot','qualified','count','cursor','status','duplicate'):
            bad=copy.deepcopy(page)
            if mutation=='snapshot':bad['snapshot']='d'*64
            if mutation=='qualified':bad['items'][0]['qualified']=True
            if mutation=='count':bad['items'][0]['records']=True
            if mutation=='cursor':bad['next_offset']=21
            if mutation=='status':bad['items'][0]['domain_status']='LIVE_QUALIFIED'
            if mutation=='duplicate':bad['items']*=2;bad['total']=22
            with self.assertRaises(DesktopError):validate_research(bad,request)
        for bad in (request|{'limit':True},request|{'offset':-1},request|{'snapshot':'bad'},request|{'argv':['anything']}):
            with self.assertRaises(DesktopError):validate_request(bad)


if __name__ == '__main__':
    unittest.main()
