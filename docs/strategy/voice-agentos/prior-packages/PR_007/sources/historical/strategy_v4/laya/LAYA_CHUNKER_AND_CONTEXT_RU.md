# Laya: весь репозиторий в связанных частях и локальный архив контекста

Дата стратегии: 2026-10-04. Этот раздел описывает дальнейшую разработку для общего ZIP. Локальная реализация V4 уже находится в SCE commit `5574ab768b39605d4631651a1e8f2451483344db`; её результат и проверки отражены в `implementation/STATUS.json` общего пакета. Этот commit имеет статус `LOCAL_UNPUBLISHED`: он не является новым опубликованным PR или подтверждением remote CI. Для данного раздела прочитан чистый checkout; сам анализ стратегии не добавлял изменений кода и не сканировал личный архив. Установленное подключение Laya/Grok этим разделом не заявляется. Функции ниже разделены на `IMPLEMENTED_EXISTING` — присутствуют в прочитанном коде — и `PLANNED` — предлагается реализовать. Проверка исходников не заменяет измерение на Windows или проверку установленного приложения.

Целевой первый результат: человек выбирает локальный репозиторий и нажимает «Подготовить репозиторий для AI». Приложение продолжает scan до конца, строит полный учёт файлов, раскладывает связанные исходники, тесты и контракты по частям, сохраняет общий индекс и показывает конкретный документ для выбранного чата. Повторное открытие приложения продолжает работу с сохранённого места. Позже тот же вход доступен голосом через Voice Agent OS/Laya.

«Один ZIP» здесь означает один переносимый комплект стратегии, статусов, происхождения и плана внедрения. Для огромного репозитория ZIP может содержать много небольших документов с единым manifest. Это не обещание поместить весь архив жизни в контекстное окно одной модели или установить все будущие функции одним действием.

## 1. Что уже есть и на что опирается разработка

| Статус | Возможность и фактическая граница | Источник в SCE |
|---|---|---|
| IMPLEMENTED_EXISTING | Полный учёт tracked-файлов pinned Git HEAD до обработки, сохранённый cursor, scan порциями; root выбирается operator profile | `content-lab/repo_context.py`: `start_scan`, `scan_page`, `get_snapshot` |
| IMPLEMENTED_EXISTING | Сохранение chunk bytes, размеров, диапазонов и хешей; проверка точного восстановления INDEXED blobs, включая пустые файлы | `repo_source.py`: `partition`; `repo_context.py`: `verify_roundtrip_db` |
| IMPLEMENTED_EXISTING | Python AST, статические импорты, unresolved-зависимости, компоненты сильной связности; JS/TS остаются `JS_TEXT_ONLY_NO_SYNTAX_CLAIM` | `repo_source.py`: `analyze`, `import_graph`, `components` |
| IMPLEMENTED_EXISTING | Выбор до 10 путей, Python dependency closure, предложение тестов по имени и нескольких явно заданных контрактов, экспорт очередной страницы | `repo_context.py`: `selection`, `export_request`; `library/repo-review-ui.mjs`: `export` |
| IMPLEMENTED_EXISTING | Неизменяемая review-сессия, исходная цель/scope/acceptance, проверка актуальности HEAD/index/байтов, импорт результата | `content-lab/context_review.py`; `content-lab/repo_context.py`: `verify_binding` |
| IMPLEMENTED_EXISTING | Сохранённая task, документ с хешем, журнал ручной передачи, импорт ответа, связывание с независимо перепроверяемыми локальными тестами | `content-lab/context_tasks.py`, `context_evidence.py`, `docs/automation/context-tasks.md` |
| IMPLEMENTED_EXISTING | Общие `items`, FTS и версии, namespace-scoped поиск актуальных heads и ограниченный context pack; версии ChatGPT export и выбранных записей библиотеки | `content-lab/content_lab.py`: `_insert_item`, `import_chatgpt_export`, `apply_library_record`; `automation_core.py`: `search`, `context_pack` |
| IMPLEMENTED_EXISTING | Ограниченный локальный intake и простые keyword topics; Laya request и voice proposals существуют как данные | `occ_local.py`: `inspect`, `TOPICS`; `occ-config/laya_request.example.json`; `occ_proposal.py` |
| PLANNED | Одна кнопка проводит все scan-порции, формирует единый manifest всего repo и очередь связанных документов | LAYA4-002, 008–010 |
| PLANNED | Квалифицированный JS/TS parser, общий граф модулей/тестов/контрактов, быстрый incremental reuse, каталог личного архива и подключённый Laya adapter | LAYA4-005–007, 011–018, 022 |

