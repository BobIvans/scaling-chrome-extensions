# RND-27 — Incremental materialized context views

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Пересобирать только изменённую часть репозитория и зависимых context packs.

## Архитектурное изменение
Merkle identifiers на blobs/chunks/derivations; dependency invalidation; parser/schema version входят в cache key.

## Конкретный эксперимент
Изменить одну функцию в большом fixture corpus; сверить incremental output с полной пересборкой.

## Критерий принятия
Exact equality где детерминировано; явный unresolved для dynamic edges; raw objects никогда не теряются.

## Функции
- `hash_derivation_inputs()`
- `invalidate_context_dependents()`
- `refresh_materialized_pack()`
- `compare_incremental_full_build()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-004 REQ-006 REQ-032. Первичные источники/технические предпосылки: S09. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
