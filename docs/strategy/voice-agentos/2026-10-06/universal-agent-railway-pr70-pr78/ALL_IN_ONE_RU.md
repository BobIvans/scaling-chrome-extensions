# Voice AgentOS — Universal Agent Railway PR70–PR78 — ALL IN ONE

---

## FILE: `AMBIENT_LIFE_CONTEXT_RU.md`

# Ambient Life Context Harvester

Reuse BrowserWatch, streamed chat archive, conversation imports, Drive ingestor, folder watcher, canonical Library and labels.

## SourceAdapter
`discover() → SourceDescriptor[]`
`observe(cursor) → Change[]`
`materialize(change) → RawArtifact`
`derive(raw) → DerivedRecord[]`
`checkpoint()`

Adapters are data-only and never grant effect authority.

Planned adapters: browser page/chat/download; Drive/Docs/Sheets/Slides with OAuth onboarding; local files/downloads; repos; AI exports/live conversations; generic user-requested HTTP(S); media/PDF/docs/spreadsheets raw bytes + extractor projection; explicit email/Telegram/other connectors when configured.

Any-data principle: preserve raw bytes + MIME + origin + times + hash + source identity even when no extractor exists. Extraction/indexing is derived.

Labels deterministic first: source, mime, host, project, conversation, repo, status. Semantic labels are suggestions until policy applies them.

Every adapter has scope, pause, tombstone/delete, freshness and sensitivity controls.

---

## FILE: `APP_UI_EVOLUTION_RU.md`

# App UI evolution

Extension UI stays hidden. Local app is the control surface.

## Six primary controls
1. 🎙 Talk / Do — voice/text goal.
2. 👁 Observe — observe current surface/context only.
3. 📥 Harvest — one-shot/continuous lifetime-context ingestion.
4. 🪞 Shadow — background/duplicate surfaces when safe.
5. ⚡ Mission — Mission Cockpit / Automate+.
6. ⏹ STOP — independent durable fence, always visible.

## Mission Cockpit
Goal; Context; Surfaces; Lanes; Approvals; Timeline; Skills; Teach; Replay; Library.

Status strip:
Goal | H2 | active H1 lanes | H0/effect | human lease | shadow count | unresolved UNKNOWN effects | STOP epoch.

Human coexistence:
Take over immediately gives foreground lease to user. Release to Agent revalidates after quiet window. No hidden fight for cursor/focus.

---

## FILE: `CODEX_ONE_LINE.txt`

Open current main; finish docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd first, then read docs/strategy/voice-agentos/2026-10-06/universal-agent-railway-pr70-pr78/CODEX_START_HERE.md and implement PR70–PR78 as the Universal Agent Railway (SurfaceGraph + Shadow Workspace + Ambient Life Context + adaptive Laya Railway + universal executor ladder + trajectory learning + temporal context graph + continuous eval + Mission Cockpit/final Windows+Studious qualification), reusing canonical Core/Library/workflow_state/goal/site-adapter/updater owners and never claiming device/production completion without direct receipts.

---

## FILE: `CODEX_START_HERE.md`

# Codex start here — Universal Agent Railway completion

1. Read root `CODEX_START_HERE.md` and `docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd/` first.
2. Do not skip PR64–PR69.
3. Then implement PR70–PR78 in order unless live code proves a dependency can safely run in parallel.
4. Before each PR audit current main and extend existing owners instead of rewriting.
5. Treat IMPLEMENTED_VS_MISSING_RU.md as dated audit, not authority over newer code.
6. Local app remains product; extension is hidden browser capability layer.
7. Every observer/executor emits exact identity, provenance, resources, receipt, verifier and FailureEdge.
8. Laya ranks/chooses typed candidates only; deterministic code grants/executes effects.
9. Preserve human foreground leases and independent STOP.
10. “Done” is FINAL_ACCEPTANCE_RU.md plus direct receipts, not docs/tests alone.

---

## FILE: `FINAL_ACCEPTANCE_RU.md`

# Final acceptance

Not done merely because an agent can click a demo page.

Universal context: enabled sources harvest incrementally; raw originals recoverable; arbitrary MIME preserved; labels+temporal relations+provenance queryable; virtualized chats expose coverage/gaps.

