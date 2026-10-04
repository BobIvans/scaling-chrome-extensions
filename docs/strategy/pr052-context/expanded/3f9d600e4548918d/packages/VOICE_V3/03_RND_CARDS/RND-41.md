# RND-41 — Capability drift monitoring

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Навык теряет валидность после обновления сайта, инструмента или модели.

## Архитектурное изменение
Fingerprint version/schema/UI selectors; canary read-only cases; quarantine broken adapter; fallback uses другой failure domain.

## Конкретный эксперимент
Изменить locator/API field/tool schema и проверить fast demotion старого skill.

## Критерий принятия
Нельзя продолжать по устаревшему cached capability; отдельные receipts для platform qualification.

## Функции
- `fingerprint_capability_environment()`
- `run_readonly_capability_canary()`
- `demote_drifted_executor()`
- `schedule_adapter_requalification()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-013 REQ-017 REQ-026. Первичные источники/технические предпосылки: S03 S05 S16. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
