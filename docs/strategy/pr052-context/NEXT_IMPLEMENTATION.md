# Next implementation — existing GitHub PR #52

Title: ROADMAP PR-020 + PR-021: Core research, Desktop receipts and criterion reconciliation.
Target branch: codex/pr020-021-research-qualification.

Checkpoint: FIX-002. Refresh refs; merge latest main into existing #52; preserve both
action_plan and studious_research strict validators/dispatch branches, both Native routes,
all Desktop panels and union installed dependencies. Keep one Core/SQLite/STOP owner.
Recipes and exact conflict snapshots: input/03_PR52_CONFLICT_REPAIR_RU.md,
input/plan/PR52_CONFLICT_RESOLUTIONS.json, input/evidence/conflicted-projections/.

Acceptance: no markers; all existing action/context/campaign/history/scan paths remain;
research jobs/replay operate on exact pinned Studious owner; actual installed layouts and
build/owned hashes match; independent STOP and lost-ack reconciliation remain correct;
latest Ubuntu/Windows final-head CI passes. Old-head CI is not inherited by the new tree.

Follow-on: FIX-003 shared SourceAddress and full original 010/011 scope. New compatible work
may already exist in another branch: inspect current refs before implementing duplicates.
The SourceAddress commit mentioned in prior conversations is not present in audited main.
Its existence elsewhere is neither ruled out nor assumed. Preserve original scope/IDs.

## Корневые документы при интеграции main

После docs-передачи к девяти app conflicts добавляются add/add conflicts в root
MASTER_CONTEXT.md и CODEX_START_HERE.md: main имеет общий handoff #51/#49/#53,
а ветка #52 — scoped handoff этой передачи. Сохранить оба полноценных контекста.
Оставить current PR52 navigation явной, а общий main handoff сохранить/связать
через docs/strategy/voice-agentos и docs/strategy/pr012-013. Его exact root copies
уже сохранены в input/evidence/main/. Оригинальные source plans не переписывать.
.gitattributes этой передачи включает текущие main rules плюс immutable source rules;
при новом drift объединять обе группы правил. Проверять actual conflict set заново.
