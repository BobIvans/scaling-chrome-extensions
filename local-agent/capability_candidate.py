from __future__ import annotations
import base64,hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path

SHA=re.compile(r'^[0-9a-f]{40}$')
SKILL=re.compile(r'^[A-Za-z0-9_.-]{1,80}$')

class CandidateError(RuntimeError):pass

def _run(argv,cwd,timeout):
    if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x and '\x00' not in x for x in argv):
        raise CandidateError('CANDIDATE_COMMAND_SCHEMA')
    kwargs=dict(cwd=str(cwd),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,shell=False)
    if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
    try:r=subprocess.run(argv,**kwargs)
    except (OSError,subprocess.TimeoutExpired) as exc:raise CandidateError('CANDIDATE_COMMAND_FAILED') from exc
    return {'argv':argv,'exit_code':r.returncode,'stdout_tail':r.stdout[-5000:],'stderr_tail':r.stderr[-5000:]}

def _within(path,root):
    try:path.resolve().relative_to(root.resolve());return True
    except Exception:return False

class CapabilityCandidatePipeline:
    """Materialize System-2 proposal artifacts and qualify repo patches in isolation.

    Candidate-provided commands are ignored. Tests come only from local policy.
    """
    def __init__(self,bridge,config,root):
        self.bridge=bridge;self.c=config or {};self.root=Path(root).expanduser().resolve();self.root.mkdir(parents=True,exist_ok=True)
    @property
    def enabled(self):return self.c.get('enabled') is True

    def _profiles(self):
        value=self.c.get('repo_profiles') or {}
        if not isinstance(value,dict):raise CandidateError('CANDIDATE_REPO_PROFILES')
        return value

    def _fetch(self,job_id):
        listing=self.bridge.codex_artifacts(job_id).get('artifacts') or []
        if not isinstance(listing,list) or len(listing)>20:raise CandidateError('CANDIDATE_ARTIFACT_LIST')
        files={}
        for item in listing:
            if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not isinstance(item.get('name'),str):
                raise CandidateError('CANDIDATE_ARTIFACT_SCHEMA')
            name=item['name'].replace('\\','/')
            if name.startswith('/') or '..' in Path(name).parts or len(name)>300:raise CandidateError('CANDIDATE_ARTIFACT_PATH')
            value=self.bridge.codex_artifact(job_id,item['id'])
            try:raw=base64.b64decode(value['bytes_base64'],validate=True)
            except Exception as exc:raise CandidateError('CANDIDATE_ARTIFACT_BASE64') from exc
            if hashlib.sha256(raw).hexdigest()!=value.get('sha256') or len(raw)!=value.get('bytes'):
                raise CandidateError('CANDIDATE_ARTIFACT_HASH')
            files[name]={'bytes':raw,'sha256':value['sha256']}
        return files

    def _manifest(self,files):
        row=files.get('CAPABILITY_MANIFEST.json')
        if not row:raise CandidateError('CANDIDATE_MANIFEST_REQUIRED')
        try:m=json.loads(row['bytes'].decode('utf-8'))
        except Exception as exc:raise CandidateError('CANDIDATE_MANIFEST_PARSE') from exc
        required={'schema','skill_id','version','kind','repo_profile','base_commit','summary','effect_class','required_test_profile','expected_files','verifier'}
        if not isinstance(m,dict) or set(m)!=required or m['schema']!='voice-agentos.capability-candidate.v1':
            raise CandidateError('CANDIDATE_MANIFEST_SCHEMA')
        if not SKILL.fullmatch(str(m['skill_id'])) or not SKILL.fullmatch(str(m['version'])):raise CandidateError('CANDIDATE_SKILL_ID')
        if m['kind']!='repo_patch' or not SHA.fullmatch(str(m['base_commit'])):raise CandidateError('CANDIDATE_KIND_OR_BASE')
        if not all(isinstance(m[x],str) and m[x] for x in ('repo_profile','summary','effect_class','required_test_profile','verifier')):
            raise CandidateError('CANDIDATE_MANIFEST_VALUE')
        if not isinstance(m['expected_files'],list) or not m['expected_files'] or any(not isinstance(x,str) or not x or x.startswith('/') or '..' in Path(x).parts for x in m['expected_files']):
            raise CandidateError('CANDIDATE_EXPECTED_FILES')
        if m['effect_class'] not in {'LOCAL_READ','LOCAL_WRITE','BROWSER_WRITE','GIT_WRITE','GITHUB_WRITE','INSTALL_UPDATE','WINDOWS_WRITE'}:
            raise CandidateError('CANDIDATE_EFFECT_CLASS')
        return m

    def _profile(self,m):
        p=self._profiles().get(m['repo_profile'])
        if not isinstance(p,dict):raise CandidateError('CANDIDATE_REPO_PROFILE_REQUIRED')
        required={'source_checkout','allowed_paths','test_profiles'}
        if set(p)!=required or not isinstance(p['allowed_paths'],list) or not isinstance(p['test_profiles'],dict):
            raise CandidateError('CANDIDATE_REPO_PROFILE_SCHEMA')
        root=Path(os.path.expandvars(os.path.expanduser(p['source_checkout']))).resolve()
        if not (root/'.git').exists():raise CandidateError('CANDIDATE_REPO_CHECKOUT_REQUIRED')
        tests=p['test_profiles'].get(m['required_test_profile'])
        if not isinstance(tests,list) or not tests or any(not isinstance(x,list) or not x or not all(isinstance(v,str) and v for v in x) for x in tests):
            raise CandidateError('CANDIDATE_TEST_PROFILE_REQUIRED')
        allowed=[str(x).replace('\\','/').strip('/') for x in p['allowed_paths']]
        if not allowed:raise CandidateError('CANDIDATE_ALLOWED_PATHS')
        return root,allowed,tests

    def try_qualify_job(self,job_id):
        if not self.enabled:return {'state':'DISABLED'}
        listing=self.bridge.codex_artifacts(job_id).get('artifacts') or []
        names={x.get('name') for x in listing if isinstance(x,dict)}
        if 'CAPABILITY_MANIFEST.json' not in names:return {'state':'NO_CAPABILITY_MANIFEST'}
        return self.qualify_job(job_id)

    def qualify_job(self,job_id):
        if not self.enabled:return {'state':'DISABLED'}
        files=self._fetch(job_id);m=self._manifest(files);patch=files.get('PATCH.diff')
        if not patch or not patch['bytes']:raise CandidateError('CANDIDATE_PATCH_REQUIRED')
        root,allowed,tests=self._profile(m)
        verify=_run(['git','cat-file','-e',m['base_commit']+'^{commit}'],root,30)
        if verify['exit_code']:_run(['git','fetch','--quiet','--no-tags','origin',m['base_commit']],root,120)
        if _run(['git','cat-file','-e',m['base_commit']+'^{commit}'],root,30)['exit_code']:raise CandidateError('CANDIDATE_BASE_MISSING')
        candidate_root=self.root/(m['skill_id']+'-'+m['version']+'-'+patch['sha256'][:12])
        worktree=candidate_root/'worktree'
        if candidate_root.exists():shutil.rmtree(candidate_root)
        candidate_root.mkdir(parents=True)
        patch_path=candidate_root/'PATCH.diff';patch_path.write_bytes(patch['bytes'])
        if _run(['git','worktree','add','--detach',str(worktree),m['base_commit']],root,90)['exit_code']:
            raise CandidateError('CANDIDATE_WORKTREE_FAILED')
        results=[];changed=[]
        try:
            check=_run(['git','apply','--check','--whitespace=error-all',str(patch_path)],worktree,60);results.append(check)
            if check['exit_code']:raise CandidateError('CANDIDATE_PATCH_CHECK_FAILED')
            apply=_run(['git','apply','--whitespace=error-all',str(patch_path)],worktree,60);results.append(apply)
            if apply['exit_code']:raise CandidateError('CANDIDATE_PATCH_APPLY_FAILED')
            names=_run(['git','diff','--name-only','--diff-filter=ACMRTUXB'],worktree,30);results.append(names)
            if names['exit_code']:raise CandidateError('CANDIDATE_DIFF_FAILED')
            changed=[x.strip().replace('\\','/') for x in names['stdout_tail'].splitlines() if x.strip()]
            if not changed or sorted(changed)!=sorted(m['expected_files']):raise CandidateError('CANDIDATE_EXPECTED_FILES_MISMATCH')
            for name in changed:
                if not any(name==prefix or name.startswith(prefix.rstrip('/')+'/') for prefix in allowed):
                    raise CandidateError('CANDIDATE_PATH_OUTSIDE_SCOPE')
            for argv in tests:
                result=_run(argv,worktree,int(self.c.get('test_timeout_seconds',900)));results.append(result)
                if result['exit_code']:raise CandidateError('CANDIDATE_TEST_FAILED')
            diff=_run(['git','diff','--check'],worktree,30);results.append(diff)
            if diff['exit_code']:raise CandidateError('CANDIDATE_DIFF_CHECK_FAILED')
            add=_run(['git','add','-A'],worktree,30);results.append(add)
            if add['exit_code']:raise CandidateError('CANDIDATE_INDEX_FAILED')
            tree=_run(['git','write-tree'],worktree,30);results.append(tree)
            if tree['exit_code']:raise CandidateError('CANDIDATE_TREE_FAILED')
            receipt={'schema':'voice-agentos.capability-qualification.v1','state':'ISOLATED_TESTED','skill_id':m['skill_id'],'version':m['version'],
                     'effect_class':m['effect_class'],'repo_profile':m['repo_profile'],'base_commit':m['base_commit'],
                     'patch_sha256':patch['sha256'],'changed_files':changed,'candidate_tree':tree['stdout_tail'].strip(),'test_profile':m['required_test_profile'],
                     'tests':results,'candidate_worktree':str(worktree),'verifier':m['verifier'],'created_at':time.time(),
                     'next':'CREATE_BOUNDED_PR_OR_DEVICE_CANARY'}
            receipt_path=candidate_root/'qualification.json';receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
            return receipt
        except Exception:
            # Preserve failed worktree/evidence for diagnosis; never activate it.
            raise
