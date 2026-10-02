# F-22: типизированный нормализатор цели и лимитов

## Подтверждённый gap

На проверенном F-21 head `one-click-context/library/agent.mjs` принимал единственную
свободную строку instruction. Native Host ограничивал bytes/mode и sandbox, но UI
не отделял цель от constraints/prohibitions и не связывал предложение с явными
budget/concurrency. Голосовой transcript не имел authority и остаётся несвязанным.

## Реализация

`goal-normalizer.mjs` создаёт один канонический `occ.goal-proposal.v1` с полями:

- непустая положительная `goal`;
- 1–20 положительных `constraints`;
- 1–20 отдельных `prohibitions`, записанных как названия запрещённых эффектов;
- целочисленные `money_budget=0` и `max_parallel=1`;
- `action_authority=false`.

Пропущенные/лишние поля, строки NUL, дубликаты, byte/count overflow, numeric
coercion и другие budget/concurrency отклоняются. Маркеры отрицания RU/EN/LV в
семантических строках отклоняются как неоднозначные: запрет нужно поместить в
типизированное поле `prohibitions` без конструкции «не делать».

UI может проверить и показать proposal локально без Native Host. Прежний Codex
handoff при настоящем click повторно нормализует текущие поля, передаёт только
канонический JSON и по-прежнему требует отдельный confirm. Выбранный context
сохраняет прежнюю untrusted-data семантику.

## Границы

F-22 не маршрутизирует proposal, не ставит durable job, не запускает action и не
подключает voice transcript. Native Host, SQLite/library/job queue, Codex sandbox
и cancel owners не изменены. Нулевой budget не является обещанием бесплатной
квоты, а `action_authority=false` запрещает будущему router трактовать confidence
или текст как разрешение на эффект.
