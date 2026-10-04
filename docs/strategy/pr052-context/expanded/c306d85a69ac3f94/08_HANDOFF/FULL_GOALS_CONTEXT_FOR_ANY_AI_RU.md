V3 УТОЧНЕНИЕ: multi-producer recording и независимые effect resources параллельны. Single writer относится только к одному конфликтующему effect target. Главная схема: 00_START/00_PARALLEL_CAPTURE_DECISION_RU.md.

# Полный контекст целей и решений для следующего AI

Не полный транскрипт и не полный код репозиториев. Это агрегированные цели и design decisions из доступного чата/ZIP.



---
SOURCE_IN_PACK: 00_START/01_MASTER_PLAN_RU.md

# Voice AgentOS V2 — локальный компилятор контекста и безопасные параллельные маршруты

Дата: 3 октября 2026. Целевой пользовательский сценарий: личное приложение Windows 11, библиотека исходников/идей/кода и голосовой control plane для работы с выбранными AI и продолжения Studious-Pancake.

## Главное решение

Не «три агента одновременно меняют одну вкладку», а **несколько независимых путей подготовки → проверка → один эффект**.

```text
Голос / текст
    → версия намерения + область прав
    → pinned snapshot + критерии результата
    → выбор реально различающихся маршрутов
       ├─ exact source / symbols
       ├─ logs / measured execution
       └─ historical decisions / alternative candidate
    → независимый verifier
    → stop losers / confirm cancellation
    → повторная проверка target version и permissions
    → один effect broker
    → наблюдение результата / receipt / reconciliation
    → история и квалифицированный reusable skill
```

Имена API/MCP/PowerShell не определяют независимость. MCP — транспорт/контракт, а не отдельный источник корректности. Playwright и CDP могут управлять тем же Chromium. Несколько coding models могут повторять одну ошибку из общего context pack. Поэтому registry должен описывать общие зависимости и реальные co-failures.

## Три режима параллелизма

**Fan-out/fan-in:** несколько непересекающихся чтений нужны все. Пример: source, test trace, текущая requirement. Система объединяет evidence, не выбирает самый быстрый неполный ответ.

**Race-to-verified:** два разных кандидата решают один контракт. Не первый ответ, а первый результат, принятый независимым verifier. Для сложного patch «тесты прошли» — необходимое, но не достаточное условие; нужны bound task criteria и regression scope.

**Delayed hedge:** запасной read/candidate запускается лишь при превышении порога задержки или недостаточном evidence первого пути. Это кандидат на лучший speed/cost trade-off; выигрыш измеряется, а не обещается. Подход связан с tail-latency research [S01].

## Что никогда не гоняем наперегонки в общей среде

Публикация сообщения, GitHub merge, перевод средств, live trade, delete, DB migration, обновление прав, ввод в один foreground, команды с общим output directory/DB. Тесты тоже могут изменять files/DB или обращаться к сети: им нужны отдельные workspaces и проверенные ограничения.

Worktree — не sandbox [S04]. Browser context отделяет browser storage, но не последствия в одном remote account [S03]. Само имя действия read-only не делает недоверенный Python безопасным.

## Локальная библиотека без подмены полноты

Raw objects остаются исходниками. Chunks, summary, labels, embeddings и graphs — воспроизводимые представления. Каждый вывод связан с source URI, object hash, byte/message span, parser version и временем. Путь с переносом/переименованием не должен терять lineage.

Нет произвольного лимита на двадцать документов. Но конечные RAM/disk/API budgets остаются. Большие данные обрабатываются порциями с durable cursor, backpressure и явными error/exclusion records. Библиотека, индекс и один AI request имеют разные границы полноты.

Важный UI: `raw stored`, `indexed`, `selected for this pack`, `omitted with reason`. Кнопка «включить всё» не должна молча означать первые N документов. Полный repo export может состоять из томов с индексом, а рабочий handoff — из target slices и нужных зависимостей.

## Дополнительные intelligence layers

**Evidence deficit planner:** находит конкретно недостающий test trace, symbol, original decision или runtime observation. Он экономит вызовы модели, потому что запрашивает недостающий факт, а не увеличивает summary.

**Authority-aware labeling:** отличает голосовую команду пользователя от цитаты в webpage, AI-предложения, observed output и политики. Лейбл VERIFIED нельзя получить из слова «готово». Confidence — оценка извлекателя, не разрешение и не доказательство.

**Snapshot closure:** context pack связан с commit, actual dirty-file hashes, индексом и policy version. До применения нужно убедиться, что цель не изменилась. Это предотвращает работу хорошего патча по неверной базе.

**Conditional failure memory:** помнит «этот locator/adapter/version уже не работал» с условиями и сроком. Смена version вызывает requalification, а не вечную блокировку.

**Context optimizer:** сравнивает источники по полезности для verified outcomes. DSPy/GEPA — optional offline experiment [S11–S13], не автоматически принятая зависимость и не право модели переписывать production policy.

**Skill minimizer:** сокращает успешный workflow по повторным проверкам; не просто сохраняет длинную цепочку кликов. Больше использования должно уменьшать цену знакомой задачи, а не наращивать тысячи агентов.

## Самый короткий путь к полезности

Не начинать с universal visual agent и трёх тяжёлых локальных моделей. Первый вертикальный сценарий — **текст/голос → собрать handoff на текущую функцию Studious → показать кратко зачем → сохранить исходники/refs → импортировать ответ выбранного AI → проверить binding**.

После того как этот сценарий даёт measured benefit, добавить voice adapter к тому же IntentSpec, два альтернативных retrieval/candidate routes и single-effect broker. Затем новые навыки через isolated coding, verification и staged update. UI/vision — последний адаптер для задач без хорошего структурированного интерфейса.

На Dell стартовый эксперимент: один CPU-heavy worker, маленькое число concurrent model requests и background indexing с низким приоритетом. Это гипотеза для настройки, не измеренная оптимальная конфигурация. Никаких заявлений «33ms end-to-end» до измерений на устройстве. Карта Laya сама показывает зависимость качества/времени от checkpoint и input length [S06].

