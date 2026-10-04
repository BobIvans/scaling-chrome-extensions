# Все сохранённые цели и условия достижения · V5

28 outcome groups покрывают 164 унаследованные продуктовые карточки. Группы пересекаются; это редакторское развитие сохранённых источников, а не 28 новых дословных цитат пользователя. Приёмка ниже предложена для будущей реализации. Исходные формулировки и историю сохраняет master archive.

## GOAL5-01 · Локальное доступное приложение на Windows

Открыть библиотеку и управлять задачами без обязательной открытой вкладки Chrome.

Сценарий: Установка → первое открытие → выбор проекта → восстановление после закрытия.

Приёмка:
* GOAL5-01-AC1: Desktop shell использует существующие service operations и один canonical store.
* GOAL5-01-AC2: Закрытие Chrome не останавливает локальный поиск и подготовку TASK.
* GOAL5-01-AC3: На Windows сохранён receipt установки, запуска и текстового управления.

Feature IDs: ACT-033, ACT-050, LIB-001, LIB-029, LIB-030, LIB-031, LIB-032, RND-010.

Milestones: M5-01.

Открытые operational decisions: DEC5-01, DEC5-10, DEC5-18, DEC5-24.

Новые уточнения задач: ACTION5-01, ACTION5-02, ACTION5-03, ACTION5-12, ACTION5-16, ACTION5-19, ACTION5-21, ACTION5-27.

Подтверждённая узкая основа V4:
* ACT-033: Текстовый UI/aria labels/состояния добавлены; установленный Windows screen-reader путь не проверялся.
* LIB-001: Существующий SQLite/Core и typed native API расширены шестью task-командами; desktop shell без Chrome не квалифицирован.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-02 · Полный учёт репозитория одной кнопкой

Выбрать repo и получить учёт всего pinned HEAD с прогрессом, отменой и продолжением.

Сценарий: Repo → полный scan → manifest → cancel/resume на порции.

Приёмка:
* GOAL5-02-AC1: Множество entries соответствует tree выбранного SHA; exclusions/errors показаны отдельно.
* GOAL5-02-AC2: Перезапуск продолжает тот же snapshot cursor, смена HEAD создаёт новую версию.
* GOAL5-02-AC3: Каждый INDEXED blob восстанавливается по chunks byte-for-byte.

Feature IDs: LIB-002, LIB-004, LIB-006, LIB-024, LIB-034, LIB-056, RND-001.

Milestones: M5-02.

Открытые operational decisions: DEC5-05, DEC5-08, DEC5-09, DEC5-23.

Новые уточнения задач: ACTION5-05, ACTION5-06, ACTION5-27, ACTION5-30.

Подтверждённая узкая основа V4:
* LIB-002: Проверен snapshot inventory 157/157; неподдерживаемые entries имеют явный статус.
* LIB-004: Пагинация inventory и task-list есть; auto-loop полного scan ещё планируется.
* LIB-006: Существующий repo scan cursor сохраняется в SQLite; произвольные source importers требуют своих контрактов.
* RND-001: Current SCE SHA и owners проверены; иные repo снимки остаются историческими.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-03 · Большие, binary и специальные источники без потери учёта

Сохранить или явно учесть источник, даже если он не помещается в текстовый документ AI.

Сценарий: Добавить большой архив → inventory → выбор оригинала/извлечения.

Приёмка:
* GOAL5-03-AC1: Unsupported/binary/LFS/submodule/link имеют отдельную причину и область покрытия.
* GOAL5-03-AC2: Размер/вложенность архивов ограничивают processing, но не скрывают неучтённые entries.
* GOAL5-03-AC3: Превышение лимита даёт явный pending/error и следующий допустимый путь.

Feature IDs: LIB-003, LIB-007, LIB-009, LIB-010, LIB-034, LIB-060.

Milestones: M5-02.

Открытые operational decisions: DEC5-08, DEC5-09.

Новые уточнения задач: ACTION5-06, ACTION5-09.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-04 · Связанные части кода для AI