Существующий `occ_local` — intake staging, а не универсальный executor: в нём есть предел `MAX_SCAN=2000` и отдельные ограничения форматов. Он не должен подменять repo inventory из `repo_context`. Пример Laya request не доказывает, что Laya установлен, имеет действующий API или умеет обращаться к выбранной вкладке. Перед адаптером требуется локально обнаружить фактический интерфейс версии Laya и сохранить capability receipt.

Текущие численные границы: scan по умолчанию 20 entries; API scan принимает 1–100, UI вызывает одну порцию. Git enumeration ограничен 32 MiB вывода с явной ошибкой; blob — 8 MiB. Базовый chunk — 4096 bytes с сохранением UTF-8 code point. UI selection использует planning budget 24 000 bytes, до 10 text chunks на страницу и continuation offset. Native envelope входа ограничен 16 000 bytes, выхода — 192 000 bytes. Эти границы нельзя просто снять для «бесконечного контекста»: будущий batch хранит данные локально и передаёт ссылки/порции.

Документы `context-foundation.md` и `context-review-ledger.md` содержат исторические next steps. Для новых task/evidence функций приоритет имеет фактический код текущего SHA и `context-tasks.md`; старое «ещё не реализовано» сохраняется как исторический статус, а не переносится без сверки.

## 2. Кнопка «Подготовить репозиторий для AI»

Предлагаемый интерфейс начинается с четырёх полей: настроенный repo alias, цель, область работы и критерии результата. Быстрый вариант «обзор всего repo» задаёт область `tracked HEAD`, но просит модель исследовать конкретную цель: например карту функций, техдолг, архитектуру или план accessibility. Текст цели сохраняется дословно. Голосовой transcript и его исправление — разные версии с происхождением; приложение не исправляет историю задним числом.

После запуска выполняются следующие шаги:

1. Зафиксировать namespace, repo alias, HEAD/tree, profile revision, цель и критерии. Рабочие незакоммиченные изменения могут стать отдельным будущим snapshot kind; по умолчанию в tracked HEAD они не попадают.
2. Сохранить полный inventory. На экране сразу появляются total/accounted/pending/error/excluded, scope и SHA. При слишком большом Git output появляется конкретная ошибка, а не усечённый «успешный» список.
3. Последовательно продолжить `scan_page` в небольших транзакциях. В UI остаются Pause/Continue/Stop и доступный текст статуса. Повторные клики присоединяются к тому же run intent. Перезапуск использует прежний snapshot/cursor.
4. Вычислить статический граф с типами доказательств и собрать группы «владелец функции + контракты + вызывающие места + релевантные тесты». Неизвестные связи остаются видимыми.
5. Построить immutable batch manifest всех tracked entries и их disposition. Включить документы по группам, краткую карту, список пробелов и обратный индекс chunk → source range → group → packet.
6. Проверить manifest: ни одного неучтённого entry; у каждого экспортируемого байта ровно один основной raw-fragment; границы и hashes сходятся. Контекстные повторы в нескольких документах имеют `reference/repeated_context`, чтобы не выдавать их за дополнительные исходные байты.
7. Показать preview передачи: цель, recipient binding, категории данных, число частей, размер и причины исключения. Сохранить локально как ZIP/папку и подготовить текущий документ. Передача в выбранную вкладку принадлежит UI adapter из UI3, а не chunker.

