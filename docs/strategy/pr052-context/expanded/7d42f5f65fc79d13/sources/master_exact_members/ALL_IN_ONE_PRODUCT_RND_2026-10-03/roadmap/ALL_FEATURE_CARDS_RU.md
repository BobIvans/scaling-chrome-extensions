# Карточки разработки

Все статусы реализации — unverified; source refs ведут к неизменным архивным материалам. Связанные карточки из SH-групп используют общие компоненты.

## LIB-001 · P0 · Единый публичный service API существующей библиотеки

Проблема: Прототип GUI обращается к private helpers; новый shell может создать второй источник состояния.

Поведение: Сверить текущий Content Lab owner и оформить публичные операции source/version/search/export; GUI и импортеры используют одну canonical SQLite и существующий job owner.

Зависимости: нет внутри каталога; см. phase dependencies.

Приёмка:

- Составлена карта current SHA → owner → таблицы → API.
- Импорт через GUI и через API виден в одном каталоге без дублирования записей.

Следующий опыт: На временной копии библиотеки пройти импорт→поиск→экспорт через оба клиента.

Метрика: Число competing stores=0; доля операций, покрытых публичным API.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/DEVELOPMENT_WORKSTREAMS.json` · `D02`

## RND-001 · P0 · Актуальная карта репозитория и владельцев runtime

Проблема: Исторические SHA и описание документа не показывают текущую готовность кода.

Поведение: На выбранном snapshot связать HEAD/tree, зависимости, платформу, CLI entrypoints и владельца qualification; старые наблюдения хранить с датой.

Зависимости: нет внутри каталога; см. phase dependencies.

Приёмка:

- У каждого утверждения о наличии функции указан source path и revision.
- Недоступный checkout даёт UNVERIFIED, а не повтор старого статуса.

Следующий опыт: Сравнить один сохранённый snapshot с будущим актуальным checkout без выполнения кода.

Метрика: Доля runtime-утверждений с точной ревизией.

Условие возвращения/начала: Нужен доступный выбранный snapshot; нынешняя упаковка repo не проверяет.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F14`
- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-20`

## RND-011 · P0 · Единая схема evidence с явными неизвестными

Проблема: Boolean success скрывает пропуски, conflicting receipts и синтетическое происхождение.

Поведение: Хранить TRUE/FALSE/UNKNOWN/NOT_RUN, hashes, time range, required cases, source revision и evidence kind; own status отделить от readiness зависимостей.

Зависимости: RND-001.

Приёмка:

- Пустой JUnit и текст AI не подтверждают запуск.
- Два несовместимых receipts дают conflict вместо выбора удобного.
- Порча одного байта обнаруживается.

Следующий опыт: Матрица valid/stale/corrupt/missing/conflicting fixtures.

Метрика: False completion count на негативном corpus.

Условие возвращения/начала: Старые неизвестные схемы сохранять raw до написания проверенного импортёра.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-12`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F12`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F13`

## LIB-002 · P1 · Полный манифест фиксированного Git snapshot

Проблема: Сканирование рабочей папки через ignore rules не даёт полного дерева коммита.

Поведение: Сначала фиксировать commit и каждый ls-tree entry: path bytes/display path, mode, blob OID, size, SHA-256 и статус сохранения.

Зависимости: LIB-001.

Приёмка:

- Множество manifest entries совпадает с выбранным Git tree.
- Unicode, пустые файлы и нестандартные пути имеют собственные записи.

Следующий опыт: Сравнить fixture дерева с ignore rules, binary и необычными именами с manifest.

Метрика: 100% entries и bytes в заявленном snapshot scope.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-001`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/03_NO_LOSS_AND_LIMITS_RU.txt`

## LIB-003 · P1 · Потоковое сохранение крупных исходников

Проблема: Ограничения 4/8 MiB в исторических путях могут оставлять большой файл вне контекста.

Поведение: Потоково записывать raw object и SHA-256; parser budget отделить от хранения; низкий свободный диск даёт checkpoint и видимую остановку.

Зависимости: LIB-001.

Приёмка:

- Файлы 9 MiB и больше выбранного RAM batch восстанавливаются byte-for-byte.
- Превышение ресурса не помечает источник COMPLETE и не уничтожает уже сохранённые bytes.

Следующий опыт: Импортировать большой текст и binary с ограниченным worker budget и прерыванием.

Метрика: Roundtrip hashes; peak RAM относительно chunk size; silent omissions=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-002`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/03_NO_LOSS_AND_LIMITS_RU.txt`

## LIB-004 · P1 · Массовый выбор и пагинация до конца

Проблема: Размер страницы 20 и selection cap 10 ошибочно превращаются в общую границу экспорта.

Поведение: Хранить selection как versioned query или явный set; проходить stable cursors до terminal page, показывать selected/processed/remaining.

Зависимости: LIB-001.

Приёмка:

- 31 и 1001 выбранных источника полностью попадают в export.
- Последняя неполная страница и изменившийся snapshot не теряют записи.

Следующий опыт: Пройти коллекцию 1001 объектов с page size 20 и restart на промежуточном cursor.

Метрика: Selected=represented+explicit failures; duplicate/omission count.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-003`

## LIB-005 · P1 · Полный многотомный текст без общего потолка частей

Проблема: Старый bundle limit числа частей способен обрезать корпус, даже если отдельные chunks корректны.

Поведение: Генерировать поток PART_n с непрерывными byte ranges и индексом исходников; размер части настраивается, число частей определяется данными и доступным диском.

Зависимости: LIB-002, LIB-003, LIB-004.

Приёмка:

- Конкатенация всех частей совпадает с full text hash.
- Fixture с >1000 малыми частями доходит до EOF без встроенного count cap.

Следующий опыт: Экспортировать тестовый корпус с маленьким part size и восстановить полный поток.

Метрика: Range gaps/overlaps=0; full text hash equality; part_count factual.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-004`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/03_NO_LOSS_AND_LIMITS_RU.txt`

## LIB-006 · P1 · Возобновляемый импорт с checkpoints

Проблема: Прерывание долгого импорта приводит к пропуску хвоста или повторной регистрации версий.

Поведение: Checkpoint связывать со source snapshot, cursor и подтверждёнными object hashes; запись версии идемпотентна, незавершённый object не публикуется как готовый.

Зависимости: LIB-001, LIB-003.

Приёмка:

- Сбой до/после commit даёт одинаковый финальный manifest после resume.
- Смена upstream revision во время resume обнаружена явно.

Следующий опыт: Прерывать worker в трёх стадиях одного большого импорта.

Метрика: Потерянные/дублированные версии=0; time to resume.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-005`

## LIB-007 · P1 · Оригиналы неподдерживаемых форматов

Проблема: Text-only ingestion стирает binary, неизвестную кодировку или содержимое с ошибкой parser.

Поведение: Original хранится независимо от extraction; состояния ORIGINAL_ONLY/UNSUPPORTED/FAILED различаются; UTF-8 errors=ignore не используется для raw.

Зависимости: LIB-003.

Приёмка:

- Binary, BOM, CRLF и non-UTF8 сохраняются с исходным hash.
- Неудачный parser не уменьшает raw coverage.

Следующий опыт: Импортировать mixed corpus и намеренно сломать один extractor.

Метрика: Raw byte fidelity=100%; explicit extraction statuses=100%.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-006`

## LIB-008 · P1 · Дедупликация bytes с сохранением всех происхождений

Проблема: Повторные архивы раздувают хранение, а дедуп по тексту может стереть пути и авторов.

Поведение: Один CAS object на identical bytes; source aliases, контейнеры, версии, роли и позиции остаются отдельными сущностями.

Зависимости: LIB-001, LIB-003.

Приёмка:

- Пять одинаковых объектов в разных путях дают один blob и пять origins.
- Удаление alias не удаляет object, пока на него есть ссылки.

Следующий опыт: Импортировать два перекрывающихся ZIP и сравнить object и alias counts.

Метрика: Storage dedup ratio; origin retention=100%.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-007`

## LIB-009 · P1 · Граф вложенных архивов и контролируемая распаковка

Проблема: Nested ZIP, одинаковые имена и опасные относительные пути нельзя безопасно разворачивать в обычное дерево.

Поведение: Сохранять каждый контейнер целиком, members адресовать container hash+entry ordinal+raw name; expansion потоковый, ограниченный активными ресурсами, с resume и журналом unsupported/encrypted.

Зависимости: LIB-003, LIB-006, LIB-008.

Приёмка:

- ../, absolute path и symlink entries не создают файлы вне object storage.
- Оригинальный nested ZIP восстанавливается, даже если expansion остановлен.

Следующий опыт: Fixture nested ZIP с duplicate entry names, traversal, encrypted placeholder и budget exhaustion.

Метрика: Preserved containers=100%; unexplained members=0; peak expansion resources.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-008`

## LIB-010 · P1 · Отдельный учёт LFS, submodules и symlinks

Проблема: Git pointer или gitlink легко ошибочно посчитать полным содержимым внешнего payload.

Поведение: Различать raw pointer, requested external payload и доступность; symlink хранить как ссылку; ссылки не обходить за scope.

Зависимости: LIB-002.

Приёмка:

- Отсутствующий LFS payload показан missing и не назван содержимым файла.
- Submodule pin и symlink target сохранены без самовольного traversal.

Следующий опыт: Экспортировать fixture с отсутствующим payload и затем добавить payload delta.

Метрика: External-payload coverage; falsely complete=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/03_NO_LOSS_AND_LIMITS_RU.txt`

## LIB-011 · P1 · Слои commit, dirty worktree и история

Проблема: Смешение HEAD и незакоммиченных файлов делает контекст невоспроизводимым.

Поведение: Показывать pinned snapshot отдельно от working overlay; branches/history добавлять как отдельные выбранные scopes с refs, revisions и tombstones.

Зависимости: LIB-002, LIB-006.

Приёмка:

- Контекст содержит commit и явный overlay diff.
- Удалённый/untracked файл не маскируется под tracked HEAD entry.

Следующий опыт: Собрать packet до и после локального изменения без нового commit.

Метрика: Воспроизводимость каждого scope; unbound paths=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/02_DESKTOP_ARCHITECTURE_RU.txt`

## LIB-014 · P1 · Точные spans и дословная реконструкция

Проблема: Сводка требований скрывает фрагменты, которые не удалось интерпретировать.

Поведение: Каждый requirement/quote связывать с raw representation hash и byte range; полный span inventory покрывает исходник, неразобранные фрагменты остаются видимыми.

Зависимости: LIB-007, LIB-008.

Приёмка:

- Все exact quotes совпадают с slice исходника.
- Склейка непересекающегося span inventory восстанавливает каждый message.

Следующий опыт: Проверить Unicode, эмодзи, CRLF и намеренные опечатки на roundtrip.

Метрика: Quote exactness=100%; unrepresented bytes=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-04`

## LIB-016 · P1 · Версионируемые извлечения и обратимые преобразования

Проблема: OCR, нормализация и новая модель могут незаметно перезаписать точный source text.

Поведение: Derived representation хранит input hash, parser/model/version, параметры, offsets и fidelity; re-extraction создаёт новую версию, прежний output доступен.

Зависимости: LIB-007, LIB-014.

Приёмка:

- Смена extractor оставляет обе версии и raw original.
- Каждая цитата разрешается в конкретную representation.

Следующий опыт: Прогнать два parser versions на одном документе и сравнить derived diff.

Метрика: Unbound derived outputs=0; reproducible extraction rate.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/data_labeling/TAXONOMY_RU.json` · `core.representation`

## LIB-024 · P1 · Четыре отдельных измерения полноты

Проблема: 100% сохранённых bytes не означает, что всё извлечено, проиндексировано и прочитано AI.

Поведение: Показывать raw capture, extraction, indexing и reviewed/used coverage отдельно для defined scope; raw COMPLETE допускается по readback, semantic UNKNOWN не маскируется.

Зависимости: LIB-002, LIB-007, LIB-014.

Приёмка:

- Binary original даёт captured=true, text_extracted=false.
- Непрочитанные chunks видны даже после успешного export.

Следующий опыт: Смешанный corpus: text, binary, broken OCR и неиспользованный tail.

Метрика: Coverage denominators reproducible; false complete=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `design/MASTER_DESKTOP_RU.txt`

## LIB-029 · P1 · Desktop transport при закрытом Chrome

Проблема: Business handlers и lifecycle завязаны на extension/native messaging.

Поведение: Выделить Transport API и desktop IPC к существующим services; Chrome capture остаётся optional source adapter.

Зависимости: LIB-001, LIB-006.

Приёмка:

- Cold launch, import/search/export работают с закрытым Chrome.
- UI не получает произвольный shell endpoint.

Следующий опыт: Один Windows scenario без установленного extension, с process restart.

Метрика: Chrome dependency count on primary path=0; scenario completion.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-009`

## LIB-030 · P1 · Миграция библиотеки с проверяемым rollback

Проблема: Переход от prototype tables к canonical service может повредить существующую библиотеку.

Поведение: Версия schema, консистентный backup, migration receipt, count/hash comparison и rollback; extension exports импортируются с replay protection.

Зависимости: LIB-001, LIB-008.

Приёмка:

- Прежняя библиотека читается после migration и после rollback.
- Повторный импорт extension export не удваивает source versions.

Следующий опыт: Копия базы со старой схемой и failure injection на середине migration.

Метрика: Data loss=0; rollback success; duplicate imports=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-011`

## LIB-031 · P1 · Проверяемая установка на Dell Windows 11

Проблема: Linux tests и PowerShell launcher не доказывают работоспособность установленного desktop.

Поведение: Поставку shell/sidecar сверить с текущим кодом; test install/cold start/uninstall сохраняет user data; выбрать Tauri или доработку Tk по измеренному сценарию.

Зависимости: LIB-029, LIB-030.

Приёмка:

- Реальный Windows receipt содержит версии, профиль, import/export и restart result.
- Uninstall не стирает библиотеку без отдельного пользовательского выбора.

Следующий опыт: Clean-user installation на Dell с путём Unicode/пробелами.

Метрика: Cold-start time, install failure rate, RAM baseline, preserved data.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-010`

## LIB-032 · P1 · Виртуальная библиотека с диапазонным preview

Проблема: Загрузка всех строк и большого документа целиком тормозит Dell и создаёт ложные UI caps.

Поведение: Virtualized rows, range reader, source/versions/extraction panel; bulk selection — query handle; preview truncation явно показан.

Зависимости: LIB-004, LIB-029.

Приёмка:

- 10k+ rows доступны без загрузки всех previews.
- Чтение конца большого файла возможно через range reader.

Следующий опыт: Synthetic 10k source library с большим Unicode текстом.

Метрика: p95 scroll/search latency; peak UI RAM; inaccessible rows=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-012`

## LIB-034 · P1 · Очередь ресурсоёмких операций вместо обрезания корпуса

Проблема: Конечная RAM/CPU Dell требует контроля; искусственное уменьшение архива решает не ту проблему.

Поведение: CPU/I/O/parser workers используют настраиваемый resource budget; backpressure и WAITING_RESOURCE сохраняют полный набор jobs, диск проверяется до commit.

Зависимости: LIB-006, LIB-029.

Приёмка:

- Задачи ждут ресурс, но не исчезают из manifest.
- Остановка по disk threshold сохраняет cursor и честный incomplete.

Следующий опыт: Прогнать один и несколько collectors при ограниченной памяти.

Метрика: Throughput, p95 UI latency, peak RAM; lost queued work=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/02_DESKTOP_ARCHITECTURE_RU.txt`

## LIB-035 · P1 · Проверяемое резервное копирование и восстановление

Проблема: Библиотека теряет ценность, если нельзя восстановить originals и связи после сбоя.

Поведение: Backup содержит согласованный metadata snapshot и referenced objects; restore проверяет hashes, missing objects и schema version; отдельный отчёт конфликта.

Зависимости: LIB-008, LIB-030.

Приёмка:

- Restore в новую папку восстанавливает queries, aliases и original hashes.
- Повреждённый blob обнаружен до заявления об успешном restore.

Следующий опыт: Roundtrip на corpus с deliberate corruption одной копии.

Метрика: Verified restore success; unresolved missing blobs; recovery time.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## LIB-041 · P1 · Инкрементальный импорт выбранных папок

