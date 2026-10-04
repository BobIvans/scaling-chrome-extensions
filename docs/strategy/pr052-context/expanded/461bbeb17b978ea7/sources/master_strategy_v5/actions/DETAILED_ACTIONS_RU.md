# Практические действия: что ещё не доведено до результата

Дата: 2026-10-04. Этот раздел уточняет V4, а не меняет её исторические статусы. Основание: 164 карточки продукта и 130 задач из master ZIP; в `implementation/STATUS.json` V4 первый task/context/evidence этап зафиксирован как локальная неопубликованная реализация. Новые 30 карточек ACTION5 имеют статус **PLANNED**. Windows shell, voice, Laya runtime, auto-send, updater и paper campaign здесь не объявлены подключёнными. Доказательства в карточках — то, что нужно получить при будущей реализации.

Главный недоопределённый слой — операционные контракты между пользовательским действием и наблюдаемым результатом. Например, «импортировать PDF» ещё не отвечает, какие страницы пропущены, куда ведёт цитата, как обновить извлечение и что восстановит backup. «Сохранить навык» ещё не определяет его версию, права и причину остановки после обновления интерфейса. Ниже эти пробелы превращены в конкретные outputs, acceptance и recovery.

## Рекомендуемые решения и вопросы, которые остаются открыты

| Тема | Рекомендуемая исходная реализация | Какой выбор ещё нужен |
|---|---|---|
| Desktop host | Сначала минимальный Windows shell над существующим UI и native dispatcher; один canonical SQLite/Core | Какой host можно упаковать и квалифицировать на Dell; выбрать по prototype/install receipt, не по непроверенному обещанию |
| Локальный transport | Framed typed IPC к существующему dispatcher, handshake, namespace и bounded envelopes; desktop только клиент | Конкретный launch/IPC lifecycle на установленном Windows; version compatibility matrix |
| Неподдерживаемый формат | Всегда raw artifact + явный unsupported/error; извлечение — независимая версия | Первый набор PDF/Office/media importers и допустимый локальный runtime budget |
| Оригинал и правки | Immutable original, separately versioned extraction и user overlay | Кто может менять metadata каждого namespace; retention raw audio и личных данных |
| Поиск всей жизни | Exact/FTS + project/time filters, SourceAddress и bounded retrieval для конкретной цели | Проекты, privacy facets и временные границы, которые пользователь хочет использовать |
| Skills | Typed registered steps, source/demo provenance, versioned preconditions и device qualification | Какие 2–3 повторяемые действия станут первым corpus; критические slots каждой операции |
| Расписание | Один existing Core owner; occurrence key; явный skip/latest/bounded catch-up | Нужно ли будить sleeping PC; defaults окна, timezone и допустимого backlog |
| SCE→Studious | Discover/pin существующие read-only/replay/paper entrypoints; library индексирует references | Текущий SHA/entrypoints и доступные dataset/provider scopes; отсутствующие команды остаются gaps |

Ни один открытый выбор не требует остановить все направления: можно заранее реализовать source contracts, exact ranges, dataset fixtures и qualification corpus. До проверки Windows можно пользоваться offline export; до voice — текстом; до Laya — зарегистрированной локальной командой. Это отдельные наблюдаемые маршруты с собственными evidence.

## Пользовательские сценарии и ожидаемые состояния

**Сценарий A — локальная библиотека без Chrome.** Пользователь открывает desktop, выбирает TXT/PDF/audio и project scope. UI показывает original и disposition каждого файла. Поиск находит цитату и открывает точный source range; пользователь исправляет tag как overlay, задаёт цель, редактирует корзину и экспортирует документ. Restart сохраняет тот же каталог и task. ACTION5-01–14 определяют контракт этого сценария. Пакет может быть перенесён вручную; отправка в чат не выводится из успешного export.

**Сценарий B — длинный разговор.** Пользователь выбирает доступный чат, запускает capture и видит inventory сообщений/ветвей. После full-scroll UI показывает coverage и неизвестные ветви. Если site не позволяет доказать полноту, результат PARTIAL и предлагает export файла. Приложение не выдаёт top/bottom snapshot за весь разговор и не считает цитаты модели собственными словами пользователя. Основные уточнения: ACTION5-04, 05, 09, 11.

**Сценарий C — голосовая повторяемая работа.** Пользователь нажимает push-to-talk или вводит фразу текстом. Один IntentSpec содержит точные repo/destination/effect slots. Неизвестный slot остаётся NEEDS_INPUT; исправление создаёт новую revision. Registered template проходит preflight, Core владеет исполнением, STOP остаётся доступен без голоса. Позже проверенная демонстрация становится skill; adapter/build/grant drift делает её stale до повторной проверки. Основные уточнения: ACTION5-18–26.

**Сценарий D — data/replay/paper R&D для Studious.** Пользователь выбирает research цель и read-only template. Bridge связывает реальный Studious entrypoint с pinned SHA; existing data owner получает observations или использует offline dataset. Library индексирует manifest и source refs. Existing replay/paper owner запускает замороженный эксперимент; независимая оценка хранит pass/fail/unknown и контрпримеры. Следующий документ указывает недостающие данные или конкретный кодовый gap. Этот сценарий не запускает sender/signing и не обещает прибыль. Основные уточнения: ACTION5-27–30.

## Порядок реализации

| Этап | Карточки | Проверяемый результат |
|---|---|---|
| A5-0 Ownership/transport | 01–03 | Один store/job owner, desktop client, совместимый IPC |
| A5-1 Original-to-packet | 04–06, 10–14 | Источник сохранён, цитата открывается, конкретный goal packet экспортирован |
| A5-2 Formats/lifecycle | 07–09, 15–17 | Разные форматы, полный accounting, backup/restore/retention |
| A5-3 Actions | 18–22, 25–26 | Typed capability, один intent, registered execution, STOP и restart |
| A5-4 Skills | 23–24 | Проверенная демонстрация и автоматическое stale после drift |
| A5-5 Studious R&D | 27–30 | Read-only gather/replay/paper evidence → следующий gap brief |