Получить пакеты, где код связан с зависимостями, тестами и контрактами.

Сценарий: Выбрать функцию → граф → группа → многотомный handoff.

Приёмка:
* GOAL5-04-AC1: Group manifest ссылается на pinned paths/revisions/ranges; часть не выдаётся за всё repo.
* GOAL5-04-AC2: Resolved, ambiguous, external и dynamic edges различаются.
* GOAL5-04-AC3: Пакеты сохраняют related tests/contracts и все заявленные gaps.

Feature IDs: ACT-009, LIB-005, LIB-014, LIB-027, RND-003, RND-004.

Milestones: M5-02.

Открытые operational decisions: DEC5-05, DEC5-06, DEC5-07, DEC5-22.

Новые уточнения задач: ACTION5-04, ACTION5-07, ACTION5-11, ACTION5-13, ACTION5-14.

Подтверждённая узкая основа V4:
* LIB-005: sourceOffset продолжает части; единый delivery manifest всего repo ещё не реализован.
* LIB-014: Byte-exact Git chunks и source binding проверяются; это не spans всех форматов.
* RND-003: Python static graph/SCC существует; JS/TS и dynamic edges обозначены gaps.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-05 · Инкрементальные изменения и история разработки

Обновлять только изменившиеся источники и зависимые пакеты, сохраняя прежние версии.

Сценарий: Новая версия repo → delta → затронутые задачи → новый запрос.

Приёмка:
* GOAL5-05-AC1: Изменение байтов/commit/branch инвалидирует соответствующие производные.
* GOAL5-05-AC2: Rename/delete отражены в provenance, старый источник остаётся историческим.
* GOAL5-05-AC3: Delta packet перечисляет заменённые/добавленные/удалённые ranges, а не молча редактирует baseline.

Feature IDs: LIB-011, LIB-023, LIB-028, LIB-041, LIB-044, LIB-054, RND-005.

Milestones: M5-02, M5-05, M5-10.

Открытые operational decisions: DEC5-05, DEC5-08, DEC5-16.

Новые уточнения задач: ACTION5-06, ACTION5-09, ACTION5-13, ACTION5-17.

Подтверждённая узкая основа V4:
* LIB-023: Изменённые источники/profile/review инвалидируют текущую проверку; общий граф всех импортёров остаётся задачей.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-06 · Точная история чатов и авторство

Сохранять доступную переписку вместе с ролями, ветвями, цитатами и ограничениями захвата.

Сценарий: Выбранный чат → захват → отчёт полноты → local source.

Приёмка:
* GOAL5-06-AC1: Оригинал и извлечение имеют собственные ID/версии; цитата не становится новой репликой автора.
* GOAL5-06-AC2: Ветви/редактирования/недоступные сообщения учитываются отдельно.
* GOAL5-06-AC3: Полнота UI-scroll проверяется сравнением с доступным authoritative export, когда он есть.

Feature IDs: LIB-012, LIB-013, LIB-014, LIB-015, LIB-016, LIB-042, LIB-043, LIB-047.

Milestones: M5-03.

Открытые operational decisions: DEC5-06, DEC5-10, DEC5-16.

Новые уточнения задач: ACTION5-04, ACTION5-05, ACTION5-06, ACTION5-07, ACTION5-08, ACTION5-11.

Подтверждённая узкая основа V4:
* LIB-014: Byte-exact Git chunks и source binding проверяются; это не spans всех форматов.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-07 · Документы и медиа с проверяемыми ссылками

Найти текст, таблицу или фрагмент аудио и открыть место в исходнике.

Сценарий: PDF/Office/audio/video → extract → chunk → поиск → точный источник.

Приёмка:
* GOAL5-07-AC1: Extractor version и page/time spans сохранены.
* GOAL5-07-AC2: OCR/ASR output не перезаписывает оригинал; uncertain text и числа видимы.
* GOAL5-07-AC3: Ленивое извлечение, отмена и повторный запуск не создают ложную новую source identity.

