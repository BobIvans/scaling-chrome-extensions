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
    def test_system2_result_is_ingested(self):
        core=Core('GAP');bridge=Bridge();kernel=self.kernel(core,None,bridge)
        out=kernel.poll_system2('s2',{'goal':'x','acceptance':[],'effects':['READ']})
        self.assertEqual(out['state'],'SYSTEM2_RESULT_INGESTED');self.assertEqual(len(core.captured),1)
if __name__=='__main__':unittest.main()
