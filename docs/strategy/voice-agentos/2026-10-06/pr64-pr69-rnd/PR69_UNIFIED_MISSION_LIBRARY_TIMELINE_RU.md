# PR69 — Unified Mission / Library Timeline UI

## Thesis

Сделать локальный AgentOS понятным человеку: одна workspace surface для lifetime context, conversations, repos, current context, missions, H2/H1/H0, parallel lanes, providers, effects, evidence, STOP и reconciliation. UI — projection, не authority.

## 1. Unified navigation

Минимальные top-level sections:
- Library
- Conversations
- Repositories
- Context Packs
- Missions
- Capabilities
- System-2 Providers
- Updates / Qualification

Existing `desktop/app.py` / `desktop/library.py` reuse. Не дублировать transport/client.

## 2. Library relations/backlinks/collections

Canonical data model:
- typed edge: `from_ref`, `to_ref`, `relation_type`, provenance/evidence, created/updated;
- relation types: references, derived_from, contradicts, supersedes, supports, belongs_to_collection, produced_by_goal, produced_by_job, related_repo_commit etc.;
- collections are views/metadata, not physical duplicate files;
- backlinks computed from same canonical edges;
- deletion/tombstone does not silently erase historical provenance.

## 3. Mission timeline

For each goal show:
- spec/acceptance/effect scope;
- H2 milestones;
- H1 ranked frontier + utility components;
- current H0/parallel admission;
- each lane resource/effect/job/provider state;
- ProgressDelta/evidence refs;
- WAITING/UNKNOWN/BLOCKED reason;
- human foreground lease/yield;
- STOP epoch;
- capability gap/build/registration events;
- update activation/reconnect events.

Timeline reads canonical job/workflow/goal/provider/effect records. UI does not synthesize success.

## 4. Operator controls

Allowed controls map to existing typed operations:
- STOP;
- Resume after allowed reconciliation;
- cancel safe queued lane;
- inspect evidence;
- open exact source range;
- approve/deny explicit gated effect where policy allows;
- select provider/profile/collection filters.

No arbitrary shell/SQL/selector fields in UI.

## 5. Fast decision observability

Show why route was selected:
- Laya answer/confidence;
- deterministic utility;
- measured lane latency;
- blocked alternatives + reason;
- parallel plan resources;
- why an obsolete lane was cancelled after first useful evidence.

This is critical for debugging autonomy without reading raw logs.

## 6. Scale/UX

- pagination/virtualized lists for large Library/timeline;
- no requirement to load lifetime context into one widget/model prompt;
- background refresh bounded and cancelable;
- UI remains responsive while PR64 lanes run;
- STOP transport remains independent/high-priority.

## Acceptance

- one workspace can locate Library source → backlink → producing goal/job/evidence;
- mission restart shows same durable lane identities;
- UNKNOWN effect visible with blocked resource/reconciliation action;
- parallel lanes update independently without freezing UI;
- STOP remains available while ordinary UI request is busy;
- no UI action bypasses Core effect/resource gates;
- relations/backlinks survive restart and have provenance;
- large result sets paginate/virtualize;
- Windows installed usability remains separate device qualification.
