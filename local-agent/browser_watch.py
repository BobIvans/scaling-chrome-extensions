from __future__ import annotations
import hashlib, inspect, json, os, re, time
from pathlib import Path
from urllib.parse import urlparse

from browser_archive import BrowserArchiveAssembler

class BrowserWatchError(RuntimeError):
    pass

def _host(url):
    try:return (urlparse(str(url)).hostname or '').lower()
    except Exception:return ''

class BrowserWatch:
    """Scheduled local-app browser context ingestion.

    The extension is only a hidden transport. Canonical persistence remains in Core.
    """
    def __init__(self,bridge,core,config,state_file,inbox_root):
        self.bridge=bridge;self.core=core;self.c=config or {}
        self.state_file=Path(state_file).expanduser().resolve();self.root=Path(inbox_root).expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True);self._validate()

    @property
    def enabled(self):return self.c.get('enabled') is True

    def _validate(self):
        if not self.enabled:return
        hosts=self.c.get('include_hosts',[])
        if not isinstance(hosts,list) or not all(isinstance(x,str) and x for x in hosts):raise BrowserWatchError('BROWSER_WATCH_HOSTS')
        if int(self.c.get('max_tabs_per_cycle',4)) not in range(1,21):raise BrowserWatchError('BROWSER_WATCH_MAX_TABS')

    def _state(self):
        if not self.state_file.exists():return {'schema':'voice-agentos.browser-watch.v1','captures':{}}
        try:value=json.loads(self.state_file.read_text(encoding='utf-8'))
        except Exception:return {'schema':'voice-agentos.browser-watch.v1','captures':{}}
        return value if value.get('schema')=='voice-agentos.browser-watch.v1' and isinstance(value.get('captures'),dict) else {'schema':'voice-agentos.browser-watch.v1','captures':{}}

    def _save(self,value):
        self.state_file.parent.mkdir(parents=True,exist_ok=True);tmp=self.state_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,self.state_file)

    def _allowed(self,tab):
        url=str(tab.get('url') or '')
        if not url.startswith(('http://','https://')):return False
        hosts=[x.lower().lstrip('.') for x in self.c.get('include_hosts',[])]
        host=_host(url)
        if hosts and not any(host==x or host.endswith('.'+x) for x in hosts):return False
        excludes=self.c.get('exclude_hosts',[])
        if any(host==x.lower().lstrip('.') or host.endswith('.'+x.lower().lstrip('.')) for x in excludes if isinstance(x,str)):return False
        pattern=self.c.get('title_regex')
        if pattern and not re.search(pattern,str(tab.get('title') or ''),re.I):return False
        return True

    def _capture(self,tab):
        stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
        assembler=BrowserArchiveAssembler(self.root/'browser-watch','watch_'+str(tab['id'])+'_'+stamp)
        try:
            capture=self.bridge.capture_archive
            kwargs={'on_chunk':assembler.add_chunk,
                    'max_bytes':int(self.c.get('max_bytes',67108864)),
                    'max_steps':int(self.c.get('max_steps',2500)),
                    'max_ms':int(self.c.get('max_ms',90000))}
            try:
                params=inspect.signature(capture).parameters
            except (TypeError,ValueError):
                params={}
            supports_kwargs=any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
            if supports_kwargs or 'respect_human_lease' in params:
                kwargs['respect_human_lease']=True
            if supports_kwargs or 'human_quiet_ms' in params:
                kwargs['human_quiet_ms']=int(self.c.get('human_quiet_ms',1800))
            manifest=capture(tab['id'],**kwargs)
            return assembler.finalize(manifest)
        except Exception as exc:
            assembler.abort(str(exc));raise

    def poll_once(self,emit_existing=False):
        if not self.enabled:return {'schema':'voice-agentos.browser-watch-poll.v1','results':[]}
        state=self._state();old=state['captures'];next_state=dict(old);results=[]
        tabs=[t for t in self.bridge.list_tabs() if isinstance(t,dict) and isinstance(t.get('id'),int) and self._allowed(t)]
        tabs=sorted(tabs,key=lambda t:(not bool(t.get('active')),int(t['id'])))[:int(self.c.get('max_tabs_per_cycle',4))]
        for tab in tabs:
            binding=hashlib.sha256((str(tab.get('url'))+'\0'+str(tab.get('title'))).encode()).hexdigest()
            try:archive=self._capture(tab)
            except Exception as exc:
                results.append({'state':'BLOCKED','tab':{'id':tab['id'],'url':tab.get('url'),'title':tab.get('title')},'reason':str(exc)});continue
            digest=archive['txt_sha256']
            if old.get(binding)==digest and not emit_existing:
                for key in ('txt_path','metadata_path','raw_stream_path'):
                    try:Path(archive[key]).unlink(missing_ok=True)
                    except Exception:pass
                results.append({'state':'UNCHANGED','tab':{'id':tab['id'],'url':tab.get('url'),'title':tab.get('title')},'sha256':digest})
                continue
            receipts=[]
            try:
                for field,prefix in [('txt_path','browser_watch_txt'),('metadata_path','browser_watch_meta'),('raw_stream_path','browser_watch_stream')]:
                    path=archive[field];raw_hash=hashlib.sha256(Path(path).read_bytes()).hexdigest()
                    receipt=self.core.capture_file(path,prefix+'_'+raw_hash[:18]);receipts.append(receipt)
                    try:self.core.annotate_capture(receipt,project='BrowserWatch',note='scheduled browser observation '+str(tab.get('url')),labels=['source:browser-watch','type:web-context','status:'+str(archive.get('status') or 'unknown').lower()])
                    except Exception:pass
                next_state[binding]=digest
                results.append({'state':'CAPTURED','tab':{'id':tab['id'],'url':tab.get('url'),'title':tab.get('title')},
                                'archive':archive,'library_receipts':receipts})
            except Exception as exc:
                results.append({'state':'LIBRARY_BLOCKED','tab':{'id':tab['id'],'url':tab.get('url'),'title':tab.get('title')},
                                'archive':archive,'reason':str(exc)})
        self._save({'schema':'voice-agentos.browser-watch.v1','checked_at':time.time(),'captures':next_state})
        return {'schema':'voice-agentos.browser-watch-poll.v1','checked_at':time.time(),'results':results}