На странице результата нужны пять независимых счётчиков: `учтено файлов`, `извлечено байт`, `упаковано частей`, `доставка подтверждена`, `критериев проверено`. 100% inventory не должно отображаться как 100% review или 100% готовности функции.

Первый полезный release этой кнопки не требует Laya-модели: deterministic scan и chunking должны работать напрямую через существующий backend. Laya добавляет удобный вход и планирование, а не обязательный model call на каждый файл. Быстрота подтверждается экспериментом на ПК, не словом «fastest» в UI.

## 3. Связанные части: граф, группы, порядок и manifest

Предлагаемый граф различает узлы `repo`, `file`, `symbol`, `test`, `contract`, `schema`, `goal`, `capability` и типы рёбер `imports_static`, `calls_static_candidate`, `tests_by_name`, `tests_observed`, `contract_declared`, `schema_reference`, `ownership_declared`, `dynamic_unresolved`. У каждого ребра есть source range/hash, parser version и evidence class. Эвристика имени теста не становится observed test coverage.

Для JS/TS сначала нужен изолированный parser spike: синтаксические деревья JS/TS/JSX/TSX, ESM/CommonJS, relative imports, package exports, workspace packages и tsconfig aliases. Точный набор поддерживаемых правил версии resolver публикуется в manifest. `import(expr)`, computed require, плагины и runtime DI отмечаются unresolved; код репозитория не импортируется, package scripts не запускаются ради построения графа. Выбор parser и его поставка требуют оценки dependencies, pins, licence, offline installation и Windows footprint, а не случайного добавления package.

Порядок групп: сначала описание проекта/контракты/точки входа, затем SCC в детерминированном порядке condensation graph, внутри группы owner перед зависимыми пояснениями и тестами. SCC — логическая группа; крупный цикл всё равно делится на bounded части. В каждой части остаются краткое описание группы, её part IDs и ссылки на недостающие соседи. Глобальный total и per-file mapping доступны независимо от порции.

Проектные файлы batch, пока не production schema:

| Файл | Содержимое |
|---|---|
| `BATCH.json` | batch ID, source manifest digest, scope, цель/revision, coverage policy, planner/parser versions, budgets |
| `REPO_MANIFEST.jsonl` | Один entry на tracked path: Git OID/mode/size, byte hash, state/reason, extractor/parser, chunks |
| `RELATIONS.jsonl` | Типизированные рёбра с provenance; unresolved рёбра учитываются отдельно |
| `GROUPS.json` | Стабильные group IDs, owners, members, tests/contracts, порядок и требуемые соседние группы |
| `PARTS_INDEX.jsonl` | part ID, document hash, bytes, source ranges, group ID, dependencies и inclusion purpose |
| `PARTS/…` | Ограниченные документы для AI; данные исходников отделены от инструкции задачи |
| `GAPS.jsonl` | Все exclusions/errors/missing/deferred/unsupported и условие восполнения |
| `RETURN_CONTRACT.json` | Идентичность задачи, packet digest, inspected parts, findings, missing context requests |
| `README.txt` | Как открыть индекс, отправить первую часть, запросить следующую и импортировать ответ |

Идентичность batch включает snapshot, goal revision, grouping/resolver versions и export policy. ID части не зависит от того, какой UI первым скачал её. История packet version и delivery attempt сохраняется отдельно от идентичности источника.

«Zero omission» для manifest означает `accounted == tracked_total` и наличие ровно одной записи disposition для каждого tracked path. `all_tracked_bytes_exportable` остаётся отдельным свойством. Binary/secret/excluded file может быть полностью учтён, но не передан AI. Нельзя требовать «ноль exclusions», чтобы скрытно начать передавать защищённые данные.

## 4. Ошибки и неполный источник

