import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile
from context_store import Store
from openai_adapter import make_payload, send_file
from run_recipe import run
from verify_pack import verify

class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.s=Store(self.root/'library',reserve_bytes=0)
    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()
    def archive(self, files):
        path=self.root/'repo.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
                for name,data in files:z.writestr(name,data)
        return path
    def test_large_archive_more_than_300_entries(self):
        files=[(f'repo/level/{i}/module.mjs',('export const x="данные😀";\r\n'*350).encode()) for i in range(333)]
        path=self.archive(files)
        self.assertGreater(path.stat().st_size,4*1024*1024)
        sid=self.s.import_source(path)
        total,rows=self.s.entries(sid,limit=500)
        self.assertEqual(total,333)
        self.assertTrue(all(x['text_state']=='TEXT_COMPLETE' for x in rows))
        index=self.s.export(sid,self.root/'export',part_bytes=100003)
        self.assertEqual(index['entries'],333)
        for record in (self.root/'export/files.jsonl').read_text().splitlines():
            r=json.loads(record)
            self.assertEqual((self.root/'export'/r['original_object']).read_bytes(),dict(files)[r['path']])
        for p in index['parts']:
            data=(self.root/'export'/p['path']).read_bytes()
            data.decode('utf-8')
            self.assertLessEqual(len(data),100003)
            self.assertEqual(hashlib.sha256(data).hexdigest(),p['sha256'])
    def test_paths_duplicates_binary_and_traversal(self):
        files=[('a/x.py',b'one'),('b/x.py',b'two'),('a/x.py',b'three'),('../escape.py',b'four'),('b.bin',b'\0\xff'),('empty/',b'')]
        sid=self.s.import_source(self.archive(files))
        total,rows=self.s.entries(sid)
        self.assertEqual(total,6)
        self.assertEqual([r['path'] for r in rows],[n for n,_ in files])
        self.assertFalse((self.root/'escape.py').exists())
        self.assertEqual(rows[4]['text_state'],'RAW_ONLY')
        self.assertEqual(self.s.blob_path(rows[4]['sha256']).read_bytes(),b'\0\xff')
        self.assertEqual(rows[5]['kind'],'directory')
    def test_bom_crlf_utf16_and_invalid_encoding(self):
        original=b'\xef\xbb\xbfhello\r\n'
        sid=self.s.import_source(self.archive([('x.unknown',original),('wide.txt','Привет\r\n'.encode('utf-16')),('invalid.txt',b'abc\xff')]))
        _,rows=self.s.entries(sid)
        text,_=self.s.text_page(rows[0]['id'])
        self.assertEqual(text.encode('utf-8'),original)
        self.assertEqual(self.s.text_page(rows[1]['id'])[0],'Привет\r\n')
        self.assertEqual(rows[2]['text_state'],'RAW_ONLY')
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM chunks WHERE entry=?',(rows[2]['id'],)).fetchone()[0],0)
    def test_pause_resume_immutable_zip(self):
        path=self.archive([(f'{i}.txt',b'hello') for i in range(40)])
        stop=[False]
        sid=self.s.import_source(path,progress=lambda x:stop.__setitem__(0,True),cancel=lambda:stop[0])
        self.assertEqual(self.s.snapshots()[0]['state'],'PAUSED')
        self.assertEqual(self.s.entries(sid)[0],1)
        path.write_bytes(b'changed original path')
        self.s.import_source('.',resume=sid)
        self.assertEqual(self.s.entries(sid)[0],40)
        self.assertEqual(self.s.snapshots()[0]['state'],'COMPLETE')
    def test_restart_search_and_annotations(self):
        sid=self.s.import_source(self.archive([('src/main.py','уникальный контекст'.encode())]))
        entry=self.s.entries(sid)[1][0]['id']
        self.s.annotate(entry,'repo,flashloan','Проверить')
        self.s.close()
        self.s=Store(self.root/'library',reserve_bytes=0)
        self.assertEqual(self.s.entries(sid,query='уникальный')[0],1)
        self.assertEqual(self.s.entries(sid,query='main.py')[0],1)
        self.assertEqual(self.s.db.execute('SELECT note FROM annotations').fetchone()[0],'Проверить')
    def test_blob_dedup_keeps_path_identities(self):
        sid=self.s.import_source(self.archive([('a.txt',b'same'),('b.txt',b'same')]))
        _,rows=self.s.entries(sid)
        self.assertEqual(rows[0]['sha256'],rows[1]['sha256'])
        self.assertNotEqual(rows[0]['id'],rows[1]['id'])
    def test_library_inside_source_rejected(self):
        with self.assertRaises(ValueError):self.s.import_source(self.root)
    def test_folder_symlink_not_followed(self):
        folder=self.root/'repo'
        folder.mkdir()
        (folder/'x.py').write_text('abc')
        try:(folder/'loop').symlink_to(folder,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
        sid=self.s.import_source(folder)
        _,rows=self.s.entries(sid)
        self.assertEqual(len(rows),2)
        self.assertIn('symlink',[r['kind'] for r in rows])
    def test_chatgpt_all_branches_roles_idempotent(self):
        data=[{'id':'c1','title':'Идеи','mapping':{'a':{'parent':None,'message':{'id':'a','author':{'role':'user'},'content':{'parts':['МОЯ ИДЕЯ']}}},'b':{'parent':'a','message':{'id':'b','author':{'role':'assistant'},'content':{'parts':['ПЛАН']}}},'c':{'parent':'a','message':{'id':'c','author':{'role':'assistant'},'content':{'parts':['ДРУГАЯ ВЕТКА',{'image':'not-fetched'}]}}}}}]
        sid=self.s.import_source(self.archive([('conversations.json',json.dumps(data).encode())]))
        entry=self.s.entries(sid)[1][0]['id']
        self.assertEqual(self.s.derive_chatgpt(entry),3)
        self.s.derive_chatgpt(entry)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM derived_messages').fetchone()[0],3)
        self.s.export(sid,self.root/'out')
        self.assertIn('МОЯ ИДЕЯ',(self.root/'out/USER_MESSAGES.txt').read_text())
        self.assertIn('ДРУГАЯ ВЕТКА',(self.root/'out/ASSISTANT_MESSAGES.txt').read_text())
    def test_corrupt_blob_export_refused(self):
        sid=self.s.import_source(self.archive([('x.py',b'abc')]))
        row=self.s.entries(sid)[1][0]
        self.s.blob_path(row['sha256']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):self.s.export(sid,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
    def test_cancel_export_no_false_complete(self):
        sid=self.s.import_source(self.archive([('x.py',b'abc')]))
        with self.assertRaises(Exception):self.s.export(sid,self.root/'out',cancel=lambda:True)
        self.assertFalse((self.root/'out').exists())
    def test_recipe_rejects_shell_steps(self):
        with self.assertRaises(ValueError):run({'schema':'sce.offline-recipe.v1','steps':['shell']},self.root/'library','x','y')
    def test_independent_verifier_detects_damage_and_unknown_goals(self):
        sid=self.s.import_source(self.archive([('x.py',b'abc'),('binary',b'\xff\0')]))
        self.s.export(sid,self.root/'export')
        result=verify(self.root/'export')
        values={x['criterion']:x['truth'] for x in result['checks']}
        self.assertEqual(values['zip_inventory_paths_occurrences'],'TRUE')
        self.assertEqual(values['all_entry_originals_integrity'],'TRUE')
        self.assertEqual(values['all_entries_have_text_derivative'],'FALSE')
        self.assertEqual(values['flashloan_ready'],'NOT_RUN')
        row=self.s.entries(sid)[1][0]
        (self.root/'export/originals'/row['sha256']).write_bytes(b'changed')
        values={x['criterion']:x['truth'] for x in verify(self.root/'export')['checks']}
        self.assertEqual(values['all_entry_originals_integrity'],'FALSE')
    def test_api_payload_and_fake_response(self):
        payload=make_payload('operator-model','review','code',50)
        self.assertFalse(payload['store'])
        self.assertEqual(payload['truncation'],'disabled')
        self.assertNotIn('tools',payload)
        source=self.root/'context.txt'
        source.write_text('source')
        class Fake:
            def open(self,req,timeout):
                self.req=req
                return io.BytesIO(json.dumps({'id':'test','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'answer'}]}]}).encode())
        fake=Fake()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'synthetic-test-key'}):
            output,status=send_file(source,'goal','operator-model',self.root/'answers',opener=fake)
        self.assertEqual(status,'completed')
        self.assertEqual((output/'answer.txt').read_text(),'answer')
        self.assertNotIn('synthetic-test-key',(output/'receipt.json').read_text())

if __name__=='__main__':unittest.main(verbosity=2)
