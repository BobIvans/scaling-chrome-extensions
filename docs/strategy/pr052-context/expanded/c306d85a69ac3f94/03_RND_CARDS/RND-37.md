# RND-37 — Negative knowledge and failure memory

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Хранить доказанное «это здесь не работает» вместе с условиями и сроком.

## Архитектурное изменение
Отказ UI locator, missing dependency, unsupported model method, false lead; condition/expiry/recheck trigger.

## Конкретный эксперимент
Повторить известный failure на том же fingerprint, затем сменить версию и проверить expiry.

## Критерий принятия
Меньше бесполезных повторов без вечной блокировки исправленных возможностей.

## Функции
- `record_conditional_failure()`
- `retrieve_negative_capability_evidence()`
- `invalidate_obsolete_failure()`
- `route_around_known_failure()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-012 REQ-015 REQ-017. Первичные источники/технические предпосылки: S14. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
