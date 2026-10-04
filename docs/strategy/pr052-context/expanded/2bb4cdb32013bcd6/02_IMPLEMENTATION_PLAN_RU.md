# План реализации одной объединённой поставки

## S0 — pinned audit и dependency preflight

Прочитать AGENTS.md и текущие repository scripts обоих checkout, записать remote, branch, HEAD, dirty state и dependency locks. Зафиксировать фактически merged состояния 001..019, current command help, input/output schema, declared effects и tests. Исторические SCE da6abf4…/Studious d1c9f4… пригодны для поиска, но не для текущего verdict. Прочитать код всех обнаруженных владельцев, потребителей и tests без лимита первых 20 файлов; inventory/reading завершать через cursors.

Создать audit/OWNER_MATRIX.json: feature/workstream → repo SHA → existing module/symbol/CLI → inputs/outputs/effects → tests → reuse/extend/new/GAP → конкретная причина. Ordinary Python functions из AST не считаются callable capability. Help/schema inspection не должен запускать trading runtime или импортировать модули с побочными effects. Для registered subprocess использовать exact executable/argv schema, а не shell строку из документа.

Разделить prerequisites: hard runtime contract dependency, compatible optional adapter и qualification-only receipt. Отсутствие Windows/API evidence не мешает implement/run offline scope, но блокирует соответствующий product claim. Перед любым integration dispatch сверить exact supported revision/schema; несовместимую комбинацию показать как BLOCKED_DEPENDENCY.

## WS-029 — actual handler catalog и Studious bridge

1. Расширить existing capability registry read-only discovery facts: repo/build identity, canonical owner, command symbol, typed argument schema, modes, timeout, effects, resource scope, receipt parser/verifier и qualification status. Продублированные имена не сливаются без owner/version.
2. Реализовать bridge как клиент текущего Studious qualification owner. Операции: inspect manifest; resolve зарегистрированный profile; prepare immutable request; dispatch; observe; cancel; reconcile после restart; import receipt; open artifacts в SCE. Расходы/leases/occurrences берутся из PR-019 Core.
3. До dispatch pin run_id, request_digest, registry/schema/config/dataset/repo revisions и idempotency key. Повторное read-only computation можно выполнять новым attempt с parent ID; незавершённый remote effect требует observe/reconcile до retry.
4. Process exit, transport delivery, domain verdict и campaign_executed — отдельные поля. exit=0 + BLOCKED или campaign_executed=false не дают PAPER_OBSERVED. Missing credentials, dataset, executable и schema mismatch имеют разные blockers.
5. UI показывает planned/running/cancelled/blocked/unknown/stale/completed и открывает domain receipt. Отмена запрещает новые dispatch, затем завершает/reconciles уже начатое по контракту handler. Restart отменённую задачу не оживляет.

Выходы: OWNER_MATRIX; HandlerManifest; BridgeRequest/Receipt; failure capsules; compatibility cases. DEC5-24 закрывается выбранным boundary, exact code audit и qualification, а не самим DTO.

## WS-030 — acquisition, datasets и point-in-time

1. Найти existing Studious broker/cache и расширить его observation model. Сохранить raw object digest, provider/upstream lineage, request parameters, received/observed/available times, chain/slot/block/commitment, cursor, completeness, adapter version, latency и acquisition origin REAL_ACQUISITION/OFFLINE_FIXTURE.
2. Snapshot/dataset manifest неизменяем: ordered observation IDs, schema, acquisition request receipt, gaps и anchor policy. SCE сохраняет ссылки на owner artifacts; strategy consumers переиспользуют тот же immutable объект.
3. Decision на времени t может видеть только available_at <= t, с declared clock skew/lag. Новая canonical anchor/revision делает dependent evidence STALE; не удалять прежний result. Incompatible anchors приводят к UNKNOWN_DISAGREEMENT, а не среднему «правильному» значению.
4. Freshness и completeness проверять до economic verifier. Пустой полный scan = NO_CANDIDATE; missing/stale/partial = INSUFFICIENT_DATA. Cursor checkpoint фиксируется после durable raw/manifest commit, чтобы retry не терял хвосты и не удваивал observations.
5. Rate/quota/backpressure общие на provider organisation и соответствующий bucket. Записать policy version; уважать полученные limits/headers, bounded retry/deadline, stop и budgets. 401/403 не лечить бесконечным 429 backoff. Secrets хранить через existing credential mechanism, в evidence только opaque reference.
6. Opportunity identity строить из normalized route/assets/anchor/state и модели settlement, без worker ID; два producer одного state дают один opportunity и два origins. Изменение state создаёт revision. Shared upstream не является независимым свидетельством.

Выходы: Observation/Dataset manifests, real-vs-fixture receipts, freshness incident corpus, provider lineage и acquisition logs. Актуальные provider notes см. research/; перед исполнением сверить документацию и account policy повторно.