Feature IDs: LIB-045, LIB-046, LIB-047, LIB-059, RND-037.

Milestones: M5-03.

Открытые operational decisions: DEC5-10, DEC5-13, DEC5-16.

Новые уточнения задач: ACTION5-06, ACTION5-07, ACTION5-08.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-08 · Одна библиотека оригиналов, версий и происхождения

Повторный импорт не размножает bytes и сохраняет все происхождения.

Сценарий: Импорт разных копий → один объект → несколько ссылок происхождения.

Приёмка:
* GOAL5-08-AC1: Source identity, raw object и extraction revision разделены.
* GOAL5-08-AC2: Одинаковые bytes могут иметь несколько provenance refs; это не несколько независимых доказательств.
* GOAL5-08-AC3: Миграция schema и конфликт restore проверяются до изменения canonical heads.

Feature IDs: LIB-001, LIB-008, LIB-009, LIB-016, LIB-030, LIB-048, LIB-052, LIB-056.

Milestones: M5-03.

Открытые operational decisions: DEC5-01, DEC5-06, DEC5-09, DEC5-10, DEC5-12, DEC5-16.

Новые уточнения задач: ACTION5-01, ACTION5-04, ACTION5-08, ACTION5-09, ACTION5-12, ACTION5-16, ACTION5-30.

Подтверждённая узкая основа V4:
* LIB-001: Существующий SQLite/Core и typed native API расширены шестью task-командами; desktop shell без Chrome не квалифицирован.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-09 · Поиск, метки, коллекции и временная применимость

Находить нужный контекст по проекту, цели, времени, источнику и исправленным меткам.

Сценарий: Короткий запрос → результаты → почему выбрано → исправление метки.

Приёмка:
* GOAL5-09-AC1: Поиск возвращает source/version/range, а не только summary.
* GOAL5-09-AC2: Ручное исправление метки переживает повторную extraction/classification.
* GOAL5-09-AC3: Противоречивые/устаревшие сведения показаны с датой применимости.

Feature IDs: ACT-052, LIB-017, LIB-018, LIB-020, LIB-021, LIB-048, LIB-050, LIB-058.

Milestones: M5-03, M5-10.

Открытые operational decisions: DEC5-14, DEC5-15.

Новые уточнения задач: ACTION5-04, ACTION5-09, ACTION5-10, ACTION5-12, ACTION5-17.

Подтверждённая узкая основа V4:
* LIB-017: Существующий local search/FTS доступен native; полный жизненный каталог требует развития.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-10 · Цели и требования не теряются

Сохранить исходную фразу и видеть, какое требование ещё не достигнуто.

Сценарий: Текст/голос → goal revision → требования → статус → следующий шаг.

Приёмка:
* GOAL5-10-AC1: Каждое требование связано с исходником либо помечено assistant-derived.
* GOAL5-10-AC2: Новый handoff сохраняет goal revision и непокрытые требования.
* GOAL5-10-AC3: Состояния proposed/implemented/tested/installed/usable различаются.

Feature IDs: ACT-056, LIB-019, LIB-020, LIB-022, LIB-025, LIB-026, LIB-053, LIB-054, RND-002.

Milestones: M5-03, M5-10.

Открытые operational decisions: DEC5-05, DEC5-07, DEC5-14, DEC5-15, DEC5-22.

Новые уточнения задач: ACTION5-10, ACTION5-13, ACTION5-27, ACTION5-30.

Подтверждённая узкая основа V4:
* LIB-019: Точный goal/scope/criteria заморожен в session/task; общая история версий целей ещё не реализована.
* LIB-022: Task связывает цель, sources, review и registered local evidence; полного UpdateCase graph ещё нет.
* LIB-025: TASK и next_request формируются из выбранного контекста/критериев; автоматический semantic retriever не подключён.
* RND-002: Узкая связь requirement/source/task/local job появилась; весь продукт не покрыт матрицей реализации.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-11 · Пакеты для разных AI и точный дозапрос