Universal surface: exact tab/window/document identity; DOM/AX/CDP/UIA/WebMCP/native observations merge; controlled vision fallback; background tab can operate while user works foreground; same mutable conversation/composer one-writer.

Laya Railway: adaptive typed questions; NONE/OTHER/clarify; increasing consequence thresholds; System-2 only when needed; replay-tested railway versions.

Action: structured interfaces preferred; exact site send readback/send-once/reconcile; UNKNOWN blocks only conflicting resources after PR64; capability gap can build/canary/register/resume.

Human coexistence: supported shadow/background routes do not steal physical mouse/focus; human lease yields/revalidates; STOP remains independent.

Domain: one end-to-end Studious Pancake campaign uses Library history + repo/data-source research + simulation/paper lanes and produces evidence, never a live-trading claim without separate qualification.

Device: target Windows 11 + real Chrome/profile/accounts/Drive credentials, with crash/restart/sleep/tab/account/network/quota/update/focus-takeover receipts.

---

## FILE: `IMPLEMENTED_VS_MISSING_RU.md`

# Current code audit — implemented vs missing

Baseline: merged PR62/#63 plus PR64–PR69 docs handoff. Always re-audit current main before coding.

## Реально уже реализовано
- canonical local Library with raw bytes, search, annotations/labels, versions/provenance;
- streamed virtualized-chat archive with order/gaps/coverage + TXT/metadata/raw JSONL;
- BrowserWatch, folder/life-context watchers, previous-conversation importers, Google Drive download/export owner;
- generic browser UI inventory with fingerprints/risk and READ_NAV broker;
- Windows UIA inventory/action broker with revalidation and dangerous-action block;
- browser/Windows human foreground lease/yield;
- Laya client/supervisor + current static question file;
- FastDecision concurrent Library/browser/Windows prefetch + utility ranking;
- durable Goal/H2/H1/H0 + pending System-2/Core restart resume;
- capability candidate isolated qualification, PR/CI/exact-head merge path;
- staged renewal/update primitives;
- AI-site effect primitive is deeper than old matrix claimed: `local-agent/site_adapter.py` + `one-click-context/site-adapter.js` already implement qualified profile binding, origin/account/workspace/conversation identity, composer/send fingerprints, draft prepare/readback, EffectIntent, send-once, outgoing reconciliation and response reading. Tests prove fixture semantics, not universal real-site qualification.

## Не завершено end-to-end
1. Actual durable parallel Core workers/resources — PR64.
2. Provider-neutral System-2 — PR66.
3. Real-site universal qualification and dynamic discovery; current site adapter is selector/profile-based and not a universal Mission executor — PR67 + PR70/74.
4. WebMCP discovery/call path.
5. Exact native-window ↔ Chromium target/tab identity + background CDP.
6. Shadow/duplicate tabs allowing human and agent to coexist safely.
7. Universal SourceAdapter/any-MIME raw preservation + extractor routing.
8. Drive OAuth onboarding/secrets broker and broader connectors.
9. Typed relations/backlinks/collections + temporal entity/event/goal graph.
10. Demonstration recorder + trajectory/replay store.
11. Hybrid DOM/AX/CDP/UIA/vision SurfaceGraph.
12. Adaptive Laya question compiler + replay/canary railway evolution.
13. Universal executor ladder.
14. Mission Cockpit for surfaces/lanes/approvals/teach/replay/provenance.
15. Production-qualified activation/reconnect.
16. Real Windows installed fault/device campaign.
17. Studious Pancake paper/simulation campaign through the same AgentOS.

---

## FILE: `LAYA_RAILWAY_V2_QUESTION_LIBRARY.json`