Проблема: Разовый импорт не отражает новые версии, исчезнувшие файлы и cloud placeholders.

Поведение: Registered root scope, content versions, rename aliases и tombstones; reparse points не обходить за scope; inaccessible placeholder фиксировать missing.

Зависимости: LIB-003, LIB-006, LIB-008.

Приёмка:

- Rename сохраняет историю версии без ошибочного удаления raw.
- Deleted upstream создаёт tombstone, а прошлый original доступен.

Следующий опыт: Обновить folder: добавить, изменить, переименовать и убрать четыре файла.

Метрика: Incremental accuracy; repeat import cost; missing reason coverage.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/DEVELOPMENT_WORKSTREAMS.json` · `D01`

## LIB-052 · P1 · Устойчивые namespaces для старых каталогов

Проблема: DESK-01, DESK-001, PR и CAT IDs разных пакетов выглядят одинаковыми и ошибочно объединяются.

Поведение: Canonical reference = archive family/version/member/record ID; friendly aliases остаются; dedup proposals только linking, original IDs не перенумеровывать.

Зависимости: LIB-008, LIB-014.

Приёмка:

- Два одноимённых IDs из разных каталогов остаются различимы.
- Merged canonical card содержит все original refs.

Следующий опыт: Импорт пересекающихся DESK/F/CAP каталогов и проверка namespace collisions.

Метрика: Unresolved ID collisions=0; historical ID retention=100%.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/08_CONTINUATION/07_HANDOFF/CONFLICTS_AND_RESOLUTIONS_RU.txt`

## LIB-056 · P1 · Формальные инварианты каталога и coverage отчёта

Проблема: Количество записей разных версий ошибочно выдаётся за уникальные реализованные функции.

Поведение: В export report явно считать source records, aliases, canonical proposals, exact raw messages и implementation evidence отдельно; каждое число выводимо из manifest.

Зависимости: LIB-014, LIB-024, LIB-052.

Приёмка:

- Сумма старых catalog counts не становится implemented count.
- Каждый canonical proposal разрешается к оригиналу или отмечен assistant_new.

Следующий опыт: Пересчитать текущий union и сформировать reproducible count table.

Метрика: Reproducible counts=100%; ambiguous count labels=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/READING_AND_ID_NAMESPACES_RU.txt`

## ACT-005 · P2 · Передача контекста и ссылки на секреты

Проблема: Один архив может смешивать личные материалы и данные, разрешённые внешнему AI.

Поведение: Хранить credential references вне prompts; строить provider-specific view с источниками и export scope, показывая фактический состав передачи.

Зависимости: нет внутри каталога; см. phase dependencies.

Приёмка:

- Секрет-канарейка не появляется в prompt, логах или handoff.
- Запрещённый источник остаётся видимым как недоступная ссылка, но его bytes не экспортируются.

Следующий опыт: Собрать два пакета одной задачи для local-only и разрешённого внешнего получателя.

Метрика: Утечки canary; расхождения preview и фактической передачи; число лишних bytes.

Условие возвращения/начала: Пока scope источника неизвестен, внешняя передача этого источника заблокирована.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`

## ACT-008 · P2 · Раздельные роли planner, retriever и critic

Проблема: Один агент формулирует план и подтверждает собственное выполнение.

Поведение: Planner предлагает шаги; retriever возвращает source-bound evidence; critic проверяет scope и недостающие условия; host принимает результат по отдельно заданным критериям.

Зависимости: нет внутри каталога; см. phase dependencies.

Приёмка:

- Critic не выдаёт grants и не переписывает пользовательскую цель.
- План с отсутствующим обязательным источником возвращается на retrieval.

Следующий опыт: На одном дефекте сравнить monolithic ответ и роли с одинаковым бюджетом.

Метрика: False acceptance; число обнаруженных gap; verified outcome на затраченный бюджет.

Условие возвращения/начала: Несколько LLM использовать только если качество превышает дешевую базовую схему.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-27`

## ACT-009 · P2 · Точечный NEXT_CONTEXT_REQUEST

Проблема: Неполный пакет приводит к догадкам либо повторной отправке всего архива.

Поведение: AIResult может запросить конкретный symbol, caller, решение или fixture; host проверяет scope и возвращает дополнительный source-bound пакет.

Зависимости: ACT-008.

Приёмка:

- Запрос неизвестного файла создаёт explicit missing, без выдуманной цитаты.
- Повтор delta не меняет исходный snapshot и не дублирует уже принятый источник.

Следующий опыт: Удалить из исходного task pack вызывающую функцию и проверить точечный цикл дополнения.

Метрика: Rounds до достаточного evidence; bytes дополнительного контекста; gap recall.

Условие возвращения/начала: Автоматический поиск не расширяет разрешённые namespace и источники.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-25`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-39`

## ACT-010 · P2 · Двусторонний handoff для разных AI

Проблема: Ответ чужого AI трудно привязать к цели и оценить без переписывания форматов.

Поведение: Экспортировать neutral task contract и views для выбранного AI; импортировать PATCH_PROPOSAL, RESEARCH_RESULT, NEEDS_CONTEXT, BLOCKED и limitations как proposal.

Зависимости: ACT-005, ACT-009.

Приёмка:

- Ответ со старым snapshot не закрывает finding.
- Текст DONE без artifacts импортируется как claim, не как результат проверки.

Следующий опыт: Сделать один ручной TXT roundtrip и один adapter roundtrip на одинаковой задаче.

Метрика: Доля валидных bindings; потери refs; число ручных преобразований.

Условие возвращения/начала: Доступность API и формат конкретного provider проверять отдельно; manual export остаётся рабочим маршрутом.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-39`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/05_SCHEMAS/AIResult.schema.json`

## ACT-052 · P2 · Личный контекст с временной областью применимости

Проблема: Старая предпочтительная модель или отменённое решение становится вечным правилом.

Поведение: Хранить source-linked preference/decision revisions, validity, supersedes и project scope; текущая явная команда обновляет planned behavior, не переписывает исторический факт.

Зависимости: ACT-005.

Приёмка:

- Отменённое решение возвращается как история с заменяющим ref.
- Preference одного проекта не выдаёт права читать другой namespace.

Следующий опыт: Создать конфликт старого ZIP и новой команды и проверить объяснимое разрешение.

Метрика: Stale preference applications; provenance completeness; correction effort.

Условие возвращения/начала: Не реконструировать отсутствующую личную историю как цитату.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/ALL_TRACKS_INDEX.json` · `RND-10`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`

## ACT-056 · P2 · Контроль цели от фразы до проверенного результата

Проблема: Сбор красивого handoff может завершить job, хотя ожидаемое пользователем действие ещё не сделано.

Поведение: Новое предложение: для каждой команды хранить явное required outcome и ledger этапов подготовлено/передано/предложен патч/проверено/применено; UI показывает достигнутый этап без переноса статуса между ними.

Зависимости: ACT-010.

Приёмка:

- Создание документа не закрывает goal «исправить баг», если patch не принят.
- Для goal «только подготовь» создание проверенного handoff является достаточным завершением.

Следующий опыт: Сравнить две команды с одинаковым контекстом и разными конечными результатами.

Метрика: Premature completions; корректность goal-stage mapping; missing next action.

Условие возвращения/начала: Сначала внедрить для одного vertical, затем расширять ontology результатов.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`

## LIB-012 · P2 · Импорт всех ветвей разговоров

Проблема: Выбор только видимой ветки теряет альтернативные ответы и исправления пользователя.

Поведение: Импортировать весь mapping conversations.json: node IDs, parent/children, roles, branch state и attachment references; raw export сохранить отдельно.

Зависимости: LIB-006, LIB-008.

Приёмка:

- Все nodes исходного mapping представлены, включая disconnected/unknown nodes.
- 1001 разговор не обрезается старым лимитом.

Следующий опыт: Fixture с разветвлённым диалогом, отсутствующим attachment и повторным импортом.

Метрика: Node/edge coverage; attachment missing ledger completeness.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-013`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/04_HISTORY_RECOVERY_RU.txt`

## LIB-013 · P2 · Авторство и вложенные цитаты в сообщениях

Проблема: Текст прежнего ассистента, вставленный пользователем, может быть ошибочно записан как новая пользовательская идея.

Поведение: Хранить observed message role отдельно от span attribution; цитаты и пересказы отмечать своим origin; UNKNOWN не угадывать по стилю.

Зависимости: LIB-012.

Приёмка:

- Вставленный ответ assistant внутри USER не становится user_asserted fact.
- Сообщение без role marker остаётся UNKNOWN.

Следующий опыт: Разметить fixture из реальных смешанных RU/EN сообщений и quoted blocks.

Метрика: Unsupported attribution rate=0; ручные corrections сохраняются.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/DEVELOPMENT_WORKSTREAMS.json` · `D03`

## LIB-015 · P2 · Раздельные времена создания, захвата и действия

Проблема: Дата получения snapshot ошибочно выдаётся за дату исходного сообщения или актуальность утверждения.

Поведение: Хранить claimed, observed captured, effective и expiry timestamps с timezone/precision/origin; относительные даты не дорисовывать.

Зависимости: LIB-008.

Приёмка:

- Capture date не заменяет неизвестный message date.
- Конфликтующие claimed timestamps остаются с origins.

Следующий опыт: Импортировать старое сообщение сегодня и несколько неоднозначных временных меток.

Метрика: Invented timestamps=0; time provenance completeness.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/data_labeling/TAXONOMY_RU.json` · `time.validity`

## LIB-017 · P2 · Поиск по ID, путям и FTS без обязательной модели

Проблема: Пользователь не должен ждать embeddings или inference, чтобы найти точный файл и прежнее решение.

Поведение: Базовый поиск по exact IDs/path/hash/FTS с facet filters; результаты возвращают source version, span и coverage, semantic rerank остаётся опциональным.

Зависимости: LIB-001, LIB-014, LIB-016.

Приёмка:

- Без модели находятся кириллица, exact path и source ID.
- Поиск по obsolete версии показывает статус и новую связь.

Следующий опыт: Набор 30 реальных запросов на сохранённых источниках: FTS baseline.

Метрика: Recall@k/time-to-source; p95 latency; model calls=0 для exact lookup.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-018`

## LIB-018 · P2 · Независимые аспекты тегов с происхождением

Проблема: Один общий tag смешивает формат, тему, цель, статус и проверенность.

Поведение: Версионируемые label assertions по 16 facets; observed/rule/user/model/imported origins различаются; custom namespaces добавляются без потери неизвестных значений.

Зависимости: LIB-014, LIB-016.

Приёмка:

- Смена темы не меняет source_id и bytes.
- Accepted label не повышает task_state и не открывает права исполнения.

Следующий опыт: Разметить stratified corpus детерминированно, затем добавить AI proposals на выбранной части.

Метрика: Correction rate; cost per accepted useful label; lost unknown tags=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/data_labeling/TAXONOMY_RU.json`

## LIB-019 · P2 · Версии целей на русском и английском

Проблема: Неполный английский, русские уточнения и отрицания могут создать несовместимые задачи.

Поведение: Raw wording сохранять; normalized goal и переводы — отдельные версии с language, negation spans, quantities и supersedes; новые явные исправления связывать с прежним intent.

Зависимости: LIB-013, LIB-014, LIB-018.

Приёмка:

- «Run… нет, только покажи» сохраняет обе версии и актуальное ограничение.
- Числа, repo names и отложенность не меняются переводом.

Следующий опыт: 20 пар RU/EN запросов с corrections и незнакомыми терминами.

Метрика: Meaning-preservation review; critical slot loss=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/DEVELOPMENT_WORKSTREAMS.json` · `D03`

## LIB-020 · P2 · Журнал незакрытых вопросов и терминов

Проблема: Неоднозначные слова JeV/Jeff и вопросы теряются в больших каталогах.

Поведение: Сохранять unanswered/ambiguous record с quote, candidate interpretations, missing evidence и next action; отвеченный вопрос закрывается ссылкой на ответ.

Зависимости: LIB-019.

Приёмка:

- Unknown term не разворачивается в выдуманный продукт.
- Повторный handoff сохраняет все unresolved IDs.

Следующий опыт: Пройти исходные запросы и сравнить вопросы с существующими ответами.

Метрика: Open-loop retention=100%; unsupported interpretation=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-06`

## LIB-021 · P2 · Противоречия без удаления прежних решений

Проблема: Историческая обязательность Chrome и текущий desktop приоритет могут смешаться в новом roadmap.

Поведение: Типизированные contradicts/supersedes связи с обеими цитатами и областью действия; resolution записывается отдельно, а не меняет источник.

Зависимости: LIB-015, LIB-019.

Приёмка:

- Новый desktop intent отмечает прежний Chrome-only шаг historical.
- Решение не распространяется на несвязанные ограничения.

Следующий опыт: Разрешить три известные пары conflicting docs в UI draft.

Метрика: Unresolved contradictions count; incorrectly discarded history=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-016`

## LIB-025 · P2 · Документ следующему AI из короткого запроса

Проблема: Новый чат начинает стратегию заново без исходников и фактического следующего gap.

Поведение: Text intent выбирает проект/goal revision; пакет включает exact refs, baseline, blockers, known actions, expected output и postchecks; сначала manual export.

Зависимости: LIB-017, LIB-019, LIB-024.

Приёмка:

- Новый reader находит raw request, pinned source и первый незакрытый шаг.
- Пакет не заявляет current implementation по старому сообщению.

Следующий опыт: Собрать одну команду «полный контекст repo и мои идеи» и дать независимому reviewer восстановить следующий шаг.

Метрика: Time to correct handoff; unsupported done claims=0; source binding completeness.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/DEVELOPMENT_WORKSTREAMS.json` · `D04`

## LIB-026 · P2 · WHY_THIS_PACKET и контролируемая корзина контекста

Проблема: Автоматическая выборка не объясняет, почему включены одни источники и отсутствуют другие.

Поведение: Для каждого элемента хранить связь с goal/question/blocker; пользователь видит selected, excluded, missing и unread; ограничение prompt меняет payload, а не архив.

Зависимости: LIB-025.

Приёмка:

- Каждый включённый item имеет reason и source version.
- Исключённый из prompt raw объект остаётся доступным и указанным.

Следующий опыт: Сравнить packet при двух разных token budgets на одном goal.

Метрика: Task evidence coverage; irrelevant-token share; silently omitted sources=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/contracts/CONTEXT_PACKET_CONTRACT.json`

## LIB-027 · P2 · NEED_CONTEXT для точного дозапроса

Проблема: AI вынужден гадать, если нужной строки или документа не было в первом payload.

Поведение: Возврат typed NEED_CONTEXT со source refs/ranges/question; host проверяет scope и собирает version-bound delta или явный missing response.

Зависимости: LIB-025, LIB-026.

Приёмка:

- Запрос существующего диапазона возвращает точный hash/span.
- Несуществующая ссылка даёт MISSING, а не синтетический текст.

Следующий опыт: Два последовательных дозапроса к большому файлу и один invalid source request.

Метрика: Exact delta fulfillment; time to evidence; fabricated payloads=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-02`

## LIB-028 · P2 · Обновления контекста вместо повторной пересылки всего ZIP

Проблема: Повторная отправка всех вложенных пакетов расходует время и маскирует реальные изменения.

Поведение: Root manifest связывает base digest и additions/changes/tombstones/goal revisions; delta применим только к совпадающей базе, иначе выдаётся full manifest.

Зависимости: LIB-005, LIB-019, LIB-025.

Приёмка:

- Base+delta восстанавливают тот же manifest, что fresh export.
- Неверный base hash обнаруживается до применения.

Следующий опыт: Сделать два updates с rename, delete и corrected goal; replay deltas.

Метрика: Transferred bytes saved; reproducibility; wrong-base acceptance=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-03`

## LIB-037 · P2 · Выбранная передача контекста провайдеру

Проблема: Наличие локального источника не означает согласие отправить весь archive внешнему AI.

Поведение: Packet привязан к configured export scope и конкретному provider request; preview показывает full paths, counts и content categories; историю передачи хранить без секретов.

Зависимости: LIB-025, LIB-026.

Приёмка:

- Источник вне configured scope не входит в payload.
- Manual packet и API payload имеют один manifest contract.

Следующий опыт: Создать public/private коллекции и экспортировать goal с обеими зависимостями.

Метрика: Unexpected exported objects=0; payload-manifest equality.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/contracts/CONTEXT_PACKET_CONTRACT.json`

