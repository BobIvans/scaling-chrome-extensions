import json,unittest
from urllib.error import HTTPError
from github_capability_pr import GitHubCapabilityPipeline,GitHubPipelineError

class Resp:
    def __init__(self,value):self.raw=json.dumps(value).encode()
    def read(self,n=-1):return self.raw[:n] if n>=0 else self.raw
class GitHubTests(unittest.TestCase):
    def cfg(self):
        return {'enabled':True,'repo_full_name':'o/r','token_env':'T','remote':'origin','base_branch':'main','branch_prefix':'agentos',
                'required_checks':['ci'],'merge_method':'squash','allow_auto_merge':True}
    def test_observe_requires_exact_head_and_checks(self):
        calls=[]
        def opener(req,timeout):
            calls.append(req.full_url)
            if req.full_url.endswith('/pulls/7'):return Resp({'state':'open','merged':False,'mergeable':True,'html_url':'u','head':{'sha':'a'*40}})
            if '/check-runs?' in req.full_url:return Resp({'check_runs':[{'name':'ci','status':'completed','conclusion':'success'}]})
            raise AssertionError(req.full_url)
        p=GitHubCapabilityPipeline(self.cfg(),opener=opener,environ={'T':'x'})
        out=p.observe({'number':7,'head_sha':'a'*40});self.assertEqual(out['state'],'CI_PASS');self.assertTrue(out['all_required_pass'])
    def test_merge_is_blocked_without_policy_grant(self):
        cfg=self.cfg();cfg['allow_auto_merge']=False
        p=GitHubCapabilityPipeline(cfg,opener=lambda *a:None,environ={'T':'x'})
        with self.assertRaisesRegex(GitHubPipelineError,'NOT_GRANTED'):p.merge({'number':1,'head_sha':'a'*40},{'GITHUB_WRITE'})
if __name__=='__main__':unittest.main()
