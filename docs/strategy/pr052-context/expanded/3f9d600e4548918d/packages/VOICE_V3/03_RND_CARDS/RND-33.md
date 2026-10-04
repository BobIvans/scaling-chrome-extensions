# RND-33 — Unknown-outcome state machine

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Отмена/таймаут не доказывает, что внешний запрос не выполнился.

## Архитектурное изменение
PREPARED→DISPATCHED→UNKNOWN→OBSERVED_SUCCESS/SAFE_TO_RETRY/MANUAL_REVIEW. Сверять external receipt по operation ID.

## Конкретный эксперимент
Смоделировать lost response после server commit; нельзя запускать второй маршрут отправки.

## Критерий принятия
Нулевая слепая повторная публикация; unresolved отдельно от failed.

## Функции
- `mark_dispatch_uncertain()`
- `query_effect_receipt()`
- `prove_safe_retry_transition()`
- `quarantine_ambiguous_operation()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-014 REQ-018 REQ-023. Первичные источники/технические предпосылки: S02. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
