import json, os, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from github_merge_watch import normalize_repo, MergeWatcher
from folder_watch import FolderWatcher
class Headers(dict):
    def get(self,key,default=None):return super().get(key,default)
class Response:
    def __init__(self,value,etag='W/"x"'):self.value=value;self.headers=Headers(ETag=etag)
    def read(self,n=-1):return json.dumps(self.value).encode()
class MiniTests(unittest.TestCase):
    def test_repo_normalize(self):self.assertEqual(normalize_repo('https://github.com/BobIvans/scaling-chrome-extensions.git'),'BobIvans/scaling-chrome-extensions')
    def test_merge_first_poll_baselines_then_emits_new(self):
        with tempfile.TemporaryDirectory() as td:
            rows=[{'number':1,'title':'x','merged':True,'merged_at':'2026-10-05T00:00:00Z','merge_commit_sha':'a'*40,'head':{'sha':'b'*40},'base':{'ref':'main'},'html_url':'x'}]
            w=MergeWatcher('a/b',Path(td)/'s.json',opener=lambda req,timeout:Response(rows));self.assertEqual(w.poll(),[])
            rows2=rows+[{'number':2,'title':'y','merged':True,'merged_at':'2026-10-05T01:00:00Z','merge_commit_sha':'c'*40,'head':{'sha':'d'*40},'base':{'ref':'main'},'html_url':'y'}]
            w.opener=lambda req,timeout:Response(rows2,'W/"y"');self.assertEqual([x['number'] for x in w.poll()],[2])
    def test_folder_watch_detects_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'src';root.mkdir();p=root/'a.txt';p.write_text('one');w=FolderWatcher([root],Path(td)/'state.json');self.assertEqual(len(w.scan()),1);self.assertEqual(w.scan(),[]);p.write_text('two');os.utime(p,None);self.assertEqual(len(w.scan()),1)
if __name__=='__main__':unittest.main()
