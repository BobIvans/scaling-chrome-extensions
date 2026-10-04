import json
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase

import native_adapter
import repo_context
import repo_history


class RepoHistoryTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.store = self.root / 'content.sqlite3'
        self.profile = {'root': str(self.repo), 'namespace': 'code',
                        'source_roots': ['.'], 'exclusions': []}
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)

    def commit(self, changes):
        for path, value in changes.items():
            target = self.repo / path
            if value is None:
                target.unlink()
            else:
                target.write_bytes(value)
        self.git('add', '-A')
        self.git('commit', '-qm', 'fixture')
        snapshot = repo_context.start_scan(self.store, 'sce', self.profile)
        while True:
            status = repo_context.scan_page(self.store, 'code', snapshot, limit=20)
            if status['state'] == 'COMPLETE':
                return snapshot

    def test_all_snapshots_and_changes_through_eof(self):
        self.commit({'old.txt': b'unique', 'removed.txt': b'gone'})
        for i in range(24):
            changes = {f'new{i:02}.txt': b'new' + str(i).encode()}
            if i == 0:
                changes.update({'old.txt': None, 'renamed.txt': b'unique',
                                'removed.txt': None})
            head = self.commit(changes)
        head = self.commit({f'bulk{i:02}.txt': str(i).encode() for i in range(25)})
        seen, cursor = [], None
        while True:
            page = repo_history.snapshots(self.store, 'code', 'sce', self.profile, limit=3, cursor=cursor)
            seen.extend(s['snapshot_id'] for s in page['snapshots'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        self.assertEqual(len(seen), 26)
        self.assertEqual(len(set(seen)), 26)
        self.assertEqual(seen[0], head)
        all_changes, cursor = [], None
        while True:
            page = repo_history.delta(self.store, 'code', 'sce', self.profile, head, limit=4, cursor=cursor)
            all_changes.extend(page['changes'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        self.assertEqual(len(all_changes), 25)
        self.assertEqual(all_changes[-1]['path'], 'bulk24.txt')
        earlier = seen[-2]
        first_delta = repo_history.delta(self.store, 'code', 'sce', self.profile, earlier, limit=10)
        renamed = [r for r in first_delta['changes'] if r['path'] == 'renamed.txt']
        self.assertEqual(renamed[0]['rename_peer'], 'old.txt')

    def test_native_scope_cursor_and_response(self):
        first = self.commit({'a.txt': b'one'})
        second = self.commit({'b.txt': b'two'})
        policy = self.root / 'policy.json'
        policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1',
                                      'money_budget': 0, 'max_parallel': 1}))
        profile = self.root / 'profile.json'
        profile.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1',
                                       'store': str(self.store), 'policy_file': str(policy),
                                       'namespaces': ['code'], 'templates': {},
                                       'repositories': {'sce': self.profile}}))
        result = native_adapter.dispatch({'type': 'durable.repo.history',
                                          'repository': 'sce', 'limit': 1}, profile)
        self.assertEqual(result['page']['snapshots'][0]['snapshot_id'], second)
        cursor = result['page']['next_cursor']
        result = native_adapter.dispatch({'type': 'durable.repo.history',
                                          'repository': 'sce', 'limit': 1, 'cursor': cursor}, profile)
        self.assertEqual(result['page']['snapshots'][0]['snapshot_id'], first)
        delta = native_adapter.dispatch({'type': 'durable.repo.delta',
                                         'repository': 'sce', 'snapshotId': second}, profile)
        self.assertEqual(delta['page']['changes'][0]['path'], 'b.txt')
        loaded, loaded_policy = native_adapter.operator_profile(profile)
        desktop_page = native_adapter.dispatch_loaded({'type': 'durable.repo.history',
            'repository': 'sce', 'limit': 1}, loaded, loaded_policy, desktop=True)
        self.assertEqual(desktop_page['page']['snapshots'][0]['snapshot_id'], second)
        with self.assertRaisesRegex(ValueError, 'REPO_CURSOR_INVALID'):
            native_adapter.dispatch({'type': 'durable.repo.delta', 'repository': 'sce',
                                     'snapshotId': first, 'cursor': cursor}, profile)
        with self.assertRaisesRegex(ValueError, 'REPO_OUTSIDE_OPERATOR_SCOPE'):
            native_adapter.dispatch({'type': 'durable.repo.history',
                                     'repository': 'other'}, profile)
        revoked = dict(self.profile, exclusions=['changed'])
        with self.assertRaisesRegex(ValueError, 'REPO_OUTSIDE_OPERATOR_SCOPE'):
            repo_history.snapshots(self.store, 'code', 'sce', revoked)

    def test_long_unicode_cursor_continues_without_path_budget_cutoff(self):
        self.commit({'base.txt': b'initial'})
        # Keep the fixture below Windows MAX_PATH while exercising UTF-8 cursors.
        long_path = '/'.join(['я' * 40] * 2) + '/long.txt'
        target = self.repo / long_path
        target.parent.mkdir(parents=True)
        target.write_bytes(b'long')
        (self.repo / (long_path + 'x')).write_bytes(b'next')
        self.git('add', '-A')
        self.git('commit', '-qm', 'unicode paths')
        head = repo_context.start_scan(self.store, 'sce', self.profile)
        while repo_context.scan_page(self.store, 'code', head)['state'] != 'COMPLETE':
            pass
        first = repo_history.delta(self.store, 'code', 'sce', self.profile, head, limit=1)
        self.assertEqual(first['changes'][0]['path'], long_path)
        self.assertIsNotNone(first['next_cursor'])
        second = repo_history.delta(self.store, 'code', 'sce', self.profile, head,
                                    limit=1, cursor=first['next_cursor'])
        self.assertEqual(second['changes'][0]['path'], long_path + 'x')
        self.assertTrue(second['eof'])