## WS-031 — qualification owner, replay/paper и экономика

1. Подключить существующие registered commands, единый all-trial registry и replay engine. Frozen experiment spec включает hypothesis, mode, dataset order/digest, config, seed, deterministic clock, anchors, criteria hash, cost model, baseline, split, stop rule и executable build.
2. До старта фиксировать trial с статусом STARTED. Хранить successes, failed, cancelled, unknown, invalid и abandoned. При source/config drift прежний verdict STALE; новая config — новый trial ID. Повтор seed оставляет attempt lineage, не увеличивает independent sample count.
3. Replay decision/artifact digests должны совпадать на тех же inputs, либо содержать ограниченную описанную nondeterminism и tolerance до запуска. Modeled fills отдельно от observed quotes и realised fills. PAPER/SHADOW — semantic profiles внутри PAPER family, fixture воспроизводит модель и не подтверждает real observation.
4. Lender-neutral contract principal/fee/repayment/asset/network использует integer atomic units, explicit rounding и adapter-specific validity. Проверить zero/min/max, недоплату единицы, wrong asset/network, ordering и неавторизованный callback, когда adapter имеет callback. Solana instruction boundary проверять как Solana, без переноса EVM callback модели на каждый lender.
5. Stateful campaign задаёт actions, seed, depth, handler_calls, useful_calls, transition histogram и invariant failures. useful_calls=0 → INVALID_CAMPAIGN. Минимизированный failing sequence хранить и replay отдельно. Target coverage определяется до запуска, не post-hoc.
6. Cost owner считает DEX/borrow/network/priority/tips/failure/latency/slippage и conversion в common numeraire с point-in-time rate. Не вычитать principal дважды: route gross delta после возврата principal → все неучтённые fees/costs. Fees уже включённые в quoted output отмечать ledger included_in_quote. Unknown mandatory cost → BLOCKED_ECONOMICS. Возможные failed included transactions учитывают расходы по фактической семантике chain, modeled сценарии помечены.
7. Development/calibration/holdout разделены по времени/venue с purge/embargo для overlapping windows. Heldout criteria frozen до запуска. После просмотра holdout изменение candidate начинает новый experiment, исходный failed trial не исчезает. Replay и no-action baselines используют одинаковые eligibility/windows.

Выходы: exact replay receipts, economic ledger с units/assumptions, nonempty stateful corpus, all attempts, holdout fingerprints и negative cases.

## WS-032 — atomic и wrapper research packs

Atlas: для каждого protocol/market указать chain/program/version, источник/дата, dataset access, supported instructions, liquidity/fees/settlement, current handler, prerequisites и gap. Registry не обещает arbitrary future adapters.

Circular/triangular: borrow → swaps → repay, один route contract, account/resource limits, size/latency sensitivity, negative edge/repayment shortfall/stale pools. Наличие quote — вход модели, не доказательство исполненной сделки.

Liquidation+swap: eligibility на point-in-time oracle/state, debt/collateral bounds, liquidation actor rights, seize/repay sequence, competition и liquidity. Если collateral доступен позднее atomic stage, classification NON_ATOMIC. Недостаточный collateral или late oracle включить в corpus.

Stable peg/wrappers: conversion rights, exchange rates, fees, liquidity, redemption delay, exposure duration и settlement failures. Atomic direct conversion и delayed redemption идут в разные модели. Discount to peg не подтверждает доступный redemption.

Каждый pack имеет versioned hypothesis, dataset contract, verifier, baseline, negative cases, supported handlers, mode, outcome schema и scope. Протокол без runnable verifier остаётся UNSUPPORTED/GAP и не делает pack pass. Реализовать replay fixtures всех трёх families; real-data claims требуют acquisition receipts соответствующего источника.

## WS-033 — intent solver и delayed capital research

Offline intent/clearing принимает typed orders: asset/amount/limit/expiry/partial-fill/owner constraints, exact dataset и settlement capabilities. Solver output проверяется отдельным constraint verifier: conservation/balance, limit, expiry, feasible capacities и settlement support. Infeasible case = NO_FEASIBLE_CLEARING, не exception и не false optimum. Сравнить с fixed baseline; optimality не заявлять без proof/bound.

Cross-chain, basis и funding имеют stage timeline, capital origin/amount/lock, finality, hedging/liquidation/margin assumptions, settlement delay и adverse cases. Funding начисляется по доступному расписанию/rate при eligibility; будущий cashflow не доступен flashloan repayment. Cross-chain route не становится single-transaction atomic из-за одинакового pack API. Выходы сравнимы с atomic packs по режиму/units/risks, а не одной общей PASS шкале.

Предоставить executable offline research/verifier cases по всем названным families и отдельный gap manifest реальных adapters. Реальный protocol execution добавляется только после actual owner audit и отдельного declared scope; текущая поставка не требует расширять money-moving permissions.

## WS-034 — scale/fault и Windows qualification

