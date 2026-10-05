# App-Centric AgentOS V7 — Local app owns the system

Date: 2026-10-05
Baseline before this V7 branch: `main@3fb4a51f7d36f6e29bbda38226b66436d66d0fc4`.

## Product rule

The user-facing product is the local Windows application.

The Chrome extension is **not** the primary data/library/mission UI. It is a hidden, permission-scoped browser capability daemon that the local application calls when it needs to:

- enumerate/resolve tabs;
- observe a selected HTTP(S) site;
- materialize visible/virtualized content;
- inventory links/files/attachments;
- later, when a site adapter is qualified, fill/send/read/reconcile browser effects.

The local app owns:

- Library and lifetime context;
- projects/labels/relations;
- repos;
- Context Cart/packets;
- goals/missions;
- Laya System-1 routing;
- System-2 provider calls;
- campaigns/parallel lanes;
- capability growth;
- Git/GitHub verification;
- updater/rollback;
- evidence and receipts;
- STOP.

This preserves one canonical Core and avoids building a second extension-centric agent product.

## Everyday UX

Primary always-on-top controller remains intentionally tiny:

1. **Observe** — app asks hidden browser bridge to capture the active/selected site, obtains the exact new capture through authenticated loopback, and ingests it into canonical Library.
2. **Automate+** — goal + acceptance + explicit effect scopes; opens/controls mission runtime and optionally the full local Library/Repo workspace.
3. **STOP** — independent Core-level stop fence.

The app may open advanced local sections (Library, Repositories, Context Cart, Missions, Automations, Skills, Evidence) but Chrome does not become the main workspace.

## What V7 now implements in code

### App → browser observation
- authenticated loopback native bridge;
- Chrome background owns the bridge;
- exact active-tab resolution;
- new-capture revision verification;
- direct capture text return to the local app;
- hotkey/clipboard remains fallback only;
- one-time explicit Chrome grant for nativeMessaging + tabs + HTTP(S) origins.

### Canonical lifetime context
- local folder watcher;
- exact-byte hashing;
- canonical `durable.library CAPTURE`;
- canonical annotation/search wrappers;
- prior AI conversation export parser for ChatGPT-style mappings and generic `messages[]`;
- derived per-conversation searchable TXT while raw export remains preserved;
- read-only Google Drive v3 connector:
  - OAuth bearer or refresh-token flow from environment variables;
  - `files.list`;
  - blob download using `files.get?alt=media`;
  - Workspace document export via `files.export`;
  - bounded local cache;
  - exact hash;
  - canonical Library capture;
- no OAuth token is written into Library.

### Laya → System-2 cognition
- local Laya client remains the System-1 typed router;
- local app can relay a bounded Codex System-2 job through the already installed native host without using extension UI;
- typed local commands:
  - `system2.codex.submit`
  - `system2.codex.status`
  - `system2.codex.result`
- System-2 output is hash-verified, saved as a local artifact, captured into canonical Library, and returned to the same mission loop;
- bounded `MissionKernel`:
  - compile against registered Core capability first;
  - call Laya when configured;
  - route `GATHER_CONTEXT` without wasting a model call;
  - invoke System-2 for novel planning/tool design;
  - feed System-2 result back into context;
  - repeat only up to configured `max_system2_cycles`;
  - stop on repeated result/no-progress.

### GitHub/update groundwork
Already inherited from V6/current Core:
- free public merge polling with ETag;
- exact merge SHA as evidence;
- registered Git fetch;
- detached worktree;
- configurable tests;
- versioned staging;
- existing `release_updater.py` with isolated activation/rollback support.

## Not yet complete / do not overclaim

The following remain implementation or device-qualification work:

1. Pin/install/benchmark a real Laya runtime/checkpoint and expose health/latency/abstention receipts.
2. Persist full H2/H1/H0 goal/frontier graph in Core, not only the current bounded mission projection.
3. Generic effectful AI-site adapters:
   - exact account/workspace/conversation/session identity;
   - composer binding;
   - draft verification;
   - send-once;
   - result readback;
   - UNKNOWN reconciliation;
   - human takeover.
4. Adapter generation + frozen-corpus qualification for arbitrary new AI sites.
5. Provider-neutral System-2 registry beyond current local Codex relay (web adapters/headless/ACP/API/local models).
6. End-to-end capability-growth implementation:
   `GapSpec → existing/dormant capability search → candidate → isolated build/test → canary → REGISTERED → resume`.
7. Runtime PR creation/CI observation/exact-head merge for generated capability candidates.
8. Production unattended updater activation. Current release updater intentionally blocks unqualified production activation.
9. Google Drive OAuth onboarding UI / secure credential storage. V7 connector expects environment-provided OAuth material.
10. Rich Library labels/relations/backlinks UI beyond existing project/annotation/search primitives.
11. Automatic connectors for cloud AI histories that are not available as browser observations or exported files.
12. Full Studious Pancake R&D campaign execution/feedback integration. Template exists, live trading remains separate.
13. Installed Windows/browser/device qualification for the whole loop.

## Target autonomous loop

```
User goal
  → Local App
  → existing Library/repo/context
  → Laya System-1
      → known recipe → Core executor
      → need evidence → app connectors / hidden browser observer
      → need System-2 → selected qualified provider
      → capability gap → ToolCandidate pipeline
  → verifier
  → evidence delta
  → frontier rebuild
  → ...
  → acceptance verified
```

Capability growth:

```
missing capability
  → GapSpec
  → reuse/compose/dormant-code search
  → System-2 TOOL_DESIGNER if required
  → isolated candidate
  → unit/fault/heldout tests
  → canary
  → PR
  → CI
  → exact-head merge verification
  → build
  → stage
  → installed/device qualification
  → stable activation + rollback
  → resume original mission
```

## Flashloan / Studious Pancake use

The same AgentOS should support a long-running paper/simulation R&D mission:

- ingest current repo and deltas;
- gather market/RPC/DEX/Jito/data-source evidence;
- keep hypotheses separate from verified code/economics;
- create exact receiver-specific context packs for multiple AI providers;
- run simulations/tests in parallel safe lanes;
- ingest AI/code/test results;
- patch repo through qualified coding flow;
- maintain qualification evidence and next blockers;
- no live signing/trading capability is inferred from paper results.

## Single source of truth for Codex

Codex should start with this file, `V7_IMPLEMENTATION_MATRIX.json`,
`V7_REMAINING_FUNCTIONS.json`, and `V7_ACCEPTANCE_CAMPAIGN.json`.
Older V2–V6 documents remain source-of-intent and compatibility constraints, but V7 overrides their UI ownership: **local app is primary; browser extension is a hidden capability layer.**