Самый маленький полезный следующий slice: owner matrix → desktop/IPC → TXT original/range → exact search → корзина → portable export, с доступным STOP для длительной подготовки. PDF/audio, voice и навыки добавляются отдельными квалифицированными этапами. Existing V4 full-repo chunking и two-tab tasks продолжают работать по прежним IDs; ACTION5 уточняет их общий substrate, а не копирует их в новый исполнитель.

Любые численные latency/memory/accuracy thresholds в проекте являются **PROPOSED_NOT_MEASURED**, пока нет receipt устройства/corpus/version. Нулевая потеря учтённых entries, сохранение raw bytes, отсутствие cross-scope disclosure и отсутствие ложного verified — инварианты контракта, а не полученные измерения.

## Детальные карточки
### ACTION5-01 — Сверить операции библиотеки и границу транзакции перед desktop

**Цель:** Определить публичные source/version/search/task/job операции, чтобы desktop, импорт и браузер использовали существующие SQLite и Core.

**Статус:** PLANNED · P0. **Owner:** Существующие Content Lab, review/task owners и Core.

**Уточняет:** G3-001, LAYA4-001, PAR3-001, EVO3-001. **Features:** LIB-001, LIB-052, ACT-054. **Зависит:** G3-001.

**Входы:**

- Фактический SCE SHA; схема существующей SQLite; список native-команд и операторских профилей

**Выходы:**

- Карта operation → owner → table/transaction → DTO; план совместимой schema migration

**Критерии готовности:**

- Каждая требуемая операция связана с текущим owner; неизвестные операции обозначены GAP с отдельным scope.
- Импорт, UI и CLI читают один source head; число новых competing stores/executors равно нулю.
- Для каждой миграции определены schema version, precondition, rollback boundary и writer lock.

**Восстановление:**

- Изменившийся SHA блокирует использование старой карты; повторная сверка сохраняет прежнюю версию.
- Невозможный rollback миграции требует restore из проверенного backup до активной записи.

**Нужные доказательства:**

- Owner matrix с pinned SHA; SQL/schema diff; fixture одного импорта через два клиента

### ACTION5-02 — Собрать установочный desktop-сценарий без работающего Chrome

**Цель:** Получить локальный Windows UI для поиска, импорта и подготовки пакета на Dell, сохранив существующий backend.

**Статус:** PLANNED · P0. **Owner:** Desktop shell использует публичный Content Lab API; Core остаётся владельцем jobs.

**Уточняет:** LAYA4-023, EVO3-016, UI3-017. **Features:** LIB-029, LIB-031, ACT-050. **Зависит:** ACTION5-01.

**Входы:**

- Owner matrix; существующий UI; выбранный desktop-host и версия Python/native bundle

**Выходы:**

- Установочный manifest; один desktop entrypoint; инструкция first-run и uninstall без удаления данных

**Критерии готовности:**

- На Windows 11 при закрытом Chrome доступны импорт TXT, поиск источника и export task document.
- First-run показывает путь данных и установленную версию; повторный запуск открывает тот же namespace.
- Uninstall shell не удаляет пользовательский корпус; backend failure даёт доступный текст ошибки.

**Восстановление:**

- Невозможная установка сохраняет диагностику и позволяет открыть offline index.
- Неудачная новая shell-версия запускается рядом с прежней до подтверждённой активации.

**Нужные доказательства:**

- Installed-device receipt; версии runtime/host; журнал трёх действий без Chrome

### ACTION5-03 — Версионировать локальный IPC и восстановление соединения

**Цель:** Подключить desktop к существующему native dispatcher через bounded типизированный протокол вместо Chrome-посредника.

**Статус:** PLANNED · P0. **Owner:** Существующие native adapter и agent bridge; desktop является клиентом.

**Уточняет:** G3-004, UI3-001, PAR3-004. **Features:** LIB-029, ACT-015, ACT-038, ACT-051. **Зависит:** ACTION5-01, ACTION5-02.

**Входы:**

- Текущие команды, schema/byte limits, namespace policy; desktop lifecycle

**Выходы:**

- Handshake с protocol/capability versions; request_id и generation fence; typed error DTO

**Критерии готовности:**

- Desktop и браузер вызывают одну командную реализацию; IPC не принимает произвольные executable, argv или SQL.
- Unknown command, oversized frame и protocol mismatch отклоняются до изменения состояния.
- После reconnect поздний ответ прежней generation не меняет UI; повтор операции использует сохранённый intent key.

**Восстановление:**

- При потере IPC read возвращается как RETRYABLE; возможный write остаётся UNKNOWN до get по прежнему key.
- Handshake mismatch предлагает совместимую версию без автоматического переноса данных.

**Нужные доказательства:**

- IPC fixtures oversized/mismatch/reconnect; журнал same-key replay; owner matrix

### ACTION5-04 — CaptureEnvelope сохраняет исходный текст и автора

**Цель:** Сохранять оригинал, извлечённый текст и пользовательские правки с самостоятельной идентичностью и точным происхождением.

**Статус:** PLANNED · P0. **Owner:** Существующий Content Lab source/version owner.

**Уточняет:** G3-002, LAYA4-013, G3-008. **Features:** LIB-013, LIB-014, LIB-015, LIB-016, LIB-058. **Зависит:** ACTION5-01.

**Входы:**

- Bytes или DOM capture; source URI/path; capture permission/scope; наблюдаемое авторство

**Выходы:**

- Raw source version; CaptureEnvelope с content hash, times, author/confidence, extraction version; correction overlay

**Критерии готовности:**

- Реконструкция raw text совпадает byte-for-byte; нормализованный search text хранит обратные offsets.
- Время сообщения, время захвата и inferred event time не объединяются в одно поле.
- Цитата другого автора внутри сообщения не становится словами пользователя; неизвестное авторство явно UNKNOWN.
- Исправление пользователя создаёт overlay/version, сохраняя исходное написание.

**Восстановление:**

- Повреждённый или недекодируемый текст остаётся raw artifact с extraction error.
- Конфликт авторства сохраняется вместе с доказательствами; прежний оригинал не переписывается.

**Нужные доказательства:**

- Roundtrip fixture RU/EN/emoji/CRLF/BOM; author/quote fixtures; provenance graph