## Измерения вместо универсальных процентов

Для каждой категории задач фиксировать requested intent, supported/unsupported, attempted, verified outcome, blocked, failed, cancelled, unknown, false-success, human intervention. Публиковать coverage вместе с conditional success: иначе система может «улучшить процент», просто перестав делать сложные задачи.

Сравнивать serial / eager-parallel / delayed hedge при одинаковых input cases, resources и timeouts. Измерять p50/p95 time-to-verified и cost per verified success; включать failures/timeouts в отчёт. Co-failure и negative cases обязательны.

В абстрактном независимом примере P(хотя бы один успех) = 1 − произведение(1 − p_i). Если все пути зависят от одной плохой библиотеки/ошибочной команды, это вычисление неприменимо. Число агентов не гарантирует большую вероятность правильного результата.

## Что реально выполнено в этом ZIP

Сохранён исходный ZIP и его 8 файлов. Составлены 32 требования, 24 дополнительные R&D карточки (всего 42 с прежними), 20 workflow specs и 225 уникальных proposed functions (129 прежних + 96 новых). Проверены первичные документы S01–S19 и прочитаны 3 repo-документа.

Небольшой offline lab демонстрирует byte-preserving source store, bounded context с omissions, delayed read/candidate race, independent verifier и idempotent single SQLite commit. 41 unit test прошёл в среде сборки. Это не desktop app, не Windows qualification и не готовая Laya интеграция. API, микрофон, реальные repo tests, browser control и trading не запускались.

Полных исходных ChatGPT/Grok/Telegram/Google Docs архивов здесь нет. Цели текущего чата собраны в реестр; старый ZIP сохранён byte-for-byte. Полный transcript или «вся жизнь без потерь» этим пакетом не заявляются.


---
SOURCE_IN_PACK: 01_CONTEXT/ALL_AIMS_AND_GOALS_RU.md

# Цели и ограничения чата

Реестр требований, а не утверждение о выполнении. Anchors — короткие цитаты или явно помеченные пересказы, не полный транскрипт.

## REQ-001 — Локальное личное приложение
Windows 11; библиотека и control plane локальны, не обязательный SaaS.

Источник: CURRENT_CHAT; anchor: local application

## REQ-002 — Голос и текст равноправны
Оба входа формируют один IntentSpec; фоновые голоса не считаются приказом.

Источник: CURRENT_CHAT; anchor: via text or or via your voice

## REQ-003 — Любой выбранный AI
Provider-neutral пакет + adapters; не привязывать память к Grok/OpenAI.

Источник: CURRENT_CHAT; anchor: for your AI of choice

## REQ-004 — Сохранение исходников
Raw bytes не заменяются summary/chunks; пути, IDs, время и источник сохраняются.

Источник: CURRENT_CHAT; anchor: entire history of my life

## REQ-005 — Нет лимита двадцати документов
Порции и бюджеты регулируют обработку; не скрывают хвост библиотеки.

Источник: RETRIEVED_PRIOR_USER_CONSTRAINT; anchor: more than 20 max docs remove

## REQ-006 — Семантический repo context
Repo map, symbols, dependencies, tests и history вместо ручной нарезки пользователем.

Источник: CURRENT_CHAT; anchor: this application could to chunk it

## REQ-007 — Несколько источников
ChatGPT/Grok exports, Google Docs exports, разрешённые private Telegram exports, Git.

Источник: CURRENT_CHAT; anchor: entire private Telegram channels

## REQ-008 — Library UI
Поиск, теги, граф целей, timeline, выбор исходников, completeness/omissions.

Источник: CURRENT_CHAT; anchor: library like Notion local application

## REQ-009 — Терминал и VS Code
Только зарегистрированные операции с рабочим проектом и областью файлов.

Источник: RETRIEVED_PRIOR_USER_CONSTRAINT; anchor: local terminal ... vs code

## REQ-010 — Документы для передачи AI
Короткое объяснение WHY_THIS_PACKET + полные ссылки на evidence + ожидаемый patch/test response.

Источник: CURRENT_CHAT_RU_PARAPHRASE; anchor: why this document should be passed to another AI

## REQ-011 — Продолжение Studious
Qualification/evidence/patch triage для BobIvans/studious-pancake. Не считать план действующим ботом.

Источник: CURRENT_CHAT; anchor: continue to work on our Studio Spancake flashloan bot

## REQ-012 — Восстановление решений
Старое предложение != новая команда; decision lineage/supersedes и даты.

Источник: CURRENT_CHAT; anchor: previous goals ... aggregated

## REQ-013 — Новая способность через код
Voice → context → AutomationSpec → coding agent → branch → tests → GitHub review → local skill update.

Источник: CURRENT_CHAT; anchor: renew the local application, renew the capabilities

## REQ-014 — Параллельные пути одной задачи
Диверсифицированные read/draft candidates; одна точка эффектов, independent verification.

Источник: CURRENT_CHAT; anchor: parallel actions would execute on same automation

## REQ-015 — Скорость и стоимость
Короткий fast path, delayed hedges, caching, budgets; не безусловный запуск всех моделей.

Источник: CURRENT_CHAT; anchor: fastest route to those aims

## REQ-016 — Подготовка во время речи
Только разрешённый read-only prefetch по устойчивой части транскрипта.

Источник: CURRENT_CHAT; anchor: lowest possible time

## REQ-017 — Измеряемая успешность
Verified completed / attempted, false-success отдельно; никаких обещаний 100% arbitrary GUI.

Источник: CURRENT_CHAT; anchor: highest sucess rate on execution

## REQ-018 — Безопасные маршруты
Не дублировать публикации/merge/удаления/trading; unknown effect требует reconciliation.

Источник: CURRENT_CHAT; anchor: multiple safe routes

## REQ-019 — Права не выдаёт модель
Typed route/LLM plan не расширяет scope; секреты остаются вне handoff.

