# Voice AgentOS — Canonical Execution Master

Date: 2026-10-05  
Repository: `BobIvans/scaling-chrome-extensions`  
Source pack: `VOICE_AGENTOS_CANONICAL_EXECUTION_RND_MASTER_2026-10-05.zip`  
Source pack SHA-256: `89b0536327e9789c88da7020642ec7b0aa484ea895d5230444ea42950ffb3c02`  
Source pack bytes: `46,405,909`

This file is the repository-native canonical execution handoff extracted from the assembled Voice AgentOS R&D pack. It is intentionally readable by Codex in-place. The large binary ZIP is not treated as runtime truth: historical layers are preserved as design/provenance, while actual repository HEAD, tests, installed build and device readback remain authoritative.

## 1. Product goal

Build a local Windows Voice AgentOS / Context Library where voice, text and events become **verifiable actions**, not only model answers.

Canonical flow:

`voice/text/event → goal → source versions/context compiler → typed plan/recipe → exact target binding → registered executor → independent verifier → receipt → durable memory`

The system should preserve long-lived context across repositories, documents, exported chats/handoffs, Chrome/Grok/other AI sessions, Telegram/media/connectors and domain systems. Receiver/model context windows limit only the generated context packet, never the canonical stored corpus.

Primary ownership is the actual current `scaling-chrome-extensions` implementation after a fresh HEAD audit. `studious-pancake` remains a separate Web3/domain owner. Do not copy a reference runtime into this repository as a second Core.

## 2. What the assembled R&D contains

The merged strategy reconciled four source packs into one scope:

- 48 scenario families;
- 7,081 historical implementation/code routes;
- 228 workgroups;
- 255 workflow representations;
- 625 design proposals;
- 117 open decision/gate records;
- 200 proposed operations;
- reference durable-journal / binding / effect-engine / compiler tests.

These numbers are traceability/design inventory, **not proof that the features are implemented or installed**.

The pack's reference harnesses previously passed 71/71 tests. That validates only the reference mechanisms (idempotency, recovery, stale fences/bindings, STOP, source integrity and mock effects). It does **not** prove a live Chrome/Grok/Windows round trip in this repository.

## 3. Truth and evidence states

Use these states explicitly:

1. PRESERVED
2. SPECIFIED
3. IMPLEMENTED
4. LOCAL_TESTED
5. DEVICE_QUALIFIED
6. PUBLISHED_PR
7. MERGED_REMOTE
8. BUILT
9. INSTALLED_VERIFIED
10. DOMAIN_QUALIFIED

Never promote a capability by prose. Every transition requires direct evidence.

Source-of-truth order:

1. Current explicit user scope.
2. Actual repo/HEAD, installed readback and direct runtime evidence.
3. Exact preserved source bytes/criteria/identity.
4. This canonical contract.
5. Historical prototypes/plans only as design evidence.

## 4. Architecture locks

The following are invariants unless new direct evidence justifies a migration:

- **ONE_CANONICAL_CORE** for tasks, events, effects, permissions, receipts, idempotency, STOP and recovery.
- **RAW_FIRST_CONTENT_ADDRESSED_SOURCES**; SQLite WAL/FTS baseline is acceptable, while vector/temporal/code graphs are rebuildable projections.
- **EXACT_TARGET_BINDINGS** before any external effect.
- **ONE_WRITER_PER_EXTERNAL_RESOURCE**; immutable/read analysis may run in parallel.
- **LEASE + MONOTONIC FENCE** blocks stale writers.
- **EFFECT_INTENT_BEFORE_EXTERNAL_EFFECT**.
- **RECONCILE_UNKNOWN_BEFORE_RETRY**; crash/ack loss must not become a blind duplicate.
- **STOP_OUTSIDE_LLM** and human takeover are always available.
- Model output, webpage text, imported archives and retrieved content are untrusted data/proposals, not authority.
- Verifier/readback is separate from the actor where practical.
- Capability promotion is immutable/versioned and verifier-backed.
- Release means code → tests → PR → CI → merge → build → install → installed readback/health → rollback evidence. A `git pull` is not an installed update.

Component roles:

- Core: reuse current Content Lab/Core owners found in the actual repo.
- State: durable SQLite WAL + content-addressed blobs + FTS baseline.
- Desktop: evolve the existing UI owner; do not rewrite only for framework preference.
- Browser: existing Chrome attach/extension/native messaging/CDP or Playwright-compatible transport behind exact identity bindings.
- Windows: native/UI Automation before vision; human fallback when ambiguity remains.
- Routing: known recipes first; Laya may be a typed router/ranker/abstainer, never canonical memory or unrestricted executor.
- Agent sandbox: coding/CodeAct-like agents only in isolated worktrees/sandboxes with brokered tools, budgets and verifier.
- Voice: benchmark RU/EN/noise ASR candidates on the same corpus; verify critical slots before effects.
- Repo context: streaming manifest, exact byte/range reads and derived AST/import graph; chunking never replaces the full source vault.
- Provider adapters: Grok UI is the first user-value vertical; other providers/transports share the same request/response contract.
- Scheduler: durable local broker with journal, leases/fences, checkpoints and missed-run policy.
- Tool factory: immutable handler + schema + effect class + verifier version.
- Release: isolated worktree → tests → PR → CI → merge → build → install → readback/health → rollback.

