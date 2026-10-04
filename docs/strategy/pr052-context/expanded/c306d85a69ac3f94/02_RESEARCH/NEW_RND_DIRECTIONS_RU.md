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