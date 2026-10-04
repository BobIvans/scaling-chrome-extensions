"""Independent file fixtures for immutable originals and recoverable staging."""
import hashlib
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from automation_core import read_connection
import source_ledger as ledger


class SourceLedgerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = self.root / 'store'
        self.first = self.root / 'first.bin'
        self.second = self.root / 'second.bin'

    def test_reuse_versions_observations_pages_and_exact_bytes(self):
        raw = b'a' * 65536 + b'b' * 65536 + b'last'
        self.first.write_bytes(raw)
        self.second.write_bytes(raw)
        first = ledger.capture_file(self.store, 'docs', 'FILE', self.first, '1' * 32)
        replay = ledger.capture_file(self.store, 'docs', 'FILE', self.first, '1' * 32)
        observed = ledger.capture_file(self.store, 'docs', 'FILE', self.first, '2' * 32)
        other = ledger.capture_file(self.store, 'docs', 'FILE', self.second, '3' * 32)
        self.assertEqual((first['raw_sha'], first['size'], first['parts']),
                         (hashlib.sha256(raw).hexdigest(), len(raw), 3))
        self.assertTrue(replay['reused'])
        self.assertEqual(first['version_id'], observed['version_id'])
        self.assertNotEqual(first['observation_id'], observed['observation_id'])
        self.assertEqual(other['raw_sha'], first['raw_sha'])
        self.assertNotEqual(other['source_id'], first['source_id'])
        db = read_connection(self.store)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM source_raw_objects').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM source_raw_parts').fetchone()[0], 3)
            self.assertEqual(db.execute('SELECT count(*) FROM source_observations').fetchone()[0], 3)
        finally:
            db.close()
        page = ledger.raw_parts(self.store, 'docs', first['version_id'], limit=2)
        self.assertEqual([p['ordinal'] for p in page['parts']], [0, 1])
        self.assertEqual(page['next_cursor'], 1)
        tail = ledger.raw_parts(self.store, 'docs', first['version_id'], after=1, limit=2)
        self.assertEqual([p['ordinal'] for p in tail['parts']], [2])
        self.assertTrue(tail['eof'])
        self.assertEqual(b''.join(ledger.read_part(self.store, 'docs', first['version_id'], i)
                                  for i in range(3)), raw)
        with self.assertRaisesRegex(ValueError, 'SOURCE_OUTSIDE_SCOPE'):
            ledger.raw_parts(self.store, 'other', first['version_id'])

    def test_interrupted_stage_never_publishes_and_recovery_reuses_parts(self):
        self.first.write_bytes(b'x' * (ledger.PART_BYTES * 2 + 1))
        calls = [0]
        def interrupt():
            calls[0] += 1
            if calls[0] == 4:
                raise RuntimeError('injected stop after first committed part')
        with self.assertRaisesRegex(RuntimeError, 'injected stop'):
            ledger.capture_file(self.store, 'docs', 'FILE', self.first, '1' * 32,
                                progress=interrupt)
        db = read_connection(self.store)
        try:
            self.assertEqual(db.execute('SELECT state FROM source_raw_objects').fetchone()[0], 'STAGING')
            self.assertEqual(db.execute('SELECT count(*) FROM source_raw_parts').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM source_versions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM source_heads').fetchone()[0], 0)
        finally:
            db.close()
        result = ledger.capture_file(self.store, 'docs', 'FILE', self.first, '1' * 32)
        self.assertEqual((result['state'], result['parts']), ('COMPLETE', 3))

    def test_drift_and_corruption_do_not_publish(self):
        self.first.write_bytes(b'a' * (ledger.PART_BYTES + 1))
        changed = [False]
        def mutate():
            if not changed[0]:
                changed[0] = True
                self.first.write_bytes(b'z' * (ledger.PART_BYTES + 1))
        with self.assertRaisesRegex(ValueError, 'SOURCE_DRIFT'):
            ledger.capture_file(self.store, 'docs', 'FILE', self.first, '1' * 32,
                                progress=mutate)
        result = ledger.capture_file(self.store, 'docs', 'FILE', self.first, '2' * 32)
        db = read_connection(self.store)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM source_versions').fetchone()[0], 1)
        finally:
            db.close()
        writer = ledger._db(self.store)
        try:
            with writer:
                writer.execute('UPDATE source_raw_parts SET raw=? WHERE raw_sha=? AND ordinal=0',
                               (b'corrupt', result['raw_sha']))
        finally:
            writer.close()
        with self.assertRaisesRegex(ValueError, 'SOURCE_RAW_CORRUPT'):
            ledger.read_part(self.store, 'docs', result['version_id'], 0)

    def test_empty_and_version_history_keyset(self):
        self.first.write_bytes(b'')
        first = ledger.capture_file(self.store, 'docs', 'FILE', self.first, '0' * 32)
        self.assertEqual((first['size'], first['parts']), (0, 0))
        for index in range(22):
            self.first.write_bytes(f'revision {index}'.encode())
            ledger.capture_file(self.store, 'docs', 'FILE', self.first, f'{index + 1:032x}')
        seen, cursor = [], None
        while True:
            page = ledger.versions(self.store, 'docs', first['source_id'], after=cursor, limit=3)
            seen.extend(item['version_id'] for item in page['versions'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        self.assertEqual((len(seen), len(set(seen))), (23, 23))

    def test_installed_style_isolated_cli(self):
        self.first.write_bytes(b'local original\x00binary')
        result = subprocess.run([sys.executable, '-I', '-X', 'utf8',
            str(Path(ledger.__file__)), '--store', str(self.store), '--namespace', 'docs',
            '--kind', 'FILE', '--path', str(self.first), '--intent-key', 'a' * 32],
            check=True, capture_output=True)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['raw_sha'], hashlib.sha256(self.first.read_bytes()).hexdigest())
        self.assertEqual(receipt['state'], 'COMPLETE')


if __name__ == '__main__':
    unittest.main()