Not yet locked without experiment: Tauri vs current shell, FTS-only vs LanceDB/Qdrant, Graphiti, exact Laya revision, Parakeet Redux vs faster-whisper, Stagehand/browser-use/DevTools MCP, and secondary Grok headless/ACP transport.

## 5. First real vertical — P0

**Selected Context → Selected Grok Tab → Verified Response**

This is not "find a selector and click Send." Success means the system can prove it acted on the selected profile/account/conversation and persisted the corresponding response.

Required steps:

1. Audit current repository owners and bind work to existing Core/UI/store/bridge code.
2. Create/select `SourceVersion + GoalRevision + ContextPacket` with exact hashes, anchors and missing/gap ledger.
3. Attach to an existing Chrome session and persist `TargetBinding(profile, session, tab, origin, account, conversation, branch, epoch, allowed_ops)`.
4. Implement read-only observation first; qualify long and virtualized chat coverage.
5. Add writer lease/fencing and durable `EffectIntent` before the first send.
6. Immediately before sending, revalidate binding, fence and STOP state; persist a request receipt/nonce.
7. Observe terminal/partial response, correlate it to the request and exact conversation, and persist raw response plus source anchors.
8. On ack loss/crash, reconcile from observable evidence; retry only after proven absence, otherwise end as `UNKNOWN`.
9. Expose progress, current step, blocker, STOP, takeover and final receipt.

P0 acceptance:

- 0 wrong-target effects on the frozen qualification corpus;
- 0 duplicate known sends after injected crash/restart;
- selected sources 100% accounted as available/partial/blocked/deferred;
- response tied to exact conversation/request;
- binding invalidates on account/chat/branch/epoch change;
- human typing into the target composer triggers handoff/revalidation;
- restart preserves verified prefix;
- `UNKNOWN` is visible and is never silently retried.

Required fault tests include wrong account/tab/chat/branch, reused tab, account switch, user typing in composer, long virtualized chat, packet split/attachments, stream stall, browser/service-worker restart, duplicate event, crash after send, ack lost, stale writer fence, STOP during send/wait, two writers, source revision change mid-run and prompt-injection attempts to expand permission.

## 6. Execution phases for the entire project

### V0 — Actual repo audit + strategy import

Goal: establish real HEAD/owners/installed state and integrate this strategy without replacing canonical owners.

Exit gates:

- repository instructions/AGENTS read if present;
- remote/base/head/dirty state captured;
- existing handlers/UI/store/bridge owners mapped;
- historical claims classified present/missing/stale;
- this strategy is available under `docs/strategy/voice-agentos/2026-10-05/`;
- implementation work uses an isolated branch/worktree.

### V1 — Context Core + large-source ingestion

Goal: repositories/docs/chat exports become durable source versions with exact reopening and bounded context packets.

Exit gates:

- streaming manifest handles binary, LFS, symlink, submodule, nested ZIP and gaps;
- content-addressed raw bytes verify by hash;
- exact range read + FTS baseline works;
- resumable import survives restart;
- context packet contains hashes/anchors/missing ledger;
- AST/import graph is derived, not source-of-truth.

### V2 — Existing Chrome → selected Grok round trip

Goal: first end-to-end user value.

Exit gates:

- exact profile/tab/account/conversation/branch/epoch binding;
- read-only observer capture qualified;
- writer lease/fence before first send;
- durable intent + nonce;
- context packet sent and read back;
- response correlated and persisted;
- crash-after-send resolves VERIFIED or UNKNOWN, never blind duplicate;
- STOP/takeover tests pass;
- 0 wrong-target effects in frozen corpus.

### V3 — Voice + recipes + durable scheduler

Goal: voice/text/hotkey create persistent tasks using known recipes that pause/resume safely.

Exit gates:

- RU/EN/noise ASR benchmark;
- critical slots verified;
- typed intent/recipe compile;
- event/schedule idempotency;
- missed-run/sleep/restart policy;
- global STOP outside model;
- parallel reads + serialized external writers.

### V4 — Capability gap → new tool → promotion

Goal: an unknown task can become a tested reusable capability without arbitrary code execution.

Exit gates:

- explicit gap object with unmet criterion;
- isolated coding worker;
- tool manifest/schema/effect class/verifier;
- unit + fault + heldout tests;
- immutable registry promotion;
- rollback/quarantine;
- original task resumes using the promoted version.

