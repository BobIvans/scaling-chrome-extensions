from __future__ import annotations
import ctypes,hashlib,json,os,re,subprocess,time
from pathlib import Path
from uuid import uuid4

DANGER=re.compile(r'\b(delete|remove|erase|destroy|pay|purchase|buy|checkout|merge|logout|log out|sign out|transfer|withdraw|deposit|swap|send funds|connect wallet|approve token|authorize|grant permission|revoke|close account|cancel subscription)\b',re.I)
WRITE=re.compile(r'\b(send|submit|save|post|publish|comment|reply|create|apply|upload|attach|confirm|accept|join|follow|like|edit|rename)\b',re.I)
READ=re.compile(r'\b(show more|load more|more|expand|collapse|open|view|details|next|previous|older|newer|continue reading|read more|download|refresh)\b',re.I)

class WindowsUIError(RuntimeError):pass

def _digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:24]

def _risk(row):
    text=' '.join(str(row.get(x) or '') for x in ('name','automation_id','class_name','control_type','value'))[:4000]
    if DANGER.search(text):return 'DANGEROUS'
    if WRITE.search(text):return 'WRITE'
    if READ.search(text):return 'READ_NAV'
    patterns=set(row.get('patterns') or [])
    ctype=str(row.get('control_type') or '')
    if 'Value' in patterns or 'Edit' in ctype:return 'INPUT'
    if 'Invoke' in patterns or 'ExpandCollapse' in patterns:return 'UNKNOWN'
    return 'READ_ONLY'

class WindowsUIBroker:
    def __init__(self,script_path,powershell='powershell.exe',runner=subprocess.run,human_quiet_ms=1800):
        self.script=Path(script_path).resolve();self.powershell=powershell;self.runner=runner;self.snapshots={}
        self.human_quiet_ms=max(500,min(10000,int(human_quiet_ms)))
        if not self.script.is_file():raise WindowsUIError('WINDOWS_UI_SCRIPT_MISSING')

    def _last_input_age_ms(self):
        if os.name!='nt':return float('inf')
        class LASTINPUTINFO(ctypes.Structure):
            _fields_=[('cbSize',ctypes.c_uint),('dwTime',ctypes.c_uint)]
        info=LASTINPUTINFO();info.cbSize=ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):return float('inf')
        now=ctypes.windll.kernel32.GetTickCount()
        return int((now-info.dwTime)&0xffffffff)

    def _call(self,mode,request,timeout=30):
        argv=[self.powershell,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(self.script),'-Mode',mode,'-RequestJson',json.dumps(request,ensure_ascii=False,separators=(',',':'))]
        kwargs=dict(stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,shell=False)
        if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
        try:r=self.runner(argv,**kwargs)
        except (OSError,subprocess.TimeoutExpired) as exc:raise WindowsUIError('WINDOWS_UI_PROCESS_FAILED') from exc
        try:value=json.loads(r.stdout.strip().splitlines()[-1])
        except Exception as exc:raise WindowsUIError('WINDOWS_UI_RESPONSE') from exc
        if value.get('ok') is not True:raise WindowsUIError(value.get('error','WINDOWS_UI_FAILED'))
        return value

    def _normalize(self,row,index):
        value={k:row.get(k) for k in ('runtime_id','hwnd','process_id','control_type','name','automation_id','class_name','enabled','offscreen','is_password','rect','patterns','value','text')}
        value['element_id']='w'+str(index);value['risk']=_risk(value)
        value['fingerprint']=_digest([value['runtime_id'],value['hwnd'],value['process_id'],value['control_type'],value['name'],value['automation_id'],value['class_name'],value['rect']])
        return value

    def inventory(self,hwnd=None,max_elements=1200):
        req={'max_elements':max(1,min(3000,int(max_elements)))}
        if hwnd is not None:req['hwnd']=int(hwnd)
        raw=self._call('Inventory',req,45);elements=[self._normalize(row,i+1) for i,row in enumerate(raw.get('elements') or []) if isinstance(row,dict)]
        snapshot_id=uuid4().hex
        snap={'schema':'voice-agentos.windows-ui-snapshot.v1','snapshot_id':snapshot_id,'hwnd':raw.get('hwnd'),'created_at':time.time(),'elements':elements}
        self.snapshots[snapshot_id]=snap
        while len(self.snapshots)>4:self.snapshots.pop(next(iter(self.snapshots)))
        return snap

    def act(self,request):
        if not isinstance(request,dict):raise WindowsUIError('WINDOWS_UI_ACTION_SCHEMA')
        snap=self.snapshots.get(request.get('snapshot_id'))
        if not snap:raise WindowsUIError('WINDOWS_UI_SNAPSHOT_STALE')
        candidates={x['element_id']:x for x in snap['elements']};bound=candidates.get(request.get('element_id'))
        if not bound or bound['fingerprint']!=request.get('expected_fingerprint'):raise WindowsUIError('WINDOWS_UI_BINDING_STALE')
        current=self.inventory(hwnd=snap['hwnd'])
        now=next((x for x in current['elements'] if x['runtime_id']==bound['runtime_id']),None)
        if not now or now['fingerprint']!=bound['fingerprint']:raise WindowsUIError('WINDOWS_UI_ELEMENT_DRIFT')
        action=request.get('action')
        if action in {'invoke','expand','set_value'} and self._last_input_age_ms()<self.human_quiet_ms:
            raise WindowsUIError('WINDOWS_UI_HUMAN_FOREGROUND_LEASE')
        if action in {'invoke','expand'}:
            if request.get('effect_class')!='WINDOWS_WRITE':raise WindowsUIError('WINDOWS_UI_EFFECT_GRANT_REQUIRED')
            if now['risk']!='READ_NAV':raise WindowsUIError('WINDOWS_UI_GENERIC_INVOKE_REQUIRES_QUALIFIED_ADAPTER')
        elif action=='scroll_into_view':
            if request.get('effect_class')!='READ':raise WindowsUIError('WINDOWS_UI_EFFECT_GRANT_REQUIRED')
        elif action=='set_value':
            if request.get('effect_class')!='WINDOWS_WRITE':raise WindowsUIError('WINDOWS_UI_EFFECT_GRANT_REQUIRED')
            if now['risk'] not in {'INPUT','READ_ONLY'} or now.get('is_password'):raise WindowsUIError('WINDOWS_UI_GENERIC_INPUT_BLOCKED')
        else:raise WindowsUIError('WINDOWS_UI_ACTION_UNSUPPORTED')
        expected={k:now.get(k) for k in ('process_id','control_type','automation_id','class_name','name')}
        payload={'hwnd':snap['hwnd'],'runtime_id':now['runtime_id'],'expected':expected,'action':action}
        if action=='set_value':payload['value']=str(request.get('value',''))
        return self._call('Act',payload,30)

    def text_snapshot(self,inventory=None,max_chars=1500000):
        snap=inventory or self.inventory();rows=[];total=0;seen=set()
        for el in snap['elements']:
            pieces=[]
            for key in ('name','value','text'):
                value=str(el.get(key) or '').strip()
                if value and value not in seen:seen.add(value);pieces.append(value)
            if not pieces:continue
            text='\n'.join(pieces);size=len(text.encode('utf-8'))
            if total+size>max_chars:break
            total+=size;rows.append('['+str(el.get('control_type'))+' '+str(el.get('risk'))+']\n'+text)
        return {'snapshot':snap,'text':'\n\n'.join(rows),'bytes':total}
