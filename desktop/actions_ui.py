"""Keyboard/text/optional voice panel using installed Core typed operations."""
from __future__ import annotations

import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk

from desktop.client import DesktopClient
from desktop.voice import Capture, WindowsHotkey, transcribe_local


class ActionsPanel:
    def __init__(self, parent, client):
        self.client=client
        self.window=tk.Toplevel(parent);self.window.title('Текст и голос → Core actions')
        self.window.geometry('850x750')
        self.events=queue.Queue(maxsize=8);self.busy=False;self.closed=False
        self.intent=None;self.compiled_input=None;self.config=None;self.capture=None;self.hotkey=None;self.original_transcript=None
        self.control=DesktopClient(client.connection)
        self.status=tk.StringVar(value='Загрузка зарегистрированных возможностей…')
        self.fields={}
        body=ttk.Frame(self.window,padding=12);body.pack(fill='both',expand=True);body.columnconfigure(1,weight=1)
        for row,(key,label) in enumerate([('command','Capability'),('repo','Repo alias'),('namespace','Namespace'),
                ('destination','Target binding ID'),('packet_id','Immutable packet ID'),('mode','Режим'),('criteria','Критерии (через ;)'),('source_refs','Source IDs (через ;)')]):
            ttk.Label(body,text=label).grid(row=row,column=0,sticky='w')
            var=self.fields[key]=tk.StringVar()
            ttk.Entry(body,textvariable=var).grid(row=row,column=1,sticky='ew')
        ttk.Label(body,text='Исходный текст / исправленный transcript').grid(row=8,column=0,columnspan=2,sticky='w')
        self.input=tk.Text(body,height=5,wrap='word');self.input.grid(row=9,column=0,columnspan=2,sticky='ew')
        toolbar=ttk.Frame(body);toolbar.grid(row=10,column=0,columnspan=2,sticky='w',pady=8)
        for label,command in [('Plan preview',self.compile),('Исправить revision',self.correct),('Enqueue',self.enqueue),('STOP (Esc)',self.stop),('Resume admission',lambda:self.call('RESUME',{}))]:
            ttk.Button(toolbar,text=label,command=command).pack(side='left',padx=3)
        bindbar=ttk.Frame(body);bindbar.grid(row=11,column=0,columnspan=2,sticky='ew')
        ttk.Label(bindbar,text='Выбранный CDP tab ID').pack(side='left')
        self.handle=tk.StringVar();ttk.Entry(bindbar,textvariable=self.handle).pack(side='left',fill='x',expand=True)
        ttk.Button(bindbar,text='Bind и показать identity',command=lambda:self.call('BIND',{'handle':self.handle.get()},self.bound)).pack(side='left')
        voicebar=ttk.Frame(body);voicebar.grid(row=12,column=0,columnspan=2,sticky='w',pady=6)
        self.hold=ttk.Button(voicebar,text='PTT: удерживать Space / кнопку')
        self.hold.pack(side='left')
        self.hold.bind('<ButtonPress-1>',lambda e:self.press());self.hold.bind('<ButtonRelease-1>',lambda e:self.release())
        self.hold.bind('<KeyPress-space>',lambda e:self.press());self.hold.bind('<KeyRelease-space>',lambda e:self.release())
        ttk.Button(voicebar,text='Stop recording',command=self.release).pack(side='left')
        ttk.Button(voicebar,text='Local ASR → editable text',command=self.transcribe).pack(side='left')
        ttk.Label(body,textvariable=self.status,wraplength=780).grid(row=13,column=0,columnspan=2,sticky='w')
        self.preview=tk.Text(body,height=14,wrap='word',state='disabled');self.preview.grid(row=14,column=0,columnspan=2,sticky='nsew');body.rowconfigure(14,weight=1)
        self.window.bind('<Escape>',lambda e:self.stop())
        self.window.bind('<FocusOut>',lambda e:self.release() if e.widget==self.window else None)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.window.after(40,self.drain)
        self.call('INFO',{},self.configured)

    def configured(self,result):
        self.config=result
        self.render(result)
        if result.get('namespaces'):
            self.fields['namespace'].set(result['namespaces'][0])
        voice=result.get('voice')
        if voice:
            try:
                self.capture=Capture(voice['capture_root'],device=voice.get('device'))
                self.hotkey=WindowsHotkey(self.press,self.release)
            except (OSError,ValueError) as exc:
                self.status.set(str(exc)+'; keyboard/text остаётся доступен.')

    def input_value(self):
        slots={k:v.get().strip() for k,v in self.fields.items() if k not in {'command','criteria','source_refs'} and v.get().strip()}
        value={'text':self.input.get('1.0','end-1c'),'command':self.fields['command'].get().strip(),
               'modality':'VOICE' if self.original_transcript is not None else 'TEXT','slots':slots,
               'criteria':[x.strip() for x in self.fields['criteria'].get().split(';') if x.strip()],
               'source_refs':[x.strip() for x in self.fields['source_refs'].get().split(';') if x.strip()]}
        if self.original_transcript is not None:
            value['original_text']=self.original_transcript
        return value

    def compiled(self,result):
        self.intent=result;self.render(result)

    def compile(self):
        value=self.input_value()
        def apply(result):
            self.compiled_input=value;self.compiled(result)
        self.call('CREATE',value,apply)

    def correct(self):
        if self.intent:
            value=self.input_value()
            def apply(result):
                self.compiled_input=value;self.compiled(result)
            self.call('CORRECT',{'intent_id':self.intent['intent_id'],'revision':self.intent['revision'],'input':value},apply)

    def enqueue(self):
        if self.input_value()!=self.compiled_input:
            self.status.set('INPUT_CHANGED: исправьте revision или создайте новый plan preview.')
            return
        if self.intent and self.intent.get('state')=='COMPILED':
            self.call('ENQUEUE',{'intent_id':self.intent['intent_id'],'revision':self.intent['revision']})

    def bound(self,result):
        self.fields['destination'].set(result['binding_id']);self.render(result)

    def render(self,result):
        self.preview.configure(state='normal');self.preview.delete('1.0','end')
        self.preview.insert('1.0',json.dumps(result,ensure_ascii=False,indent=2));self.preview.configure(state='disabled')
        self.status.set(result.get('state','Результат Core получен. Execution запускает существующий registered worker.'))

    def worker(self,operation,apply):
        if self.busy or self.closed:
            return
        self.busy=True
        def run():
            try:
                result=operation();error=None
            except Exception as exc:
                result=None;error=str(exc)
            if not self.closed:
                try:self.events.put_nowait((result,error,apply))
                except queue.Full:pass
        threading.Thread(target=run,daemon=True).start()

    def call(self,action,payload,apply=None):
        self.worker(lambda:self.client.request({'type':'durable.action','action':action,'payload':payload})['result']['action'],apply or self.render)

    def stop(self):
        if self.capture:
            self.capture.stop('STOP')
        self.client.cancel()
        self.status.set('STOP: новые действия блокируются; возможный remote effect сохраняется как unknown.')
        # Dedicated control connection does not share the ASR/request worker gate.
        def run():
            try:
                if self.control.identity is None:self.control.handshake()
                result=self.control.request({'type':'durable.action','action':'STOP','payload':{}})['result']['action']
                error=None
            except Exception as exc:
                result=None;error='CORE_STOP_NOT_CONFIRMED: '+str(exc)
            if not self.closed:
                try:self.events.put_nowait((result,error,self.render))
                except queue.Full:pass
        threading.Thread(target=run,daemon=True).start()

    def press(self):
        if not self.capture:
            self.status.set('VOICE_UNAVAILABLE; вводите текст. Capture/model выбирает operator policy.')
            return
        try:
            self.capture.press();self.status.set('Микрофон записывает. Отпустите кнопку или нажмите STOP.')
        except Exception as exc:self.status.set(str(exc))

    def release(self):
        if self.capture and self.capture.stream is not None:
            self.render(self.capture.stop())

    def transcribe(self):
        if not self.capture or not self.capture.session or self.capture.stream is not None:
            return
        before=self.input_value()
        def apply(result):
            if self.input_value()!=before:
                self.status.set('VOICE_LATE_RESULT: текст изменился; transcript не заменил новый ввод.')
                return
            self.transcribed(result)
        self.worker(lambda:transcribe_local(self.capture.session,self.config['voice'],self.client.connection),apply)

    def transcribed(self,result):
        self.original_transcript=result['text'];self.input.delete('1.0','end');self.input.insert('1.0',result['text'])
        self.status.set('Transcript непроверен. Исправьте critical slots и создайте/исправьте plan preview; action не запущен.')

    def drain(self):
        if self.closed:return
        try:
            while True:
                result,error,apply=self.events.get_nowait();self.busy=False
                if error:self.status.set(error)
                else:apply(result)
        except queue.Empty:pass
        try:
            if self.hotkey:self.hotkey.poll()
            if self.capture:self.capture.poll()
        except Exception as exc:
            self.status.set(str(exc)+'; текстовый STOP остаётся доступен.')
        self.window.after(40,self.drain)

    def close(self):
        self.closed=True
        if self.hotkey:self.hotkey.close()
        if self.capture:self.capture.stop('STOP')
        self.control.close();self.client.cancel();self.window.destroy()
