from __future__ import annotations
import json,os,re,subprocess,time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request,urlopen

REPO=re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
SHA=re.compile(r'^[0-9a-f]{40}$')
SAFE=re.compile(r'[^A-Za-z0-9._/-]+')

class GitHubPipelineError(RuntimeError):pass

def _run(argv,cwd,timeout):
    if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x and '\x00' not in x for x in argv):
        raise GitHubPipelineError('GITHUB_COMMAND_SCHEMA')
    kwargs=dict(cwd=str(cwd),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,shell=False)
    if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
    try:r=subprocess.run(argv,**kwargs)
    except (OSError,subprocess.TimeoutExpired) as exc:raise GitHubPipelineError('GITHUB_COMMAND_FAILED') from exc
    return {'argv':argv,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}

class GitHubCapabilityPipeline:
    """Push a locally qualified candidate and optionally exact-head merge it.

    Repo/base/check names are local policy. System-2 cannot override them.
    """
    def __init__(self,config,opener=urlopen,environ=None):
        self.c=config or {};self.opener=opener;self.env=environ if environ is not None else os.environ;self._validate()
    @property
    def enabled(self):return self.c.get('enabled') is True
    def _validate(self):
        if not self.enabled:return
        required={'enabled','repo_full_name','token_env','remote','base_branch','branch_prefix','required_checks','merge_method','allow_auto_merge'}
        if set(self.c)!=required or not REPO.fullmatch(str(self.c['repo_full_name'])):raise GitHubPipelineError('GITHUB_PIPELINE_CONFIG')
        if not isinstance(self.c['required_checks'],list) or any(not isinstance(x,str) or not x for x in self.c['required_checks']):raise GitHubPipelineError('GITHUB_REQUIRED_CHECKS')
        if self.c['merge_method'] not in {'merge','squash','rebase'}:raise GitHubPipelineError('GITHUB_MERGE_METHOD')
    def _token(self):
        token=str(self.env.get(self.c['token_env'],'')).strip()
        if not token:raise GitHubPipelineError('GITHUB_TOKEN_MISSING')
        return token
    def _api(self,method,path,body=None):
        url='https://api.github.com/repos/'+self.c['repo_full_name']+path
        data=None if body is None else json.dumps(body,separators=(',',':')).encode()
        req=Request(url,data=data,method=method,headers={'Authorization':'Bearer '+self._token(),'Accept':'application/vnd.github+json',
            'X-GitHub-Api-Version':'2022-11-28','User-Agent':'VoiceAgentOS/1','Content-Type':'application/json'})
        try:
            raw=self.opener(req,timeout=30).read(2_000_001)
        except HTTPError as exc:raise GitHubPipelineError('GITHUB_HTTP_'+str(exc.code)) from exc
        except Exception as exc:raise GitHubPipelineError('GITHUB_HTTP_FAILED') from exc
        if len(raw)>2_000_000:raise GitHubPipelineError('GITHUB_RESPONSE_LIMIT')
        try:return json.loads(raw.decode()) if raw else {}
        except Exception as exc:raise GitHubPipelineError('GITHUB_RESPONSE_SCHEMA') from exc
    def _branch(self,receipt):
        base=self.c['branch_prefix'].strip('/') or 'agentos'
        skill=SAFE.sub('-',str(receipt['skill_id'])).strip('-')[:40]
        version=SAFE.sub('-',str(receipt['version'])).strip('-')[:20]
        return (base+'/'+skill+'-'+version+'-'+receipt['patch_sha256'][:10])[:180]
    def publish(self,receipt,effect_scope):
        if not self.enabled:return {'state':'DISABLED'}
        if 'GITHUB_WRITE' not in set(effect_scope):raise GitHubPipelineError('GITHUB_WRITE_SCOPE_REQUIRED')
        if not isinstance(receipt,dict) or receipt.get('schema')!='voice-agentos.capability-qualification.v1' or receipt.get('state')!='ISOLATED_TESTED':
            raise GitHubPipelineError('GITHUB_QUALIFIED_CANDIDATE_REQUIRED')
        base_commit=receipt.get('base_commit')
        if not isinstance(base_commit,str) or not SHA.fullmatch(base_commit):raise GitHubPipelineError('GITHUB_BASE_COMMIT')
        worktree=Path(receipt['candidate_worktree']).resolve()
        if not (worktree/'.git').exists() and not (worktree.parent/'.git').exists():
            # linked worktrees use a .git file, not directory
            if not (worktree/'.git').is_file():raise GitHubPipelineError('GITHUB_WORKTREE_REQUIRED')
        branch=self._branch(receipt)
        remote=self.c['remote'];base=self.c['base_branch']
        fetch=_run(['git','fetch','--quiet',remote,base],worktree,120)
        if fetch['exit_code']:raise GitHubPipelineError('GITHUB_BASE_FETCH_FAILED')
        remote_base=_run(['git','rev-parse',remote+'/'+base],worktree,30)
        if remote_base['exit_code'] or remote_base['stdout'].strip()!=base_commit:raise GitHubPipelineError('GITHUB_BASE_DRIFT')
        cached=_run(['git','diff','--cached','--name-only'],worktree,30)
        changed=[x.strip().replace('\\','/') for x in cached['stdout'].splitlines() if x.strip()]
        if sorted(changed)!=sorted(receipt.get('changed_files') or []):raise GitHubPipelineError('GITHUB_CANDIDATE_DIFF_DRIFT')
        if _run(['git','switch','-c',branch],worktree,30)['exit_code']:raise GitHubPipelineError('GITHUB_BRANCH_CREATE_FAILED')
        title='AgentOS capability: '+str(receipt['skill_id'])+' '+str(receipt['version'])
        if _run(['git','commit','-m',title],worktree,60)['exit_code']:raise GitHubPipelineError('GITHUB_COMMIT_FAILED')
        head=_run(['git','rev-parse','HEAD'],worktree,30)['stdout'].strip()
        if not SHA.fullmatch(head):raise GitHubPipelineError('GITHUB_HEAD_SHA')
        push=_run(['git','push','--set-upstream',remote,'HEAD:refs/heads/'+branch],worktree,120)
        if push['exit_code']:raise GitHubPipelineError('GITHUB_PUSH_FAILED')
        body='Automated bounded capability candidate.\n\nBase: '+base_commit+'\nPatch: '+receipt['patch_sha256']+'\nQualification: ISOLATED_TESTED\nChanged files:\n- '+'\n- '.join(changed)
        created=self._api('POST','/pulls',{'title':title,'head':branch,'base':base,'body':body,'draft':False})
        number=created.get('number')
        if not isinstance(number,int):raise GitHubPipelineError('GITHUB_PR_CREATE_SCHEMA')
        return {'schema':'voice-agentos.capability-pr.v1','state':'PR_OPEN','number':number,'url':created.get('html_url'),
                'head_sha':head,'branch':branch,'base_branch':base,'base_commit':base_commit,'candidate':receipt,
                'required_checks':list(self.c['required_checks']),'auto_merge':self.c['allow_auto_merge'] is True}
    def observe(self,pr_receipt):
        if not isinstance(pr_receipt,dict) or not isinstance(pr_receipt.get('number'),int) or not SHA.fullmatch(str(pr_receipt.get('head_sha',''))):
            raise GitHubPipelineError('GITHUB_PR_RECEIPT')
        number=pr_receipt['number'];expected=pr_receipt['head_sha']
        pr=self._api('GET','/pulls/'+str(number))
        head=(pr.get('head') or {}).get('sha')
        if head!=expected:raise GitHubPipelineError('GITHUB_PR_HEAD_DRIFT')
        checks=self._api('GET','/commits/'+expected+'/check-runs?per_page=100').get('check_runs') or []
        by_name={x.get('name'):x for x in checks if isinstance(x,dict)}
        required={}
        for name in self.c['required_checks']:
            row=by_name.get(name)
            required[name]={'status':row.get('status'),'conclusion':row.get('conclusion')} if row else {'status':'MISSING','conclusion':None}
        all_pass=all(v['status']=='completed' and v['conclusion'] in {'success','neutral','skipped'} for v in required.values())
        return {'schema':'voice-agentos.capability-pr-observation.v1','state':'CI_PASS' if all_pass else 'CI_PENDING_OR_FAILED',
                'number':number,'url':pr.get('html_url'),'head_sha':expected,'pr_state':pr.get('state'),'merged':pr.get('merged') is True,
                'mergeable':pr.get('mergeable'),'required_checks':required,'all_required_pass':all_pass}
    def merge(self,pr_receipt,effect_scope):
        if 'GITHUB_WRITE' not in set(effect_scope):raise GitHubPipelineError('GITHUB_WRITE_SCOPE_REQUIRED')
        if self.c['allow_auto_merge'] is not True:raise GitHubPipelineError('GITHUB_AUTO_MERGE_NOT_GRANTED')
        observation=self.observe(pr_receipt)
        if observation['merged']:return {**observation,'state':'MERGED_REMOTE','reused':True}
        if not observation['all_required_pass']:raise GitHubPipelineError('GITHUB_REQUIRED_CHECKS_NOT_PASSING')
        result=self._api('PUT','/pulls/'+str(pr_receipt['number'])+'/merge',{'sha':pr_receipt['head_sha'],'merge_method':self.c['merge_method']})
        if result.get('merged') is not True:raise GitHubPipelineError('GITHUB_MERGE_REJECTED')
        merged_sha=result.get('sha')
        if not isinstance(merged_sha,str) or not SHA.fullmatch(merged_sha):raise GitHubPipelineError('GITHUB_MERGE_SHA')
        return {'schema':'voice-agentos.capability-pr-merge.v1','state':'MERGED_REMOTE','number':pr_receipt['number'],
                'head_sha':pr_receipt['head_sha'],'merge_commit_sha':merged_sha,'url':observation['url'],'required_checks':observation['required_checks']}
