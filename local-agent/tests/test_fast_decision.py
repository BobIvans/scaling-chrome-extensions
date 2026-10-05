import tempfile,threading,time,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fast_decision import FastDecisionEngine,utility

def candidate(cid,kind,effect='READ',progress=50,info=50,success=80,latency=20,risk=0,unlock=20,parallel=True,resources=None):
    return {'id':cid,'kind':kind,'text':kind,'depends_on':[],'effect_class':effect,'verifier':'receipt','resources':resources or [],
            'components':{'progress':progress,'information_gain':info,'success_probability':success,'latency_cost':latency,
                'human_cost':0,'resource_cost':5,'risk_penalty':risk,'freshness_penalty':0,'unlock_count':unlock,'parallelizable':parallel},
            'state':'CANDIDATE'}

class Core:
    def __init__(self,barrier=None):self.barrier=barrier
    def library_search(self,query='',limit=8,**kw):
        if self.barrier:self.barrier.wait(timeout=1)
        return {'state':'MATCHES','rows':[{'source_ref':{'source_key':'x','revision':'r'},'annotation':{'project':'P','labels':['a']},'snippet':'hello','why_selected':'EXACT_QUOTE','total_bytes':10}]}
class Bridge:
    def __init__(self,activity=999999,barrier=None):self.activity=activity;self.barrier=barrier
    def ui_inventory(self):
        if self.barrier:self.barrier.wait(timeout=1)
        return {'tabId':1,'snapshot_id':'s','document_token':'d','human_activity_ms':self.activity,'document_has_focus':True,'elements':[]}
class Win:
    def __init__(self,barrier=None):self.barrier=barrier
    def inventory(self):
        if self.barrier:self.barrier.wait(timeout=1)
        return {'snapshot_id':'w','elements':[]}

class FastDecisionTests(unittest.TestCase):
    def test_prefetch_runs_independent_reads_in_parallel(self):
        with tempfile.TemporaryDirectory() as td:
            barrier=threading.Barrier(3)
            e=FastDecisionEngine(Core(barrier),Bridge(barrier=barrier),Win(barrier),Path(td)/'s.json')
            r=e.prefetch({'goal':'find exact flashloan context'})
            self.assertEqual(set(r['lanes']),{'library','browser_ui','windows_ui'})
            self.assertTrue(r['parallel'])
            self.assertTrue(all(x['state']=='OK' for x in r['lanes'].values()))
            self.assertEqual(r['lanes']['library']['value']['rows'][0]['source_key'],'x')
    def test_abstention_uses_fastest_verified_route(self):
        e=FastDecisionEngine(Core(),None,None,config={'laya_override_margin':5})
        f=[candidate('route_context','GATHER_CONTEXT',progress=35,info=95,success=95,latency=20),
           candidate('route_system2','SYSTEM2','LOCAL_PROCESS',progress=60,info=60,success=70,latency=90)]
        p={'lanes':{'library':{'state':'OK','elapsed_ms':5,'value':{'rows':[]}}},'elapsed_ms':5}
        d=e.choose(f,None,['READ','LOCAL_PROCESS'],p)
        self.assertEqual(d['route'],'GATHER_CONTEXT');self.assertEqual(d['reason'],'DETERMINISTIC_FASTEST_VERIFIED')
    def test_bad_laya_route_is_overridden_but_close_route_is_respected(self):
        e=FastDecisionEngine(Core(),None,None,config={'laya_override_margin':10})
        f=[candidate('route_context','GATHER_CONTEXT',progress=90,info=90,success=95,latency=5),
           candidate('route_system2','SYSTEM2','LOCAL_PROCESS',progress=20,info=20,success=50,latency=90)]
        p={'lanes':{'library':{'state':'OK','elapsed_ms':5,'value':{}}},'elapsed_ms':5}
        self.assertEqual(e.choose(f,'SYSTEM2',['READ','LOCAL_PROCESS'],p)['route'],'GATHER_CONTEXT')
        f[1]['components'].update(progress=90,information_gain=90,success_probability=95,latency_cost=5)
        self.assertEqual(e.choose(f,'SYSTEM2',['READ','LOCAL_PROCESS'],p)['route'],'SYSTEM2')
    def test_human_foreground_blocks_browser_mutation(self):
        e=FastDecisionEngine(Core(),Bridge(activity=10),None,config={'human_quiet_ms':1800})
        f=[candidate('route_browser','BROWSER_UI','BROWSER_WRITE',progress=99)]
        p={'lanes':{'browser_ui':{'state':'OK','elapsed_ms':2,'value':{'human_activity_ms':10,'document_has_focus':True}}},'elapsed_ms':2}
        d=e.choose(f,'BROWSER_UI',['READ','BROWSER_WRITE'],p)
        self.assertEqual(d['route'],'STOP');self.assertEqual(d['blocked'][0]['reason'],'HUMAN_FOREGROUND')
    def test_parallel_plan_only_safe_disjoint_lanes(self):
        e=FastDecisionEngine(Core(),None,None,config={'max_parallel_lanes':3})
        f=[candidate('a','A','READ',progress=80,resources=['library']),candidate('b','B','LOCAL_PROCESS',progress=70,resources=['cpu']),
           candidate('c','C','READ',progress=60,resources=['library']),candidate('d','D','GITHUB_WRITE',progress=99,resources=['git'])]
        p={'lanes':{},'elapsed_ms':1}
        rows=e.parallel_plan(f,None,['READ','LOCAL_PROCESS','GITHUB_WRITE'],p)
        ids=[x['candidate_id'] for x in rows]
        self.assertIn('a',ids);self.assertIn('b',ids);self.assertNotIn('c',ids);self.assertNotIn('d',ids)

if __name__=='__main__':unittest.main()