{
  "schema": "voice-agentos.laya-railway-v2-questions.v1",
  "passes": {
    "route": [
      "next_mode:choice",
      "needs_clarification:noul",
      "progress_value:score",
      "risk_level:score"
    ],
    "evidence": [
      "best_source:choice",
      "evidence_sufficient:noul",
      "freshness_required:noul"
    ],
    "surface": [
      "target_surface:choice",
      "target_identity_exact:noul",
      "human_conflict:noul",
      "best_executor:choice"
    ],
    "action": [
      "action_candidate:choice",
      "expected_postcondition:choice",
      "action_reversible:noul",
      "needs_approval:noul"
    ],
    "critic": [
      "wrong_target_risk:noul",
      "better_read_only_route_exists:noul",
      "semantic_match:noul",
      "abort_or_wait:choice"
    ],
    "progress": [
      "meaningful_progress:noul",
      "closed_acceptance:allowed_ids",
      "next_parallel_lane_value:score",
      "obsolete_lanes:allowed_ids"
    ]
  },
  "thresholds": {
    "read": 0.7,
    "route_context": 0.78,
    "mutable_ui": 0.88,
    "consequential_effect": 0.93
  },
  "fail_closed": [
    "NONE_OR_OTHER_REQUIRED",
    "LOW_CONFIDENCE_REOBSERVE_OR_HUMAN",
    "MODEL_NEVER_GRANTS_EFFECT_AUTHORITY"
  ]
}

---

## FILE: `LAYA_RAILWAY_V2_RU.md`

# Laya Railway V2 — Adaptive Typed Question Compiler

Static `laya_questions.json` is not enough for “achieve anything.” Laya must receive the smallest sufficient typed decision set over exact code-generated candidates.

## DecisionStateV2
Contains bounded Goal/H2/H1/H0, acceptance/prohibitions/effect scope, SurfaceGraph, relevant ContextGraph evidence/gaps/freshness, exact ActionCandidates, human leases, active parallel lanes, known capabilities/GapSpecs and recent FailureEdges/trajectory hints.

## Adaptive passes
A Route — always:
- `next_mode Choice`: USE_KNOWN_CAPABILITY / RETRIEVE_CONTEXT / OBSERVE_SURFACE / ACT / ASK_SYSTEM2 / BUILD_CAPABILITY / WAIT / STOP
- `needs_clarification Noul`
- `progress_value Score`
- `risk_level Score`

B Evidence — only if context needed:
- best_source Choice
- evidence_sufficient Noul
- freshness_required Noul

C Surface/target — only for action:
- target_surface Choice
- target_identity_exact Noul
- human_conflict Noul
- best_executor Choice

D Action:
- action_candidate Choice
- expected_postcondition Choice
- action_reversible Noul
- needs_approval Noul (policy remains authority)

E Critic gate — effectful only:
- wrong_target_risk Noul
- better_read_only_route_exists Noul
- semantic_match Noul
- EXECUTE / REOBSERVE / ASK_SYSTEM2 / ASK_HUMAN / STOP

F After step:
- meaningful_progress Noul
- closed_acceptance IDs
- next_parallel_lane_value Score
- obsolete_lanes

## Thresholds
READ ~0.70; routing/context ~0.78; mutable browser/UI ~0.88; send/publish/delete/merge/install >=0.93 plus deterministic identity/effect gate and configured approval. NONE/OTHER/clarify must always exist.

## Evolution
Railway versions are code/data. System-2 may propose question changes after failures, but production questions change only after PR77 replay/canary promotion.

“1-by-1” means one internal decision edge at a time. User states the goal once; Railway iterates until it needs human intent/approval or reaches acceptance.

---

## FILE: `MASTER_CONTEXT_RU.md`

# MASTER CONTEXT — Universal Agent Railway

## Конечная цель
Local Windows 11 app — главный продукт. Chrome extension — скрытый capability daemon.

Приложение должно: принимать voice/text goal; автоматически находить нужный lifetime context; собирать previous AI conversations, Google Drive docs/files, local folders, repositories, downloads и доступные web sources; сохранять raw originals/hash/provenance/version/labels/relations; наблюдать tabs и Windows UI; выполнять независимые lanes параллельно; работать рядом с пользователем без борьбы за foreground; использовать exact account/workspace/conversation/tab/window/resource identity; выбирать WebMCP/MCP/API/COM/CLI/CDP/DOM/UIA/vision executor; делать mutable effects только через qualified effect contract + readback/reconcile; при gap строить/canary/register capability и продолжать исходную goal; использовать Laya как fast System-1 rail; записывать trajectories/failures/demonstrations; иметь Mission Cockpit; и использовать Studious Pancake paper qualification как реальный acceptance campaign.

