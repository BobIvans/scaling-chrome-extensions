# RND-30 — Independent stop and intent revision

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Система должна быстро останавливаться и понимать «нет, не этот repo».

## Архитектурное изменение
Отдельный high-priority control channel; пересмотр intent отзывает pending plans и leases; committed эффекты не выдавать за undone.

## Конкретный эксперимент
Во время retrieval/patch подготовки/ожидания merge дать stop и смену проекта.

## Критерий принятия
Ни одного нового effect после подтверждённого stop; unknown external effects идут в reconciliation.

## Функции
- `process_stop_signal()`
- `revoke_pending_intent_generation()`
- `supersede_running_plan()`
- `report_irreversible_boundary()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-002 REQ-018 REQ-020. Первичные источники/технические предпосылки: S02. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
