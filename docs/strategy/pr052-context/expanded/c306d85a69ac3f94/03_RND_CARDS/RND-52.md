# RND-52 — Recording-to-automation opportunity miner
**Статус:** refinement; proposed R&D, не установленная интеграция.

## Зачем
Нужно понять, какие повторяющиеся действия действительно стоит автоматизировать.

## Устройство
Cross-source traces → user-confirmed task episode → estimated repeated work → candidate skill → separate verifier.

## Эксперимент
Из ручного CI triage выделить повторяемые части, не запоминая секретные случайные действия.

## Acceptance
Нет auto-enable только по наблюдению; saved manual effort измеряется после approved replay.

## Функции
- `segment_cross_source_task_episode()`
- `rank_automation_opportunities()`
- `draft_skill_from_correlated_episode()`
- `measure_verified_manual_effort_saved()`

Requirements: REQ-013 REQ-033. Sources: S24 S12.
