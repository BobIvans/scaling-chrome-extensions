# RND-38 — Skill minimization

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Успешную длинную траекторию сокращать до минимальной проверенной процедуры.

## Архитектурное изменение
Удалять redundant reads/clicks с offline replay и postcondition oracle; API/CLI замена GUI где подтверждено.

## Конкретный эксперимент
Длинный workflow vs minimized workflow на unseen fixtures и changed windows.

## Критерий принятия
Меньше действий/latency, одинаковый verified outcome; убрать шаг нельзя только по мнению LLM.

## Функции
- `slice_successful_trajectory()`
- `eliminate_redundant_steps()`
- `validate_minimized_skill()`
- `compare_skill_behavioral_equivalence()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-013 REQ-015 REQ-017. Первичные источники/технические предпосылки: S12 S18. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
