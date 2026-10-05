from __future__ import annotations
import json, os, re, time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request,urlopen
from urllib.error import HTTPError
REPO=re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$');SHA=re.compile(r'^[0-9a-f]{40}$')
class MergeWatchError(RuntimeError):pass
def normalize_repo(value):
    raw=str(value or '').strip().removesuffix('.git')
    for prefix in ('https://github.com/','http://github.com/','git@github.com:'):
        if raw.startswith(prefix):raw=raw[len(prefix):]
    raw=raw.strip('/')
    if not REPO.fullmatch(raw):raise MergeWatchError('GITHUB_REPO_REQUIRED')
    return raw
class MergeWatcher:
    def __init__(self,repo,state_file,token_env='GITHUB_TOKEN',opener=urlopen):
        self.repo=normalize_repo(repo);self.state_file=Path(state_file).expanduser().resolve();self.token_env=token_env;self.opener=opener
    def _state(self):
        if not self.state_file.exists():return {'schema':'voice-agentos.merge-watch.v1','repo':self.repo,'seen':[],'etag':None}
        value=json.loads(self.state_file.read_text(encoding='utf-8'))
        return value if value.get('schema')=='voice-agentos.merge-watch.v1' and value.get('repo')==self.repo else {'schema':'voice-agentos.merge-watch.v1','repo':self.repo,'seen':[],'etag':None}
    def _save(self,value):
        self.state_file.parent.mkdir(parents=True,exist_ok=True);tmp=self.state_file.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,self.state_file)
    def poll(self,emit_existing=False):
        state=self._state();url='https://api.github.com/repos/'+quote(self.repo,safe='/')+'/pulls?state=closed&sort=updated&direction=desc&per_page=30'
        headers={'Accept':'application/vnd.github+json','User-Agent':'VoiceAgentOSMini/1','X-GitHub-Api-Version':'2022-11-28'}
        token=os.environ.get(self.token_env,'').strip()
        if token:headers['Authorization']='Bearer '+token
        if state.get('etag'):headers['If-None-Match']=state['etag']
        try:
            response=self.opener(Request(url,headers=headers),timeout=15);raw=response.read(2000001)
            if len(raw)>2000000:raise MergeWatchError('GITHUB_RESPONSE_LIMIT')
            rows=json.loads(raw.decode());etag=response.headers.get('ETag')
        except HTTPError as exc:
            if exc.code==304:return []
            raise MergeWatchError('GITHUB_WATCH_HTTP_'+str(exc.code)) from exc
        if not isinstance(rows,list):raise MergeWatchError('GITHUB_WATCH_SCHEMA')
        merged=[]
        for row in rows:
            sha=row.get('merge_commit_sha');merged_at=row.get('merged_at')
            if row.get('merged') is not True or not merged_at or not isinstance(sha,str) or not SHA.fullmatch(sha):continue
            merged.append({'repo':self.repo,'number':row.get('number'),'title':row.get('title',''),'merged_at':merged_at,'merge_commit_sha':sha,'head_sha':(row.get('head') or {}).get('sha'),'base_ref':(row.get('base') or {}).get('ref'),'html_url':row.get('html_url')})
        seen=set(state.get('seen',[]));fresh=[x for x in merged if x['merge_commit_sha'] not in seen]
        if not state.get('initialized') and not emit_existing:fresh=[]
        state.update(initialized=True,etag=etag or state.get('etag'),checked_at=time.time(),seen=list(dict.fromkeys([x['merge_commit_sha'] for x in merged]+list(seen)))[:200]);self._save(state)
        return sorted(fresh,key=lambda x:x['merged_at'])