## LIB-038 · P2 · Редактирование приватных данных как отдельная проекция

Проблема: Скрытие секретов перед передачей может разрушить цитаты или незаметно изменить original.

Поведение: Redacted view хранит policy/version и mapping к raw spans; originals локально неизменны; exported packet сообщает об удалённых диапазонах без их раскрытия.

Зависимости: LIB-014, LIB-016, LIB-037.

Приёмка:

- Raw hash не меняется после redaction.
- Test secret не встречается в payload/log/preview index.

Следующий опыт: Fixture из заметок с synthetic tokens и полезными adjacent code lines.

Метрика: Secret leakage=0; useful context retained; redaction traceability.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/data_labeling/TAXONOMY_RU.json` · `access.sensitivity`

## LIB-039 · P2 · Ссылки на секреты вместо ключей в библиотеке

Проблема: API ключ может попасть в raw context, stdout или WebView storage.

Поведение: Credentials живут в отдельном local secret provider; task/config содержит opaque credential_ref; сбор контекста исключает runtime secret material.

Зависимости: LIB-029, LIB-037.

Приёмка:

- Ключ не записывается в source DB, export, stdout и localStorage.
- Отсутствующий credential_ref даёт понятный MISSING_CREDENTIAL.

Следующий опыт: Использовать synthetic credential и просканировать generated packet/logs.

Метрика: Credential leakage=0; secret-independent reproducibility.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/02_DESKTOP_ARCHITECTURE_RU.txt`

## LIB-048 · P2 · Группы происхождения вместо подсчёта копий как доказательств

Проблема: Пять копий одной статьи или старого AI ответа создают ложное ощущение независимого подтверждения.

Поведение: Claim lineage группирует exact copies и quoted secondary sources; доказательства показывают original families и supported scope, близость текста только candidate link.

Зависимости: LIB-008, LIB-018.

Приёмка:

- Одинаковая статья из двух ZIP даёт одну source family и два aliases.
- Пересказ без первоисточника сохраняет secondary status.

Следующий опыт: Fixture original→quote→summary→copied archive и действительно независимый source.

Метрика: Independent family count accuracy; false corroboration=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-21`

## LIB-050 · P2 · Коллекции и сохранённые представления без копирования

Проблема: Одни и те же материалы нужны в проектах, чатах, R&D и задачах, но папки создают дубли.

Поведение: Drive-like tree и Notion-like saved queries/backlinks отображают один source/version; фильтры проектов, тем, ролей, свежести и evidence state сохраняются как view definitions.

Зависимости: LIB-017, LIB-018, LIB-032.

Приёмка:

- Добавление source в две коллекции не копирует raw blob.
- Saved view обновляется после новых tags без потери manual pins.

Следующий опыт: Создать views «мои идеи», «unanswered», «Studious blockers» на одном corpus.

Метрика: Time-to-find; duplicate storage due to views=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/02_DESKTOP_ARCHITECTURE_RU.txt`

## LIB-053 · P2 · Проверка «ни одна цель не потеряна» при новом handoff

Проблема: Новая краткая дорожная карта может забыть deferred идеи и редкие ограничения.

Поведение: Сравнивать полный goal registry с новым handoff: covered/deferred/superseded/unmapped; каждый прежний goal сохраняет место или явную причину изменения.

Зависимости: LIB-019, LIB-020, LIB-025, LIB-052.

Приёмка:

- Идея из конца длинного запроса обнаруживается, если не отражена в handoff.
- Deferred не меняется на rejected без решения.

Следующий опыт: Намеренно удалить один редкий goal из draft packet и проверить checker.

Метрика: Goal carryover coverage; silent omission count=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/03_MASTER_STRATEGY.md`

## LIB-055 · P2 · Benchmark полезности библиотеки на собственных задачах

Проблема: Сравнение с Notion и число функций не измеряют пользу для конкретного рабочего процесса.

Поведение: Frozen набор найти решение/собрать repo context/найти missing source/восстановить backup; измерить время, exactness, RAM и ручные corrections до и после изменения.

Зависимости: LIB-017, LIB-025, LIB-032.

Приёмка:

- Все сравнения используют одинаковый dataset и инструкции.
- Заявление об улучшении сопровождается сырыми результатами, environment и sample size.

Следующий опыт: 10–30 реальных рабочих задач с baseline текущего пути и новой вертикалью.

Метрика: Median/p95 task time, source accuracy, verified completion, maintenance cost.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## LIB-057 · P2 · Учёт реально прочитанного контекста по версии

Проблема: Наличие всего корпуса в ZIP не доказывает, что исполнитель прочёл каждый файл.

Поведение: Read/used inventory хранит version+range+reader/run; source_available, retrieved, parsed, semantically_reviewed и cited различаются; unknown остаётся unknown.

Зависимости: LIB-014, LIB-024, LIB-025.

Приёмка:

- Неоткрытый последний том не получает reviewed status.
- После source update прежний read receipt не покрывает новую версию.

Следующий опыт: Новый reviewer читает выборочно 3 из 10 parts; проверить coverage statement.

Метрика: False reviewed claims=0; explicit unread bytes/ranges.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/contracts/CONTEXT_PACKET_CONTRACT.json`

## LIB-059 · P2 · Контракты точности для чисел, единиц и таблиц

Проблема: Модельная нормализация может смешать валюту, сеть, сумму, token units или пример с фактическим результатом.

Поведение: Structured values сохраняют lexical original, unit/network IDs, normalization rule и source spans; example/hypothetical/observed outcome различаются; ambiguous values не вычисляются молча.

Зависимости: LIB-014, LIB-016, LIB-018.

Приёмка:

- Числа из исторического примера funnel не появляются как measured statistics.
- Decimal/scientific/raw token amounts восстанавливаются без float округления.

Следующий опыт: Fixture с евро/SOL, decimal amounts и старой примерной воронкой результатов.

Метрика: Numeric/unit exactness; hypothetical-to-observed promotions=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/data_labeling/TAXONOMY_RU.json` · `economics.hypothesis`

## ACT-014 · P3 · Контрпримеры и замороженные критерии выбора

Проблема: Кандидат может пройти слабые или изменённые под себя тесты.

Поведение: Фиксировать acceptance до выбора патча; отдельно создавать негативные кейсы, проверять удаление assertions и выполнять held-out случаи в изоляции.

Зависимости: ACT-008.

Приёмка:

- Патч, выключивший проверку, не выигрывает по зелёному CI.
- Одинаковый набор обязательных критериев применяется ко всем кандидатам.

Следующий опыт: Создать намеренно неверный fix, проходящий старый тест, и измерить обнаружение.

Метрика: Mutation detection; regression escape; доля ослабленных gates.

Условие возвращения/начала: Generated test code тоже требует отдельной среды исполнения.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-27`

## LIB-022 · P3 · Граф цель → код → проверка → результат

Проблема: Каталожная функция и старый green receipt могут быть приняты за текущую реализацию.

Поведение: Связать requirement span с owner/SHA, test definition, actual run receipt и device/environment; отдельные состояния proposed, source_present, tested и device_verified.

Зависимости: LIB-014, LIB-019.

Приёмка:

- Тест на старом SHA не подтверждает изменённую функцию.
- Наличие файла SUCCESS не даёт DONE.

Следующий опыт: На frozen fixture поменять код после receipt и проверить ослабление статуса.

Метрика: Доля целей с актуальным evidence chain; false implementation claims=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-05`

## LIB-023 · P3 · Инвалидация зависимого контекста при обновлении источника

Проблема: Новые исходники не обновляют summaries, embeddings и recommendations; устаревший контекст выглядит свежим.

Поведение: Source revision событие инвалидирует только зависимые derived artifacts; raw и исторические выводы остаются; delta re-index и пересборка packet идут через existing queue.

Зависимости: LIB-016, LIB-022.

Приёмка:

- Изменение одного source помечает его summary stale.
- Независимые summaries не пересчитываются без причины.

Следующий опыт: Поменять source fragment в графе с двумя независимыми ветвями.

Метрика: Stale detection recall; unnecessary recomputation; update latency.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## LIB-033 · P3 · Открытие точного источника в VS Code

Проблема: Finding без привязки к конкретной версии/строке не помогает продолжить исправление.

Поведение: Source links открывают mapped checkout file:line; при другом current SHA показать различие и предложить pinned view.

Зависимости: LIB-002, LIB-011, LIB-029.

Приёмка:

- Правильно открываются пути с Unicode и пробелами.
- Старый line reference не выдаётся за текущую строку после изменения файла.

Следующий опыт: Fixture rename и drift между pinned source и local checkout.

Метрика: Correct target rate; stale link detection.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-023`

## LIB-044 · P3 · История GitHub PR, issues и CI с полной пагинацией

Проблема: Текущий snapshot не объясняет abandoned branches и невыполненные обещания прошлых PR.

Поведение: Отдельный authorized adapter хранит PR/issue/comments/checks refs, head/base SHAs, timestamps и completeness cursors; старый merge status не становится current without refresh.

Зависимости: LIB-004, LIB-011, LIB-022.

Приёмка:

- Все страницы выбранного scope представлены или явно missing.
- CI receipt связан с exact commit, а не только номером PR.

Следующий опыт: Импорт fixture из >1 страницы обсуждений с changed PR head.

Метрика: History scope coverage; wrong-SHA attribution=0.

Условие возвращения/начала: После Git snapshot и manual handoff; доступ/API лимиты сверять при реализации.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## LIB-054 · P3 · Капсулы неудачных попыток

Проблема: Новый чат повторяет уже неудачный подход, потому что сохранены только хорошие результаты.

Поведение: Failure capsule хранит goal/source version, attempt, environment, evidence, reason и условия повторения; связать с recipes и handoff.

Зависимости: LIB-020, LIB-022, LIB-025.

Приёмка:

- Неудачный импорт/поиск остаётся доступен в next packet.
- Успех новой попытки не удаляет старые причины.

Следующий опыт: Повторить похожий запрос с сохранённой failure capsule и без неё.

Метрика: Repeated-known-error rate; recovery time.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-09`

## RND-002 · P3 · Матрица требование → код → проверка → результат

Проблема: Заявленное в ZIP завершение и существующая функция могут расходиться.

Поведение: Для каждой цели фиксировать implementation evidence, test evidence и blockers; различать missing code, no test, not run, failed и stale.

Зависимости: RND-001.

Приёмка:

- Совпадение имени не закрывает требование.
- Изменение binding инвалидирует затронутый результат.

Следующий опыт: Внести в fixture пять обещанных функций, из которых только две имеют рабочий тест.

Метрика: Точность обнаружения незавершённых требований.

Условие возвращения/начала: После карты source owners и доступного каталога требований.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-028`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_WORKFLOW_CATALOG.json` · `SCE_V2::W3-WF26`

## RND-003 · P3 · Полный dependency graph для контекста и анализа изменений

Проблема: Python AST и regex JS не покрывают межъязыковые или динамические связи.

Поведение: Строить граф resolved/unresolved edges для поддержанных языков, SCC и impacted tests; динамические связи сохранять явными неизвестными.

Зависимости: RND-001.

Приёмка:

- Цикл из трёх модулей образует SCC с точными paths.
- Dynamic import и alias без resolver не считаются закрытыми.

Следующий опыт: Небольшой смешанный Python/JS/TS corpus с циклами, alias и config dispatch.

Метрика: Recall известных dependency edges и unresolved count.

Условие возвращения/начала: Полный semantic parser добавлять отдельно для каждого фактически нужного языка.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-03`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::SMELL-05`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::SMELL-06`

## RND-004 · P3 · Кандидаты code smells с воспроизводимым подтверждением

Проблема: Большая функция, TODO или broad except ещё не доказанный дефект.

Поведение: Формировать finding с source span, affected scenario, гипотезой и минимальным reproducer; ранжировать по silent loss, неверным effects и blocker impact.

Зависимости: RND-001, RND-003.

Приёмка:

- Статический finding имеет STATIC_CANDIDATE до отдельной проверки.
- FIXED требует diff и релевантного результата проверки.

Следующий опыт: Разобрать десять кандидатов и отделить подтверждённые дефекты от ложных срабатываний.

Метрика: Подтверждённые дефекты на час анализа; false-positive rate.

Условие возвращения/начала: Автоисправление только после подтверждения проблемы и выбранного scope.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/11_CODE_SMELLS_AND_PRIORITIES_RU.txt`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::SMELL-10`

## RND-005 · P3 · История PR и неудачных попыток как контекст изменения

Проблема: Новая задача может повторять уже отвергнутую реализацию либо закрытый PR.

Поведение: Привязывать PR/ветку/commit/review/CI к цели, восстанавливать причины отказа и показывать различия текущей базы.

Зависимости: RND-001, RND-002.

Приёмка:

- Пагинация включает последнюю страницу PR history.
- Закрыт без merge и merged различаются; отсутствующие данные отмечены.

Следующий опыт: Подготовить историю одного blocker из сохранённых PR metadata, затем проверить вручную связи.

Метрика: Доля повторных попыток с найденным релевантным прошлым опытом.

Условие возвращения/начала: Для недоступных PR сохранять missing-source запись, не выдумывать причину.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `OCC_RND::history.version_link`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `OCC_RND::library.search_related_attempts`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## RND-006 · P3 · AI-код → изолированный patch → независимая проверка

Проблема: Текст AI не гарантирует пригодный patch на нужной базе.

Поведение: Собирать TaskSpec и context digest, принимать patch в отдельном worktree, проверять allowed paths, base и postconditions; вернуть evidence в библиотеку.

Зависимости: RND-002, RND-003, RND-004.

Приёмка:

- Wrong base и изменённый patch hash отклоняются.
- Два worktree не делят test artifacts.
- Редактирование expected answer вместо исправления дефекта не проходит независимый сценарий.

Следующий опыт: Одна реальная маленькая исправляемая ошибка на pinned fixture репозитория.

Метрика: Verified patch rate, число повторов и cost per accepted patch.

Условие возвращения/начала: После working context roundtrip и установленных проверок репозитория.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-04`
- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-05`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::PIPE-08`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::PIPE-09`

## RND-007 · P3 · PR/CI/merge с привязкой к реально проверенному дереву

Проблема: Успешная проверка старого head не подтверждает новый публикуемый код.

Поведение: Готовить reviewable diff, сверять опубликованный tree/head с tested tree и сохранять фактический merged SHA из ответа сервиса.

Зависимости: RND-006.

Приёмка:

- Смена head инвалидирует старую проверку.
- Неизвестный ответ публикации требует reconciliation до повтора.
- Squash SHA не путается с прежним branch head.

Следующий опыт: Испытать dry-run adapter на fixture ответах CI с изменением head и таймаутом.

Метрика: Расхождения tested/published tree и duplicate publications.

Условие возвращения/начала: Реальные записи GitHub только в отдельно заданном scope.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-06`
- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-07`
- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-08`

## RND-008 · P3 · Воспроизводимая сборка и идентичность установленного приложения

Проблема: Тесты checkout могут относиться к другому коду, чем запущенный desktop или bot.

Поведение: Записывать toolchain, dependencies, artifact digest, установленный entrypoint и source fingerprint до и после обновления.

Зависимости: RND-001.

Приёмка:

- Различие installed/source hashes даёт BLOCKED.
- Сборка фиксирует различия nondeterministic artifacts.
- Неудачная миграция не активирует новый runtime.

Следующий опыт: Установить две версии в изолированных каталогах и обнаружить намеренную подмену entrypoint.

Метрика: Доля запусков с проверенной installed identity.

Условие возвращения/начала: Реальное устройство и поддержанная текущим репозиторием среда ещё не проверены.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F15`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-035`
- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-09`

## ACT-001 · P4 · Единый IntentSpec для текста и голоса

Проблема: Разные способы ввода могут порождать несовместимые команды и терять исправления.

Поведение: Создавать типизированный intent с goal, project, operation_id, revision, snapshot, режимом эффекта, бюджетом и ссылками на исходный ввод; отделять интерпретацию от исходной фразы.

Зависимости: нет внутри каталога; см. phase dependencies.

