# RND-26 — Causal context evaluation

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Проверять, какие фрагменты реально помогают коду, а какие засоряют контекст.

## Архитектурное изменение
Held-out tasks: полный pack, semantic slice, slice без выбранного evidence, compact+delta; одинаковый coder и verifier.

## Конкретный эксперимент
Ablation по clauses/tests/history на исторических bug задачах; новые commit families отделить от train.

## Критерий принятия
Измерить verified patch rate и marginal utility/KB без утечки ответа из будущих PR.

## Функции
- `build_context_ablation_set()`
- `measure_evidence_utility()`
- `compare_pack_variants()`
- `freeze_holdout_partitions()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-006 REQ-015 REQ-017. Первичные источники/технические предпосылки: S11 S12. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
