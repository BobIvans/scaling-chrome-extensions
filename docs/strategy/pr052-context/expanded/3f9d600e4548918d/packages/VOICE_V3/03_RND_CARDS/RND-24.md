# RND-24 — Evidence deficit planner

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Научить app замечать, какой конкретно информации не хватает.

## Архитектурное изменение
Coverage matrix goal→required observations; вместо ещё одного полного prompt запрашивать один missing source/test/error.

## Конкретный эксперимент
Дать bug с отсутствующим trace и противоречивыми заметками; проверить выбор следующего чтения.

## Критерий принятия
Измерить time-to-sufficient-evidence и bytes/request; missing обязательное evidence блокирует действие.

## Функции
- `derive_evidence_requirements()`
- `compute_context_deficit()`
- `choose_next_observation()`
- `emit_needs_context_request()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-010 REQ-015 REQ-023. Первичные источники/технические предпосылки: S11. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