| Ситуация | Обязательное поведение |
|---|---|
| Git HEAD изменился во время scan | Сохранить прежний run как SOURCE_DRIFT; новый scan получает новый snapshot; не смешивать commits |
| Large blob или enumeration limit | Явная ошибка/metadata entry; будущий streaming implementation квалифицируется отдельно; нет молчаливого truncation |
| Binary или non-UTF8 | Raw bytes/hash могут сохраниться; текстовый pack отмечает omission. Извлечение текстовой версии получает собственный extractor и link на оригинал |
| LFS pointer | Учесть pointer как tracked bytes и отдельно `payload_missing`; не называть pointer полным содержимым большого файла |
| Submodule/symlink | Записать metadata/target; по умолчанию не обходить. Отдельно выбранный submodule — отдельный pinned source scope |
| Missing promisor blob | ERROR, без скрытого network fetch; отдельная операция получения объектов должна иметь собственный scope |
| Parser fail или неизвестная кодировка | Сохранить raw/text fallback, reason и missing graph coverage; не превращать сбой parser в «связей нет» |
| Нет места/падение процесса | Незавершённая транзакция откатывается; completed parts с хешами остаются; resume проверяет их до продолжения |
| Изменён canonical item/chunk/manifest | CORRUPT; rebuild из проверяемого исходника, без silent repair истории доказательств |
| Изменилась export policy | Новый share projection и digest; уже подготовленная передача старого projection перестаёт быть ready |

## 5. Инкрементальная работа и Windows 16 GB

Существующий delta показывает изменения и affected dependents для разрешённых Python static edges; это ещё не reuse parser cache. Следующая реализация должна использовать ключ `(raw_hash, parser_version, resolver_config_hash, extraction_policy_version)` для derived results. Неизменённый blob можно не парсить повторно; изменение resolver/roots инвалидирует graph interpretation даже при прежних байтах.

Инвалидация проходит отдельными связями: source revision → extraction → chunk/group → packet → interpretation/evidence. Изменение одного файла не обязано удалять весь архив. При изменении публичного контракта затронутые потребители получают `STALE/RECHECK_REQUIRED`; unresolved dynamic edge расширяет uncertainty, а не даёт ложное обещание минимального affected set. Rename сохраняет link на прежний источник, но не переписывает исторические path IDs.

Предлагаемый первый профиль Dell/Windows: один DB writer, один parser worker по умолчанию, максимум два read-only parser workers после замера, ограниченная очередь из 32 готовых fragments, постраничный UI, пакетные FTS writes. Workers возвращают предложения изменения индекса; транзакцию делает существующий owner. Текущий `Core.policy.max_parallel=1` не ослабляется этой стратегией: production parallel scheduler развивается отдельно по PAR3.

Не держать весь исходный архив и все embeddings в RAM. Raw bytes и большие результаты — на диске, индекс/метаданные — в существующем SQLite, hot cache ограничен. Token estimate отображает метод; byte count не выдаётся за точный provider token count. Сначала exact paths/FTS/graph retrieval, затем необязательный reranker с измеряемой пользой. GPU, новая модель или платный API для первой кнопки не требуются.

## 6. Каталог, журнал и контекст всей жизни

Единица источника должна отделять: оригинальные bytes; extraction/transcript; пользовательскую интерпретацию; модельное summary; действия и доказательства результата. Предлагаемые поля каталога: `source_id`, `source_revision`, `origin_kind`, `origin_locator`, `project_id`, `lifetime_scope`, `captured_at`, `source_event_at`, `extractor_version`, `raw_sha256`, `text_sha256`, `language`, `rights/share_profile`, `retention_policy`, `parent_refs`. Время события и время импорта не смешиваются. Неизвестное время остаётся null.

Для each capture сохраняется intent: «сохранить заметку», «источник для проекта», «история решения», «временный input», «семейный архив» или пользовательский тип. Это помогает выбирать, что искать и передавать позднее. Источник не становится глобально доступным всем автоматизациям из-за того, что один раз был импортирован.

