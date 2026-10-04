"""Paged context workflow. SQLite/Core remain the data and execution owners."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
import uuid
from desktop.client import DesktopClient, DesktopError, environment


class LibraryWindow:
    def __init__(self,parent,connection,namespace,existing_ids=None):
        self.connection=connection;self.ns=namespace;self.client=DesktopClient(connection)
        # STOP never shares the ordinary transport lock or UI worker queue.
        self.stop_client=DesktopClient(connection);self.events=queue.Queue(maxsize=8)
        self.closed=False;self.busy=False;self.rows=[];self.offset=0;self.next_offset=None;self.history=[];self.preview_cursor=0;self.existing_ids=list(existing_ids or [])
        root=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'ContextLibrary'
        root.mkdir(parents=True,exist_ok=True)
        self.journal=root/(hashlib.sha256(connection.profile_path.encode()).hexdigest()+'.transport.json')
        self.ids={'selection_id':'','packet_id':'','projection_id':'','operation_id':'','job_id':''}
        try:
            saved=json.loads(self.journal.read_text());self.ids.update({k:v for k,v in saved.items() if k in self.ids and isinstance(v,str)})
        except (OSError,ValueError):pass
        self.window=w=tk.Toplevel(parent);w.title('Библиотека, пакеты и Core — '+namespace);w.geometry('1080x780')
        w.protocol('WM_DELETE_WINDOW',self.close);w.bind('<Control-Shift-X>',lambda e:self.stop())
        self.status=tk.StringVar(value='Подключение…');self.query=tk.StringVar();self.goal=tk.StringVar();self.criteria=tk.StringVar()
        self.project_filter=tk.StringVar();self.time_filter=tk.StringVar();self.history_filter=tk.BooleanVar(value=False)
        self.destination=tk.StringVar();self.ref_start=tk.StringVar(value='0');self.ref_end=tk.StringVar(value='0')
        self.doc=tk.StringVar(value=self.ids['packet_id']);self.ordinal=tk.StringVar(value='0')
        head=ttk.Frame(w,padding=8);head.pack(fill='x')
        ttk.Button(head,text='STOP — Ctrl+Shift+X',command=self.stop).pack(side='left')
        ttk.Button(head,text='Состояние / продолжить',command=self.control).pack(side='left',padx=5)
        ttk.Button(head,text='Возможности',command=lambda:self.read('CAPABILITIES',{})).pack(side='left')
        ttk.Button(head,text='Выполнить одно задание Core',command=self.work).pack(side='right')
        ttk.Button(head,text='Проверить последнюю операцию',command=self.operation).pack(side='right',padx=5)
        ttk.Label(w,textvariable=self.status,wraplength=1000).pack(fill='x',padx=8)
        nb=ttk.Notebook(w);nb.pack(fill='both',expand=True,padx=8,pady=8)
        sources=ttk.Frame(nb,padding=8);nb.add(sources,text='Источники и корзина')
        bar=ttk.Frame(sources);bar.pack(fill='x')
        ttk.Entry(bar,textvariable=self.query).pack(side='left',fill='x',expand=True)
        ttk.Button(bar,text='Найти',command=lambda:self.search(0)).pack(side='left')
        ttk.Button(bar,text='Назад',command=self.previous).pack(side='left')
        ttk.Button(bar,text='Далее',command=self.next).pack(side='left')
        ttk.Button(bar,text='Импорт файла',command=self.capture).pack(side='left')
        scopebar=ttk.Frame(sources);scopebar.pack(fill='x')
        ttk.Label(scopebar,text='Проект').pack(side='left');ttk.Entry(scopebar,textvariable=self.project_filter,width=20).pack(side='left')
        ttk.Label(scopebar,text='Применимо на (Unix seconds)').pack(side='left');ttk.Entry(scopebar,textvariable=self.time_filter,width=16).pack(side='left')
        ttk.Checkbutton(scopebar,text='История',variable=self.history_filter).pack(side='left')
        ttk.Button(scopebar,text='Аннотация / коррекция',command=lambda:self.guard(self.annotation)).pack(side='left')
        ttk.Button(scopebar,text='Выбор основной библиотеки',command=self.adopt).pack(side='left')
        ttk.Label(sources,text='Страница до 20 источников; «Далее» читает весь корпус. Выберите точный диапазон байтов.').pack(anchor='w')
        frame=ttk.Frame(sources);frame.pack(fill='both',expand=True)
        self.listbox=tk.Listbox(frame,exportselection=False,height=12);self.listbox.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(frame,command=self.listbox.yview);scroll.pack(side='right',fill='y');self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.bind('<<ListboxSelect>>',self.selected)
        rangebar=ttk.Frame(sources);rangebar.pack(fill='x',pady=6)
        for label,var in (('Начало',self.ref_start),('Конец',self.ref_end)):
            ttk.Label(rangebar,text=label).pack(side='left');ttk.Entry(rangebar,textvariable=var,width=12).pack(side='left',padx=4)
        ttk.Button(rangebar,text='Прочитать диапазон',command=lambda:self.guard(lambda:self.read_range(0))).pack(side='left')
        ttk.Button(rangebar,text='Добавить в корзину',command=lambda:self.guard(self.select)).pack(side='left')
        ttk.Button(rangebar,text='Удалить источник',command=lambda:self.guard(self.delete)).pack(side='left')
        ttk.Button(rangebar,text='Убрать диапазон из корзины',command=lambda:self.guard(self.remove)).pack(side='left')
        readerbar=ttk.Frame(sources);readerbar.pack(fill='x')
        ttk.Button(readerbar,text='Предыдущие байты',command=lambda:self.guard(lambda:self.read_range(max(0,self.preview_cursor-8192)))).pack(side='left')
        ttk.Button(readerbar,text='Следующие байты',command=lambda:self.guard(lambda:self.read_range(self.preview_cursor+8192))).pack(side='left')
        ttk.Label(readerbar,text='До 8192 байтов за чтение; base64 сохраняет точные байты, text — только preview.').pack(side='left')
        task=ttk.Frame(nb,padding=8);nb.add(task,text='Пакет и результат')
        for label,var in (('Цель',self.goal),('Критерии — разделитель ;',self.criteria),('Зарегистрированное назначение',self.destination),('ID документа',self.doc),('Номер части',self.ordinal)):
            ttk.Label(task,text=label).pack(anchor='w');ttk.Entry(task,textvariable=var).pack(fill='x',pady=(0,6))
        actions=ttk.Frame(task);actions.pack(fill='x')
        for name,fn in [('Собрать пакет',self.build),('Share-проекция',self.project),('Экспорт',self.export),('Импорт AI-результата',self.result),('NEED_CONTEXT',self.need),('Информация',lambda:self.read('DOCUMENT',{'document_id':self.doc.get(),'kind':'INFO'})),('Прочитать часть',lambda:self.read('PART',{'document_id':self.doc.get(),'ordinal':int(self.ordinal.get())}))]:
            ttk.Button(actions,text=name,command=lambda f=fn:self.guard(f)).pack(side='left',padx=2)
        ttk.Label(task,text='Пакет готовится локально. Импортированный ответ остаётся AI_CLAIM; критерии автоматически не закрываются.',wraplength=980).pack(anchor='w',pady=12)
        recovery=ttk.Frame(nb,padding=8);nb.add(recovery,text='Backup и офлайн-синхронизация')
        for name,fn in [('Создать проверяемый backup',lambda:self.folder_job('BACKUP')),('Восстановить в отдельную копию',self.restore),('Экспорт офлайн-снимка',lambda:self.folder_job('SYNC_EXPORT')),('Импорт офлайн-снимка',self.sync_import)]:
            ttk.Button(recovery,text=name,command=lambda f=fn:self.guard(f)).pack(anchor='w',pady=6)
        ttk.Label(recovery,text='Восстановление создаёт отдельную копию с отключённым запуском. Активация требует остановки всех владельцев и отдельной проверки оператора.',wraplength=900).pack(anchor='w',pady=12)
        output=ttk.Frame(nb);nb.add(output,text='Проверенный ответ')
        self.output=tk.Text(output,wrap='word',state='disabled');self.output.pack(fill='both',expand=True)
        self.after=w.after(40,self.drain)
        self.call(lambda:(self.client.handshake(),self.stop_client.handshake()),lambda x:self.search(0))

    def guard(self,fn):
        try:fn()
        except (ValueError,KeyError,IndexError,DesktopError) as e:self.status.set(str(e)[:100])

    def call(self,fn,apply=None,*,priority=False):
        if self.closed:return
        if self.busy and not priority:self.status.set('Дождитесь ответа. STOP доступен независимо.');return
        if not priority:self.busy=True
        def run():
            try:result=('ok',fn(),apply,priority)
            except (DesktopError,OSError,ValueError,subprocess.SubprocessError) as e:result=('error',str(e)[:100],None,priority)
            if not self.closed:
                try:self.events.put(result,timeout=1)
                except queue.Full:pass
        threading.Thread(target=run,daemon=True).start()

    def drain(self):
        if self.closed:return
        try:
            while True:
                kind,value,apply,priority=self.events.get_nowait()
                if not priority:self.busy=False
                if kind=='error':self.status.set(('STOP_UNCONFIRMED: ' if priority else 'Ответ не получен; проверьте тот же ID операции. ')+value)
                else:
                    self.output.configure(state='normal');self.output.delete('1.0','end');self.output.insert('end',json.dumps(value,ensure_ascii=False,indent=2));self.output.configure(state='disabled')
                    if apply:self.guard(lambda:apply(value))
        except queue.Empty:pass
        self.after=self.window.after(40,self.drain)

    def save_ids(self):
        stage=self.journal.with_suffix('.tmp');stage.write_text(json.dumps(self.ids));os.replace(stage,self.journal)

    def request(self,action,args,op=None):
        r={'type':'durable.library','namespace':self.ns,'action':action,'arguments':args}
        if op:r['operationId']=op
        return self.client.request(r)['result']['library']['data']

    def read(self,action,args,apply=None):self.call(lambda:self.request(action,args),apply)

    def submit(self,action,args):
        if self.busy:self.status.set('Дождитесь ответа.');return
        op='desktop-'+uuid.uuid4().hex;self.ids['operation_id']=op;self.ids['job_id']='';self.save_ids()
        def applied(r):
            self.ids['job_id']=r['job_id'];self.save_ids();self.status.set('Сохранено в Core: '+r['state']+'. ID: '+op)
        self.call(lambda:self.request(action,args,op),applied)

    def operation(self):
        if not self.ids['operation_id']:return
        self.read('OPERATION',{'operation_id':self.ids['operation_id']},self.apply_job)

    def apply_job(self,r):
        self.status.set('Core: '+r.get('state','UNKNOWN'))
        result=r.get('result',{})
        if r.get('state')=='SUCCEEDED':
            for k in ('selection_id','packet_id','projection_id'):
                if k in result:self.ids[k]=result[k]
            self.save_ids();self.doc.set(result.get('projection_id',result.get('packet_id',self.doc.get())))
            if 'source_ref' in result:
                reason=simpledialog.askstring('WHY_THIS_PACKET','Почему выбранный источник основной библиотеки нужен?',parent=self.window)
                if reason:
                    args={'rows':[{'source_ref':result['source_ref'],'reason':reason}]}
                    if self.ids['selection_id']:args['parent']=self.ids['selection_id']
                    self.submit('SELECT',args)

    def work(self):
        def run():
            self.connection.verify()
            self.client.verify_backend_bundle()
            command=Path(self.connection.adapter_path).parent/'context_runtime.py'
            proc=subprocess.run([self.connection.python_path,'-I','-X','utf8',str(command),'--profile',self.connection.profile_path,'work'],env=environment(),capture_output=True,timeout=600,check=False)
            if proc.returncode:raise DesktopError('CORE_WORKER_FAILED')
            return self.request('OPERATION',{'operation_id':self.ids['operation_id']}) if self.ids['operation_id'] else {'state':'IDLE'}
        self.call(run,self.apply_job)

    def stop(self):
        op='stop-'+uuid.uuid4().hex
        def run():
            self.stop_client.handshake()
            return self.stop_client.request({'type':'durable.stop','requestId':op})['result']['library']['data']
        self.call(run,lambda r:self.status.set('STOP: '+r['control_ack']+'; текущие эффекты требуют проверки.'),priority=True)

    def control(self):
        def applied(r):
            self.status.set('Core остановлен' if r['stopped'] else 'Core разрешает новые задания')
            if r['stopped']:
                from tkinter import messagebox
                if messagebox.askyesno('Продолжить','Разрешить новые задания? Старые отменённые задания не возобновятся.',parent=self.window):
                    self.call(lambda:self.client.request({'type':'durable.control.resume','expectedEpoch':r['epoch']}))
        self.read('CONTROL',{},applied)

    def search(self,offset):
        def apply(r):
            self.rows=r['rows'];self.offset=r['offset'];self.next_offset=r['next_offset'];self.listbox.delete(0,'end')
            for row in self.rows:self.listbox.insert('end',row['source_ref']['source_key']+' — '+row['snippet'].replace('\n',' ')[:180])
            self.status.set('Страница '+str(offset)+': '+r['state']+('; есть продолжение' if self.next_offset is not None else '; конец выдачи'))
        args={'query':self.query.get(),'offset':offset,'limit':20,'history':self.history_filter.get()}
        if self.project_filter.get():args['project']=self.project_filter.get()
        if self.time_filter.get():args['as_of']=int(self.time_filter.get())
        self.read('SEARCH',args,apply)

    def next(self):
        if self.next_offset is not None:self.history.append(self.offset);self.search(self.next_offset)

    def previous(self):
        if self.history:self.search(self.history.pop())

    def selected(self,_event=None):
        if self.listbox.curselection():
            self.preview_cursor=0
            row=self.rows[self.listbox.curselection()[0]];self.ref_start.set('0');self.ref_end.set(str(row['total_bytes']))

    def ref(self):
        row=self.rows[self.listbox.curselection()[0]]
        return {**row['source_ref'],'start':int(self.ref_start.get()),'end':int(self.ref_end.get())}

    def read_range(self,cursor):
        ref=self.ref();length=ref['end']-ref['start']
        if cursor>=length and length:self.status.set('Конец выбранного диапазона.');return
        self.preview_cursor=cursor;start=ref['start']+cursor
        self.read('READ',{'source_ref':{**ref,'start':start,'end':min(ref['end'],start+8192)}})

    def adopt(self):
        if not self.existing_ids:
            self.status.set('Выберите источник в основном окне и заново откройте окно контекста.');return
        self.submit('ADOPT_ITEM',{'item_id':self.existing_ids.pop(0)})

    def annotation(self):
        ref=self.ref();project=simpledialog.askstring('Проект','Ключ проекта:',parent=self.window)
        if not project:return
        note=simpledialog.askstring('Коррекция','Проверенная локальная заметка:',parent=self.window)
        if not note:return
        valid_from=simpledialog.askinteger('Применимость','Начало (Unix seconds), отмена = без ограничения:',minvalue=0,parent=self.window)
        valid_until=simpledialog.askinteger('Применимость','Конец, исключая границу; отмена = без ограничения:',minvalue=0,parent=self.window)
        supersedes=simpledialog.askstring('Версии','Ревизия, которую исправляет источник (можно пусто):',parent=self.window)
        conflict=simpledialog.askstring('Конфликт','Общая группа конфликтующих утверждений (можно пусто):',parent=self.window)
        self.submit('ANNOTATE',{'source_ref':ref,'annotation':{'project':project,'valid_from':valid_from,'valid_until':valid_until,'supersedes':supersedes or None,'conflict_group':conflict or None,'note':note}})

    def capture(self):
        path=filedialog.askopenfilename(parent=self.window)
        if path:
            key=simpledialog.askstring('Источник','Стабильный ключ источника (буквы, цифры, _.-):',initialvalue='source',parent=self.window)
            if key:self.submit('CAPTURE',{'path':path,'source_key':key})

    def select(self):
        reason=simpledialog.askstring('WHY_THIS_PACKET','Почему этот диапазон нужен для цели?',parent=self.window)
        if reason:
            args={'rows':[{'source_ref':self.ref(),'reason':reason}]}
            if self.ids['selection_id']:args['parent']=self.ids['selection_id']
            self.submit('SELECT',args)

    def remove(self):
        ordinal=simpledialog.askinteger('Корзина','Номер диапазона для удаления:',minvalue=0,parent=self.window)
        if ordinal is not None:self.submit('REMOVE_RANGE',{'selection_id':self.ids['selection_id'],'ordinal':ordinal})

    def build(self):self.submit('BUILD_PACKET',{'selection_id':self.ids['selection_id'],'goal':self.goal.get(),'criteria':[x.strip() for x in self.criteria.get().split(';') if x.strip()]})
    def project(self):self.submit('PROJECT',{'packet_id':self.ids['packet_id'],'destination':self.destination.get()})
    def export(self):
        output=filedialog.asksaveasfilename(title='Новая папка экспорта',parent=self.window)
        if output:self.submit('EXPORT',{'projection_id':self.ids['projection_id'],'output':output,'destination':self.destination.get()})
    def result(self):
        path=filedialog.askopenfilename(title='JSON AI-результата',parent=self.window)
        if path:self.submit('RESULT',{'path':path,'result_id':'result-'+uuid.uuid4().hex})
    def need(self):
        path=filedialog.askopenfilename(title='Точный NEED_CONTEXT JSON',parent=self.window)
        if path:
            with Path(path).open('rb') as stream:raw=stream.read(12_001)
            if len(raw)>12_000:raise ValueError('CONTEXT_FRAME_LIMIT')
            self.submit('NEED_CONTEXT',{'request':json.loads(raw)})
    def folder_job(self,action):
        output=filedialog.asksaveasfilename(title='Новая папка результата',parent=self.window)
        if output:self.submit(action,{'output':output})
    def restore(self):
        backup=filedialog.askdirectory(title='Проверенный backup',parent=self.window);output=filedialog.asksaveasfilename(title='Новая папка восстановленной копии',parent=self.window)
        if backup and output:self.submit('RESTORE_COPY',{'backup':backup,'output':output})
    def sync_import(self):
        bundle=filedialog.askdirectory(title='Офлайн-снимок',parent=self.window)
        if bundle:self.submit('SYNC_IMPORT',{'bundle':bundle})
    def delete(self):
        from tkinter import messagebox
        key=self.ref()['source_key']
        def apply(r):
            if messagebox.askyesno('Удаление',f"Версии: {r['versions']}; зависимые пакеты: {r['dependent_packets']}. Скрыть источник с сохраняемым tombstone?",parent=self.window):self.submit('DELETE',{'source_key':key})
        self.read('DELETION_IMPACT',{'source_key':key},apply)
    def close(self):
        self.closed=True;self.client.close();self.stop_client.close();self.window.after_cancel(self.after);self.window.destroy()