Источник: ASSISTANT_PROPOSED_SAFETY_BOUNDARY; anchor: safely ... permissions

## REQ-020 — Accessibility-first
Stop/undo/correction/voice status; пользователь имеет приоритет над GUI worker.

Источник: CURRENT_CHAT; anchor: people with disabilities

## REQ-021 — Приватность
Локальный capture opt-in; public/private/sensitive, field-level cloud-export approval.

Источник: CURRENT_CHAT; anchor: hold any data locally

## REQ-022 — API budget
Провайдеры настраиваются по key references и явному лимиту расходов; ключи не включать в ZIP.

Источник: CURRENT_CHAT; anchor: use my api key

## REQ-023 — Evidence truth
Не путать source_fact, model_claim, implementation, tests, installed qualification, real market evidence.

Источник: DERIVED_ACCEPTANCE_CRITERION; anchor: highest successful ... execution

## REQ-024 — Без обязательного расширения
Desktop — основной интерфейс; Chrome может быть управляемым приложением/optional adapter.

Источник: RETRIEVED_PRIOR_USER_CONSTRAINT; anchor: remove wire to chrome extensions

## REQ-025 — Daily workflows
Повторяемые планы/исследования/документы/квитанции; расписания не стартуют от импорта.

Источник: CURRENT_CHAT; anchor: executions I need to do daily

## REQ-026 — R&D технологий
GitHub/Hugging Face/X разведка, первичные источники и локальные сравнения.

Источник: CURRENT_CHAT; anchor: new technologies ... hugging face

## REQ-027 — Вопрос о каталоге ChatGPT
Отдельный опциональный путь публикации; точная иконка неизвестна.

Источник: CURRENT_CHAT_RU_PARAPHRASE; anchor: insert a link to your service

## REQ-028 — Пакет продолжения
Два стартовых RU документа, JSON work items/workflows, tested offline reference.

Источник: CURRENT_CHAT; anchor: agregate bigger zip

## REQ-029 — Сохранить предыдущие идеи
18 прежних R&D и 129 функций остаются в legacy с происхождением и статусом.

Источник: CURRENT_CHAT; anchor: this entire chat aims and goals you outlined

## REQ-030 — Не заявлять недоступные данные
Исходный ZIP сохранён; более ранние архивы/полные приватные истории не получены здесь.

Источник: SCOPE_BOUNDARY; anchor: go thourgh our ideas and my inputs

## REQ-031 — Один владелец runtime
SCE Core/content.sqlite остаются owners; Studious владеет qualification, voice/Laya advisory.

Источник: RETRIEVED_PRIOR_DECISION_UNVERIFIED_IMPLEMENTATION; anchor: one evolving context/automation library

## REQ-032 — Прогрессивная полнота
Inventory/cursor/coverage/explicit exclusions; retrieval budget не ограничивает хранение.

Источник: CURRENT_CHAT; anchor: aggregate any context, any data

---
SOURCE_IN_PACK: 02_RESEARCH/NEW_RND_DIRECTIONS_RU.md

# 24 дополнительных направления

18 прежних направлений сохранены без потерь в `10_LEGACY`; здесь RND-19…42. Три карточки явно являются усилением обсуждённых идей, а не полностью новой темой.

## RND-19 — Failure-domain diversity
Не путать три обёртки pytest с тремя независимыми страховками.

Эксперимент: Сравнить 3 обёртки одного пути с 2 реально разными источниками evidence на fault-injection corpus.

Приёмка: Записать co-failure matrix и marginal recovery каждого маршрута; не выводить независимость из названия инструмента.

## RND-20 — Adaptive hedging
Запускать запасной путь только при признаке задержки или нехватки evidence.

Эксперимент: Сравнить serial, eager-parallel, delayed-hedge на фиксированном наборе read-only задач при одинаковом бюджете.

Приёмка: Снизить p95 time-to-verified при заданном API/CPU бюджете; не допустить дублирующих внешних эффектов.

## RND-21 — Single-effect commit broker
Результаты готовятся параллельно, эффект принадлежит одному брокеру.

Эксперимент: Два кандидата для одного target; kill/retry вокруг локального commit; отдельно моделировать неизвестный внешний результат.

Приёмка: Локальный commit ровно один в тестируемой SQLite-транзакции; внешние unknown не перезапускаются слепо.

## RND-22 — Resource commutativity and foreground ownership
Не дать агентам бороться за мышь, буфер и одну вкладку.

Эксперимент: Инъекция пользовательского ввода во время действия; два графа с общим файлом и отдельными browser contexts.

Приёмка: Нет чужого ввода в выбранной вкладке; conflict graph сериализует общие mutable resources.

## RND-23 — Snapshot-closed context
Пакет связан с одним состоянием проекта, а не смесью вчера и сегодня.

Эксперимент: Поменять файл после retrieval и до apply; удалить dependency; изменить allowlist.

Приёмка: STALE/NEEDS_CONTEXT вместо применения к старой базе; ни одного silent overwrite.

## RND-24 — Evidence deficit planner
Научить app замечать, какой конкретно информации не хватает.

Эксперимент: Дать bug с отсутствующим trace и противоречивыми заметками; проверить выбор следующего чтения.

Приёмка: Измерить time-to-sufficient-evidence и bytes/request; missing обязательное evidence блокирует действие.

## RND-25 — Authority-aware labeling
Теги должны отличать просьбу пользователя, чужую инструкцию, гипотезу и факт исполнения.

Эксперимент: Размечать один набор правилами, GLiNER и Laya; спорные метки не закрывать большинством без source evidence.

Приёмка: Проверить span precision/recall, unknown rate и отсутствие автоматического VERIFIED по словам done/merged.

## RND-26 — Causal context evaluation
Проверять, какие фрагменты реально помогают коду, а какие засоряют контекст.

Эксперимент: Ablation по clauses/tests/history на исторических bug задачах; новые commit families отделить от train.