### ACTION5-05 — Учитывать full-scroll чат и недоступные ветви

**Цель:** Снимать доступные сообщения полностью и отличать capture текущей ветви от полного conversation export.

**Статус:** PLANNED · P0. **Owner:** Существующий browser/capture adapter → Content Lab, без нового store.

**Уточняет:** LAYA4-004, LAYA4-014, UI3-011, G3-006. **Features:** LIB-012, LIB-024, LIB-057. **Зависит:** ACTION5-04.

**Входы:**

- Выбранная conversation identity; видимые сообщения и их IDs; scroll state; доступный export

**Выходы:**

- Message inventory; ветви с known/unknown visibility; capture coverage ledger; resume cursor

**Критерии готовности:**

- Top/middle/bottom и virtualized-history fixtures дают по одной source version на наблюдаемый message ID.
- Loading/end-of-history подтверждается наблюдением; scroll без новых сообщений сам по себе не означает COMPLETE.
- Недоступная ветвь, удалённое сообщение, вложение и login wall отображаются как конкретный gap.
- Export и DOM capture связываются по происхождению; разные ветви не склеиваются по похожему тексту.

**Восстановление:**

- После перезагрузки capture продолжает с message IDs и проверяет старые hashes.
- Unknown end-of-history сохраняет PARTIAL и предлагает официальный export/ручной файл.

**Нужные доказательства:**

- Message/branch corpus; capture inventory; restart/virtualized scroll receipts

### ACTION5-06 — Закрепить общий контракт файлового импортера

**Цель:** Каждый файл должен сохраняться как оригинал с disposition и отдельной версией извлечения.

**Статус:** PLANNED · P0. **Owner:** Существующие intake/extractor и Content Lab owners.

**Уточняет:** LAYA4-014, LAYA4-004, LAYA4-017. **Features:** LIB-006, LIB-007, LIB-041, LIB-047. **Зависит:** ACTION5-01, ACTION5-04.

**Входы:**

- Выбранные files/folder scope; MIME/extension; bytes; extractor registry/version

**Выходы:**

- Importer manifest с discovered/imported/unsupported/error; source versions; bounded checkpoints

**Критерии готовности:**

- Несовпадение extension/MIME отражается в manifest; extraction не скрывает оригинал.
- У каждого выбранного файла ровно один исход: imported, excluded с причиной, unsupported или error.
- Повторное продолжение создаёт новые версии только для изменённых bytes и сохраняет все origins.
- Unknown importer fields сохраняются в raw envelope, не становятся исполнимыми настройками.

**Восстановление:**

- Исчерпание диска или crash оставляет committed sources и незавершённый cursor.
- Unsupported формат можно повторно извлечь после появления квалифицированного importer version.

**Нужные доказательства:**

- Fixture manifest; interruption/retry outputs; hashes оригиналов

### ACTION5-07 — Разделить PDF/Office текст, таблицы и OCR

**Цель:** Предоставить точные page/sheet/cell ranges и указать качество извлечения для документов.

**Статус:** PLANNED · P1. **Owner:** Версионируемые extraction adapters существующего Content Lab.

**Уточняет:** LAYA4-014, LAYA4-016, G3-003. **Features:** LIB-045, LIB-059, LIB-014. **Зависит:** ACTION5-06.

**Входы:**

- PDF/DOCX/XLSX/PPTX originals; extractor version; OCR policy

**Выходы:**

- Text spans с page/paragraph/slide/cell refs; table structure; OCR confidence; extraction gaps

**Критерии готовности:**

- Клик по найденному тексту открывает исходную страницу/ячейку и версию файла.
- Числа, единицы, отрицательные значения и merged cells сверены на размеченном corpus; потеря структуры помечена.
- Scanned PDF имеет OCR-derived label и сохраняет original page; OCR не выдаётся за точный imported text.
- Password-protected/unsupported embedded object остаётся конкретным gap.

**Восстановление:**

- Ошибка одной страницы не переводит весь файл в COMPLETE.
- Повтор extraction новым движком сохраняет старую версию и invalidate зависимый packet.

**Нужные доказательства:**

- Golden tables/numbers corpus; extraction coverage; page/range screenshots

### ACTION5-08 — Импортировать audio/video с проверяемым transcript

**Цель:** Связать transcript с временными участками оригинала и отдельно хранить ASR и ручные исправления.

**Статус:** PLANNED · P1. **Owner:** Существующий extraction owner; ASR только адаптер извлечения.

**Уточняет:** LAYA4-014, LAYA4-013, LAYA4-023. **Features:** LIB-046, LIB-016, ACT-029, ACT-034. **Зависит:** ACTION5-06, ACTION5-04.

**Входы:**

- Выбранное audio/video; модель ASR/version; язык; политика retention

**Выходы:**

- Media source hash; timed transcript; model/config receipt; correction overlay

**Критерии готовности:**

- Фрагмент transcript открывает соответствующий time range оригинала.
- Unintelligible segment обозначен UNKNOWN; speaker identity не выводится без evidence.
- RU/EN/code-switch corrections не изменяют ASR оригинал; модель/версия сохранены.
- Без разрешённого внешнего profile медиа остаётся локальным.

**Восстановление:**

- Длинный файл обрабатывается частями с checkpoints; соседние overlap segments дедуплицируются по времени.
- Неудачный ASR оставляет media available и позволяет вручную внести timed note.

**Нужные доказательства:**

- Timed golden corpus; transcript/source hash receipts; restart and correction fixtures

### ACTION5-09 — Учитывать архивы, папки и вложения как граф происхождения

**Цель:** Сохранять структуру вложенности и все исключения, чтобы импорт архива не терял данные и происхождение.

**Статус:** PLANNED · P1. **Owner:** Существующий intake/Content Lab importer.

**Уточняет:** LAYA4-004, LAYA4-010, LAYA4-014, LAYA4-017. **Features:** LIB-009, LIB-010, LIB-041, LIB-048, LIB-060. **Зависит:** ACTION5-06.

**Входы:**

- Выбранный folder/archive; архивные member paths; extractor policy; byte/depth budgets

**Выходы:**

