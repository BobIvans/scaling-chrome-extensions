# MASTER CONTEXT — audit/repair ROADMAP PR-001…021

Repository: `BobIvans/scaling-chrome-extensions`. Audit snapshot main: `7253c40398905967ade0541717bcbfac25fec5b9`.
Repair title: **Reconcile PR001–021 source ownership and preserve shared Core during PR52 integration**.
This is a repair handoff, not a newly created GitHub PR. Existing target PR:
[SCE #52](https://github.com/BobIvans/scaling-chrome-extensions/pull/52), companion [Studious #565](https://github.com/BobIvans/studious-pancake/pull/565).

Пользователь попросил найти документы первых 21 PR приложенной AUTOMATION_STRATEGY V3,
проверить последовательность реальных merges и при наличии проблем создать ZIP исправлений.
Аудит/ZIP завершены; implementation repairs и remote mutations этим запросом не выполнялись.

## Source of truth

1. Текущие инструкции пользователя, actual repo instructions и свежие Git/GitHub refs.
2. Original V3 `sources/archives/STRATEGY_V3.zip`: все 539 members сохранены без сокращения.
3. `sources/archives/PR001.zip`…`PR009.zip`, `PR010_021.zip`, шесть combined archives:
   точные plans/contracts/original criteria; provenance в `sources/SOURCE_INDEX.json`.
4. `sources/v5/briefs`, `coverage`, `source_master/strategy_v5` и original delivery DAG.
5. Current code/tests/CI и fresh `evidence/PR001_021_STATUS.json`: устанавливают фактический
   delivery scope. Dated snapshots и copies source plans не являются current states.

## Что уже есть

Все merges #38–#51, относящиеся к roadmap, кроме numbering gaps, находятся в current main;
полная observed последовательность — `01_MERGE_SEQUENCE_RU.md`. #53 сохраняет документы.
#49 и #51 реально merged; source ledger не нужно писать заново. 17 roadmap numbers имеют
merged code slices, 010/011 ещё не completed foundations, 020/021 — unmerged #52/#565.
Existing current-main verification: 708 passed, 3 desktop display skips, 0 failed.
No product/device qualification inferred. Full original criteria remain preserved.

## С чего продолжить

Прочитать `CODEX_START_HERE.md`, `00_FINDINGS_RU.md`, `03_PR52_CONFLICT_REPAIR_RU.md`,
`04_IMPLEMENTATION_PLAN_RU.md`, `plan/FIX_PLAN.json`.
First concrete repair: preserve current action/context/campaign owners while integrating
#52 research branch across nine conflicted files. Foundation next: versioned shared
SourceAddress/read adapters over ChatGPT/context/source ledger, then PR010_011 original
scope and dependent lifecycle/importers. Это внутренние work items, не новая нумерация
исходного roadmap и не обещание шести отдельных PR.

Canonical owners: `content.sqlite3`, `automation_core.Core`/queue/jobs/leases,
`workflow_state.py` и `core_control` STOP. Исходные тексты/AI results остаются данными.
Existing source IDs/raw bytes/observations/extractions/search items не сливать в одну
identity и не заменять вторым store. Side selection при merge не должна терять routes,
installed modules или build/owned hashes. Старые criterion IDs/wording не менять ради summary.

## Условия завершения

Контекст этого ZIP цел и проверяем. Code repair завершён только после meaningful
regressions и fresh final-head CI. Полный roadmap finished только при пригодном
criterion-specific integration/device evidence. NOT_RUN/DEFERRED остаются отдельными.
Remote PR statuses и SHA обновить перед любой дальнейшей action.
