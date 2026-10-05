import tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from browser_archive import BrowserArchiveAssembler

class ArchiveTests(unittest.TestCase):
    def test_stream_reassembles_order_and_updates(self):
        with tempfile.TemporaryDirectory() as td:
            a=BrowserArchiveAssembler(td,'case')
            a.add_chunk({'kind':'records','records':[
                {'id':'m2','role':'assistant','kind':'chat','text':'world','bytes':5,'hash':'h2','part_index':0,'part_count':1},
                {'id':'m1','role':'user','kind':'chat','text':'hel','bytes':5,'hash':'h1','part_index':0,'part_count':2}]})
            a.add_chunk({'kind':'records','records':[
                {'id':'m1','role':'user','kind':'chat','text':'lo','bytes':5,'hash':'h1','part_index':1,'part_count':2}]})
            a.add_chunk({'kind':'records','records':[
                {'id':'m2','role':'assistant','kind':'chat','text':'world!','bytes':6,'hash':'h3','part_index':0,'part_count':1}]})
            out=a.finalize({'state':'ARCHIVE_CAPTURED','source':'https://x/','status':'BEST_EFFORT',
                'coverage':{'complete':True},'warnings':[],'artifacts':None,'frame_capture':{'frames':1},
                'order':['m1','m2']})
            text=Path(out['txt_path']).read_text()
            self.assertIn('[USER 1]\nhello',text)
            self.assertIn('[ASSISTANT 2]\nworld!',text)
            self.assertEqual(out['gaps'],[])

    def test_missing_part_is_explicit_gap(self):
        with tempfile.TemporaryDirectory() as td:
            a=BrowserArchiveAssembler(td,'gap')
            a.add_chunk({'kind':'records','records':[
                {'id':'m1','role':'user','kind':'chat','text':'a','bytes':2,'hash':'h','part_index':0,'part_count':2}]})
            out=a.finalize({'state':'ARCHIVE_CAPTURED','source':'x','status':'PARTIAL',
                'coverage':{'complete':False},'warnings':['gap'],'artifacts':None,'frame_capture':{},'order':['m1']})
            self.assertEqual(out['gaps'][0]['reason'],'MISSING_PART')
            self.assertIn('MISSING STREAM RECORD',Path(out['txt_path']).read_text())

if __name__=='__main__':
    unittest.main()