- Archive-member graph; disposition каждого entry; dedup origin links; blocked-entry report

**Критерии готовности:**

- Вложенные ZIP, одинаковые bytes в двух путях, empty entry и missing attachment учтены отдельно по происхождению.
- Traversal path, symlink, compression bomb и budget limit дают явный blocked/error и не записывают вне staging scope.
- Repo LFS pointers/submodules остаются отдельным disposition до фактического получения разрешённых bytes.
- Повторная распаковка не считает копии независимыми подтверждениями.

**Восстановление:**

- Budget exceed сохраняет исходный архив и список необработанных entries.
- Resume проверяет parent archive hash, изменившийся архив создаёт новый import run.

**Нужные доказательства:**

- Nested/archive edge fixtures; origin graph; accounted-entry report

### ACTION5-10 — Версионировать автометки и пользовательские исправления

**Цель:** Сделать теги объяснимыми и обратимыми, чтобы автоматизация не переписывала пользовательскую классификацию.

**Статус:** PLANNED · P1. **Owner:** Существующий metadata/catalog owner.

**Уточняет:** LAYA4-015, G3-008, EVO3-002. **Features:** LIB-018, LIB-019, LIB-021, LIB-050. **Зависит:** ACTION5-04, ACTION5-06.

**Входы:**

- Source version; taxonomy version; rules/model proposals; user overlays

**Выходы:**

- Labels по независимым facets project/type/topic/status/privacy; label origin/confidence; correction history

**Критерии готовности:**

- Каждый автоматический tag указывает rule/model version и supporting source span либо отмечен inference.
- User correction имеет приоритет в представлении и не удаляет прежнее предложение.
- Разные facets не объединяют source type, цель, статус исполнения и private scope в одну метку.
- Taxonomy upgrade не переименовывает исторические labels без version mapping.

**Восстановление:**

- Низкая confidence оставляет uncategorized или suggestion, без потери поиска.
- Failed retagging возвращает прежнюю отображаемую версию до atomic activation.

**Нужные доказательства:**

- Размеченный label corpus; correction replay; facet/version mapping

### ACTION5-11 — Сделать SourceAddress для точной цитаты и диапазона

**Цель:** Любой вывод, найденный фрагмент и packet должен ссылаться на неизменяемую версию и точный range оригинала.

**Статус:** PLANNED · P0. **Owner:** Публичный read API Content Lab и существующий provenance owner.

**Уточняет:** G3-003, LAYA4-016, LAYA4-009. **Features:** LIB-014, LIB-033, LIB-040, RND-011. **Зависит:** ACTION5-04, ACTION5-06.

**Входы:**

- Source ID/version/hash; byte/text/time/page ranges; derived extraction mappings

**Выходы:**

- Typed SourceAddress; bounded range API; resolver с validity/stale states

**Критерии готовности:**

- SourceAddress открывает тот же диапазон после restart; изменение оригинала не переносит ссылку молча.
- Derived text указывает исходный range и extraction version; unsupported mapping возвращает UNKNOWN.
- Ошибочные range bounds, namespace и hash отклоняются до чтения.
- Удалённый оригинал возвращает tombstone/missing и не подменяется совпадающей цитатой.

**Восстановление:**

- Stale address предлагает доступную новую версию и diff как отдельный выбор.
- Повреждённый range отменяет экспорт зависимого packet до проверки.

**Нужные доказательства:**

- Range roundtrip corpus; access-scope tests; deletion/version drift fixtures

### ACTION5-12 — Квалифицировать поиск по точным источникам и областям

**Цель:** Предоставить быстрый локальный поиск без модели, с project/time/source/version filters.

**Статус:** PLANNED · P0. **Owner:** Существующий Content Lab search owner.

**Уточняет:** LAYA4-016, LAYA4-018, LAYA4-025. **Features:** LIB-017, LIB-032, LIB-050, LIB-052. **Зависит:** ACTION5-10, ACTION5-11.

**Входы:**

- FTS/index существующей библиотеки; labels; source heads; operator namespace scope

**Выходы:**

- QuerySpec exact-ID/path/quote/FTS; result ranges; explainable filters; saved views

**Критерии готовности:**

- ID/path/exact quote возвращают правильный source version или явный no-match; выдача включает ranges.
- Namespace/project/time filters применяются до построения packet и не раскрывают cross-scope snippets.
- Saved view хранит запрос, а не копии источников; deleted source исчезает из current view.
- Latency и relevance измерены на corpus отдельно для cold/warm; пороги описаны как proposed до измерения.

**Восстановление:**

- FTS corruption предлагает rebuild из источников, не теряя оригиналы.
- Модельная подсказка не заменяет deterministic exact-source route.

**Нужные доказательства:**

- Query golden set; filtered-result receipts; measured benchmark с device/corpus metadata

### ACTION5-13 — Зафиксировать WHY_THIS_PACKET и управляемую корзину контекста

**Цель:** Показать, почему выбраны источники для цели и какие необходимые части ещё не помещены.

**Статус:** PLANNED · P0. **Owner:** Существующие repo/context selection и task owner.

**Уточняет:** G3-003, G3-009, LAYA4-018, LAYA4-021, LAYA4-025. **Features:** LIB-025, LIB-026, LIB-027, LIB-028, ACT-009. **Зависит:** ACTION5-11, ACTION5-12.

**Входы:**

- Дословная goal revision; scope; frozen criteria; retrieval results; byte/part budgets

**Выходы:**

- Selection plan с criterion→source links; exclusions/missing dependencies; editable basket; frozen packet digest

**Критерии готовности:**

- Для каждого включённого range указана связь с goal/criterion либо user choice.
- Обязательный источник вне budget попадает в next-part/missing ledger; количество частей не имеет скрытого общего потолка.
- User removal меняет selection revision и packet digest; старый пакет остаётся auditable.
- Неизвестное утверждение создаёт bounded NEXT_CONTEXT_REQUEST, а не fabricated evidence.

**Восстановление:**

- Source drift возвращает RESCAN/RESELECT с конкретными affected criteria.
- Retrieval model failure оставляет exact-source search и ручную корзину доступны.

