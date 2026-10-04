# RND-19 — Failure-domain diversity

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Не путать три обёртки pytest с тремя независимыми страховками.

## Архитектурное изменение
Добавить дерево общих зависимостей: interpreter, browser engine, remote account, model/provider, verifier, source lineage.

## Конкретный эксперимент
Сравнить 3 обёртки одного пути с 2 реально разными источниками evidence на fault-injection corpus.

## Критерий принятия
Записать co-failure matrix и marginal recovery каждого маршрута; не выводить независимость из названия инструмента.

## Функции
- `route_dependency_fingerprint()`
- `estimate_cofailure_matrix()`
- `select_diverse_portfolio()`
- `record_marginal_recovery()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-014 REQ-017. Первичные источники/технические предпосылки: S01 S02. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