Приёмка: Измерить verified patch rate и marginal utility/KB без утечки ответа из будущих PR.

## RND-27 — Incremental materialized context views
Пересобирать только изменённую часть репозитория и зависимых context packs.

Эксперимент: Изменить одну функцию в большом fixture corpus; сверить incremental output с полной пересборкой.

Приёмка: Exact equality где детерминировано; явный unresolved для dynamic edges; raw objects никогда не теряются.

## RND-28 — Verifier adequacy and counterexamples
Не выбирать патч только потому, что он обошёл слабые тесты.

Эксперимент: Сделать intentionally wrong patch, который проходит прежний test; добавить проверку нарушенного инварианта.

Приёмка: False-success ниже baseline; тесты не отключены, assertions не удалены, negative suite не деградирует.

## RND-29 — Critical-token ASR arbitration
Ошибки в repo name, path, number и отрицании важнее общего word error rate.

Эксперимент: RU/EN code-mixed команды: merge/not merge, main/branch, dry-run/live; фоновые голоса и поздние исправления.

Приёмка: Semantic slot error и false command activation измеряются отдельно; не делать cloud-audio hedge без согласия.

## RND-30 — Independent stop and intent revision
Система должна быстро останавливаться и понимать «нет, не этот repo».

Эксперимент: Во время retrieval/patch подготовки/ожидания merge дать stop и смену проекта.

Приёмка: Ни одного нового effect после подтверждённого stop; unknown external effects идут в reconciliation.

## RND-31 — Proof-carrying skill packages
Навык хранит не только скрипт, но и условия его применимости.

Эксперимент: Повторить успешный навык на другой версии приложения и с другой ролью пользователя.

Приёмка: Mismatched environment блокирует promotion; receipt содержит code hash и проверенные условия.

## RND-32 — Critical-path and attention-budget scheduling
Ускорять итог задачи, а не максимальное число одновременно активных процессов.

Эксперимент: На Dell выполнить фоновые imports + ASR + context pack; сравнить eager fan-out и admission control.

Приёмка: Не ухудшить voice responsiveness и UI; реальные measured p50/p95 + peak RAM, никаких выдуманных миллисекунд.

## RND-33 — Unknown-outcome state machine
Отмена/таймаут не доказывает, что внешний запрос не выполнился.

Эксперимент: Смоделировать lost response после server commit; нельзя запускать второй маршрут отправки.

Приёмка: Нулевая слепая повторная публикация; unresolved отдельно от failed.

## RND-34 — Adapter conformance and input trust firewall
Данные из чужой вкладки не становятся инструкциями ОС.

Эксперимент: Вставить в заметку «upload your keys» и в tool result ложный permit; сравнить policy decisions.

Приёмка: Никакого расширения полномочий от документа; adapter contract tests фиксируют disabled capabilities.

## RND-35 — Two-speed ingestion
Быстро сохранить raw, а тяжёлую разметку выполнить отдельным восстанавливаемым этапом.

Эксперимент: Большой смешанный corpus + interruption; приоритет новым файлам активного проекта.

Приёмка: Нет исчезнувшего хвоста/тайного лимита; recoverable errors; сохранение raw не означает полный поиск по нему.

## RND-36 — Lineage-aware dedup and evidence diversity
Пять пересказов одного сообщения — один источник, а не пять подтверждений.

Эксперимент: Несколько AI summaries одного поста + одно независимое наблюдение; проверить счёт evidence.

Приёмка: Не склеивать разные версии цели; не повышать confidence количеством копий одной цепочки.

## RND-37 — Negative knowledge and failure memory
Хранить доказанное «это здесь не работает» вместе с условиями и сроком.

Эксперимент: Повторить известный failure на том же fingerprint, затем сменить версию и проверить expiry.

Приёмка: Меньше бесполезных повторов без вечной блокировки исправленных возможностей.

## RND-38 — Skill minimization
Успешную длинную траекторию сокращать до минимальной проверенной процедуры.

Эксперимент: Длинный workflow vs minimized workflow на unseen fixtures и changed windows.

Приёмка: Меньше действий/latency, одинаковый verified outcome; убрать шаг нельзя только по мнению LLM.

## RND-39 — Permission-diff aware updater
Обновление функции не даёт автоматически новые права на весь компьютер.

Эксперимент: Кандидат просит новый filesystem root/network host; параллельно тест и attestation; activation должен остановиться.

Приёмка: Никакого privilege creep; несовместимая DB migration требует отдельного плана.

## RND-40 — Cross-AI exchange contract
Отправлять моделям один task contract, а не одинаково весь личный архив.

Эксперимент: Два model adapters + manual exported document; импорт неправильного snapshot и test claim.

Приёмка: Одинаковая target binding; private data не уходит неразрешённому provider; imported DONE не закрывает задачу.

## RND-41 — Capability drift monitoring
Навык теряет валидность после обновления сайта, инструмента или модели.

Эксперимент: Изменить locator/API field/tool schema и проверить fast demotion старого skill.

Приёмка: Нельзя продолжать по устаревшему cached capability; отдельные receipts для platform qualification.

## RND-42 — Offline context-and-skill optimizer
Улучшать способы собирать контекст по результатам, не добавляя бездумно больше текста.

Эксперимент: Одинаковый набор задач для baseline и learned context policy; reject reward hacking и критические regression.

Приёмка: Promotion только по held-out verified outcomes, без изменения permissions и production policy.

---
SOURCE_IN_PACK: 04_WORKFLOWS/PARALLEL_EXAMPLES_RU.md

# 20 примеров параллельных автоматизаций

Параллельны чтения и изолированные кандидаты. После проверки эффект один; строки ниже не запускают ПК, API или торговлю.

## WF-01 — «Собери контекст для исправления функции»
Путь A: Search exact symbols and call sites.

Путь B: Retrieve relevant failing-test traces.

Путь C: Retrieve source-bound historical decisions.

Объединение: `join_required_evidence`.

