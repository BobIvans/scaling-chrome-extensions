#!/usr/bin/env python3
"""Small local desktop FRONT-END prototype for the bundled archive CLI.
No Chrome, model, internet, voice control, bot execution or general-purpose shell.
UI availability and screen-reader behavior must be tested on the target Windows PC.
"""
from pathlib import Path
import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class Desktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('OCC — Local Evidence Archive (prototype)')
        self.geometry('1000x680')
        self.events = queue.Queue()
        self.running = False
        self.source, self.archive = tk.StringVar(), tk.StringVar()
        self.status = tk.StringVar(value='Local only. Originals may contain private data. Do not upload without review.')
        frame = ttk.Frame(self, padding=12); frame.pack(fill='both', expand=True)
        for row, title, variable in [(0, 'Source folder / Git repository', self.source), (1, 'Archive folder (outside source)', self.archive)]:
            ttk.Label(frame, text=title).grid(row=row*2, column=0, sticky='w')
            entry = ttk.Entry(frame, textvariable=variable); entry.grid(row=row*2+1, column=0, sticky='ew', pady=(0,10))
            ttk.Button(frame, text='Browse '+str(row+1), command=lambda v=variable:self.browse(v)).grid(row=row*2+1, column=1, padx=6)
        frame.columnconfigure(0, weight=1)
        actions = ttk.Frame(frame); actions.grid(row=4, column=0, columnspan=2, sticky='ew')
        options = [('Archive folder', 'folder'), ('Archive Git HEAD', 'git'), ('Verify archive', 'verify'),
                   ('Export all UTF-8 text', 'text'), ('Static code catalog', 'catalog')]
        for title, command in options:
            ttk.Button(actions, text=title, command=lambda c=command:self.launch(c)).pack(side='left', padx=3, pady=8)
        ttk.Label(frame, textvariable=self.status, wraplength=940).grid(row=5,column=0,columnspan=2,sticky='w',pady=8)
        self.log = tk.Text(frame, wrap='word', height=24, state='disabled')
        self.log.grid(row=6, column=0, columnspan=2, sticky='nsew')
        frame.rowconfigure(6,weight=1)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def browse(self, var):
        value = filedialog.askdirectory(mustexist=False)
        if value: var.set(value)

    def launch(self, command):
        if self.running:
            messagebox.showinfo('Already running', 'This prototype allows one archive task at a time.'); return
        if not self.archive.get() or (command in {'folder','git'} and not self.source.get()):
            messagebox.showerror('Missing path', 'Select the source and archive folders.'); return
        args = [sys.executable, str(Path(__file__).with_name('archive_tool.py')), command]
        if command in {'folder','git'}:
            args += ['--source', self.source.get(), '--out', self.archive.get()]
        else:
            args += ['--archive', self.archive.get()]
            if command in {'text','catalog'}:
                dest = filedialog.askdirectory(title='Select new or empty export folder', mustexist=False)
                if not dest: return
                args += ['--out',dest]
        self.running=True
        self.status.set('Running local archive operation. No cloud or bot commands are invoked.')
        def worker():
            try:
                p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     encoding='utf-8', errors='replace', shell=False)
                assert p.stdout is not None
                for line in p.stdout: self.events.put(('log',line))
                self.events.put(('done',p.wait()))
            except OSError as exc:
                self.events.put(('log',str(exc)+'\n')); self.events.put(('done',2))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='log':
                    self.log.configure(state='normal'); self.log.insert('end',value); self.log.see('end'); self.log.configure(state='disabled')
                else:
                    self.running=False; self.status.set(f'Finished. Exit code: {value}. Inspect the receipt; completion does not mean semantic correctness.')
        except queue.Empty: pass
        self.after(100,self.poll)

    def close(self):
        if self.running:
            messagebox.showinfo('Operation active','Do not interrupt a write by closing this prototype. Inspect the terminal if recovery is needed.'); return
        self.destroy()

if __name__=='__main__':
    Desktop().mainloop()
