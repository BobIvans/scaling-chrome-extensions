# Параллельные стратегии: сначала параллельные доказательства

Это R&D-архитектура, не торговый совет и не заявление о прибыльности. В этом пакете нет доступа к кошельку/подписанту и нет отправки транзакций.

## Разделить research/control plane и execution path

Библиотека, голос, Laya и LLM управляют гипотезами, конфигурациями, анализом и документами. Низколатентный execution path должен работать по заранее проверенному детерминированному контракту, а не ждать речевого ввода или генерации LLM перед каждым swap.

Предлагаемый конвейер:

`Shared approved data feeds → point-in-time state cache → strategy workers → candidate deduplication → simulation budget queue → cost/risk checks → conflict/capital coordinator → operator-gated execution boundary → independent receipts`

До отдельного разрешения последний execution boundary остаётся disabled; pipeline заканчивается наблюдением/replay/simulation.

## Где параллелить

Разные независимые исследования и вычисления маршрутов могут читать общий snapshot. Общие RPC/price/pool запросы дедуплицируются. Worker не должен отдельно опрашивать тот же account для каждого варианта стратегии. Иначе число strategies растёт, а quota расходуется на одинаковые данные.

Параллельность записи/отправки ограничивается конфликтующими account sets, общим капиталом, доступными лимитами и фактической инфраструктурой. Solana-транзакции имеют атомарную семантику и явные аккаунты; Jito submission/bundles требуют отдельного учёта исполнения. [S33,S34] Не выдавать «100 workers» за «100 независимых одновременно прибыльных flashloans».

Flashloan ограничивает жизненный цикл займа атомарной транзакцией соответствующего протокола; ожидание роста long-позиции и неатомарный cross-chain settlement — другие классы стратегии. Изучать их отдельными risk/evidence contracts, не маскировать под гарантированно возвращаемый flashloan.

## Приоритетные семейства экспериментов

Начальный scope — уже существующая связка репозитория, а не новый бот на каждый market: circular route replay; exact constant-product capacity; quote→simulation divergence; stale-state rejection; fee-accounting reconciliation; executable-route coverage; routing contention; provider data latency; capital reuse timing. Для нового DEX/asset сначала источник и reproducible state, затем executable integration, затем издержки и holdout.

Второй круг R&D: совместимость intent/orderflow; netting вместо лишних swaps; конкурентный market-data/simulation service; opportunity explanation; data quality scoring; оптимизация allocation между стратегиями. Это гипотезы, не утверждение что соответствующие рынки уже доступны/выгодны в нужном виде.

## Что хранить в каждом decision episode

source/event/receive timestamps; slot и consistency basis; raw source/pool state hashes; route и суммы в точных единицах; запрошенные котировки; simulation errors/CU; известные комиссии; какие издержки уже включены; failure assumptions; environment/config/revision; rejected alternatives; итог и тип evidence.

Не путать quoted, simulated, modeled fill и realized fill. Все компоненты net edge приводятся к одной quote unit, встроенные fee/slippage не вычитаются дважды. Замораживать holdout до подбора thresholds. Учитывать trial count, selection bias и зависимые observations; лучший из тысячи backtests не является автоматически устойчивым edge.

## Admission и остановка

В approved observation-mode нужны source rights, provider allowlist/quota, budget, stop switch, recovery и point-in-time consistency. Для real money требуется отдельный review chain и risk budget; исследовательский agent не может самостоятельно их повысить. `NO_EDGE`, `INCONCLUSIVE`, `DATA_INVALID`, `ENVIRONMENT_BLOCKER` — полезные результаты, которые тоже попадают в библиотеку.

На Dell начать с small bounded read pool и одного writer, измеряя bottleneck. Предел concurrency выбирать по измерениям CPU/RAM/RPC quota/latency, а не по желаемому числу стратегий.
