from __future__ import annotations
import argparse, ctypes, hashlib, json, os, queue, re, subprocess, threading, time
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from browser_archive import BrowserArchiveAssembler
from browser_watch import BrowserWatch
from capability_candidate import CapabilityCandidatePipeline
from control_bridge import ChromeBridge
from core_client import CoreClient
from github_merge_watch import MergeWatcher
from github_capability_pr import GitHubCapabilityPipeline
from laya_client import LayaClient
from laya_supervisor import LayaSupervisor
from life_context_pipeline import LifeContextPipeline
from mission_kernel import MissionKernel
from self_renew import VerifiedRenewal
from windows_uia import WindowsUIBroker

CAPTURE_MARKER='BEGIN CAPTURED SOURCE TEXT'
SOURCE_RE=re.compile(r'^SOURCE:\s*(.+)$',re.M)

def expand(value):
    return os.path.expandvars(os.path.expanduser(str(value)))

def load_settings(path):
    value=json.loads(Path(path).read_text(encoding='utf-8'))
    if value.get('schema')!='voice-agentos.mini-settings.v1':raise ValueError('MINI_SETTINGS_SCHEMA')
    return value

def press_capture_hotkey(keys):
    if os.name!='nt':raise RuntimeError('WINDOWS_HOTKEY_REQUIRED')
    codes={'ALT':0x12,'SHIFT':0x10,'CTRL':0x11,'C':0x43}
    values=[codes[x.upper()] for x in keys]
    user32=ctypes.windll.user32
    for code in values:user32.keybd_event(code,0,0,0)
    for code in reversed(values):user32.keybd_event(code,0,2,0)

