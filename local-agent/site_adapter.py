from __future__ import annotations
import hashlib,json,os,re,time,uuid
from pathlib import Path
from urllib.parse import urlsplit

HEX=re.compile(r'^[0-9a-f]{64}$')
ID=re.compile(r'^[A-Za-z0-9_.-]{1,80}$')
ADAPTER_VERSION='browser-site-text.v1'

class SiteAdapterError(RuntimeError):pass

def _digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class SiteAdapterRegistry:
    """Local policy for effectful AI-site adapters. Unknown sites remain observe-only."""
    def __init__(self,config):
        self.c=config or {}
        if self.c.get('enabled') is True:self._validate()
    @property
    def enabled(self):return self.c.get('enabled') is True
    def _validate(self):
        profiles=self.c.get('profiles')
        if not isinstance(profiles,dict) or len(profiles)>100:raise SiteAdapterError('SITE_REGISTRY_SCHEMA')
        for key,row in profiles.items():
            if not ID.fullmatch(str(key)) or not isinstance(row,dict):raise SiteAdapterError('SITE_PROFILE_SCHEMA')
            required={'origin','selectors','max_text_bytes','qualification'}
            if set(row)!=required:raise SiteAdapterError('SITE_PROFILE_SCHEMA')
            if not isinstance(row['origin'],str):
                raise SiteAdapterError('SITE_ORIGIN_SCHEMA')
            parsed=urlsplit(row['origin'])
            if parsed.scheme!='https' or not parsed.hostname or parsed.path not in {'','/'} or parsed.query or parsed.fragment or parsed.username or parsed.password:
                raise SiteAdapterError('SITE_ORIGIN_SCHEMA')
            selectors=row['selectors']
            if not isinstance(selectors,dict) or set(selectors)!={'account','workspace','conversation','composer','send','outgoing','response','response_final'}:raise SiteAdapterError('SITE_SELECTORS_SCHEMA')
            for name,value in selectors.items():
                if name in {'conversation','response_final'} and value is None:continue
                if not isinstance(value,str) or not value or len(value)>500:raise SiteAdapterError('SITE_SELECTORS_SCHEMA')
            if not isinstance(row['max_text_bytes'],int) or not 1<=row['max_text_bytes']<=2000000:raise SiteAdapterError('SITE_TEXT_LIMIT')
            q=row['qualification']
            if q is not None:
                if not isinstance(q,dict) or set(q)!={'status','adapter_version','code_digest','contract_digest','evidence_refs'}:raise SiteAdapterError('SITE_QUALIFICATION_SCHEMA')
                if q['status']!='PASS' or q['adapter_version']!=ADAPTER_VERSION or not HEX.fullmatch(str(q['code_digest'])) or not HEX.fullmatch(str(q['contract_digest'])) or not isinstance(q['evidence_refs'],list) or not q['evidence_refs']:
                    raise SiteAdapterError('SITE_QUALIFICATION_SCHEMA')
    def profile(self,profile_id,require_qualified=False):
        if not self.enabled:raise SiteAdapterError('SITE_REGISTRY_DISABLED')
        if not ID.fullmatch(str(profile_id)):raise SiteAdapterError('SITE_PROFILE_ID')
        row=self.c['profiles'].get(profile_id)
        if not isinstance(row,dict):raise SiteAdapterError('SITE_PROFILE_NOT_FOUND')
        contract={'profile_id':profile_id,'origin':row['origin'].rstrip('/'),'selectors':row['selectors'],'max_text_bytes':row['max_text_bytes']}
        digest=_digest(contract);payload={**contract,'contract_digest':digest}
        q=row.get('qualification')
        if require_qualified:
            if not q or q['status']!='PASS' or q['adapter_version']!=ADAPTER_VERSION or q['contract_digest']!=digest:
                raise SiteAdapterError('SITE_QUALIFICATION_REQUIRED')
        return payload,q