**Нужные доказательства:**

- Selection fixtures; goal coverage report; packet/range digest checks

### ACTION5-14 — Сделать быстрый переносимый share projection

**Цель:** Экспортировать только выбранные версии и диапазоны, с provenance и машинным index для другого AI.

**Статус:** PLANNED · P0. **Owner:** Существующие context/task export и share projection owners.

**Уточняет:** LAYA4-019, LAYA4-020, G3-005, TAB4-19. **Features:** LIB-005, LIB-037, LIB-038, ACT-005, ACT-010. **Зависит:** ACTION5-11, ACTION5-13.

**Входы:**

- Frozen selection; destination profile; private field exclusions; provider-neutral task schema

**Выходы:**

- TXT/MD/JSON/ZIP projection; manifest/digests; preview; result template; optional delta

**Критерии готовности:**

- Preview и export имеют один projection digest; все omissions отмечены и доступны для продолжения.
- Private overlay/excluded source не попадает в share bytes; эвристика секретов не выдаётся за гарантию.
- После export offline index позволяет найти исходный range без сети.
- Grok/ChatGPT/Gemini profile меняет transport formatting, сохраняя source/goal identity; фактические лимиты требуют qualification.

**Восстановление:**

- Disk/write error оставляет прежний законченный artifact; partial ZIP не отмечается ready.
- Policy или source change инвалидирует readiness прежнего projection.

**Нужные доказательства:**

- Export reconstruction; forbidden-byte fixtures; offline index scenario

### ACTION5-15 — Резервировать библиотеку согласованным snapshot

**Цель:** Получать проверяемый backup базы и blobs вместе с версией схемы и происхождением.

**Статус:** PLANNED · P1. **Owner:** Существующий Content Lab data owner; Core координирует maintenance intent.

**Уточняет:** LAYA4-027, EVO3-014, LAYA4-017. **Features:** LIB-035, LIB-036, LIB-039. **Зависит:** ACTION5-01, ACTION5-06.

**Входы:**

- Existing DB/blob stores; active jobs/leases; selected backup scope; schema/version manifest

**Выходы:**

- Atomic backup manifest; DB snapshot; referenced blobs; integrity receipt; secret reference inventory

**Критерии готовности:**

- Backup во время допустимых операций даёт согласованный source-head/event/blob snapshot.
- Каждый blob и DB artifact проходит hash/integrity check; missing bytes не скрываются.
- Ключи не копируются из credential storage в архив; сохраняются ссылки и шаги повторного подключения.
- Пользователь видит расположение, размер, время и последний проверенный restore status.

**Восстановление:**

- Недостаток места отменяет ready backup и сохраняет старый проверенный snapshot.
- Crash до manifest commit оставляет staging removable, без promotion.

**Нужные доказательства:**

- Backup manifest; concurrent-write fixture; integrity receipt

### ACTION5-16 — Проверить restore и миграцию на копии до активации

**Цель:** Восстанавливать личный каталог и переносить схему без второй базы в рабочем режиме.

**Статус:** PLANNED · P1. **Owner:** Существующий data owner и updater; копия только staging.

**Уточняет:** LAYA4-027, EVO3-015, TAB4-14, TAB4-15. **Features:** LIB-030, LIB-035, ACT-047. **Зависит:** ACTION5-15, ACTION5-03.

**Входы:**

- Verified backup; target schema/migration version; installed build binding

**Выходы:**

- Dry-run migrated copy; validation report; activation checkpoint; rollback/restore plan

**Критерии готовности:**

- Restore восстанавливает hashes, source heads, overlays, tombstones и task state; старое UNKNOWN не превращается в sent.
- Schema migration rehearsal сравнивает record/relationship counts и exact-source queries до/после.
- Активен один canonical DB path; activation выполняется при закрытых writer leases.
- Downgrade, не совместимый с новой схемой, использует проверенный pre-migration backup.

**Восстановление:**

- Corrupt/missing backup part предотвращает activation и показывает affected sources.
- Validation failure оставляет предыдущую active library и staging report.

**Нужные доказательства:**

- Restore/migration fixture receipts; before/after invariants; installed-device activation receipt

### ACTION5-17 — Определить tombstone, retention и очистку производных данных

**Цель:** Удалять выбранные данные предсказуемо и не возвращать их из cache, backup или старого packet.

**Статус:** PLANNED · P1. **Owner:** Существующий Content Lab provenance/data owner.

**Уточняет:** LAYA4-017, LAYA4-027, EVO3-010. **Features:** LIB-023, LIB-051, ACT-052. **Зависит:** ACTION5-11, ACTION5-15.

**Входы:**

- Source versions; dependents; user retention policy; active context leases; backup inventory

**Выходы:**

- Deletion impact preview; tombstone event; cache/retrieval invalidation; retention receipt

**Критерии готовности:**

- До удаления показаны зависимые packets/reviews и данные, ещё находящиеся в snapshots.
- Current retrieval не возвращает tombstoned source; lease завершение не resurrect data.
- Raw original, transcript, derived index и external projection имеют отдельные retention states.
- Restore old backup применяет текущие tombstones либо явно предлагает отдельный recovery namespace.

**Восстановление:**

- Частичная cleanup сохраняет tombstone и pending cleanup task; не показывает erasure completed.
- Уже отправленную внешнюю копию помечают remote retention unknown, без ложного удаления.

**Нужные доказательства:**

- Deletion/restore/cache corpus; impact graph; retention receipts

### ACTION5-18 — Типизировать capabilities по версии, эффекту и qualification

**Цель:** Показать реально доступные действия, их область, ограничения и установленную сборку.

**Статус:** PLANNED · P0. **Owner:** Существующие Core, native dispatcher и qualification owner.

**Уточняет:** PAR3-003, EVO3-017, TAB4-13, LAYA4-022. **Features:** ACT-002, ACT-003, ACT-012, ACT-054, RND-009. **Зависит:** ACTION5-01, ACTION5-03.

**Входы:**

- Registered commands/templates; installed build receipt; policy grants; capability test corpus

**Выходы:**

- CapabilityDescriptor с inputs/outputs/effects/resources/grant revision/version/stop semantics; status catalog