Один итог: Один review/handoff pack.

Проверка: Pinned source hashes, обязательные refs, coverage/omissions, короткий WHY_THIS_PACKET.

Fault test: Поиск быстрее завершился без нужного test trace.

## WF-02 — «Пусть два AI предложат исправление одной ошибки»
Путь A: Prepare patch in workspace A from same base.

Путь B: Prepare patch in workspace B from same base.

Путь C: Independent invariant/counterexample verifier.

Объединение: `race_to_verified_candidate`.

Один итог: Один принятый patch candidate; merge только отдельным разрешённым действием.

Проверка: Patch target binding, failing test reproduction, regression, untouched permissions/tests.

Fault test: Первый patch прошёл слабый test, но нарушил независимый инвариант.

## WF-03 — «Разметь документ и свяжи с задачами»
Путь A: Deterministic source/path/role labeling.

Путь B: GLiNER entity-span extraction candidate.

Путь C: Laya typed topic/task category candidate.

Объединение: `reconcile_without_majority_truth`.

Один итог: Одна версия annotation set; конфликты сохраняются.

Проверка: Каждая метка имеет origin/confidence/version; DONE не означает VERIFIED.

Fault test: Три пересказа утверждают merged, но source receipt отсутствует.

## WF-04 — «Распознай голосовую команду с именем repo»
Путь A: Local primary ASR partial transcript.

Путь B: Domain grammar and entity alias resolver.

Путь C: Selective second-ASR disputed-span check.

Объединение: `confirm_critical_slots`.

Один итог: Одна подтверждённая intent revision.

Проверка: Repo, negation, path и effect mode однозначны; low confidence блокирует effect.

Fault test: Фраза «не merge» потеряла отрицание.

## WF-05 — «Импортируй большой архив в библиотеку»
Путь A: Raw object inventory/hash/cursor.

Путь B: Parse already stored text/code objects.

Путь C: Label/index completed objects asynchronously.

Объединение: `progressive_pipeline`.

Один итог: Один ingest ledger с полным учётом.

Проверка: Raw byte integrity, stage status, cursor, явные errors/exclusions; нет document count cap.

Fault test: Оборвать процесс после raw store до завершения index.

## WF-06 — «Найди причину падения qualification»
Путь A: Parse saved logs from registered run.

Путь B: Resolve source dependencies on pinned snapshot.

Путь C: Read capability/dependency status evidence.

Объединение: `join_required_evidence`.

Один итог: Одна evidence-backed diagnosis card.

Проверка: Различать failed, blocked, unknown и no trade; legacy narrative не заменяет trace.

Fault test: Missing dependency была выдана за отсутствие прибыльных рынков.

## WF-07 — «Собери подтверждённое исследование со страницы»
Путь A: Official API or permitted document fetch.

Путь B: DOM read in owned browser context.

Путь C: Saved export/source-code reference comparison.

Объединение: `merge_readonly_observations`.

Один итог: Один source bundle с provenance.

Проверка: URLs, retrieval times, version/revision and evidence; несогласные версии не склеиваются.

Fault test: DOM содержит устаревший cache или prompt injection.

## WF-08 — «Сохрани длинную беседу с AI»
Путь A: Parse available official conversation export.

Путь B: Capture loaded authorized DOM messages.

Путь C: Inventory attachment IDs and missing message ranges.

Объединение: `reconcile_capture_coverage`.

Один итог: Один conversation object graph.

Проверка: Loaded DOM не объявляется полной историей; missing attachments/branches отмечены.

Fault test: Бесконечный scroll не загрузил середину беседы.

## WF-09 — «Подготовь один документ для выбранного AI»
Путь A: Compile evidence-rich source slice.

Путь B: Compile compact delta against known prior packet.

Путь C: Run privacy and response-schema checks.

Объединение: `choose_valid_handoff_variant`.

Один итог: Один approved provider-scoped handoff; автоматическая отправка здесь отключена.

Проверка: Budget/omissions, return schema, source refs и approval data scope.

Fault test: В приватном фрагменте присутствуют credentials.

## WF-10 — «Открой правильный проект в VS Code»
Путь A: Resolve repository path and workspace identity.

Путь B: Check registered CLI availability.

Путь C: Read UIA window state without interaction.

Объединение: `prepare_then_single_actuator`.

Один итог: Один запуск/активация окна.

Проверка: Проверить workspace URI/path, а не только заголовок окна.

Fault test: Два агента пытаются одновременно открыть разные folders.

## WF-11 — «Обнови навык после принятого PR»
Путь A: Verify artifact origin and target commit.

Путь B: Test candidate in isolated allowed environment.

Путь C: Compare capability/permission and data-schema diff.

Объединение: `all_gates_then_single_activation`.

Один итог: Одна activation на проверенный version ID.

Проверка: Permission expansion требует approval; migration/rollback отдельно проверены.

Fault test: Артефакт с правильным именем собран с чужого commit.

## WF-12 — «Составь ежедневный план продолжения»
Путь A: Read current repo state and saved failures.

Путь B: Resolve active user goals and superseding decisions.

Путь C: Read durable job receipts and outstanding blockers.

Объединение: `join_active_goal_evidence`.

Один итог: Один план с action proposals, без автоматического старта.

Проверка: Не возвращать superseded задачу; source/ref на каждый пункт.

Fault test: Старый AI summary предлагает уже отменённую архитектуру.

## WF-13 — «Останови текущую автоматизацию»
Путь A: Revoke active intent generation.

Путь B: Ask workers to stop and verify termination.

Путь C: Reconcile already-dispatched effect status.

Объединение: `parallel_stop_observe`.

Один итог: Одна итоговая stop receipt.

Проверка: Не обещать rollback необратимого; новые эффекты после stop запрещены.

Fault test: Запрос ушёл удалённому сервису до отмены.

## WF-14 — «Запусти проверку проекта без лишних дублей»
Путь A: Validate runtime/dependency environment.

Путь B: Select changed-symbol test subset.

