import unittest
from persistent_mission import PersistentMissionController

class Core:
    def __init__(self):self.goal=None;self.rev=0;self.jobs={}
    def goal_create(self,spec,goal_id=None):
        self.rev=1;self.goal={'goal_id':goal_id or 'g','revision':1,'value':{'state':'ACTIVE','spec':spec,'h2':[],'h1':[],'h0':None,'evidence_refs':[],'closed_acceptance':[],'no_progress':0,'runtime':{}}};return self.goal
    def goal_inspect(self,gid):return self.goal
    def goal_plan(self,gid,rev,h2,h1,decision):
        self.rev+=1;self.goal={'goal_id':gid,'revision':self.rev,'value':{**self.goal['value'],'h2':h2,'h1':h1,'last_decision':decision}};return self.goal
    def goal_admit(self,gid,rev,cid):self.rev+=1;self.goal['revision']=self.rev;self.goal['value']['h0']={'candidate_id':cid};return {'goal_id':gid,'revision':self.rev,'h0':self.goal['value']['h0']}
    def goal_progress(self,gid,rev,delta):self.rev+=1;self.goal['revision']=self.rev;self.goal['value']['h0']=None;self.goal['value']['no_progress']=0 if delta['meaningful'] else self.goal['value']['no_progress']+1;return self.goal
    def goal_checkpoint(self,gid,rev,runtime,state=None):self.rev+=1;self.goal['revision']=self.rev;self.goal['value']['runtime']=runtime;self.goal['value']['state']=state or self.goal['value']['state'];return self.goal
    def goal_list(self,offset=0,limit=50):return {'items':[self.goal] if self.goal else []}
    def library_search(self,q,limit=20):return {'items':[{'id':'x'}]}
    def job_get(self,jid):return self.jobs[jid]
class Kernel:
    def __init__(self,state='WAITING_SYSTEM2'):self.state=state
    def capture_browser_context(self):return {'state':'CONTEXT_GATHERED','sha256':'a'*64}
    def start(self,mission):
        if self.state=='WAITING_SYSTEM2':return {'state':'WAITING_SYSTEM2','system2_job_id':'s2','role':'PLANNER'}
        return {'state':self.state}
    def poll_system2(self,jid,mission):return {'state':'SYSTEM2_RESULT_INGESTED','sha256':'b'*64}
class Laya:
    enabled=True
    def decide(self,state,questions):return {'answers':{'frontier_choice':{'choice':'mission_step','answer_confidence':.9,'voice_agentos_admitted':True}}}

class Tests(unittest.TestCase):
    def mission(self):return {'goal':'do work','acceptance':['verified'],'effects':['LOCAL_PROCESS'],'context_text':'ctx'}
    def test_pending_system2_survives_checkpoint_and_resumes(self):
        core=Core();ctl=PersistentMissionController(core,Kernel(),Laya())
        first=ctl.step(self.mission());self.assertEqual(first['value']['state'],'WAITING');self.assertEqual(first['value']['runtime']['job_id'],'s2')
        second=ctl.step(self.mission(),'g');self.assertEqual(second['value']['runtime'],{})
    def test_library_fallback_can_progress(self):
        core=Core();ctl=PersistentMissionController(core,Kernel('NEEDS_CONTEXT'),None)
        out=ctl.step({'goal':'find prior context','acceptance':['found'],'effects':['LOCAL_PROCESS'],'context_text':'ctx'})
        self.assertEqual(out['goal_id'],'g')
if __name__=='__main__':unittest.main()
