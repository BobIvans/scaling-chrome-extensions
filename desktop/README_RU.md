# Desktop 0.1: установленная библиотека без Chrome

Окно подключается к **уже установленному текущему backend**. Нужны Python 3.11+
с Tkinter, `content-lab/native_adapter.py`, настроенный native-profile и готовая
библиотека `content.sqlite3`. Desktop ничего не скачивает и не регистрирует.

В Windows PowerShell откройте папку `desktop` и запустите:

```powershell
.\Launch_Windows.ps1 -PythonPath 'C:\Program Files\Python313\python.exe'
```

В настройках выберите Python, установленный `native_adapter.py` и профиль.
SHA-256 backend получите локально и сверяйте с выбранной установкой:

```powershell
(Get-FileHash -LiteralPath 'C:\SCE Backend\content-lab\native_adapter.py' -Algorithm SHA256).Hash.ToLowerInvariant()
```

После сохранения настроек достаточно `Launch_Windows.ps1`. При несовместимом
backend откройте настройки или обновите свою установку; старые source excerpts
из roadmap не являются обновлением. Пример конфигурации: `connection.example.json`.
Окно показывает фактический путь библиотеки. Chrome, Node и Codex для этого
пути подключения не требуются. Существующий браузерный installer сохраняется.

1. Подключитесь и выберите библиотеку/namespace.
2. Введите поиск и нажмите Enter. Это **лучшие 20 совпадений**.
3. Выберите до 10 источников, прочитайте контекст.
4. Заполните цель, область и критерии. Сохраните документ в новую папку.

Результат: `TASK_DRAFT.txt` и `DRAFT_METADATA.json`. Текст сохраняет BOM/CRLF;
metadata содержит точные source IDs, версии, owner digest и отдельный hash файла.
Документ имеет scope `SELECTED_ITEMS`, canonical task ID отсутствует. Его можно
вручную передать AI. Успешное сохранение не означает отправку, прочтение или merge.

Полный список файлов уже собранного снимка сохраняется отдельной кнопкой.
Выберите alias репозитория из профиля и укажите ID снимка из backend/export receipt.
Desktop проходит реальные manifest pages **до EOF**, записывая JSONL потоково.
Общего лимита файлов, частей, страниц или размера репозитория нет. На странице
до 20 строк; это размер ответа. Полный исходный ZIP64 экспорт остаётся у
`repo_archive.py`, scan — у существующего владельца. Поиск/выбранный документ
не являются полным экспортом репозитория.

Отмена — Escape. Изменение запроса, namespace, выбора или reconnect отбрасывает
старые ответы. Работает один read subprocess; stdout/stderr вместе ограничены
192000 байтами, запрос — 16000, deadline чтения — 10 секунд.
Диагностика показывает версии, identities и budgets, без запроса/текста источников.
Bundle build status остаётся UNKNOWN, когда проверенного backend bundle нет.

Оператор может явно включить управление существующим ledger сканирования,
добавив `"desktop_scan_enabled": true` в native-profile. Возможность появляется
только когда в готовой библиотеке уже есть таблица `repo_scan_runs`; Desktop
не создаёт схему. Выберите репозиторий и нажмите «Статус сканирования» для
восстановления последнего запуска. «Новый запуск» создаёт уникальный intent;
«Следующая порция» обрабатывает до 20 файлов с сохранением cursor в backend.
Пауза, продолжение и отмена используют сохранённую revision. Закрытие окна
не меняет состояние запуска; прерванную в момент записи порцию можно повторить
после открытия. Шаги запускаются вручную, фонового планировщика Desktop нет.
Deadline одного шага — 120 секунд; истечение времени не отмечает запуск
успешным, статус и сохранённый cursor нужно перечитать.
При выключенном флаге все операции Desktop остаются только чтением.

Для установки только shell в новую отдельную папку версии используйте:

```powershell
& 'C:\Program Files\Python313\python.exe' -I -X utf8 .\package.py stage --shell $PWD.Path --output 'C:\SCE Desktop\v0.1'
```

Команда переносит проверенные shell files без тестовых fixtures. Backend,
профиль, corpus и папки результатов должны быть снаружи новой папки версии.
`OWNED_FILES.json` проверяет shell files перед запуском. Linux-проверка:

```bash
python -I -X utf8 desktop/package.py verify --shell desktop
python -I -X utf8 desktop/preflight.py --config /absolute/path/connection.json
python -I -X utf8 desktop/app.py --config /absolute/path/connection.json
```

Для отката откройте предыдущую папку версии и снова подключитесь. Удаление
только проверенного shell (закройте окно перед запуском):

```powershell
& 'C:\Program Files\Python313\python.exe' -I -X utf8 .\package.py uninstall --shell $PWD.Path
```

Удаление проверяет manifest и внешний профиль, отказывается от неизвестных
файлов/links/reparse paths/пересечения data roots. Удаляются только перечисленные
shell files и локальная connection.json. Backend, policy, corpus и результаты
сохраняются. Папка shell не удаляется рекурсивно.

Windows CI проверяет subprocess, Unicode/space paths и сохранение данных.
При поддержке backend можно сохранить полную историю снимков и изменения
указанного снимка в отдельные JSONL-папки. Кнопки читают страницы до явного EOF,
сохраняют receipt с SHA-256 и допускают отмену без публикации неполной папки.
ID снимка можно взять из сохранённой истории. Это метаданные репозитория;
содержимое файлов и полный dependency graph в этих двух экспортах отсутствуют.
Программный API delta принимает `baseSnapshotId` для сравнения с выбранным
завершённым историческим снимком; Desktop кнопка использует предыдущий
завершённый снимок по умолчанию.
Настоящая установка на Dell/Windows 11, peak memory, keyboard/UI и orphan cleanup
требуют device receipt. Самостоятельный installer с runtime, TXT import,
canonical task writes, voice/Grok/updater — следующие отдельные части roadmap.
