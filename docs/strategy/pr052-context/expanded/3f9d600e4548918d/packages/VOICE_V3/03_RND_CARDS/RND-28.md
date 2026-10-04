# RND-28 — Verifier adequacy and counterexamples

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Не выбирать патч только потому, что он обошёл слабые тесты.

## Архитектурное изменение
Task-specific independent oracles + property/metamorphic tests; mutation-testing эксперименты; разделить test author и patch author.

## Конкретный эксперимент
Сделать intentionally wrong patch, который проходит прежний test; добавить проверку нарушенного инварианта.

## Критерий принятия
False-success ниже baseline; тесты не отключены, assertions не удалены, negative suite не деградирует.

## Функции
- `generate_contract_counterexample()`
- `run_metamorphic_checks()`
- `measure_verifier_mutation_score()`
- `reject_test_weakening_patch()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-011 REQ-017 REQ-023. Первичные источники/технические предпосылки: S11. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
