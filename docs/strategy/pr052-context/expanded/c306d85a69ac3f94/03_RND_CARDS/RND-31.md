# RND-31 — Proof-carrying skill packages

**Статус:** R&D specification, не реализованная интеграция. Новизна: `hardening_of_prior_idea`.

## Проблема
Навык хранит не только скрипт, но и условия его применимости.

## Архитектурное изменение
Skill manifest: input/output schemas, preconditions, postconditions, provenance, environment fingerprint, permissions, expiry, rollback scope.

## Конкретный эксперимент
Повторить успешный навык на другой версии приложения и с другой ролью пользователя.

## Критерий принятия
Mismatched environment блокирует promotion; receipt содержит code hash и проверенные условия.

## Функции
- `build_skill_contract()`
- `attach_skill_evidence_bundle()`
- `validate_skill_environment()`
- `expire_skill_qualification()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-013 REQ-017 REQ-019. Первичные источники/технические предпосылки: S15 S18. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