Форматы развиваются по отдельным extractor cards: text/Markdown, Git, chat export, документы, PDF/OCR, аудио/transcript, images/vision, event/log exports. Unsupported attachment учитывается как запись с причиной. Любой OCR/ASR имеет model/tool version, ranges/timestamps, quality state и ссылку на оригинал. Автоматическая метка темы имеет автора/правило, version и evidence. Исправление пользователя хранится overlay и переживает переиндексацию. Метка `implemented` требует evidence владельца функции; слово «done» в переписке не выставляет её.

Нужны три вида поиска: точная цитата/ID/path; фильтры project/type/topic/date/status; смысловой поиск, если его добавление оправдал измеренный retrieval gain. Results показывают excerpt, origin, revision, freshness и почему результат найден. Timeline группирует conversation/project/goal events и позволяет открыть первоисточник. Каталог может включать частные личные записи, но repo request по умолчанию получает только выбранный project scope.

Dedup разделяется на exact bytes, одинаковое extraction и semantic similarity. Exact duplicate можно хранить один раз физически с несколькими origin refs. Семантически похожие записи не сливаются автоматически: они могут быть разными решениями или изменением взглядов. Удалённый current source и старые версии различаются; tombstone не должен случайно воскреснуть после reimport. Retention/delete policy описывает также raw, derived indexes, snapshots и резервные копии. Удаление локального контекста не утверждает удаление уже переданного внешнему сервису документа.

«Контекст всей жизни» реализуется как растущий локальный corpus, а не бесконечная память модели. Для задачи собирается bounded working set: исходная цель → project/time filters → exact/FTS hits → graph neighbours → проверяемое summary с raw refs → document parts. Связанные summaries образуют уровни day/project/episode/lifetime, но оригиналы сохраняются согласно policy. Любое summary обязано уметь раскрыться до supporting source ranges. Conflict, missing and uncertainty переходят в пакет вместе с summary. Модель может запрашивать дополнительные parts по manifest; запрос разрешается только внутри выбранного scope.

Контекстные журналы не дублируют полные приватные документы. Событие хранит IDs, revisions, actor/source, cause, previous/new state, digest, reason и evidence ref. Для диагностики полезны counts, latency, error code и scope; raw content читается через отдельный контролируемый просмотр.

## 7. Laya, Voice Agent OS и выбранная вкладка Grok Build

Предлагаемый Laya adapter принимает типизированное намерение, например `prepare_repo_context`, `find_context`, `compile_ai_packet`, `show_packet`, `request_more_context`, `inspect_result`. Он возвращает structured proposal и вызывает существующий owner через зарегистрированный интерфейс. Текст из repo/chat/doc остаётся данными; он не добавляет команды, разрешения, получателей или пути выполнения.

Рецепт «подготовь repo для Grok» после однократной настройки связывает repo alias, разрешённый data scope, цель, export profile, actual destination binding и нужный workflow version. Внутри этого уже согласованного scope приложение продолжает routine steps без повторных вопросов. Новая цель с другим repo/account/chat или более широким набором личных данных создаёт изменённый plan scope. Нельзя использовать один label `Grok Build` как доказательство, что выбран правильный чат.

Пользователь показывает приложению открытую вкладку Grok и отдельно GitHub/release destination. UI adapter сохраняет фактически проверяемое binding account/workspace/chat/tab plus revision, а не произвольные координаты. Chunker выдаёт ему неизменяемые parts. UI adapter последовательно подготавливает и доставляет parts, связывает наблюдаемые receipts с task. Если исход отправки неизвестен, новый send не выполняется вслепую; pending attempt восстанавливается из текущего чата. Эти задачи продолжают UI3-002–012, а LAYA4 не объявляет их реализованными.