class SiteAdapterRuntime:
    def __init__(self,core,bridge,config,root):
        self.core=core;self.bridge=bridge;self.registry=SiteAdapterRegistry(config)
        self.root=Path(root).expanduser().resolve();self.root.mkdir(parents=True,exist_ok=True)
    @property
    def enabled(self):return self.registry.enabled
    def bind(self,profile_id,tab_id=None,require_qualified=False):
        profile,q=self.registry.profile(profile_id,require_qualified=require_qualified)
        result=self.bridge.site_bind(profile,tab_id);binding=result.get('result')
        if not isinstance(binding,dict) or binding.get('state')!='BOUND' or result.get('adapter_version')!=ADAPTER_VERSION or binding.get('adapter_version')!=ADAPTER_VERSION or binding.get('contract_digest')!=profile['contract_digest']:
            raise SiteAdapterError('SITE_BINDING_SCHEMA')
        if require_qualified and (result.get('code_digest')!=q['code_digest'] or profile['contract_digest']!=q['contract_digest']):
            raise SiteAdapterError('SITE_QUALIFICATION_CODE_DRIFT')
        return {'schema':'voice-agentos.site-binding.v1','profile_id':profile_id,'tab_id':result.get('tabId'),
                'adapter_version':ADAPTER_VERSION,'code_digest':result.get('code_digest'),'contract_digest':profile['contract_digest'],
                'binding':binding,'bound_at':time.time()}
    def qualification_probe(self,profile_id,tab_id=None,evidence_refs=None):
        profile,_=self.registry.profile(profile_id,require_qualified=False)
        result=self.bridge.site_bind(profile,tab_id);binding=result.get('result') or {}
        if binding.get('state')!='BOUND':raise SiteAdapterError('SITE_CANARY_FAILED')
        return {'profile_id':profile_id,'binding':binding,'qualification_template':{
            'status':'PASS','adapter_version':ADAPTER_VERSION,'code_digest':result.get('code_digest'),
            'contract_digest':profile['contract_digest'],'evidence_refs':list(evidence_refs or [])}}
    def _qualified(self,site_binding):
        profile,q=self.registry.profile(site_binding['profile_id'],require_qualified=True)
        if site_binding.get('adapter_version')!=ADAPTER_VERSION or site_binding.get('contract_digest')!=q['contract_digest'] or site_binding.get('code_digest')!=q['code_digest']:
            raise SiteAdapterError('SITE_BINDING_QUALIFICATION_DRIFT')
        return profile,q
    def prepare(self,site_binding,draft):
        profile,_=self._qualified(site_binding)
        result=self.bridge.site_prepare(profile,site_binding['binding'],draft,site_binding.get('tab_id'))
        if result.get('code_digest')!=site_binding['code_digest'] or (result.get('result') or {}).get('state')!='DRAFT_PREPARED':
            raise SiteAdapterError('SITE_DRAFT_PREPARE_FAILED')
        return result
    def _outbox(self,operation_id,draft):
        raw=draft.encode('utf-8');sha=hashlib.sha256(raw).hexdigest();path=self.root/(operation_id+'.txt')
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise SiteAdapterError('SITE_OUTBOX_CONFLICT')
        else:
            tmp=path.with_suffix('.tmp');tmp.write_bytes(raw);os.replace(tmp,path)
        return path,sha
    def send_once(self,profile_id,draft,tab_id=None,operation_id=None):
        if not isinstance(draft,str) or not draft:raise SiteAdapterError('SITE_DRAFT_REQUIRED')
        site=self.bind(profile_id,tab_id,require_qualified=True)
        self.prepare(site,draft)
        operation_id=operation_id or uuid.uuid4().hex
        path,draft_sha=self._outbox(operation_id,draft)
        effect_binding={'kind':'AI_SITE_MESSAGE','profile_id':profile_id,'tab_id':site['tab_id'],'adapter_version':ADAPTER_VERSION,
                        'code_digest':site['code_digest'],'contract_digest':site['contract_digest'],'identity':site['binding']['identity'],
                        'site_binding':site['binding'],'draft_sha256':draft_sha,'draft_path':str(path)}
        effect=self.core.effect_begin(operation_id,effect_binding)
        state=effect['value']['state'];revision=effect['revision']
        if state=='OBSERVED':return {'state':'MESSAGE_OBSERVED','operation_id':operation_id,'effect':effect,'site_binding':site,'reused':True}
        if state not in {'INTENT_RECORDED','DISPATCHING','UNKNOWN_EFFECT','NOT_APPLIED'}:
            raise SiteAdapterError('SITE_EFFECT_STATE')
        if state in {'DISPATCHING','UNKNOWN_EFFECT'}:return self.reconcile_operation(operation_id)
        if state=='NOT_APPLIED':
            effect=self.core.effect_transition(operation_id,'DISPATCHING',revision,[]);revision=effect['revision']
        else:
            effect=self.core.effect_transition(operation_id,'DISPATCHING',revision,[]);revision=effect['revision']
        try:self.bridge.site_send(self.registry.profile(profile_id,True)[0],site['binding'],draft,site['tab_id'])
        except Exception:
            return self._finish_reconcile(operation_id,revision,effect_binding,draft)
        return self._finish_reconcile(operation_id,revision,effect_binding,draft)
    def _finish_reconcile(self,operation_id,revision,binding,draft):
        profile,_=self.registry.profile(binding['profile_id'],require_qualified=True)
        result=self.bridge.site_reconcile(profile,binding['site_binding'],draft,binding['tab_id'])
        observation=result.get('result') or {}
        if observation.get('state')=='MESSAGE_OBSERVED':
            evidence=['site-message:'+binding['draft_sha256']]
            effect=self.core.effect_transition(operation_id,'OBSERVED',revision,evidence)
            return {'state':'MESSAGE_OBSERVED','operation_id':operation_id,'observation':observation,'effect':effect,'site_binding':{'schema':'voice-agentos.site-binding.v1','profile_id':binding['profile_id'],'tab_id':binding['tab_id'],'adapter_version':binding['adapter_version'],'code_digest':binding['code_digest'],'contract_digest':binding['contract_digest'],'binding':binding['site_binding']}}
        effect=self.core.effect_transition(operation_id,'UNKNOWN_EFFECT',revision,[])
        return {'state':'EFFECT_UNKNOWN','operation_id':operation_id,'observation':observation,'effect':effect,'site_binding':{'schema':'voice-agentos.site-binding.v1','profile_id':binding['profile_id'],'tab_id':binding['tab_id'],'adapter_version':binding['adapter_version'],'code_digest':binding['code_digest'],'contract_digest':binding['contract_digest'],'binding':binding['site_binding']}}
    def reconcile_operation(self,operation_id):
        effect=self.core.effect_inspect(operation_id);binding=effect['value']['binding'];state=effect['value']['state'];revision=effect['revision']
        if binding.get('kind')!='AI_SITE_MESSAGE':raise SiteAdapterError('SITE_EFFECT_KIND')
        path=Path(binding['draft_path'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=binding['draft_sha256']:raise SiteAdapterError('SITE_OUTBOX_DRIFT')
        draft=path.read_text(encoding='utf-8')
        if state=='OBSERVED':return {'state':'MESSAGE_OBSERVED','operation_id':operation_id,'effect':effect,'reused':True}
        profile,_=self.registry.profile(binding['profile_id'],require_qualified=True)
        result=self.bridge.site_reconcile(profile,binding['site_binding'],draft,binding['tab_id']);observation=result.get('result') or {}
        if observation.get('state')=='MESSAGE_OBSERVED':
            updated=self.core.effect_transition(operation_id,'OBSERVED',revision,['site-message:'+binding['draft_sha256']])
            return {'state':'MESSAGE_OBSERVED','operation_id':operation_id,'observation':observation,'effect':updated}
        if state=='DISPATCHING':
            updated=self.core.effect_transition(operation_id,'UNKNOWN_EFFECT',revision,[])
            return {'state':'EFFECT_UNKNOWN','operation_id':operation_id,'observation':observation,'effect':updated}
        return {'state':'EFFECT_UNKNOWN','operation_id':operation_id,'observation':observation,'effect':effect}
    def read(self,site_binding):
        profile,_=self._qualified(site_binding)
        result=self.bridge.site_read(profile,site_binding['binding'],site_binding.get('tab_id'))
        return result.get('result') or {}
