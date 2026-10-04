# RND-53 — Fast local-first versus remote hedge calibration
**Статус:** new_experiment; proposed R&D, не установленная интеграция.

## Зачем
На CPU laptop параллельные большие модели могут замедлить всё.

## Устройство
Benchmark rules/FTS alone, local Laya router, local+consented remote hedge; no unconditional fan-out; common resource budget.

## Эксперимент
Одинаковый held-out RU/EN command corpus; warm/cold, contention, slow API и offline fault.

## Acceptance
Выбирать по cost per verified success и p95 response; reject policy, ухудшающую critical commands.

## Функции
- `profile_on_device_route_budget()`
- `compare_local_remote_hedge_policies()`
- `track_quality_latency_pareto_frontier()`
- `promote_empirically_better_portfolio()`

Requirements: REQ-036 REQ-015. Sources: S01 S06 S22 S23.