Обратный путь: полученный результат → source/packet binding → код/PR artifact → проверка repo evidence → exact merged revision → отдельный staged update → проверки установленной версии → registry доступных capabilities. Фраза пользователя или Grok «merged» является сигналом начать наблюдение, а не доказательством новой установленной функции. Детали доставки и самообновления принадлежат UI3/EVO3; chunker снабжает их source manifests и пересобирает только затронутый контекст.

Доступность входит в первый UI: клавиатурный порядок, именованные controls, доступный live progress, отсутствие обязательного drag-and-drop, большой Stop, resume и объяснение проблемы простыми словами. Голос — альтернативный вход в тот же intent contract. Ошибка ASR не может незаметно поменять repository/destination. Управление должно оставаться доступным текстом, даже когда распознавание голоса или модель недоступны. Обещание «автоматизировать любое действие на ПК» заменяется расширяемым каталогом реально квалифицированных capabilities с честным статусом и конкретной областью действия.

## 8. Preview и экспорт для разных AI

Основной packet не зависит от Grok, ChatGPT или Gemini. Provider profile задаёт проверенные ограничения транспорта, способ вложения/пасты, размер части и ожидаемый return format. Не следует жёстко кодировать непроверенный лимит сервиса или выдавать echo prompt hash за server-byte verification.

Перед передачей пользователь видит исходные categories/projects, конкретные parts и разницу с прошлой версией. Raw local archive и share projection имеют разные IDs и retention. Секреты, protected names, содержимое другого проекта и private overlays не попадают в пакет только потому, что находятся рядом. Heuristic detection дополняет явный scope и preview: оно не считается гарантией нахождения всех секретов. Использование редактированной копии меняет share digest, а оригинал остаётся связанным через provenance без раскрытия скрытого текста.

Для большого архива первый документ содержит задачу, карту, критерии и manifest, затем отправляются требуемые связанные части. Если новая chat session нужна из-за ограничений окна, carry-over содержит проверенные decisions/open issues/source references и номер предыдущей сессии. Он не утверждает, что следующая модель уже прочитала всё. Доставка, claimed review и проверка критерия остаются разными уровнями.

## 9. Эксперименты и предлагаемые пороги

Все пороги ниже — **PROPOSED_NOT_MEASURED**. Они не описывают полученную скорость текущего приложения. До release нужен device receipt с CPU/SSD/RAM/OS, версиями кода/parser, corpus manifest и cold/warm режимом.

| Experiment | Набор и сравнение | Предлагаемый критерий перехода |
|---|---|---|
| LX4-01 Полнота | 2 005 и 10 000 tracked entries; пустые, binary, CRLF/BOM, ошибки, длинные пути | 100% entries имеют disposition; 100% INDEXED bytes восстанавливаются; 0 silent omissions |
| LX4-02 Restart | 100 остановок процесса на границах inventory/scan/part commit; сравнение с непрерывным run | 0 потерянных/лишних entries и частей; одинаковый итоговый digest при одинаковых версиях |
| LX4-03 JS/TS graph | 200 размеченных fixtures ESM/CommonJS/TS/JSX/aliases/workspaces/dynamic | 100% известных динамических случаев помечены unresolved; ≥98% precision поддерживаемых local-static edges; recall публикуется отдельно |
| LX4-04 Группировка | 30 задач: plain file order против owner+contracts+tests groups при одинаковом byte budget | ≥90% обязательных source refs присутствуют в top packet+explicit next refs; 0 непомеченных inference edges |
| LX4-05 Incremental | 1% source edits, rename/delete, parser/resolver update; сравнение с clean rebuild | Тот же semantic index/manifest; ≥80% неизменённых parse outputs reused; 0 stale outputs приняты как current |
| LX4-06 Windows бюджет | Dell 5400 16 GB, SSD, 10 000 files/250 MiB text, 1 и 2 workers | Peak RSS ≤1.5 GiB для backend; UI input p95 ≤200 ms; прогресс не реже 1 s; Pause/Stop acknowledged ≤2 s; total throughput записан без заранее объявленной скорости |
| LX4-07 Каталог | 100 000 source versions, 1 000 000 text chunks; 100 заданных exact/project queries | Warm search p95 ≤500 ms; ≥95% exact-source target в top 5; 0 cross-scope выдач; cold latency отдельно |
| LX4-08 Lifetime retrieval | 50 вопросов по четырём проектам и трём временным периодам | 100% фактических ответов имеют действующие source refs либо явную неизвестность; ≥90% необходимых источников в выбранном bounded set |
| LX4-09 Share projection | 100 fixtures с protected fields, mixed projects, пользовательскими исключениями и изменением policy | 0 известных запрещённых байтов в export; 100% policy changes меняют/revoke projection readiness |
| LX4-10 Accessibility | 10 сценариев keyboard-only; 10 с исправленным голосовым input; screen-reader review | 100% core actions доступны без мыши/голоса; 0 неверных repo/destination после corrections; Stop доступен во всех длительных состояниях |
| LX4-11 Multi-AI packet | Один manifest, три adapter profiles; ограничения на часть и carry-over | Source/goal identity сохранена; каждое omission учтено; 0 ложных delivered/read/verified статусов |
| LX4-12 Restore | Backup до/после migration; повреждённая часть, удалённый source, replay старого update | Восстановление hashes/versions, 0 stale resurrection; повреждение локализовано и явно показано |

