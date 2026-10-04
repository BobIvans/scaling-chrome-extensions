# RND-49 — Desired-state action equivalence
**Статус:** new_detail; proposed R&D, не установленная интеграция.

## Зачем
Разные команды запуска могут быть одним и тем же методом с общим failure domain.

## Устройство
ActionSpec описывает desired state; registry связывает API/CLI/UIA с pre/postconditions; diversity измерять по восстановленным failures.

## Эксперимент
Открыть проект code CLI, OS URI handler и UIA; проверить одинаковый итог без тройного открытия.

## Acceptance
Победитель определяется target state; другой route не создаёт duplicate window.

## Функции
- `define_action_equivalence_class()`
- `map_goal_to_reachable_state()`
- `choose_shortest_verified_route()`
- `reconcile_same_goal_effects()`

Requirements: REQ-034 REQ-036. Sources: S02 S05.