Быстро передать выбранный контекст ChatGPT/Grok/Gemini и вернуть запрос недостающего диапазона.

Сценарий: Корзина → preview → части → выбранный AI → ответ/NEED_CONTEXT.

Приёмка:
* GOAL5-11-AC1: Один provider-neutral manifest, отдельный qualified transport каждого адресата.
* GOAL5-11-AC2: Пакет имеет goal/source/destination scope и declared gaps.
* GOAL5-11-AC3: NEED_CONTEXT указывает версию и диапазон; supplied не означает read/used.

Feature IDs: ACT-005, ACT-008, ACT-009, ACT-010, ACT-013, LIB-025, LIB-026, LIB-027, LIB-028, LIB-037, LIB-038, LIB-039, LIB-040, LIB-057.

Milestones: M5-02, M5-03, M5-04.

Открытые operational decisions: DEC5-02, DEC5-03, DEC5-05, DEC5-07, DEC5-13, DEC5-14, DEC5-22, DEC5-23.

Новые уточнения задач: ACTION5-05, ACTION5-11, ACTION5-13, ACTION5-14, ACTION5-15.

Подтверждённая узкая основа V4:
* LIB-025: TASK и next_request формируются из выбранного контекста/критериев; автоматический semantic retriever не подключён.
* LIB-037: TASK можно вручную скопировать/скачать для выбранного AI; UI target и auto-send ещё планируются.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-12 · Сохранённая задача и надёжная ручная передача

Восстановить задачу и результат после перезапуска без повторной отправки неизвестной попытки.

Сценарий: Task → подготовка → manual transfer → наблюдение → result import.

Приёмка:
* GOAL5-12-AC1: Идемпотентные task/event keys и immutable packet сохраняются.
* GOAL5-12-AC2: Unknown outcome требует сверки, cancel сохраняет неопределённость.
* GOAL5-12-AC3: Ответ связан с task/session/packet; DONE не закрывает критерий.

Feature IDs: ACT-015, ACT-022, ACT-023, ACT-024, ACT-057, LIB-037.

Milestones: M5-01, M5-04.

Открытые operational decisions: DEC5-02, DEC5-03, DEC5-13, DEC5-18, DEC5-21.

Новые уточнения задач: ACTION5-03, ACTION5-14, ACTION5-21, ACTION5-25, ACTION5-26.

Подтверждённая узкая основа V4:
* ACT-015: taskKey/eventKey дают устойчивую identity ручных операций; external effect identity впереди.
* ACT-022: SQLite intent/events и reference-only UI cache работают для ручной передачи; автоматический executor не добавлен.
* ACT-023: Unknown/manual observation восстанавливается, включая cancel; remote reconciliation adapter ещё не подключён.
* ACT-024: Задача восстанавливается в новом процессе; полный DAG автоматических эффектов впереди.
* ACT-057: Есть task resume и unknown receipt controls; общая панель кампании дальше.
* LIB-037: TASK можно вручную скопировать/скачать для выбранного AI; UI target и auto-send ещё планируются.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-13 · Выбранная вкладка Grok и управление её интерфейсом

Один раз показать нужный чат и передавать документы в пределах настроенного сценария.

Сценарий: Показать чат → bind → проверить draft → send → подтвердить появление.

Приёмка:
* GOAL5-13-AC1: Account/chat/session binding перепроверяется перед эффектом.
* GOAL5-13-AC2: Draft/upload/send имеют разные receipts; потеря наблюдения не вызывает blind retry.
* GOAL5-13-AC3: После UI drift adapter теряет qualification до canary/rebinding.

Feature IDs: ACT-003, ACT-004, ACT-035, ACT-036, ACT-037, ACT-039, LIB-037.

Milestones: M5-04.

Открытые operational decisions: DEC5-02, DEC5-03, DEC5-04, DEC5-13, DEC5-18.

Новые уточнения задач: ACTION5-14, ACTION5-18, ACTION5-19, ACTION5-21, ACTION5-24.

