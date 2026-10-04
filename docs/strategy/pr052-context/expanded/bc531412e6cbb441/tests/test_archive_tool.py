import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import archive_tool as a


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.src = self.base / 'source'
        self.src.mkdir()
        self.out = self.base / 'archive'

    def tearDown(self):
        self.tmp.cleanup()

    def collect(self, ref=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return a.collect(self.src, self.out, ref)

    def test_more_than_1000_files_no_document_cap(self):
        for n in range(1007):
            (self.src / f'{n}.txt').write_text(f'file {n}\n', encoding='utf-8')
        receipt = self.collect()
        self.assertEqual(receipt['counts']['stored_files'], 1007)
        self.assertEqual(a.verify(self.out)['state'], 'VERIFIED')

    def test_large_single_line_and_unicode_reconstruction(self):
        (self.src / 'русский 🐈.md').write_text('😀Яé' * 40000 + '\nlast line\r\n', encoding='utf-8')
        self.collect()
        dest = self.base / 'text'
        result = a.export_text(self.out, dest, 19)
        self.assertGreater(result['parts'], 20)
        self.assertEqual(a.verify_text(self.out, dest)['state'], 'VERIFIED')

    def test_empty_binary_utf16_and_dotfile(self):
        (self.src / 'empty').write_bytes(b'')
        (self.src / 'binary.bin').write_bytes(bytes(range(256)))
        (self.src / 'utf16.txt').write_bytes('Привет'.encode('utf-16'))
        (self.src / '.hidden').write_text('included')
        self.collect()
        dest = self.base / 'text'
        result = a.export_text(self.out, dest, 100)
        self.assertEqual(result['non_utf8_or_binary_files'], 2)
        self.assertEqual(result['text_files'], 2)
        self.assertEqual(a.verify_text(self.out, dest)['state'], 'VERIFIED')

    def test_no_extension_filter(self):
        (self.src / 'file.rs').write_text('fn main() {}')
        (self.src / 'LICENSE').write_text('license')
        self.assertEqual(self.collect()['counts']['stored_files'], 2)

    def test_git_pinned_snapshot_not_working_edits(self):
        subprocess.run(['git', 'init', '-q', str(self.src)], check=True)
        subprocess.run(['git', '-C', str(self.src), 'config', 'user.email', 'test@example.invalid'], check=True)
        subprocess.run(['git', '-C', str(self.src), 'config', 'user.name', 'Test'], check=True)
        p = self.src / 'nested'; p.mkdir()
        (p / 'hello.txt').write_bytes(b'committed\r\n')
        subprocess.run(['git', '-C', str(self.src), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.src), 'commit', '-qm', 'test'], check=True)
        (p / 'hello.txt').write_text('uncommitted')
        receipt = self.collect('HEAD')
        rows = [x for x in a.manifest_rows(self.out) if x['status'] == 'STORED']
        self.assertEqual(a.object_path(self.out, rows[0]['sha256']).read_bytes(), b'committed\r\n')
        self.assertEqual(receipt['scope'], 'PINNED_GIT_TREE')
        self.assertEqual(a.verify(self.out)['state'], 'VERIFIED')

    def test_symlink_target_never_read(self):
        target = self.base / 'outside.txt'; target.write_text('SECRET TARGET')
        try:
            os.symlink(target, self.src / 'link')
        except OSError:
            self.skipTest('symlinks unavailable')
        result = self.collect()
        self.assertEqual(result['counts']['stored_files'], 0)
        self.assertEqual(result['counts']['metadata_only'], 1)

    def test_raw_secret_named_file_private_not_omitted(self):
        (self.src / '.env').write_text('TEST_ONLY=example-not-a-real-key')
        result = self.collect()
        self.assertEqual(result['counts']['possible_secret_names'], 1)
        self.assertEqual(result['share_state'], 'PRIVATE_UNREVIEWED')
        self.assertEqual(result['counts']['stored_files'], 1)

    def test_corrupted_object_detected(self):
        (self.src / 'a.txt').write_text('abc')
        self.collect()
        row = next(a.manifest_rows(self.out))
        a.object_path(self.out, row['sha256']).write_text('bad')
        self.assertEqual(a.verify(self.out)['state'], 'FAILED')

    def test_corrupted_manifest_detected(self):
        (self.src / 'a.txt').write_text('abc')
        self.collect()
        (self.out / 'manifest.jsonl').write_text('')
        self.assertEqual(a.verify(self.out)['state'], 'FAILED')

    def test_export_tamper_detected(self):
        (self.src / 'a.txt').write_text('abc')
        self.collect(); dest = self.base / 'text'
        a.export_text(self.out, dest)
        (dest / 'ALL_TEXT.txt').write_text('lost')
        self.assertEqual(a.verify_text(self.out, dest)['state'], 'FAILED')

    def test_output_inside_source_refused(self):
        with self.assertRaises(ValueError):
            a.collect(self.src, self.src / 'out')

    def test_rescan_keeps_old_cas_revisions(self):
        p = self.src / 'a.txt'; p.write_text('old')
        self.collect()
        old = next(a.manifest_rows(self.out))['sha256']
        p.write_text('new'); self.collect()
        self.assertTrue(a.object_path(self.out, old).exists())
        self.assertEqual(a.verify(self.out)['state'], 'VERIFIED')

    def test_no_code_execution_in_static_catalog(self):
        marker = self.base / 'MUST_NOT_EXIST'
        code = f"from pathlib import Path\nPath({str(marker)!r}).touch()\nimport argparse\np=argparse.ArgumentParser()\np.add_argument('--paper')\ndef main():\n    try:\n        pass\n    except:\n        pass\n"
        (self.src / 'script.py').write_text(code)
        self.collect()
        result = a.catalog(self.out, self.base / 'catalog')
        self.assertFalse(marker.exists())
        self.assertEqual(result['symbols'], 1)
        self.assertEqual(result['command_candidates'], 1)
        self.assertGreaterEqual(result['signals'], 2)

    def test_all_chat_branches_preserved(self):
        value = [{'id':'c','title':'conversation','mapping':{
            'root': {'parent':None,'children':['a','b'],'message':None},
            'a': {'parent':'root','children':[],'message':{'author':{'role':'user'},'content':{'parts':['one']}}},
            'b': {'parent':'root','children':[],'message':{'author':{'role':'assistant'},'content':{'parts':['alternate']}}}}}]
        src = self.base / 'chats.json'; src.write_text(json.dumps(value))
        result = a.chats(src, self.base / 'import')
        self.assertEqual(result['nodes'], 3)
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), result['original_sha256'])

    def test_unsupported_chat_shape_keeps_original(self):
        src = self.base / 'chats.json'; src.write_text('[{"messages":[]}]')
        with self.assertRaises(ValueError):
            a.chats(src, self.base / 'import')
        self.assertTrue((self.base / 'import' / 'original.json').exists())
        self.assertNotEqual(json.loads((self.base/'import'/'import_status.json').read_text())['state'], 'COMPLETE')

    def test_writer_lock_blocks_second_writer(self):
        self.out.mkdir(); (self.out / '.writer.lock').write_text('test')
        with self.assertRaises(FileExistsError):
            self.collect()

    def test_archive_path_escape_blocked(self):
        self.out.mkdir()
        for bad in ('../secret', '/etc/passwd', 'C:/keys', '..\\keys'):
            with self.assertRaises(ValueError):
                a.safe_child(self.out, bad)

    def test_empty_folder(self):
        self.assertEqual(self.collect()['counts']['entries'], 0)
        self.assertEqual(a.verify(self.out)['state'], 'VERIFIED')

    def test_lfs_pointer_explicit(self):
        (self.src/'large.bin').write_text('version https://git-lfs.github.com/spec/v1\noid sha256:'+'a'*64+'\nsize 99999999\n')
        result = self.collect()
        self.assertEqual(result['counts']['lfs_pointers'], 1)
        self.assertFalse(result['lfs_payloads_resolved'])


    def test_file_larger_than_eight_mib(self):
        size = 8*1024*1024 + 123
        with (self.src/'large.txt').open('wb') as f:
            for _ in range(8): f.write(b'x' * (1024*1024))
            f.write(b'y' * 123)
        result = self.collect()
        self.assertEqual(result['counts']['bytes'], size)
        dest = self.base/'text'
        a.export_text(self.out,dest)
        self.assertEqual(a.verify_text(self.out,dest)['state'],'VERIFIED')

    def test_special_posix_path_bytes_preserved(self):
        if os.name != 'posix': self.skipTest('POSIX path-byte fixture')
        name = b'odd\tline\nname-\xff.txt'
        raw = os.fsencode(self.src)+b'/'+name
        with open(raw,'wb') as f: f.write(b'raw path test')
        self.collect()
        row = next(a.manifest_rows(self.out))
        import base64
        self.assertEqual(base64.b64decode(row['path_bytes_b64']),name)
        self.assertEqual(a.verify(self.out)['state'],'VERIFIED')

    def test_unfinished_new_scan_prevents_success(self):
        (self.src/'x').write_text('x'); self.collect()
        (self.out/'in_progress.json').write_text('{"state":"INTERRUPTED"}')
        self.assertEqual(a.verify(self.out)['state'],'FAILED')

    def test_invalid_git_ref_rejected(self):
        with self.assertRaises(ValueError): self.collect('HEAD;echo injection')

    def test_duplicate_chat_json_not_silently_accepted(self):
        src=self.base/'chats.json'
        src.write_text('[{"mapping":{"a":{},"a":{}}}]')
        with self.assertRaises(ValueError): a.chats(src,self.base/'import')
        self.assertTrue((self.base/'import'/'original.json').exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)