Смысловая полезность AI оценивается отдельно от extraction correctness. В LX4-04/LX4-08 evaluator сравнивает найденные источники и реальные выполненные критерии, а не убедительность текста модели. Сначала запускаются deterministic fixtures, затем реальные пользовательские repo/архивы только в выбранной области. Увеличение corpus не должно автоматически включать external sends.

## 10. Порядок доведения до готовности

В `TASKS_LAYA4.json` находятся 28 карточек с зависимостями, конкретным результатом, критериями, recovery и требуемыми доказательствами. Все новые карточки имеют `implementation_status=PLANNED`. Они развивают G3/UI3/PAR3/EVO3, не меняя исторический статус старых записей.

| Стадия | Карточки | Пользовательский результат |
|---|---|---|
| L4-S0 Основание | 001 | Зафиксирован контракт владельцев и интерфейсов, воспроизводимое основание |
| L4-S1 Полный batch repo | 002–010 | Один запуск до полного inventory, связанные порции и ZIP с честными gaps |
| L4-S2 Быстрые изменения | 011–012 | Пересборка затронутых данных, cache и stale evidence |
| L4-S3 Локальный каталог | 013–018, 027 | Источники/метки/поиск/версии/retention/restore и bounded lifetime retrieval |
| L4-S4 AI и Laya | 019–025 | Preview, provider-neutral packets, вход голосом/текстом, scoped recipes и объяснимый запрос контекста |
| L4-S5 Квалификация и R&D | 026, 028 | Измеренный сценарий Windows и следующий brief по незакрытым целям |

Быстрейший первый usable slice: 001 → 002 → 004 → 008 → 009 → 010 → 019 → 020, с минимальным accessible path из 023 и квалификацией 026. Он использует нынешний Python graph; отсутствие JS parser остаётся явным gap. Полный JS/TS research slice добавляет 005–007. Установленный Laya adapter из 022 добавляется после уже работающей локальной кнопки. Прочие направления остаются в плане со своими условиями возврата, а не блокируют первый полезный результат.

Производственный критерий этого направления: на выбранном Windows-устройстве пользователь запускает подготовку, видит все учтённые файлы и пробелы, открывает нужную связанную часть, находит источник по цитате, получает документ для выбранного AI, переживает restart и может проверить происхождение любого вывода. Автоматическая отправка, merge и обновление приложения требуют своих receipts из UI3/EVO3; один удачный chunking run не закрывает эти этапы.
