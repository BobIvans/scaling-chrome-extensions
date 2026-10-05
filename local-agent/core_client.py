from __future__ import annotations
import hashlib, json, os, subprocess
from pathlib import Path
from uuid import uuid4

class CoreError(RuntimeError):
    pass

class CoreClient:
    def __init__(self, connection_path):
        self.connection_path=Path(connection_path).expanduser().resolve()
        self.connection=json.loads(self.connection_path.read_text(encoding='utf-8'))
        required={'python_path','adapter_path','profile_path','expected_adapter_sha256'}
        if not required <= self.connection.keys():raise CoreError('MINI_CONNECTION_SCHEMA')
        self.identity=None;self.info=None
    def _verify(self):
        adapter=Path(self.connection['adapter_path']).resolve()
        if not adapter.is_file():raise CoreError('MINI_ADAPTER_MISSING')
        if hashlib.sha256(adapter.read_bytes()).hexdigest()!=self.connection['expected_adapter_sha256']:raise CoreError('MINI_ADAPTER_CHANGED')
    def _raw(self, request, timeout=130):
        self._verify();raw=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode()
        if len(raw)>16000:raise CoreError('MINI_INPUT_LIMIT')
        argv=[self.connection['python_path'],'-I','-X','utf8',self.connection['adapter_path'],'--profile',self.connection['profile_path'],'--desktop-stdio']
        kwargs=dict(input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(Path(self.connection['adapter_path']).parent),timeout=timeout,shell=False)
        if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
        try:r=subprocess.run(argv,**kwargs)
        except (OSError,subprocess.TimeoutExpired) as exc:raise CoreError('MINI_CORE_UNAVAILABLE') from exc
        if r.returncode!=0:raise CoreError('MINI_CORE_PROCESS_FAILED')
        try:value=json.loads(r.stdout.decode('utf-8'))
        except Exception as exc:raise CoreError('MINI_CORE_RESPONSE') from exc
        if value.get('schema')!='occ.desktop-stdio-result.v1' or value.get('ok') is not True:raise CoreError(value.get('error','MINI_CORE_REJECTED'))
        return value
    def handshake(self):
        value=self._raw({'type':'durable.info'},20);self.identity=value['adapter_context'];self.info=value['result']['info'];return self.info
    def request(self, request, timeout=130):
        if self.info is None:self.handshake()
        value=self._raw(request,timeout)
        if value.get('adapter_context')!=self.identity:self.identity=self.info=None;raise CoreError('MINI_CORE_IDENTITY_CHANGED')
        return value['result']
    def action(self, action, payload=None):return self.request({'type':'durable.action','action':action,'payload':payload or {}})['action']
    def stop(self):
        if self.info is None:self.handshake()
        caps=set(self.info.get('capabilities',[]))
        if 'durable.stop' in caps:return self.request({'type':'durable.stop','requestId':uuid4().hex})['library']['data']
        if 'durable.action' in caps:return self.action('STOP',{})
        raise CoreError('MINI_STOP_UNAVAILABLE')
    def capture_file(self, path, source_key):
        if self.info is None:self.handshake()
        if 'durable.library' not in set(self.info.get('capabilities',[])):raise CoreError('MINI_LIBRARY_UNAVAILABLE')
        ns=self.connection.get('preferred_namespace') or self.info['namespaces'][0]
        req={'type':'durable.library','namespace':ns,'action':'CAPTURE','arguments':{'path':str(Path(path).resolve()),'source_key':source_key},'operationId':uuid4().hex}
        return self.request(req,130)['library']['data']
    def create_action(self, text, criteria, source_refs=None, command=None, slots=None):
        payload={'text':text,'modality':'TEXT','slots':slots or {},'criteria':criteria or ['Verify requested outcome.'],'source_refs':source_refs or []}
        if command:payload['command']=command
        return self.action('CREATE',payload)
    def enqueue_action(self, intent_id, revision):return self.action('ENQUEUE',{'intent_id':intent_id,'revision':revision})
