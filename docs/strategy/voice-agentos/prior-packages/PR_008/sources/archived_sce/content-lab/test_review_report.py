import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase

import automation_core as core
import context_review as review
import native_adapter as native
import repo_context as repo
import review_report as report
import context_handoff


class ReportTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store, self.source, self.output = (self.root / name for name in ('store', 'source', 'output'))
        self.source.mkdir()
        self.output.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@invalid')
        self.git('config', 'core.autocrlf', 'false')
        (self.source / 'main.py').write_text('import helper\ndef answer():\n    return helper.value\n', encoding='utf-8')
        (self.source / 'helper.py').write_text('value = 42\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.repo_profile = {'root': str(self.source), 'namespace': 'code', 'source_roots': ['.'], 'exclusions': []}
        snapshot = repo.start_scan(self.store, 'sce', self.repo_profile)
        self.snapshot_id = snapshot
        while repo.scan_page(self.store, 'code', snapshot)['state'] != 'COMPLETE':
            pass
        exported = repo.export_request(self.store, 'code', snapshot, ['main.py'],
                                       'Check local result', 'Selected source and helper', ['Report contains both sources'])
        self.claim = exported['document']['review_result_template']
        self.claim['coverage']['reviewed'] = [r['source_key'] for r in self.claim['sources']]
        self.claim['coverage']['not_reviewed'] = []
        self.claim['findings'] = [{'finding_id': 'candidate', 'classification': 'CODE_DEFECT', 'disposition': 'DONE',
            'source_key': self.claim['sources'][0]['source_key'], 'source_sha256': self.claim['sources'][0]['sha256'],
            'criterion': 'Synthetic unverified claim', 'evidence_refs': [], 'duplicate_of': None, 'supersedes': None}]
        status = review.import_review(self.store, 'code', self.claim)
        self.profile = {'namespace': 'code', 'session_id': status['session_id'], 'review_id': status['review_id'],
                        'output_root': str(self.output), 'repository': 'sce', 'repository_profile': self.repo_profile}
        self.policy = {'schema': 'occ.automation-policy.v1', 'max_parallel': 1, 'money_budget': 0,
                       'reports': {'chosen': self.profile}}
        self.payload = {'kind': 'review_report', 'report_profile': 'chosen'}
        self.runner = core.Core(self.store, self.policy)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.source), *args], stderr=subprocess.DEVNULL).decode().strip()

    def enqueue(self, key='one'):
        return core.enqueue(self.store, self.policy, key, self.payload)

    def expire(self, job):
        db = core.connection(self.store)
        with db:
            db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (job['id'],))
        db.close()
        self.assertIsNone(self.runner.claim())
        self.assertEqual(self.runner.get(job['id'])['state'], 'NEEDS_RECONCILIATION')

    def test_worker_readback_restart_and_idempotent_replay(self):
        job = self.enqueue()
        result = self.runner.run_once()
        self.assertEqual(result['state'], 'SUCCEEDED')
        receipt = result['result']
        path = self.output / receipt['filename']
        self.assertEqual(path.read_bytes(), report.expected_report(self.store, self.profile))
        self.assertEqual(receipt['state'], 'SUCCESS_VERIFIED')
        self.assertFalse(receipt['findings_closed'])
        self.assertFalse(review.get_session(self.store, 'code', self.profile['session_id'])['findings'][0]['closed'])
        self.assertEqual(self.enqueue()['id'], job['id'])
        self.enqueue('second-key')
        self.assertTrue(core.Core(self.store, self.policy).run_once()['result']['reused'])
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_wrong_existing_result_is_not_success_or_overwritten(self):
        path = report.output_path(self.store, self.profile)
        path.write_bytes(b'process exited zero but this is not the report')
        self.enqueue()
        result = self.runner.run_once()
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertEqual(result['result']['reason'], 'REPORT_POSTCONDITION_FAILED')
        self.assertEqual(path.read_bytes(), b'process exited zero but this is not the report')

    def test_readback_rejects_equal_size_wrong_bytes_and_missing_file(self):
        expected = report.expected_report(self.store, self.profile)
        path = report.output_path(self.store, self.profile)
        with self.assertRaises(OSError):
            report.verify_output(path, expected)
        path.write_bytes(b'x' * len(expected))
        with self.assertRaisesRegex(ValueError, 'POSTCONDITION'):
            report.verify_output(path, expected)

    def test_dirty_dependency_head_or_index_blocks_output(self):
        for mode in ('dirty', 'index', 'head'):
            with self.subTest(mode=mode):
                self.git('reset', '--hard', self.claim['base_repo_sha'])
                (self.source / 'helper.py').write_text('value = 99\n', encoding='utf-8')
                if mode in {'index', 'head'}:
                    self.git('add', 'helper.py')
                if mode == 'head':
                    self.git('commit', '-qm', 'changed')
                with self.assertRaisesRegex(ValueError, 'CURRENT_COMPLETE'):
                    report.write_report(self.store, self.profile)
                self.assertEqual(list(self.output.iterdir()), [])

    def test_review_superseded_or_scope_revoked_blocks_output(self):
        revoked = copy.deepcopy(self.profile)
        revoked['repository_profile']['exclusions'] = ['helper.py']
        with self.assertRaisesRegex(ValueError, 'CURRENT_COMPLETE'):
            report.write_report(self.store, revoked)
        changed = copy.deepcopy(self.claim)
        changed['findings'][0]['criterion'] = 'superseding review'
        review.import_review(self.store, 'code', changed)
        with self.assertRaisesRegex(ValueError, 'REVIEW_CHANGED'):
            report.write_report(self.store, self.profile)

    def test_unknown_coverage_cannot_be_called_complete(self):
        changed = copy.deepcopy(self.claim)
        changed['coverage']['reviewed'] = []
        status = review.import_review(self.store, 'code', changed)
        profile = self.profile | {'review_id': status['review_id']}
        with self.assertRaisesRegex(ValueError, 'COVERAGE_INCOMPLETE'):
            report.write_report(self.store, profile)

    def test_output_root_cannot_include_store_or_source(self):
        for root in (self.root, self.store, self.source):
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'BOUNDARY'):
                report.write_report(self.store, self.profile | {'output_root': str(root)})

    def test_source_changes_after_write_prevent_success(self):
        calls = 0
        def progress():
            nonlocal calls
            calls += 1
            if calls == 3:
                (self.source / 'helper.py').write_text('value = 9\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'CURRENT_COMPLETE'):
            report.write_report(self.store, self.profile, progress=progress)

    def test_cancel_after_effect_keeps_cancelled_without_duplicate_output(self):
        job = self.enqueue()
        claimed = self.runner.claim()
        report.write_report(self.store, self.profile)
        self.runner.cancel(job['id'])
        self.expire(claimed)
        result = self.runner.reconcile_report(job['id'], True)
        self.assertEqual(result['state'], 'CANCELLED')
        self.assertEqual(result['result']['state'], 'SUCCESS_VERIFIED')
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_crash_after_effect_reconciles_without_writing(self):
        job = self.enqueue()
        claimed = self.runner.claim()
        receipt = report.write_report(self.store, self.profile)
        self.expire(claimed)
        path = self.output / receipt['filename']
        before = path.stat().st_mtime_ns
        with self.assertRaisesRegex(ValueError, 'PROCESS_STOP'):
            self.runner.reconcile_report(job['id'], False)
        result = self.runner.reconcile_report(job['id'], True)
        self.assertEqual(result['state'], 'SUCCEEDED')
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_crash_before_or_during_effect_never_creates_output_on_reconcile(self):
        for partial in (False, True):
            with self.subTest(partial=partial):
                job = self.enqueue('partial' if partial else 'missing')
                claimed = self.runner.claim()
                if partial:
                    report.output_path(self.store, self.profile).write_bytes(b'partial')
                self.expire(claimed)
                result = self.runner.reconcile_report(job['id'], True)
                self.assertEqual(result['state'], 'BLOCKED')
                self.assertEqual(len(list(self.output.iterdir())), int(partial))

    def native_profile(self):
        policy_path, profile_path = self.root / 'policy.json', self.root / 'native.json'
        policy_path.write_text(json.dumps(self.policy), encoding='utf-8')
        profile = {'schema': 'occ.native-durable-profile.v1', 'store': str(self.store), 'policy_file': str(policy_path),
                   'namespaces': ['code'], 'templates': {'report': self.payload}, 'repositories': {'sce': self.repo_profile}}
        profile_path.write_text(json.dumps(profile), encoding='utf-8')
        return profile_path

    def test_native_enqueue_scope_and_visible_result_without_private_paths(self):
        path = self.native_profile()
        request = {'type': 'durable.review.report', 'namespace': 'code', 'sessionId': self.profile['session_id'],
                   'template': 'report', 'taskKey': 'native-one'}
        with self.assertRaisesRegex(ValueError, 'SESSION_MISMATCH'):
            native.dispatch(request | {'sessionId': 'a' * 64}, path)
        job = native.dispatch(request, path)['job']
        self.assertEqual(job['next_step'], 'RUN_REGISTERED_LOCAL_WORKER')
        self.runner.run_once()
        result = native.dispatch({'type': 'durable.get', 'jobId': job['id']}, path)['job']
        self.assertEqual(result['outcome']['verified_property'], 'LOCAL_REPORT_BYTES')
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn('Synthetic unverified claim', json.dumps(result))

    def test_template_cannot_choose_path_session_shell_or_budget(self):
        for field in ('output_root', 'session_id', 'argv', 'money_budget'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'REPORT_JOB_SCHEMA'):
                core.enqueue(self.store, self.policy, 'invalid', self.payload | {field: 'injection'})
        bad = copy.deepcopy(self.policy)
        bad['reports']['chosen']['review_id'] = 'invalid'
        with self.assertRaisesRegex(ValueError, 'HASH'):
            core.enqueue(self.store, bad, 'bad', self.payload)

    def test_real_isolated_adapter_returns_queue_and_worker_receipt(self):
        profile_path = self.native_profile()
        adapter = Path(native.__file__)
        def call(value):
            process = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(adapter), '--profile', str(profile_path)],
                                     input=json.dumps(value).encode(), capture_output=True, check=True)
            response = json.loads(process.stdout)
            self.assertTrue(response['ok'], response)
            return response['result']
        job = call({'type': 'durable.review.report', 'namespace': 'code', 'sessionId': self.profile['session_id'],
                    'template': 'report', 'taskKey': 'isolated-one'})['job']
        worker = subprocess.run([sys.executable, str(Path(core.__file__)), '--store', str(self.store), 'work',
                                 '--policy', str(self.root / 'policy.json')], capture_output=True, check=True)
        self.assertEqual(json.loads(worker.stdout)['state'], 'SUCCEEDED')
        result = call({'type': 'durable.get', 'jobId': job['id']})['job']
        self.assertEqual(result['outcome']['state'], 'SUCCESS_VERIFIED')

    def test_v7_handoff_roundtrip_preserves_v4_v5_and_canonical_ledger(self):
        profiles = {'sce': self.repo_profile}
        bundle = context_handoff.handoff(self.store, 'code', self.profile['session_id'], repo_profiles=profiles)
        self.assertEqual(bundle['request']['schema_version'], '4.0')
        self.assertEqual(bundle['overlay']['schema'], 'occ.evidence_overlay.v5')
        self.assertIn('Selected source and helper', bundle['rendered_txt'])
        self.assertFalse(bundle['overlay']['authorization_granted'])
        reply = bundle['review_template']
        reply['v4_review']['disposition'] = 'PROPOSE_CHANGE'
        reply['v4_review']['summary'] = 'Proposal with no trusted evidence'
        status = context_handoff.import_bound(self.store, 'code', self.profile['session_id'], reply, repo_profiles=profiles)
        self.assertFalse(status['findings'][0]['closed'])
        self.assertEqual(status['findings'][0]['classification'], 'PROPOSAL_ONLY')
        self.assertEqual(context_handoff.import_bound(self.store, 'code', self.profile['session_id'], reply, repo_profiles=profiles)['import_state'], 'UNCHANGED')
        db = core.connection(self.store)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM review_bound_claims').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)
        finally:
            db.close()

    def test_v7_wrong_goal_scope_overlay_and_changed_source_reject(self):
        profiles = {'sce': self.repo_profile}
        bundle = context_handoff.handoff(self.store, 'code', self.profile['session_id'], repo_profiles=profiles)
        with self.assertRaisesRegex(ValueError, 'OVERLAY'):
            context_handoff.import_bound(self.store, 'code', self.profile['session_id'], bundle['review_template'] | {'overlay_digest': '0'*64}, repo_profiles=profiles)
        other = repo.export_request(self.store, 'code', self.snapshot_id,
                                    ['main.py'], 'Changed goal', 'Changed scope', ['Different criterion'])
        with self.assertRaisesRegex(ValueError, 'OVERLAY'):
            context_handoff.import_bound(self.store, 'code', other['review']['session_id'], bundle['review_template'], repo_profiles=profiles)
        (self.source / 'helper.py').write_text('value = 99\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'CURRENT_COMPLETE'):
            context_handoff.import_bound(self.store, 'code', self.profile['session_id'], bundle['review_template'], repo_profiles=profiles)

    def test_v7_native_handoff_is_bounded_and_bound_import_uses_selected_session(self):
        profile_path = self.native_profile()
        request = {'type': 'durable.review.handoff', 'namespace': 'code', 'sessionId': self.profile['session_id']}
        handoff = native.dispatch(request, profile_path)['handoff']
        self.assertLess(len(json.dumps(handoff).encode()), native.OUTPUT_BYTES)
        reply = native.dispatch({'type': 'durable.review.importBound', 'namespace': 'code',
                                 'sessionId': self.profile['session_id'], 'review': handoff['review_template']}, profile_path)
        self.assertFalse(reply['review']['execution_authorized'])