Путь C: Read baseline receipts and choose independent invariant checks.

Объединение: `join_preflight_then_budgeted_tests`.

Один итог: Один registered test job per worktree/environment.

Проверка: stdout/stderr/exit code/base SHA/env fingerprint; wrapper≠independent test.

Fault test: PowerShell и MCP указывают на один сломанный Python.

## WF-15 — «Покажи влияние изменения одной функции»
Путь A: AST/local symbol analysis.

Путь B: SCIP/LSP references from approved indexer.

Путь C: Runtime coverage/error trace mapping.

Объединение: `merge_typed_graph_edges`.

Один итог: Один typed impact graph.

Проверка: Observed/static/heuristic/unresolved edges разделены; affected tests не заявлены исполненными.

Fault test: Dynamic import отсутствует в статическом call graph.

## WF-16 — «Найди обещанные, но не реализованные функции»
Путь A: Extract requirements from selected planning docs.

Путь B: Read code symbols and registered capabilities.

Путь C: Read exact-head test/installed evidence receipts.

Объединение: `requirements_evidence_reconciliation`.

Один итог: Один gap report и scoped next-change packet.

Проверка: CODE_PRESENT, TESTED, INSTALLED_VERIFIED различаются; document claim не evidence.

Fault test: Ранее assistant утверждал full merge по плану, но подтверждений нет.

## WF-17 — «Разреши противоречие двух старых решений»
Путь A: Find original user messages and timestamps.

Путь B: Trace quote/summary lineage.

Путь C: Read current implementation-related evidence.

Объединение: `authority_temporal_reconciliation`.

Один итог: Одна новая decision record с явной unresolved веткой.

Проверка: User intent и implementation fact не смешиваются; uncertainty сохраняется.

Fault test: Новая копия старой заметки ошибочно считается новым решением.

## WF-18 — «Повтори знакомый workflow быстрее»
Путь A: Reuse version-qualified compiled skill.

Путь B: Prepare a source-checking fallback route.

Путь C: Run independent current-state verifier.

Объединение: `delayed_hedge_then_single_effect`.

Один итог: Один результат при актуальном environment fingerprint.

Проверка: Нет повторной генерации кода для известной способности; stale skill quarantined.

Fault test: Сайт изменил поле/selector после последнего успеха.

## WF-19 — «Работай, пока я использую Chrome»
Путь A: Read local indexes without focus.

Путь B: Prepare drafts in isolated owned browser/workspace.

Путь C: Check user foreground/clipboard activity.

Объединение: `resource_partitioned_execution`.

Один итог: Background read/preparation; GUI input по единой аренде.

Проверка: Не перехватывать пользовательский ввод; browser context не sandbox удалённого аккаунта.

Fault test: Пользователь начинает печатать во время агентского шага.

## WF-20 — «Продолжи R&D flashloan без live-операций»
Путь A: Read documented capability/dependency state.

Путь B: Analyse explicitly recorded market fixtures.

Путь C: Generate test/evidence/patch handoff candidates.

Объединение: `offline_evidence_join`.

Один итог: Один R&D пакет; signer/sender не подключены.

Проверка: Synthetic, historical и real observed market evidence разделены; live_authorized=false.

Fault test: Агент предлагает включить live вместо исправления missing dependencies.

---
SOURCE_IN_PACK: 00_START/02_NEXT_IMPLEMENTATION_RU.md

# Следующая реализация: 8 work items, не номера существующих PR

Сначала прочитать current code/exact commit. Документы репозитория уже указывают на существующие owners — повторно не создавать queue/store. В этом выполнении ветки, PR, merge не создавались.

## CTX-PAR-01 — Preserve existing owners + trustworthy context intake
Подключить desktop client к existing SCE service owner, не создавать вторую queue/database. На pinned current source проверить documented scan/export caps; добавить streaming progress/coverage/error ledger.

Приёмка: Raw bytes и provenance survive restart; more-than-20 не обрывается; no scanned code execution.

Связи: RND-23 RND-27 RND-35.

## CTX-PAR-02 — Goal-bound handoff and labeling
IntentSpec из текста, evidence requirements, authority-aware tags и provider-neutral HandoffBundle. UI показывает краткое WHY_THIS_PACKET, sources и omissions.

Приёмка: Required missing evidence возвращает NEEDS_CONTEXT; приватные источники не уходят provider без scope.

Связи: RND-24 RND-25 RND-36 RND-40.

## CTX-PAR-03 — Read/candidate races with real diversity
Failure-domain registry, serial/eager/hedged comparator, budgets и cancellation receipts. Вначале только чтение и подготовка artifacts.

Приёмка: First invalid answer rejected; co-failure recorded; loser cancel confirmed; deadline не приводит к effect.

Связи: RND-19 RND-20 RND-32.

## CTX-PAR-04 — Effect broker and resource ownership
Target revision, operation ID, single writer, leases/fencing and unknown-effect reconciliation. Existing Core must remain authority.

Приёмка: Same intent duplicate produces one local effect; external unknown не повторяется вслепую; foreground user wins.

Связи: RND-21 RND-22 RND-30 RND-33.

## CTX-PAR-05 — Studious evidence vertical
Registered inspection/test adapter, source-bound failure triage, exact-head evidence, независимые fix criteria. Не интегрировать signer/sender.

Приёмка: Одна команда создаёт проверяемый failure/context handoff; не выдает fixture/test green за market qualification.

Связи: RND-23 RND-24 RND-28 RND-37.

## CTX-PAR-06 — Voice and accessibility adapter
Push-to-talk/optional wake + critical-slot checks, separate stop path, live command preview, RU/EN project aliases.

Приёмка: Same typed input contract as text; false activation/negation errors measured; installed Dell receipt captured.

Связи: RND-29 RND-30.

## CTX-PAR-07 — Safe skill factory and updater
Unknown action → isolated candidate code → independent tests → reviewable package → permission diff → staged activation.