Подтверждённая узкая основа V4:
* ACT-004: Импортированный task result не выбирает команды или profile; полная политика всех будущих adapters отдельно.
* LIB-037: TASK можно вручную скопировать/скачать для выбранного AI; UI target и auto-send ещё планируются.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-14 · GitHub, изменения и фактический merge

Связать ответ AI с repo/PR/проверенной итоговой ревизией.

Сценарий: Ответ → change candidate → checks → merge observation → exact revision.

Приёмка:
* GOAL5-14-AC1: Review/patch/PR связываются с конкретным base и change identity.
* GOAL5-14-AC2: Squash/rebase/merge сопоставляются по фактическим artifacts и policy.
* GOAL5-14-AC3: Фраза о merge и UI title сами по себе не заменяют проверку remote SHA.

Feature IDs: ACT-011, LIB-044, RND-005, RND-006, RND-007.

Milestones: M5-05.

Открытые operational decisions: DEC5-16, DEC5-20.

Новые уточнения задач: ACTION5-19.

Подтверждённая узкая основа V4:
* RND-006: Verifier проверяет существующий Core patch/test worktree; импорт ответа AI сам не запускает patch job.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-15 · Независимые проверки результата

Проверять критерий по подходящему доказательству, сохраняя неизвестное.

Сценарий: Критерий → зарегистрированный check → receipt → independent revalidation.

Приёмка:
* GOAL5-15-AC1: Local tests, CI, merge, installation и device outcome имеют отдельные bindings.
* GOAL5-15-AC2: Изменение input/template/policy/registry/bytes делает связанные evidence stale.
* GOAL5-15-AC3: Проверка измеряет сам критерий, а не доверяет модели или одному exit code без test binding.

Feature IDs: ACT-012, ACT-013, ACT-014, ACT-053, RND-008, RND-011, RND-023, RND-042, RND-043.

Milestones: M5-05.

Открытые operational decisions: DEC5-01, DEC5-04, DEC5-18, DEC5-20, DEC5-23, DEC5-24.

Новые уточнения задач: ACTION5-11, ACTION5-18, ACTION5-24, ACTION5-30.

Подтверждённая узкая основа V4:
* ACT-012: Есть narrow local-test receipt с актуальной revalidation; CI/merge/install/device не подтверждаются.
* RND-011: Схема local-evidence явно отделяет CI/merge/install и semantic claim. Полная UpdateEvidence далее.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-16 · Обновление приложения и новые проверенные возможности

Получить обновление из точной версии, установить его и проверить новую capability.

Сценарий: Merge → staging → tests → install → canary → registry.

Приёмка:
* GOAL5-16-AC1: Release/source/assets имеют проверяемую связь.
* GOAL5-16-AC2: Staging, schema migration и rollback проходят репетицию.
* GOAL5-16-AC3: Capability registry связан с установленной build и device qualification.

Feature IDs: ACT-045, ACT-046, ACT-047, ACT-048, RND-008.

Milestones: M5-05, M5-06.

Открытые operational decisions: DEC5-01, DEC5-10, DEC5-19, DEC5-20.

Новые уточнения задач: ACTION5-16, ACTION5-24.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-17 · Текст в зарегистрированные действия и Laya-маршрутизация

Сказать или написать цель, получить исполнимый план либо запрос на разработку недостающей функции.

Сценарий: Фраза → IntentSpec → known handler / missing capability → plan preview.

Приёмка:
* GOAL5-17-AC1: Intent slots, capability version, scope и input references проверяются до enqueue.
* GOAL5-17-AC2: Laya advisory result не расширяет полномочия и может вернуть unknown.
* GOAL5-17-AC3: Неизвестная capability создаёт bounded coding/research request.

Feature IDs: ACT-001, ACT-002, ACT-003, ACT-004, ACT-006, ACT-007, ACT-051, ACT-054, RND-009, RND-010.

Milestones: M5-07.

