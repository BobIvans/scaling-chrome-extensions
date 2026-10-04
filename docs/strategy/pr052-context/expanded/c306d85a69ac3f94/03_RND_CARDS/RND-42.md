# RND-42 — Offline context-and-skill optimizer

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Улучшать способы собирать контекст по результатам, не добавляя бездумно больше текста.

## Архитектурное изменение
DSPy/GEPA как optional offline optimizer для retrieval rules, labels, skill prompts; immutable holdout + cost/privacy constraints.

## Конкретный эксперимент
Одинаковый набор задач для baseline и learned context policy; reject reward hacking и критические regression.

## Критерий принятия
Promotion только по held-out verified outcomes, без изменения permissions и production policy.

## Функции
- `evaluate_context_policy_candidate()`
- `optimize_offline_context_program()`
- `audit_optimizer_data_leakage()`
- `promote_validated_context_policy()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-015 REQ-017 REQ-026. Первичные источники/технические предпосылки: S11 S12 S13. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
