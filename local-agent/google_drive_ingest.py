from __future__ import annotations
import hashlib, json, mimetypes, os, re, time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API='https://www.googleapis.com/drive/v3'
TOKEN_URL='https://oauth2.googleapis.com/token'
GOOGLE_PREFIX='application/vnd.google-apps.'
EXPORTS={
    'application/vnd.google-apps.document':('text/plain','.txt'),
    'application/vnd.google-apps.spreadsheet':('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','.xlsx'),
    'application/vnd.google-apps.presentation':('application/vnd.openxmlformats-officedocument.presentationml.presentation','.pptx'),
    'application/vnd.google-apps.drawing':('application/pdf','.pdf'),
}
SAFE=re.compile(r'[^A-Za-z0-9._ -]+')

class DriveError(RuntimeError):pass

def safe_name(name, fallback='drive-file'):
    value=SAFE.sub('_',str(name or '')).strip(' ._')[:150] or fallback
    return value

class GoogleDriveIngestor:
    """Read-only Drive connector. OAuth secrets/tokens are read from environment only."""
    def __init__(self,config,state_file,opener=urlopen,environ=None):
        self.c=config or {};self.state_file=Path(state_file).expanduser().resolve();self.opener=opener;self.env=environ if environ is not None else os.environ
        self._validate()
    def _validate(self):
        if self.c.get('enabled') is not True:return
        if not isinstance(self.c.get('download_root'),str):raise DriveError('DRIVE_DOWNLOAD_ROOT_REQUIRED')
        folders=self.c.get('folder_ids',[])
        if not isinstance(folders,list) or not all(isinstance(x,str) and x and '\n' not in x for x in folders):raise DriveError('DRIVE_FOLDER_IDS')
        for key in ('access_token_env','refresh_token_env','client_id_env'):
            if key in self.c and (not isinstance(self.c[key],str) or not self.c[key]):raise DriveError('DRIVE_ENV_NAME')
        if not self.c.get('access_token_env') and not (self.c.get('refresh_token_env') and self.c.get('client_id_env')):raise DriveError('DRIVE_OAUTH_CONFIG_REQUIRED')
        if int(self.c.get('max_files_per_poll',100)) not in range(1,1001):raise DriveError('DRIVE_MAX_FILES')
        if int(self.c.get('max_bytes_per_file',10_000_000))<1:raise DriveError('DRIVE_MAX_BYTES')
    @property
    def enabled(self):return self.c.get('enabled') is True
    def _state(self):
        if not self.state_file.exists():return {'schema':'voice-agentos.drive-ingest-state.v1','files':{}}
        try:value=json.loads(self.state_file.read_text(encoding='utf-8'))
        except Exception:return {'schema':'voice-agentos.drive-ingest-state.v1','files':{}}
        return value if value.get('schema')=='voice-agentos.drive-ingest-state.v1' and isinstance(value.get('files'),dict) else {'schema':'voice-agentos.drive-ingest-state.v1','files':{}}
    def _save(self,state):
        self.state_file.parent.mkdir(parents=True,exist_ok=True);tmp=self.state_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,self.state_file)
    def _env(self,name,required=False):
        value=str(self.env.get(name,'')).strip() if name else ''
        if required and not value:raise DriveError('DRIVE_OAUTH_SECRET_MISSING')
        return value
    def _token(self):
        direct=self._env(self.c.get('access_token_env'))
        if direct:return direct
        refresh=self._env(self.c.get('refresh_token_env'),True);client=self._env(self.c.get('client_id_env'),True);secret=self._env(self.c.get('client_secret_env'))
        form={'client_id':client,'refresh_token':refresh,'grant_type':'refresh_token'}
        if secret:form['client_secret']=secret
        req=Request(TOKEN_URL,data=urlencode(form).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST')
        try:raw=self.opener(req,timeout=15).read(1_000_001)
        except Exception as exc:raise DriveError('DRIVE_OAUTH_REFRESH_FAILED') from exc
        if len(raw)>1_000_000:raise DriveError('DRIVE_OAUTH_RESPONSE_LIMIT')
        try:value=json.loads(raw.decode('utf-8'))
        except Exception as exc:raise DriveError('DRIVE_OAUTH_RESPONSE_SCHEMA') from exc
        token=value.get('access_token')
        if not isinstance(token,str) or not token:raise DriveError('DRIVE_OAUTH_REFRESH_FAILED')
        return token
    def _get(self,url,token,limit,accept='application/json'):
        req=Request(url,headers={'Authorization':'Bearer '+token,'Accept':accept,'User-Agent':'VoiceAgentOS/1'})
        try:raw=self.opener(req,timeout=30).read(limit+1)
        except Exception as exc:raise DriveError('DRIVE_HTTP_FAILED') from exc
        if len(raw)>limit:raise DriveError('DRIVE_RESPONSE_LIMIT')
        return raw
    def _list(self,token):
        folders=self.c.get('folder_ids') or [None];seen={};page_size=min(1000,int(self.c.get('max_files_per_poll',100)))
        max_files=int(self.c.get('max_files_per_poll',100))
        for folder in folders:
            token_page=None
            while len(seen)<max_files:
                q="trashed=false"
                if folder:q="'"+folder.replace("'","\\'")+"' in parents and "+q
                params={'q':q,'pageSize':min(page_size,max_files-len(seen)),'spaces':'drive','supportsAllDrives':'true','includeItemsFromAllDrives':'true',
                        'fields':'nextPageToken,files(id,name,mimeType,modifiedTime,md5Checksum,size,parents,capabilities(canDownload))'}
                if token_page:params['pageToken']=token_page
                raw=self._get(API+'/files?'+urlencode(params),token,2_000_000)
                try:value=json.loads(raw.decode('utf-8'))
                except Exception as exc:raise DriveError('DRIVE_LIST_SCHEMA') from exc
                rows=value.get('files')
                if not isinstance(rows,list):raise DriveError('DRIVE_LIST_SCHEMA')
                for row in rows:
                    if isinstance(row,dict) and isinstance(row.get('id'),str):seen[row['id']]=row
                    if len(seen)>=max_files:break
                token_page=value.get('nextPageToken')
                if not token_page:break
        return list(seen.values())
    def _download(self,row,token):
        mime=row.get('mimeType','');file_id=row['id'];max_bytes=int(self.c.get('max_bytes_per_file',10_000_000))
        if isinstance(row.get('capabilities'),dict) and row['capabilities'].get('canDownload') is False:raise DriveError('DRIVE_DOWNLOAD_NOT_ALLOWED')
        if mime in EXPORTS:
            export_mime,ext=EXPORTS[mime]
            url=API+'/files/'+quote(file_id,safe='')+'/export?'+urlencode({'mimeType':export_mime})
            raw=self._get(url,token,min(max_bytes,10_000_000),accept=export_mime)
        elif mime.startswith(GOOGLE_PREFIX):
            raise DriveError('DRIVE_GOOGLE_TYPE_UNSUPPORTED')
        else:
            ext=Path(row.get('name','')).suffix or mimetypes.guess_extension(mime or '') or '.bin'
            url=API+'/files/'+quote(file_id,safe='')+'?'+urlencode({'alt':'media','supportsAllDrives':'true'})
            raw=self._get(url,token,max_bytes,accept=mime or 'application/octet-stream')
        root=Path(os.path.expandvars(os.path.expanduser(self.c['download_root']))).resolve();root.mkdir(parents=True,exist_ok=True)
        stem=safe_name(Path(row.get('name','drive-file')).stem,file_id[:12]);target=root/(stem+'__'+file_id[:12]+ext)
        tmp=target.with_suffix(target.suffix+'.tmp');tmp.write_bytes(raw);os.replace(tmp,target)
        return {'path':str(target),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'exported_mime':mime if mime not in EXPORTS else EXPORTS[mime][0]}
    def poll(self,emit_existing=False):
        if not self.enabled:return []
        token=self._token();rows=self._list(token);state=self._state();old=state['files'];fresh=[];next_state={}
        for row in rows:
            fid=row['id'];finger='|'.join(str(row.get(x,'')) for x in ('modifiedTime','md5Checksum','size','mimeType'))
            next_state[fid]=finger
            if old.get(fid)==finger:continue
            if not old and not emit_existing:continue
            try:download=self._download(row,token)
            except DriveError as exc:
                fresh.append({'state':'BLOCKED','file_id':fid,'name':row.get('name',''),'mime_type':row.get('mimeType',''),'reason':str(exc)})
                continue
            fresh.append({'state':'DOWNLOADED','file_id':fid,'name':row.get('name',''),'mime_type':row.get('mimeType',''),
                          'modified_time':row.get('modifiedTime'),'parents':row.get('parents',[]),**download})
        self._save({'schema':'voice-agentos.drive-ingest-state.v1','checked_at':time.time(),'files':next_state})
        return fresh
