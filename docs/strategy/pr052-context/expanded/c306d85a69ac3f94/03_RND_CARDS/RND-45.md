# RND-45 — Join-semantics compiler
**Статус:** new; proposed R&D, не установленная интеграция.

## Зачем
Нельзя использовать first-winner для всей агрегации и wait-all для каждой команды.

## Устройство
Каждому узлу задать UNION, REQUIRED_EVIDENCE_JOIN, FIRST_VERIFIED, PARTITIONED_MAP или PREPARE_COMMIT.

## Эксперимент
Одинаковую задачу выполнить с неправильным и правильным join mode.

## Acceptance
Ни потерянных поздних фактов, ни ожидания необязательного архива на critical path.

## Функции
- `classify_parallel_join_semantics()`
- `compile_join_contract()`
- `validate_route_merge_policy()`
- `explain_join_wait_reason()`

Requirements: REQ-035 REQ-034. Sources: S01 S02.
