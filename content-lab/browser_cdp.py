"""Optional selected Chrome DOM adapter, configured and qualified by operator.

No Grok selectors, API endpoints or upload support are invented. A local CDP
endpoint and measured semantic selectors are explicitly selected in policy.
Unknown identity/history keeps send disabled or uncertain. This text-only route
does not pretend that a local path is an uploaded binary attachment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler

from automation_core import digest
from action_intent import exact, text


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*_args,**_kwargs):
        raise ValueError('ACTION_CDP_REDIRECT_REFUSED')


class CDP:
    def __init__(self, endpoint):
        parsed=urlsplit(endpoint)
        if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.path not in {'','/'} or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('ACTION_LOCAL_CDP_ENDPOINT_REQUIRED')
        self.endpoint=endpoint.rstrip('/')
        self.port=parsed.port
        self.opener=build_opener(ProxyHandler({}),NoRedirect())

    def get(self,path):
        with self.opener.open(self.endpoint+path,timeout=5) as response:
            raw=response.read(1_000_001)
        if len(raw)>1_000_000:
            raise ValueError('ACTION_CDP_FRAME_LIMIT')
        return json.loads(raw)

    def evaluate(self,handle,expression):
        target=next((t for t in self.get('/json/list') if t.get('id')==handle and t.get('type')=='page'),None)
        if target is None:
            raise ValueError('ACTION_TARGET_REBIND_REQUIRED')
        ws_url=target.get('webSocketDebuggerUrl','')
        parsed=urlsplit(ws_url)
        if parsed.scheme!='ws' or parsed.hostname!='127.0.0.1' or parsed.port!=self.port:
            raise ValueError('ACTION_CDP_TARGET_SOCKET')
        try:
            import websocket
        except ImportError as exc:
            raise ValueError('ACTION_CDP_WEBSOCKET_UNAVAILABLE') from exc
        # No proxy and no cross-host websocket; this connection is local only.
        with websocket.create_connection(ws_url,timeout=5,suppress_origin=True,http_proxy_host=None) as sock:
            sock.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':expression,'returnByValue':True,'awaitPromise':True}}))
            while True:
                raw=sock.recv()
                if len(raw)>1_000_000:
                    raise ValueError('ACTION_CDP_FRAME_LIMIT')
                message=json.loads(raw)
                if message.get('id')!=1:
                    continue
                if message.get('error') or message.get('result',{}).get('exceptionDetails'):
                    raise ValueError('ACTION_CDP_EVALUATION_FAILED')
                return message['result']['result'].get('value')


class BrowserAdapter:
    version='cdp-semantic-text.v1'

    def __init__(self,config,transport=None):
        exact(config,{'endpoint','origin','selectors','max_text_bytes'}, {'qualification'})
        parsed=urlsplit(config['origin'])
        if parsed.scheme!='https' or not parsed.hostname or parsed.path not in {'','/'} or parsed.query or parsed.fragment:
            raise ValueError('ACTION_BROWSER_ORIGIN_REQUIRED')
        exact(config['selectors'],{'account','workspace','composer','send','outgoing','response'})
        if type(config['max_text_bytes']) is not int or config['max_text_bytes']<1:
            raise ValueError('ACTION_PROVIDER_LIMIT_REQUIRED')
        for value in config['selectors'].values():
            text(value)
        self.config=config
        self.transport=transport or CDP(config['endpoint'])
        self.contract_digest=digest({k:v for k,v in config.items() if k!='qualification'})

    def require_qualified(self):
        receipt=self.config.get('qualification')
        exact(receipt,{'scope','status','adapter_version','code_digest','contract_digest','environment_digest','evidence_refs'})
        actual=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if (receipt['scope']!='SELECTED_UI' or receipt['status']!='PASS' or receipt['adapter_version']!=self.version or
                receipt['code_digest']!=actual or receipt['contract_digest']!=self.contract_digest or
                receipt['environment_digest']!=self.environment_digest() or not receipt['evidence_refs']):
            raise ValueError('ACTION_BROWSER_QUALIFICATION_REQUIRED')

    def environment_digest(self):
        version=self.transport.get('/json/version')
        # A restart changes the socket ID, not the installed browser contract.
        return digest({k:version.get(k) for k in ['Browser','Protocol-Version','User-Agent','V8-Version','WebKit-Version']})

    def _eval(self,handle,body,argument=None):
        # Only this installed module supplies executable JS. Configuration
        # selectors and prompt data are quoted as JSON, never string-executed.
        expression='((cfg,arg)=>{'+body+'})('+json.dumps(self.config['selectors'])+','+json.dumps(argument,ensure_ascii=True)+')'
        value=self.transport.evaluate(handle,expression)
        if isinstance(value,dict) and value.get('error'):
            raise ValueError(value['error'])
        return value

    def observe(self,handle):
        value=self._eval(handle,"""
          const pick=s=>{const a=document.querySelectorAll(s);return a.length===1?a[0].textContent.trim():null;};
          return {origin:location.origin,account:pick(cfg.account),workspace:pick(cfg.workspace),
                  conversation:location.href,focused:document.hasFocus(),contract_digest:arg};
        """,self.contract_digest)
        if not isinstance(value,dict) or value.get('origin')!=self.config['origin'].rstrip('/'):
            raise ValueError('ACTION_TARGET_ORIGIN_MISMATCH')
        return value

    def canary(self,handle):
        value=self._eval(handle,"""
          const c=document.querySelectorAll(cfg.composer),s=document.querySelectorAll(cfg.send);
          if(c.length!==1||s.length!==1)return {error:'ACTION_ADAPTER_STALE'};
          if(!document.hasFocus())return {error:'ACTION_USER_TAKEOVER'};
          const t=c[0];if(!(t instanceof HTMLTextAreaElement || t instanceof HTMLInputElement || t.isContentEditable))return {error:'ACTION_INPUT_UNSUPPORTED'};
          if(!t.getClientRects().length || !s[0].getClientRects().length)return {error:'ACTION_ADAPTER_STALE'};
          return {state:'CANARY_OK',upload:'UNSUPPORTED',route:'TEXT_COMPOSER'};
        """)
        return value

    def prepare(self,handle,prompt):
        self.require_qualified()
        self.canary(handle)
        rendered=json.dumps(prompt,ensure_ascii=False,sort_keys=True)
        if len(rendered.encode('utf-8'))>self.config['max_text_bytes']:
            raise ValueError('ACTION_PROVIDER_PART_LIMIT')
        return self._eval(handle,"""
          const el=document.querySelector(cfg.composer);const current=('value' in el?el.value:el.textContent)||'';
          if(current && current!==arg)return {error:'ACTION_DRAFT_CONFLICT'};
          if('value' in el){const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
            Object.getOwnPropertyDescriptor(proto,'value').set.call(el,arg);
          }else{el.textContent=arg;}
          el.dispatchEvent(new Event('input',{bubbles:true}));
          const actual='value' in el?el.value:el.textContent;
          return actual===arg?{state:'DRAFT_ATTACHED',evidence_kind:'UI_OBSERVED_TEXT'}:{error:'ACTION_DRAFT_MISMATCH'};
        """,rendered)

    def send(self,handle,prompt):
        self.require_qualified()
        rendered=json.dumps(prompt,ensure_ascii=False,sort_keys=True)
        self.canary(handle)
        return self._eval(handle,"""
          const el=document.querySelector(cfg.composer),button=document.querySelector(cfg.send);
          if(('value' in el?el.value:el.textContent)!==arg)return {error:'ACTION_DRAFT_MISMATCH'};
          if(button.disabled||button.getAttribute('aria-disabled')==='true')return {error:'ACTION_SEND_UNAVAILABLE'};
          button.click();return {state:'SEND_INVOKED',remote_effect:'UNKNOWN'};
        """,rendered)

    def reconcile(self,handle,prompt):
        self.require_qualified()
        rendered=json.dumps(prompt,ensure_ascii=False,sort_keys=True)
        return self._eval(handle,"""
          const matches=[...document.querySelectorAll(cfg.outgoing)].filter(x=>x.textContent.trim()===arg);
          if(matches.length>1)return {state:'CONFLICT',matches:matches.length,evidence_kind:'UI_OBSERVED'};
          if(matches.length===1)return {state:'MESSAGE_OBSERVED',evidence_kind:'UI_OBSERVED',message_id:matches[0].getAttribute('data-message-id')};
          return {state:'EFFECT_UNKNOWN',reason:'HISTORY_MATCH_UNAVAILABLE',history_complete:false};
        """,rendered)

    def read_result(self,handle):
        self.require_qualified()
        return self._eval(handle,"""
          const rows=[...document.querySelectorAll(cfg.response)];
          return rows.map(x=>({text:x.textContent,message_id:x.getAttribute('data-message-id'),
                              finalized:x.getAttribute('data-finalized')==='true'}));
        """)
