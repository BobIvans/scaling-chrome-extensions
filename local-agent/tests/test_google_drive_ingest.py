import json, os, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from google_drive_ingest import GoogleDriveIngestor

class Headers(dict):
    def get(self,key,default=None):return super().get(key,default)
class Response:
    def __init__(self,raw,headers=None):self.raw=raw if isinstance(raw,bytes) else json.dumps(raw).encode();self.headers=Headers(headers or {})
    def read(self,n=-1):return self.raw[:n] if n>=0 else self.raw

class DriveTests(unittest.TestCase):
    def test_refresh_list_export_and_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            calls=[]
            def opener(req,timeout):
                calls.append(req.full_url)
                if req.full_url.endswith('/token'):return Response({'access_token':'ACCESS'})
                if '/drive/v3/files?' in req.full_url:
                    return Response({'files':[{'id':'doc1234567890','name':'Plan','mimeType':'application/vnd.google-apps.document','modifiedTime':'2026-10-05T00:00:00Z','parents':['folder'],'capabilities':{'canDownload':True}}]})
                if '/export?' in req.full_url:return Response(b'hello drive')
                raise AssertionError(req.full_url)
            cfg={'enabled':True,'download_root':str(Path(td)/'out'),'folder_ids':['folder'],'refresh_token_env':'RT','client_id_env':'CID','max_files_per_poll':50,'max_bytes_per_file':100000}
            env={'RT':'refresh','CID':'client'}
            w=GoogleDriveIngestor(cfg,Path(td)/'state.json',opener=opener,environ=env)
            self.assertEqual(w.poll(),[])
            state=json.loads((Path(td)/'state.json').read_text());state['files']={};(Path(td)/'state.json').write_text(json.dumps(state))
            rows=w.poll(emit_existing=True)
            self.assertEqual(rows[0]['state'],'DOWNLOADED');self.assertEqual(Path(rows[0]['path']).read_text(),'hello drive')
            self.assertTrue(any('/export?' in x for x in calls))
    def test_access_token_and_blob_download(self):
        with tempfile.TemporaryDirectory() as td:
            def opener(req,timeout):
                if '/drive/v3/files?' in req.full_url:
                    return Response({'files':[{'id':'blob123456789','name':'data.txt','mimeType':'text/plain','modifiedTime':'2026-10-05T01:00:00Z','size':'3','capabilities':{'canDownload':True}}]})
                if 'alt=media' in req.full_url:return Response(b'abc')
                raise AssertionError(req.full_url)
            cfg={'enabled':True,'download_root':str(Path(td)/'out'),'folder_ids':[],'access_token_env':'AT','max_files_per_poll':50,'max_bytes_per_file':100000}
            w=GoogleDriveIngestor(cfg,Path(td)/'state.json',opener=opener,environ={'AT':'token'})
            rows=w.poll(emit_existing=True);self.assertEqual(rows[0]['sha256'],'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
if __name__=='__main__':unittest.main()