Открытые operational decisions: DEC5-01, DEC5-02, DEC5-17, DEC5-19, DEC5-24.

Новые уточнения задач: ACTION5-01, ACTION5-03, ACTION5-18, ACTION5-19, ACTION5-20, ACTION5-27.

Подтверждённая узкая основа V4:
* ACT-004: Импортированный task result не выбирает команды или profile; полная политика всех будущих adapters отдельно.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-18 · Голос с исправлением намерения

Управлять теми же задачами голосом без потери контроля при ошибке распознавания.

Сценарий: Hotkey → речь → preview slots → correction → тот же text workflow.

Приёмка:
* GOAL5-18-AC1: Capture/ASR/intent отделены; версия намерения меняется при исправлении.
* GOAL5-18-AC2: Неуверенные критические slots не превращаются в тихое действие.
* GOAL5-18-AC3: TTS/background speech и lifecycle микрофона входят в qualification corpus.

Feature IDs: ACT-028, ACT-029, ACT-030, ACT-031, ACT-034, ACT-058.

Milestones: M5-07.

Открытые operational decisions: DEC5-12, DEC5-17.

Новые уточнения задач: ACTION5-08, ACTION5-20, ACTION5-22.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-19 · Доступное управление PC и независимая остановка

Работать текстом, клавиатурой или голосом и остановить исполнение независимо от модели.

Сценарий: Разрешённое действие → наблюдаемый outcome → stop/cancel/recovery.

Приёмка:
* GOAL5-19-AC1: Keyboard/text path доступен для каждого важного voice action.
* GOAL5-19-AC2: STOP и отмена не ждут ответа облачной модели; uncertain внешние effects сохраняются.
* GOAL5-19-AC3: Focus ownership и передача управления пользователю проверяются на устройстве.

Feature IDs: ACT-025, ACT-032, ACT-033, ACT-035, ACT-036, ACT-038, ACT-040, LIB-033.

Milestones: M5-04, M5-07.

Открытые operational decisions: DEC5-03, DEC5-04, DEC5-18, DEC5-21, DEC5-22.

Новые уточнения задач: ACTION5-03, ACTION5-11, ACTION5-21, ACTION5-26.

Подтверждённая узкая основа V4:
* ACT-033: Текстовый UI/aria labels/состояния добавлены; установленный Windows screen-reader путь не проверялся.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-20 · Расписания и длительные кампании

Продолжать разрешённую задачу по условию/расписанию после offline или перезапуска.

Сценарий: Campaign → registered jobs → checkpoints → offline/resume → outcome.

Приёмка:
* GOAL5-20-AC1: Missed-run/catch-up policy и input freshness сохраняются в campaign manifest.
* GOAL5-20-AC2: Нет повторного внешнего эффекта при restart/clock drift.
* GOAL5-20-AC3: Бюджет, deadline и отсутствие прогресса дают явную остановку.

Feature IDs: ACT-024, ACT-025, ACT-049, RND-024, RND-044.

Milestones: M5-08.

Открытые operational decisions: DEC5-21, DEC5-22.

Новые уточнения задач: ACTION5-25, ACTION5-26, ACTION5-30.

Подтверждённая узкая основа V4:
* ACT-024: Задача восстанавливается в новом процессе; полный DAG автоматических эффектов впереди.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-21 · Параллельное исследование с учётом ресурсов

Подготавливать и исследовать независимые данные одновременно, сохраняя один интегратор.

Сценарий: DAG → conflict/admission → isolated workers → one integrator → receipt.

Приёмка:
* GOAL5-21-AC1: Read/write/UI/shared-repo resources имеют canonical identity и leases.
* GOAL5-21-AC2: Cross-branch results сравниваются на одном immutable baseline.
* GOAL5-21-AC3: Admission измеряется на Dell; production parallelism меняется только после qualification.

Feature IDs: ACT-016, ACT-017, ACT-018, ACT-019, ACT-020, ACT-021, ACT-027, ACT-055, RND-025, RND-026, RND-039.

Milestones: M5-08, M5-10.

