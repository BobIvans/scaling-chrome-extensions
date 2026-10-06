# CODEX START HERE — PR64–PR69

Implementation baseline: `main@06fbd2f31776690a2b15888d8ab0dff9dd47961f`.

## Текущая команда

Не начинай с PR65–PR69. Сначала реализуй **PR64 Durable Parallel Execution V9** из `PR64_DURABLE_PARALLEL_EXECUTION_V9_RU.md`. После каждого merged PR перечитывай текущий `main`, обновляй evidence и только затем переходи к следующему PR.

## Порядок чтения

1. `MASTER_CONTEXT_PR64_PR69_RU.md`
2. `CURRENT_GAP_AUDIT_RU.md`
3. `IMPLEMENTATION_DAG_PR64_PR69.json`
4. `ACCEPTANCE_MATRIX_PR64_PR69.json`
5. Документ конкретного PR
6. `RISK_FAULT_MATRIX_PR64_PR69.json`
7. текущий `.github/workflows/deterministic-core.yml`, tests и live Git history

## Правило работы

- Переиспользуй `automation_core.py`, `workflow_state.py`, `campaign_runtime.py`, `goal_runtime.py`, `persistent_mission.py`, `fast_decision.py`, `site_adapter.py`, `release_updater.py` и текущий Desktop transport.
- Не создавай отдельный scheduler/DB/queue только ради parallelism.
- Любая новая durable schema должна иметь migration/backward-compatible read path и tests на restart.
- Каждый effect должен быть привязан к exact identity/resource/effect intent.
- Любой UNKNOWN должен блокировать только те resources, для которых исход реально неоднозначен; legacy/unbound effects остаются conservative-global до миграции.
- Default behaviour после PR64 должен оставаться безопасным для старой конфигурации: `max_parallel=1` или эквивалентный conservative default.
- Нельзя снимать device/production gate только потому, что CI зелёный.

## PR64 first implementation cut

Минимально полезный первый cut PR64 должен доказать:

`3 independent durable jobs → 3 compatible resource bindings → concurrent RUNNING → one finishes first → evidence persisted → another lane cancelled as obsolete → crash/restart preserves remaining lane identities → conflicting writer never overlaps`.

После этого расширяй на Campaign + Persistent Mission integration и fault corpus.

## Один текст для старта Codex

См. `CODEX_ONE_LINE_PR64_PR69.txt`.
