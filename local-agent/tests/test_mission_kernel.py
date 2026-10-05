import tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mission_kernel import MissionKernel

class Core:
    def __init__(self,state='COMPILED'):self.state=state;self.captured=[]
    def create_action(self,goal,criteria,refs):
        if self.state=='COMPILED':return {'state':'COMPILED','intent_id':'i','revision':1}
        return {'state':'NEEDS_DEVELOPMENT','development_request':{'capability':'x'}}
    def enqueue_action(self,intent_id,revision):return {'id':'job','state':'QUEUED'}
    def capture_file(self,path,key):self.captured.append((str(path),key));return {'state':'CAPTURED','namespace':'n','source_key':key,'revision':'a'*64,'sha256':'b'*64,'bytes':Path(path).stat().st_size}
    def annotate_capture(self,*a,**k):return {'state':'ANNOTATED'}

class Bridge:
    def __init__(self):self.submits=[];self.acts=[]
    def codex_submit(self,instruction,text,mode='analyze'):
        self.submits.append((instruction,text,mode));return {'job':{'id':'s2','state':'QUEUED'}}
    def codex_result(self,job_id):return {'job':{'id':job_id,'state':'COMPLETE'},'text':'tool candidate','sha256':'c'*64}
    def ui_inventory(self):
        return {'tabId':7,'snapshot_id':'s','document_token':'d','url':'https://x','title':'X','elements':[
            {'element_id':'e1','role':'button','name':'Show more','risk':'READ_NAV','fingerprint':'f1'},
            {'element_id':'e2','role':'button','name':'Delete all','risk':'DANGEROUS','fingerprint':'f2'}]}
    def ui_act(self,request,tab_id=None):self.acts.append((request,tab_id));return {'state':'UI_CLICK_INVOKED'}

class Laya:
    enabled=True
    def __init__(self,answers):self.answers=answers
    def decide(self,state,questions):return {'answers':self.answers}

class Registry:
    enabled=True
    def __init__(self):self.preferred=None;self.sessions={}
    def describe(self,role=None):
        return [{'provider_id':'web','kind':'AI_SITE','roles':['PLANNER','RESEARCHER'],'priority':100,'estimated_latency_ms':100,'supports_artifacts':False,'available':True,'state':'QUALIFIED'},
                {'provider_id':'codex','kind':'LOCAL_CODEX','roles':['PLANNER','CODER','TOOL_DESIGNER'],'priority':90,'estimated_latency_ms':1000,'supports_artifacts':True,'available':True,'state':'READY'}]
    def submit(self,role,instruction,text,mode='analyze',preferred_provider=None,request_id=None):
        self.preferred=preferred_provider;sid='d'*32
        provider='web' if preferred_provider=='web' else 'codex'
        self.sessions[sid]={'provider_id':provider,'role':role,'mode':mode}
        return {'session_id':sid,'provider_id':provider,'kind':'AI_SITE' if provider=='web' else 'LOCAL_CODEX','state':'WAITING','local_job_id':None if provider=='web' else 'local-job'}
    def is_session(self,sid):return sid in self.sessions
    def poll(self,sid):
        row=self.sessions[sid]
        return {'session_id':sid,'provider_id':row['provider_id'],'kind':'AI_SITE' if row['provider_id']=='web' else 'LOCAL_CODEX',
                'role':row['role'],'mode':row['mode'],'state':'COMPLETE','local_job_id':None if row['provider_id']=='web' else 'local-job',
                'result':{'text':'provider answer','sha256':'e'*64}}
class KernelTests(unittest.TestCase):
    def kernel(self,core,laya=None,bridge=None):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup)
        q=Path(td.name)/'q.json';q.write_text('{}')
        return MissionKernel(core,bridge,laya,q,td.name)
    def test_registered_capability_queues_core(self):
        out=self.kernel(Core(),None,None).start({'goal':'x','acceptance':['done'],'effects':['READ'],'context_text':''})
        self.assertEqual(out['state'],'CORE_JOB_QUEUED')
    def test_missing_capability_calls_system2_tool_designer(self):
        bridge=Bridge();out=self.kernel(Core('GAP'),None,bridge).start({'goal':'x','acceptance':['done'],'effects':['READ'],'context_text':'ctx'})
        self.assertEqual(out['state'],'WAITING_SYSTEM2');self.assertEqual(out['role'],'TOOL_DESIGNER');self.assertEqual(bridge.submits[0][2],'build')
    def test_laya_gather_context_does_not_call_system2(self):
        bridge=Bridge();laya=Laya({'mission_route':'GATHER_CONTEXT','system2_role':'RESEARCHER'})
        out=self.kernel(Core('GAP'),laya,bridge).start({'goal':'x','acceptance':['done'],'effects':['READ'],'context_text':''})
        self.assertEqual(out['state'],'NEEDS_CONTEXT');self.assertEqual(bridge.submits,[])
    def test_laya_safe_read_nav_ui_action_is_exact_bound(self):
        bridge=Bridge();laya=Laya({'mission_route':'BROWSER_UI','ui_candidate':'e1','ui_action':'CLICK_READ_NAV'})
        out=self.kernel(Core('GAP'),laya,bridge).start({'goal':'expand context','acceptance':['done'],'effects':['READ','BROWSER_WRITE'],'context_text':''})
        self.assertEqual(out['state'],'BROWSER_UI_EFFECT');self.assertEqual(bridge.acts[0][0]['expected_fingerprint'],'f1');self.assertEqual(bridge.acts[0][1],7)
    def test_laya_cannot_use_generic_dangerous_click(self):
        bridge=Bridge();laya=Laya({'mission_route':'BROWSER_UI','ui_candidate':'e2','ui_action':'CLICK_READ_NAV'})
        out=self.kernel(Core('GAP'),laya,bridge).start({'goal':'x','acceptance':['done'],'effects':['READ','BROWSER_WRITE'],'context_text':''})
        self.assertEqual(out['state'],'BROWSER_UI_BLOCKED');self.assertEqual(bridge.acts,[])
    def test_laya_can_choose_qualified_web_system2_provider(self):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup)
        q=Path(td.name)/'q.json';q.write_text('{}')
        registry=Registry();bridge=Bridge()
        laya=Laya({'mission_route':'SYSTEM2','system2_role':'PLANNER','system2_provider':'web'})
        kernel=MissionKernel(Core('GAP'),bridge,laya,q,td.name,system2_registry=registry)
        out=kernel.start({'goal':'plan','acceptance':['done'],'effects':['READ'],'context_text':'existing context'})
        self.assertEqual(out['state'],'WAITING_SYSTEM2');self.assertEqual(out['system2_provider'],'web')
        self.assertEqual(out['system2_session_id'],'d'*32);self.assertEqual(registry.preferred,'web')
        result=kernel.poll_system2(out['system2_session_id'],{'goal':'plan','acceptance':['done'],'effects':['READ']})
        self.assertEqual(result['state'],'SYSTEM2_RESULT_INGESTED');self.assertEqual(result['system2_provider'],'web')
        self.assertEqual(result['text'],'provider answer')
    def test_system2_result_is_ingested(self):
        core=Core('GAP');bridge=Bridge();kernel=self.kernel(core,None,bridge)
        out=kernel.poll_system2('s2',{'goal':'x','acceptance':[],'effects':['READ']})
        self.assertEqual(out['state'],'SYSTEM2_RESULT_INGESTED');self.assertEqual(len(core.captured),1)
if __name__=='__main__':unittest.main()
