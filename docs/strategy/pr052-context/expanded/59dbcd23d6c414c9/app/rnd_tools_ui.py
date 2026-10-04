"""Tk launcher for the shipped offline R&D tools. Never executes imported code."""
import argparse
import datetime as dt
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

BASE = Path(__file__).resolve().parents[1] / 'rnd_v2'

class ToolsWindow:
    def __init__(self, root, log_dir):
        self.root, self.log_dir = root, Path(log_dir)
        self.process = None
        self.log_handle = None
        self.stopped = False
        self.buttons = []
        root.title('SCE R&D — офлайн контекст и доказательства')
        root.geometry('1040x650')
        top = ttk.Frame(root, padding=10); top.pack(fill='x')
        for title, fn in [('Разметить context pack', self.label), ('Контекст по цели', self.goal),
                          ('Сравнить версии', self.diff), ('Python code smells', self.smells),
                          ('Проверить receipts', self.qualify)]:
            button = ttk.Button(top, text=title, command=fn)
            button.pack(side='left', padx=3); self.buttons.append(button)
        options=ttk.Frame(root,padding=8);options.pack(fill='x')
        self.all_context=tk.BooleanVar(value=False)
        ttk.Checkbutton(options,text='Контекст по цели: включить все текстовые фрагменты',variable=self.all_context).pack(side='left')
        ttk.Button(options,text='STOP',command=self.stop).pack(side='right')
        ttk.Label(root,text='Все инструменты локальные. Теги и smells — кандидаты. Receipts проверяют заданные критерии; live не разрешается.',padding=8).pack(fill='x')
        self.log=tk.Text(root,wrap='word',font=('Consolas',10))
        self.log.pack(fill='both',expand=True,padx=8,pady=8)
        self.status=ttk.Label(root,text='Выберите действие.',padding=8);self.status.pack(fill='x')
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.after(150,self.poll)

    def folder(self,title):return filedialog.askdirectory(title=title)

    def destination(self,prefix):
        parent=self.folder('Родительская папка для НОВОГО результата')
        if not parent:return None
        return str(Path(parent)/(prefix+'_'+dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')))

    def label(self):
        pack=self.folder('Экспортированный context pack с index.json и files.jsonl')
        if not pack:return
        dest=self.destination('labels')
        if not dest:return
        namespace=simpledialog.askstring('Источник','Стабильное имя источника для сравнения версий:',initialvalue='my-repository')
        if not namespace:return
        self.launch('labeling/label_context.py',['build',pack,dest,'--namespace',namespace],dest)

    def goal(self):
        labels=self.folder('Папка разметки с labels.jsonl и manifest.json')
        if not labels:return
        goal=simpledialog.askstring('Цель','Какую задачу продолжить?')
        if not goal:return
        dest=self.destination('goal_context')
        if not dest:return
        args=['goal',labels,dest,'--goal',goal]
        if self.all_context.get():args.append('--include-all')
        self.launch('labeling/label_context.py',args,dest)

    def diff(self):
        old=self.folder('Прежняя папка labels')
        if not old:return
        new=self.folder('Новая папка labels с тем же namespace')
        if not new:return
        out=filedialog.asksaveasfilename(title='Новый JSON разницы версий',defaultextension='.json')
        if out:self.launch('labeling/label_context.py',['diff',old,new,out],out)

    def smells(self):
        repo=self.folder('Папка Python проекта для чтения')
        if not repo:return
        out=filedialog.asksaveasfilename(title='НОВЫЙ JSON отчёт ВНЕ анализируемого проекта',defaultextension='.json')
        if out and Path(out).exists():
            messagebox.showinfo('Новый отчёт','Выберите новое имя, чтобы прежний отчёт не выглядел результатом прерванного запуска.');return
        if out:self.launch('smells/repo_smells.py',[repo,'--output',out],out)

    def qualify(self):
        plan=filedialog.askopenfilename(title='План qualification JSON',filetypes=[('JSON','*.json')])
        if not plan:return
        evidence=self.folder('Корень evidence артефактов')
        if not evidence:return
        receipts=filedialog.askopenfilenames(title='Receipts JSON (отмена — проверить отсутствие evidence)',filetypes=[('JSON','*.json')])
        out=filedialog.asksaveasfilename(title='НОВЫЙ JSON отчёт ВНЕ корня evidence',defaultextension='.json')
        if not out:return
        args=['--plan',plan,'--evidence-root',evidence,'--output',out]
        for r in receipts:args.extend(['--receipt',r])
        self.launch('web3/qualification.py',args,out)

    def launch(self,relative,args,destination):
        if self.process:return
        script=BASE/relative
        try:
            if not script.is_file():raise ValueError('Модуль отсутствует: '+str(script))
            self.log_dir.mkdir(parents=True,exist_ok=True)
            self.log_path=self.log_dir/(dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.log')
            self.log_handle=self.log_path.open('wb')
            flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            self.process=subprocess.Popen([sys.executable,'-u',str(script),*args],stdin=subprocess.DEVNULL,
                stdout=self.log_handle,stderr=subprocess.STDOUT,shell=False,creationflags=flags,
                env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'})
            self.destination_path=destination;self.stopped=False
            self.log.delete('1.0','end')
            self.status.config(text='Выполняется локально. Полный журнал: '+str(self.log_path))
            for b in self.buttons:b.config(state='disabled')
        except Exception as exc:
            if self.log_handle:self.log_handle.close();self.log_handle=None
            self.process=None
            messagebox.showerror('R&D',str(exc))

    def poll(self):
        if self.process:
            try:
                # Display tail only; the full log remains on disk. Source context is not truncated.
                with self.log_path.open('rb') as f:
                    f.seek(max(0,self.log_path.stat().st_size-60000));tail=f.read().decode('utf-8',errors='replace')
                self.log.delete('1.0','end');self.log.insert('1.0',tail)
            except OSError:pass
            code=self.process.poll()
            if code is not None:
                self.log_handle.close();self.log_handle=None;self.process=None
                for b in self.buttons:b.config(state='normal')
                state='STOP: операция прервана; проверьте неполные результаты.' if self.stopped else ('Завершено; читайте статусы в отчёте.' if code==0 else f'Exit {code}: критерии не пройдены или ошибка; смотрите журнал.')
                self.status.config(text=state+' '+self.destination_path)
        self.root.after(150,self.poll)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.stopped=True;self.process.terminate()

    def close(self):
        if self.process:
            self.stop();self.status.config(text='Останавливается. Закройте окно после завершения процесса.');return
        self.root.destroy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--log-dir');a=p.parse_args()
    root=tk.Tk()
    logs=a.log_dir or filedialog.askdirectory(title='Выберите папку журналов R&D')
    if not logs:root.destroy();return
    ToolsWindow(root,logs);root.mainloop()

if __name__=='__main__':main()