Candidate lifecycle:

`PROPOSED → BUILT_ISOLATED → TESTED → HELDOUT_PASS → DEVICE_QUALIFIED → PROMOTED_IMMUTABLE`

### V5 — Coding + GitHub + installed update loop

Goal: agent carries a code change to a verified installed release.

Exit gates:

- isolated worktree per writer;
- stale-head/conflict gates;
- PR/CI/merge receipts;
- build artifact hash;
- verified installer path as applicable;
- installed version readback + health;
- rollback tested;
- never claim updated app from `git pull` alone.

### V6 — Domain campaigns

Goal: add Studious/Web3, media/research, Telegram/connectors, knowledge graphs and other scenario families behind domain-specific verifiers.

Exit gates:

- each domain has frozen dataset/criteria;
- Studious/Web3 remains paper/simulation by default;
- 24h campaigns use real elapsed intervals and restart evidence;
- negative/blocked results are preserved;
- generic browser success never substitutes domain proof.

Live financial/signing effects remain disabled until a separate explicit signer policy, budget/risk boundary and live qualification exist.

### V7 — Parallel autonomy + self-improvement

Goal: parallel goals and reusable skills without losing evidence/resource control.

Exit gates:

- DAG scheduling with resource leases;
- no-progress detector and bounded attempts;
- trajectory → skill extraction with heldout evaluation;
- provider/model replacement without memory migration;
- continuous capability inventory and stale invalidation;
- human-readable receipts, STOP and recovery remain first-class.

## 7. Context Library rules

Store `SourceIdentity` and `SourceVersion` separately from blobs. Byte-identical content may deduplicate, but origin/revision/author must not collapse.

Manifest must account for text, binary, LFS pointer, symlink, submodule, nested ZIP and failed/blocked/deferred entries.

Retrieval baseline is exact path/range + FTS. Tree-sitter/symbol/import graph and SCC/module grouping are derived accelerators. Vectors/temporal graphs are experiments only if they improve measured retrieval.

The Context Compiler produces a packet, not a lossy replacement for the repository: selected parts, exact anchors/hashes, omitted/missing ledger, receiver budget, goal revision and provenance.

## 8. Skill / Tool Factory rules

If a registered capability is absent, create a Gap with typed IO, unmet criterion, effect class, resource scope, verifier and fixtures.

Generated code runs only in isolated worktrees/sandboxes and through brokered tools. Promotion requires tests, heldout evaluation, device qualification where relevant, immutable versioning and rollback. Trajectory mining may propose new recipes/skills but may not grant unrestricted whole-app self-rewrite.

## 9. Qualification and release rules

Minimum evidence record:

- criterion ID;
- source/task revision;
- actor and scope;
- exact target;
- handler/version/hash;
- input digest;
- observed artifact;
- verifier/version;
- environment/time;
- result and limitations.

A 24-hour campaign succeeds only after a real measured 24-hour interval with heartbeat/sleep/restart/missed-window evidence.

## 10. How Codex should execute this repository

1. Start with V0 against the **current** HEAD; do not trust this document for current file ownership.
2. Map existing `content-lab`, `agent-bridge`, `desktop`, browser/native and root handoff code to the phases.
3. Reuse existing owners; do not create parallel Core/store/queue abstractions.
4. Implement code, tests, fault injection, migration and evidence, not only docs.
5. Deliver work in cohesive PRs sized around verifiable verticals. Large PRs are acceptable when the scope is one coherent capability; do not combine unrelated irreversible effects just to reduce PR count.
6. Continue phase-by-phase V0 → V7. Do not stop merely because P0 is complete.
7. If a gate requires unavailable hardware/account/external qualification, implement and locally test everything possible, mark the exact remaining gate `BLOCKED` or `UNKNOWN`, and continue with independent work that does not fabricate that proof.
8. Before every external effect, preserve exact binding, EffectIntent, lease/fence, STOP and reconciliation invariants.
9. Every PR must state which phase/exit gates it advances, the tests run and what remains.
10. Never report PR/merge/build/install/device/domain qualification unless GitHub/runtime evidence directly supports it.

## 11. One-line execution command

Read `docs/strategy/voice-agentos/2026-10-05/VOICE_AGENTOS_CANONICAL_EXECUTION_MASTER.md` and `PHASES.json`, audit the actual current HEAD and existing owners first, then execute the Voice AgentOS program across this repository phase-by-phase V0→V7 (do not stop at planning/docs or P0): reuse existing Core/store/UI/bridge owners, implement code/tests/fault-recovery/evidence for each exit gate, preserve exact-target/EffectIntent/lease-fence/STOP/reconcile invariants, create appropriately scoped PRs, and continue until every implementable gate is satisfied; never claim merge/install/device/domain qualification without direct evidence, and record genuinely blocked external qualification instead of guessing.