## Уже есть
PR62: fast decision + parallel observation/prefetch.
PR63: persistent Goal/H2/H1/H0 + checkpoints/restart resume.
PR64–PR69 roadmap: durable parallel execution; capability promotion; provider-neutral System-2; effectful AI sites; release activation; unified timeline UI.

## Completion wave
PR70–PR78 adds universal surfaces, shadow workspaces, ambient life context, adaptive Laya Railway V2, universal ActionCompiler, trajectory memory/self-healing, temporal context graph, continuous eval/failure localization and final Windows/flashloan qualification.

---

## FILE: `PR70_UNIVERSAL_SURFACE_GRAPH_V10_RU.md`

# PR70 — Universal Surface Graph V10

## Purpose
Merge WebMCP/CDP/DOM/AX/extension/UIA/native/vision observations into exact SurfaceGraph; introduce surface identity and observer ladder.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Exact tab/window/document identity
- Observer ladder is deterministic
- WebMCP manifests are untrusted data
- Vision fallback has fixture corpus

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR71_SHADOW_WORKSPACE_PARALLEL_HUMAN_AGENT_COEXISTENCE_RU.md`

# PR71 — Shadow Workspace & Parallel Human-Agent Coexistence

## Purpose
Background CDP, duplicate read tabs, shadow leases and exact conversation/composer writer resources.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- User can keep foreground while safe background browser lane runs
- Duplicate read tab cannot become concurrent same-conversation writer
- Human Take Over fences conflicting resource
- Shadow state survives mission restart

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR72_AMBIENT_LIFE_CONTEXT_HARVESTER_RU.md`

# PR72 — Ambient Life Context Harvester

## Purpose
SourceAdapter registry, any-MIME raw preservation, Drive OAuth onboarding, downloads/AI chats/folders/connectors and automatic labels.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Raw artifact preserved without extractor
- Incremental checkpoints/dedup
- Source pause/delete/sensitivity controls
- Drive onboarding no longer requires hand-edited token env only

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR73_LAYA_RAILWAY_V2_RU.md`

# PR73 — Laya Railway V2

## Purpose
Adaptive typed question compiler with route/evidence/target/action/critic/progress passes and fail-closed thresholds.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Smallest sufficient question set
- Exact candidate IDs only
- Consequence-aware confidence gates
- Question versions replay-tested

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR74_UNIVERSAL_ACTION_COMPILER_EXECUTOR_LADDER_RU.md`

# PR74 — Universal Action Compiler & Executor Ladder

## Purpose
Compile semantic action to safest WebMCP/MCP/API/COM/CLI/CDP/DOM/UIA/vision executor with typed verifier.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Structured interface outranks click
- Every effect maps to local effect class/resources
- No arbitrary generated command authority
- GapSpec emitted when no route

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR75_TEACH_TRAJECTORY_MEMORY_SELF_HEALING_ADAPTERS_RU.md`

# PR75 — Teach + Trajectory Memory + Self-Healing Adapters

## Purpose
Demonstration recorder, semantic recipes, replay, drift localization and canary repair.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Teach creates immutable trajectory
- Recipe derived without secret capture
- Replay validates semantic postconditions
- Failed adapter can be repaired/versioned/canary promoted

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR76_TEMPORAL_CONTEXT_GRAPH_CONTEXTPACK_COMPILER_RU.md`

# PR76 — Temporal Context Graph & ContextPack Compiler

