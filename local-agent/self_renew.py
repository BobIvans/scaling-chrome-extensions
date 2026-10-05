from __future__ import annotations
import json,os,re,shutil,subprocess,time
from pathlib import Path
SHA=re.compile(r'^[0-9a-f]{40}$')
class RenewError(RuntimeError):pass
def run(argv,cwd,timeout):
    if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x and '\0' not in x for x in argv):raise RenewError('RENEW_COMMAND_SCHEMA')
    kwargs=dict(cwd=str(cwd),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,shell=False)
    if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
    try:r=subprocess.run(argv,**kwargs)
    except (OSError,subprocess.TimeoutExpired) as exc:raise RenewError('RENEW_COMMAND_FAILED') from exc
    return {'argv':argv,'exit_code':r.returncode,'stdout_tail':r.stdout[-4000:],'stderr_tail':r.stderr[-4000:]}
class VerifiedRenewal:
    def __init__(self,config,receipt_root):self.c=config or {};self.receipt_root=Path(receipt_root).expanduser().resolve()
    def enabled(self):return self.c.get('enabled') is True
    def stage_merge(self,merge):
        if not self.enabled():return {'state':'DISABLED'}
        sha=merge.get('merge_commit_sha')
        if not isinstance(sha,str) or not SHA.fullmatch(sha):raise RenewError('RENEW_SHA_REQUIRED')
        root=Path(self.c['source_checkout']).expanduser().resolve();stage_root=Path(self.c['staging_root']).expanduser().resolve()
        if not (root/'.git').exists():raise RenewError('RENEW_GIT_CHECKOUT_REQUIRED')
        stage_root.mkdir(parents=True,exist_ok=True);stage=stage_root/sha
        if run(['git','fetch','--quiet','--no-tags','origin',sha],root,120)['exit_code']:raise RenewError('RENEW_FETCH_FAILED')
        if run(['git','cat-file','-e',sha+'^{commit}'],root,30)['exit_code']:raise RenewError('RENEW_COMMIT_MISSING')
        if stage.exists():shutil.rmtree(stage)
        if run(['git','worktree','add','--detach',str(stage),sha],root,60)['exit_code']:raise RenewError('RENEW_WORKTREE_FAILED')
        results=[]
        for command in self.c.get('test_commands',[]):
            result=run(command,stage,int(self.c.get('test_timeout_seconds',600)));results.append(result)
            if result['exit_code']:raise RenewError('RENEW_TEST_FAILED')
        desktop=None;d=self.c.get('desktop_install') or {}
        if d.get('enabled') is True:
            output=Path(os.path.expandvars(d['versions_root'])).expanduser().resolve()/sha
            argv=[d.get('python_path') or os.sys.executable,str(stage/'desktop/install.py'),'install','--source',str(stage),'--output',str(output),'--profile',str(Path(os.path.expandvars(d['profile_path'])).expanduser().resolve())]
            result=run(argv,stage,int(d.get('timeout_seconds',600)));results.append(result)
            if result['exit_code']:raise RenewError('RENEW_DESKTOP_STAGE_FAILED')
            desktop={'state':'VERSION_STAGED','root':str(output),'activation':'NOT_PERFORMED_REQUIRES_QUALIFICATION'}
        receipt={'schema':'voice-agentos.verified-renewal.v1','state':'STAGED_VERIFIED_SOURCE','repo':merge.get('repo'),'merge_commit_sha':sha,'merged_at':merge.get('merged_at'),'staging_root':str(stage),'tests':results,'desktop':desktop,'created_at':time.time(),'next':'QUALIFY_AND_ACTIVATE_THROUGH_STABLE_CONTROLLER'}
        self.receipt_root.mkdir(parents=True,exist_ok=True);p=self.receipt_root/(sha+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,p);return receipt
