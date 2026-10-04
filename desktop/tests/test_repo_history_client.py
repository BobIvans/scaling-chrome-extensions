import sys
from pathlib import Path
import json
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from desktop import client, draft


class HistoryClientTests(unittest.TestCase):
    def test_strict_history_and_delta_pages(self):
        req = {'type': 'durable.repo.history', 'repository': 'sce', 'limit': 1}
        client.validate_request(req)
        page = {'schema': 'occ.repo-history-page.v1', 'namespace': 'code',
                'alias': 'sce', 'snapshots': [{'snapshot_id': 'a' * 64,
                'alias': 'sce', 'repo_sha': 'b' * 40, 'cursor': 1,
                'total': 1, 'created': 1.5}], 'next_cursor': None, 'eof': True}
        client.validate_history_page(page, req)
        with self.assertRaises(client.DesktopError):
            client.validate_history_page({**page, 'eof': False}, req)
        delta_req = {'type': 'durable.repo.delta', 'repository': 'sce',
                     'snapshotId': 'a' * 64, 'limit': 1}
        client.validate_request(delta_req)
        delta = {'schema': 'occ.repo-delta-page.v1', 'snapshot_id': 'a' * 64,
                 'base_snapshot_id': 'c' * 64, 'base_repo_sha': 'd' * 40,
                 'changes': [{'path': 'a.py', 'kind': 'MODIFIED', 'oid': 'b' * 40,
                              'mode': '100644', 'previous_oid': 'c' * 40,
                              'previous_mode': '100644'}],
                 'next_cursor': None, 'eof': True, 'scope': 'PINNED_TREE_PATHS'}
        client.validate_delta_page(delta, delta_req)
        client.validate_request(dict(delta_req, baseSnapshotId='c' * 64))
        client.validate_delta_page(delta, dict(delta_req, baseSnapshotId='c' * 64))
        with self.assertRaises(client.DesktopError):
            client.validate_delta_page({**delta, 'snapshot_id': '0' * 64}, delta_req)
        with self.assertRaises(client.DesktopError):
            client.validate_delta_page(delta, dict(delta_req, baseSnapshotId='0' * 64))

    def test_continuation_and_cancel(self):
        class Fake:
            info = {'namespaces': ['code']}
            calls = []

            def request(self, request):
                self.calls.append(request)
                token = request.get('cursor')
                page = {'namespace': 'code', 'snapshots': [token or 'first'],
                        'next_cursor': 'next' if token is None else None}
                return {'result': {'page': page}}

        fake = Fake()
        self.assertEqual([page['snapshots'][0] for page in client.DesktopClient.history_pages(fake, 'sce')],
                         ['first', 'next'])
        self.assertEqual(fake.calls[1]['cursor'], 'next')

    def test_atomic_complete_export(self):
        class Fake:
            identity = None

            def history_pages(self, repository, *, cancel=None):
                self.repository = repository
                for i in range(3):
                    yield {'snapshots': [{'snapshot_id': str(i)}]}

            def delta_pages(self, repository, snapshot_id, *, cancel=None):
                yield {'snapshot_id': snapshot_id, 'base_snapshot_id': 'base',
                       'changes': [{'path': 'a.py'}]}

        with tempfile.TemporaryDirectory() as temp:
            fake = Fake()
            out = Path(temp) / 'history'
            receipt = draft.save_repo_history(out, fake, 'sce')
            self.assertEqual(receipt['rows'], 3)
            self.assertEqual([json.loads(row)['snapshot_id'] for row in
                              (out / 'REPO_SNAPSHOTS.jsonl').read_text().splitlines()],
                             ['0', '1', '2'])
            delta = draft.save_repo_history(Path(temp) / 'delta', fake, 'sce', snapshot_id='h')
            self.assertEqual((delta['rows'], delta['base_snapshot_id']), (1, 'base'))


if __name__ == '__main__':
    unittest.main()