Приёмка:

- Одинаковые текстовый и окончательный голосовой ввод дают эквивалентные слоты.
- Отсутствующий capability или неоднозначный project даёт BLOCKED/NEEDS_INPUT, без запуска shell.

Следующий опыт: Разметить 30 команд с отрицаниями, названиями repo и исправлениями и проверить сериализацию.

Метрика: Точность критических слотов; число неявных значений; доля воспроизводимых разборов.

Условие возвращения/начала: Реализацию начать после определения владельца команд и библиотечного состояния в актуальном коде.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/05_SCHEMAS/ActionSpec.schema.json`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`

## ACT-002 · P4 · Каталог реальных исполнимых capabilities

Проблема: Названия из документов принимаются за существующие команды.

Поведение: Хранить versioned manifest capability с входной/выходной схемой, реальным entrypoint, разрешёнными эффектами, footprint ресурсов и проверенными средами.

Зависимости: ACT-001.

Приёмка:

- Каждая enabled capability разрешается в существующий adapter и executable entrypoint.
- Документальная идея без adapter остаётся planned и не появляется как готовая кнопка Run.

Следующий опыт: Сопоставить один текущий workflow с реальным entrypoint после чтения репозитория.

Метрика: Доля enabled capabilities с исполнимым контрактом и receipt; ложные enabled.

Условие возвращения/начала: Не включать capability, пока текущий код и среда не проверены.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`

## ACT-003 · P4 · Полномочия как отдельная версия политики

Проблема: Planner может спутать желание выполнить задачу с получением доступа.

Поведение: Host проверяет project roots, tool IDs, виды эффекта, целевые сервисы и уже действующую авторизацию; новая потребность в доступе показывается отдельно от плана.

Зависимости: ACT-001, ACT-002.

Приёмка:

- Policy deny не обходится ни workflow JSON, ни output модели.
- Действующая авторизация повторно используется в своей области; расширение области отражается в permission diff.

Следующий опыт: Проверить разрешённый read и запрещённый write для одного intent.

Метрика: Неразрешённые эффекты; повторные лишние запросы; полнота policy audit.

Условие возвращения/начала: Не выдавать широкие права ради прохождения неизвестного workflow.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-35`

## ACT-004 · P4 · Разделение инструкций и недоверенного контекста

Проблема: Импортированный README или ответ AI может содержать команды сменить политику.

Поведение: Передавать документы в data lane с origin/authority; только доверенный host получает capability grants из пользовательской политики.

Зависимости: ACT-003.

Приёмка:

- Инструкция из Telegram export отправить ключ не меняет права job.
- Поддельный permit внутри tool result не принимается как authorisation.

Следующий опыт: Вставить hostile инструкции в три разрешённых источника и сравнить исходные и итоговые scopes.

Метрика: Число authority escalation; покрытие origin labels.

Условие возвращения/начала: Любой новый adapter проходит этот корпус до разрешения действий.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-35`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`

## ACT-006 · P4 · Детерминированный маршрут известных команд

Проблема: Обязательный LLM на каждом простом действии увеличивает задержку и неопределённость.

Поведение: Известные typed intents выполнять через проверенный registry; неоднозначные обращения передавать в advisory planner, STOP обрабатывать локально.

Зависимости: ACT-001, ACT-002.

Приёмка:

- Повтор known command выбирает одинаковый adapter без генерации кода.
- Неизвестная команда становится proposal, а не строкой терминала.

Следующий опыт: Сравнить простой rule router с ручной эталонной разметкой команд.

Метрика: Intent accuracy; p50/p95 routing; число лишних model calls.

Условие возвращения/начала: Правила расширяются по проверенным примерам, не по угадыванию названия функции.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/02_NEXT_IMPLEMENTATION_RU.md`

## ACT-011 · P4 · Snapshot fence перед изменением

Проблема: Патч или план может быть подготовлен для уже устаревшего состояния.

Поведение: Связать кандидата с commit, dirty patch, source hashes, intent revision и policy version; перед изменением сравнить с текущим состоянием.

Зависимости: ACT-001, ACT-003.

Приёмка:

- Изменение HEAD, исходника или разрешения переводит кандидата в STALE.
- Перепланирование сохраняет оба snapshots и причину отклонения.

Следующий опыт: Изменить один файл между retrieval и commit на fixture.

Метрика: Отклонённые stale candidates; silent overwrite; время обновления.

Условие возвращения/начала: Нельзя применять к новой базе по одному совпадению имени проекта.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-21`

## ACT-012 · P4 · Проверяемый исход и ExecutionReceipt

Проблема: Зелёный лог или уверенное сообщение модели не доказывает нужный результат.

Поведение: До выполнения задавать outcome predicates; receipt связывать с операцией, входами, средой, артефактами, границей эффекта и проверившим компонентом.

Зависимости: ACT-001, ACT-002, ACT-011.

Приёмка:

- Тест другого SHA отвергается.
- Структурная валидность JSON не подменяет проверку результата пользователя.

Следующий опыт: Подложить ложный DONE, чужой тест и частичный экспорт под один goal.

Метрика: False acceptance; доля receipts с полным binding; verified task success.

Условие возвращения/начала: Verified всегда указывает scope; не повышать исторический prototype receipt до production.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-22`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/05_SCHEMAS/ExecutionReceipt.schema.json`

## ACT-015 · P4 · Идентичность намеренной операции

Проблема: Повтор запроса после сбоя и новая одинаковая команда пользователя имеют разный смысл.

Поведение: Выдавать operation_id на логическую операцию; retry сохраняет ID, новое намерение получает новый; id привязывается к canonical intent.

Зависимости: ACT-001.

Приёмка:

- Один ID с другим intent отклоняется.
- Повтор того же запроса возвращает существующий status/receipt.

Следующий опыт: Послать 16 повторов, затем новую намеренную команду с таким же текстом.

Метрика: Duplicate operations; ошибочно склеенные намерения; replay consistency.

Условие возвращения/начала: Хеш текста сам по себе не является достаточной идентичностью операции.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-23`

## ACT-022 · P4 · Транзакционный outbox состояния и заданий

Проблема: Сбой между обновлением job state и постановкой эффекта оставляет потерянную задачу.

Поведение: Согласованно фиксировать state transition, outbox intent и receipt в существующем durable owner; dispatcher читает только подтверждённые записи.

Зависимости: ACT-015.

Приёмка:

- Crash до transaction commit не создаёт выполнимую половину записи.
- Restart после commit повторно видит ту же outbox запись и operation ID.

Следующий опыт: Fault injection до/после каждой локальной транзакционной границы.

Метрика: Lost jobs; orphan outbox; replay convergence.

Условие возвращения/начала: Не объявлять произвольный remote action ACID и не создавать вторую конкурирующую очередь.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-23`

## ACT-023 · P4 · UNKNOWN и сверка внешнего результата

Проблема: Timeout не показывает, выполнился ли запрос на стороне сервиса.

Поведение: Переводить ambiguous outcome в UNKNOWN; сначала читать external operation/status или искать observable effect; повторять только по доказанному отсутствию либо идемпотентному контракту.

Зависимости: ACT-012, ACT-015, ACT-022.

Приёмка:

- Lost response после remote commit не вызывает второй submit.
- Недоступная сверка остаётся UNKNOWN с причиной, а не FAILED/SUCCESS.

Следующий опыт: Смоделировать сервер, выполнивший запрос и потерявший ответ.

Метрика: Слепые повторы; время resolution; unresolved age.

Условие возвращения/начала: Без наблюдаемого результата необратимую операцию автоматически не повторять.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-23`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-33.md` · `RND-33`

## ACT-024 · P4 · Возобновляемый workflow с проверенными checkpoints

Проблема: Перезапуск ПК или процесса заставляет workflow начинаться заново.

Поведение: Хранить verified prefix, pending steps, attempts и bindings; на resume переоценивать freshness и permissions, не повторять подтверждённый эффект.

Зависимости: ACT-011, ACT-012, ACT-022, ACT-023.

Приёмка:

- Restart сохраняет verified шаги и отдельно unknown шаги.
- Устаревшие inputs инвалидируют только зависимую часть плана.

Следующий опыт: Остановить workflow после каждого шага, восстановить и сравнить итог с непрерывным запуском.

Метрика: Resume success; повторные эффекты; восстановленные checkpoints.

Условие возвращения/начала: Нельзя продолжать на изменённой среде без revalidation.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-33.md` · `RND-33`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`

## ACT-025 · P4 · Deadline, отмена и bounded retries

Проблема: Фоновый job может бесконечно повторяться и продолжать после отмены.

Поведение: Задать parent cancellation, deadline и retry policy на шаг; отмена запрещает новые эффекты, уже отправленные внешние запросы передаются reconciliation.

Зависимости: ACT-015, ACT-023, ACT-024.

Приёмка:

- После подтверждённого cancel новые effect steps не стартуют.
- Retry exhaustion виден как конкретный blocker, без бесконечного цикла.

Следующий опыт: Отменить parent при одновременно queued, running и remote-unknown steps.

Метрика: Cancel-to-no-new-work latency; runaway retries; untracked child jobs.

Условие возвращения/начала: Отмена HTTP не трактуется как доказанная отмена server-side эффекта.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/05_SCHEMAS/ActionSpec.schema.json`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-36`

## ACT-026 · P4 · Сквозные измерения команды

Проблема: Время ответа модели не равно времени полезного результата.

Поведение: Фиксировать speech-end, accepted intent, context-ready, action-start, verified outcome, очередь, retries и стоимость всех ветвей.

Зависимости: ACT-001, ACT-012.

Приёмка:

- Медленный failed candidate учитывается в общей стоимости.
- Отчёт отделяет routing, retrieval, model и execution latency.

Следующий опыт: Прогнать 20 baseline задач и сохранить сырые timestamps вместе с итогами.

Метрика: p50/p95 time-to-verified; false acceptance; total cost; completion rate.

Условие возвращения/начала: Не публиковать SLA и миллисекунды до измерения на целевой машине.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-42`

## ACT-032 · P4 · Локальная независимая остановка

Проблема: STOP, зависящий от облака или занятого ASR, не может быстро остановить работу.

Поведение: Отдельная кнопка/shortcut и локальный путь отменяют запуск новых шагов и leases; интерфейс честно показывает завершённое, остановленное и UNKNOWN.

Зависимости: ACT-025, ACT-023.

Приёмка:

- STOP срабатывает при зависшем planner и недоступной сети.
- Уже отправленный неизвестный эффект не помечается как отменённый без сверки.

Следующий опыт: Остановить каждый тип job при искусственно зависшем worker.

Метрика: Stop acknowledgment latency; новые эффекты после stop; корректность итоговых статусов.

Условие возвращения/начала: Полную отмену необратимых внешних действий не обещать.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-36`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`

## ACT-035 · P4 · Выбор API, CLI, UIA, DOM и визуального маршрута

Проблема: Универсальный кликер может использовать нестабильный путь при наличии точного API.

Поведение: Для capability регистрировать реальные доступные маршруты; выбирать по контракту и evidence, сначала структурированные интерфейсы, визуальный fallback только с наблюдаемым outcome.

Зависимости: ACT-002, ACT-003, ACT-012.

Приёмка:

- Отсутствие API не превращает автоматически произвольный GUI клик в разрешённый.
- Маршрут имеет preconditions, resource footprint и отдельный qualification status.

Следующий опыт: Одно безопасное действие выполнить через два подготовительных маршрута и сравнить verified результат.

Метрика: Task success по route; drift sensitivity; false action; latency.

Условие возвращения/начала: Vision-first universal desktop оставлять позже, пока узкие адаптеры не квалифицированы.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/ALL_TRACKS_INDEX.json` · `RND-05`

## ACT-037 · P4 · Browser adapter как опциональная возможность

Проблема: Зависимость библиотеки от Chrome противоречит desktop-first направлению.

Поведение: Браузер подключать только для конкретного источника/действия с session/account binding; наблюдение и подготовка могут идти параллельно, submit координируется по backend target.

Зависимости: ACT-003, ACT-012, ACT-035.

Приёмка:

- Desktop import/export работает без extension.
- Два browser contexts одного аккаунта не выполняют одну форму дважды.

Следующий опыт: Проверить один браузерный read workflow и один rehearsal submit без реальной публикации.

Метрика: Session binding errors; duplicate submit; capture coverage.

Условие возвращения/начала: Каждый сайт требует своей проверенной семантики; универсальный доступ не предполагать.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/ALL_TRACKS_INDEX.json` · `RND-07`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`

## ACT-038 · P4 · Терминал и VS Code через типизированные adapters

Проблема: Свободная строка shell из transcript не даёт контролируемого действия.

Поведение: Предоставлять зарегистрированные argv templates, working directory и tool версии; навигацию в VS Code привязывать к path/symbol; stdout и exit status возвращать как evidence.

Зависимости: ACT-002, ACT-003, ACT-012, ACT-035.

Приёмка:

- Инъекция shell metacharacters в имя проекта не создаёт второй команды.
- Command receipt включает точный cwd, argv, input revision и exit status.

Следующий опыт: Сделать open-file и одну безопасную зарегистрированную проверку в fixture repo.

Метрика: Argument validation failures; navigation accuracy; reproduction rate.

Условие возвращения/начала: Неизвестная команда остаётся proposal до добавления adapter, а не run-any-shell.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/02_STRATEGY/NEXT_DEVELOPMENT_NOW_LATER_RU.txt`

## ACT-039 · P4 · Canary и карантин при дрейфе интерфейса

Проблема: Успешный ранее маршрут ломается после обновления сайта или CLI.

Поведение: Хранить fingerprint схемы/locator/tool версии; дешёвый probe проверяет contract, broken route уходит в quarantine до переоценки.

Зависимости: ACT-002, ACT-012, ACT-035.

Приёмка:

- Переименованный CLI flag отключает соответствующий route до действия.
- Успех старого canary не переиспользуется для другой версии приложения.

Следующий опыт: Изменить API field, UIA name и CLI flag в controlled fixtures.

Метрика: Drift detection recall; false quarantine; время восстановления.

Условие возвращения/начала: Canary не заменяет полную проверку outcome, особенно для необратимого шага.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-32`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-41.md` · `RND-41`

## ACT-040 · P4 · Локальное перепланирование остатка workflow

Проблема: Любая ошибка заставляет повторять все шаги или продолжать по устаревшему плану.

Поведение: После каждого наблюдаемого checkpoint сравнивать delta; сохранять verified prefix и строить минимальный recovery suffix с теми же scopes.

Зависимости: ACT-011, ACT-012, ACT-024, ACT-039.

Приёмка:

- Переименование окна не повторяет уже сохранённый артефакт.
- Изменение обязательной предпосылки создаёт BLOCKED/NEEDS_CONTEXT, не скрытое продолжение.

Следующий опыт: В середине fixture workflow изменить состояние одного зависимого ресурса.

Метрика: Повторные шаги; repair success; сохранённый verified prefix.

Условие возвращения/начала: Planner не расширяет права при ремонте маршрута.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-33`

## ACT-044 · P4 · Память неудачных попыток с условиями применимости

Проблема: Новый чат повторяет ранее неработающий путь или навсегда блокирует уже исправленный.

Поведение: Failure capsule хранит inputs, fingerprint, error, уже проверенные alternatives, negative evidence и условие expiry; обновление среды возвращает candidate на проверку.

Зависимости: ACT-012, ACT-024, ACT-039.

Приёмка:

- Известный тот же failure не вызывает бессмысленную полную повторную попытку.
- Новая версия инструмента не блокируется вечным отрицательным правилом.

Следующий опыт: Повторить один failure, затем исправить fixture version и проверить requalification.

Метрика: Avoided repeats; stale negative blocks; recovery after version change.

Условие возвращения/начала: Не обобщать отсутствие успеха одного примера до невозможности всего класса действий.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-37.md` · `RND-37`

## ACT-051 · P4 · Read-first tool gateway к библиотеке и jobs

Проблема: Подключение AI API иногда понимается как автоматический доступ ко всему ПК.

Поведение: Предоставить typed search, read_span, snapshot_status, jobs.propose, jobs.status и reports.create_request; сервер независимо валидирует входы, scopes и budgets.

Зависимости: ACT-002, ACT-003, ACT-005, ACT-010.

Приёмка:

- Неверные source revision и path traversal отвергаются server-side.
- Tool proposal не выполняет произвольный shell и не читает keyring.

Следующий опыт: Подключить один тестовый caller к read-only gateway и прогнать bad inputs.

Метрика: Contract conformance; unauthorized tool calls; useful task completion.

Условие возвращения/начала: Поддержку MCP/Tasks/Skills конкретного клиента и API проверять интеграционным тестом, не названием протокола.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`

