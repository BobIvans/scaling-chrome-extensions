# RND-20 — Adaptive hedging

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Запускать запасной путь только при признаке задержки или нехватки evidence.

## Архитектурное изменение
Первая дешёвая read-попытка стартует сразу; второй путь после deadline/uncertainty trigger; отменить проигравших с receipt.

## Конкретный эксперимент
Сравнить serial, eager-parallel, delayed-hedge на фиксированном наборе read-only задач при одинаковом бюджете.

## Критерий принятия
Снизить p95 time-to-verified при заданном API/CPU бюджете; не допустить дублирующих внешних эффектов.

## Функции
- `compute_hedge_trigger()`
- `reserve_speculation_budget()`
- `cancel_loser_candidates()`
- `audit_cancellation_completion()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-014 REQ-015. Первичные источники/технические предпосылки: S01. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
