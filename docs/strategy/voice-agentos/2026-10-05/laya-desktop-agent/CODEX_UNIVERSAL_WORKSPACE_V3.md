# Codex update — Universal Workspace + Inverse Goal Planning V3

This is the next implementation layer after Long-Horizon V2.

## Product outcome

Build one installed local workspace that feels like Notion + repo intelligence + agent control:

- Home/Inbox
- Library
- Conversations
- Repositories
- Context Cart
- AI Targets
- Missions/Actions
- Automations/Campaigns
- Skills/Tools
- Evidence/Receipts
- Work Sessions
- Settings/Policies

Do not build a second store or separate app. Reuse the current one-click-context Library/workspace, Desktop, Context Library, repo modules and durable action runtime.

## Read V3 contracts

- `UNIVERSAL_WORKSPACE_PRODUCT_RU.md`
- `INVERSE_GOAL_PLANNING_RU.md`
- `MASTER_7081_TO_WORKSPACE_MAPPING_RU.md`
- `WORKSPACE_SECTIONS.json`
- `LIBRARY_RECORD.schema.json`
- `UNIVERSAL_GOAL.schema.json`
- `LAYA_ACTION_ONTOLOGY.json`
- `LAYA_INVERSE_SCENARIO_LATTICE.json`
- `LAYA_MENTAL_FRAMES.json`
- `LAYA_DECISION_QUESTIONS_V3.json`
- `LAYA_UNIVERSAL_WORKFLOWS_V3.json`
- `UNIVERSAL_AUTOMATION_SCENARIOS.json`
- `LIBRARY_LABEL_TAXONOMY.json`
- `UNIVERSAL_WORKSPACE_FUNCTION_BACKLOG.json`

## Implementation strategy

### V3-A Workspace shell + Library
Map current canonical data into LibraryRecord views. Add navigation, global search, tags/labels/collections/backlinks/history. Preserve current project/session and annotation behavior.

### V3-B Conversations + Repos + Context Cart
Add dedicated conversation workspace and repo workspace. Implement open-loop extraction and cross-source Context Cart/context sets.

### V3-C Mission editor + inverse planner
Persist UniversalGoal. Derive anti-goals. Generate candidate frontier from forward/backward/premortem/counterexample/bottleneck/information-gain frames. Keep H2/H1/H0 separation.

### V3-D Laya utility routing
Pin a real local Laya runtime/checkpoint. Batch choice/score/noul questions. Record probabilities/confidence/latency/checkpoint digest. Deterministic policy combines component scores; Laya does not grant effects.

### V3-E Automation surfaces
Inbox processor, selected-target watcher, repo watcher, work-session continuation, waiting-goal resume after event/quota/new capability.

### V3-F Skills/Evidence/Settings + device qualification
Expose capability lifecycle and receipts. Qualify installed Windows navigation and cross-surface flows.

## Critical end-to-end scenarios

1. Import arbitrary file → Library → Laya labels → search → Context Cart → selected Grok → response → Mission.
2. Clone repo → full scan → focused pack → Mission → Grok multi-step plan → H1/H0 → patch/test/PR.
3. Observe Grok attachment → download → Library → relate to repo/mission → next action automatically.
4. User works in Chrome → background repo/research lanes continue → UI lane resumes later.
5. Missing capability → prioritized by unlock_count → tool imported/generated/qualified → all compatible waiting missions resume.
6. AI says DONE → inverse/counterexample completion gate → verifier → close or replan.
7. No progress → inverse route selection instead of repeating the same prompt.
8. Next-day Work Session resume → capture delta/staleness → rebuild frontier.

## Constraint

"Automate anything" means accept arbitrary goals and compose/extend typed capabilities. It does not mean unrestricted shell/click authority. Unknown effects and irreversible operations stay behind explicit registered effect gates.

Implement actual runtime/UI/tests and update status docs. Do not stop at documentation.
