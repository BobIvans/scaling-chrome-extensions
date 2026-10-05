import tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from browser_watch import BrowserWatch

class Bridge:
    def list_tabs(self):return [{'id':1,'url':'https://grok.com/c/1','title':'Grok','active':True},{'id':2,'url':'chrome://settings','title':'x'}]
    def capture_archive(self,tab_id,on_chunk,max_bytes,max_steps,max_ms):
        on_chunk({'kind':'records','records':[{'id':'m1','role':'user','kind':'chat','text':'hello','bytes':5,'hash':'h','part_index':0,'part_count':1}]})
        return {'state':'ARCHIVE_CAPTURED','source':'https://grok.com/c/1','status':'BEST_EFFORT','coverage':{'complete':True},
                'warnings':[],'artifacts':None,'frame_capture':{},'order':['m1']}
class Core:
    def __init__(self):self.calls=0
    def capture_file(self,path,key):self.calls+=1;return {'namespace':'n','source_key':key,'revision':'a'*64,'sha256':'b'*64,'bytes':Path(path).stat().st_size}
    def annotate_capture(self,*a,**k):return {}

class WatchTests(unittest.TestCase):
    def test_watch_captures_then_deduplicates(self):
        with tempfile.TemporaryDirectory() as td:
            core=Core();w=BrowserWatch(Bridge(),core,{'enabled':True,'include_hosts':['grok.com'],'max_tabs_per_cycle':2},Path(td)/'state.json',td)
            first=w.poll_once();self.assertEqual(first['results'][0]['state'],'CAPTURED');self.assertEqual(core.calls,3)
            second=w.poll_once();self.assertEqual(second['results'][0]['state'],'UNCHANGED');self.assertEqual(core.calls,3)
if __name__=='__main__':unittest.main()
