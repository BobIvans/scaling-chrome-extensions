"""Real SQLite/CLI, exact-byte, and process-boundary export qualification."""
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlsplit, unquote
import zipfile

import repo_archive as archive
import repo_context as repo
import repo_archive_input as manifest
import repo_scan
from repo_artifacts import file_proof

LAB = Path(archive.__file__).parent


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.scripts = [], set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'href' in attrs:
            self.links.append(attrs['href'])
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag in {'script', 'iframe', 'img'} or 'src' in attrs:
            self.scripts.append(tag)


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.root = Path(cls.fixture.name)
        cls.checkout = cls.root / 'repo'
        cls.checkout.mkdir()
        cls.source = {'root': str(cls.checkout), 'namespace': 'code', 'source_roots': ['.'], 'exclusions': ['operator']}
        cls.raw_sources = {'long.txt': b'L' * (32 * 4096) + b'tail',
                           'binary.bin': bytes(range(256)) * 2, 'empty.txt': b'',
                           'text/русский.txt': 'Привет\r\n👋 — весь контекст\n'.encode()}
        cls.raw_sources.update({f'files/{n:03}.py': f'x = {n}\n'.encode() for n in range(42)})
        for path, raw in dict(cls.raw_sources, **{'.env': b'protected', 'credentials.json': b'protected',
                 'operator/private.txt': b'protected', 'secrets.txt': b'-----BEGIN PRIVATE KEY-----\nprotected'}).items():
            target = cls.checkout / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        def git(*args):
            return subprocess.run(['git', '-C', str(cls.checkout), *args], capture_output=True, check=True)
        git('init', '-q')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        git('config', 'core.autocrlf', 'false')
        git('add', '-A')
        git('commit', '-qm', 'fixture')
        cls.baseline = cls.root / 'baseline'
        cls.snapshot_id = repo.start_scan(cls.baseline, 'sce', cls.source)
        while repo.scan_page(cls.baseline, 'code', cls.snapshot_id, limit=100)['state'] != 'COMPLETE':
            pass
        # No WAL files remain after the last source connection closes.

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.store, self.directory, self.output = self.work / 'store', self.work / 'manifest', self.work / 'exports'
        shutil.copytree(self.baseline, self.store)
        self.policy = self.work / 'policy.json'
        self.policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'money_budget': 0, 'max_parallel': 1}))
        self.profile = self.work / 'profile.json'
        self.profile_value = {'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
                              'policy_file': str(self.policy), 'namespaces': ['code'],
                              'templates': {}, 'repositories': {'sce': self.source}}
        self.profile.write_text(json.dumps(self.profile_value))
        self.batch = manifest.write_manifest(self.store, 'sce', self.source, self.snapshot_id, self.directory)
        self.export_id = repo.digest(archive.export_binding(self.batch, self.directory))
        self.stage = self.output / ('.stage-' + self.export_id)
        self.final = self.output / ('REPO_' + self.export_id + '.zip')
        self.receipt = self.output / ('REPO_' + self.export_id + '.receipt.json')

    def build(self, **kwargs):
        return archive.build(self.profile, 'sce', self.directory, self.output, **kwargs)

    def command(self, event=None, behavior='kill', count=1):
        if event is None:
            return [sys.executable, '-I', '-X', 'utf8', str(LAB / 'repo_archive.py'),
                    '--profile', str(self.profile), '--repository', 'sce', '--manifest', str(self.directory), '--output', str(self.output)]
        script = '''import sys,os,json,errno
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import repo_archive as a
n=0
def hook(event,**context):
 global n
 if event!=sys.argv[6]:return
 n+=1
 if n!=int(sys.argv[8]):return
 if sys.argv[7]=='kill':os._exit(91)
 if sys.argv[7]=='hold':
  print('HELD',flush=True)
  sys.stdin.read(1)
 if sys.argv[7]=='disk':raise OSError(errno.ENOSPC,'injected full disk')
 if sys.argv[7]=='permission':raise OSError(errno.EACCES,'injected permission')
a.boundary=hook
sys.exit(a.main(['--profile',sys.argv[2],'--repository','sce','--manifest',sys.argv[3],'--output',sys.argv[4]]+json.loads(sys.argv[5])))
'''
        return [sys.executable, '-I', '-X', 'utf8', '-c', script, str(LAB), str(self.profile),
                str(self.directory), str(self.output), '[]', event, behavior, str(count)]

    def run_fault(self, event, behavior='kill', count=1):
        result = subprocess.run(self.command(event, behavior, count), capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 91 if behavior == 'kill' else 2, result.stderr.decode())
        return result

    def payload_proofs(self):
        return {p.name: (file_proof(p), p.stat().st_mtime_ns) for p in (self.stage / 'payload/parts').glob('*.bin')}

    def test_real_cli_all_50_entries_78_parts_exact_bytes_zip64_and_sorted_outputs(self):
        before = self.source_digest()
        result = subprocess.run(self.command(), capture_output=True, check=True, timeout=30)
        receipt = json.loads(result.stdout)
        self.assertEqual((receipt['entry_count'], receipt['part_count'], receipt['gap_count']), (50, 78, 4))
        self.assertTrue(receipt['captured_export_complete'])
        self.assertFalse(receipt['all_tracked_bytes_exportable'])
        self.assertEqual(before, self.source_digest())
        with zipfile.ZipFile(self.final) as zf:
            entries = [json.loads(l) for l in zf.read('REPO_MANIFEST.jsonl').splitlines()]
            parts = [json.loads(l) for l in zf.read('PARTS_INDEX.jsonl').splitlines()]
            outputs = [json.loads(l) for l in zf.read('EXPORT_MANIFEST.jsonl').splitlines()]
            self.assertEqual(len(entries), 50)
            self.assertEqual(len(parts), 78)
            names = [o['path'] for o in outputs]
            self.assertEqual(names, sorted(names))
            self.assertEqual(set(names) | {'EXPORT_MANIFEST.jsonl'}, set(zf.namelist()))
            self.assertIsNone(zf.testzip())
            for source, raw in self.raw_sources.items():
                source_parts = sorted((p for p in parts if p['path'] == source), key=lambda p: p['chunk_ordinal'])
                recovered = b''.join(zf.read('parts/' + p['part_id'] + '.bin') for p in source_parts)
                self.assertEqual(raw, recovered)
                self.assertEqual(source_parts[-1]['source_end'], len(raw))
            self.assertTrue(all(info.extract_version >= 45 for info in zf.infolist()))
            for out in outputs:
                raw = zf.read(out['path'])
                self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (out['bytes'], out['sha256']))
        self.assertEqual(file_proof(self.final), {k: receipt['archive'][k] for k in ('bytes', 'sha256')})

    def source_digest(self):
        db = repo.db_for(self.store)
        try:
            return repo.digest([[tuple(r) for r in db.execute('SELECT * FROM ' + table + ' ORDER BY 1,2')]
                                for table in ('repo_entries', 'repo_snapshots', 'repo_heads')])
        finally:
            db.close()

    def test_atomic_part_crash_before_and_after_rename_and_lost_checkpoint(self):
        for event in ('part_before_rename', 'part_after_rename'):
            with self.subTest(event=event):
                self.run_fault(event)
                proofs = self.payload_proofs()
                self.assertEqual(len(proofs), 0 if event == 'part_before_rename' else 1)
                if event == 'part_after_rename':
                    (self.stage / 'EXPORT_STATE.json').unlink()
                receipt = self.build(action='RESUME')
                self.assertEqual(receipt['part_count'], 78)
                for name, proof in proofs.items():
                    self.assertEqual(self.payload_proofs()[name], proof)
                shutil.rmtree(self.output)

    def test_crash_during_zip_rebuild_preserves_parts(self):
        self.run_fault('zip_chunk', count=5)
        self.assertFalse(self.final.exists())
        self.assertFalse(self.receipt.exists())
        self.assertTrue(self.final.with_name(self.final.name + '.partial').exists())
        proofs = self.payload_proofs()
        receipt = self.build(action='RESUME')
        self.assertEqual(receipt['reused_parts'], 78)
        self.assertEqual(receipt['written_parts'], 0)
        self.assertEqual(self.payload_proofs(), proofs)

    def test_disk_full_and_permission_at_real_part_and_zip_boundaries_then_resume(self):
        for event, behavior, reason in [('part_write', 'disk', 'DISK_FULL'), ('zip_write', 'disk', 'DISK_FULL'),
                                         ('part_write', 'permission', 'PERMISSION_DENIED')]:
            with self.subTest(event=event, behavior=behavior):
                self.run_fault(event, behavior)
                state = self.build(action='STATUS')
                self.assertEqual((state['state'], state['reason']), ('BLOCKED', reason))
                self.assertFalse(self.receipt.exists())
                self.assertEqual(self.build(action='RESUME')['state'], 'PUBLISHED')
                shutil.rmtree(self.output)

    def test_concurrent_writer_kernel_lock_and_duplicate_completed_build(self):
        process = subprocess.Popen(self.command('part_after_rename', 'hold'), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'HELD')
            other = subprocess.run(self.command() + ['--resume'], capture_output=True, timeout=30)
            self.assertEqual(other.returncode, 2)
            self.assertEqual(json.loads(other.stdout)['reason'], 'EXPORT_LOCKED')
            process.communicate('x', timeout=30)
            self.assertEqual(process.returncode, 0)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
        proof = file_proof(self.final)
        receipt = self.build()
        self.assertTrue(receipt['reconciled'])
        self.assertEqual(receipt['reused_parts'], 78)
        self.assertEqual(file_proof(self.final), proof)

    def test_corrupt_staged_parts_only_rewrite_affected_payloads(self):
        self.run_fault('zip_write')
        proofs = self.payload_proofs()
        names = list(proofs)
        root = self.stage / 'payload/parts'
        (root / names[0]).write_bytes(b'corrupted')
        (root / names[1]).unlink()
        receipt = self.build(action='RESUME')
        self.assertEqual((receipt['written_parts'], receipt['reused_parts']), (2, 76))
        after = self.payload_proofs()
        for name in names[2:]:
            self.assertEqual(after[name], proofs[name])

    def test_tampered_metadata_profile_pending_proof_and_checkpoint_refuse_publication(self):
        original = (self.directory / 'PARTS_INDEX.jsonl').read_bytes()
        with (self.directory / 'PARTS_INDEX.jsonl').open('ab') as stream:
            stream.write(b'{}\n')
        with self.assertRaisesRegex(ValueError, 'MANIFEST_UNVERIFIED'):
            self.build()
        (self.directory / 'PARTS_INDEX.jsonl').write_bytes(original)
        value = json.loads(self.profile.read_text())
        value['repositories']['sce']['exclusions'] = []
        self.profile.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'PROFILE_CHANGED'):
            self.build()
        self.profile.write_text(json.dumps(self.profile_value))
        proof = (self.directory / 'VALIDATION.json').read_bytes()
        (self.directory / 'VALIDATION.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'MANIFEST_UNVERIFIED'):
            self.build()
        (self.directory / 'VALIDATION.json').write_bytes(proof)
        db = repo.db_for(self.store)
        db.execute('UPDATE repo_snapshots SET cursor=0 WHERE id=?', (self.snapshot_id,))
        db.commit()
        db.close()
        with self.assertRaisesRegex(ValueError, 'MANIFEST_UNVERIFIED'):
            self.build()
        self.assertFalse(self.final.exists())

    def test_checkpoint_identity_mismatch_never_resets(self):
        self.run_fault('part_after_rename')
        path = self.stage / 'EXPORT_STATE.json'
        value = json.loads(path.read_text())
        value['export_id'] = '0' * 64
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_IDENTITY_MISMATCH'):
            self.build(action='NEW_RUN')

    def test_cancel_requires_new_run_retaining_prior_terminal_receipt(self):
        def cancel(event, **context):
            if event == 'part_after_rename':
                raise KeyboardInterrupt()
        with mock.patch.object(archive, 'boundary', cancel):
            with self.assertRaisesRegex(ValueError, 'CANCELLED'):
                self.build()
        prior = self.build(action='STATUS')
        self.assertEqual(prior['state'], 'CANCELLED')
        with self.assertRaisesRegex(ValueError, 'CANCELLED_REQUIRES_NEW_RUN'):
            self.build(action='RESUME')
        receipt = self.build(action='NEW_RUN')
        self.assertNotEqual(prior['run_id'], receipt['run_id'])
        self.assertEqual(json.loads((self.stage / ('RUN_' + prior['run_id'] + '.json')).read_text())['state'], 'CANCELLED')

    @unittest.skipIf(os.name == 'nt', 'POSIX SIGINT receipt; Windows KeyboardInterrupt tested separately')
    def test_real_ctrl_c_preserves_cancel_tombstone(self):
        process = subprocess.Popen(self.command('part_after_rename', 'hold'), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'HELD')
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=30)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(self.build(action='STATUS')['state'], 'CANCELLED')
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()

    def test_offline_relocated_links_hostile_metadata_all_source_and_part_pages(self):
        # Git paths unrepresentable on some OSes remain metadata, never output paths.
        hostile = 'CON/<script>alert(1)</script>\t\n"русский".py'
        db = repo.db_for(self.store)
        db.execute('UPDATE repo_entries SET path=? WHERE snapshot_id=? AND path=?', (hostile, self.snapshot_id, 'files/000.py'))
        db.execute('UPDATE repo_chunks SET path=? WHERE snapshot_id=? AND path=?', (hostile, self.snapshot_id, 'files/000.py'))
        for item in db.execute('SELECT id,payload FROM items'):
            payload = json.loads(item['payload'])
            if payload.get('path') == 'files/000.py':
                payload['path'] = hostile
                db.execute('UPDATE items SET payload=? WHERE id=?', (json.dumps(payload), item['id']))
        db.commit()
        db.close()
        shutil.rmtree(self.directory)
        manifest.write_manifest(self.store, 'sce', self.source, self.snapshot_id, self.directory)
        result = self.build()
        self.final = Path(result['archive_path'])
        relocated = self.work / 'relocated'
        with zipfile.ZipFile(self.final) as zf:
            zf.extractall(relocated)
        documents = {}
        for path in relocated.rglob('*.html'):
            raw = path.read_text(encoding='utf-8')
            parser = Links()
            parser.feed(raw)
            self.assertFalse(parser.scripts)
            self.assertNotIn('<script>alert(1)</script>', raw)
            documents[path.resolve()] = parser
        for path, document in documents.items():
            for href in document.links:
                split = urlsplit(href)
                self.assertFalse(split.scheme or split.netloc)
                target = (path.parent / unquote(split.path)).resolve()
                self.assertTrue(target.is_relative_to(relocated.resolve()))
                self.assertTrue(target.is_file(), href)
                if split.fragment:
                    self.assertIn(split.fragment, documents[target].ids)
        self.assertGreater(len(documents), 3)

    def test_orphan_or_non_indexed_raw_chunks_never_export(self):
        db = repo.db_for(self.store)
        row = list(db.execute('SELECT * FROM repo_chunks LIMIT 1').fetchone())
        row[1] = '.env'
        db.execute('INSERT INTO repo_chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', row)
        db.commit()
        db.close()
        with self.assertRaisesRegex(ValueError, 'PAYLOAD_HASH_MISMATCH|MANIFEST_UNVERIFIED'):
            self.build()
        self.assertFalse(self.final.exists())

    def test_rename_before_receipt_reconciles_without_replacing_archive(self):
        self.run_fault('publish_after_rename')
        self.assertTrue(self.final.exists())
        self.assertFalse(self.receipt.exists())
        before = (file_proof(self.final), self.final.stat().st_mtime_ns)
        receipt = self.build(action='RESUME')
        self.assertTrue(receipt['reconciled'])
        self.assertEqual((file_proof(self.final), self.final.stat().st_mtime_ns), before)
        self.assertEqual(json.loads(self.receipt.read_text())['archive'], receipt['archive'])

    def test_damaged_or_extra_member_final_blocks_without_overwrite(self):
        self.build()
        with zipfile.ZipFile(self.final, 'a') as zf:
            zf.writestr('unapproved.bin', b'junk')
        before = file_proof(self.final)
        with self.assertRaisesRegex(ValueError, 'OUTPUT_CONFLICT'):
            self.build(action='RESUME')
        self.assertEqual(file_proof(self.final), before)
        self.final.write_bytes(b'damaged')
        with self.assertRaisesRegex(ValueError, 'OUTPUT_CONFLICT'):
            self.build(action='RESUME')
        self.assertEqual(self.final.read_bytes(), b'damaged')

    def test_declared_disk_and_time_budgets_and_small_copy_buffer(self):
        with self.assertRaisesRegex(ValueError, 'RESOURCE_BUDGET_EXCEEDED'):
            self.build(disk_bytes=1)
        self.assertEqual(self.build(action='STATUS')['state'], 'BLOCKED')
        with self.assertRaisesRegex(ValueError, 'RESOURCE_BUDGET_EXCEEDED'):
            self.build(action='RESUME', seconds=1e-12)
        receipt = self.build(action='RESUME', buffer_bytes=1024)
        self.assertEqual(receipt['state'], 'PUBLISHED')

    def test_status_read_only_and_no_automatic_resume(self):
        def files():
            # SQLite read-only WAL readers may create transient lock sidecars.
            return sorted(p.relative_to(self.work).as_posix() for p in self.work.rglob('*')
                          if p.name not in {'content.sqlite3-wal', 'content.sqlite3-shm'})
        before, ledger = files(), self.source_digest()
        self.assertEqual(self.build(action='STATUS')['state'], 'NEW')
        self.assertEqual(before, files())
        self.assertEqual(ledger, self.source_digest())
        self.assertFalse(self.output.exists())
        self.run_fault('part_after_rename')
        with self.assertRaisesRegex(ValueError, 'EXPLICIT_RESUME_REQUIRED'):
            self.build()

    def test_symlink_and_inside_source_store_or_manifest_paths_refused(self):
        for path in (self.store / 'exports', self.directory / 'exports', self.checkout / 'exports'):
            with self.assertRaisesRegex(ValueError, 'OUTPUT_MUST_BE_OUTSIDE'):
                archive.build(self.profile, 'sce', self.directory, path)
        if os.name == 'posix':
            target = self.work / 'actual'
            target.mkdir()
            symbolic = self.work / 'link'
            symbolic.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'ARTIFACT_LINK_FORBIDDEN'):
                archive.build(self.profile, 'sce', self.directory, symbolic)

    def test_legacy_scan_and_manifest_cli_idempotent_after_archive(self):
        status = repo_scan.scan(self.profile, 'sce', snapshot_id=self.snapshot_id)
        self.assertEqual(status['counts'], {'EXCLUDED': 4, 'INDEXED': 46})
        command = [sys.executable, '-I', '-X', 'utf8', str(LAB / 'repo_manifest.py'), '--profile', str(self.profile),
                   '--repository', 'sce', '--snapshot', self.snapshot_id, '--output', str(self.directory)]
        result = subprocess.run(command, capture_output=True, check=True, timeout=30)
        self.assertEqual(json.loads(result.stdout)['batch_id'], self.batch['batch_id'])
        self.build()
        self.assertEqual(repo.get_snapshot(self.store, 'code', self.snapshot_id, offset=40)['next_offset'], None)

    def test_profile_revocation_at_publish_blocks_before_final_rename(self):
        def revoke(event, **context):
            if event == 'publish_before_rename':
                value = json.loads(self.profile.read_text())
                value['repositories'].clear()
                self.profile.write_text(json.dumps(value))
        with mock.patch.object(archive, 'boundary', revoke):
            with self.assertRaisesRegex(ValueError, 'REPO_OUTSIDE_OPERATOR_SCOPE'):
                self.build()
        self.assertFalse(self.final.exists())
        self.assertFalse(self.receipt.exists())

    def test_manifest_rejects_corrupt_git_oid_ranges_revision_and_missing_empty_part(self):
        for mutation in ("UPDATE repo_entries SET oid='" + '0' * 40 + "' WHERE state='INDEXED'",
                         'UPDATE repo_chunks SET byte_end=byte_end+1',
                         "UPDATE repo_chunks SET revision='" + '0' * 64 + "'",
                         "DELETE FROM repo_chunks WHERE path='empty.txt'"):
            with self.subTest(mutation=mutation):
                db = repo.db_for(self.store)
                try:
                    db.execute('BEGIN')
                    db.execute(mutation)
                    snap = repo.load_snapshot(db, 'code', self.snapshot_id)
                    with self.assertRaisesRegex(ValueError, 'PAYLOAD_HASH_MISMATCH|MANIFEST_UNVERIFIED'):
                        manifest.validate_snapshot(db, snap)
                    db.rollback()
                finally:
                    db.close()

    def test_pinned_historical_manifest_does_not_read_git_or_working_tree(self):
        with mock.patch.object(repo, 'git', side_effect=AssertionError('export must not call Git')):
            receipt = self.build()
        self.assertTrue(receipt['captured_export_complete'])

    def test_installed_cli_modules_support_foreground_scan_manifest_archive(self):
        installer = (LAB.parent / 'agent-bridge/Install.ps1').read_text()
        names = re.findall(r"'([^']+)'", re.search(r'foreach\(\$occFile in @\((.*?)\)\)', installer).group(1))
        installed = self.work / 'installed/content-lab'
        installed.mkdir(parents=True)
        for name in names:
            shutil.copyfile(LAB / name, installed / name)
        scan_cmd = [sys.executable, '-I', '-X', 'utf8', str(installed / 'repo_scan.py'), '--profile', str(self.profile),
                    '--repository', 'sce', '--resume-snapshot', self.snapshot_id, '--manifest-output', str(self.directory)]
        scan_result = subprocess.run(scan_cmd, capture_output=True, check=True, timeout=30)
        self.assertEqual(json.loads(scan_result.stdout)['batch_id'], self.batch['batch_id'])
        command = self.command()
        command[4] = str(installed / 'repo_archive.py')
        result = subprocess.run(command, capture_output=True, check=True, timeout=30)
        self.assertEqual(json.loads(result.stdout)['state'], 'PUBLISHED')


if __name__ == '__main__':
    unittest.main()