**Критерии готовности:**

- Capability недоступна без совпадения installed version, typed input contract и действующего grant.
- Описание различает read-only, local write, remote send и money-moving effect; hazard влияет на policy, не на маркетинговый title.
- PLANNED/UNKNOWN/QUALIFIED/STALE не объединяются в available.
- Изменение grant, adapter или build инвалидирует соответствующую qualification.

**Восстановление:**

- Unknown command возвращает small scoped development proposal; не исполняет guessed code.
- Qualification fail переводит capability в disabled/stale и сохраняет reason.

**Нужные доказательства:**

- Registry schema; installed-version fixtures; grant/qualification drift receipts

### ACTION5-19 — Операторские execution templates без shell из документа

**Цель:** Разрешить известные действия через заранее зарегистрированные команды и существующий job owner.

**Статус:** PLANNED · P0. **Owner:** Существующие automation Core и qualification adapter.

**Уточняет:** PAR3-003, LAYA4-022, LAYA4-024, TAB4-02. **Features:** ACT-004, ACT-006, ACT-011, RND-010. **Зависит:** ACTION5-18.

**Входы:**

- Operator profile/policy; registered template; typed slot values; pinned repository context

**Выходы:**

- Validated execution request; scope/budget preflight; Core job reference; evidence receipt

**Критерии готовности:**

- Doc/transcript/AI answer не задаёт executable/argv/env; выбирается operator-registered template.
- Template validation проверяет namespace, repo alias, expected version, allowed paths и bounded resources.
- Intent replay не создаёт вторую задачу; cancel использует существующий Core semantics.
- Read-only research template не получает signer, sender или wallet capability через наследование.

**Восстановление:**

- Precondition drift отменяет admission и требует fresh request.
- Невозможно доказать external effect — UNKNOWN и reconciliation, без повторного запуска.

**Нужные доказательства:**

- Profile/template validation corpus; same-key job replay; forbidden-param fixtures

### ACTION5-20 — Один IntentSpec для текста, голоса и Laya proposal

**Цель:** Разбирать разные входы в одну ревизию цели с критическими slots и явными неизвестностями.

**Статус:** PLANNED · P0. **Owner:** Существующий intent compiler; Laya/ASR advisory adapters, Core executor.

**Уточняет:** PAR3-005, LAYA4-022, LAYA4-023, G3-002. **Features:** ACT-001, ACT-007, ACT-030, ACT-031. **Зависит:** ACTION5-18, ACTION5-19.

**Входы:**

- Text или transcript source ref; corrected input; target aliases; capability registry

**Выходы:**

- IntentSpec goal revision/slots/scope; ambiguity report; deterministic plan proposal

**Критерии готовности:**

- Одинаковый исправленный text и voice transcript компилируются в одинаковый typed plan при одинаковых версиях.
- Repo, destination, effect kind и amount не угадываются при неоднозначности.
- Correction создаёт новую intent revision и отзывает неисполненный old intent.
- Из Laya принят только типизированный proposal; неизвестные instructions не обходят template/grant validation.

**Восстановление:**

- Ambiguous critical slot остаётся NEEDS_INPUT и сохраняет подготовленный контекст.
- Исправление после возможного эффекта требует reconciliation прежнего intent до нового action.

**Нужные доказательства:**

- Text/voice parity corpus; RU/EN critical-slot cases; correction/replay receipts

### ACTION5-21 — Доступный STOP вне модели и микрофона

**Цель:** Предоставить локальную остановку из каждого длительного состояния и различать прекращение подготовки и уже возможный внешний эффект.

**Статус:** PLANNED · P0. **Owner:** Existing Core cancellation owner; desktop/browser accessible controls.

**Уточняет:** UI3-016, PAR3-015, PAR3-021, TAB4-16. **Features:** ACT-032, ACT-033, ACT-036, ACT-057. **Зависит:** ACTION5-03, ACTION5-19.

**Входы:**

- Existing Core cancel API; UI pending states; active resource leases; accessible controls

**Выходы:**

- Всегда доступная кнопка/keyboard STOP; cancel request; stopped/unknown reconciliation projection

**Критерии готовности:**

- STOP доступен keyboard-only и без работающего ASR/model/Chrome.
- Подготовка, queue, active command и unknown send имеют разные наблюдаемые outcomes.
- После STOP истёкший worker/adapter не возобновляет действие и не меняет task как fresh owner.
- Screen-reader status объясняет, что остановлено и что требует проверки; предлагаемая задержка реакции измеряется на устройстве.

**Восстановление:**

- Непрерываемый внешний процесс остаётся CANCEL_REQUESTED/UNKNOWN с recovery path.
- Resume создаёт проверку checkpoints, а не автоматически продолжает uncertain effect.

**Нужные доказательства:**

- Keyboard/screen-reader device scenarios; late-callback fixtures; cancellation receipt

### ACTION5-22 — Квалифицировать voice capture и исправление критических slots

**Цель:** Сделать голос альтернативным входом в локальное приложение, сохраняя текстовый путь и жизненный цикл аудио.

**Статус:** PLANNED · P1. **Owner:** Существующий voice intake → intent compiler; ASR не executor.

**Уточняет:** UI3-017, LAYA4-023, TAB4-16, PAR3-021. **Features:** ACT-028, ACT-029, ACT-030, ACT-034, ACT-058. **Зависит:** ACTION5-08, ACTION5-20, ACTION5-21.

**Входы:**

- Mic device choice; push-to-talk policy; ASR adapter; RU/EN/code-switch corpus

**Выходы:**

- Capture session identity; audio retention choice; transcript/revision; slot correction UI; qualification receipt

**Критерии готовности:**

- Повтор hotkey не открывает второй capture stream; микрофон освобождён после stop/crash recovery.
- TTS/background speech и ошибочная фраза не получают готового execution grant.
- До action пользователь может исправить repo/destination/effect slots текстом; correction сохраняет provenance.
- Latency/accuracy/critical-slot error измерены на выбранном Windows mic и отмечены как qualification данного устройства.

**Восстановление:**

- Mic denied/model unavailable оставляет text input и показывает конкретный fallback.
- ASR failure не удаляет выбранный audio source вопреки retention policy.