Приёмка: First run may use coder, known replay uses qualified skill; new permissions never auto-granted; no core overwrite while running.

Связи: RND-31 RND-38 RND-39 RND-41.

## CTX-PAR-08 — Offline optimization and portfolio learning
Контекстные ablations, skill minimization, held-out evaluation DSPy/GEPA candidates. Реальные traces снабжают offline optimizer.

Приёмка: No holdout leakage; promotion only on verified outcomes and unchanged policy constraints; rollback retained.

Связи: RND-26 RND-38 RND-42.

## Что отдавать coding AI первым
Первое изменение должно сделать рабочим только выбранный вертикальный сценарий. Не нужно одновременно добавлять Temporal, Graphiti, LanceDB, UFO, 5 моделей и новый shell runtime. 225 функций в backlog — карта возможностей, не требование создавать 225 пустых wrappers.

Документ `08_HANDOFF/FIRST_DOCUMENT_TO_ANY_AI_RU.txt` содержит scope и требования к ответу. В контекст следующей модели добавить исходный код exact snapshot, а не только этот план. Отсутствующий код должен вернуть NEEDS_CONTEXT, не придуманную реализацию.


---
SOURCE_IN_PACK: 07_EVIDENCE/KNOWN_CORRECTIONS_RU.md

# Исправления и уточнения предыдущих ответов

1. PowerShell, MCP и OpenHands могут запускать один и тот же pytest/Python. Это не три независимых метода проверки. Нужен реестр failure domains и diversity по underlying dependencies.
2. CDP и Playwright не должны одновременно нажимать в одной вкладке. Browser contexts [S03] изолируют browser session, но не один внешний аккаунт. Нужны foreground/resource leases и один write actor.
3. Majority/consensus нескольких AI не является verifier. Патч/вывод подтверждается task-specific evidence и независимыми checks.
4. Транзакционный откат для «любого действия» не существует как универсальная гарантия. Локальный SQLite commit в lab атомарен; публикации, платежи и внешние side effects требуют idempotency/reconciliation [S02].
5. 33ms Laya не гарантия всей voice pipeline и не замер Dell. Model card [S06] описывает ограничения/разную accuracy; small typed router не идеальный classifier.
6. Task/skill formats нельзя считать автоматически доступными в любом AI web tab. MCP extensions проверены в current specification [S16], поддержка negotiated per client.
7. Полный static call graph не следует из Tree-sitter AST. В SCE документировано Python/static и JS TEXT_ONLY; unresolved edges должны оставаться видимыми.
8. «20 entries» в SCE docs — scan page size, не общий library cap. Но другие explicit size/export caps есть и требуют streaming migration, а не удаления safety checks.
9. CI green, model DONE, build attestation, installed qualification и live market result — разные evidence types. Bot README прямо описывает ограничения.
10. Предыдущий файл `06_SOURCES.md` с заголовком Verified сохранён как historical artifact. Его неперепроверенные performance/version assertions не переиспользуются как проверенные факты. Текущий source registry отдельный.
11. Инструкции workflow JSON этого ZIP — наш canonical format, не подтверждённый native Laya import API. Автоматического исполнения или автоподключения привилегий от импорта нет.
12. Исходные полные личные архивы, прошлые ZIP и весь repo здесь не собраны; полный inventory ограничен фактически доступными файлами. Требования текущего чата собраны, а missing data указаны.


# Предыдущие 129 функций (сохранённые proposals)
`capture_voice_stream()`
`capture_active_window_event()`
`capture_accessibility_event()`
`capture_clipboard_event()`
`ingest_file(path)`
`ingest_folder(path)`
`ingest_repo(repo_path)`
`ingest_git_history(repo_path)`
`ingest_chat_export(source, path)`
`ingest_document_export(source, path)`
`ingest_terminal_trace()`
`normalize_object()`
`content_address_object()`
`deduplicate_object()`
`attach_provenance()`
`index_fulltext()`
`index_embeddings()`
`index_temporal_event()`
`index_entity_graph()`
`index_repo_symbols()`
`index_import_graph()`
`index_call_graph()`
`index_tests_to_symbols()`
`index_commit_symbol_diff()`
`refresh_incremental_indexes()`
`resolve_goal_entities()`
`retrieve_exact()`
`retrieve_semantic()`
`retrieve_temporal()`
`retrieve_graph_neighbors()`
`retrieve_code_dependencies()`
`detect_superseded_facts()`
`detect_conflicting_context()`
`rank_evidence()`
`compile_context_pack()`
`compile_context_delta()`
`estimate_context_budget()`
`generate_handoff_bundle()`
`transcribe_stream()`
`detect_end_of_utterance()`
`bias_domain_vocabulary()`
`parse_typed_intent()`
`classify_risk()`
`estimate_intent_confidence()`
`prefetch_from_partial_transcript()`
`escalate_to_planner()`
`build_action_spec()`
`decompose_to_dag()`
`find_parallelizable_nodes()`
`declare_preconditions()`
`declare_postconditions()`
`declare_required_capabilities()`
`compute_rollback_plan()`
`register_executor()`
`register_skill()`
`list_capabilities()`
`match_capability()`
`score_executor()`
`update_executor_score()`
`choose_primary_executor()`
`choose_fallback_executors()`
`mark_executor_degraded()`
`execute_local_function()`
`execute_powershell()`
`execute_process()`
`execute_git()`
`execute_mcp_tool()`
`execute_http_api()`
`execute_browser_cdp()`
`execute_playwright()`
`execute_browsercode_script()`
`execute_windows_uia()`
`execute_win32()`
`execute_com()`
`execute_ufo_workflow()`
`execute_gui_vision_agent()`
`snapshot_pre_state()`
`verify_preconditions()`
`execute_with_timeout()`
`verify_postconditions()`
`compare_expected_actual()`
`retry_with_same_executor()`
`fallback_to_next_executor()`
`rollback_action()`
`create_execution_receipt()`
`checkpoint_workflow()`
`resume_workflow()`
`create_automation_spec()`
`create_git_worktree()`
`invoke_coding_agent()`
`apply_patch_isolated()`
`run_targeted_tests()`
`run_regression_tests()`
`package_skill()`
`validate_skill_manifest()`
`atomic_install_skill()`
`healthcheck_skill()`
`rollback_skill_version()`
`promote_skill_to_fast_path()`
`record_command_case()`
`record_trajectory()`
`label_outcome()`
`compute_success_rate()`
`compute_latency_distribution()`
`compute_cost_per_success()`
`compare_executor_paths()`
`mine_repeated_sequences()`
`synthesize_candidate_skill()`
`regression_test_all_commands()`
`resolve_secret_reference()`
`redact_sensitive_context()`
`enforce_path_scope()`
`enforce_network_scope()`
`enforce_command_allowlist()`
`permission_gate()`
`require_human_approval()`
`audit_tool_call()`
`revoke_skill_capability()`
`scan_repo_state()`
`build_studious_repo_map()`
`run_qualification_suite()`
`parse_qualification_failures()`
`map_failure_to_symbols()`
`retrieve_related_pr_history()`
`retrieve_related_chat_decisions()`
`compile_failure_handoff()`
`generate_patch_branch()`
`validate_flashloan_patch()`
`write_qualification_receipt()`