Расширить существующий corpus конечными вертикалями: repo→context→AI→patch→PR/final tree→release→install/rollback; text/voice→intent→research→dataset→replay→report; backup→restore→requalification. UI labels показывают build/device/provider scope и первые missing receipts.

Scale generator создаёт детерминированные repos/corpora/архивы с last-entry sentinel, >20 files/docs, oversize blobs, mixed formats, deep/shared archive families, Unicode/long paths, cancellations и disk-full. Сравнивать set IDs и reconstructed raw hashes, а не только counts. Archive family graph хранит container hash и все nesting origins; shared archive сканировать один раз на hash, вернуть original container byte-for-byte. Bounds на unpacking/CPU/RAM/disk дают явный pending/error с continuation.

Начальные benchmark points 21/1000/10000 entries и blob 9/64 MiB — предлагаемые контрольные размеры, а не maxima и не готовый performance SLA. Extend doubling sweep до измеренного resource boundary; прекратить по заранее pinned RAM/disk/time budgets, показать full pending ledger. Воспроизводимый stalled worker/deadline case нужен без ожидания часов.

На Windows 11/Dell 16 GB снять OS/build/CPU/RAM/free disk, runtime versions, actual installed build, cold/warm runs, process RSS peak, p50/p95 responsiveness, elapsed, I/O, retries и result completeness. Проверить close Chrome, clean install non-cwd, process-tree STOP, sleep/reboot/offline, mic denied, focus/wrong target, restore, canary и interrupted rollback. Linux smoke fixtures имеют свой environment и не закрывают device criteria. Voice optional adapter case остаётся NOT_RUN при отсутствии qualified ASR; text path тестировать независимо.

Каждый confirmed fault получает minimal reproduction, owning module и regression case; исправлять owner, не вводить второй scheduler/updater. Performance пороги фиксировать перед кандидатным сравнением по baseline, выбранному corpus и профилю пользователя.

## WS-035 — полезность, baseline и ablation

Frozen пользовательские retrieval/coding/research tasks с expected outcomes/source ranges, hard negatives и критериями до запуска. Пары manual/no-action/full context/source-linked slice/ablation/compact+delta используют одинаковые dataset, coder/verifier versions и budgets. Variant order counterbalance; сохранять seed и повторные observations с lineage. Новые исправления/future market labels исключить из packet.

Accepted verified task count, denominator всех started attempts, failure/unknown/intervention rates, total elapsed и stage latencies, resource peak и API/token/RPC/compute/setup/maintenance/review costs сохранять по attempt. Unknown prices отдельны; free tier не делает стоимость compute/maintenance автоматически нулевой. Unknown/cancelled attempts в denominator не пропадают.

Стоимость полезной задачи = учтённые total costs / verified accepted outcomes, только при denominator >0; при 0 возвращать UNDEFINED_NO_VERIFIED_OUTCOME. Product ROI считать по измеренному manual effort и всем overhead; modeled market PnL отдельной колонкой с assumptions. Sample size/confidence отражают независимые evidence families; wrapper around same pytest не новая независимая оценка.

DEC5-23: выбрать versioned outcome schema/counting rules и evidence-strength model на основе actual corpus. Отчёт публикует raw attempts, preregistered thresholds, paired differences и limits; количество PR, ZIP size и количество catalog cards не являются пользой.

## WS-036 — reconciliation и final delivery

Сверить source task DAG отдельно от package/workstream DAG. Полный ledger содержит exact original criterion text, source owner, current proposed owner, required evidence kind, status, receipts, blocker owner и next evidence. Сохранить 160 task /164 feature /28 goal /24 decision IDs; records разных catalogs перекрываются и не суммируются в число функций.

Delivered, installed, usable и release-qualified — разные факты. Passing local tests может закрыть local verified property, а соответствующий Windows/Grok/Laya/network criterion остаётся OPEN/NOT_RUN. DEFERRED сохраняет explicit condition/owner, не считается completion. PARTIAL feature не становится whole-feature PASS из-за одного subcriterion.

Reconcile final revisions после merge/squash/rebase по compatible code tree/build artifacts; prerelease receipts от другой ревизии stale, если нет проверяемой equivalence mapping. Сформировать RELEASE_SCOPE.json, OPEN_BLOCKERS.json, versioned ADRs DEC5-23/24, release notes, implemented functions report и следующий конкретный brief. New unrelated ideas идут в следующую roadmap version, не расширяют V5 closure бесконечно.

Порядок внутренней интеграции: S0 → WS-029 → WS-030 → WS-031 → WS-032/033 → WS-034 → WS-035 → WS-036. Документы/fixtures можно готовить до prerequisites, runtime readiness не наследуется от планирования. Полное завершение требует пригодного evidence всех mandatory criteria выбранного frozen release scope; V5-complete claim — всех обязательных V5 criteria без silent deferral.