## Purpose
Typed temporal relations/backlinks and minimal goal-specific evidence packs.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Edges carry provenance/time
- Contradictions/supersession represented
- Bounded ContextPack references raw evidence
- Labels/FTS/graph/optional embeddings compose

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR77_CONTINUOUS_EVALS_FAILURE_LOCALIZATION_RAILWAY_PROMOTION_RU.md`

# PR77 — Continuous Evals + Failure Localization + Railway Promotion

## Purpose
Local regression harness, interaction-edge failure ownership and replay/canary for rail/skills/adapters.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- FailureEdge identifies repair owner
- Old successes replay against new rail
- Promotion requires non-regression gates
- Metrics cover success, latency, intervention and uncertainty

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `PR78_MISSION_COCKPIT_V2_WINDOWS_FLASHLOAN_FINAL_QUALIFICATION_RU.md`

# PR78 — Mission Cockpit V2 + Windows/Flashloan Final Qualification

## Purpose
Final app UI plus real installed Windows and Studious Pancake qualification campaigns.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Six primary controls work end-to-end
- Cockpit shows surfaces/lanes/approvals/timeline/teach/replay
- Installed Windows fault campaign receipts
- Studious Pancake paper campaign demonstrates multi-source multi-lane AgentOS

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.

---

## FILE: `README.md`

# Voice AgentOS — Universal Agent Railway Completion R&D (PR70–PR78)

Date: 2026-10-06. Repository: `BobIvans/scaling-chrome-extensions`.

This package continues — and does not replace — the canonical PR64–PR69 wave at:
`docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd/`.

End product: a local Windows 11 AgentOS that can observe browser/Windows surfaces, harvest lifetime context, coexist with the human through background/shadow surfaces, make fast typed System-1 decisions through Laya, escalate to System-2 only when needed, execute through the strongest verified interface, verify every effect, remember successful trajectories and self-heal through replay/canary.

Core railway:
`Observe Fabric → SurfaceGraph → Temporal ContextGraph → Candidate Actions → Laya typed questions → deterministic admission → executor ladder → receipt/verifier → ProgressDelta → trajectory memory → next decision`.

Vision is a fallback/cross-check, not the primary control plane.

## Order
1. Implement PR64–PR69 first.
2. Then implement PR70–PR78.
3. Reuse canonical Core/Library/workflow_state/goal/site-adapter/release owners.
4. Do not create a second DB, queue, effect ledger, resource manager or browser authority.
5. Never claim installed Windows/device/production/domain qualification without direct receipts.

---

## FILE: `RESEARCH_SOURCE_LEDGER.json`

{
  "schema": "voice-agentos.external-rnd-sources.v1",
  "observed_date": "2026-10-06",
  "sources": [
    {
      "name": "Microsoft UFO2 Desktop AgentOS",
      "url": "https://www.microsoft.com/en-us/research/project/agents-for-productivity/publications/",
      "use": "hybrid UIA/native/vision desktop AgentOS"
    },
    {
      "name": "Chrome WebMCP",
      "url": "https://developer.chrome.com/docs/ai/webmcp/",
      "use": "typed browser tools and structured actuation"
    },
    {
      "name": "Chrome WebMCP Security",
      "url": "https://developer.chrome.com/docs/ai/webmcp/secure-tools",
      "use": "indirect prompt injection/tool-manifest security"
    },
    {
      "name": "OpenCUA/AgentNet",
      "url": "https://github.com/xlang-ai/OpenCUA",
      "use": "trajectory/demonstration data and GUI agents"
    },
    {
      "name": "Jev typed decisions",
      "url": "https://github.com/realbogart/jev",
      "use": "Choice/Score/Noul bounded System-1 decisions"
    },
    {
      "name": "Jev browser skill",
      "url": "https://github.com/ChenYCL/jev-browser-skill",
      "use": "typed judgment + code-owned browser loop"
    },
    {
      "name": "UI-TARS Desktop",
      "url": "https://github.com/bytedance/UI-TARS-desktop",
      "use": "visual GUI-agent fallback reference"
    },
    {
      "name": "Cua Driver",
      "url": "https://github.blog/",
      "use": "browser CDP/native-window/background-control pattern; verify live implementation before adopting"
    }
  ],
  "note": "External sources inspire architecture; local code/tests/receipts remain implementation authority."
}

---

## FILE: `ROADMAP_PR70_PR78.json`

{
  "schema": "voice-agentos.universal-agent-railway.v1",
  "date": "2026-10-06",
  "depends_on": {
    "canonical_pr64_pr69": "docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd/"
  },
  "prs": [
    {
      "pr": 70,
      "title": "Universal Surface Graph V10",
      "purpose": "Merge WebMCP/CDP/DOM/AX/extension/UIA/native/vision observations into exact SurfaceGraph; introduce surface identity and observer ladder."
    },
    {
      "pr": 71,
      "title": "Shadow Workspace & Parallel Human-Agent Coexistence",
      "purpose": "Background CDP, duplicate read tabs, shadow leases and exact conversation/composer writer resources."
    },
    {
      "pr": 72,
      "title": "Ambient Life Context Harvester",
      "purpose": "SourceAdapter registry, any-MIME raw preservation, Drive OAuth onboarding, downloads/AI chats/folders/connectors and automatic labels."
    },
    {
      "pr": 73,
      "title": "Laya Railway V2",
      "purpose": "Adaptive typed question compiler with route/evidence/target/action/critic/progress passes and fail-closed thresholds."
    },
    {
      "pr": 74,
      "title": "Universal Action Compiler & Executor Ladder",
      "purpose": "Compile semantic action to safest WebMCP/MCP/API/COM/CLI/CDP/DOM/UIA/vision executor with typed verifier."
    },
    {
      "pr": 75,
      "title": "Teach + Trajectory Memory + Self-Healing Adapters",
      "purpose": "Demonstration recorder, semantic recipes, replay, drift localization and canary repair."
    },
    {
      "pr": 76,
      "title": "Temporal Context Graph & ContextPack Compiler",
      "purpose": "Typed temporal relations/backlinks and minimal goal-specific evidence packs."
    },
    {
      "pr": 77,
      "title": "Continuous Evals + Failure Localization + Railway Promotion",
      "purpose": "Local regression harness, interaction-edge failure ownership and replay/canary for rail/skills/adapters."
    },
    {
      "pr": 78,
      "title": "Mission Cockpit V2 + Windows/Flashloan Final Qualification",
      "purpose": "Final app UI plus real installed Windows and Studious Pancake qualification campaigns."
    }
  ],
  "final_state": "LOCAL_WINDOWS_AGENTOS_UNIVERSAL_OBSERVE_CONTEXT_DECIDE_EXECUTE_VERIFY_LEARN"
}

---

## FILE: `TEMPORAL_CONTEXT_GRAPH_RU.md`

# Temporal ContextGraph + ContextPack Compiler

Lifetime context stays local; models receive only a bounded evidence subgraph.

Nodes: Source, Artifact, Conversation, Message, Person/Agent, Account, Workspace, Site, Repo, File, Document, Goal, Decision, Action, Effect, Receipt, Skill, Surface, Event, Claim, AcceptanceCriterion.

Edges: DERIVED_FROM, VERSION_OF, PART_OF, MENTIONS, SUPPORTS, CONTRADICTS, SUPERSEDES, PRODUCED_BY, EXECUTED_ON, OBSERVED_AT, RELATED_TO, BELONGS_TO_PROJECT, REQUIRES, BLOCKS, SATISFIES, SAME_IDENTITY_AS.

Every edge is temporal/provenanced: valid_from, valid_until, observed_at, exact source refs.

ContextPack input: GoalState + SurfaceGraph + acceptance.
Output: exact evidence refs, relevant environment conventions, prior successful trajectories, contradictions, coverage gaps, candidate skills/providers.

Retrieval: identifiers/labels → FTS → graph neighborhood → optional embeddings → temporal/freshness ranking. Embeddings help discovery but never replace exact refs.

---

## FILE: `TRAJECTORY_MEMORY_SELF_HEALING_RU.md`

# Teach / Trajectory Memory / Self-Healing

Teach button records synchronized surface identities, DOM/AX/UIA summaries, optional screenshot digests, high-level mouse/keyboard actions without secret values, exact targeted controls, transitions/downloads and outcome/user rating.

Raw demo remains immutable. Derived recipe compresses to semantic steps and avoids brittle coordinates/selectors.

Replay: frozen fixtures + fresh read-only/canary + layout perturbations; verify semantic postconditions.

Failure repair:
FailureEdge → fresh SurfaceGraph → alternate tool/control/dormant match → optional System-2 contract update → replay → canary → promote adapter version → resume waiting goal.

Never silently rewrite production selectors/questions after one failure.

---

## FILE: `UNIVERSAL_ACTION_COMPILER_RU.md`

# Universal ActionCompiler + Executor Ladder

Laya chooses among admitted semantic candidates; it never writes selectors, shell commands, SQL or arbitrary tool calls.

## Preference
1 deterministic built-in/local function
2 WebMCP
3 registered MCP/application API
4 native API/COM
5 CLI/structured local owner
6 browser CDP
7 exact DOM/site adapter
8 Windows UIA
9 visual grounding + exact verifier
10 build/qualify new capability

ActionCandidate fields: action_id, semantic_goal, executor_id, target_surface_id, identity_binding, effect_class, resources, inputs_schema, preconditions, expected_postconditions, verifier, reversibility, approval_class, estimated_latency, failure_modes.

WebMCP names/descriptions/outputs are untrusted source text. Local code maps tools to effect classes and policy.

No route: GapSpec → dormant search → compose → System-2 candidate → isolated tests → canary → REGISTERED → resume waiting goal.

---

## FILE: `UNIVERSAL_SURFACE_AND_SHADOW_WORKSPACE_RU.md`

# Universal SurfaceGraph + Shadow Workspace

## Surface identity
OS: process_id, hwnd, executable, window class/title, UIA root.
Browser: profile/session, windowId, tabId/CDP targetId, origin, URL, document token, account/workspace/conversation identity.
Page: DOM/AX digest, WebMCP manifest digest, frames/controls.
Optional visual: screenshot digest + parsed controls.

Edges: NATIVE_WINDOW_FOR_TAB, DOCUMENT_IN_TAB, FRAME_IN_DOCUMENT, CONTROL_IN_SURFACE, TOOL_EXPOSED_BY_SURFACE, SHADOW_OF, SAME_ACCOUNT, SAME_CONVERSATION, DERIVED_FROM.

## Observer ladder
WebMCP → CDP DOM/AX/network/download → existing extension archive/DOM → Windows UIA/native API → OCR/visual grounding → raw screenshot evidence.

## Shadow browser modes
- BACKGROUND_EXACT_TAB: background CDP route when it does not steal focus.
- DUPLICATE_READ_TAB: same authenticated profile for read/research, separate document state.
- ISOLATED_AGENT_TAB: exploration/synthesis tab.
- SAME_CONVERSATION_WRITER: exactly one writer lease; never simultaneous sends from duplicated composers.

## Windows
Prefer background native API/COM/CLI; UIA only when safe/non-disruptive; otherwise yield foreground. Optional virtual/PiP desktop can be added later.

Resource identity must include site/account/conversation/composer, not only tab ID.

---

## FILE: `WEB_RESEARCH_SYNTHESIS_RU.md`

# External R&D synthesis — 2026-10-06

## Hybrid structured perception
Microsoft UFO² frames Windows automation as a Desktop AgentOS using UIA/native application interfaces with visual fallback. Direction for us: semantic structure first; vision fallback/cross-check.

## Exact browser/native surface identity
Cua Driver work demonstrates combining typed CDP browser state/actions with native window/accessibility and background browser control. Direction: bind process/window ↔ browser target/tab/document in one SurfaceGraph.

## WebMCP
Chrome WebMCP lets pages expose typed tools with names/descriptions/JSON schemas. Security guidance treats tool manifests/outputs as untrusted content vulnerable to indirect prompt injection. Direction: discover WebMCP before clicking, but keep authority/effect policy local.

## Demonstrations and trajectories
OpenCUA/AgentNet emphasizes synchronized UI/action trajectories and demonstration data. Direction: Teach mode → immutable trajectory → semantic recipe → replay/canary → skill.

## Typed System-1 rail
Jev ecosystem exposes Choice/Score/Noul. Community browser implementations feed exact allowed actions/DOM state to Jev and let code own the loop. Direction: Laya chooses among deterministic candidate IDs and never invents commands/permissions.

## GUI models
OpenCUA/UI-TARS/OmniParser-like approaches are useful for fallback visual grounding, but structured/browser/native routes should remain preferred for reliability/cost on modest local hardware.

## Repair ownership
Agent failures should be localized to observer/model/rail/provider/executor/memory/environment/verifier edges so the correct component is repaired.

## Earlier topology idea
The exact named “Lepton + Hugging Face Text-to-Topology DOM encoder” project from earlier R&D was not verified. Preserve the underlying topology-aware idea, but ground production implementation in DOM/AX/CDP/UIA/WebMCP; learned graph encoders remain optional experiments.
