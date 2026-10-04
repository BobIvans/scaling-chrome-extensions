"""Opt-in Desktop control uses the same committed repository scan ledger."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'content-lab'))
sys.path.insert(0, str(ROOT))
from desktop.client import Connection, DesktopClient, DesktopError, sha_file, validate_scan_run
import repo_context
from test_repo_history import RepoHistoryTests


class DesktopScanTests(unittest.TestCase):
    setUp = RepoHistoryTests.setUp
    git = RepoHistoryTests.git
    def connect_client(self):
        adapter = ROOT / 'content-lab' / 'native_adapter.py'
        connection = Connection.from_dict({'schema': 'occ.desktop-connection.v1',
            'protocol': 'occ.desktop-stdio.v1', 'python_path': sys.executable,
            'adapter_path': str(adapter), 'profile_path': str(self.profile_path),
            'expected_adapter_sha256': sha_file(adapter), 'preferred_namespace': 'code'})
        client = DesktopClient(connection)
        self.addCleanup(client.close)
        client.handshake()
        return client

    def test_opt_in_scan_survives_client_reopen_and_step_replay(self):
        (self.repo / 'one.py').write_text('x = 1\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'base')
        repo_context.db_for(self.store).close()
        policy = self.root / 'policy.json'
        policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1',
                                      'money_budget': 0, 'max_parallel': 1}))
        self.profile_path = self.root / 'profile.json'
        profile = {'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
                   'policy_file': str(policy), 'namespaces': ['code'], 'templates': {},
                   'repositories': {'sce': self.profile}}
        self.profile_path.write_text(json.dumps(profile))
        client = self.connect_client()
        self.assertNotIn('durable.repo.scanRun', client.info['capabilities'])
        with self.assertRaisesRegex(DesktopError, 'DESKTOP_CAPABILITY_UNAVAILABLE'):
            client.request({'type': 'durable.repo.scanRun', 'repository': 'sce', 'action': 'STATUS'})
        profile['desktop_scan_enabled'] = True
        self.profile_path.write_text(json.dumps(profile))
        client = self.connect_client()
        self.assertIn('durable.repo.scanRun', client.info['capabilities'])
        start = client.request({'type': 'durable.repo.scanRun', 'repository': 'sce',
                                'action': 'START', 'intentKey': '1' * 32})['result']['scan_run']
        self.assertEqual((start['state'], start['cursor'], start['total']), ('RUNNING', 0, 1))
        paused = client.request({'type': 'durable.repo.scanRun', 'repository': 'sce',
                                 'action': 'PAUSE', 'runId': start['run_id'],
                                 'expectedRevision': start['run_revision']})['result']['scan_run']
        client.close()
        client = self.connect_client()
        status = client.request({'type': 'durable.repo.scanRun', 'repository': 'sce',
                                 'action': 'STATUS'})['result']['scan_run']
        self.assertEqual(status['state'], 'PAUSED')
        resumed = client.request({'type': 'durable.repo.scanRun', 'repository': 'sce',
                                  'action': 'CONTINUE', 'runId': status['run_id'],
                                  'expectedRevision': status['run_revision']})['result']['scan_run']
        step = {'type': 'durable.repo.scanRun', 'repository': 'sce', 'action': 'STEP',
                'runId': resumed['run_id'], 'expectedRevision': resumed['run_revision'],
                'expectedCursor': resumed['cursor']}
        done = client.request(step)['result']['scan_run']
        self.assertEqual((done['state'], done['cursor']), ('COMPLETE', 1))
        self.assertEqual(client.request(step)['result']['scan_run']['cursor'], 1)
        with self.assertRaises(DesktopError):
            validate_scan_run(dict(done, processed=2), step)


if __name__ == '__main__':
    unittest.main()
