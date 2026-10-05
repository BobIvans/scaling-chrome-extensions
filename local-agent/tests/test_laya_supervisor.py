import json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from laya_supervisor import LayaSupervisor,LayaSupervisorError

class Resp:
    def read(self,n=-1):return json.dumps({'status':'ok','loaded':['multilingual'],'revisions':{'multilingual':'abc'},'device':'cpu'}).encode()
class Tests(unittest.TestCase):
    def cfg(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:path=f.name
        return {'enabled':True,'python_path':path,'host':'127.0.0.1','port':8765,'device':'cpu','models':['multilingual'],
                'default_model':'multilingual','threads':4,'max_loaded':1,'preload':True,'api_key_env':'',
                'min_confidence':.72,'startup_timeout_seconds':30,'idle_unload_seconds':0}
    def test_health_reuses_exact_loopback_service(self):
        s=LayaSupervisor(self.cfg(),opener=lambda req,timeout:Resp())
        out=s.start();self.assertEqual(out['state'],'READY');self.assertTrue(out['reused']);self.assertEqual(out['health']['device'],'cpu')
    def test_non_loopback_rejected(self):
        c=self.cfg();c['host']='0.0.0.0'
        with self.assertRaisesRegex(LayaSupervisorError,'LOOPBACK'):LayaSupervisor(c)
if __name__=='__main__':unittest.main()
