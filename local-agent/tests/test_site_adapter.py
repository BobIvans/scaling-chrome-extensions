import hashlib,json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from site_adapter import SiteAdapterRuntime,_digest,ADAPTER_VERSION,SiteAdapterError

class Core:
    def __init__(self):self.effects={}
    def effect_begin(self,op,binding):
        if op not in self.effects:self.effects[op]={'revision':1,'value':{'binding':binding,'state':'INTENT_RECORDED','evidence':[]}}
        return self.effects[op]
    def effect_inspect(self,op):return self.effects[op]
    def effect_transition(self,op,state,expected,evidence):
        row=self.effects[op];self.assertEqual if False else None
        if row['revision']!=expected:raise RuntimeError('rev')
        row={'revision':expected+1,'value':{**row['value'],'state':state,'evidence':evidence}};self.effects[op]=row;return row
class Bridge:
    def __init__(self,code):self.code=code;self.sent=0;self.observed=False
    def site_bind(self,p,tab_id=None):return {'tabId':7,'adapter_version':ADAPTER_VERSION,'code_digest':self.code,'result':{'state':'BOUND','adapter_version':ADAPTER_VERSION,'contract_digest':p['contract_digest'],'identity':{'origin':p['origin'],'account':'a','workspace':'w','conversation':'c'},'composer_fingerprint':'c','send_fingerprint':'s'}}
    def site_prepare(self,*args):return {'code_digest':self.code,'result':{'state':'DRAFT_PREPARED'}}
    def site_send(self,*args):self.sent+=1;self.observed=True;return {'result':{'state':'SEND_INVOKED'}}
    def site_reconcile(self,*args):return {'result':{'state':'MESSAGE_OBSERVED' if self.observed else 'EFFECT_UNKNOWN'}}
    def site_read(self,*args):return {'result':{'state':'RESPONSES_OBSERVED','responses':[]}}

class Tests(unittest.TestCase):
    def cfg(self,code):
        base={'profile_id':'x','origin':'https://x.invalid','selectors':{'account':'#a','workspace':'#w','conversation':None,'composer':'#c','send':'#s','outgoing':'.u','response':'.a'},'max_text_bytes':1000}
        d=_digest(base)
        return {'enabled':True,'profiles':{'x':{'origin':base['origin'],'selectors':base['selectors'],'max_text_bytes':1000,
            'qualification':{'status':'PASS','adapter_version':ADAPTER_VERSION,'code_digest':code,'contract_digest':d,'evidence_refs':['fixture']}}}}
    def test_send_once_records_and_reconciles(self):
        code='a'*64;core=Core();bridge=Bridge(code)
        with tempfile.TemporaryDirectory() as td:
            r=SiteAdapterRuntime(core,bridge,self.cfg(code),td);out=r.send_once('x','hello',operation_id='op')
            self.assertEqual(out['state'],'MESSAGE_OBSERVED');self.assertEqual(bridge.sent,1)
            again=r.reconcile_operation('op');self.assertEqual(again['state'],'MESSAGE_OBSERVED');self.assertEqual(bridge.sent,1)
    def test_code_drift_blocks_write(self):
        with tempfile.TemporaryDirectory() as td:
            r=SiteAdapterRuntime(Core(),Bridge('b'*64),self.cfg('a'*64),td)
            with self.assertRaisesRegex(SiteAdapterError,'CODE_DRIFT'):r.send_once('x','hello')
if __name__=='__main__':unittest.main()
