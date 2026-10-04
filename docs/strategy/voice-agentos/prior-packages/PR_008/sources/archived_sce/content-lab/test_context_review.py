import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase

import automation_core as core
import context_review as review
import native_adapter


class ReviewTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / 'store'
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'note.md').write_text('Synthetic selected source', encoding='utf-8')
        core.sync(self.store, 'project', self.source)
        self.ids = [r['id'] for r in core.search(self.store, 'project', 'selected')]
        self.session = review.create_session(self.store, 'project', self.ids, 'private review goal', 'a' * 40)
        self.result = {'schema': 'occ.review-result.v1', 'session_id': self.session['session_id'],
            'snapshot_sha256': self.session['snapshot_sha256'], 'sources': self.session['sources'],
            'base_repo_sha': 'a' * 40,
            'coverage': {'reviewed': ['note.md'], 'not_reviewed': [], 'missing_dependencies': []},
            'findings': [{'finding_id': 'F001', 'classification': 'CODE_DEFECT', 'disposition': 'DONE',
                'source_key': 'note.md', 'source_sha256': self.session['sources'][0]['sha256'],
                'criterion': 'Claimed fixed by model', 'evidence_refs': [{'kind': 'TEST_RECEIPT', 'sha256': 'f' * 64}],
                'duplicate_of': None, 'supersedes': None}]}

    def test_restart_discovers_export_without_restoring_permissions(self):
        review.import_review(self.store, 'project', self.result)
        runner = Path(review.__file__)
        process = subprocess.run([sys.executable, str(runner), '--store', str(self.store),
            '--namespace', 'project', 'list'], capture_output=True, text=True, check=True)
        status = json.loads(process.stdout)[0]
        self.assertEqual(status['export_bundle_id'], self.session['export_bundle_id'])
        self.assertEqual(status['state'], 'NEEDS_REVIEW')
        for key in ('execution_authorized', 'dispatch_allowed', 'approvals_restored', 'timers_restored'):
            self.assertFalse(status[key])
        self.assertNotIn('private review goal', process.stdout)
        self.assertNotIn('Claimed fixed by model', process.stdout)

    def test_idempotence_versioning_and_old_replay(self):
        first = review.import_review(self.store, 'project', self.result)
        repeated = review.import_review(self.store, 'project', self.result)
        self.assertEqual(repeated['duplicate_of'], first['review_id'])
        changed = copy.deepcopy(self.result)
        changed['findings'][0]['disposition'] = 'OPEN'
        second = review.import_review(self.store, 'project', changed)
        self.assertEqual(second['supersedes'], first['review_id'])
        self.assertNotEqual(second['review_id'], first['review_id'])
        self.assertEqual(review.import_review(self.store, 'project', self.result)['review_id'], second['review_id'])
        self.assertEqual(review.create_session(self.store, 'project', self.ids, 'private review goal', 'a' * 40)['session_id'], self.session['session_id'])
        db = core.connection(self.store)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM review_results').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)
        finally:
            db.close()

    def test_done_and_supplied_test_receipt_cannot_close_finding(self):
        result = review.import_review(self.store, 'project', self.result)
        self.assertEqual(result['findings'][0]['state'], 'STATIC_CANDIDATE')
        self.assertFalse(result['findings'][0]['closed'])
        self.assertFalse(result['findings'][0]['evidence_verified'])

    def test_changed_source_becomes_stale(self):
        (self.source / 'note.md').write_text('changed selected source', encoding='utf-8')
        core.sync(self.store, 'project', self.source)
        result = review.import_review(self.store, 'project', self.result)
        self.assertEqual(result['state'], 'STALE')
        self.assertEqual(result['changed_dependencies'], ['note.md'])
        self.assertFalse(result['execution_authorized'])

    def test_missing_dependency_needs_context(self):
        (self.source / 'note.md').unlink()
        core.sync(self.store, 'project', self.source)
        self.assertEqual(review.import_review(self.store, 'project', self.result)['state'], 'NEEDS_CONTEXT')
        self.assertEqual(review.get_session(self.store, 'project', self.session['session_id'])['missing_dependencies'], ['note.md'])

    def test_missing_coverage_needs_context(self):
        self.result['coverage']['missing_dependencies'] = ['device receipt']
        self.assertEqual(review.import_review(self.store, 'project', self.result)['state'], 'NEEDS_CONTEXT')

    def test_changed_snapshot_and_hash_and_base_reject(self):
        for change in ({'snapshot_sha256': 'b' * 64}, {'base_repo_sha': 'b' * 40},
                       {'sources': [self.session['sources'][0] | {'item_id': 'c' * 64}]}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'BINDING'):
                review.import_review(self.store, 'project', self.result | change)

    def test_strict_json_and_no_action_fields(self):
        for raw in (b'{"schema":1,"schema":2}', b'{"value":NaN}', b'x' * (review.MAX_BYTES + 1)):
            with self.assertRaises(ValueError):
                review.strict_json(raw)
        for key in ('argv', 'patches', 'approval', 'execution_authorized', 'shell'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                review.import_review(self.store, 'project', self.result | {key: True})
        self.result['findings'] = self.result['findings'] * 51
        with self.assertRaises(ValueError):
            review.import_review(self.store, 'project', self.result)

    def test_namespace_isolation(self):
        for method in (review.get_session,):
            with self.assertRaisesRegex(ValueError, 'OUTSIDE_SCOPE'):
                method(self.store, 'private', self.session['session_id'])
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SCOPE'):
            review.import_review(self.store, 'private', self.result)
        self.assertEqual(review.list_sessions(self.store, 'private'), [])

    def test_corrupt_persisted_session_rejected(self):
        db = core.connection(self.store)
        with db:
            db.execute("UPDATE review_sessions SET payload='{}'")
        db.close()
        with self.assertRaisesRegex(ValueError, 'CORRUPT'):
            review.get_session(self.store, 'project', self.session['session_id'])

    def test_existing_native_surface_with_scoped_operator_profile(self):
        policy = {'schema': 'occ.automation-policy.v1', 'max_parallel': 1, 'money_budget': 0, 'sources': {}, 'repos': {}}
        policy_path = self.root / 'policy.json'
        policy_path.write_text(json.dumps(policy), encoding='utf-8')
        profile = {'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
                   'policy_file': str(policy_path), 'namespaces': ['project'], 'templates': {}}
        profile_path = self.root / 'profile.json'
        profile_path.write_text(json.dumps(profile), encoding='utf-8')
        value = native_adapter.dispatch({'type': 'durable.review.list', 'namespace': 'project'}, profile_path)
        self.assertEqual(value['reviews'][0]['session_id'], self.session['session_id'])
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SCOPE'):
            native_adapter.dispatch({'type': 'durable.review.get', 'namespace': 'private', 'sessionId': self.session['session_id']}, profile_path)
        status = native_adapter.dispatch({'type': 'durable.review.import', 'namespace': 'project', 'review': self.result}, profile_path)['review']
        self.assertEqual(status['state'], 'NEEDS_REVIEW')
