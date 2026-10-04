"""Windows-compatible Tk desktop shell; no Chrome or network service required."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from context_store import Store

class Desktop:
    def __init__(self, root, library):
        self.root, self.library = root, Path(library)
        self.store = Store(library)
        self.busy = False
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.offset, self.page_size, self.seq = 0, 200, 0
        self.sid, self.entry = None, None
        self.rows = {}
        root.title('SCE Desktop — локальная библиотека контекста [прототип]')
        root.geometry('1240x790')
        root.minsize(900, 620)
        bar = ttk.Frame(root, padding=8)
        bar.pack(fill='x')
        for label, fn in [('Импорт ZIP / файлов', self.import_files), ('Импорт папки', self.import_folder),
                          ('Продолжить ZIP', self.resume), ('Экспорт ВСЕГО snapshot', self.export),
                          ('STOP', self.cancel.set)]:
            ttk.Button(bar, text=label, command=fn).pack(side='left', padx=3)
        ttk.Label(root, text='Локально • оригиналы + полные пути • число записей не ограничено настройкой • без автоматической отправки в AI', padding=6).pack(fill='x')
        ttk.Button(root, text='R&D: разметка / контекст цели / code smells / evidence', command=self.rnd_tools).pack(fill='x', padx=8)
        selector = ttk.Frame(root, padding=6)
        selector.pack(fill='x')
        self.snap = ttk.Combobox(selector, state='readonly', width=90)
        self.snap.pack(side='left', fill='x', expand=True)
        self.snap.bind('<<ComboboxSelected>>', self.choose_snapshot)
        ttk.Button(selector, text='Обновить', command=self.refresh_snapshots).pack(side='left')
        searchbar = ttk.Frame(root, padding=6)
        searchbar.pack(fill='x')
        ttk.Label(searchbar, text='Поиск по пути или тексту:').pack(side='left')
        self.query = ttk.Entry(searchbar, width=45)
        self.query.pack(side='left', fill='x', expand=True, padx=6)
        self.query.bind('<Return>', lambda e: self.search())
        ttk.Button(searchbar, text='Найти', command=self.search).pack(side='left')
        ttk.Button(searchbar, text='← Записи', command=lambda: self.page(-1)).pack(side='left')
        ttk.Button(searchbar, text='Записи →', command=lambda: self.page(1)).pack(side='left')
        self.count = ttk.Label(searchbar)
        self.count.pack(side='left', padx=6)
        pane = ttk.Panedwindow(root, orient='horizontal')
        pane.pack(fill='both', expand=True, padx=8)
        left, right = ttk.Frame(pane), ttk.Frame(pane)
        pane.add(left, weight=1)
        pane.add(right, weight=2)
        self.tree = ttk.Treeview(left, columns=('path','state','bytes'), show='headings', selectmode='browse')
        for key, title, width in [('path','Полный путь',350),('state','Состояние',120),('bytes','Байты',80)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        scroll = ttk.Scrollbar(left, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self.select_entry)
        textbar = ttk.Frame(right)
        textbar.pack(fill='x')
        ttk.Button(textbar, text='← Текст', command=lambda: self.text_page(-1)).pack(side='left')
        ttk.Button(textbar, text='Текст →', command=lambda: self.text_page(1)).pack(side='left')
        self.text_count = ttk.Label(textbar)
        self.text_count.pack(side='left')
        ttk.Button(textbar, text='Разобрать ChatGPT JSON', command=self.parse_chat).pack(side='right')
        self.preview = tk.Text(right, wrap='word', font=('Consolas',10))
        sy = ttk.Scrollbar(right, command=self.preview.yview)
        self.preview.configure(yscrollcommand=sy.set)
        sy.pack(side='right', fill='y')
        self.preview.pack(fill='both', expand=True)
        notes = ttk.Frame(root, padding=8)
        notes.pack(fill='x')
        ttk.Label(notes, text='Теги:').pack(side='left')
        self.tags = ttk.Entry(notes, width=25)
        self.tags.pack(side='left', padx=4)
        ttk.Label(notes, text='Заметка:').pack(side='left')
        self.note = ttk.Entry(notes)
        self.note.pack(side='left', fill='x', expand=True, padx=4)
        ttk.Button(notes, text='Сохранить', command=self.annotate).pack(side='left')
        ttk.Button(notes, text='Открыть проект в VS Code', command=self.vscode).pack(side='left')
        ttk.Button(notes, text='PowerShell в проекте', command=self.terminal).pack(side='left')
        ttk.Button(notes, text='AI: выбранный TXT', command=self.ask_ai).pack(side='left')
        self.status = ttk.Label(root, text=str(self.library), padding=8)
        self.status.pack(fill='x')
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh_snapshots()
        root.after(100, self.poll)

    def rnd_tools(self):
        script=Path(__file__).resolve().parent/'rnd_tools_ui.py'
        subprocess.Popen([sys.executable,str(script),'--log-dir',str(self.library/'rnd_runs')],shell=False)

    def work(self, action):
        if self.busy:
            messagebox.showinfo('Задание выполняется', 'Дождитесь завершения или нажмите STOP.')
            return
        self.busy = True
        self.cancel.clear()
        self.status.config(text='Выполняется…')
        def run():
            s = None
            try:
                s = Store(self.library)
                def progress(text):
                    # Coalesce progress to avoid unbounded UI messages.
                    self.last_progress = text
                result = action(s, progress, self.cancel.is_set)
                self.events.put(('done', str(result)))
            except Exception as e:
                self.events.put(('error', str(e)))
            finally:
                if s:
                    s.close()
        self.last_progress = ''
        threading.Thread(target=run, daemon=False).start()

    def poll(self):
        if self.busy and getattr(self, 'last_progress', ''):
            self.status.config(text=self.last_progress)
        try:
            while True:
                kind, result = self.events.get_nowait()
                self.busy = False
                self.status.config(text=('Ошибка: ' if kind == 'error' else 'Готово: ') + result[:500])
                self.refresh_snapshots()
                if kind == 'error':
                    messagebox.showerror('Операция не завершена', result)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def refresh_snapshots(self):
        self.snapshots = self.store.snapshots()
        self.snap['values'] = [f'{x["created"]} | {x["state"]} | {x["source"]} | {x["id"][:8]}' for x in self.snapshots]
        if self.snapshots:
            self.snap.current(0)
            self.choose_snapshot()

    def choose_snapshot(self, event=None):
        if self.snap.current() < 0:
            return
        self.sid = self.snapshots[self.snap.current()]['id']
        self.offset = 0
        self.refresh_entries()

    def refresh_entries(self):
        if not self.sid:
            return
        try:
            total, rows = self.store.entries(self.sid, self.offset, self.page_size, self.query.get())
            self.tree.delete(*self.tree.get_children())
            self.rows = {str(r['id']):r for r in rows}
            for r in rows:
                self.tree.insert('', 'end', iid=str(r['id']), values=(r['path'],r['text_state'],r['size']))
            self.total = total
            self.count.config(text=f'{self.offset + (1 if rows else 0)}–{self.offset+len(rows)} / {total}')
        except Exception as e:
            messagebox.showerror('Поиск', str(e))

    def search(self):
        self.offset = 0
        self.refresh_entries()

    def page(self, delta):
        next_offset = self.offset + delta * self.page_size
        if 0 <= next_offset < getattr(self,'total',0):
            self.offset = next_offset
            self.refresh_entries()

    def select_entry(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.entry, self.seq = int(selected[0]), 0
        row = self.store.db.execute('SELECT tags,note FROM annotations WHERE entry=?', (self.entry,)).fetchone()
        for widget, value in [(self.tags,row['tags'] if row else ''),(self.note,row['note'] if row else '')]:
            widget.delete(0,'end')
            widget.insert(0,value)
        self.render_text()

    def render_text(self):
        if not self.entry:
            return
        text, self.text_total = self.store.text_page(self.entry,self.seq)
        row = self.store.db.execute('SELECT * FROM entries WHERE id=?',(self.entry,)).fetchone()
        self.preview.config(state='normal')
        self.preview.delete('1.0','end')
        self.preview.insert('1.0', json.dumps(dict(row),ensure_ascii=True,indent=2)+'\n\n'+text)
        self.preview.config(state='disabled')
        self.text_count.config(text=f'Страница {self.seq+1 if self.text_total else 0}/{self.text_total} — весь текст в экспорте')

    def text_page(self, delta):
        if 0 <= self.seq+delta < getattr(self,'text_total',0):
            self.seq += delta
            self.render_text()

    def import_files(self):
        paths = filedialog.askopenfilenames(title='Выберите ZIP или любые файлы')
        if paths:
            def action(s,p,c):
                results=[]
                for path in paths:
                    if c(): break
                    results.append(s.import_source(path,p,c))
                return ', '.join(results)
            self.work(action)

    def import_folder(self):
        path = filedialog.askdirectory(title='Репозиторий или папка документов')
        if path:
            self.work(lambda s,p,c:s.import_source(path,p,c))

    def resume(self):
        sid = self.sid
        if sid:
            self.work(lambda s,p,c:s.import_source('.',p,c,resume=sid))

    def export(self):
        if not self.sid:
            return
        parent = filedialog.askdirectory(title='Куда сохранить новый context pack?')
        if not parent:
            return
        size = simpledialog.askinteger('Размер TXT-части','Байт на часть (не токены):',initialvalue=200000,minvalue=4)
        if not size:
            return
        sid = self.sid
        import datetime
        dest = Path(parent) / ('context_'+sid[:8]+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        def action(s,p,c):
            index=s.export(sid,dest,size,p,c)
            return f'{dest} — {index["entries"]} записей, {len(index["parts"])} TXT'
        self.work(action)

    def parse_chat(self):
        entry = self.entry
        if entry:
            self.work(lambda s,p,c: f'{s.derive_chatgpt(entry)} сообщений. Экспортируйте snapshot для USER_MESSAGES.txt / ASSISTANT_MESSAGES.txt.')

    def annotate(self):
        if self.entry and not self.busy:
            self.store.annotate(self.entry,self.tags.get(),self.note.get())
            self.status.config(text='Теги и заметка сохранены.')

    def project_path(self):
        if not self.sid:
            return None
        snapshot = self.store.db.execute('SELECT * FROM snapshots WHERE id=?',(self.sid,)).fetchone()
        if snapshot['kind'] != 'folder':
            messagebox.showinfo('Проект','Для терминала/VS Code выберите snapshot локальной папки. ZIP не исполняется и не распаковывается в проект.')
            return None
        p = Path(snapshot['source'])
        if not p.is_dir():
            raise ValueError('Исходная папка больше не существует.')
        return p

    def vscode(self):
        try:
            path = self.project_path()
            if not path: return
            # Launch real Code.exe instead of passing untrusted paths through code.cmd.
            candidates = [Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Microsoft VS Code/Code.exe',
                          Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Microsoft VS Code/Code.exe']
            exe = next((str(p) for p in candidates if p.is_file()),None)
            if not exe:
                exe=filedialog.askopenfilename(title='Выберите исполняемый файл VS Code',filetypes=[('Executable','*.exe'),('All','*')])
            if exe:
                subprocess.Popen([exe,'--new-window',str(path)],shell=False)
        except Exception as e: messagebox.showerror('VS Code',str(e))

    def terminal(self):
        try:
            path = self.project_path()
            if not path: return
            if os.name != 'nt': raise ValueError('Эта кнопка предназначена для Windows PowerShell.')
            exe = shutil.which('powershell.exe')
            if not exe: raise ValueError('PowerShell не найден.')
            subprocess.Popen([exe,'-NoProfile','-NoExit'],cwd=path,shell=False,creationflags=subprocess.CREATE_NEW_CONSOLE)
        except Exception as e: messagebox.showerror('PowerShell',str(e))

    def ask_ai(self):
        if self.busy: return
        source=filedialog.askopenfilename(title='Выберите один TXT context pack для OpenAI API',filetypes=[('Text','*.txt')])
        if not source: return
        model=simpledialog.askstring('API model','Укажите доступный вам ID модели:',initialvalue=os.environ.get('OPENAI_MODEL',''))
        if not model: return
        goal=simpledialog.askstring('Задача','Что проверить в выбранном контексте?')
        if not goal: return
        tokens=simpledialog.askinteger('Ответ','Max output tokens:',initialvalue=4000,minvalue=1)
        if not tokens: return
        if not messagebox.askyesno('Передача контекста в OpenAI API',f'{source}\n{Path(source).stat().st_size} байт\nМодель: {model}\nЗадача: {goal}\n\nБудет отправлен весь выбранный TXT. Проверьте его на секреты. Возможна плата API. Отправить?'): return
        def action(s,p,c):
            from openai_adapter import send_file
            output,status=send_file(source,goal,model,self.library/'ai_outputs',tokens)
            if not c(): s.import_source(output/'answer.txt',p,c)
            return f'API {status}: {output}; результат модели требует проверки.'
        self.work(action)

    def close(self):
        if self.busy:
            self.cancel.set()
            messagebox.showinfo('Остановка','Отправлен STOP. Дождитесь сохранения состояния и закройте окно снова.')
            return
        self.store.close()
        self.root.destroy()

def main():
    root=tk.Tk()
    root.withdraw()
    library=filedialog.askdirectory(title='Выберите папку локальной библиотеки (вне импортируемого репозитория)')
    if not library:
        root.destroy()
        return
    root.deiconify()
    Desktop(root,library)
    root.mainloop()

if __name__=='__main__': main()
