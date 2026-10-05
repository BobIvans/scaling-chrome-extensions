from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
DEFAULT_EXT={'.txt','.md','.json','.jsonl','.csv','.tsv','.log','.py','.js','.ts','.html','.pdf','.docx','.pptx','.xlsx','.zip'}
class FolderWatcher:
    def __init__(self,roots,state_file,extensions=None,max_bytes=200000000):
        self.roots=[Path(x).expanduser().resolve() for x in roots];self.state_file=Path(state_file).expanduser().resolve();self.extensions={x.lower() for x in (extensions or DEFAULT_EXT)};self.max_bytes=max_bytes
    def _state(self):
        if not self.state_file.exists():return {'schema':'voice-agentos.folder-watch.v1','files':{}}
        try:value=json.loads(self.state_file.read_text(encoding='utf-8'))
        except Exception:return {'schema':'voice-agentos.folder-watch.v1','files':{}}
        return value if value.get('schema')=='voice-agentos.folder-watch.v1' else {'schema':'voice-agentos.folder-watch.v1','files':{}}
    def _save(self,value):
        self.state_file.parent.mkdir(parents=True,exist_ok=True);tmp=self.state_file.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');os.replace(tmp,self.state_file)
    def scan(self):
        old=self._state()['files'];now={};changed=[]
        for root in self.roots:
            if not root.exists() or not root.is_dir():continue
            for p in root.rglob('*'):
                try:
                    if not p.is_file() or p.is_symlink() or p.suffix.lower() not in self.extensions:continue
                    st=p.stat()
                except OSError:continue
                if st.st_size>self.max_bytes:continue
                key=str(p);finger=f'{st.st_size}:{st.st_mtime_ns}';now[key]=finger
                if old.get(key)!=finger:
                    try:
                        h=hashlib.sha256()
                        with p.open('rb') as stream:
                            for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
                        changed.append({'path':key,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':h.hexdigest()})
                    except OSError:continue
        self._save({'schema':'voice-agentos.folder-watch.v1','checked_at':time.time(),'files':now});return changed
