# RND-23 — Snapshot-closed context

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Пакет связан с одним состоянием проекта, а не смесью вчера и сегодня.

## Архитектурное изменение
Repo SHA + dirty-file hashes + index hash + config/policy version + source revision задают snapshot; перед effect повторная проверка.

## Конкретный эксперимент
Поменять файл после retrieval и до apply; удалить dependency; изменить allowlist.

## Критерий принятия
STALE/NEEDS_CONTEXT вместо применения к старой базе; ни одного silent overwrite.

## Функции
- `freeze_context_snapshot()`
- `validate_snapshot_closure()`
- `compare_target_revision()`
- `invalidate_stale_candidate()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-006 REQ-012 REQ-032. Первичные источники/технические предпосылки: S04. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
