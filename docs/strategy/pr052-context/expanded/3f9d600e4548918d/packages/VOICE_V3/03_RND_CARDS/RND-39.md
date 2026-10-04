# RND-39 — Permission-diff aware updater

**Статус:** R&D specification, не реализованная интеграция. Новизна: `hardening_of_prior_idea`.

## Проблема
Обновление функции не даёт автоматически новые права на весь компьютер.

## Архитектурное изменение
Проверить commit/artifact provenance, version, API contract, permissions diff; stage, healthcheck, single activation; откат только обратимого.

## Конкретный эксперимент
Кандидат просит новый filesystem root/network host; параллельно тест и attestation; activation должен остановиться.

## Критерий принятия
Никакого privilege creep; несовместимая DB migration требует отдельного плана.

## Функции
- `compute_capability_permission_diff()`
- `verify_update_origin()`
- `stage_skill_candidate()`
- `activate_approved_skill_version()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-013 REQ-018 REQ-019. Первичные источники/технические предпосылки: S15. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
