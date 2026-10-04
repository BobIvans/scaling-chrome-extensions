# RND-32 — Critical-path and attention-budget scheduling

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Ускорять итог задачи, а не максимальное число одновременно активных процессов.

## Архитектурное изменение
DAG priorities по критическому пути; RAM/CPU/network/provider budgets; foreground lease; idle-only reindex.

## Конкретный эксперимент
На Dell выполнить фоновые imports + ASR + context pack; сравнить eager fan-out и admission control.

## Критерий принятия
Не ухудшить voice responsiveness и UI; реальные measured p50/p95 + peak RAM, никаких выдуманных миллисекунд.

## Функции
- `estimate_workflow_critical_path()`
- `admit_resource_bounded_nodes()`
- `pause_background_indexing()`
- `score_latency_reliability_frontier()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-014 REQ-015 REQ-020. Первичные источники/технические предпосылки: S01 S05. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
