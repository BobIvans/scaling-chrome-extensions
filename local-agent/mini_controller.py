from __future__ import annotations
import argparse, ctypes, hashlib, json, os, queue, re, threading, time
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from control_bridge import ChromeBridge
from core_client import CoreClient
from folder_watch import FolderWatcher
from github_merge_watch import MergeWatcher
from laya_client import LayaClient
from self_renew import VerifiedRenewal

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
        self.events=queue.Queue();self.context=None;self.context_file=None;self.core=None;self.bridge=None;self.stop_event=threading.Event()
        self.panel=None;self.details=None
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

    def _clipboard(self):
        try:return self.root.clipboard_get()
        except tk.TclError:return ''

    def observe(self):
        before=self._clipboard();self.status.set('Observe · waiting for Chrome capture…')
        def start():
            direct=False
            if self.bridge:
                try:
                    tab=self.bridge.active_tab();tid=tab.get('id') if isinstance(tab,dict) else None
                    self.bridge.start_capture(tid);direct=True
                except Exception as exc:self.events.put(('log','bridge fallback: '+str(exc)))
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
        path.write_text(text,encoding='utf-8');self.context=text;self.context_file=path
        match=SOURCE_RE.search(text);source=match.group(1) if match else 'Chrome'
        self.status.set(f'Observed · {source[:28]} · {len(text.encode()):,} B')
        if self.core:
            def ingest():
                try:
                    key='chrome_'+stamp.replace('T','_').replace('Z','')+'_'+digest[:8]
                    receipt=self.core.capture_file(path,key);self.events.put(('status','Library captured · '+str(receipt.get('state','OK'))))
                except Exception as exc:self.events.put(('log','Library capture pending/manual: '+str(exc)))
            threading.Thread(target=ingest,daemon=True).start()

    def open_automate(self):
        if self.panel and self.panel.winfo_exists():self.panel.lift();return
        w=self.panel=tk.Toplevel(self.root);w.title('Voice AgentOS · Automate+');w.geometry('760x700');w.attributes('-topmost',True)
        body=ttk.Frame(w,padding=12);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Goal / command').pack(anchor='w');self.goal=tk.Text(body,height=8);self.goal.pack(fill='x')
        self.goal.insert('1.0','Observe the selected context, decide the fastest verified route, use System-2 only when needed, build missing capabilities safely, verify and continue until acceptance.')
        ttk.Label(body,text='Acceptance · one line each').pack(anchor='w',pady=(8,0));self.acceptance=tk.Text(body,height=4);self.acceptance.pack(fill='x')
        self.acceptance.insert('1.0','The requested outcome is independently verified.\nNo UNKNOWN external effect is blindly retried.')
        flags=ttk.LabelFrame(body,text='Explicit effect scope');flags.pack(fill='x',pady=8);self.effect_vars={}
        for i,name in enumerate(['LOCAL_WRITE','LOCAL_PROCESS','BROWSER_WRITE','GIT_WRITE','GITHUB_WRITE','MESSAGE_SEND','INSTALL_UPDATE']):
            v=tk.BooleanVar(value=name in {'LOCAL_WRITE','LOCAL_PROCESS'});self.effect_vars[name]=v
            ttk.Checkbutton(flags,text=name,variable=v).grid(row=i//3,column=i%3,sticky='w',padx=6)
        buttons=ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons,text='Preview / Laya',command=self.preview_mission).pack(side='left')
        ttk.Button(buttons,text='Run registered',command=self.run_mission).pack(side='left',padx=6)
        ttk.Button(buttons,text='Watch merges now',command=self.poll_merges_once).pack(side='left')
        self.details=tk.Text(body,height=22);self.details.pack(fill='both',expand=True,pady=8)
        self.details.insert('1.0',('Context: '+str(self.context_file)) if self.context_file else 'Context: none — press Observe first or use Library/Repo.')

    def _mission_state(self):
        goal=self.goal.get('1.0','end').strip();criteria=[x.strip() for x in self.acceptance.get('1.0','end').splitlines() if x.strip()]
        effects=['READ']+[k for k,v in self.effect_vars.items() if v.get()]
        return {'goal':goal,'acceptance':criteria,'effects':effects,'context_file':str(self.context_file) if self.context_file else None,
                'context_sha256':hashlib.sha256(self.context.encode()).hexdigest() if self.context else None}

    def preview_mission(self):
        state=self._mission_state();result={'state':state}
        endpoint=self.settings.get('laya_endpoint','')
        if endpoint:
            try:
                questions=json.loads((Path(__file__).parent/'laya_questions.json').read_text(encoding='utf-8'))
                result['laya']=LayaClient(endpoint).decide(state,questions,float(self.settings.get('laya_min_confidence',0.72)))
            except Exception as exc:result['laya_error']=str(exc)
        else:result['laya']='UNCONFIGURED — Core compiler only; configure local Laya endpoint for typed routing.'
        self._show(result)

    def run_mission(self):
        if not self.core:self.status.set('Core offline');return
        state=self._mission_state()
        def work():
            try:
                refs=[state['context_sha256']] if state['context_sha256'] else []
                created=self.core.create_action(state['goal'],state['acceptance'],refs)
                out={'created':created}
                if created.get('state')=='COMPILED':out['job']=self.core.enqueue_action(created['intent_id'],created['revision'])
                else:out['next']='Use missing_slots/development_request; Cognitive Relay maps it to System-2/capability growth when available.'
                self.events.put(('details',out))
            except Exception as exc:self.events.put(('error','Mission: '+str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def stop(self):
        self.stop_event.set();self.status.set('STOP requested…')
        if self.core:
            def work():
                try:self.events.put(('details',{'stop':self.core.stop()}))
                except Exception as exc:self.events.put(('error','STOP: '+str(exc)))
            threading.Thread(target=work,daemon=True).start()

    def poll_merges_once(self):self.events.put(('poll_merges',None))

    def _start_watchers(self):
        gh=self.settings.get('github_watch') or {}
        if gh.get('enabled'):
            def merge_loop():
                watcher=MergeWatcher(gh['repo'],Path(expand(self.settings['inbox_root']))/'merge-watch.json',gh.get('token_env','GITHUB_TOKEN'))
                interval=max(65 if not os.environ.get(gh.get('token_env','GITHUB_TOKEN')) else 15,int(gh.get('poll_seconds',90)))
                while not self.stop_event.wait(interval):
                    try:
                        for row in watcher.poll():self.events.put(('merge',row))
                    except Exception as exc:self.events.put(('log','merge watch: '+str(exc)))
            threading.Thread(target=merge_loop,daemon=True).start()
        roots=[expand(x) for x in self.settings.get('watch_folders',[]) if str(x).strip()]
        if roots:
            def folder_loop():
                watcher=FolderWatcher(roots,Path(expand(self.settings['inbox_root']))/'folder-watch.json')
                interval=max(5,int(self.settings.get('folder_poll_seconds',30)))
                while not self.stop_event.wait(interval):
                    try:
                        for row in watcher.scan():self.events.put(('file',row))
                    except Exception as exc:self.events.put(('log','folder watch: '+str(exc)))
            threading.Thread(target=folder_loop,daemon=True).start()

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
                try:self.events.put(('log','Auto-captured '+str(self.core.capture_file(row['path'],'auto_'+row['sha256'][:16]).get('state')))
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
                elif kind=='status':self.status.set(value)
                elif kind=='error':self.status.set(value)
                elif kind=='details':self._show(value)
                elif kind=='merge':self._handle_merge(value)
                elif kind=='file':self._handle_file(value)
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