**Нужные доказательства:**

- Mic lifecycle fixtures; RU/EN ASR corpus; installed-device receipts

### ACTION5-23 — Преобразовать показанную автоматизацию в тестируемый skill

**Цель:** Записывать демонстрацию в ограниченный навык с typed slots, preconditions и expected outcomes.

**Статус:** PLANNED · P2. **Owner:** Existing skill catalog/projected metadata; Core executes registered steps.

**Уточняет:** PAR3-024, LAYA4-024, G3-010. **Features:** ACT-041, ACT-042, ACT-043. **Зависит:** ACTION5-18, ACTION5-19, ACTION5-20, ACTION5-21.

**Входы:**

- User-selected demonstration scope; observed steps; capability versions; source refs

**Выходы:**

- Skill draft; typed step graph; parameter slots; required grants; replay qualification cases

**Критерии готовности:**

- Skill включает только наблюдаемые и разрешённые steps; пароль/secret values заменены credential references.
- Recorded tab/focus координаты не считаются переносимой identity без adapter binding.
- Skill replay проходит sandbox fixture и device scenario с независимым outcome receipt.
- Оптимизация лишних steps сохраняет preconditions, STOP и expected effect invariants.

**Восстановление:**

- Необъяснимый шаг остаётся manual/NEEDS_CONTEXT и блокирует autonomous qualification.
- Replay failure сохраняется как failure capsule с applicability conditions.

**Нужные доказательства:**

- Demo-source refs; skill schema; sandbox/device replay receipts

### ACTION5-24 — Инвалидировать skills при drift и permission diff

**Цель:** Связать работоспособность навыка с build/adapter/template/grant и своевременно требовать повторную qualification.

**Статус:** PLANNED · P2. **Owner:** Existing qualification/provenance owner; updater сообщает version change.

**Уточняет:** UI3-019, EVO3-010, TAB4-13, PAR3-023. **Features:** ACT-039, ACT-044, ACT-048, RND-042. **Зависит:** ACTION5-18, ACTION5-23.

**Входы:**

- Skill dependency manifest; installed version changes; grant diff; adapter canary results

**Выходы:**

- Affected-skill graph; stale reason; repair brief; requalification receipt

**Критерии готовности:**

- Изменившийся adapter/critical permission помечает зависимый skill STALE до execution admission.
- Не затронутые навыки сохраняют valid receipt только при доказанной dependency independence.
- Permission growth отображается как новый scope; прежний grant не расширяется молча.
- Repaired skill имеет новую version; failure capsules не исчезают.

**Восстановление:**

- Canary failure помещает capability/skill в quarantine, текстовый/manual fallback остаётся доступен.
- Отсутствующие dependency hashes дают UNKNOWN вместо optimistic reuse.

**Нужные доказательства:**

- Drift/permission corpus; affected graph; repaired skill qualification

### ACTION5-25 — Зафиксировать durable расписание и offline catch-up

**Цель:** Запускать согласованные повторяемые задачи через existing Core с расписанием, missed-run policy и идентичностью occurrence.

**Статус:** PLANNED · P1. **Owner:** Existing Core job/scheduler owner; Windows launch mechanism только будит owner.

**Уточняет:** PAR3-016, PAR3-019, LAYA4-024, EVO3-019. **Features:** ACT-049, ACT-024, RND-024. **Зависит:** ACTION5-19, ACTION5-21.

**Входы:**

- ScheduleSpec timezone/trigger/window; capability/template; scope; catch-up policy; budget

**Выходы:**

- Saved schedule revision; occurrence key; missed-run ledger; Core job linkage; pause/edit controls

**Критерии готовности:**

- Timezone Europe/Riga, DST, sleep/offline и clock change fixtures не создают duplicate occurrence.
- Для missed runs явно выбран skip/latest/bounded catch-up; нет неконтролируемого backlog.
- После policy/version drift schedule paused до revalidation.
- Schedule edit создаёт новую revision и не переписывает результаты старых occurrences.

**Восстановление:**

- Wake failure фиксируется при следующем запуске; catch-up следует прежней policy.
- Interactive UI или unresolved external effect не повторяются автоматически в фоне.

**Нужные доказательства:**

- Schedule/DST/offline corpus; occurrence/job references; device wake receipt

### ACTION5-26 — Продолжать work после restart с resource и checkpoint checks

**Цель:** Обеспечить предсказуемое восстановление очереди, когда Windows закрывает приложение, усыпляет ПК или меняется контекст.

**Статус:** PLANNED · P1. **Owner:** Existing Core scheduler/lease owner; UI отображает состояние.

**Уточняет:** PAR3-007, PAR3-014, PAR3-016, PAR3-022, TAB4-22. **Features:** ACT-024, ACT-027, ACT-040, ACT-057. **Зависит:** ACTION5-03, ACTION5-19, ACTION5-21, ACTION5-25.

**Входы:**

- Existing Core checkpoints/leases; source/target revisions; resource budget; queued intents

**Выходы:**

- Resume eligibility report; bounded queue projection; foreground/background admission

**Критерии готовности:**

- Restart не оживляет cancelled intent и не возобновляет unknown send до reconciliation.
- Changed HEAD/source/grant инвалидирует затронутый checkpoint; unaffected read-only work может продолжаться.
- Foreground user input сохраняет приоритет; пределы RAM/CPU и concurrency измерены на Dell, не заявлены заранее.
- Queue перегрузка показывается как waiting/budget blocker, исходный корпус не обрезается.

**Восстановление:**

- Corrupt checkpoint сохраняет failure capsule и безопасно начинает разрешённую immutable подготовку заново.
- Suspend во время possible write оставляет uncertainty и точную следующую проверку.

**Нужные доказательства:**

- Kill/suspend/restart corpus; lease/fence receipts; measured Dell resource profile

### ACTION5-27 — Сверить SCE→Studious read-only capability bridge

**Цель:** Связать библиотеку контекста с фактическими research/qualification owners studious-pancake без второй торговой системы.

**Статус:** PLANNED · P0. **Owner:** SCE existing Core/qualification bridge; Studious existing data/replay/qualification owners.