class Mini:
    def __init__(self,root,settings_path):
        self.root=root;self.settings_path=Path(settings_path).resolve();self.settings=load_settings(self.settings_path)
        self.events=queue.Queue();self.context=None;self.context_file=None;self.context_sha256=None;self.context_metadata=None;self.core=None;self.bridge=None;self.laya=None;self.laya_supervisor=None;self.kernel=None;self.life=None;self.browser_watch=None;self.windows_ui=None;self.candidate_pipeline=None;self.github_pipeline=None;self.shutdown_event=threading.Event();self.mission_cancel=threading.Event()
        self.panel=None;self.details=None;self.current_goal=None
        self._configure_window();self._build();self._init_clients();self._start_watchers();self.root.after(150,self._drain)

    def _configure_window(self):
        r=self.root;r.title('Voice AgentOS Mini');r.attributes('-topmost',True)
        try:r.attributes('-alpha',0.91)
        except tk.TclError:pass
        r.overrideredirect(True);r.configure(bg='#10151d')
        r.update_idletasks();width,height=342,70
        x=max(0,r.winfo_screenwidth()-width-18);y=max(0,r.winfo_screenheight()-height-72)
        r.geometry(f'{width}x{height}+{x}+{y}')
        r.bind('<ButtonPress-1>',self._drag_start);r.bind('<B1-Motion>',self._drag)

    def _drag_start(self,e):self._dx=e.x;self._dy=e.y
    def _drag(self,e):self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

    def _build(self):
        frame=tk.Frame(self.root,bg='#10151d',padx=7,pady=7);frame.pack(fill='both',expand=True)
        style={'font':('Segoe UI',9,'bold'),'bd':0,'padx':8,'pady':6}
        tk.Button(frame,text='Observe',command=self.observe,bg='#24415f',fg='white',**style).pack(side='left',padx=3)
        tk.Button(frame,text='Automate+',command=self.open_automate,bg='#315e8f',fg='white',**style).pack(side='left',padx=3)
        tk.Button(frame,text='STOP',command=self.stop,bg='#762f3d',fg='white',**style).pack(side='left',padx=3)
        self.status=tk.StringVar(value='Ready · local controller')
        tk.Label(frame,textvariable=self.status,bg='#10151d',fg='#a9b8c9',font=('Segoe UI',8),anchor='w').pack(side='left',fill='x',expand=True,padx=(6,0))

    def _init_clients(self):
        try:
            self.core=CoreClient(expand(self.settings['connection_path']));info=self.core.handshake()
            self.status.set('Core ready · '+str(len(info.get('capabilities',[])))+' capabilities')
        except Exception as exc:self.status.set('Core offline · '+str(exc))
        try:
            self.bridge=ChromeBridge(expand(self.settings['chrome_control_state']));self.bridge.request('ping')
        except Exception:self.bridge=None
        runtime=self.settings.get('laya_runtime') or {}
        endpoint=self.settings.get('laya_endpoint','')
        if runtime.get('enabled'):
            try:
                cfg=dict(runtime);cfg['python_path']=expand(cfg['python_path'])
                self.laya_supervisor=LayaSupervisor(cfg)
                ready=self.laya_supervisor.ensure();endpoint=ready.get('endpoint') or endpoint
                self.status.set('Laya ready · '+str((ready.get('health') or {}).get('device','local')))
                if runtime.get('benchmark_on_start'):
                    bench_client=LayaClient(endpoint,api_key_env=runtime.get('api_key_env',''),model=runtime.get('default_model'))
                    receipt=self.laya_supervisor.benchmark(bench_client,int(runtime.get('benchmark_rounds',3)))
                    path=Path(expand(self.settings['inbox_root']))/'laya-benchmark.json';path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
                    if self.core:
                        try:self.core.capture_file(path,'laya_benchmark_'+hashlib.sha256(path.read_bytes()).hexdigest()[:16])
                        except Exception:pass
            except Exception as exc:self.events.put(('log','Pinned Laya unavailable: '+str(exc)))
        self.laya=LayaClient(endpoint,api_key_env=runtime.get('api_key_env',''),model=runtime.get('default_model')) if endpoint else None
        if self.core:
            try:self._restore_active_goal()
            except Exception as exc:self.events.put(('log','Goal restore blocked: '+str(exc)))
            win_cfg=self.settings.get('windows_ui') or {}
            if os.name=='nt' and win_cfg.get('enabled',True):
                try:self.windows_ui=WindowsUIBroker(Path(__file__).parent/'windows_uia.ps1',powershell=win_cfg.get('powershell','powershell.exe'),human_quiet_ms=int(win_cfg.get('human_quiet_ms',1800)))
                except Exception as exc:self.events.put(('log','Windows UIA disabled: '+str(exc)))
            cg=self.settings.get('capability_growth') or {}
            if self.bridge and cg.get('enabled'):
                try:self.candidate_pipeline=CapabilityCandidatePipeline(self.bridge,cg,Path(expand(self.settings['inbox_root']))/'capability-candidates')
                except Exception as exc:self.events.put(('log','Capability growth disabled: '+str(exc)))
            gp=self.settings.get('capability_pr') or {}
            if gp.get('enabled'):
                try:self.github_pipeline=GitHubCapabilityPipeline(gp)
                except Exception as exc:self.events.put(('log','Capability PR pipeline disabled: '+str(exc)))
            self.kernel=MissionKernel(self.core,self.bridge,self.laya,Path(__file__).parent/'laya_questions.json',
                expand(self.settings['inbox_root']),windows_ui=self.windows_ui,candidate_pipeline=self.candidate_pipeline,
                github_pipeline=self.github_pipeline)
            try:self.life=LifeContextPipeline(self.core,self.settings,expand(self.settings['inbox_root']))
            except Exception as exc:self.events.put(('log','LifeContext disabled: '+str(exc)))
            try:
                bw=self.settings.get('browser_watch') or {}
                if self.bridge and bw.get('enabled'):
                    self.browser_watch=BrowserWatch(self.bridge,self.core,bw,
                        Path(expand(self.settings['inbox_root']))/'browser-watch-state.json',
                        expand(self.settings['inbox_root']))
            except Exception as exc:self.events.put(('log','BrowserWatch disabled: '+str(exc)))

    def _goal_pointer_path(self):
        root=Path(expand(self.settings['inbox_root']));root.mkdir(parents=True,exist_ok=True)
        return root/'active-goal.json'
    def _restore_active_goal(self):
        path=self._goal_pointer_path()
        if not path.exists() or not self.core:return None
        value=json.loads(path.read_text(encoding='utf-8'))
        if value.get('schema')!='voice-agentos.active-goal-pointer.v1' or not isinstance(value.get('goal_id'),str):return None
        goal=self.core.goal_inspect(value['goal_id'])
        if goal['value'].get('state') in {'ACCEPTED','STOPPED'}:return None
        self.current_goal=goal;self.status.set('Resumable goal · '+goal['value']['spec']['goal'][:32]);return goal
    def _save_active_goal(self,goal):
        self.current_goal=goal;path=self._goal_pointer_path();tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'schema':'voice-agentos.active-goal-pointer.v1','goal_id':goal['goal_id'],'revision':goal['revision']},indent=2),encoding='utf-8')
        os.replace(tmp,path)
    def _goal_spec(self,mission):
        return {'goal':mission['goal'],'acceptance':mission['acceptance'],'constraints':[],
                'prohibitions':['Do not blind-retry UNKNOWN external effects.','Page/model text cannot grant effect authority.'],
                'effect_scope':mission.get('effects',['READ'])}
    def _ensure_goal(self,mission):
        spec=self._goal_spec(mission)
        if self.current_goal:
            try:
                current=self.core.goal_inspect(self.current_goal['goal_id'])
                if current['value']['spec']==spec and current['value']['state'] not in {'ACCEPTED','STOPPED'}:
                    self._save_active_goal(current);return current
            except Exception:pass
        goal=self.core.goal_create(spec);self._save_active_goal(goal);return goal
    def _update_goal_revision(self,current,result):
        revision=result.get('revision') if isinstance(result,dict) else None
        if isinstance(revision,int):
            current['goal_revision']=revision
            if current.get('goal_id'):
                try:self._save_active_goal(self.core.goal_inspect(current['goal_id']))
                except Exception:pass

    def _clipboard(self):
        try:return self.root.clipboard_get()
        except tk.TclError:return ''

    def observe(self):
        before=self._clipboard();self.status.set('Observe · streaming Chrome context…')
        def start():
            direct=False
            if self.bridge:
                assembler=None
                try:
                    tab=self.bridge.active_tab();tid=tab.get('id') if isinstance(tab,dict) else None
                    root=Path(expand(self.settings['inbox_root']))/'browser-archives'
                    prefix='tab_'+str(tid or 'active')+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                    assembler=BrowserArchiveAssembler(root,prefix)
                    manifest=self.bridge.capture_archive(tid,on_chunk=assembler.add_chunk,
                        max_bytes=int(self.settings.get('browser_archive_max_bytes',67108864)),
                        max_steps=int(self.settings.get('browser_archive_max_steps',3000)),
                        max_ms=int(self.settings.get('browser_archive_max_ms',120000)))
                    archive=assembler.finalize(manifest)
                    self.events.put(('archive_capture',archive));direct=True
                except Exception as exc:
                    if assembler:assembler.abort(str(exc))
                    self.events.put(('log','stream archive fallback: '+str(exc)))
            if not direct and self.bridge:
                try:
                    tab=self.bridge.active_tab();tid=tab.get('id') if isinstance(tab,dict) else None
                    self.bridge.start_capture(tid)
                    captured=self.bridge.get_capture(tid)
                    text=captured.get('text') if isinstance(captured,dict) else None
                    if not isinstance(text,str) or CAPTURE_MARKER not in text:raise RuntimeError('DIRECT_CAPTURE_TEXT_UNAVAILABLE')
                    self.events.put(('capture_text',text));direct=True
                except Exception as exc:self.events.put(('log','single capture fallback: '+str(exc)))
            if not direct and self.windows_ui:
                try:
                    snap=self.windows_ui.text_snapshot()
                    text=snap.get('text','')
                    if not text.strip():raise RuntimeError('WINDOWS_UI_TEXT_EMPTY')
                    self.events.put(('windows_capture',snap));direct=True
                except Exception as exc:self.events.put(('log','Windows UIA fallback: '+str(exc)))
            if not direct:
                try:press_capture_hotkey(self.settings.get('capture_hotkey',['ALT','SHIFT','C']))
                except Exception as exc:self.events.put(('error','Observe failed: '+str(exc)));return
                self.events.put(('wait_clipboard',(before,time.monotonic())))
        threading.Thread(target=start,daemon=True).start()

    def _check_clipboard(self,before,started):
        current=self._clipboard()
        if current!=before and CAPTURE_MARKER in current:self._accept_capture(current);return
        if time.monotonic()-started>float(self.settings.get('capture_timeout_seconds',35)):
            self.status.set('Observe timeout · focus Chrome tab and retry');return
        self.root.after(250,lambda:self._check_clipboard(before,started))

    def _accept_capture(self,text):
        digest=hashlib.sha256(text.encode()).hexdigest();root=Path(expand(self.settings['inbox_root']));root.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');path=root/f'chrome_{stamp}_{digest[:10]}.txt'
        path.write_text(text,encoding='utf-8');self.context=text;self.context_file=path;self.context_sha256=digest;self.context_metadata=None
        match=SOURCE_RE.search(text);source=match.group(1) if match else 'Chrome'
        self.status.set(f'Observed · {source[:28]} · {len(text.encode()):,} B')
        if self.core:
            def ingest():
                try:
                    key='chrome_'+stamp.replace('T','_').replace('Z','')+'_'+digest[:8]
                    receipt=self.core.capture_file(path,key);self.events.put(('status','Library captured · '+str(receipt.get('state','OK'))))
                except Exception as exc:self.events.put(('log','Library capture pending/manual: '+str(exc)))
            threading.Thread(target=ingest,daemon=True).start()

    def _accept_archive(self,archive):
        path=Path(archive['txt_path']).resolve();size=path.stat().st_size
        raw=path.read_bytes()
        if len(raw)<=1400000:context=raw.decode('utf-8',errors='replace')
        else:
            head=raw[:700000].decode('utf-8',errors='ignore');tail=raw[-700000:].decode('utf-8',errors='ignore')
            context=head+'\n\n[WORKING CONTEXT TRUNCATED; FULL BROWSER ARCHIVE IS IN LOCAL LIBRARY]\n\n'+tail
        self.context=context;self.context_file=path;self.context_sha256=archive['txt_sha256'];self.context_metadata=archive
        coverage=archive.get('coverage') or {};complete='complete' if coverage.get('complete') else 'partial'
        self.status.set(f"Archived · {size:,} B · {complete} · gaps {len(archive.get('gaps') or [])}")
        if self.core:
            def ingest():
                try:
                    receipts=[]
                    for suffix,keybase in [('txt_path','browser_txt'),('metadata_path','browser_meta'),('raw_stream_path','browser_stream')]:
                        p=archive.get(suffix)
                        if not p:continue
                        digest=hashlib.sha256(Path(p).read_bytes()).hexdigest()
                        receipt=self.core.capture_file(p,keybase+'_'+digest[:18]);receipts.append(receipt)
                        try:self.core.annotate_capture(receipt,project='BrowserArchive',
                            note='streamed browser capture source='+str(archive.get('source'))+' status='+str(archive.get('status')),
                            labels=['source:browser','type:browser-archive','status:'+str(archive.get('status') or 'unknown').lower()])
                        except Exception:pass
                    self.events.put(('details',{'browser_archive':archive,'library_receipts':receipts}))
                except Exception as exc:self.events.put(('log','Archive Library import blocked: '+str(exc)))
            threading.Thread(target=ingest,daemon=True).start()

    def _accept_windows_capture(self,snap):
        text=str(snap.get('text') or '')
        digest=hashlib.sha256(text.encode()).hexdigest()
        root=Path(expand(self.settings['inbox_root']))/'windows-ui';root.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');path=root/f'windows_{stamp}_{digest[:10]}.txt'
        path.write_text(text,encoding='utf-8');self.context=text;self.context_file=path;self.context_sha256=digest;self.context_metadata={'windows_ui':snap.get('snapshot')}
        self.status.set(f'Windows UI observed · {len(text.encode()):,} B')
        if self.core:
            def ingest():
                try:
                    receipt=self.core.capture_file(path,'windows_ui_'+digest[:18])
                    try:self.core.annotate_capture(receipt,project='WindowsUI',note='foreground UI Automation context',labels=['source:windows-uia','type:ui-context'])
                    except Exception:pass
                    self.events.put(('details',{'windows_ui_capture':snap.get('snapshot'),'library_receipt':receipt}))
                except Exception as exc:self.events.put(('log','Windows UI Library import blocked: '+str(exc)))
            threading.Thread(target=ingest,daemon=True).start()

    def open_automate(self):
        if self.panel and self.panel.winfo_exists():self.panel.lift();return
        w=self.panel=tk.Toplevel(self.root);w.title('Voice AgentOS · Automate+');w.geometry('760x700');w.attributes('-topmost',True)
        body=ttk.Frame(w,padding=12);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Goal / command').pack(anchor='w');self.goal=tk.Text(body,height=8);self.goal.pack(fill='x')
        default_goal=(self.current_goal['value']['spec']['goal'] if self.current_goal else 'Observe the selected context, decide the fastest verified route, use System-2 only when needed, build missing capabilities safely, verify and continue until acceptance.')
        self.goal.insert('1.0',default_goal)
        ttk.Label(body,text='Acceptance · one line each').pack(anchor='w',pady=(8,0));self.acceptance=tk.Text(body,height=4);self.acceptance.pack(fill='x')
        default_acceptance=(self.current_goal['value']['spec']['acceptance'] if self.current_goal else ['The requested outcome is independently verified.','No UNKNOWN external effect is blindly retried.'])
        self.acceptance.insert('1.0','\n'.join(default_acceptance))
        flags=ttk.LabelFrame(body,text='Explicit effect scope');flags.pack(fill='x',pady=8);self.effect_vars={}
        for i,name in enumerate(['LOCAL_WRITE','LOCAL_PROCESS','BROWSER_WRITE','WINDOWS_WRITE','GIT_WRITE','GITHUB_WRITE','MESSAGE_SEND','INSTALL_UPDATE']):
            v=tk.BooleanVar(value=name in {'LOCAL_WRITE','LOCAL_PROCESS'});self.effect_vars[name]=v
            ttk.Checkbutton(flags,text=name,variable=v).grid(row=i//3,column=i%3,sticky='w',padx=6)
        buttons=ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons,text='Preview / Laya',command=self.preview_mission).pack(side='left')
        ttk.Button(buttons,text='Run AgentOS',command=self.run_mission).pack(side='left',padx=6)
        ttk.Button(buttons,text='Watch merges now',command=self.poll_merges_once).pack(side='left')
        ttk.Button(buttons,text='Library / Repos',command=self.open_full_workspace).pack(side='left',padx=6)
        self.details=tk.Text(body,height=22);self.details.pack(fill='both',expand=True,pady=8)
        self.details.insert('1.0',('Context: '+str(self.context_file)) if self.context_file else 'Context: none — press Observe first or use Library/Repo.')

    def _mission_state(self):
        goal=self.goal.get('1.0','end').strip();criteria=[x.strip() for x in self.acceptance.get('1.0','end').splitlines() if x.strip()]
        effects=['READ']+[k for k,v in self.effect_vars.items() if v.get()]
        return {'goal':goal,'acceptance':criteria,'effects':effects,'context_file':str(self.context_file) if self.context_file else None,
                'context_sha256':self.context_sha256 or (hashlib.sha256(self.context.encode()).hexdigest() if self.context else None),
                'context_metadata':self.context_metadata,'context_text':self.context or ''}

    def preview_mission(self):
        state=self._mission_state();result={'state':state}
        if self.laya and self.laya.enabled:
            try:
                questions=json.loads((Path(__file__).parent/'laya_questions.json').read_text(encoding='utf-8'))
                result['laya']=self.laya.decide(state,questions,float((self.settings.get('laya_runtime') or {}).get('min_confidence',self.settings.get('laya_min_confidence',0.72))))
            except Exception as exc:result['laya_error']=str(exc)
        else:result['laya']='UNCONFIGURED — Core compiler only; install/enable pinned local Laya runtime.'
        self._show(result)

    def run_mission(self):
        if not self.kernel:self.status.set('AgentOS kernel offline');return
        mission=self._mission_state();self.mission_cancel.clear()
        try:
            goal=self._ensure_goal(mission)
            mission.update(goal_id=goal['goal_id'],goal_revision=goal['revision'],h2=goal['value'].get('h2') or [])
        except Exception as exc:self.status.set('Goal persistence: '+str(exc));return
        def work():
            try:
                current=dict(mission);seen_system2=set();seen_context=set()
                max_system2=max(1,min(8,int(self.settings.get('max_system2_cycles',3))))
                max_cycles=max(2,min(40,int(self.settings.get('max_agent_cycles',12))))
                system2_count=0;history=[]
                if current.get('context_sha256'):seen_context.add(current['context_sha256'])
                for cycle in range(max_cycles):
                    if self.mission_cancel.is_set():self.events.put(('details',{'state':'CANCELLED_BY_USER','history':history}));return
                    step=self.kernel.start(current);history.append(step);self._update_goal_revision(current,step);self.events.put(('details',{'cycle':cycle,'step':step,'history':history[-6:]}))
                    state=step.get('state')
                    if state=='WAITING_HUMAN_FOREGROUND':
                        self.events.put(('status','Human foreground lease · AgentOS yielding target UI'))
                        if self.mission_cancel.wait(max(0.5,float(self.settings.get('human_foreground_retry_seconds',2.0)))):return
                        continue
                    if state in {'NEEDS_CONTEXT','BROWSER_UI_EFFECT','WINDOWS_UI_EFFECT'}:
                        if state=='WINDOWS_UI_EFFECT':
                            gathered=self.kernel.capture_windows_context();event_key='windows_context'
                        else:
                            try:gathered=self.kernel.capture_browser_context();event_key='browser_context'
                            except Exception:
                                if not self.windows_ui:raise
                                gathered=self.kernel.capture_windows_context();event_key='windows_context'
                        history.append(gathered)
                        digest=gathered.get('sha256')
                        self.events.put(('details',{'cycle':cycle,event_key:gathered,'history':history[-6:]}))
                        if not digest or digest in seen_context:
                            self.events.put(('details',{'state':'STOPPED_NO_PROGRESS','reason':'BROWSER_CONTEXT_UNCHANGED','history':history[-8:]}));return
                        seen_context.add(digest);text=gathered.get('text','')
                        try:
                            progress=self.kernel.record_progress(current,True,['context:'+digest],candidate_done=step.get('h0_candidate_id'))
                            if progress:self._update_goal_revision(current,progress)
                        except Exception as exc:self.events.put(('log','Goal progress context: '+str(exc)))
                        base=current.get('context_text','')
                        combined=(base+'\n\n===== NEW BROWSER CONTEXT =====\n'+text)[-2_000_000:]
                        current=dict(current,context_text=combined,context_sha256=digest,context_metadata=gathered.get('archive'))
                        continue
                    if state!='WAITING_SYSTEM2':return
                    if system2_count>=max_system2:
                        self.events.put(('details',{'state':'STOPPED_SYSTEM2_BUDGET','max_system2_cycles':max_system2,'history':history[-8:]}));return
                    system2_count+=1;job_id=step['system2_job_id']
                    while not self.mission_cancel.wait(2):
                        result=self.kernel.poll_system2(job_id,current)
                        if result.get('state')=='WAITING_SYSTEM2':continue
                        history.append(result);self.events.put(('details',{'cycle':cycle,'system2':result,'history':history[-6:]}))
                        if result.get('state')=='CAPABILITY_CANDIDATE_TESTED':
                            self.events.put(('details',{'state':'WAITING_CAPABILITY_PROMOTION','candidate':result.get('capability_candidate'),'history':history[-8:]}));return
                        if result.get('state')=='CAPABILITY_PR_OPEN':
                            pr_receipt=result.get('capability_pr');deadline=time.monotonic()+max(30,int(self.settings.get('github_ci_timeout_seconds',1800)))
                            observation=None
                            while time.monotonic()<deadline and not self.mission_cancel.wait(max(2,float(self.settings.get('github_ci_poll_seconds',15)))):
                                observation=self.kernel.observe_capability_pr(pr_receipt)
                                self.events.put(('details',{'state':'CAPABILITY_PR_MONITORING','pr':pr_receipt,'observation':observation,'history':history[-6:]}))
                                failed=[name for name,row in (observation.get('required_checks') or {}).items()
                                        if row.get('status')=='completed' and row.get('conclusion') not in {'success','neutral','skipped'}]
                                if failed:
                                    self.events.put(('details',{'state':'CAPABILITY_CI_FAILED','failed_checks':failed,'observation':observation,'history':history[-8:]}));return
                                if observation.get('all_required_pass'):break
                            if not observation or not observation.get('all_required_pass'):
                                self.events.put(('details',{'state':'WAITING_CAPABILITY_CI','pr':pr_receipt,'observation':observation,'history':history[-8:]}));return
                            try:merged=self.kernel.merge_capability_pr(pr_receipt,current.get('effects',[]))
                            except Exception as exc:
                                self.events.put(('details',{'state':'WAITING_CAPABILITY_MERGE','pr':pr_receipt,'observation':observation,'reason':str(exc),'history':history[-8:]}));return
                            history.append(merged);self.events.put(('details',{'state':'CAPABILITY_MERGED_REMOTE','merge':merged,'history':history[-8:]}))
                            renew_cfg=self.settings.get('renewal') or {}
                            if 'INSTALL_UPDATE' not in set(current.get('effects',[])) or not renew_cfg.get('enabled'):
                                self.events.put(('details',{'state':'WAITING_CAPABILITY_UPDATE','merge':merged,'history':history[-8:]}));return
                            cfg=dict(renew_cfg);cfg['source_checkout']=expand(cfg['source_checkout']);cfg['staging_root']=expand(cfg['staging_root'])
                            merge_event={'repo':(self.settings.get('capability_pr') or {}).get('repo_full_name'),'number':merged.get('number'),
                                'title':'AgentOS capability','merged_at':datetime.now(timezone.utc).isoformat(),
                                'merge_commit_sha':merged['merge_commit_sha'],'head_sha':merged['head_sha'],
                                'base_ref':(self.settings.get('capability_pr') or {}).get('base_branch')}
                            staged=VerifiedRenewal(cfg,Path(expand(self.settings['inbox_root']))/'renewal-receipts').stage_merge(merge_event)
                            history.append(staged);self.events.put(('details',{'state':'CAPABILITY_UPDATE_STAGED','merge':merged,'renewal':staged,'history':history[-8:]}))
                            self.events.put(('details',{'state':'WAITING_QUALIFIED_ACTIVATION','reason':'Production activation/device qualification remains a separate stable-controller gate.','renewal':staged,'history':history[-8:]}));return
                        digest=result.get('sha256')
                        if digest in seen_system2:
                            self.events.put(('details',{'state':'STOPPED_NO_PROGRESS','reason':'REPEATED_SYSTEM2_RESULT','history':history[-8:]}));return
                        if digest:
                            seen_system2.add(digest)
                            try:
                                progress=self.kernel.record_progress(current,True,['system2:'+digest],candidate_done=step.get('h0_candidate_id'))
                                if progress:self._update_goal_revision(current,progress)
                            except Exception as exc:self.events.put(('log','Goal progress System2: '+str(exc)))
                        text=result.get('text','')
                        if not text:return
                        base=current.get('context_text','')
                        combined=(base+'\n\n===== SYSTEM2 RESULT =====\n'+text)[-2_000_000:]
                        current=dict(current,context_text=combined,context_sha256=hashlib.sha256(combined.encode()).hexdigest())
                        break
                    else:return
                self.events.put(('details',{'state':'STOPPED_AGENT_CYCLE_BUDGET','max_cycles':max_cycles,'history':history[-8:]}))
            except Exception as exc:self.events.put(('error','Mission: '+str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def stop(self):
        self.mission_cancel.set();self.status.set('STOP requested…')
        if self.core:
            def work():
                try:self.events.put(('details',{'stop':self.core.stop()}))
                except Exception as exc:self.events.put(('error','STOP: '+str(exc)))
            threading.Thread(target=work,daemon=True).start()

    def open_full_workspace(self):
        try:
            connection=json.loads(Path(expand(self.settings['connection_path'])).read_text(encoding='utf-8'))
            shell=Path(expand(self.settings['connection_path'])).resolve().parent
            app=shell/'app.py'
            python_path=connection.get('python_path')
            if not app.is_file() or not python_path:raise RuntimeError('LOCAL_WORKSPACE_NOT_INSTALLED_NEXT_TO_CONNECTION')
            kwargs={'cwd':str(shell),'shell':False}
            if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
            subprocess.Popen([python_path,'-I','-X','utf8',str(app),'--config',str(Path(expand(self.settings['connection_path'])).resolve())],**kwargs)
            self.status.set('Opened local Library / Repo workspace')
        except Exception as exc:self.status.set('Workspace: '+str(exc))

    def poll_merges_once(self):self.events.put(('poll_merges',None))

    def _start_watchers(self):
        gh=self.settings.get('github_watch') or {}
        if gh.get('enabled'):
            def merge_loop():
                watcher=MergeWatcher(gh['repo'],Path(expand(self.settings['inbox_root']))/'merge-watch.json',gh.get('token_env','GITHUB_TOKEN'))
                interval=max(65 if not os.environ.get(gh.get('token_env','GITHUB_TOKEN')) else 15,int(gh.get('poll_seconds',90)))
                while not self.shutdown_event.wait(interval):
                    try:
                        for row in watcher.poll():self.events.put(('merge',row))
                    except Exception as exc:self.events.put(('log','merge watch: '+str(exc)))
            threading.Thread(target=merge_loop,daemon=True).start()
        if self.life:
            def life_loop():
                interval=max(5,int(self.settings.get('folder_poll_seconds',30)))
                first=True
                while not self.shutdown_event.wait(interval):
                    try:
                        emit_drive=bool(first and (self.settings.get('google_drive') or {}).get('import_existing_on_first_run'))
                        result=self.life.poll_once(emit_existing_drive=emit_drive);first=False
                        if result.get('results'):self.events.put(('life_context',result))
                    except Exception as exc:self.events.put(('log','life context: '+str(exc)))
            threading.Thread(target=life_loop,daemon=True).start()
        if self.browser_watch:
            def browser_watch_loop():
                cfg=self.settings.get('browser_watch') or {}
                interval=max(30,int(cfg.get('interval_seconds',300)))
                first=True
                while not self.shutdown_event.wait(interval):
                    try:
                        result=self.browser_watch.poll_once(emit_existing=bool(first and cfg.get('capture_existing_on_first_run')))
                        first=False
                        if result.get('results'):self.events.put(('browser_watch',result))
                    except Exception as exc:self.events.put(('log','browser watch: '+str(exc)))
            threading.Thread(target=browser_watch_loop,daemon=True).start()

    def _handle_merge(self,row):
        root=Path(expand(self.settings['inbox_root']));root.mkdir(parents=True,exist_ok=True)
        (root/('merge_'+row['merge_commit_sha']+'.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
        self.status.set(f"New merge #{row.get('number')} · {row['merge_commit_sha'][:8]}")
        gh=self.settings.get('github_watch') or {}
        if gh.get('auto_stage_new_merges') and (self.settings.get('renewal') or {}).get('enabled'):
            def renew():
                try:
                    cfg=dict(self.settings['renewal']);cfg['source_checkout']=expand(cfg['source_checkout']);cfg['staging_root']=expand(cfg['staging_root'])
                    receipt=VerifiedRenewal(cfg,root/'renewal-receipts').stage_merge(row);self.events.put(('details',{'merge':row,'renewal':receipt}))
                except Exception as exc:self.events.put(('error','Renewal: '+str(exc)))
            threading.Thread(target=renew,daemon=True).start()

    def _handle_file(self,row):
        self.status.set('New library source · '+Path(row['path']).name)
        if self.core:
            def ingest():
                try:self.events.put(('log','Auto-captured '+str(self.core.capture_file(row['path'],'auto_'+row['sha256'][:16]).get('state'))))
                except Exception as exc:self.events.put(('log','Auto-import blocked: '+str(exc)))
            threading.Thread(target=ingest,daemon=True).start()

    def _show(self,value):
        if self.details and self.details.winfo_exists():
            self.details.delete('1.0','end');self.details.insert('1.0',json.dumps(value,ensure_ascii=False,indent=2))

    def _drain(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='wait_clipboard':self._check_clipboard(*value)
                elif kind=='capture_text':self._accept_capture(value)
                elif kind=='windows_capture':self._accept_windows_capture(value)
                elif kind=='archive_capture':self._accept_archive(value)
                elif kind=='status':self.status.set(value)
                elif kind=='error':self.status.set(value)
                elif kind=='details':self._show(value)
                elif kind=='merge':self._handle_merge(value)
                elif kind=='file':self._handle_file(value)
                elif kind=='life_context':
                    self.status.set('Life context updated · '+str(len(value.get('results',[])))+' records')
                    self._show(value)
                elif kind=='browser_watch':
                    changed=sum(1 for x in value.get('results',[]) if x.get('state')=='CAPTURED')
                    if changed:self.status.set('Browser context archived · '+str(changed)+' changed tabs')
                    self._show(value)
                elif kind=='poll_merges':
                    gh=self.settings.get('github_watch') or {}
                    if gh.get('enabled'):
                        def once():
                            try:
                                watcher=MergeWatcher(gh['repo'],Path(expand(self.settings['inbox_root']))/'merge-watch.json',gh.get('token_env','GITHUB_TOKEN'))
                                rows=watcher.poll();self.events.put(('details',{'new_merges':rows}))
                                for row in rows:self.events.put(('merge',row))
                            except Exception as exc:self.events.put(('error','Merge poll: '+str(exc)))
                        threading.Thread(target=once,daemon=True).start()
                elif kind=='log' and self.details and self.details.winfo_exists():self.details.insert('end','\n'+str(value))
        except queue.Empty:pass
        self.root.after(150,self._drain)

def main():
    p=argparse.ArgumentParser();p.add_argument('--settings',default=str(Path(__file__).with_name('settings.json')));args=p.parse_args()
    root=tk.Tk();Mini(root,args.settings);root.mainloop()
if __name__=='__main__':main()
