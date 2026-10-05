from __future__ import annotations
import json, socket
from pathlib import Path

class BridgeError(RuntimeError):pass
class ChromeBridge:
    def __init__(self,state_file):self.state_file=Path(state_file).expanduser().resolve()
    def state(self):
        try:value=json.loads(self.state_file.read_text(encoding='utf-8'))
        except Exception as exc:raise BridgeError('CHROME_BRIDGE_OFFLINE') from exc
        if value.get('schema')!='occ.agentos-local-control.v1' or value.get('host')!='127.0.0.1' or not isinstance(value.get('port'),int) or not isinstance(value.get('token'),str):raise BridgeError('CHROME_BRIDGE_STATE')
        return value
    def request(self,command,args=None,timeout=35):
        state=self.state();payload=json.dumps({'token':state['token'],'command':command,'args':args or {}},separators=(',',':')).encode()+b'\n'
        try:
            with socket.create_connection((state['host'],state['port']),timeout=5) as sock:
                sock.settimeout(timeout);sock.sendall(payload);parts=[];total=0
                while True:
                    chunk=sock.recv(65536)
                    if not chunk:break
                    total+=len(chunk)
                    if total>2400000:raise BridgeError('CHROME_BRIDGE_OUTPUT_LIMIT')
                    parts.append(chunk)
                    if b'\n' in chunk:break
        except OSError as exc:raise BridgeError('CHROME_BRIDGE_OFFLINE') from exc
        try:value=json.loads(b''.join(parts).split(b'\n',1)[0].decode())
        except Exception as exc:raise BridgeError('CHROME_BRIDGE_RESPONSE') from exc
        if value.get('ok') is not True:raise BridgeError(value.get('error','CHROME_BRIDGE_FAILED'))
        return value.get('result')
    def request_stream(self,command,args=None,on_chunk=None,timeout=260):
        state=self.state();payload=json.dumps({'token':state['token'],'command':command,'args':args or {}},separators=(',',':')).encode()+b'\n'
        try:
            with socket.create_connection((state['host'],state['port']),timeout=5) as sock:
                sock.settimeout(timeout);sock.sendall(payload);buffer=b''
                while True:
                    chunk=sock.recv(65536)
                    if not chunk:
                        if buffer.strip():raise BridgeError('CHROME_BRIDGE_STREAM_TRUNCATED')
                        raise BridgeError('CHROME_BRIDGE_STREAM_CLOSED')
                    buffer+=chunk
                    if len(buffer)>4800000:raise BridgeError('CHROME_BRIDGE_STREAM_FRAME_LIMIT')
                    while b'\n' in buffer:
                        raw,buffer=buffer.split(b'\n',1)
                        if not raw:continue
                        try:value=json.loads(raw.decode())
                        except Exception as exc:raise BridgeError('CHROME_BRIDGE_STREAM_RESPONSE') from exc
                        if value.get('event')=='chunk':
                            if on_chunk:on_chunk(value.get('chunk'))
                            continue
                        if value.get('event')=='result' or 'ok' in value:
                            if value.get('ok') is not True:raise BridgeError(value.get('error','CHROME_BRIDGE_FAILED'))
                            return value.get('result')
                        raise BridgeError('CHROME_BRIDGE_STREAM_SCHEMA')
        except OSError as exc:raise BridgeError('CHROME_BRIDGE_OFFLINE') from exc
    def active_tab(self):return self.request('tabs.active')
    def list_tabs(self):return self.request('tabs.list')
    def start_capture(self,tab_id=None):return self.request('tab.capture.start',{} if tab_id is None else {'tabId':tab_id},40)
    def get_capture(self,tab_id=None):return self.request('capture.get',{} if tab_id is None else {'tabId':tab_id},10)
    def capture_archive(self,tab_id=None,on_chunk=None,max_bytes=67108864,max_steps=3000,max_ms=120000,respect_human_lease=True,human_quiet_ms=1800):
        args={'maxBytes':int(max_bytes),'maxSteps':int(max_steps),'maxMs':int(max_ms),
              'respectHumanLease':bool(respect_human_lease),'humanQuietMs':int(human_quiet_ms)}
        if tab_id is not None:args['tabId']=int(tab_id)
        return self.request_stream('tab.capture.archive',args,on_chunk=on_chunk,timeout=max(180,int(max_ms/1000)+60))
    def ui_inventory(self,tab_id=None):
        args={} if tab_id is None else {'tabId':int(tab_id)}
        return self.request('browser.ui.inventory',args,20)
    def ui_act(self,request,tab_id=None):
        args={'request':request}
        if tab_id is not None:args['tabId']=int(tab_id)
        return self.request('browser.ui.act',args,30)
    def codex_submit(self,instruction,text,mode='analyze'):return self.request('system2.codex.submit',{'instruction':instruction,'text':text,'mode':mode},45)
    def codex_status(self,job_id):return self.request('system2.codex.status',{'jobId':job_id},10)
    def codex_result(self,job_id):return self.request('system2.codex.result',{'jobId':job_id},45)
    def codex_artifacts(self,job_id):return self.request('system2.codex.artifacts',{'jobId':job_id},20)
    def codex_artifact(self,job_id,artifact_id):return self.request('system2.codex.artifact',{'jobId':job_id,'artifactId':artifact_id},45)