## ACT-054 · P4 · Полный журнал trust-version решений

Проблема: После обновления политики невозможно понять, почему старое действие разрешили.

Поведение: Сохранять intent, source refs, policy version, grants, verifier version, outcome и ограничения в append-only receipt chain, с отдельными correction events.

Зависимости: ACT-003, ACT-011, ACT-012, ACT-015.

Приёмка:

- Исторический permit можно воспроизвести по его версии политики.
- Редактирование display summary не меняет оригинальный audit event.

Следующий опыт: Выполнить fixture job, сменить policy и сравнить old/new decisions.

Метрика: Audit replay completeness; unexplained decisions; altered source events.

Условие возвращения/начала: Audit не должен записывать секреты; retention настраивается отдельно.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-35`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/05_SCHEMAS/ActionSpec.schema.json`

## ACT-057 · P4 · Панель продолжения после сбоя

Проблема: Технический журнал не помогает пользователю понять, что безопасно продолжить.

Поведение: Новое предложение: показывать для каждого незавершённого goal последний verified checkpoint, unknown effects, изменившиеся inputs и один предлагаемый следующий шаг с источниками.

Зависимости: ACT-023, ACT-024, ACT-025, ACT-044.

Приёмка:

- Панель отличает «повторить чтение» от «сначала сверить внешний результат».
- Нажатие Resume сохраняет operation identity и повторно проверяет актуальность.

Следующий опыт: Дать пользователю три synthetic failure capsules и измерить восстановление без чтения raw logs.

Метрика: Recovery decision time; wrong retry attempts; resumed task success.

Условие возвращения/начала: Не предлагать одну кнопку retry для всех типов ошибок.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/02_NEXT_IMPLEMENTATION_RU.md`

## RND-009 · P4 · Каталог действительных qualification-команд

Проблема: Список Python функций или JSON workflow не равен установленной доступной команде.

Поведение: Верифицировать registry по actual CLI/help/schema/profile и owner; Laya adapter допускать после проверки его реального формата.

Зависимости: RND-001, RND-008.

Приёмка:

- Неизвестная команда остаётся candidate и не запускается.
- Пример JSON не помечается native Laya import без проверки.

Следующий опыт: Сопоставить десять source candidates и реально найденные CLI entrypoints.

Метрика: Доля candidate commands с подтверждённым контрактом и environment binding.

Условие возвращения/начала: До доступа к установленному профилю показывать только проектную схему.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-041`
- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-10`

## RND-010 · P4 · Desktop bridge к существующему qualification owner

Проблема: Новый универсальный runner может создать второй несовместимый verdict.

Поведение: Делегировать установленному owner и импортировать его domain receipt; artifact audit не выдавать за запуск market campaign.

Зависимости: RND-008, RND-009.

Приёмка:

- Exit code=0 и domain BLOCKED отображаются раздельно.
- campaign_executed=false не становится PAPER_OBSERVED.

Следующий опыт: Пройти один положительный и один отрицательный локальный qualification-сценарий.

Метрика: Agreement adapter/domain verdict; число false success.

Условие возвращения/начала: После точного command contract и установленной среды.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-036`
- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-12`

## RND-039 · P4 · Budget admission и цена проверенной полезной задачи

Проблема: Наличие API key не задаёт бюджет, а токены/повторы скрывают реальную цену результата.

Поведение: Отдельно учитывать token/API/RPC/compute расходы, reserved output, retries и abandoned work; показывать estimate и actual per verified outcome.

Зависимости: RND-011.

Приёмка:

- Параллельные jobs не резервируют один и тот же остаток бюджета дважды.
- Ошибка/отмена не теряет уже понесённый расход.
- Неизвестный тариф остаётся UNKNOWN.

Следующий опыт: Fixture campaign с двумя конкурирующими запросами и частично выполненным job.

Метрика: Actual cost per verified task и budget overrun.

Условие возвращения/начала: Тарифы и доступные квоты уточнять при интеграции, не переносить из старых чатов.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-047`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `VOICE_V3::LEGACY-F105`

## ACT-007 · P5 · Laya как сменный advisory adapter

Проблема: Пакеты смешивают классификатор Laya, workflow IR и исполняющую среду.

Поведение: Определить neutral routing interface; сравнить Laya-кандидат с rules и другими adapters, сохраняя prediction как рекомендацию без прав на выполнение. Совместимость проверять экспериментом.

Зависимости: ACT-001, ACT-002, ACT-006.

Приёмка:

- Нет утверждения о нативном импорте наших workflow JSON в Laya.
- Смена router не меняет policy, operation identity и обязательные проверки.

Следующий опыт: На одном RU/EN code-switch corpus измерить routing quality локально после проверки реального интерфейса выбранного инструмента.

Метрика: False confident routing; стоимость; latency; доля abstain.

Условие возвращения/начала: Не делать Laya обязательной зависимостью, пока измеримое преимущество не показано.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/02_NEXT_IMPLEMENTATION_RU.md`

## ACT-013 · P5 · Независимость доказательств и маршрутов

Проблема: Несколько оболочек одного теста ошибочно считаются независимыми подтверждениями.

Поведение: Сохранять lineage источников, toolchain, model, fixture и shared dependencies; оценивать co-failure, а не количество голосов.

Зависимости: ACT-012.

Приёмка:

- Три пересказа одного README образуют одну evidence family.
- Разные обёртки одного pytest не повышают independent-evidence count.

Следующий опыт: Всем маршрутам дать общий неверный snapshot и добавить независимый инвариант.

Метрика: Joint failure; marginal recovery каждого маршрута; false consensus.

Условие возвращения/начала: Не публиковать проценты надёжности из предположения независимости.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-24`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-19.md` · `RND-19`

## ACT-016 · P5 · Граф конфликтов общих ресурсов

Проблема: Глобальный single-writer тормозит независимую работу, а отсутствие scopes создаёт гонки.

Поведение: Декларировать read/write footprint: файл, branch/head, UI focus, clipboard, port, аккаунт; сериализовать конфликтующие эффекты и разрешать независимые.

Зависимости: ACT-002, ACT-015.

Приёмка:

- Два job на одной вкладке ждут lease, два независимых append-only producers работают параллельно.
- Windows aliases, case и junction не создают два владельца одного ресурса.

Следующий опыт: Запустить API collector, индексатор и два GUI job; проверить конфликт только GUI.

Метрика: Resource collisions; параллельные независимые задачи; очередь конфликтов.

Условие возвращения/начала: Топология resources уточняется на настоящих adapters, не только в JSON.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-20`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/00_START/00_PARALLEL_CAPTURE_DECISION_RU.md`

## ACT-017 · P5 · Общая подготовка immutable данных

Проблема: Несколько задач заново строят одинаковый индекс и расходуют память.

Поведение: Coalesce одинаковые read preparations по snapshot, parser/version и scope; выдавать immutable результат подписчикам с отдельной отменой.

Зависимости: ACT-011, ACT-016.

Приёмка:

- Пять подписчиков инициируют одну подготовку.
- Отмена одного подписчика не лишает остальных результата.

Следующий опыт: Пять simultaneous goals запрашивают один repo graph; отменить один.

Метрика: Повторные rebuild; cache hit; retained memory; latency подписчиков.

Условие возвращения/начала: Разные права или snapshots никогда не объединяются одним key.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-31`

## ACT-018 · P5 · Отложенный резерв вместо постоянного fan-out

Проблема: Постоянный запуск нескольких дорогих путей может ухудшать итоговую задержку.

Поведение: Подключать backup для разрешённой read/preparation работы по измеренному slow-tail или ошибке; выбирать первый прошедший обязательные проверки результат.

Зависимости: ACT-012, ACT-013, ACT-016.

Приёмка:

- Самый быстрый неверный кандидат проигрывает более медленному валидному.
- Backup не отправляет дублирующий внешний submit.

Следующий опыт: Сравнить serial, eager и delayed hedge на одинаковом corpus и бюджете.

Метрика: p95 time-to-verified; total attempt cost; recovery; wasted work.

Условие возвращения/начала: Включать по классам задач после измерений, не назначать универсальный порог.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-19`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-20.md` · `RND-20`

## ACT-019 · P5 · Явная семантика объединения параллельных ветвей

Проблема: Режим first-result теряет обязательные части полного сбора.

Поведение: Выбирать COMPLEMENTARY_UNION, REQUIRED_EVIDENCE_JOIN, FIRST_VERIFIED, PARTITIONED_MAP или PREPARE_COMMIT с собственным условием завершения.

Зависимости: ACT-012, ACT-016.

Приёмка:

- UNION сохраняет late observations до завершения объявленного scope.
- REQUIRED_EVIDENCE_JOIN не закрывается первым удачным checker.

Следующий опыт: На одном workflow сделать обязательный поздний результат и проверить разные join modes.

Метрика: Потерянные обязательные ветви; корректность coverage; время завершения.

Условие возвращения/начала: Не переиспользовать FIRST_VERIFIED для полного экспорта или суммы partitions.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/00_START/00_PARALLEL_CAPTURE_DECISION_RU.md`

## ACT-020 · P5 · Многопоточная запись observations

Проблема: Ранние документы запрещали всю параллельную запись, хотя пользователь уточнил необходимость одновременного capture.

Поведение: Микрофон, DOM, Git, terminal и accessibility collectors append-only пишут в свои namespace с sequence, timestamp и source revision; views объединяются отдельно.

Зависимости: ACT-016, ACT-019.

Приёмка:

- Одновременные producers сохраняют все sequences и provenance.
- Дедуп raw bytes сохраняет каждую исходную ссылку и версию.

Следующий опыт: Запустить три collectors с duplicate и out-of-order observations и остановить один.

Метрика: Capture gaps; late arrival lag; duplicate lineage retention.

Условие возвращения/начала: Реальные connectors подключать по одному после проверки доступа и coverage.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/00_START/00_PARALLEL_CAPTURE_DECISION_RU.md`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/01_YOUR_WORDS/VOICE-USER-EXCERPT-01.txt`

## ACT-021 · P5 · Один commit на конкретный effect target

Проблема: Несколько правильных кандидатов могут дважды изменить один внешний объект.

Поведение: Scoped commit broker выбирает проверенного кандидата и владеет конкретной операцией/target; независимые targets сохраняют параллельность.

Зависимости: ACT-011, ACT-012, ACT-015, ACT-016.

Приёмка:

- Два concurrent commit для одного ID создают один локальный эффект.
- Два разных разрешённых targets не блокируются глобальным mutex.

Следующий опыт: Гонка двух кандидатов вокруг одной локальной записи и двух независимых файлов.

Метрика: Duplicate mutations; throughput независимых targets; lease conflicts.

Условие возвращения/начала: Для удалённого сервиса граница гарантий описывается отдельно.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-23`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/00_START/00_PARALLEL_CAPTURE_DECISION_RU.md`

## ACT-027 · P5 · Планировщик ресурсов Dell и foreground приоритет

Проблема: Одновременные ASR, индексатор и тесты конкурируют за ограниченные CPU/RAM.

Поведение: Ограничивать тяжёлые jobs и provider budget, приоритет отдавать audio/UI; лёгкое I/O допускается параллельно, backpressure явно виден.

Зависимости: ACT-016, ACT-025, ACT-026.

Приёмка:

- При давлении памяти background jobs замедляются без потери очереди.
- Одновременные задачи не обходят общий бюджет попыток.

Следующий опыт: Сравнить 1/2/4 workers при Chrome, ASR и импорте на Dell после подключения runtime.

Метрика: Peak RAM; voice p95; jobs/hour; стоимость; throttled time.

Условие возвращения/начала: Выбор числа workers основывать на измерениях, не путать с лимитом документов.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-40`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-32.md` · `RND-32`

## ACT-028 · P5 · Push-to-talk и единый capture stream

Проблема: Голосовой ввод привязан к браузеру или запускает несколько конкурирующих устройств capture.

Поведение: Desktop hotkey/доступная кнопка управляют одним аудиопотоком с индикатором; ASR/VAD и архиватор читают разрешённые ветви этого потока.

Зависимости: ACT-001, ACT-020, ACT-025.

Приёмка:

- Голосовой ввод доступен без обязательной Chrome extension.
- Индикатор, stop и отмена работают при недоступной модели.

Следующий опыт: Провести одно voice-to-handoff действие на Windows, включая остановку записи.

Метрика: Capture activation errors; dropped frames; end-to-end latency.

Условие возвращения/начала: Ambient always-on режим оставить отдельным последующим исследованием.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/02_NEXT_IMPLEMENTATION_RU.md`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/00_START/00_PARALLEL_CAPTURE_DECISION_RU.md`

## ACT-029 · P5 · Сменный ASR и корпус RU/EN/code-switch

Проблема: Название модели и общий WER не показывают пригодность на Dell и кодовых именах.

Поведение: ASR adapter возвращает transcript, alternatives, timestamps и uncertainty; сравнивать кандидатов на разрешённых пользовательских примерах и воспроизводимом корпусе.

Зависимости: ACT-028, ACT-026.

Приёмка:

- Оригинальный transcript хранится отдельно от исправленного.
- Cloud audio route включается только для разрешённого scope; отказ сети не включает его скрыто.

Следующий опыт: Сравнить минимум два реальных кандидата или один кандидат и baseline на одном corpus.

Метрика: WER; critical-slot error; endpointing latency; RAM; real-time factor.

Условие возвращения/начала: Не фиксировать победителя или актуальную поддержку модели без отдельной проверки.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/02_NEXT_IMPLEMENTATION_RU.md`

## ACT-030 · P5 · Арбитраж критических голосовых слотов

Проблема: Ошибки в отрицании, имени repo, сумме и режиме важнее обычной опечатки.

Поведение: Выделять критические слоты, разрешать aliases через библиотеку, показывать адресное исправление; неизвестные значения не домысливать.

Зависимости: ACT-001, ACT-029.

Приёмка:

- «Не merge», «main/branch» и «dry-run/live» сохраняют правильное различие.
- Фоновое «да» не подтверждает публикацию или финансовое действие.

Следующий опыт: Корпус minimal pairs с отрицаниями, близкими именами и фоновыми голосами.

Метрика: Critical-slot error; false activation; количество уточнений на задачу.

Условие возвращения/начала: До приемлемой точности потенциально критические слоты требуют явного review.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-29.md` · `RND-29`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`

## ACT-031 · P5 · Исправление intent и отзыв старой revision

Проблема: Фраза «запусти… нет, только подготовь» может породить две задачи.

Поведение: Хранить partial/final/correction как revisions одной логической команды; позднее уточнение отзывает права старого intent; partial допускает только подготовительное чтение.

Зависимости: ACT-001, ACT-011, ACT-025, ACT-030.

Приёмка:

- Старая revision после correction не проходит commit fence.
- Смена project не смешивает контекст двух задач.

Следующий опыт: Подать позднее отрицание во время подготовки action.

Метрика: Stale-intent commits; correction latency; потерянные revisions.

Условие возвращения/начала: Speculative действия разрешать только в пределах обратимой read preparation.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-36`

## ACT-033 · P5 · Доступность без обязательной речи и мыши

Проблема: Только voice UI исключает людей с трудностями речи и утомляет пользователя.

Поведение: Один intent API поддерживает текст, клавиатуру, screen-reader и доступные controls; озвучивание статуса по запросу, focus/error доступен программно.

Зависимости: ACT-001, ACT-028, ACT-031, ACT-032.

Приёмка:

- Основной import→goal→handoff поток проходит без мыши.
- Labels, errors, focus и cancel доступны screen-reader без focus trap.

Следующий опыт: Проверить полный сценарий на Windows с клавиатурой и выбранным screen-reader.

Метрика: Task completion по способу ввода; focus traps; error recovery steps.

Условие возвращения/начала: Не объявлять доступность для всех пользователей по одному скриншоту или тесту.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/01_CONTEXT/VISIBLE_USER_INPUT_ANCHORS_RU.md`

