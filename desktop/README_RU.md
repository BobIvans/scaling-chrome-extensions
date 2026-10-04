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

Кнопка «Исследования» читает зарегистрированные офлайн-задания Core, по 20 строк на страницу. Повторное нажатие открывает следующую страницу; после конца начинается новый просмотр. Если список изменился между страницами, переподключитесь. Desktop не запускает исследовательские процессы. Завершённое вычисление не означает рыночную или аппаратную квалификацию.
## Объединённый PR-014 + PR-015: контекст и локальные задания

Версия 0.2.0 добавляет отдельное окно «Контекст и задания». Старый профиль без
`context_service` сохраняет прежний режим чтения. SQLite `content.sqlite3`,
канонические items/FTS/heads и очередь durable Core остаются владельцами данных.

Оператор добавляет в policy `context_services.local` по примеру
`docs/automation/pr014-015/context-service.example.json`, а в native profile —
`"context_service": "local"`. Абсолютные input/output roots, namespace, actions и
назначения задаются оператором. AI-ответы не меняют эти разрешения. В destination
нужно перечислить разрешённые source_keys и защищаемые литералы; автоматическая
проверка секретов не гарантирует обнаружение неизвестных секретов.

Установка на Windows с Python 3.11+ и Tk:

```powershell
.\desktop\Install_Windows.ps1 -PythonPath C:\Python313\python.exe -ProfilePath C:\ContextData\profile.json
```

Версионная папка в LOCALAPPDATA содержит проверяемый backend и shell, а store,
profile, policy и квалификация остаются отдельно. Установщик создаёт ярлык в
Start Menu, не скачивает runtime и не требует Chrome или исходного checkout.
Данные не должны находиться внутри папки установки. Для обновления используйте
новую версионную папку и переподключите профиль; старую можно сохранить для
отката. Новая версия требует повторной квалификации. Это Python/Tk-пакет;
самостоятельный подписанный EXE и проверка на пользовательском Windows-устройстве
ещё не квалифицированы.

Настройка установленного backend (пути замените на ваши):

```powershell
$Backend = "$env:LOCALAPPDATA\ContextLibrary\versions\0.2.0\backend"
C:\Python313\python.exe -I -X utf8 "$Backend\context_runtime.py" --profile C:\ContextData\profile.json initialize
C:\Python313\python.exe -I -X utf8 "$Backend\context_runtime.py" --profile C:\ContextData\profile.json qualify
```

`qualify` запускает независимые локальные тесты и сохраняет receipt с build/grant
хэшами и логом. Изменение кода или профиля делает receipt STALE. DEVICE остаётся
NOT_RUN. Подключитесь; откройте «Контекст и задания»:

1. Импортируйте файл с устойчивым source_key. Команда сохраняет задание; кнопка
   «Выполнить одно задание Core» использует существующий Core, затем проверяет
   сохранённую операцию. После потерянного ответа используйте тот же ID.
2. Поиск выдаёт страницы до 20 строк. «Далее» продолжает до EOF. Выберите точный
   диапазон байтов и причину WHY_THIS_PACKET, добавьте в корзину.
3. Соберите пакет с целью и критериями. Создайте share-проекцию для разрешённого
   назначения; прочитайте её части и экспортируйте в новую папку.
4. Импортируйте JSON результата как AI_CLAIM. DONE в тексте не закрывает критерий
   и не даёт разрешения на запуск. NEED_CONTEXT JSON привязан к конкретному пакету,
   критерию, ревизии и диапазону; delta не отправляется автоматически.
5. Backup проверяет байты и SQLite. Restore создаёт отдельную проверенную копию,
   накладывает текущие tombstones и блокирует запуск восстановленных заданий.

STOP (Ctrl+Shift+X в окне контекста) работает через отдельный транспорт. Только
DURABLE_FENCED подтверждает запись запрета нового запуска. Работавший эффект может
оставаться неопределённым. «Состояние / продолжить» не запускает старые отменённые
задания и отказывает при незавершённой reconciliation. Закрытие окна не отменяет
уже сохранённое задание Core. Временный transport journal хранит только ID;
источники, intents и результаты остаются в SQLite.

Удаление версионного пакета:

```powershell
C:\Python313\python.exe -I -X utf8 "$env:LOCALAPPDATA\ContextLibrary\versions\0.2.0\desktop\install.py" uninstall --output "$env:LOCALAPPDATA\ContextLibrary\versions\0.2.0"
```

Неизвестные файлы в папке установки блокируют удаление. Store/profile/policy и
внешние результаты сохраняются. Удалите ярлык Start Menu отдельно. Проверка
доступности, клавиатуры, установок/обновлений и быстродействия на Windows/Dell
остаётся отдельным обязательным приёмочным этапом.

Фоновый Core не имеет общего таймаута размера источника: окно может закрыться,
а сохранённое задание продолжает работать. Если процесс действительно потерян,
сначала остановите/проверьте все worker-процессы. Только после этой проверки:

```powershell
C:\Python313\python.exe -I -X utf8 "$Backend\context_runtime.py" --profile C:\ContextData\profile.json --id JOB_ID --process-stopped reconcile
```

Команда проверяет completed local receipt и реальные байты/артефакты. Для
незавершённых CAPTURE/BUILD_PACKET/PROJECT явно добавьте `--resume-local`:
возобновляется тот же job/operation ID, только при неизменных grant/build/STOP
эпохе. Cancelled или старый fenced intent не запускается повторно. Другие
неопределённые эффекты команда оставляет reconciliation-required. Не ставьте
`--process-stopped`, пока процесс фактически не проверен.
