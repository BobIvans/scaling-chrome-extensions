"""Local search and selected-context drafts, independent of Chrome."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from desktop import SHELL_VERSION
from desktop.client import Connection, DesktopClient, DesktopError, PROTOCOL
from desktop.draft import save_draft, save_manifest
from desktop.preflight import check
from desktop.state import Fence

MESSAGES = {
    'DESKTOP_SETUP_REQUIRED': 'Нужны установленный backend, профиль и готовая библиотека. Откройте настройки.',
    'DESKTOP_RUNTIME_TK_REQUIRED': 'Выберите Python 3.11+ с установленным Tkinter.',
    'DESKTOP_PROTOCOL_UNAVAILABLE': 'Backend не поддерживает Desktop. Обновите установленный backend и переподключитесь.',
    'DESKTOP_HANDSHAKE_REQUIRED': 'Сначала подключитесь к библиотеке.',
    'DESKTOP_ADAPTER_CHANGED': 'Версия backend изменилась. Проверьте путь и SHA-256 в настройках.',
    'DESKTOP_PROFILE_CHANGED': 'Профиль или библиотека изменились. Переподключитесь.',
    'DESKTOP_TIMEOUT': 'Чтение заняло слишком долго. Можно повторить запрос.',
    'DESKTOP_CANCELLED': 'Операция отменена.',
    'DESKTOP_CONTEXT_DIGEST': 'Контекст не прошёл проверку целостности.',
    'DESKTOP_OUTPUT_CONFLICT': 'Папка результата уже существует. Выберите новое имя.',
    'DESKTOP_OUTPUT_FAILED': 'Не удалось сохранить документ. Проверьте место на диске и права доступа.',
    'DESKTOP_CAPABILITY_UNAVAILABLE': 'Этот backend ещё не поддерживает выбранную операцию.',
    'DESKTOP_ITEM_SCHEMA_UNAVAILABLE': 'Формат источника требует обновления Desktop.',
    'DESKTOP_CLASSIFIER_UNAVAILABLE': 'Версия проверки форматов требует обновления Desktop.',
    'FORMAT_BACKFILL_REQUIRED': 'Для выбранного источника ещё не проверен формат. Обновите библиотеку и повторите поиск.',
    'DESKTOP_DRAFT_FIELDS_REQUIRED': 'Заполните цель, область и критерии.',
    'ITEM_OUTSIDE_SCOPE_OR_STALE': 'Выбранный источник изменился. Повторите поиск.',
}


class App:
    def __init__(self, root, config_path):
        self.root, self.config_path = root, config_path.absolute()
        self.owner_thread = threading.get_ident()
        self.fence = Fence()
        self.client = None
        self.connection = None
        self.report = None
        self.context = None
        self.items = []
        self.events = queue.Queue(maxsize=8)
        self.worker = None
        self.worker_cancel = threading.Event()
        self.closing = False
        root.title('Context Library — Desktop ' + SHELL_VERSION)
        root.geometry('1040x800')
        root.minsize(780, 620)
        body = ttk.Frame(root, padding=12)
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(5, weight=1)
        body.rowconfigure(7, weight=1)
        self.status = tk.StringVar(value='Выберите установленную библиотеку в настройках.')
        self.location = tk.StringVar(value='')
        self.namespace = tk.StringVar()
        self.query = tk.StringVar()
        self.snapshot = tk.StringVar()
        self.repository = tk.StringVar()
        toolbar = ttk.Frame(body)
        toolbar.grid(row=0, column=0, columnspan=3, sticky='ew')
        ttk.Button(toolbar, text='Настройки', command=self.configure).pack(side='left')
        ttk.Button(toolbar, text='Подключиться', command=self.connect).pack(side='left', padx=6)
        ttk.Button(toolbar, text='Отмена (Esc)', command=self.cancel).pack(side='left')
        ttk.Button(toolbar, text='Контекст и задания', command=self.open_library).pack(side='right', padx=6)
        ttk.Button(toolbar, text='Диагностика', command=self.diagnostics).pack(side='right')
        ttk.Label(body, textvariable=self.status, wraplength=940).grid(row=1, column=0, columnspan=3, sticky='w', pady=(8, 3))
        ttk.Label(body, textvariable=self.location, wraplength=940).grid(row=2, column=0, columnspan=3, sticky='w')
        ttk.Label(body, text='Библиотека').grid(row=3, column=0, sticky='w', pady=6)
        self.ns_box = ttk.Combobox(body, textvariable=self.namespace, state='readonly')
        self.ns_box.grid(row=3, column=1, sticky='ew')
        ttk.Label(body, text='Поиск').grid(row=4, column=0, sticky='w')
        search_entry = ttk.Entry(body, textvariable=self.query)
        search_entry.grid(row=4, column=1, sticky='ew')
        search_entry.bind('<Return>', lambda _event: self.search())
        self.search_button = ttk.Button(body, text='Найти', command=self.search, state='disabled')
        self.search_button.grid(row=4, column=2, padx=(8, 0))
        results_frame = ttk.Labelframe(body, text='Лучшие совпадения (до 20 результатов)', padding=4)
        results_frame.grid(row=5, column=0, columnspan=3, sticky='nsew', pady=8)
        self.results = tk.Listbox(results_frame, selectmode='extended', exportselection=False, height=8)
        scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.results.yview)
        self.results.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.results.pack(fill='both', expand=True)
        self.results.bind('<<ListboxSelect>>', self.selection_changed)
        self.context_button = ttk.Button(body, text='Прочитать выбранные источники (до 10)',
                                         command=self.read_context, state='disabled')
        self.context_button.grid(row=6, column=0, columnspan=3, sticky='w')
        self.preview = tk.Text(body, height=8, wrap='word', state='disabled')
        self.preview.grid(row=7, column=0, columnspan=3, sticky='nsew', pady=8)
        self.goal, self.scope, self.acceptance = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for row, label, variable in ((8, 'Цель', self.goal), (9, 'Область', self.scope),
                                     (10, 'Критерии', self.acceptance)):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky='w', pady=3)
            ttk.Entry(body, textvariable=variable).grid(row=row, column=1, columnspan=2, sticky='ew')
        self.save_button = ttk.Button(body, text='Сохранить TASK_DRAFT.txt', command=self.save, state='disabled')
        self.save_button.grid(row=11, column=0, columnspan=3, sticky='w', pady=8)
        inventory = ttk.Labelframe(body, text='Полный список файлов сохранённого снимка', padding=6)
        inventory.grid(row=12, column=0, columnspan=3, sticky='ew')
        inventory.columnconfigure(3, weight=1)
        ttk.Label(inventory, text='Репозиторий').grid(row=0, column=0)
        self.repo_box = ttk.Combobox(inventory, textvariable=self.repository, width=16, state='readonly')
        self.repo_box.grid(row=0, column=1, padx=6)
        ttk.Label(inventory, text='ID снимка').grid(row=0, column=2)
        ttk.Entry(inventory, textvariable=self.snapshot).grid(row=0, column=3, sticky='ew')
        self.inventory_button = ttk.Button(inventory, text='Сохранить весь список', command=self.export_inventory, state='disabled')
        self.inventory_button.grid(row=0, column=4, padx=6)
        ttk.Label(inventory, text='Снимок должен быть уже собран backend. Список читается до конца; размер репозитория не ограничен.',
                  wraplength=920).grid(row=1, column=0, columnspan=5, sticky='w', pady=(4, 0))
        root.bind('<Escape>', lambda _event: self.cancel())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.query.trace_add('write', self.query_changed)
        self.namespace.trace_add('write', self.query_changed)
        self.snapshot.trace_add('write', self.query_changed)
        self.repository.trace_add('write', self.query_changed)
        self.after_id = root.after(40, self.drain)
        if self.config_path.is_file():
            root.after(0, self.connect)

    def assert_main(self):
        assert threading.get_ident() == self.owner_thread, 'Tk must stay on its owner thread'

    def busy(self):
        return self.worker is not None and self.worker.is_alive()

    def update_controls(self):
        ready = self.client is not None and self.client.identity is not None and not self.closing
        idle = ready and not self.busy()
        self.search_button.configure(state='normal' if idle else 'disabled')
        self.context_button.configure(state='normal' if idle and self.results.curselection() else 'disabled')
        self.save_button.configure(state='normal' if idle and self.context is not None else 'disabled')
        manifest = idle and 'durable.repo.manifest' in self.client.info['capabilities'] if ready else False
        self.inventory_button.configure(state='normal' if manifest else 'disabled')

    def open_library(self):
        if self.connection is None:
            self.status.set('Сначала подключитесь к библиотеке.')
            return
        from desktop.library import LibraryWindow
        LibraryWindow(self.root,self.connection,self.namespace.get(),existing_ids=[self.items[i]['id'] for i in self.results.curselection()])

    def clear_context(self):
        self.context = None
        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        self.preview.configure(state='disabled')

    def query_changed(self, *_args):
        if self.closing:
            return
        self.fence.invalidate(namespace=self.namespace.get())
        self.worker_cancel.set()
        if self.client:
            self.client.cancel()
        self.clear_context()
        self.items = []
        self.results.delete(0, 'end')
        self.update_controls()

    def selection_changed(self, _event=None):
        if self.closing:
            return
        self.fence.invalidate()
        self.worker_cancel.set()
        if self.client:
            self.client.cancel()
        self.clear_context()
        self.update_controls()

    def cancel(self):
        self.fence.invalidate()
        self.worker_cancel.set()
        if self.client:
            self.client.cancel()
        self.status.set('Операция отменена.')
        self.update_controls()

    def start(self, operation, work, apply):
        self.assert_main()
        if self.busy() or self.closing:
            self.status.set('Дождитесь завершения отмены текущего чтения.')
            return
        ticket = self.fence.begin(operation)
        cancel = self.worker_cancel = threading.Event()

        def emit(kind, value):
            while not self.closing:
                try:
                    self.events.put((ticket, kind, value, apply), timeout=0.05)
                    return
                except queue.Full:
                    if cancel.is_set():
                        return

        def progress(count, total):
            # Progress is expendable. A bounded queue never scales with corpus size.
            try:
                self.events.put_nowait((ticket, 'progress', (count, total), apply))
            except queue.Full:
                pass

        def run():
            try:
                emit('result', work(cancel, progress))
            except DesktopError as exc:
                emit('error', exc.code)
            except (OSError, ValueError, KeyError, TypeError):
                emit('error', 'DESKTOP_OPERATION_FAILED')

        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()
        self.status.set('Чтение… Можно отменить или закрыть окно.')
        self.update_controls()

    def drain(self):
        self.assert_main()
        if self.closing:
            if self.busy() or self.client is not None and self.client.busy:
                self.after_id = self.root.after(40, self.drain)
            else:
                self.root.destroy()
            return
        for _ in range(8):
            try:
                ticket, kind, value, apply = self.events.get_nowait()
            except queue.Empty:
                break
            if not self.fence.accepts(ticket):
                continue
            if kind == 'error':
                self.status.set(MESSAGES.get(value, 'Операция не завершена. Код: ' + value))
                self.clear_context()
            elif kind == 'progress':
                self.status.set(f'Сохранено строк: {value[0]} из {value[1]}')
            else:
                apply(value)
        self.update_controls()
        self.after_id = self.root.after(40, self.drain)

    def configure(self):
        if self.busy():
            self.cancel()
            return
        window = tk.Toplevel(self.root)
        window.title('Подключение к установленной библиотеке')
        window.transient(self.root)
        window.columnconfigure(1, weight=1)
        current = self.connection.as_dict() if self.connection else {}
        values = {}
        fields = [('python_path', 'Python'), ('adapter_path', 'native_adapter.py'),
                  ('profile_path', 'Профиль backend'), ('expected_adapter_sha256', 'SHA-256 backend'),
                  ('preferred_namespace', 'Библиотека (необязательно)')]
        for row, (key, label) in enumerate(fields):
            ttk.Label(window, text=label).grid(row=row, column=0, sticky='w', padx=8, pady=4)
            variable = values[key] = tk.StringVar(value=current.get(key) or '')
            ttk.Entry(window, textvariable=variable, width=64).grid(row=row, column=1, padx=8, sticky='ew')
            if key.endswith('_path'):
                def choose(v=variable):
                    path = filedialog.askopenfilename(parent=window)
                    if path:
                        v.set(path)
                ttk.Button(window, text='Выбрать', command=choose).grid(row=row, column=2, padx=8)
        ttk.Label(window, text='Проверьте SHA-256 установленного backend перед сохранением. Данные backend не копируются.',
                  wraplength=720).grid(row=5, column=0, columnspan=3, padx=8, pady=6)

        def save_settings():
            try:
                value = {'schema': 'occ.desktop-connection.v1', 'protocol': PROTOCOL,
                         **{key: variable.get() for key, variable in values.items()}}
                value['preferred_namespace'] = value['preferred_namespace'] or None
                connection = Connection.from_dict(value)
                connection.verify()
                raw = json.dumps(connection.as_dict(), ensure_ascii=False, indent=2).encode('utf-8')
                # Configuration is shell state, never a backend profile mutation.
                import os
                import tempfile
                fd, name = tempfile.mkstemp(prefix='.connection-', dir=self.config_path.parent)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(name, self.config_path)
                finally:
                    Path(name).unlink(missing_ok=True)
                window.destroy()
                self.connect()
            except (DesktopError, OSError) as exc:
                messagebox.showerror('Настройка', MESSAGES.get(str(exc), str(exc)), parent=window)

        ttk.Button(window, text='Проверить и сохранить', command=save_settings).grid(row=6, column=0, columnspan=3, pady=8)

    def connect(self):
        if self.busy():
            self.cancel()
            return
        self.fence.invalidate(reconnect=True)
        self.clear_context()
        self.location.set('')
        self.report = None
        if self.client:
            self.client.close()
        try:
            self.connection = Connection.load(self.config_path)
        except DesktopError as exc:
            self.client = None
            self.status.set(MESSAGES.get(exc.code, exc.code))
            self.update_controls()
            return
        self.client = client = DesktopClient(self.connection)

        def work(cancel, _progress):
            report = check(self.connection)
            if cancel.is_set():
                raise DesktopError('DESKTOP_CANCELLED')
            hello = client.handshake()
            repos = client.request({'type': 'durable.repo.list'})['result']['repositories']
            return report, hello, repos

        def connected(value):
            self.report, hello, repos = value
            info = hello['result']['info']
            self.ns_box.configure(values=info['namespaces'])
            self.namespace.set(self.connection.preferred_namespace or info['namespaces'][0])
            self.repo_box.configure(values=[v['repository'] for v in repos])
            self.repository.set(repos[0]['repository'] if repos else '')
            self.fence.invalidate(namespace=self.namespace.get(), identity=hello['adapter_context'])
            self.location.set('Данные: ' + info['store_path'] + ' · Desktop ' + SHELL_VERSION)
            self.status.set('Подключено. Поиск показывает лучшие совпадения; полный список файлов сохраняется отдельно.')
        self.start('durable.info', work, connected)

    def search(self):
        if self.client is None or self.client.identity is None:
            return
        self.clear_context()
        request = {'type': 'durable.search', 'namespace': self.namespace.get(), 'query': self.query.get(), 'limit': 20}
        client = self.client

        def apply(reply):
            self.items = reply['result']['items']
            self.results.delete(0, 'end')
            for item in self.items:
                self.results.insert('end', item['source_key'] + ' — ' + item['snippet'].replace('\n', ' '))
            self.status.set(f'Лучшие совпадения: {len(self.items)} (TOP_MATCHES_BOUNDED).')
        self.start('durable.search', lambda _cancel, _progress: client.request(request), apply)

    def read_context(self):
        indexes = self.results.curselection()
        if not 1 <= len(indexes) <= 10:
            self.status.set('Выберите от 1 до 10 источников для одного документа.')
            return
        request = {'type': 'durable.context', 'namespace': self.namespace.get(),
                   'ids': [self.items[i]['id'] for i in indexes], 'maxBytes': 48_000}
        client = self.client

        def apply(reply):
            self.context = reply['result']['context']
            self.preview.configure(state='normal')
            self.preview.delete('1.0', 'end')
            self.preview.insert('1.0', '\n\n'.join(item['text'] for item in self.context['items']))
            self.preview.configure(state='disabled')
            self.status.set(f'Выбранный контекст: {len(self.context["items"])} источников, {self.context["bytes"]} байт.')
        self.start('durable.context', lambda _cancel, _progress: client.request(request), apply)

    def output_folder(self, name):
        parent = filedialog.askdirectory(parent=self.root, title='Выберите папку для результата')
        if not parent:
            return None
        from tkinter.simpledialog import askstring
        child = askstring('Новая папка', 'Имя новой папки результата:', initialvalue=name, parent=self.root)
        if not child or child in {'.', '..'} or any(char in child for char in '/\\\0'):
            return None
        return Path(parent) / child

    def save(self):
        if self.context is None:
            return
        output = self.output_folder('context-draft')
        if output is None:
            return
        context, identity = self.context, dict(self.client.identity)
        goal, scope, criteria = self.goal.get(), self.scope.get(), self.acceptance.get()

        def work(cancel, _progress):
            if cancel.is_set():
                raise DesktopError('DESKTOP_CANCELLED')
            return save_draft(output, context, identity, goal, scope, criteria, cancel=cancel)
        self.start('local.draft', work, lambda _value: self.status.set('Документ сохранён: ' + str(output / 'TASK_DRAFT.txt')))

    def export_inventory(self):
        output = self.output_folder('repository-manifest')
        if output is None:
            return
        client, repository, snapshot = self.client, self.repository.get(), self.snapshot.get()
        self.start('durable.repo.manifest',
                   lambda cancel, progress: save_manifest(output, client, repository, snapshot,
                                                         cancel=cancel, progress=progress),
                   lambda value: self.status.set(f'Полный список сохранён: {value["rows"]} файлов · {output}'))

    def diagnostics(self):
        window = tk.Toplevel(self.root)
        window.title('Диагностика подключения')
        view = tk.Text(window, width=96, height=24, wrap='word')
        view.pack(fill='both', expand=True)
        value = self.report or {'state': 'SETUP_REQUIRED', 'shell_version': SHELL_VERSION}
        view.insert('1.0', json.dumps(value, ensure_ascii=False, indent=2))
        view.configure(state='disabled')

    def close(self):
        self.fence.close()
        self.closing = True
        self.worker_cancel.set()
        if self.client:
            self.client.close()
        self.update_controls()
        # drain() keeps the event loop responsive until the child is reaped.


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).parent / 'connection.json')
    args = parser.parse_args(argv)
    try:
        root = tk.Tk()
    except tk.TclError:
        print('DESKTOP_RUNTIME_TK_REQUIRED', file=sys.stderr)
        return 1
    App(root, args.config)
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
