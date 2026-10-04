# RND-21 — Single-effect commit broker

**Статус:** R&D specification, не реализованная интеграция. Новизна: `hardening_of_prior_idea`.

## Проблема
Результаты готовятся параллельно, эффект принадлежит одному брокеру.

## Архитектурное изменение
Уникальный operation_id, payload hash, snapshot revision, writer lease/fencing token, durable outbox и reconciliation.

## Конкретный эксперимент
Два кандидата для одного target; kill/retry вокруг локального commit; отдельно моделировать неизвестный внешний результат.

## Критерий принятия
Локальный commit ровно один в тестируемой SQLite-транзакции; внешние unknown не перезапускаются слепо.

## Функции
- `issue_intent_operation_id()`
- `acquire_effect_lease()`
- `commit_verified_candidate()`
- `reconcile_unknown_effect()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-014 REQ-018. Первичные источники/технические предпосылки: S02. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
