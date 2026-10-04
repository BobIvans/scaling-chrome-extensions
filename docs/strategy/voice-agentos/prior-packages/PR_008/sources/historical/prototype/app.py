"""Offline desktop prototype: preserved repository -> catalog -> AI handoff.

Stdlib/Tkinter only. The backend never becomes an implicit PC automation runner.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

try:
    import context_pipeline as pipeline
except ImportError:
    pipeline = None


APP_TITLE = "Context Library · репозиторий → контекст → AI"
PREVIEW_BYTES = 65_536


def human_size(size: int | str | None) -> str:
    value = float(size or 0)
    for unit in ("Б", "КиБ", "МиБ", "ГиБ", "ТиБ"):
        if value < 1024 or unit == "ТиБ":
            return f"{value:.0f} {unit}" if unit == "Б" else f"{value:.1f} {unit}"
        value /= 1024
    return str(size)


def parse_labels(value: str) -> list[str]:
    """Keep user order while removing empty and duplicate labels."""
    return list(dict.fromkeys(label.strip() for label in value.split(",") if label.strip()))


def open_folder(path: Path) -> None:
    """Open an existing local directory without passing input through a shell."""
    folder = path.expanduser().resolve()
    if not folder.is_dir():
        raise ValueError("Папка результата ещё не создана.")
    if sys.platform == "win32":
        os.startfile(str(folder))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)], shell=False)
    else:
        subprocess.Popen(["xdg-open", str(folder)], shell=False)


def automation_proposal(goal: str, provider: str, snapshot: Path, handoff: dict) -> dict:
    """A reviewable specification, deliberately not a vendor-executable workflow."""
    return {
        "schema": "context-library.automation-proposal.v1",
        "status": "draft_not_connected",
        "goal": goal,
        "provider": provider,
        "snapshot_path": str(snapshot),
        "handoff": handoff,
        "network_calls": False,
        "execution_enabled": False,
        "laya_compatible": "unverified_requires_installed_laya_adapter_and_schema",
        "steps": [
            {"id": "capture", "status": "local_snapshot_available", "depends_on": [],
             "action": "verify_pinned_snapshot_manifest"},
            {"id": "context", "status": "handoff_created", "depends_on": ["capture"],
             "action": "review_selected_files_and_dependency_context"},
            {"id": "send", "status": "manual_only", "depends_on": ["context"],
             "action": "user_uploads_handoff_to_selected_AI"},
            {"id": "result", "status": "future_adapter_required", "depends_on": ["send"],
             "action": "import_response_as_untrusted_proposal_with_source_links"},
            {"id": "verify", "status": "future_adapter_required", "depends_on": ["result"],
             "action": "verify_changed_commit_and_tests_before_follow_up_actions"},
        ],
        "acceptance": [
            "Исходный commit и manifest доступны в передаваемом пакете.",
            "Каждая предлагаемая правка ссылается на путь и проверяемый критерий.",
            "Merge подтверждается данными GitHub/локального Git, а не одной фразой в ответе AI.",
            "Команды из ответа AI не запускаются при импорте документа.",
        ],
    }


class ContextLibraryApp(tk.Tk):
    def __init__(self, backend: Any = None) -> None:
        super().__init__()
        self.backend = backend or pipeline
        self.title(APP_TITLE)
        self.geometry("1240x850")
        self.minsize(900, 660)
        self.configure(background="#f4f6fa")
        self.events: queue.Queue = queue.Queue()
        self.preview_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.preview_future = None
        self.preview_token = 0
        self.busy = False
        self.snapshot: Path | None = None
        self.catalog: dict = {}
        self.records: dict[str, dict] = {}
        self.file_nodes: dict[str, str] = {}
        self.snapshots_by_label: dict[str, Path] = {}
        self.last_output: Path | None = None
        self.render_generation = 0
        self.repo_var = tk.StringVar()
        self.library_var = tk.StringVar(value=str(Path.home() / "ContextLibrary"))
        self.snapshot_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.labels_var = tk.StringVar()
        self.provider_var = tk.StringVar(value="ChatGPT")
        self.dependencies_var = tk.BooleanVar(value=True)
        self.scope_var = tk.StringVar(value="all")
        self.status_var = tk.StringVar(value="1. Выбери репозиторий и папку библиотеки.")
        self.catalog_summary_var = tk.StringVar(value="Снимок ещё не открыт.")
        self.preview_notice_var = tk.StringVar(value="Выбери файл в каталоге.")
        self.build_buttons: list[ttk.Button] = []
        self._style()
        self._layout()
        self.bind("<Control-f>", self._focus_search)
        self.bind("<Control-Return>", lambda _event: self.create_handoff())
        self.bind("<F5>", lambda _event: self.refresh_snapshots())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(80, self._drain_events)
        self.repo_entry.focus_set()
        self._log("Приложение работает локально. Сетевые интеграции не настроены.")
        if self.backend is None:
            self.after(100, lambda: messagebox.showerror(
                "Нет backend", "Рядом с app.py нужен файл context_pipeline.py.", parent=self))

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6fa")
        style.configure("TLabel", background="#f4f6fa", foreground="#182a3d", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Meta.TLabel", foreground="#4e6075", font=("Segoe UI", 9))
        style.configure("TButton", padding=(10, 7), font=("Segoe UI", 10))
        style.configure("Primary.TButton", background="#145c91", foreground="white")
        style.map("Primary.TButton", background=[("active", "#0f466f"), ("disabled", "#8ca4b7")])
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("TNotebook.Tab", padding=(14, 9), font=("Segoe UI", 10))

    def _layout(self) -> None:
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Вся структура репозитория. Один понятный контекст.", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Локальный прототип · Python + Git · без AI-токенов для сбора и chunking", style="Meta.TLabel").pack(anchor="w", pady=(3, 13))
        paths = ttk.Frame(outer)
        paths.pack(fill="x")
        paths.columnconfigure(1, weight=1)
        ttk.Label(paths, text="Папка Git-репозитория").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.repo_entry = ttk.Entry(paths, textvariable=self.repo_var)
        self.repo_entry.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Выбрать репозиторий…", command=self.choose_repo).grid(row=0, column=2, padx=(8, 0))
        ttk.Label(paths, text="Локальная библиотека").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(paths, textvariable=self.library_var).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Выбрать библиотеку…", command=self.choose_library).grid(row=1, column=2, padx=(8, 0))
        scan_bar = ttk.Frame(outer)
        scan_bar.pack(fill="x", pady=(8, 8))
        self.scan_button = ttk.Button(scan_bar, text="1. Снять HEAD и разбить весь репозиторий", style="Primary.TButton", command=self.scan)
        self.scan_button.pack(side="left")
        self.build_buttons.append(self.scan_button)
        ttk.Label(scan_bar, text="Текстовые части: 256 КиБ · число частей не ограничено", style="Meta.TLabel").pack(side="left", padx=12)
        snapshot_bar = ttk.Frame(outer)
        snapshot_bar.pack(fill="x", pady=(0, 9))
        ttk.Label(snapshot_bar, text="Снимки библиотеки").pack(side="left", padx=(0, 10))
        self.snapshot_combo = ttk.Combobox(snapshot_bar, state="readonly", textvariable=self.snapshot_var)
        self.snapshot_combo.pack(side="left", fill="x", expand=True)
        self.snapshot_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_snapshot())
        ttk.Button(snapshot_bar, text="Обновить (F5)", command=self.refresh_snapshots).pack(side="left", padx=(8, 0))
        ttk.Button(snapshot_bar, text="Открыть снимок…", command=self.open_snapshot).pack(side="left", padx=(8, 0))
        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill="both", expand=True)
        self.catalog_tab = ttk.Frame(self.tabs, padding=10)
        self.handoff_tab = ttk.Frame(self.tabs, padding=14)
        self.log_tab = ttk.Frame(self.tabs, padding=10)
        self.help_tab = ttk.Frame(self.tabs, padding=16)
        self.tabs.add(self.catalog_tab, text="2. Каталог и связи")
        self.tabs.add(self.handoff_tab, text="3. Задача → пакет для AI")
        self.tabs.add(self.log_tab, text="Журнал")
        self.tabs.add(self.help_tab, text="Что работает сейчас")
        self._catalog_layout()
        self._handoff_layout()
        self.log_text = self._text_widget(self.log_tab, wrap="word")
        self.log_text.configure(state="disabled")
        help_text = (
            "РАБОТАЕТ ЛОКАЛЬНО\n\n"
            "• Снимок отслеживаемых Git-файлов из одного HEAD; исходные байты, пути и хеши.\n"
            "• Каталог, метки, поиск, группы связанных файлов и текстовые части.\n"
            "• Документ задачи и пакет контекста для ручной передачи ChatGPT, Grok или Gemini.\n"
            "• Черновик автоматизации со стадиями и критериями результата.\n\n"
            "ГРАНИЦЫ ЭТОГО ПРОТОТИПА\n\n"
            "Кнопка снимка берёт Git HEAD. Изменённые и untracked-файлы рабочего дерева не становятся "
            "его содержимым; их состояние учитывается backend-отчётом. Папка библиотеки должна находиться вне репозитория.\n\n"
            "Выбор AI задаёт адресата документа. Он не подключает аккаунт, чат или API. Laya, голос, "
            "клики по ПК, автоматическая отправка, получение ответа, запуск кода и проверка GitHub merge здесь "
            "не подключены. JSON автоматизации — проект контракта; совместимость с установленной Laya надо проверить отдельно.\n\n"
            "Связи вычисляются эвристически. Динамические импорты, неоднозначные пути и runtime-связи требуют "
            "проверки. Связанные файлы не означают доказанную полноту архитектуры.\n\n"
            "ПОЛНЫЙ ИСХОДНИК И ПРЕДПРОСМОТР\n\n"
            "Предпросмотр ограничен 64 КиБ; ограничение не удаляет исходный файл и не ограничивает "
            "число частей. Экспорт имеет manifest и список исключений. Возможные секреты требуют локального "
            "просмотра до передачи AI. Локальный снимок может содержать приватные данные.\n\n"
            "КЛАВИАТУРА\n\n"
            "Tab / Shift+Tab — перейти к контролу; стрелки — каталог и вкладки; Ctrl+F — поиск; "
            "Ctrl+Enter — собрать пакет; F5 — обновить снимки. Для меток вводи слова через запятую. "
            "Совместимость с конкретным экранным диктором и Windows ещё не проверена."
        )
        self._replace_text(self._text_widget(self.help_tab, wrap="word"), help_text)
        status = ttk.Frame(outer)
        status.pack(fill="x", pady=(10, 0))
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=125)
        self.progress.pack(side="right", padx=(10, 0))
        ttk.Label(status, textvariable=self.status_var, wraplength=900).pack(side="left", fill="x", expand=True)

    def _text_widget(self, parent: tk.Widget, wrap: str = "none") -> tk.Text:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap=wrap, font=("Consolas", 10), background="#ffffff", foreground="#15273d", borderwidth=1, relief="solid", padx=10, pady=8, undo=False)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        if wrap == "none":
            horizontal = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
            text.configure(xscrollcommand=horizontal.set)
            horizontal.pack(fill="x")
        return text

    def _catalog_layout(self) -> None:
        search = ttk.Frame(self.catalog_tab)
        search.pack(fill="x", pady=(0, 8))
        ttk.Label(search, text="Путь / функция / метка / текст").pack(side="left", padx=(0, 8))
        self.search_entry = ttk.Entry(search, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda _event: self.search())
        ttk.Button(search, text="Найти", command=self.search).pack(side="left", padx=(8, 0))
        ttk.Button(search, text="Все файлы", command=self.show_all).pack(side="left", padx=(8, 0))
        ttk.Label(self.catalog_tab, textvariable=self.catalog_summary_var, style="Meta.TLabel", wraplength=1100).pack(anchor="w", pady=(0, 8))
        pane = ttk.Panedwindow(self.catalog_tab, orient="horizontal")
        pane.pack(fill="both", expand=True)
        tree_frame = ttk.Frame(pane)
        right = ttk.Frame(pane)
        pane.add(tree_frame, weight=3)
        pane.add(right, weight=2)
        self.tree = ttk.Treeview(tree_frame, columns=("size", "kind", "labels"), selectmode="extended")
        self.tree.heading("#0", text="SCC-группа / путь (Git HEAD)")
        self.tree.heading("size", text="Размер")
        self.tree.heading("kind", text="Тип")
        self.tree.heading("labels", text="Метки")
        self.tree.column("#0", width=340, minwidth=160)
        self.tree.column("size", width=80, minwidth=65, stretch=False)
        self.tree.column("kind", width=72, minwidth=60, stretch=False)
        self.tree.column("labels", width=150, minwidth=90)
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        tree_horizontal = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_horizontal.set)
        tree_horizontal.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.select_file)
        details_tabs = ttk.Notebook(right)
        details_tabs.pack(fill="both", expand=True, padx=(10, 0))
        preview = ttk.Frame(details_tabs, padding=8)
        related = ttk.Frame(details_tabs, padding=8)
        chunks = ttk.Frame(details_tabs, padding=8)
        details_tabs.add(preview, text="Предпросмотр")
        details_tabs.add(related, text="Связи")
        details_tabs.add(chunks, text="Части / символы")
        ttk.Label(preview, textvariable=self.preview_notice_var, wraplength=380, style="Meta.TLabel").pack(anchor="w", pady=(0, 6))
        self.preview_text = self._text_widget(preview)
        self.preview_text.configure(state="disabled")
        label_bar = ttk.Frame(preview)
        label_bar.pack(fill="x", pady=(8, 0))
        ttk.Label(label_bar, text="Ваши метки через запятую (автометки сохраняются)").pack(anchor="w")
        ttk.Entry(label_bar, textvariable=self.labels_var).pack(fill="x", pady=5)
        self.labels_button = ttk.Button(label_bar, text="Сохранить метки выбранного файла", command=self.save_labels)
        self.labels_button.pack(anchor="w")
        self.build_buttons.append(self.labels_button)
        self.related_text = self._text_widget(related, wrap="word")
        self.chunks_text = self._text_widget(chunks, wrap="word")
        self.related_text.configure(state="disabled")
        self.chunks_text.configure(state="disabled")

    def _handoff_layout(self) -> None:
        ttk.Label(self.handoff_tab, text="Что AI должен исследовать или предложить?", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.handoff_tab, text="Опиши результат, ограничения и способ проверки. Текст попадёт в экспорт, но не в журнал.", style="Meta.TLabel", wraplength=1050).pack(anchor="w", pady=(6, 10))
        self.goal_text = self._text_widget(self.handoff_tab, wrap="word")
        self.goal_text.insert("1.0", "Исследуй архитектуру репозитория. Найди незавершённые функции и составь задачи с зависимостями, ссылками на файлы и критериями готовности. Отдели подтверждённый код от предположений. Не запускай торговлю и не меняй внешние системы.")
        controls = ttk.Frame(self.handoff_tab)
        controls.pack(fill="x", pady=10)
        ttk.Label(controls, text="Адресат документа").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Combobox(controls, textvariable=self.provider_var, values=("ChatGPT", "Grok", "Gemini"), state="readonly", width=16).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(controls, text="Весь снимок", value="all", variable=self.scope_var).grid(row=0, column=2, padx=12)
        ttk.Radiobutton(controls, text="Выбранные файлы", value="selected", variable=self.scope_var).grid(row=0, column=3)
        ttk.Checkbutton(controls, text="Добавить связанные зависимости выбранных файлов", variable=self.dependencies_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(9, 0))
        actions = ttk.Frame(self.handoff_tab)
        actions.pack(fill="x", pady=(0, 10))
        export = ttk.Button(actions, text="Собрать документ для AI (Ctrl+Enter)", style="Primary.TButton", command=self.create_handoff)
        export.pack(side="left")
        automation = ttk.Button(actions, text="Создать автоматизацию — проект", command=lambda: self.create_handoff(as_automation=True))
        automation.pack(side="left", padx=8)
        self.build_buttons.extend([export, automation])
        ttk.Button(actions, text="Открыть результат", command=self.open_last_output).pack(side="left")
        ttk.Button(self.handoff_tab, text="Автоотправка / Laya / голос — не подключено", state="disabled").pack(anchor="w")
        self.export_result_var = tk.StringVar(value="Готовый пакет сохраняется локально. Передай его выбранному AI вручную после просмотра manifest и исключений.")
        ttk.Label(self.handoff_tab, textvariable=self.export_result_var, wraplength=1100).pack(anchor="w", pady=(10, 0))

    @staticmethod
    def _replace_text(widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _focus_search(self, _event: Any = None) -> str:
        self.tabs.select(self.catalog_tab)
        self.search_entry.focus_set()
        return "break"

    def _log(self, message: str) -> None:
        # Called by the UI queue only; goal/file contents are never passed here.
        self.log_text.configure(state="normal")
        self.log_text.insert("end", str(message).replace("\x00", "") + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_busy(self, value: bool, message: str | None = None) -> None:
        self.busy = value
        for button in self.build_buttons:
            button.configure(state="disabled" if value else "normal")
        if value:
            self.progress.start(12)
        else:
            self.progress.stop()
        if message:
            self.status_var.set(message)

    def _run_task(self, name: str, work: Callable, success: Callable) -> None:
        if self.busy:
            self.status_var.set("Дождись завершения текущей операции.")
            return
        if self.backend is None:
            messagebox.showerror("Нет backend", "Нужен context_pipeline.py рядом с app.py.", parent=self)
            return
        self._set_busy(True, name)
        self._log(name)
        def run() -> None:
            try:
                result = work()
                self.events.put(("success", success, result))
            except Exception as exc:
                self.events.put(("error", name, exc))
        threading.Thread(target=run, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "log":
                    self._log(event[1])
                elif event[0] == "success":
                    self._set_busy(False)
                    try:
                        event[1](event[2])
                    except Exception as exc:
                        self._report_error("Ошибка отображения результата", exc)
                elif event[0] == "error":
                    self._set_busy(False)
                    self._report_error(event[1], event[2])
                elif event[0] == "preview":
                    self._show_preview(event[1], event[2])
        except queue.Empty:
            pass
        self.after(80, self._drain_events)

    def _report_error(self, name: str, exc: Exception) -> None:
        self.status_var.set(f"Операция не завершена: {name}")
        self._log(f"ОШИБКА: {name} ({type(exc).__name__}). Подробности показаны в диалоге.")
        messagebox.showerror(name, str(exc)[:2500], parent=self)

    def choose_repo(self) -> None:
        path = filedialog.askdirectory(title="Выбери папку Git-репозитория", parent=self)
        if path:
            self.repo_var.set(path)

    def choose_library(self) -> None:
        path = filedialog.askdirectory(title="Выбери библиотеку вне Git-репозитория", parent=self)
        if path:
            self.library_var.set(path)
            self.refresh_snapshots()

    def scan(self) -> None:
        if not self.repo_var.get().strip() or not self.library_var.get().strip():
            messagebox.showinfo("Нужны две папки", "Выбери репозиторий и папку библиотеки вне него.", parent=self)
            return
        repo = Path(self.repo_var.get()).expanduser().resolve()
        library = Path(self.library_var.get()).expanduser().resolve()
        if repo == library or repo in library.parents:
            messagebox.showerror("Библиотека внутри репозитория", "Выбери папку вне репозитория, чтобы результаты не попадали в следующие снимки.", parent=self)
            return
        def work() -> tuple[dict, list]:
            result = self.backend.build_catalog(str(repo), str(library), part_bytes=262_144,
                log_callback=lambda message: self.events.put(("log", message)))
            snapshot = Path(result["snapshot_path"])
            return self.backend.load_catalog(str(snapshot)), self.backend.list_snapshots(str(library))
        def done(result: tuple[dict, list]) -> None:
            self._fill_snapshots(result[1])
            self._set_catalog(result[0])
            self._log("Снимок и каталог созданы. Проверь полноту и сообщения backend.")
        self._run_task("Сбор Git HEAD, графа связей и частей контекста…", work, done)

    def refresh_snapshots(self) -> None:
        library = self.library_var.get().strip()
        if not library:
            return
        self._run_task("Чтение списка снимков…", lambda: self.backend.list_snapshots(library), self._fill_snapshots)

    def _fill_snapshots(self, snapshots: list) -> None:
        self.snapshots_by_label = {}
        for item in snapshots:
            if isinstance(item, dict):
                value = item.get("snapshot_path") or item.get("path")
                if not value:
                    continue
                path = Path(value)
                label = f"{item.get('repo_name', path.name)} · {str(item.get('commit', ''))[:12]} · {item.get('snapshot_id', path.name)}"
            else:
                path = Path(item)
                label = path.name
            # Keep all snapshots even when an older backend gives duplicate display names.
            if label in self.snapshots_by_label:
                label = f"{label} · {path}"
            self.snapshots_by_label[label] = path
        self.snapshot_combo.configure(values=list(self.snapshots_by_label))
        self.status_var.set(f"Снимков в выбранной библиотеке: {len(self.snapshots_by_label)}.")

    def load_selected_snapshot(self) -> None:
        snapshot = self.snapshots_by_label.get(self.snapshot_var.get())
        if snapshot:
            self._load_snapshot(snapshot)

    def open_snapshot(self) -> None:
        path = filedialog.askdirectory(title="Папка сохранённого снимка с catalog.json", parent=self)
        if path:
            self._load_snapshot(Path(path))

    def _load_snapshot(self, snapshot: Path) -> None:
        def done(catalog: dict) -> None:
            catalog.setdefault("snapshot_path", str(snapshot))
            self._set_catalog(catalog)
        self._run_task("Открытие сохранённого каталога…", lambda: self.backend.load_catalog(str(snapshot)), done)

    def _set_catalog(self, catalog: dict) -> None:
        self.preview_token += 1
        self.catalog = catalog
        self.snapshot = Path(catalog["snapshot_path"])
        self.records = {record["path"]: record for record in catalog.get("files", [])}
        for label, path in self.snapshots_by_label.items():
            if path.resolve() == self.snapshot.resolve():
                self.snapshot_var.set(label)
                break
        self.search_var.set("")
        self._replace_text(self.preview_text, "")
        self._replace_text(self.related_text, "")
        self._replace_text(self.chunks_text, "")
        self.labels_var.set("")
        self.preview_notice_var.set("Выбери файл. Просмотр ограничен 64 КиБ; исходные байты сохранены в снимке.")
        self.show_all()
        self.tabs.select(self.catalog_tab)
        self.status_var.set("Снимок открыт. Найди нужные файлы, добавь метки и сформулируй задачу AI.")

    def show_all(self) -> None:
        if not self.catalog:
            return
        self._render_files(list(self.records.values()))

    def _render_files(self, records: list[dict]) -> None:
        self.render_generation += 1
        generation = self.render_generation
        self.tree.delete(*self.tree.get_children())
        self.file_nodes = {}
        group_order = {group["id"]: index for index, group in enumerate(self.catalog.get("groups", []))}
        records = sorted(records, key=lambda r: (group_order.get(r.get("group_id"), len(group_order)), r["path"]))
        group_nodes: dict[str, str] = {}
        completeness = self.catalog.get("completeness", {})
        summary = (f"Git HEAD {self.catalog.get('commit', '?')} · файлов в снимке: {len(self.records)} · "
            f"в выборке: {len(records)} · частей: {len(self.catalog.get('chunks', []))} · "
            f"связей: {len(self.catalog.get('edges', []))} · нерешённых: {len(self.catalog.get('unresolved_edges', []))}\n"
            f"Все Git blob: {completeness.get('tracked_git_blob_scope_complete', 'не проверено')} · "
            f"внешние данные (LFS/submodules): {completeness.get('external_payload_complete', 'не проверено')} · "
            "рабочая копия не включена; граф связей частичный.")
        self.catalog_summary_var.set(summary)
        def insert_batch(start: int = 0) -> None:
            if generation != self.render_generation:
                return
            for index in range(start, min(start + 180, len(records))):
                record = records[index]
                group = str(record.get("group_id") or "Без установленной группы")
                if group not in group_nodes:
                    group_nodes[group] = self.tree.insert("", "end", text=group, open=True)
                node = self.tree.insert(group_nodes[group], "end", text=record["path"], values=(
                    human_size(record.get("size")), record.get("kind", ""), ", ".join(record.get("labels", []))))
                self.file_nodes[node] = record["path"]
            if start + 180 < len(records):
                self.after(1, lambda: insert_batch(start + 180))
        insert_batch()

    def search(self) -> None:
        if not self.snapshot:
            return
        query = self.search_var.get().strip()
        if not query:
            self.show_all()
            return
        snapshot = str(self.snapshot)
        def done(results: list) -> None:
            records = [self.records[item["path"]] for item in results if item.get("path") in self.records]
            self._render_files(records)
            self.status_var.set(f"Поиск завершён: найдено файлов {len(records)}. Запрос не записан в журнал.")
        self._run_task("Поиск по путям, меткам и доступному тексту…", lambda: self.backend.search_catalog(snapshot, query), done)

    def selected_paths(self) -> list[str]:
        return [self.file_nodes[node] for node in self.tree.selection() if node in self.file_nodes]

    def select_file(self, _event: Any = None) -> None:
        selected = self.selected_paths()
        if not selected or not self.snapshot:
            return
        path = selected[0]
        record = self.records[path]
        self.labels_var.set(", ".join(record.get("manual_labels", [])))
        self.preview_token += 1
        token = self.preview_token
        self.preview_notice_var.set(f"{path}\n{human_size(record.get('size'))} · загрузка локального предпросмотра…")
        edges = [edge for edge in self.catalog.get("edges", []) if edge.get("source") == path or edge.get("target") == path]
        related_lines = ["Статические связи (эвристика; runtime-связи могут отсутствовать):", ""]
        related_lines.extend(f"{edge.get('kind', 'связь')}: {edge.get('source')} → {edge.get('target')}" for edge in edges)
        group = record.get("group_id")
        related_lines.extend(["", "Другие пути в группе:"])
        related_lines.extend(other for other, data in self.records.items() if other != path and data.get("group_id") == group)
        self._replace_text(self.related_text, "\n".join(related_lines))
        chunks = [chunk for chunk in self.catalog.get("chunks", []) if chunk.get("id") in record.get("text_part_refs", []) or path in chunk.get("file_paths", [])]
        self._replace_text(self.chunks_text, json.dumps({"path": path, "sha256": record.get("sha256"), "status": record.get("status"), "analysis_status": record.get("analysis_status"), "symbols": record.get("symbols", []), "parts": chunks, "note": "Части ограничены байтами и упорядочены по зависимостям; список символов — отдельные координаты AST, не гарантия границ частей по функциям."}, ensure_ascii=False, indent=2))
        snapshot = str(self.snapshot)
        if self.preview_future:
            self.preview_future.cancel()
        def preview() -> None:
            try:
                result = self.backend.get_preview(snapshot, path, max_bytes=PREVIEW_BYTES)
            except Exception as exc:
                result = {"text": f"Не удалось открыть предпросмотр: {type(exc).__name__}. Проверь manifest снимка.", "path": path}
            self.events.put(("preview", token, result))
        self.preview_future = self.preview_executor.submit(preview)

    def _show_preview(self, token: int, result: dict) -> None:
        if token != self.preview_token:
            return
        notices = [result.get("path", ""), f"Размер исходника: {human_size(result.get('size'))}."]
        if result.get("status") and result.get("status") != "exported":
            notices.append(f"Статус: {result['status']}. Проверь manifest: содержимое может быть внешним или недоступным.")
        elif result.get("binary"):
            notices.append("Бинарный файл: байты сохранены; текстовый просмотр недоступен.")
        elif result.get("truncated"):
            notices.append("Показаны первые 64 КиБ. Полный исходник сохранён в снимке.")
        else:
            notices.append("Показан доступный текст файла из сохранённого снимка.")
        if result.get("sensitive_reasons"):
            notices.append("Обнаружены возможные чувствительные данные: проверь экспорт перед передачей.")
        self.preview_notice_var.set("\n".join(notices))
        self._replace_text(self.preview_text, result.get("text") or "Нет текстового предпросмотра.")

    def save_labels(self) -> None:
        paths = self.selected_paths()
        if len(paths) != 1 or not self.snapshot:
            messagebox.showinfo("Выбери один файл", "Для изменения меток выбери ровно один файл в каталоге.", parent=self)
            return
        path, snapshot = paths[0], str(self.snapshot)
        labels = parse_labels(self.labels_var.get())
        def done(record: dict) -> None:
            self.records[path].update(record)
            for node, item_path in self.file_nodes.items():
                if item_path == path:
                    self.tree.set(node, "labels", ", ".join(record.get("labels", labels)))
            self.status_var.set("Метки сохранены отдельно от исходных байтов.")
            self._log("Метки выбранного файла обновлены.")
        self._run_task("Сохранение меток…", lambda: self.backend.set_labels(snapshot, path, labels), done)

    def create_handoff(self, as_automation: bool = False) -> None:
        if not self.snapshot:
            messagebox.showinfo("Сначала снимок", "Сначала собери или открой снимок репозитория.", parent=self)
            return
        if self.busy:
            self.status_var.set("Дождись завершения текущей операции.")
            return
        goal = self.goal_text.get("1.0", "end-1c").strip()
        if not goal:
            self.tabs.select(self.handoff_tab)
            self.goal_text.focus_set()
            messagebox.showinfo("Опиши задачу", "Введи желаемый результат и критерии проверки.", parent=self)
            return
        selected = self.selected_paths() if self.scope_var.get() == "selected" else None
        if selected == []:
            messagebox.showinfo("Файлы не выбраны", "Выдели файлы в каталоге или выбери режим «Весь снимок».", parent=self)
            return
        folder = filedialog.askdirectory(title="Куда сохранить пакет для AI (вне репозитория)", initialdir=self.library_var.get() or None, parent=self)
        if not folder:
            return
        output_root = Path(folder).resolve()
        repo_value = self.repo_var.get().strip()
        if repo_value:
            repo = Path(repo_value).expanduser().resolve()
            if output_root == repo or repo in output_root.parents:
                messagebox.showerror("Экспорт внутри репозитория", "Выбери папку вне репозитория.", parent=self)
                return
        snapshot = self.snapshot
        provider = self.provider_var.get()
        include_dependencies = self.dependencies_var.get()
        def work() -> tuple[dict, Path]:
            result = self.backend.make_handoff(str(snapshot), goal, provider, str(output_root), selected_paths=selected, include_dependencies=include_dependencies)
            handoff_path = Path(result["handoff_path"])
            destination = handoff_path if handoff_path.is_dir() else handoff_path.parent
            if as_automation:
                proposal = automation_proposal(goal, provider, snapshot, result)
                (destination / "AUTOMATION_PROPOSAL_NOT_CONNECTED.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return result, destination
        def done(data: tuple[dict, Path]) -> None:
            result, destination = data
            self.last_output = destination
            omitted = result.get("omissions", [])
            omitted_count = len(omitted) if isinstance(omitted, (list, dict)) else omitted
            mode = "Пакет и проект автоматизации" if as_automation else "Пакет для AI"
            self.export_result_var.set(f"{mode} сохранён: {destination}\nИсключения: {omitted_count}. Открой manifest перед ручной передачей. Автоотправка не выполнялась.")
            self.status_var.set("Экспорт завершён. Пакет готов к локальному просмотру и ручной передаче.")
            self._log(f"Экспорт завершён; адресат {provider}; автоматизация: {'проект' if as_automation else 'нет'}; сетевых действий: 0.")
            self.tabs.select(self.handoff_tab)
        self._run_task("Сбор документа задачи и пакета контекста…", work, done)

    def open_last_output(self) -> None:
        if not self.last_output:
            messagebox.showinfo("Пока нет результата", "Сначала собери пакет для AI.", parent=self)
            return
        try:
            open_folder(self.last_output)
        except Exception as exc:
            self._report_error("Не удалось открыть папку", exc)

    def close(self) -> None:
        if self.busy and not messagebox.askyesno("Операция выполняется", "Закрытие прервёт текущую операцию. Незавершённый результат не следует считать готовым. Закрыть приложение?", parent=self):
            return
        self.preview_executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def main() -> int:
    try:
        app = ContextLibraryApp()
    except tk.TclError as exc:
        print(f"Desktop display/Tkinter unavailable: {exc}", file=sys.stderr)
        return 2
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
