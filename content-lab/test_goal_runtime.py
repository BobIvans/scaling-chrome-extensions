import tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import goal_runtime

class GoalTests(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.store=Path(self.t.name)
    def tearDown(self):self.t.cleanup()
    def spec(self):return {'goal':'ship agent','acceptance':['verified'],'constraints':[],'prohibitions':['no blind retry'],'effect_scope':['READ','LOCAL_WRITE']}
    def candidate(self,i='a',deps=None,progress=80):
        return {'id':i,'kind':'research','text':'do '+i,'depends_on':deps or [],'effect_class':'READ','verifier':'receipt','resources':['repo'],
                'components':{'progress':progress,'information_gain':70,'success_probability':90,'latency_cost':10,'human_cost':0,'resource_cost':5,'risk_penalty':0,'freshness_penalty':0,'unlock_count':20,'parallelizable':True},'state':'CANDIDATE'}
    def test_persist_rank_admit_progress(self):
        g=goal_runtime.create(self.store,self.spec());gid=g['goal_id']
        p=goal_runtime.plan(self.store,gid,g['revision'],[{'id':'m','text':'milestone','state':'ACTIVE','acceptance':['done'],'depends_on':[]}],[self.candidate('a'),self.candidate('b',progress=20)],{'route':'READ'})
        self.assertEqual(p['value']['h1'][0]['id'],'a')
        a=goal_runtime.admit(self.store,gid,p['revision'],'a');self.assertEqual(a['h0']['state'],'ADMITTED_PROPOSAL')
        d=goal_runtime.progress(self.store,gid,a['revision'],{'digest':'a'*64,'meaningful':True,'evidence_refs':['receipt:x'],'closed_acceptance':[],'candidate_done':'a','state':'ACTIVE'})
        self.assertEqual(d['value']['h1'][0]['state'],'DONE');self.assertEqual(d['value']['no_progress'],0)
    def test_effect_scope_and_dependencies_gate_h0(self):
        g=goal_runtime.create(self.store,self.spec());gid=g['goal_id']
        write=self.candidate('w');write['effect_class']='GITHUB_WRITE'
        blocked=self.candidate('b',['w'])
        p=goal_runtime.plan(self.store,gid,g['revision'],[],[write,blocked],{})
        with self.assertRaisesRegex(ValueError,'EFFECT_OUTSIDE_SCOPE'):goal_runtime.admit(self.store,gid,p['revision'],'w')
        with self.assertRaisesRegex(ValueError,'DEPENDENCY'):goal_runtime.admit(self.store,gid,p['revision'],'b')
if __name__=='__main__':unittest.main()