## ACT-034 · P5 · Жизненный цикл микрофона и хранения аудио

Проблема: Sleep/resume, смена микрофона и ошибка audio могут скрыто потерять запись.

Поведение: Показывать состояния устройства и сохранения; раздельно задавать recording, retention и cloud transcription scopes; после сбоя объяснять, какой сегмент сохранён.

Зависимости: ACT-028, ACT-029, ACT-033.

Приёмка:

- Смена микрофона не создаёт ложное подтверждение команды.
- После sleep/resume виден захваченный и отсутствующий диапазон.

Следующий опыт: Сменить устройство, усыпить ПК и отключить аудио во время записи.

Метрика: Lost audio interval; recovery time; неверные статусы capture.

Условие возвращения/начала: Политику долгого хранения и ambient capture задавать отдельно от обычного push-to-talk.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`

## ACT-036 · P5 · Владение focus и уступка пользователю

Проблема: Агент может печатать в чужое окно после движения мыши пользователем.

Поведение: Lease на interactive desktop связывать с окном/контролом; обнаруживать foreground user activity и приостанавливать automation до безопасного продолжения.

Зависимости: ACT-016, ACT-032, ACT-035.

Приёмка:

- Ручное переключение окна блокирует ввод в старый target.
- Clipboard сохраняется/восстанавливается по контракту и не переписывается другим job.

Следующий опыт: Во время rehearsal переключить окно и вручную изменить clipboard.

Метрика: Wrong-window inputs; user-interruption recovery; lease violations.

Условие возвращения/начала: Shared mouse/keyboard нельзя запускать параллельно без scoped coordination.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-20`

## ACT-055 · P5 · Предварительная смета полной попытки

Проблема: Цена показывается только для победителя, скрывая retries и parallel losers.

Поведение: Оценивать ожидаемые CPU/time/API затраты всех ветвей до запуска и фактические после; budget guard влияет на число routes и размер допустимого контекста.

Зависимости: ACT-018, ACT-026, ACT-027.

Приёмка:

- Backup и отменённые обращения входят в итоговую стоимость.
- Бюджет не приводит к молчаливому удалению исходников или ложному DONE.

Следующий опыт: Сравнить predicted и actual cost на serial и hedged corpus.

Метрика: Estimate error; over-budget jobs; cost per verified outcome.

Условие возвращения/начала: Цены provider брать из проверенной на момент внедрения конфигурации, не из старых ZIP.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/01_MASTER_GOALS_AND_ARCHITECTURE_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-40`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/10_OPENAI_AND_AUTOMATION_CONTRACTS_RU.md`

## ACT-058 · P5 · Защита от собственного TTS и фоновой речи

Проблема: Озвученный агентом текст или сторонний голос может распознаться как новая команда.

Поведение: Разделить playback/capture states, ограничить command activation явным вводом, сохранять причину rejection и позволять немедленную ручную отмену.

Зависимости: ACT-029, ACT-030, ACT-032, ACT-034.

Приёмка:

- TTS, произносящий текст с командой, не создаёт effect intent.
- Шум/фон не подтверждает критический слот; пользователь может исправить его текстом.

Следующий опыт: Проиграть агентский TTS и фоновые minimal pairs одновременно с capture fixture.

Метрика: Self-trigger rate; background false activation; blocked valid speech.

Условие возвращения/начала: При включении ambient режима потребуется отдельный более широкий corpus и разрешение capture.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`

## ACT-049 · P6 · Durable расписания на ПК с catch-up политикой

Проблема: Цель 24/7 не определяет поведение после сна ноутбука и пропущенных запусков.

Поведение: Для будущего расписания хранить timezone, next_run, missed-run policy, concurrency key и budget; повтор события использует durable operation identity.

Зависимости: ACT-024, ACT-025, RND-039.

Приёмка:

- Sleep/resume не запускает бесконтрольно все пропущенные тяжёлые jobs.
- Два события одного occurrence не создают две операции.

Следующий опыт: На fake clock смоделировать сон, переход даты и restart; реальное расписание создавать только отдельной командой.

Метрика: Duplicate occurrences; scheduling lag; bounded catch-up.

Условие возвращения/начала: В этом архиве расписания только специфицируются; 24/7 выполнение требует реально работающего host.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/ALL_TRACKS_INDEX.json` · `RND-12`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/02_STRATEGY/NEXT_DEVELOPMENT_NOW_LATER_RU.txt`

## ACT-053 · P6 · Общий корпус отказов и квалификация на Windows

Проблема: Offline Linux prototype tests выдаются за проверку всего desktop продукта.

Поведение: Сохранять корпус intent errors, stale state, dups, unknown effects, user interruption, audio и interface drift; receipts группировать по OS/runtime/adapter и held-out split. Base qualification covers text/jobs without requiring speech; audio and route-diversity suites apply only to installed optional adapters.

Зависимости: ACT-012, ACT-026, ACT-032, LIB-048.

Приёмка:

- Linux algorithm tests и Windows real-device результаты показаны раздельно.
- Success rate всегда связан с corpus, sample size, environment и критериями.

Следующий опыт: Начать с 20 Windows операторских команд и fault scenarios; размер corpus не является лимитом приложения.

Метрика: Task success; false accept; coverage matrix; platform-specific failures.

Условие возвращения/начала: Новые adapters не наследуют qualification другого инструмента автоматически.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-42`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`

## RND-012 · P6 · Детерминированный replay рыночных наблюдений

Проблема: Нельзя сравнивать стратегии на разных незафиксированных входах.

Поведение: Фиксировать dataset digest, order, seed, clock, chain anchor и config; записывать decisions и объяснённую nondeterminism.

Зависимости: RND-011.

Приёмка:

- Повтор одного replay даёт одинаковые decision/artifact digests либо явно описанное отличие.
- Replay никогда не маркируется как текущее market observation.

Следующий опыт: Два запуска одной версии и один запуск изменённой версии на одинаковом сохранённом потоке.

Метрика: Replay reproducibility и explained divergence rate.

Условие возвращения/начала: Нужен набор сохранённых рыночных данных или явно синтетическая fixture.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F21`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E01`

## RND-013 · P6 · Flashloan repayment и boundary/fuzz corpus

Проблема: Округления, комиссии и границы размера могут нарушить возврат займа.

Поведение: Сохранять lender-neutral контракт principal/fee/repay в atomic units и adapter-specific cases; минимизировать failing seed.

Зависимости: RND-008, RND-011, RND-012.

Приёмка:

- Проверены zero/min/max/rounding и недостающий repayment.
- Неавторизованный callback или неверная сеть не проходит fixture.

Следующий опыт: Один adapter на pinned local validator/fork; реальная поддержка adapter сначала устанавливается по коду.

Метрика: Количество полезных boundary cases; минимальные воспроизводимые отказы.

Условие возвращения/начала: После выбранного protocol adapter; реальные транзакции не следуют из этой карточки.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F18`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F28`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E04`

## RND-014 · P6 · Непустая stateful invariant campaign

Проблема: Зелёный invariant-тест может не вызвать полезных операций из-за постоянных revert.

Поведение: Измерять handler calls, depth, covered transitions, reason distribution и сохранённый corpus.

Зависимости: RND-012, RND-013.

Приёмка:

- Нулевые полезные calls дают INVALID_CAMPAIGN.
- Найденный failing seed воспроизводится отдельно.

Следующий опыт: Включить заведомо vacuous handler и сравнить с рабочим state machine.

Метрика: Полезные transitions и воспроизводимость нарушений.

Условие возвращения/начала: Не расширять число trials до проверки непустого покрытия.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F19`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E05`

## RND-015 · P6 · Общий брокер рыночных данных для исследователей

Проблема: Каждый worker отдельно запрашивает одинаковые данные и расходует квоты.

Поведение: Один versioned acquisition broker сохраняет immutable observations и выдаёт ссылки независимым strategy workers.

Зависимости: RND-011.

Приёмка:

- Четыре подписчика одного snapshot используют один сохранённый объект.
- Запросы, source IDs, ошибки и пробелы отражены в журнале.

Следующий опыт: Сравнить 1/2/4 replay workers с общим cache и независимым fetch.

Метрика: Duplicate fetch ratio, CPU/RAM и requests per useful observation.

Условие возвращения/начала: Реальный fetch только после выбора доступного провайдера и его лимитов.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `OCC_RND::source.shared_pit_feed`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-029`

## RND-016 · P6 · Point-in-time согласованность и инвалидирование anchors

Проблема: Смешивание разных моментов рынка создаёт искусственный edge.

Поведение: Привязывать признаки к observed/available time, chain/slot/commitment и revision; смена canonical anchor инвалидирует зависимые результаты.

Зависимости: RND-012, RND-015.

Приёмка:

- Будущее значение недоступно replay decision до своего available time.
- Замена anchor делает старый verdict stale.

Следующий опыт: Подмешать задержанный и будущий snapshot в один route.

Метрика: Point-in-time violations и false edges из-за смешения времени.

Условие возвращения/начала: До покрытия timestamp semantics внешнего API данные остаются time-uncertain.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-037`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E07`

## RND-017 · P6 · Сравнение независимых provider views

Проблема: Две разные торговые марки могут зависеть от одного upstream.

Поведение: Хранить lineage провайдера и сопоставлять state на совместимом anchor; disagreement даёт UNKNOWN и отдельный incident.

Зависимости: RND-015, RND-016.

Приёмка:

- Несовместимые anchors не сравниваются как равные.
- Общий upstream отмечен, независимость не выводится из имени.

Следующий опыт: Fixture common-upstream outage и один независимый источник.

Метрика: Disagreement rate, common-failure correlation и marginal recovery.

Условие возвращения/начала: Дополнительного провайдера подключать после измерения полезности и стоимости.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F23`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E06`

## RND-018 · P6 · Freshness, completeness и backpressure рыночного потока

Проблема: Устаревшая quote либо пропущенный интервал может выглядеть как доступная возможность.

Поведение: Применять версионированные freshness budgets, cursors, explicit gaps, bounded retry и backpressure.

Зависимости: RND-015, RND-016.

Приёмка:

- Stale quote отклоняется на границе настроенного бюджета.
- 429/disconnect не теряет cursor и не создаёт бесконечный retry.

Следующий опыт: Ввести задержку, 429 и потерю сети в сохранённую capture session.

Метрика: Gap duration, stale acceptance count, recovery latency.

Условие возвращения/начала: Freshness thresholds выбирать из измеренной стратегии, не задавать произвольной общей константой.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F24`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E02`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E09`

## RND-019 · P6 · Полная экономика opportunity в совместимых единицах

Проблема: Gross quote spread не учитывает расходы и может оказаться отрицательным net edge.

Поведение: Пересчитывать DEX/borrow/priority/tip/failure costs, slippage и fee conversion в integer units с версией assumptions.

Зависимости: RND-013, RND-016, RND-018.

Приёмка:

- Перестановка decimals выявляет unit mismatch.
- Увеличение каждого cost не повышает net edge.
- Неизвестная обязательная комиссия блокирует экономический PASS.

Следующий опыт: Независимый пересчёт десяти fixture routes с fee/decimal sweeps.

Метрика: Accounting error и доля false-positive net edges.

Условие возвращения/начала: Реальные fee schedules получать заново перед будущей campaign.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F25`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-038`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E03`

## RND-020 · P6 · Модель liquidity, slippage и задержек исполнения

Проблема: Quote для малого объёма и мгновенного времени не подтверждает исполнение нужного размера.

Поведение: Строить size/latency sensitivity curves по snapshots, хранить assumptions и неблагоприятные сценарии.

Зависимости: RND-016, RND-019.

Приёмка:

- Sweep размера выявляет liquidity boundary.
- Задержка данных не исчезает из отчёта.
- Modeled fill остаётся modeled.

Следующий опыт: Матрица трёх размеров и трёх задержек на одинаковых historical routes.

Метрика: Доля net edge, сохранившаяся при adversarial timing, и model uncertainty.

Условие возвращения/начала: Без глубины/состояния пула выводить недостаточность данных.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F27`

## RND-021 · P6 · Проверка атомарной границы маршрута

Проблема: Идея стратегии может требовать операции вне доступной атомарной транзакции.

Поведение: Составлять contract route: chain, supported instructions, borrow/repay, writable accounts, resource constraints и settlement timing.

Зависимости: RND-013, RND-019, RND-020.

Приёмка:

- Внешняя delayed settlement стадия отмечается non-atomic.
- Отсутствующий adapter или instruction остаётся UNSUPPORTED.

Следующий опыт: Проверить один circular route и один намеренно non-atomic route на pinned fixture.

Метрика: Доля маршрутов с полностью описанными atomic dependencies.

Условие возвращения/начала: Сначала подтвердить поддержку конкретного lender и venue в текущем коде.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F26`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/10_PARALLEL_WEB3_RND_RU.txt`

## RND-022 · P6 · Настоящая paper/shadow campaign с честными labels

Проблема: Синтетический test PASS и реальное наблюдение рынка дают разные доказательства.

Поведение: Записывать observed interval, gaps, provider lineage, quotes, hypothetical fills, assumptions и failure costs; realised PnL хранить отдельно только при реальных подтверждённых fills.

Зависимости: RND-010, RND-011, RND-015, RND-018, RND-019, RND-020, RND-021.

Приёмка:

- Fixture не закрывает real-observation gate.
- Отчёт содержит фактическую длительность и все gaps.
- Гипотетический PnL не помечен реализованным.

Следующий опыт: Ограниченная observation campaign после проверки адаптера; длительность выбрать по необходимому покрытию режимов.

Метрика: Coverage regimes, modeled net distribution и доля качественных наблюдений.

Условие возвращения/начала: Нет данных о реальном profitability; длительность 24h сама по себе ничего не доказывает.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-13`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F29`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-042`

## RND-023 · P6 · Fault/stop/recovery qualification на Dell

Проблема: Сон Windows, загрузка CPU или неизвестный outcome может ломать unattended кампанию.

Поведение: Проверять process tree stop, heartbeat, checkpoints, sleep/restart и effect-specific reconciliation; сохранить независимый от ASR STOP.

Зависимости: RND-010, RND-018, RND-022.

Приёмка:

- После STOP нет новых запрещённых dispatch.
- Неизвестный effect не повторяется вслепую после restart.
- Измерения сняты на целевом устройстве.

Следующий опыт: Отмена под indexing/ASR load, отключение сети и restart в трёх контрольных точках.

Метрика: p95/p99 stop latency, recovery success и duplicate effect count.

Условие возвращения/начала: Без реального устройства результаты остаются device-unverified.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F30`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::W3-F31`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `SCE_WEB3::W3-E10`

## RND-024 · P6 · Расписание R&D и campaign DAG с checkpoint

Проблема: План JSON без установленного scheduler не выполняет ежедневную работу.

Поведение: Расширять существующего queue owner: dependencies, deadline, quota, per-resource lease, checkpoint, overlap policy и typed result join.

Зависимости: RND-009, RND-011, RND-023.

Приёмка:

- Неуспешный required node блокирует dependent node.
- Два ticks одной schedule не дублируют run.
- Прерванный job сохраняет точку продолжения.

Следующий опыт: Смоделировать двое суток virtual time с missed tick, restart и overlapping job.

Метрика: Выполненные полезные jobs/сутки, skipped reasons и recovery latency.

Условие возвращения/начала: Расписание устанавливается отдельной конкретной настройкой; ZIP его не включает.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-11`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_WORKFLOW_CATALOG.json` · `SCE_V2::W3-WF27`

## RND-027 · P6 · Единая identity opportunity и защита от двойного учёта

Проблема: Одинаковая рыночная возможность может учитываться как прибыль многих стратегий.

Поведение: Выдавать candidate identity из route/assets/state, хранить producer lineage и объединять совместимые observations без потери версий.

Зависимости: RND-015, RND-016.

Приёмка:

- Два workers одного route/state дают одну economic opportunity с двумя origins.
- Новый state создаёт новую версию, а не стирает старую.

Следующий опыт: Обработать три перекрывающихся detector outputs.

Метрика: Duplicate candidate rate и ошибка attribution.

Условие возвращения/начала: Ключ identity настраивать по фактической protocol semantics.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-031`