Открытые operational decisions: DEC5-21.

Новые уточнения задач: ACTION5-26.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-22 · Навыки из демонстраций и их устаревание

Повторять показанный сценарий и переставать использовать его после несовместимого обновления.

Сценарий: Показать → record → contract → qualification → reusable skill.

Приёмка:
* GOAL5-22-AC1: Demonstration сохраняет inputs, scope, preconditions и outcome evidence.
* GOAL5-22-AC2: Навык проходит тесты normal/fault cases перед регистрацией.
* GOAL5-22-AC3: UI/code/policy changes инвалидируют затронутую версию навыка.

Feature IDs: ACT-039, ACT-041, ACT-042, ACT-043, ACT-044, RND-043.

Milestones: M5-06, M5-07, M5-10.

Открытые operational decisions: DEC5-04, DEC5-19.

Новые уточнения задач: ACTION5-23, ACTION5-24, ACTION5-30.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-23 · Долговременный архив, восстановление и выборочная передача

Расти от сотен к тысячам источников, восстанавливать данные и делиться выбранной проекцией.

Сценарий: Добавить источники → поиск/pack → backup → restore → controlled sharing.

Приёмка:
* GOAL5-23-AC1: Backup включает schema, bytes, versions и heads; restore проверяет hashes/conflicts.
* GOAL5-23-AC2: Retention/delete учитывает производные и backup scope.
* GOAL5-23-AC3: Размер корпуса не подменяется размером AI packet; retrieval остаётся bounded.

Feature IDs: ACT-052, LIB-006, LIB-032, LIB-035, LIB-036, LIB-038, LIB-039, LIB-040, LIB-051, LIB-060.

Milestones: M5-03, M5-06, M5-10.

Открытые operational decisions: DEC5-02, DEC5-09, DEC5-11, DEC5-12, DEC5-13, DEC5-14.

Новые уточнения задач: ACTION5-06, ACTION5-09, ACTION5-11, ACTION5-12, ACTION5-14, ACTION5-15, ACTION5-16, ACTION5-17.

Подтверждённая узкая основа V4:
* LIB-006: Существующий repo scan cursor сохраняется в SQLite; произвольные source importers требуют своих контрактов.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-24 · Автоматизация исследований Studious через библиотеку

Из локальной цели запускать зарегистрированный сбор данных, replay и paper qualification.

Сценарий: SCE goal → Studious context → registered research job → evidence → next brief.

Приёмка:
* GOAL5-24-AC1: Repo/function/test handler подтверждён по actual source и registered profile.
* GOAL5-24-AC2: Read-only/replay/paper режимы и их data receipts явно различаются.
* GOAL5-24-AC3: Следующий brief основан на конкретном blocker, data gap и experiment result.

Feature IDs: RND-009, RND-010, RND-012, RND-015, RND-018, RND-022, RND-023, RND-024, RND-042, RND-043, RND-044.

Milestones: M5-09.

Открытые operational decisions: DEC5-01, DEC5-19, DEC5-21, DEC5-22, DEC5-24.

Новые уточнения задач: ACTION5-18, ACTION5-19, ACTION5-24, ACTION5-25, ACTION5-27, ACTION5-28, ACTION5-29, ACTION5-30.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-25 · Будущие web3-стратегии как проверяемые эксперименты

Сравнивать стратегии на согласованных данных и сохранять отрицательные результаты.

Сценарий: Гипотеза → data manifest → deterministic replay → counterexamples → decision.

Приёмка:
* GOAL5-25-AC1: Point-in-time inputs, costs, units, holdout и dependency boundaries заморожены.
* GOAL5-25-AC2: Flashloan/atomic, delayed capital и market-maker hypotheses не смешиваются как один execution path.
* GOAL5-25-AC3: Replay/paper results не объявляются прибылью live системы; qualification для каждого adapter отдельная.