**Уточняет:** LAYA4-007, PAR3-003, G3-001, LAYA4-028. **Features:** RND-001, RND-002, RND-009, RND-010. **Зависит:** ACTION5-18, ACTION5-19.

**Входы:**

- Фактические pinned SCE и Studious SHA; CLI/qualification contracts; registered operator profiles

**Выходы:**

- Двухрепозиторная owner matrix; read-only command inventory; DTO mapping; missing-capability ledger

**Критерии готовности:**

- Каждая предлагаемая команда подтверждена code entrypoint и текущим test/contract либо отмечена GAP.
- Bridge сохраняет repo/build identity и явный режим READ_ONLY/REPLAY/PAPER; данные не становятся live permission.
- Signer/sender/wallet/grants не создаются через context importer или Laya proposal.
- Нет второго market-data owner, trading runtime или независимого job executor.

**Восстановление:**

- API/CLI drift ставит bridge STALE; пакет исследования остаётся доступным offline.
- Missing command создаёт небольшой source-linked implementation brief.

**Нужные доказательства:**

- Pinned owner/entrypoint matrix; fixture DTO mapping; forbidden-live-capability corpus

### ACTION5-28 — Собрать research observations с freshness и provenance

**Цель:** Автоматизировать разрешённый сбор данных для R&D через существующий Studious data owner и сохранять проверяемый контекст результатов.

**Статус:** PLANNED · P1. **Owner:** Existing Studious gathering/data owner; SCE индексирует references/observations.

**Уточняет:** LAYA4-024, LAYA4-028, PAR3-011, PAR3-017. **Features:** RND-015, RND-016, RND-017, RND-018, LIB-049. **Зависит:** ACTION5-27, ACTION5-25, ACTION5-11.

**Входы:**

- Registered read-only gathering template; chosen provider scope; capture window; quota policy

**Выходы:**

- Dataset manifest; provider/source timestamps; missing/stale/error ledger; source refs; bounded research packet

**Критерии готовности:**

- Каждое observation связано с provider/version/time and raw hash; отсутствующая информация остаётся UNKNOWN.
- Quota/backpressure/partial capture отражаются отдельно от отсутствия opportunity.
- Повторное использование одного dataset исследователями не считается независимым provider evidence.
- Offline fixture run воспроизводим; реальный сетевой run требует установленного adapter и его scope.

**Восстановление:**

- Provider outage сохраняет checkpoint и gap; retries bounded policy, не создают бесконечный loop.
- Point-in-time/freshness drift инвалидирует зависимый analysis, сохраняя raw observations.

**Нужные доказательства:**

- Gathering fixture; dataset/freshness manifest; bounded-retry receipts

### ACTION5-29 — Привязать replay/paper гипотезу к замороженным критериям

**Цель:** Дать воспроизводимый исследовательский цикл: гипотеза → dataset → existing replay/paper command → независимая оценка → следующий brief.

**Статус:** PLANNED · P1. **Owner:** Existing Studious replay/paper/qualification owners; SCE task/evidence layer.

**Уточняет:** PAR3-017, PAR3-022, EVO3-009, LAYA4-028. **Features:** RND-012, RND-019, RND-022, RND-028, RND-029, RND-041. **Зависит:** ACTION5-27, ACTION5-28, ACTION5-13.

**Входы:**

- Hypothesis/version; immutable dataset; existing qualification templates; cost/unit definitions; holdout policy

**Выходы:**

- ExperimentCase; exact run/config/result refs; pass/fail/unknown evaluation; counterexamples; next R&D request

**Критерии готовности:**

- Paper/replay output имеет свой mode label и не выдаётся за on-chain execution или measured real profit.
- Стоимость, комиссии, slippage и delay assumptions указаны с units и coverage gaps.
- Criteria/holdout frozen до запуска; неудачные trials сохраняются в реестре.
- Итог привязан к exact dataset/config/repo revision; source drift переводит evidence в stale.

**Восстановление:**

- Empty/invalid dataset даёт BLOCKED_EMPTY_DATA, не успешную campaign.
- Failed trial сохраняет replay capsule и конкретный source/data запрос следующего шага.

**Нужные доказательства:**

- Exact experiment receipt; frozen criteria/config; counterexample/holdout corpus

### ACTION5-30 — Вести общий qualification corpus и next brief из незакрытых aims

**Цель:** Определить наблюдаемые пользовательские результаты и не терять требования при следующем обновлении ZIP или кода.

**Статус:** PLANNED · P0. **Owner:** Existing task/review/qualification owners; roadmap является проекцией evidence.

**Уточняет:** G3-009, G3-010, G3-011, G3-012, EVO3-021, EVO3-024, LAYA4-026, TAB4-20, TAB4-21. **Features:** LIB-053, LIB-055, LIB-056, ACT-053, ACT-056, RND-043, RND-044, RND-046. **Зависит:** ACTION5-13, ACTION5-14, ACTION5-18, ACTION5-21, ACTION5-27.

**Входы:**

- Saved exact goals; all task statuses; source/version bindings; deterministic and device receipts; open decisions

**Выходы:**

- Aim→task→case→evidence matrix; golden/fault/accessibility corpus; prioritized next implementation brief; deferred register update

**Критерии готовности:**

- Каждая цель имеет реализованный результат с scope/evidence либо named gap/decision/deferred condition.
- Corpus покрывает wrong repo/tab, stale source, unsupported input, cancelled job, unknown send, restore и denied mic.
- Linux fixture pass не повышает Windows/Grok/Laya qualification; model claim не закрывает criterion.
- Next brief выбирает конкретный gap, owners, input artifacts, acceptance, recovery и verification scope.
- Публикация кода, внешняя отправка и live-money permissions остаются отдельным фактическим scope; roadmap не расширяет их.

**Восстановление:**

- Missing evidence оставляет критерий open и предлагает самый небольшой полезный test/source request.
- Master update сохраняет прежние IDs/versions и проверяет coverage всех исходных aim refs.

**Нужные доказательства:**

- Coverage matrix; fixture/device receipt manifests; no-goal-left-behind diff; next brief