## RND-028 · P6 · Реестр гипотез и всех испытаний стратегии

Проблема: При множестве экспериментов сохраняются победители и теряется история отбора.

Поведение: До запуска фиксировать hypothesis, dataset, baseline, variation, criteria, cost и stop rule; сохранять все outcomes, включая отрицательные.

Зависимости: RND-011, RND-012.

Приёмка:

- Trial ID неизменяем и связан с точной версией config.
- Неудачный trial остаётся в сравнении.

Следующий опыт: Провести пять synthetic variations с одним случайным победителем.

Метрика: Доля trials с predeclared criteria и сохранённым negative result.

Условие возвращения/начала: Пороги определять до просмотра holdout.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `OCC_RND::research.register_trial`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-032`

## RND-029 · P6 · Time/venue holdout и защита от look-ahead

Проблема: Большой перебор стратегий легко отбирает случайный выигрыш или использует будущие данные.

Поведение: Разделять development/calibration/holdout по времени и источникам, учитывать overlapping windows и сохранять no-action baseline.

Зависимости: RND-016, RND-028.

Приёмка:

- Изменённый после просмотра holdout кандидат получает новый trial.
- Будущий PR/market label не попадает во вход decision.

Следующий опыт: Tune на одном фиксированном интервале и оценить один раз на отложенном интервале.

Метрика: Out-of-sample stability и leakage violations.

Условие возвращения/начала: Без достаточного независимого набора не объявлять устойчивость.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-040`

## RND-036 · P6 · Утверждение из новости → первоисточник → experiment

Проблема: Социальный пересказ технологии или стратегии может многократно цитировать один непроверенный источник.

Поведение: Хранить claim, attribution, source graph, дату, противоречия и воспроизведение; число перепечаток не считать независимым подтверждением.

Зависимости: RND-011, RND-028.

Приёмка:

- Три перепечатки одного сообщения дают один корневой источник.
- Непроверенное claim не становится supported feature.

Следующий опыт: Пять сохранённых публикаций с общими upstream источниками.

Метрика: Source diversity и доля claims с проверяемым primary evidence.

Условие возвращения/начала: Новый web scouting запускается отдельно; текущий пакет лишь развивает сохранённую стратегию.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::LVF23`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-026`

## RND-042 · P6 · Избирательная requalification при drift

Проблема: Изменение API, команды или adapter может сделать прежний PASS недействительным.

Поведение: Привязать receipts к environment/schema/dependency fingerprints; изменённый критический dependency ставит только затронутые проверки в очередь.

Зависимости: RND-003, RND-008, RND-011, RND-024.

Приёмка:

- Изменение adapter инвалидирует зависимые receipts.
- Правка несвязанного README не запускает полную campaign.

Следующий опыт: Изменить source schema и затем unrelated doc в fixture графе.

Метрика: Selective invalidation precision и unsafe reuse count.

Условие возвращения/начала: После provenance графа и проверенных receipt bindings.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-033`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `VOICE_V3::RND-41`

## RND-043 · P6 · Корпус контрпримеров и капсулы неудач

Проблема: Неудачи теряются и возвращаются как новые promising hypotheses.

Поведение: Сохранять минимальный dataset/seed/config/log/assumption capsule для stale quotes, fees, liquidity, provider disagreement и неверных кодовых попыток.

Зависимости: RND-011, RND-012, RND-028.

Приёмка:

- Counterexample воспроизводится на закреплённой версии.
- Negative corpus автоматически входит в оценку нового варианта.

Следующий опыт: Минимизировать один failing market fixture и один broken code handoff.

Метрика: Failure replay success и повторные ранее известные ошибки.

Условие возвращения/начала: Секретные значения исключать из share projection с явной записью о редактировании.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-012`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `ASSISTANT_V3::AI-RND-11`

## RND-044 · P6 · Автоматический следующий R&D документ из blocker

Проблема: После ошибки пользователь повторно собирает контекст для нового чата.

Поведение: Компилировать цель, точные sources, unsuccessful attempts, evidence, remaining gap, bounded patch/experiment и acceptance в переносимый документ.

Зависимости: RND-002, RND-011, RND-028, RND-043.

Приёмка:

- Чистый новый чат получает все required source refs или явные missing slots.
- Документ не помечает BLOCKED как DONE.

Следующий опыт: Передать один failure capsule в независимый новый контекст и проверить восстановление следующего шага.

Метрика: Continuation accuracy и повторные вопросы о потерянном контексте.

Условие возвращения/начала: Рекомендация следующего действия не означает автоматический запуск.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-034`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-037`

## LIB-040 · P7 · Read-only доступ AI к ranges библиотеки

Проблема: Пересылка архивов неудобна при повторных точечных вопросах.

Поведение: Scoped MCP/resource API отдаёт manifest, source versions и ranges; read contract не предоставляет shell и сохраняет audit read scope.

Зависимости: LIB-017, LIB-027, LIB-037.

Приёмка:

- Range response совпадает с source hash/version.
- Outside-scope request отвергается без раскрытия metadata.

Следующий опыт: Локальный prototype reader выполняет search→range→citation и invalid scope query.

Метрика: Exact source retrieval latency; unauthorized reads=0.

Условие возвращения/начала: Добавлять после работающего manual handoff и source scope controls.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-046`

## LIB-042 · P7 · Telegram export с правками и медиа

Проблема: Text dump теряет edits, reply links, voice files и отсутствующие attachments.

Поведение: Импортировать разрешённый export с chat/message IDs, replies, edit history и media inventory; live fetch — отдельный adapter с cursor/watermark.

Зависимости: LIB-012, LIB-016, LIB-041.

Приёмка:

- Reply chains и unavailable media видны в source graph.
- Повторный import с edit создаёт version, а не отдельную несвязанную копию.

Следующий опыт: Два экспорта одного synthetic чата с edited message и voice placeholder.

Метрика: Messages/edits/media coverage; duplicate versions=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-040`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## LIB-043 · P7 · RSS и веб-снимки с версией тела страницы

Проблема: URL и заголовок недостаточны, чтобы воспроизвести исследование или заметить изменившуюся страницу.

Поведение: Сохранять доступный body, URL, capture time, response status, hash и extraction version; deleted/blocked content отмечать, не восстанавливать по памяти.

Зависимости: LIB-006, LIB-016, LIB-023.

Приёмка:

- Изменение body создаёт новую source version.
- RSS duplicate link не удаляет отдельное происхождение.

Следующий опыт: Fixture feed и страницы с revisions, redirect и unavailable response.

Метрика: Freshness lag; reproducible cited body; unsupported content claims=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-040`
- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## LIB-045 · P7 · PDF/Office/OCR как ленивые извлечения

Проблема: Документы с таблицами или сканами остаются ORIGINAL_ONLY либо теряют структуру при plain text extraction.

Поведение: Lazy adapters сохраняют pages/cells/regions и parser fidelity; extraction отдельно от originals; OCR confidence не объявляет exactness.

Зависимости: LIB-007, LIB-016.

Приёмка:

- Таблица проверяется по эталону значений/ячеек.
- OCR error не меняет оригинал и отражается в metadata.

Следующий опыт: Набор PDF/DOCX/table/scan и ручной gold subset.

Метрика: Cell accuracy, page coverage, extraction time, unsupported inventory.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/FEATURE_BACKLOG.json` · `DESK-041`

## LIB-046 · P7 · Аудио и видео с временными ссылками

Проблема: Транскрипт без исходного медиа и таймкодов не позволяет проверить сказанное.

Поведение: Original media, ASR transcript, subtitle/OCR frames связать через source-time intervals; исправления создают derived version, missing media явно отмечается.

Зависимости: LIB-007, LIB-014, LIB-016.

Приёмка:

- Quote открывает соответствующий timestamp исходного файла.
- Исправленная транскрипция не переписывает original audio.

Следующий опыт: Короткое RU/EN media с числами, repo names и deliberately wrong ASR token.

Метрика: Alignment error; critical-token error rate; raw media retention.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-23`

## LIB-047 · P7 · Версионируемая схема импортера и неизвестные поля

Проблема: Новый формат export может сломать старый adapter или потерять неизвестные поля.

Поведение: Raw envelope сохранять; parser schema/version указывает supported поля; unknown values сохраняются и доступны для нового parser, adapter health виден.

Зависимости: LIB-006, LIB-008, LIB-016.

Приёмка:

- Новые поля не теряются после import/export.
- Несовместимая schema даёт explicit degraded status.

Следующий опыт: Изменить fixture export field names и добавить неизвестную вложенную структуру.

Метрика: Unknown-field retention=100%; silent schema drift=0.

Условие возвращения/начала: Выполнять после зависимостей и сверки актуального owner; состояние реализации проверяется по текущему коду, а не по старому ZIP.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/data_labeling/TAXONOMY_RU.json` · `extension_contract`

## LIB-049 · P7 · Выбор следующего недостающего доказательства

Проблема: Большой backlog растёт быстрее, чем закрываются причины неопределённости.

Поведение: Evidence debt по цели включает source/test/device/data gaps; next read/experiment ранжировать по устранению blocker и измеренной стоимости, не по количеству карточек.

Зависимости: LIB-020, LIB-022, LIB-024.

Приёмка:

- Каждая рекомендация указывает конкретный missing proof и зависимую цель.
- Непроверенный ROI отображён как оценка.

Следующий опыт: На десяти открытых целях сравнить FIFO и debt-based выбор сбора.

Метрика: Time-to-unblock; verified questions resolved per hour.

Условие возвращения/начала: После достоверного requirement/evidence graph и измерения baseline.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `CONTINUATION_V3/ASSISTANT_RND_PROPOSALS.json` · `ASSISTANT-RND-01`

## LIB-058 · P7 · Редактор заметок с неизменным импортным оригиналом

Проблема: Пользователю нужны собственные annotations и страницы, но редактирование может затереть source evidence.

Поведение: Рабочая заметка/blocks — новый authored artifact с backlinks и revision history; imported original read-only, цитаты ссылаются на версии; undo/restore.

Зависимости: LIB-016, LIB-030, LIB-050.

Приёмка:

- Редактирование заметки не меняет hash импортного оригинала.
- После undo backlinks и version history сохраняются.

Следующий опыт: Создать note из трёх source quotes и отредактировать свой текст.

Метрика: Source mutation errors=0; note restore success.

Условие возвращения/начала: После raw library и поиска; rich block editor не блокирует первый handoff.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `design/MASTER_DESKTOP_RU.txt`

## LIB-060 · P7 · Проверка масштаба архива по семействам, а не повторной распаковке

Проблема: Каждый новый master ZIP повторно вкладывает все старые packages и многократно раздувает обработку.

Поведение: Предложить content-addressed archive graph с original container preservation и общими member objects; compact portable package использует manifest aliases и отдельный materialize contract, не теряя возможность вернуть исходные ZIP.

Зависимости: LIB-008, LIB-009, LIB-028, LIB-056.

Приёмка:

- Каждый оригинальный архив возвращается с прежним hash.
- Повторно вложенный archive hash сканируется один раз, все nesting paths остаются.

Следующий опыт: Сравнить naive recursive unpack и archive graph на текущих пяти ZIP.

Метрика: Unique bytes/expanded logical bytes ratio; scan time; original recovery=100%.

Условие возвращения/начала: После correctness raw preservation; compact format не заменяет original uploads до roundtrip verifier.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/03_NO_LOSS_AND_LIMITS_RU.txt`

## RND-025 · P7 · Измеренная параллельность strategy/replay workers

Проблема: Число процессов не равно полезной пропускной способности или on-chain параллелизму.

Поведение: Раздельно конфигурировать capture, detector, simulation и ledger stages; independent workspaces читать immutable snapshots, общие изменяемые ресурсы координировать.

Зависимости: RND-012, RND-015, RND-018, RND-024.

Приёмка:

- Прогоны 1/2/4 workers используют одинаковый dataset и суммарный budget.
- Нет дублирующих writers одного ledger.
- Сохранены p95 latency, memory и dropped-work причины.

Следующий опыт: Сравнить throughput и полезный результат при 1/2/4 workers до увеличения лимита.

Метрика: Verified opportunities/hour при одинаковых затратах.

Условие возвращения/начала: Concurrency текущего runtime не повышается без отдельной проверки его owner.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/automation/GAP_MATRIX_RU.txt` · `GAP-14`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-030`

## RND-026 · P7 · Граф конфликтов ресурсов и капитала

Проблема: Несколько хороших opportunities могут требовать одинаковые accounts, capital или state.

Поведение: Строить conflict graph по writable resources и funding; назначать только совместимые simulation jobs и переоценивать устаревшие кандидаты.

Зависимости: RND-021, RND-025.

Приёмка:

- Конфликтующий shared resource не получает двух активных leases.
- Изменение snapshot отменяет прежнее допущение.

Следующий опыт: Replay portfolio с shared pools/accounts и независимыми маршрутами.

Метрика: Conflict rate, wasted simulations и полезный throughput.

Условие возвращения/начала: Live resource coordination требует отдельного runtime qualification, здесь только research spec.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `OCC_RND::EXP-039`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-030`

## RND-030 · P7 · Атлас рынков, протоколов и проверяемых возможностей

Проблема: Стремление охватить все деньги/рынки не определяет доступность данных и техническую реализуемость.

Поведение: Каталогизировать chain/venue/protocol/pairs, data access, liquidity observations, settlement, adapter support, costs и experiment status; ранжировать следующий пробел.

Зависимости: RND-015, RND-028, RND-029.

Приёмка:

- Каждый новый рынок имеет источник, дату и missing requirements.
- Объём рынка не помечается доступной прибылью.

Следующий опыт: Составить source-backed карточки трёх рынков и выбрать один по измеримой доступности данных.

Метрика: Coverage выбранного market universe и cost per evaluated hypothesis.

Условие возвращения/начала: Расширять после полезного полного цикла на одной вертикали.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/10_PARALLEL_WEB3_RND_RU.txt`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_WORKFLOW_CATALOG.json` · `SCE_V2::07_web3_research_to_experiment`

## RND-031 · P7 · Circular/triangular арбитраж как сравнимый research pack

Проблема: Наличие цикла цен ещё не означает net executable opportunity.

Поведение: Описать borrow→swaps→repay, средства проверки поддержанных инструкций, costs и sensitivity; выводить кандидатов в replay/paper portfolio.

Зависимости: RND-019, RND-020, RND-021, RND-029, RND-030.

Приёмка:

- Fee/size/resource boundary включены в отчёт.
- Unsupported lender/venue не скрывается generic route.

Следующий опыт: Один трёхшаговый historical route и отрицательный контроль с закрывающими edge fees.

Метрика: Out-of-sample modeled net и accepted/rejected reason distribution.

Условие возвращения/начала: Profitability неизвестна; live не включается этим roadmap.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/10_PARALLEL_WEB3_RND_RU.txt`

## RND-032 · P7 · Liquidation+swap как отдельный research pack

Проблема: Eligibility, oracle timing и collateral settlement могут разрушить liquidation-гипотезу.

Поведение: Проверять eligibility на выбранном state, доступность collateral, обязательный repayment и конкуренцию; хранить actor-specific assumptions.

Зависимости: RND-013, RND-019, RND-021, RND-029, RND-030.

Приёмка:

- Позднее oracle update не используется в раннем решении.
- Неатомарное получение collateral исключается из atomic claim.

Следующий опыт: Replay одного eligible и одного ineligible liquidation fixture.

Метрика: Eligibility accuracy и modeled net после расходов.

Условие возвращения/начала: Требуются protocol state и подтверждённый adapter; доходность неизвестна.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/10_PARALLEL_WEB3_RND_RU.txt`

## RND-033 · P7 · Stable peg и wrapper conversions с settlement-моделью

Проблема: Отклонение цены от номинала не означает доступный мгновенный redemption.

Поведение: Хранить fee, redemption rights, delay, liquidity, exposure duration и различать atomic conversion от inventory-risk позиции.

Зависимости: RND-019, RND-020, RND-021, RND-029, RND-030.

Приёмка:

- Delayed redemption не проходит flashloan atomic contract.
- Конвертация размера учитывает фактическую доступную ликвидность.

Следующий опыт: Сравнить мгновенный conversion fixture с отложенным redeem fixture.

