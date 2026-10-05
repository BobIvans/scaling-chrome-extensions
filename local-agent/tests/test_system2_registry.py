import tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from system2_registry import System2ProviderRegistry,System2RegistryError

class Bridge:
    def __init__(self):self.jobs={};self.n=0
    def codex_submit(self,instruction,text,mode='analyze'):
        self.n+=1;j='j'+str(self.n);self.jobs[j]={'state':'QUEUED','text':'answer'};return {'job':{'id':j,'state':'QUEUED'}}
    def codex_result(self,j):
        row=self.jobs[j];row['state']='COMPLETE';return {'job':{'id':j,'state':'COMPLETE'},'text':row['text'],'sha256':'x'}
class FakeReg:
    def profile(self,pid,require_qualified=False):
        if pid!='web':raise ValueError('profile')
        return ({'profile_id':'web'}, {'status':'PASS'})
class Site:
    enabled=True
    def __init__(self):self.registry=FakeReg();self.sent=0;self.responses=[];self.unknown=False
    def bind(self,pid,tab_id=None,require_qualified=False):return {'profile_id':pid,'tab_id':7,'binding':{'identity':{'origin':'https://x'}}}
    def read(self,binding):return {'state':'RESPONSES_OBSERVED','identity':{'origin':'https://x'},'responses':list(self.responses)}
    def send_once(self,pid,draft,tab_id=None,operation_id=None):
        self.sent+=1
        return {'state':'EFFECT_UNKNOWN' if self.unknown else 'MESSAGE_OBSERVED','operation_id':operation_id,
                'site_binding':{'profile_id':pid,'tab_id':7,'binding':{'identity':{'origin':'https://x'}}}}
    def reconcile_operation(self,op):return {'state':'EFFECT_UNKNOWN' if self.unknown else 'MESSAGE_OBSERVED'}

def config(default='codex'):
    return {'enabled':True,'default_provider':default,'providers':{
      'codex':{'kind':'LOCAL_CODEX','enabled':True,'roles':['PLANNER','CODER','TOOL_DESIGNER'],'priority':50,'estimated_latency_ms':1000,'supports_artifacts':True},
      'web':{'kind':'AI_SITE','enabled':True,'roles':['PLANNER','RESEARCHER'],'priority':80,'estimated_latency_ms':500,'supports_artifacts':False,
             'profile_id':'web','tab_id':7,'response_timeout_seconds':60}}}

class Tests(unittest.TestCase):
    def registry(self,td,default='codex'):
        self.bridge=Bridge();self.site=Site()
        return System2ProviderRegistry(self.bridge,self.site,config(default),td)
    def test_coder_prefers_artifact_capable_local_provider(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.registry(td,'web')
            self.assertEqual(r.choose('CODER')['provider_id'],'codex')
    def test_preferred_qualified_web_provider_completes_new_final_response(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.registry(td)
            self.site.responses=[{'message_id':'old','text':'old','finalized':True}]
            s=r.submit('PLANNER','plan','ctx',preferred_provider='web')
            self.assertEqual(self.site.sent,1)
            self.site.responses.append({'message_id':'new','text':'new answer','finalized':True})
            out=r.poll(s['session_id'])
            self.assertEqual(out['state'],'COMPLETE');self.assertEqual(out['result']['text'],'new answer');self.assertEqual(self.site.sent,1)
    def test_site_unknown_effect_never_resends(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.registry(td);self.site.unknown=True
            s=r.submit('PLANNER','plan','ctx',preferred_provider='web')
            self.assertEqual(s['state'],'UNKNOWN_EFFECT');self.assertEqual(self.site.sent,1)
            self.assertEqual(r.poll(s['session_id'])['state'],'UNKNOWN_EFFECT');self.assertEqual(self.site.sent,1)
    def test_session_persists_across_registry_restart(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.registry(td);s=r.submit('PLANNER','plan','ctx',preferred_provider='codex')
            r2=System2ProviderRegistry(self.bridge,self.site,config(),td)
            out=r2.poll(s['session_id']);self.assertEqual(out['state'],'COMPLETE');self.assertEqual(out['result']['text'],'answer')
    def test_multiple_new_final_web_responses_are_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.registry(td);s=r.submit('PLANNER','plan','ctx',preferred_provider='web')
            self.site.responses=[{'message_id':'a','text':'a','finalized':True},{'message_id':'b','text':'b','finalized':True}]
            self.assertEqual(r.poll(s['session_id'])['state'],'RESPONSE_CONFLICT')

if __name__=='__main__':unittest.main()