# Новые 96 функций (proposals)
`route_dependency_fingerprint()` — RND-19
`estimate_cofailure_matrix()` — RND-19
`select_diverse_portfolio()` — RND-19
`record_marginal_recovery()` — RND-19
`compute_hedge_trigger()` — RND-20
`reserve_speculation_budget()` — RND-20
`cancel_loser_candidates()` — RND-20
`audit_cancellation_completion()` — RND-20
`issue_intent_operation_id()` — RND-21
`acquire_effect_lease()` — RND-21
`commit_verified_candidate()` — RND-21
`reconcile_unknown_effect()` — RND-21
`infer_resource_access_sets()` — RND-22
`build_conflict_graph()` — RND-22
`acquire_foreground_lease()` — RND-22
`yield_to_user_input()` — RND-22
`freeze_context_snapshot()` — RND-23
`validate_snapshot_closure()` — RND-23
`compare_target_revision()` — RND-23
`invalidate_stale_candidate()` — RND-23
`derive_evidence_requirements()` — RND-24
`compute_context_deficit()` — RND-24
`choose_next_observation()` — RND-24
`emit_needs_context_request()` — RND-24
`extract_label_candidates()` — RND-25
`reconcile_label_authority()` — RND-25
`normalize_project_aliases()` — RND-25
`abstain_on_label_conflict()` — RND-25
`build_context_ablation_set()` — RND-26
`measure_evidence_utility()` — RND-26
`compare_pack_variants()` — RND-26
`freeze_holdout_partitions()` — RND-26
`hash_derivation_inputs()` — RND-27
`invalidate_context_dependents()` — RND-27
`refresh_materialized_pack()` — RND-27
`compare_incremental_full_build()` — RND-27
`generate_contract_counterexample()` — RND-28
`run_metamorphic_checks()` — RND-28
`measure_verifier_mutation_score()` — RND-28
`reject_test_weakening_patch()` — RND-28
`identify_critical_voice_slots()` — RND-29
`request_selective_asr_check()` — RND-29
`reconcile_transcript_hypotheses()` — RND-29
`freeze_confirmed_intent_revision()` — RND-29
`process_stop_signal()` — RND-30
`revoke_pending_intent_generation()` — RND-30
`supersede_running_plan()` — RND-30
`report_irreversible_boundary()` — RND-30
`build_skill_contract()` — RND-31
`attach_skill_evidence_bundle()` — RND-31
`validate_skill_environment()` — RND-31
`expire_skill_qualification()` — RND-31
`estimate_workflow_critical_path()` — RND-32
`admit_resource_bounded_nodes()` — RND-32
`pause_background_indexing()` — RND-32
`score_latency_reliability_frontier()` — RND-32
`mark_dispatch_uncertain()` — RND-33
`query_effect_receipt()` — RND-33
`prove_safe_retry_transition()` — RND-33
`quarantine_ambiguous_operation()` — RND-33
`validate_adapter_contract()` — RND-34
`classify_input_trust_origin()` — RND-34
`isolate_untrusted_document_instructions()` — RND-34
`enforce_egress_field_policy()` — RND-34
`register_ingestion_stage()` — RND-35
`resume_ingestion_cursor()` — RND-35
`stream_large_source_objects()` — RND-35
`schedule_progressive_enrichment()` — RND-35
`trace_information_lineage()` — RND-36
`cluster_near_duplicate_claims()` — RND-36
`compute_independent_evidence_count()` — RND-36
`preserve_conflicting_source_versions()` — RND-36
`record_conditional_failure()` — RND-37
`retrieve_negative_capability_evidence()` — RND-37
`invalidate_obsolete_failure()` — RND-37
`route_around_known_failure()` — RND-37
`slice_successful_trajectory()` — RND-38
`eliminate_redundant_steps()` — RND-38
`validate_minimized_skill()` — RND-38
`compare_skill_behavioral_equivalence()` — RND-38
`compute_capability_permission_diff()` — RND-39
`verify_update_origin()` — RND-39
`stage_skill_candidate()` — RND-39
`activate_approved_skill_version()` — RND-39
`compile_provider_scoped_handoff()` — RND-40
`validate_ai_return_contract()` — RND-40
`bind_ai_patch_to_snapshot()` — RND-40
`merge_model_evidence_without_effects()` — RND-40
`fingerprint_capability_environment()` — RND-41
`run_readonly_capability_canary()` — RND-41
`demote_drifted_executor()` — RND-41
`schedule_adapter_requalification()` — RND-41
`evaluate_context_policy_candidate()` — RND-42
`optimize_offline_context_program()` — RND-42
`audit_optimizer_data_leakage()` — RND-42
`promote_validated_context_policy()` — RND-42