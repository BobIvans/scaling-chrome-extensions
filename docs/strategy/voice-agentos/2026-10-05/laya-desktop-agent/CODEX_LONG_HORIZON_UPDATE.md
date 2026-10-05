# Codex update — Universal Long-Horizon Laya Agent V2

This supersedes any interpretation that PR #55 only needs a selected-Grok round trip.

## Read first

- parent `VOICE_AGENTOS_CANONICAL_EXECUTION_MASTER.md`
- existing `laya-desktop-agent` files
- `RECOVERED_7081_AUTOMATION_VARIANTS_RU.md`
- `UNIVERSAL_LONG_HORIZON_AGENT_RU.md`
- `LAYA_UNIVERSAL_AUTONOMY_WORKFLOWS_V2.json`
- `LAYA_LONG_HORIZON_QUESTIONS_V2.json`
- `GROK_ATTACHMENT_CONTINUATION_WORKFLOW.json`
- `ANY_SOURCE_ENVELOPE.schema.json`
- `LONG_HORIZON_FUNCTION_BACKLOG.json`

## Required implementation outcome

The installed local app must support this full path:

`user goal → any source observation → durable goal state → Laya frontier ranking → generative planner only when needed → one admitted action → verifier → checkpoint → automatic continuation`.

It must specifically support:
1. selected Grok/Grok Build tab observation;
2. inventory of links/documents/attachments inside a conversation;
3. safe click/open/download + raw artifact ingestion;
4. parsing that artifact into new context;
5. Laya deciding the next route;
6. Grok returning a multi-step plan that is imported into H2/H1 rather than blindly executed;
7. independent read/research/test work continuing in parallel;
8. user foreground activity pausing only the conflicting UI lane;
9. unknown capability creating and qualifying a new tool, then resuming the original goal;
10. STOP/resume of unfinished work;
11. quota/event waiting and restart recovery;
12. no-progress detection and alternative replanning;
13. completion only from direct acceptance verifiers.

## Runtime ownership

Audit and reuse current owners:
- `automation_core.py`: durable queue/events/leases/STOP/recovery.
- `action_intent.py`: typed compiler and Laya boundary.
- `action_runtime.py`: target bindings, packets, effect attempts, reconcile/results.
- `browser_cdp.py` + extension/native bridge: browser observation/effects.
- repo/context modules: canonical source capture/groups/packets.
- Desktop: Workbench/Targets/Mission/Laya Inspector/Timeline.

Do not create a second scheduler, Core, state database, target registry or effect journal.

## Laya R&D

Benchmark/pin a real local runtime. Current candidates include the Python Laya stack with Router/batch/abstention and JS/ONNX variants. Record exact version/checkpoint/hash/backend and CPU/RAM/latency on target machine.

Laya consumes bounded DecisionState and typed questions. It never:
- generates shell;
- grants permissions;
- registers handlers;
- decides that an external effect already happened.

## Implementation slices

### V2-A Any-source + attachments
LH001–LH007 + LH028–LH029. Add extension/browser attachment inventory, exact element binding, allowed open/download, download receipt/hash, raw ingestion and tests.

### V2-B Goal horizons + Laya
LH008–LH019 + Laya questions/workflows. Persist H2/H1/H0; import provider multi-step plans; batch Laya routing; parallel read scheduler; progress/no-progress.

### V2-C Continuation/recovery
LH020–LH023 + LH030–LH031. Durable waits, human foreground leases, UNKNOWN reconciliation, feedback docs, work-session continuation.

### V2-D Capability growth
LH024–LH027. Gap → isolated adapter/tool → heldout/device qualification → immutable promotion → resume original goal.

### V2-E Long-horizon qualification
LH032. Real Windows/browser scenario:
selected Grok conversation → answer contains document → app detects/downloads/ingests it → Laya chooses next action → Grok proposes multiple steps → app executes only qualified H0 actions while tracking future horizon → a missing tool is built/qualified → original task resumes → acceptance is verified.

## Fault corpus

Wrong tab/account/conversation; attachment element drift; download interrupted/danger/duplicate; file parser failure; new tab inherits no action grant; user types into composer; provider quota; browser restart; process restart; crash after effect; ack lost; duplicate event; stale multi-step plan; Laya low confidence; repeated no-progress; capability build fails; repo HEAD changes; STOP while background lanes exist.

## Delivery

Implement actual code/tests/UI and keep docs/status updated. Split into cohesive PRs, but continue beyond the first selected-tab vertical. Do not mark V2 complete from mock tests alone.