Feature IDs: RND-012, RND-013, RND-014, RND-015, RND-016, RND-017, RND-018, RND-019, RND-020, RND-021, RND-022, RND-023, RND-024, RND-025, RND-026, RND-027, RND-028, RND-029, RND-030, RND-031, RND-032, RND-033, RND-034, RND-035, RND-042, RND-043, RND-045, RND-046.

Milestones: M5-09.

Открытые operational decisions: DEC5-21, DEC5-22, DEC5-23, DEC5-24.

Новые уточнения задач: ACTION5-24, ACTION5-25, ACTION5-28, ACTION5-29, ACTION5-30.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-26 · Медиа, новости и технологические источники

Собирать разрешённые материалы, выделять утверждения и связывать их с первоисточниками.

Сценарий: Выбранный канал/материал → extract → claims → source check → draft.

Приёмка:
* GOAL5-26-AC1: Source snapshot, timestamp и claim/quote identity сохраняются.
* GOAL5-26-AC2: Пересказы одного источника не считаются независимым подтверждением.
* GOAL5-26-AC3: Контентный workflow возвращает документ/сценарий с источниками и coverage report.

Feature IDs: LIB-042, LIB-043, LIB-046, RND-036, RND-037, RND-038.

Milestones: M5-03, M5-09.

Открытые operational decisions: DEC5-16.

Новые уточнения задач: ACTION5-08.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-27 · Измерение пользы, стоимости и успеха

Выбирать автоматизацию по подтверждённому результату и полной цене попытки.

Сценарий: Baseline → campaign corpus → receipts → success/cost report → next priority.

Приёмка:
* GOAL5-27-AC1: Все начатые attempts, unknown, failures, repeats и human interventions входят в отчёт.
* GOAL5-27-AC2: Сравнение manual/no-action baseline и ablation использует фиксированный corpus.
* GOAL5-27-AC3: Порог принятия задаётся до experiment; proposals и measured results различаются.

Feature IDs: ACT-013, ACT-026, ACT-055, LIB-049, LIB-055, LIB-057, RND-014, RND-039, RND-040, RND-041, RND-045, RND-046.

Milestones: M5-08, M5-09, M5-10.

Открытые operational decisions: DEC5-05, DEC5-14, DEC5-21, DEC5-22, DEC5-23, DEC5-24.

Новые уточнения задач: ACTION5-05, ACTION5-28, ACTION5-29, ACTION5-30.

В этой карте нет текущего implementation evidence данной цели. Это не утверждение, что отсутствуют все исторические prototypes; перед разработкой сверить актуальный handler и criteria.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

## GOAL5-28 · Доставка продукта и понятное продолжение работы

Открыть один пакет, понять статус функций, следующий шаг и нужное действие.

Сценарий: ZIP → start → status/goal → one next task → verified increment.

Приёмка:
* GOAL5-28-AC1: Start page ведёт к актуальной стратегии и preserved history.
* GOAL5-28-AC2: Код, proposal, тест, installed release и пользовательская доступность имеют разные статусы.
* GOAL5-28-AC3: Следующий запрос содержит конкретный unmet goal и evidence gap.

Feature IDs: ACT-050, ACT-054, ACT-057, LIB-031, LIB-032, LIB-053, RND-001, RND-011.

Milestones: M5-01, M5-06, M5-10.

Открытые operational decisions: DEC5-01, DEC5-02, DEC5-18, DEC5-23.

Новые уточнения задач: ACTION5-01, ACTION5-02, ACTION5-11, ACTION5-12, ACTION5-18, ACTION5-21, ACTION5-26, ACTION5-27, ACTION5-30.

Подтверждённая узкая основа V4:
* ACT-057: Есть task resume и unknown receipt controls; общая панель кампании дальше.
* RND-001: Current SCE SHA и owners проверены; иные repo снимки остаются историческими.
* RND-011: Схема local-evidence явно отделяет CI/merge/install и semantic claim. Полная UpdateEvidence далее.

Остальная готовность остаётся открытой до exact source/build, criterion и нужного device/adapter receipt. V5 не повышает implementation status.

