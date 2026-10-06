# CURRENT GAP AUDIT — что реально отсутствует после PR62/PR63

## A. Durable parallel execution

### Уже есть
- `FastDecisionEngine.prefetch()` выполняет независимые Library/browser/Windows reads concurrent.
- `FastDecisionEngine.parallel_plan()` строит safe disjoint lane plan.
- `campaign_runtime.advance()` может за одну транзакцию admission зарезервировать READ/WRITE resources и enqueue несколько независимых nodes.
- `workflow_state.acquire()` уже умеет конфликт READ/WRITE, resource epochs, capacity/demand и UNKNOWN reservation.
- Goal runtime хранит durable H2/H1/H0 и ProgressDelta.

### Фактический blocker
- `automation_core.validate_policy()` требует `max_parallel == 1`.
- `Core.claim()` прекращает admission нового job при наличии любого `RUNNING` или `NEEDS_RECONCILIATION`.
- `Core.run_once()` исполняет один claim.
- PersistentMissionController checkpoint хранит один `pending_kind/job_id`, а не durable set lanes.
- `parallel_plan` сейчас decision metadata; он не создаёт автоматически canonical parallel jobs.

### Следствие
Campaign DAG может admission несколько jobs, но canonical worker фактически сериализует их. UNKNOWN одного legacy job может остановить всю очередь вместо только конфликтующего resource.

## B. Capability self-growth

### Уже есть
- action/capability gap foundations;
- System-2 artifacts;
- `CAPABILITY_MANIFEST.json` + patch verification;
- isolated worktree/tests;
- GitHub PR/required-check/exact-head merge pipeline;
- skill lifecycle API pieces;
- verified update staging.

### Осталось
- typed GapSpec as first-class durable record;
- dormant capability search before generation;
- explicit STAGING→CANARY→REGISTERED promotion;
- registered capability contract digest bound to install/runtime identity;
- waiting goals subscription + wake/replan after REGISTERED.

## C. Provider-neutral System-2

### Уже есть
- Codex relay through browser/bridge;
- Laya fast router;
- mission checkpoint for one System-2 job.

### Осталось
- provider registry and uniform request/result/event schema;
- provider qualification/capability declarations;
- headless/ACP/API/local/browser plugin adapters;
- durable fan-out/hedging/cancel/restart semantics;
- resource identity for mutable sessions/composers.

## D. Effectful AI sites

Важно: это не greenfield.

`local-agent/site_adapter.py` уже содержит:
- local profile registry;
- selector/contract digest;
- qualification object;
- exact bind;
- prepare;
- durable outbox;
- Core effect begin/transition;
- send_once;
- reconcile_operation;
- UNKNOWN effect handling;
- read.

Поэтому PR67 должен закрыть qualification completeness: account/workspace/conversation/session identity, composer fingerprint/readback, human takeover, branch/response completion, wrong-target/drift/restart fixtures, provider plugin integration.

## E. Production activation

### Уже есть
- verified source stage;
- isolated qualification target activation;
- version directories/pointer concepts;
- data rehearsal;
- rollback primitives.

### Осталось
- release artifact owner/provenance manifest;
- stable controller outside candidate;
- predecessor identity receipt;
- durable STOP receipt tied to activation;
- real device qualification receipt;
- atomic activation + post-activation health;
- automatic rollback on failed health;
- reconnect/rebind Core/browser/providers and resume goals/lanes.

## F. Unified workspace

### Уже есть
- Library/search/context/package/repo UI;
- Mini Observe/Automate+/STOP;
- canonical labels and annotations;
- goal/list APIs.

### Осталось
- typed relations/backlinks/collections;
- one navigation surface: Library / Conversations / Repos / Context / Missions;
- mission H2/H1/H0/parallel-lanes timeline;
- provider/executor/verifier/evidence events;
- human takeover/STOP/UNKNOWN/reconciliation visibility;
- UI actions remain projections onto Core, not state owners.
