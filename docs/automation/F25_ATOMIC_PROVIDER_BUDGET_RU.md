# F-25: атомарный бюджет до provider API

## Подтверждённый gap и owner

Voice/goal UI передавал только типизированный `money_budget=0`, а durable core
справедливо запрещал любые траты. В репозитории не было отдельного контракта,
который будущий backend мог бы вызвать **до** provider request и который атомарно
защищал бы общий hard cap. Владельцем выбран `content-lab/provider_budget.py` на
существующем `automation_core.connection` и том же `content.sqlite3`: новая
очередь, библиотека или browser-side ledger не создаются.

## Контракт

План `occ.provider-budget.v1` задаёт стабильный budget ID, `USD_MICRO`, целый
`hard_cap_microunits` и 1–3 попытки. `reserve_budget` использует
`BEGIN IMMEDIATE`, поэтому параллельные callers не могут превысить сумму
`used + reserved <= hard_cap`. Нулевой cap отклоняет вызов до записи operation.
Один `op_key` является idempotency key: replay возвращает ту же reservation и не
списывает сумму повторно; изменившиеся amount или plan дают conflict.
Перед запуском конкурентных backend workers вызывается `initialize_budget_store`;
сами reservations сериализуются SQLite-транзакцией, а не process-local lock.

Успешно наблюдённый ответ переводится `RESERVED → SETTLED`; доказанно неотправленный
request — `RESERVED → RELEASED`. Только RELEASED разрешает явный bounded retry с
предыдущим reservation ID. Неизвестный исход становится `NEEDS_RECONCILIATION`,
сохраняет всю сумму reserved и запрещает retry/обычный settle, пока независимый
receipt не будет явно reconciled. Actual usage не может превышать reservation,
а provider receipt связывается SHA-256. Append-only events сохраняют попытки.

## Границы

Модуль не читает secrets, не вызывает сеть/provider, не запускает worker и не
выдаёт action authority. Текущий OCC policy по-прежнему требует
`money_budget=0`, поэтому существующие paths не получают возможность тратить.
Положительный план в unit tests является только локальной accounting fixture;
подключение реального backend требует отдельного review, бюджета и разрешения.