Метрика: Ошибка classification atomic/non-atomic и sensitivity net.

Условие возвращения/начала: После получения актуальных конкретных правил redemption.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/10_PARALLEL_WEB3_RND_RU.txt`

## RND-037 · P7 · Медиа и transcripts как воспроизводимый research corpus

Проблема: Извлечённый текст видео теряет timestamp, speaker или исходное утверждение.

Поведение: Импортировать предоставленные SRT/VTT/audio/video metadata, связывать transcript spans с claims; optional ASR имеет свою версию и confidence, original сохраняется.

Зависимости: RND-011, RND-036.

Приёмка:

- Каждый claim открывает точный media timestamp/span.
- Неразобранный media object остаётся RAW_ONLY.
- ASR confidence не трактуется как истинность утверждения.

Следующий опыт: Сопоставить предоставленные subtitles и ручную расшифровку короткого RU/EN отрывка.

Метрика: Citation timestamp accuracy и claim extraction corrections.

Условие возвращения/начала: Live media connectors после полезного офлайн импорта и проверенных условий доступа.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## RND-038 · P7 · Technology scout по конкретным пробелам продукта

Проблема: Бесконечный список новых моделей не закрывает конкретные задачи приложения.

Поведение: Связывать paper/model/tool release с текущим blocker, версией, лицензией, runtime requirements и коротким baseline experiment.

Зависимости: RND-002, RND-028, RND-036.

Приёмка:

- У каждого candidate указан затрагиваемый gap и измеримый результат.
- Старый benchmark не выдаётся за результат на Dell.

Следующий опыт: Сравнить один candidate extractor/router с текущим deterministic baseline.

Метрика: Доля scout candidates, уменьшивших конкретный blocker при допустимых затратах.

Условие возвращения/начала: Не устанавливать model до определения benchmark и нужных ресурсов.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `OCC_RND::research.fetch_primary_metadata`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `OCC_RND::research.license_compatibility_review`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `OCC_RND::research.compare_revisions`

## RND-041 · P7 · ROI автоматизации против ручного/no-action baseline

Проблема: Количество jobs, PR или документов не показывает экономию времени и пользу.

Поведение: Считать manual baseline time, setup/maintenance/review cost, failures и полезные accepted outputs; отдельно оценивать продуктовый ROI и modeled market PnL.

Зависимости: RND-028, RND-039.

Приёмка:

- Отчёт включает стоимость настройки и ручных исправлений.
- Непринятый результат не считается завершённой полезной задачей.

Следующий опыт: Одинаковая недельная выборка research/context задач в ручном и автоматизированном режиме.

Метрика: Net minutes saved и cost per accepted outcome.

Условие возвращения/начала: Порог окупаемости выбрать до расширения масштабов.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-032`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/MASTER_FUNCTION_CATALOG.json` · `SCE_V2::PIPE-18`

## RND-046 · P7 · Карта отсутствующих доказательств до решения о масштабировании

Проблема: Большой каталог и красивый report создают ложное чувство завершённости.

Поведение: Показывать отдельные evidence gaps: sources, parser coverage, repo implementation, real device, market regimes, economics и operational recovery; каждый gate имеет владельца и выходной artifact.

Зависимости: RND-022, RND-023, RND-025, RND-029, RND-041.

Приёмка:

- Размер ZIP и число карточек не входят как доказательство готовности.
- Отсутствующий evidence блокирует только соответствующее утверждение.
- Отчёт перечисляет следующий самый полезный сбор данных.

Следующий опыт: Подать полный архив без device/market receipts и проверить, что readiness остаётся unverified по этим осям.

Метрика: False-readiness claims и время поиска необходимого evidence.

Условие возвращения/начала: Eventual live readiness требует отдельной текущей программы runtime/risk/signer/settlement; здесь не оценивается.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-014`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-004`

## ACT-041 · P8 · Контракт переносимого навыка

Проблема: Успешный prompt или цепочка кликов ошибочно считается reusable skill.

Поведение: Skill manifest включает input/output schemas, effects, scopes, pre/postconditions, environment fingerprint, код/version, replay corpus и fallback.

Зависимости: ACT-002, ACT-003, ACT-012, ACT-039.

Приёмка:

- Несовместимая среда блокирует skill invocation или возвращает planner.
- Promotion требует receipt, привязанный к skill code hash.

Следующий опыт: Один known workflow воспроизвести с другим project path и версией fixture app.

Метрика: Replay success; contract mismatch detection; skills с полными manifests.

Условие возвращения/начала: Не публиковать skill как production до проверенного применения в нужной среде.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-34`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-31.md` · `RND-31`

## ACT-042 · P8 · Демонстрация пользователя в проверяемый навык

Проблема: Повторяемая ручная последовательность не превращается в автоматизацию.

Поведение: Записывать разрешённую демонстрацию, извлекать параметры/условия, очищать приватные значения и репетировать в копии состояния перед сохранением skill.

Зависимости: ACT-020, ACT-035, ACT-041.

Приёмка:

- Запись не захватывает неразрешённые окна/секреты.
- Навык проходит unseen input, а не только буквальный replay одного видео.

Следующий опыт: Записать один локальный file workflow и воспроизвести на другом имени файла.

Метрика: Time-to-skill; held-out success; hidden parameter leakage.

Условие возвращения/начала: Демонстрация сама по себе не доказывает надёжность и не выдаёт новые scopes.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-34`
- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/OCC_RND/docs/05_ACCESSIBILITY_RU.md`

## ACT-043 · P8 · Сокращение навыка с сохранением инвариантов

Проблема: Длинная запись содержит лишние шаги и хрупкие задержки.

Поведение: Предлагать удаление/замену шагов и сравнивать исходный и сокращённый skill на held-out fixtures, сохраняя outcome predicates.

Зависимости: ACT-012, ACT-014, ACT-041, ACT-042.

Приёмка:

- Удаление шага принимается только при сохранении mandatory checks.
- Оптимизация не убирает authorization, evidence или проверку среды.

Следующий опыт: Сравнить длинный и минимизированный file workflow при изменённых путях и окнах.

Метрика: Step count; time-to-verified; regression rate.

Условие возвращения/начала: Не минимизировать по одному успешному replay.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-38.md` · `RND-38`

## ACT-045 · P8 · Unknown capability в небольшой coding workflow

Проблема: Просьба «любое действие» не имеет готового adapter и может уйти в неограниченную генерацию.

Поведение: Неизвестную способность превращать в scoped AutomationSpec, patch proposal в отдельной среде, контрактные тесты и reviewable integration; после проверки добавить один capability.

Зависимости: ACT-008, ACT-010, ACT-014, ACT-041.

Приёмка:

- Generated code не меняет trust policy и не получает production credentials.
- Следующий вызов проверенного skill не требует повторной генерации.

Следующий опыт: Создать один новый read-only adapter из задачи и проверить два held-out случая.

Метрика: Spec-to-verified-skill time; reuse success; scope creep.

Условие возвращения/начала: Git worktree не считать песочницей; интеграция зависит от разрешённого отдельного сценария.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/02_NEXT_IMPLEMENTATION_RU.md`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-27`

## ACT-046 · P8 · Staged updater и проверка происхождения релиза

Проблема: Загрузка нового кода может активировать чужую или устаревшую сборку.

Поведение: Проверять доверенные release metadata/digest, совместимость и healthcheck; скачивать в staging и активировать одну версию атомарно в своей границе.

Зависимости: ACT-011, ACT-012, ACT-041.

Приёмка:

- Правильный checksum от недоверенного publisher не проходит.
- Повтор release event не выполняет вторую активацию.

Следующий опыт: Подать чужой пакет, старую подписанную версию и корректный новый release.

Метрика: Rejected invalid releases; interrupted update recovery; activation consistency.

Условие возвращения/начала: Текущую поддержку подписи/attestation конкретного distribution channel проверить отдельно.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-38`

## ACT-047 · P8 · Миграции данных и ограниченный rollback

Проблема: Обновление кода и схемы может оставить смешанную несовместимую версию.

Поведение: До activation проверять migration plan на копии, backup/read compatibility и возможность возврата; явно описывать необратимые migrations.

Зависимости: ACT-024, ACT-046.

Приёмка:

- Ошибка миграции сохраняет пригодную прежнюю версию либо явный recovery state.
- Rollback тестируется на данных, а не только переключением бинарника.

Следующий опыт: Fault injection на migration steps и восстановление копии библиотеки.

Метрика: Data consistency; recovery time; успешность проверенного возврата.

Условие возвращения/начала: Не обещать универсальный rollback внешних сообщений, сделок или необратимой миграции.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-38`
- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/00_START/02_NEXT_IMPLEMENTATION_RU.md`

## ACT-048 · P8 · Permission diff при обновлении навыка

Проблема: Новая версия навыка может тихо получить более широкий доступ.

Поведение: Сравнивать filesystem roots, network hosts и effects старого и нового manifest; прежние scopes переносить, новые рассматривать отдельно по политике.

Зависимости: ACT-003, ACT-041, ACT-046.

Приёмка:

- Новый host/root не активируется от одного upgrade event.
- Неизменённые уже разрешённые scopes не требуют повторного запроса без причины.

Следующий опыт: Обновить skill с одним новым read root и проверить поведение политики.

Метрика: Privilege creep; корректность diff; лишние confirmations.

Условие возвращения/начала: Если authority расширяется, активация этой части ждёт соответствующей авторизации.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/packages/VOICE_V3/03_RND_CARDS/RND-39.md` · `RND-39`

## ACT-050 · P8 · Личное приложение и публичная оболочка возможностей

Проблема: Публичное распространение продукта может случайно включить личный контекст.

Поведение: Отделить per-user namespace и локальную библиотеку от public capability metadata и демонстрационного corpus; личный desktop поток остаётся работоспособным без публикации.

Зависимости: ACT-003, ACT-005, ACT-041, ACT-046.

Приёмка:

- Distribution package не содержит private goals, source archives, tokens и локальные пути пользователя.
- Два тестовых пользователя не читают namespace друг друга.

Следующий опыт: Собрать dry-run public manifest из synthetic corpus и проверить privacy boundary.

Метрика: Private artifact leakage; cross-user isolation; install success.

Условие возвращения/начала: Каталоги/магазины, коммерческое распространение и их текущие требования проверять перед реальной публикацией.

Источники:

- `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03(1).zip` → `VOICE_AGENTOS_PARALLEL_CONTEXT_V2_2026-10-03/03_RND/NEW_TRACKS.json` · `RND-41`

## LIB-036 · P8 · Опциональная синхронизация snapshots и событий

Проблема: Синхронизация живого SQLite файла может создавать conflicting writers.

Поведение: Локальный режим остаётся основным; sync передаёт immutable objects, snapshots/events и конфликтующие revisions, не общий writable DB file.

Зависимости: LIB-023, LIB-035.

Приёмка:

- Concurrent notes не перезаписывают друг друга без conflict record.
- Offline устройство импортирует события без повторных aliases.

Следующий опыт: Два локальных replicas с divergent edits и последующим merge.

Метрика: Convergence after sync; lost edits=0; offline functionality.

Условие возвращения/начала: Вернуться после надёжного local backup/restore и реальной потребности второго устройства.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/07_COMPETITORS_AND_DATA_PIPELINES_RU.txt`

## LIB-051 · P8 · Управляемое удаление и срок хранения

Проблема: Пожизненная память требует возможности убрать выбранные личные материалы и производные индексы.

Поведение: Разработать deletion impact preview по aliases/derived objects/backups; tombstone и физическое удаление разделить; retention выбирается по collection, исходное намерение сохранить всё не превращается в запрет удалить.

Зависимости: LIB-008, LIB-023, LIB-035, LIB-038.

Приёмка:

- Удалённый private source исчезает из FTS/vector/pack caches согласно выбранному режиму.
- Shared blob не уничтожается, пока нужен другому разрешённому source.

Следующий опыт: Synthetic private source с aliases и embeddings: dry-run deletion graph.

Метрика: Residual searchable private material=0; correct shared-object retention.

Условие возвращения/начала: Реализовать после backup/scope controls и явного выбора retention; автоматическое удаление по умолчанию выключено.

Источники:

- `OCC_ALL_USER_IDEAS_STRATEGY_FULL_CONTEXT_V3_RU_2026-10-03.zip` → `RND_V2/data_labeling/TAXONOMY_RU.json` · `access.sensitivity`

## RND-034 · P8 · Intent/clearing и coincidence-of-wants solver

Проблема: Концепция solver не подтверждает доступ к intents и возможность settlement.

Поведение: Исследовать typed order constraints, matching/clearing, data access и проверяемый settlement proof; сначала offline solver.

Зависимости: RND-021, RND-029, RND-030.

Приёмка:

- Нарушение limit/expiry constraint отклоняется.
- Неподдержанный settlement отмечается до оценки выгоды.

Следующий опыт: Небольшой синтетический набор пересекающихся intents и независимый checker clearing.

Метрика: Constraint violations, solved value после modeled costs.

Условие возвращения/начала: Только после данных/adapter; не заявлять готовый интегрированный solver.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/10_PARALLEL_WEB3_RND_RU.txt`

## RND-035 · P8 · Cross-chain, basis и funding как отдельные capital/time стратегии

Проблема: Задержанные расчёты и будущие выплаты нельзя считать одним мгновенным займом.

Поведение: Вести отдельную модель capital exposure, transfer/settlement delays, funding timing, inventory и failure scenarios; не смешивать PASS с atomic routes.

Зависимости: RND-019, RND-020, RND-029, RND-030.

Приёмка:

- Каждая стадия имеет time horizon и источник финансирования.
- Отсутствующий future cashflow не идёт в available repayment.

Следующий опыт: Offline timeline одного cross-chain и одного funding сценария с задержкой/отказом.

Метрика: Capital-at-risk duration и sensitivity к задержкам.

Условие возвращения/начала: Дальняя R&D ветка; никаких предположений о готовности adapters и доходности.

Источники:

- `SCE_DESKTOP_FULL_CONTEXT_LAYA_RND_RU_2026-10-03 (2).zip` → `SCE_DESKTOP_RND_2026-10-03/01_RND/10_PARALLEL_WEB3_RND_RU.txt`

## RND-040 · P8 · Ablation качества контекста для coding-задач

Проблема: Больший prompt может быть дороже и менее полезен для конкретного patch.

Поведение: Сравнивать full pack, source-linked slice, slice без выбранного evidence и compact+delta на одном coder/verifier и frozen bug families.

Зависимости: RND-003, RND-006, RND-028, RND-039.

Приёмка:

- У всех вариантов одинаковые task/compute условия.
- Будущие исправления исключены из context.
- Результат оценивается исправленным поведением.

Следующий опыт: Десять сохранённых bug задач с удержанным holdout.

Метрика: Verified patch rate, utility/KB и cost per verified patch.

Условие возвращения/начала: После стабильного end-to-end coding loop; raw архив никогда не режется ради эксперимента.

Источники:

- `AUTOMATION_STRATEGY_ALL_IDEAS_V3_RU_2026-10-03(1).zip` → `STRATEGY_V3/03_CATALOGS/STRUCTURED_RND_CARDS.json` · `VOICE_V3::RND-26`

## RND-045 · P8 · Портфель экспериментов по ожидаемой информационной пользе

Проблема: Сотни идей конкурируют за небольшой compute/data budget.

Поведение: Ранжировать unresolved hypotheses по decision impact, cost и ожидаемому уменьшению неопределённости; хранить объяснение и периодически проверять ranking.

Зависимости: RND-028, RND-029, RND-039, RND-041.

Приёмка:

- Дешёвый опровергающий эксперимент может обойти дорогой scale-up.
- Изменение prerequisite возвращает только связанные deferred cards.
- Ranking не претендует на доказанную доходность.

Следующий опыт: Сравнить FIFO и экспертно проверенный information-value ranking на десяти прошлых blocker задачах.

Метрика: Resolved decision uncertainty per budget unit.

Условие возвращения/начала: После накопления достоверных time/cost/outcome данных.

Источники:

- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-015`
- `OCC_STRATEGY_MASTER_2026-10-03(1).zip` → `OCC_STRATEGY_MASTER_2026-10-03/catalogs/ASSISTANT_FUTURE_RND.json` · `AI-RND-035`

