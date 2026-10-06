# Voice AgentOS PR64–PR69 — ALL IN ONE R&D / IMPLEMENTATION HANDOFF

This file is a flattened mirror of the canonical ZIP for Codex navigation. The ZIP retains the structured individual files.


---

## FILE: `README.md`

# INDEX — Voice AgentOS PR64–PR69 R&D pack

- `MASTER_CONTEXT_PR64_PR69_RU.md` — полный контекст и invariants.
- `CODEX_START_HERE_PR64_PR69.md` — точка входа для Codex.
- `CURRENT_GAP_AUDIT_RU.md` — почему PR64 нужен прямо сейчас.
- `PR64_DURABLE_PARALLEL_EXECUTION_V9_RU.md`
- `PR65_CAPABILITY_CANARY_REGISTERED_GOAL_RESUME_RU.md`
- `PR66_PROVIDER_NEUTRAL_SYSTEM2_REGISTRY_RU.md`
- `PR67_EFFECTFUL_AI_SITE_RUNTIME_RU.md`
- `PR68_RELEASE_ACTIVATION_RECONNECT_RU.md`
- `PR69_UNIFIED_MISSION_LIBRARY_TIMELINE_RU.md`
- `ACCEPTANCE_MATRIX_PR64_PR69.json`
- `IMPLEMENTATION_DAG_PR64_PR69.json`
- `CODEX_TASKS_PR64_PR69.json`
- `RISK_FAULT_MATRIX_PR64_PR69.json`
- `SOURCE_OF_TRUTH_PR64_PR69.json`
- `CODEX_ONE_LINE_PR64_PR69.txt`
- `index.json` — hashes/bytes этого ZIP.

Implementation merge order: `64 → 65 → 66 → 67 → 68 → 69`.
Research/tests могут готовиться параллельно, но merge order сохраняет contracts.

---

## FILE: `MASTER_CONTEXT_PR64_PR69_RU.md`

# Voice AgentOS R&D: PR64–PR69 — MASTER CONTEXT

Дата фиксации: 2026-10-06  
Репозиторий: `BobIvans/scaling-chrome-extensions`  
Implementation baseline: `main@06fbd2f31776690a2b15888d8ab0dff9dd47961f` — после merge PR #62 (Fast Decision V8) и PR #63 (Persistent H2/H1/H0 Mission Runtime V8).

## 1. Цель пакета

Этот пакет — канонический R&D/implementation handoff для следующей шестёрки PR. Он не заменяет старый Voice AgentOS master-roadmap, а конкретизирует ближайшую линию развития после #62/#63:

`#64 Durable Parallel Execution V9` → `#65 Capability Canary → REGISTERED → Waiting Goal Resume` → `#66 Provider-Neutral System-2 Registry` → `#67 Qualified Effectful AI-Site Runtime` → `#68 Release Artifact + Qualified Activation + Reconnect` → `#69 Unified Mission/Library Timeline UI`.

Главная продуктовая цель остаётся прежней: локальный AgentOS — мозг, память, authority, mission runtime и lifetime Library; Chrome — скрытый capability driver; Windows UIA — второй UI driver; Laya — быстрый System-1; System-2 providers — сменные reasoning/coding workers; Core — единственный владелец effect authority, durable jobs, STOP, leases, reconciliation и evidence.

## 2. Что уже реально есть в baseline

- `local-agent/fast_decision.py`: настоящий concurrent prefetch через `ThreadPoolExecutor`, измерение latency, utility ranking, `parallel_plan()` для safe disjoint lanes.
- `content-lab/goal_runtime.py`: durable GoalState, H2, H1, один H0, revisions, ProgressDelta, effect/dependency gates.
- `local-agent/persistent_mission.py`: reopen goal, checkpoint pending System-2/Core job, restart resume, rebuild frontier.
- `content-lab/campaign_runtime.py` + `workflow_state.py`: DAG dependencies, READ/WRITE resource leases, capacity/demand, SAVEPOINT admission, UNKNOWN reservation/reconciliation.
- `content-lab/automation_core.py`: canonical jobs/STOP/cancel/reconciliation/worker, но политика всё ещё требует `max_parallel == 1`, а `Core.claim()` глобально сериализует RUNNING/NEEDS_RECONCILIATION.
- `local-agent/site_adapter.py`: уже есть важный effectful substrate — local registry, qualification digest, exact site binding, prepare, outbox, `effect_begin`, `send_once`, `reconcile_operation`, UNKNOWN effect handling. PR67 обязан завершать/квалифицировать этот owner, а не строить второй adapter runtime.
- `local-agent/self_renew.py` и `content-lab/release_updater.py`: verified staging и isolated qualification activation существуют; unattended production activation намеренно заблокирован.
- `desktop/app.py` / `desktop/library.py`: локальные UI surfaces существуют, но нет unified mission + Library + relations/backlinks + live parallel-lane timeline.

## 3. Главный обнаруженный архитектурный разрыв

У нас уже есть **parallel observation/planning/admission primitives**, но ещё нет **end-to-end durable parallel execution**.

Текущая ситуация:

1. Fast Decision может выбрать несколько независимых lanes.
2. Campaign runtime способен enqueue несколько независимых nodes и зарезервировать disjoint resources.
3. Persistent Mission умеет переживать restart, но хранит по сути один pending System-2/Core job path.
4. Core worker остаётся глобально serial: `validate_policy()` требует `max_parallel == 1`; `claim()` отказывается запускать новый job, если любой job RUNNING или NEEDS_RECONCILIATION.

Следовательно PR64 — не косметическая оптимизация. Это мост от «параллельно придумали/запланировали» к «параллельно исполняем, crash-safe, resource-safe, restart-safe, first-useful-evidence driven».

## 4. Канонические invariants PR64–PR69

Ни один из PR не имеет права нарушить следующие правила:

1. **One authority:** SQLite/Core остаётся authority. UI, Laya, browser page, AI result и provider plugin — не authority.
2. **One writer per mutable resource:** один composer/tab, один Git branch/worktree, один install pointer, один wallet/effect owner — сериализуются.
3. **Parallel where disjoint:** Library READ, repo read-analysis, independent providers, independent simulations и разные immutable resources могут идти параллельно.
4. **STOP wins:** durable STOP запрещает новые admissions и fences running owners. Никакой local worker/provider не обходит STOP.
5. **Unknown is not retry permission:** UNKNOWN effect блокирует конфликтующий resource до reconciliation; не создаёт слепой повтор.
6. **Restart is normal:** каждый long-lived lane имеет durable identity/checkpoint и может быть inspected/resumed/reconciled после crash/restart.
7. **Evidence before claim:** «job finished», «AI said DONE», «page changed» или «PR merged» не равны product acceptance без independent evidence.
8. **No duplicate runtimes:** не создавать новый queue, новую mission DB, второй resource manager, второй updater или второй site adapter, если существующий owner можно расширить.
9. **Foreground human ownership:** браузер/Windows foreground mutation всегда уступает человеку.
10. **Device qualification separate:** CI/local tests не являются доказательством installed Windows/Chrome/account/device qualification.

## 5. PR sequence

| PR | Название | Главная цель | Blocker для следующего |
|---|---|---|---|
| #64 | Durable Parallel Execution V9 | Сделать parallel lanes реально исполняемыми и restart-safe | Нужен для безопасного fan-out System-2 и long missions |
| #65 | Capability Canary → REGISTERED → Goal Resume | Автоматически довести GapSpec/candidate до зарегистрированного skill и разбудить waiting goal | Нужен для self-growth |
| #66 | Provider-Neutral System-2 Registry | Единый durable request/result contract для Codex/web/headless/API/local providers | Нужен для multi-provider parallel reasoning |
| #67 | Qualified Effectful AI-Site Runtime | Закрыть exact identity/composer/send/reconcile/response contracts и device qualification path | Нужен для browser providers с effects |
| #68 | Release Artifact + Qualified Activation + Reconnect | Версионированный artifact, predecessor/STOP/device gates, activation/rollback/rebind/resume | Нужен для безопасного self-update |
| #69 | Unified Mission/Library Timeline UI | Library/Conversations/Repos/Context/Missions + relations/backlinks + lane timeline | Делает систему наблюдаемой и управляемой человеком |

## 6. Что НЕ входит в этот пакет

- PR70 Studious Pancake full parallel paper/simulation qualification — следующий domain campaign после PR69.
- Никакая торговля/live wallet effect не включается этим roadmap.
- Не утверждается DEVICE_QUALIFIED для Dell/Windows/Chrome/accounts.
- Не включается «автоматически merge/install everything» без явных grants и receipts.
- Не заменяется текущая canonical Library model context-ом.

## 7. Source of truth для Codex

Перед реализацией каждого PR Codex обязан прочитать:

1. Этот `MASTER_CONTEXT_PR64_PR69_RU.md`.
2. `CODEX_START_HERE_PR64_PR69.md`.
3. Документ конкретного PR.
4. `CURRENT_GAP_AUDIT_RU.md`.
5. `ACCEPTANCE_MATRIX_PR64_PR69.json` и `IMPLEMENTATION_DAG_PR64_PR69.json`.
6. Текущий `main`, текущие tests/workflows и live GitHub state — номера/SHA из этого пакета являются baseline snapshot, а не вечной истиной.

## 8. Definition of done для всей волны

Волна PR64–PR69 считается реализованной только если:

- parallel lanes не только планируются, но реально работают одновременно при disjoint resources;
- crash/restart/lease expiry/STOP/UNKNOWN не создают double effects;
- first useful evidence может re-rank frontier и отменить лишние lanes;
- missing capability способен пройти candidate → tests → canary → REGISTERED и waiting goal продолжится;
- System-2 provider заменяем без изменения mission semantics;
- effectful AI-site send имеет exact identity + draft readback + send-once + reconcile;
- production activation требует реальных predecessor/STOP/device receipts, умеет rollback и reconnect;
- UI показывает canonical live state, но не получает authority;
- все applicable CI gates green на exact PR heads;
- device gates остаются честно NOT_RUN/OPEN до реального устройства.

---

## FILE: `CODEX_START_HERE_PR64_PR69.md`

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

---

## FILE: `CURRENT_GAP_AUDIT_RU.md`

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

---

## FILE: `PR64_DURABLE_PARALLEL_EXECUTION_V9_RU.md`

# PR64 — Durable Parallel Execution V9

## Thesis

Сделать parallelism частью canonical durable execution, а не только Fast Decision metadata. После PR64 независимые jobs должны реально выполняться одновременно, переживать restart и использовать один resource authority.

## Current blockers to remove

- `automation_core.validate_policy`: fixed `max_parallel == 1`.
- `Core.claim`: any RUNNING/NEEDS_RECONCILIATION globally blocks new claim.
- no generic job↔resource-admission binding outside campaign-specific node records.
- Persistent Mission has one active pending job model.

## Proposed architecture

### 1. Generic job admission binding

Добавить в canonical workflow state generic binding (название может быть уточнено, но owner должен быть один):

`workflow_job_admissions(job_id, owner, goal_id?, lane_id?, effect_class, binding_digest, lease_owner, state, created, updated)`.

Resource leases остаются в существующих `workflow_leases/workflow_reservations`; новая таблица только связывает canonical Core job с уже существующим lease owner. Не дублировать resource truth.

Legacy jobs без binding должны считаться conservative writer/global resource, пока migration/admission не докажет более узкий scope.

### 2. Atomic multi-admission

Добавить canonical operation уровня Goal/Campaign, которая:

1. revalidates goal revision/STOP epoch;
2. checks candidate dependencies/effect scope;
3. выбирает disjoint H1 candidates;
4. acquire resources/capacity в одной SQLite transaction;
5. enqueue canonical jobs;
6. записывает lane bindings;
7. возвращает durable `parallel_admission` receipt.

Single H0 остаётся backward compatible. Можно реализовать `ADMIT_MANY`/`PARALLEL_ADMIT`, где one-item batch эквивалентен старому admit.

### 3. Resource-aware Core claim

Новая логика `claim()`:

- считает RUNNING slots против operator `max_parallel`;
- не claim job при конфликте его resource binding с active/UNKNOWN lease;
- допускает параллельный claim disjoint resources;
- expired RUNNING переводит job в reconciliation/UNKNOWN и сохраняет его resource reservation;
- UNKNOWN блокирует только конфликтующие resources;
- legacy unbound UNKNOWN остаётся global blocker.

Default конфигурация остаётся conservative (`max_parallel=1`), чтобы старый policy не становился автоматически многопоточным.

### 4. Worker pool

Нужен bounded worker supervisor, но authority остаётся SQLite. Реализация может использовать threads/processes, однако tests должны доказать correctness с несколькими независимыми `Core` owners/processes.

Обязательные свойства:
- max workers operator-owned;
- no busy loop;
- exact lease token per job;
- heartbeat renews both job lease and resource fence;
- STOP visible всем workers;
- shutdown не объявляет unfinished effects failed/safe без reconciliation.

### 5. Durable mission lanes

Расширить Persistent Mission checkpoint до массива lanes:

```json
{
  "parallel_runtime": {
    "revision": 1,
    "lanes": [
      {
        "lane_id": "repo_read",
        "candidate_id": "...",
        "job_id": "...",
        "resources": ["repo:X:read"],
        "state": "RUNNING",
        "effect_class": "LOCAL_READ",
        "result_digest": null,
        "evidence_refs": []
      }
    ]
  }
}
```

Не сохранять transient thread objects. Только durable identifiers/bindings.

### 6. First useful evidence wins

Когда lane выдаёт meaningful evidence:
- ingest ProgressDelta immediately;
- rebuild/rerank H1;
- если acceptance/route изменился, pending lanes классифицировать KEEP/CANCEL/LET_FINISH;
- cancel only when effect semantics permit;
- already-dispatched unknown effects не отменять как будто эффекта не было.

### 7. STOP semantics

STOP:
- increments durable epoch;
- no new parallel admissions;
- marks queued lanes CANCELLED_BEFORE_DISPATCH;
- running lanes get cancel request;
- unknown resource reservations remain until reconciliation;
- Goal checkpoint сохраняется и может RESUME на новом epoch после explicit revalidation.

## Files likely touched

Primary:
- `content-lab/automation_core.py`
- `content-lab/workflow_state.py`
- `content-lab/campaign_runtime.py`
- `content-lab/goal_runtime.py`
- `content-lab/native_adapter.py`
- `local-agent/core_client.py`
- `local-agent/persistent_mission.py`
- `local-agent/fast_decision.py`
- `local-agent/mini_controller.py`

Tests:
- new `content-lab/test_parallel_core.py`
- extend campaign/goal/workflow tests
- extend `local-agent/tests/test_persistent_mission.py`
- fault tests with crash/restart/expired lease/STOP.

## Mandatory acceptance scenarios

1. 3 disjoint READ/LOCAL_PROCESS jobs become RUNNING concurrently.
2. Two WRITE jobs for same resource never overlap.
3. READ+READ same resource can overlap; READ+WRITE cannot.
4. capacity/demand limits block only affected lane.
5. one UNKNOWN resource does not freeze unrelated lanes.
6. legacy UNKNOWN remains conservative-global.
7. crash one worker → expired lease → only its resources require reconciliation.
8. app restart restores lane set without duplicate enqueue/send.
9. first useful evidence causes immediate replan and safe cancellation of obsolete lane.
10. STOP prevents new admissions and fences all current owners.
11. no double terminal transition under racing workers.
12. CI passes Linux+Windows exact head; installed-device parallel performance remains separate qualification.

## Non-goals

- no provider fanout yet beyond existing owners;
- no arbitrary AI send qualification;
- no production activation;
- no UI redesign.

---

## FILE: `PR65_CAPABILITY_CANARY_REGISTERED_GOAL_RESUME_RU.md`

# PR65 — Capability Canary → REGISTERED → Waiting Goal Resume

## Thesis

После PR64 AgentOS должен не только обнаруживать capability gap и генерировать patch, но и завершать безопасный reusable lifecycle до состояния, в котором исходная durable goal может автоматически продолжиться.

## Existing owners to extend

- `content-lab/action_intent.py` / action runtime gap states;
- `local-agent/capability_candidate.py` — artifact/hash/manifest/isolation/tests;
- `local-agent/github_capability_pr.py` — PR/CI/exact-head merge;
- Core skill lifecycle APIs;
- `local-agent/self_renew.py` — verified staging;
- Goal checkpoint/resume from PR63/PR64.

Не создавать отдельный plugin marketplace DB.

## Lifecycle

`GAP_DETECTED` → `DORMANT_SEARCH` → (`REUSED` | `BUILD_REQUESTED`) → `CANDIDATE` → `FIXTURE_QUALIFIED` → `MERGED_SOURCE` → `STAGED` → `CANARY_PENDING` → `CANARY_PASS` → `REGISTERED` → `WAITING_GOALS_REPLANNED`.

Failure states должны быть durable и не уничтожать исходную goal.

## 1. Typed GapSpec

First-class record:
- `gap_id`;
- normalized capability contract;
- inputs/outputs;
- effect class;
- verifier/postcondition;
- required resources;
- requester goal/lane;
- evidence refs;
- compatible existing skill criteria;
- policy/grant requirements.

GapSpec — data, не permission на код/merge/install.

## 2. Dormant capability search first

До генерации нового кода:
- search registered skills;
- repo symbol/import/closed-PR/history search;
- staged but not registered candidates;
- compatible older contract versions.

Если найден reusable capability, провести requalification against current dependencies вместо generation.

## 3. Canary contract

CANARY не равен production activation.

Canary должен иметь:
- exact artifact/source commit/contract digest;
- isolated or marked target;
- bounded fixture/input set;
- expected effects/resources;
- independent readback/postcondition;
- rollback/cleanup;
- no claims of device qualification unless actual target device receipt exists.

## 4. REGISTERED binding

Skill может стать REGISTERED только если совпадают:
- capability id/version;
- contract digest;
- installed artifact digest;
- dependency digests;
- qualification receipt;
- scope/effect class;
- target profile.

REGISTERED событие публикуется в canonical Core/Library evidence.

## 5. Waiting goal subscription/resume

Когда goal/lane blocked by gap:
- checkpoint `waiting_for_capability` with gap_id + contract digest;
- goal не polling blindly every few ms;
- REGISTERED event finds compatible waiters;
- reopens goal revision;
- rebuilds frontier;
- capability must be revalidated at admission time;
- no automatic effect if effect scope/grant changed while waiting.

## 6. Parallel interaction

PR64 позволяет одновременно:
- искать dormant implementation;
- запускать System-2 designer;
- продолжать unrelated research lanes.

First successful qualified path invalidates/cancels redundant build lanes where safe.

## Acceptance

- gap survives restart;
- dormant reusable capability wins before code generation;
- malformed/changed artifacts never promote;
- CI green alone cannot REGISTER;
- canary failure rolls back candidate state and keeps goal blocked, not lost;
- exact REGISTERED event wakes only compatible goals;
- changed effect scope prevents resume effect;
- duplicate REGISTERED notifications are idempotent;
- multiple goals may wait on one capability and resume independently;
- capability invalidation re-blocks future admissions but does not rewrite historical receipts.

---

## FILE: `PR66_PROVIDER_NEUTRAL_SYSTEM2_REGISTRY_RU.md`

# PR66 — Provider-Neutral System-2 Registry

## Thesis

Mission runtime не должен знать «Codex» как единственный тип System-2. Нужен единый provider contract, в который могут подключаться local Codex relay, headless/ACP, HTTP API, local model и позднее qualified browser-site provider.

## Core rule

Provider возвращает proposals/results/artifacts, но не получает effect authority. Effects всегда проходят Core/H0/resource/effect contracts.

## Proposed owner

`local-agent/system2_registry.py` + plugin modules. Existing `control_bridge.codex_submit/codex_result` становится первым adapter, не удаляется.

## Provider descriptor

- `provider_id`;
- plugin kind/version/code digest;
- capabilities: REASON / RESEARCH / CODE / ARTIFACT / STREAM;
- transport class;
- mutable-session resource identity;
- context/input limits;
- qualification receipt;
- secrets/token env references by name only;
- cost/latency class supplied by local policy;
- allowed roles/modes.

## Uniform request

- request_id;
- goal_id/lane_id;
- role;
- instruction digest;
- context refs / bounded packet;
- requested output contract;
- artifact contract;
- deadline/budget;
- no direct effect scope grant.

## Uniform result

- provider_id/request_id;
- state: QUEUED/RUNNING/WAITING/COMPLETE/FAILED/CANCELLED/UNKNOWN;
- text/result digest;
- evidence refs;
- artifact descriptors with hashes;
- provider receipt/latency;
- finish reason;
- no `criterion_verified=true` unless independent verifier sets it elsewhere.

## Durable fanout and hedging

PR64 worker/lane model should support:
- launch provider A/B/C on disjoint sessions;
- first-useful-result or quorum policy;
- cancel redundant pending calls where transport semantics allow;
- keep COMPLETE results as evidence even if not selected;
- provider crash/restart poll by request id;
- mutable browser composer/session represented as WRITE resource.

## Plugins in PR66

Required:
1. `codex_relay` adapter over existing bridge.
2. one headless/subprocess/ACP-shaped plugin contract with test fixture (real external setup may remain NOT_RUN).
3. generic HTTP/API plugin interface using local policy and token env names; tests use local fake server/fixture, not external spend.
4. local-model plugin interface for process/loopback providers.
5. browser-site plugin type may be registered but effectful send remains qualification-gated until PR67.

## Selection

Laya/FastDecision may rank providers using measured latency/qualification/capability/cost class. Deterministic fallback must exist. A provider must not be selected solely because its page/model text says it is capable.

## Acceptance

- MissionKernel no longer hardcodes Codex semantics for System-2 lifecycle;
- existing Codex path remains compatible;
- two providers can run concurrently after PR64;
- provider result survives app restart;
- wrong request_id/result digest is rejected;
- provider secret values never persist in receipts;
- provider failure does not erase other lanes;
- mutable provider session conflicts are serialized by resource identity;
- disabled/unqualified provider cannot be selected for roles outside grant;
- zero-spend tests remain possible with fixtures/local fake providers.

---

## FILE: `PR67_EFFECTFUL_AI_SITE_RUNTIME_RU.md`

# PR67 — Qualified Effectful AI-Site Runtime

## Thesis

Довести существующий `site_adapter.py` from substrate to qualified runtime for effectful AI sites. Не делать generic blind click/send. Каждое отправление привязывается к exact site identity, exact composer, durable EffectIntent и reconciliation.

## Existing implementation to preserve

`SiteAdapterRegistry/Runtime` уже имеет profile/contract digest, qualification object, bind, prepare, outbox, `send_once`, Core effect transitions, UNKNOWN reconciliation и read. PR67 расширяет и квалифицирует этот owner.

## Required contracts

### Exact identity
Binding должен различать как минимум:
- origin/provider;
- account identity evidence;
- workspace/org/project;
- conversation/thread;
- branch/session where applicable;
- tab/document token;
- adapter version/code digest/contract digest.

Нельзя send, если required identity field UNKNOWN/AMBIGUOUS или drifted после prepare.

### Composer binding
- exact element/fingerprint;
- visibility/enabled state;
- focus/selection semantics;
- human activity lease;
- pre-draft empty/current value observation;
- max text bytes;
- attachment state if provider supports attachments.

### Draft prepare + independent readback
`prepare()` обязан после mutation прочитать composer заново и доказать exact draft digest. Если readback differs — no send.

### Send once
- durable outbox bytes/hash;
- EffectIntent before dispatch;
- exact send control fingerprint;
- one dispatch attempt per effect revision;
- post-send observation tied to outgoing draft digest/message identity;
- exception/timeout → reconcile, not blind repeat.

### UNKNOWN reconciliation
- observe conversation/outgoing message history;
- if exact outgoing evidence exists → OBSERVED;
- if independent evidence proves not applied → NOT_APPLIED may permit a later re-dispatch;
- ambiguous remains UNKNOWN and blocks same composer/conversation WRITE resource.

### Response stream reader
- response message identity/branch;
- streaming vs final state;
- chunk/result digest;
- attachments/artifacts inventory;
- completion/cancel/error reason;
- preserve raw archive in Library when useful.

## Qualification corpus

Frozen fixtures + device canary must include:
- wrong account;
- wrong workspace;
- wrong conversation;
- composer replaced between bind and send;
- selector drift;
- page navigation/document token drift;
- duplicate/outgoing already present;
- send timeout after actual dispatch;
- human takeover during prepare;
- response branch change;
- virtualized message list;
- restart in DISPATCHING/UNKNOWN.

## Integration with PR66

Qualified AI site becomes a `browser_site` System-2 provider. Provider request uses PR66 contract; actual message dispatch uses PR67 exact effect contract. Provider registry does not bypass site qualification.

## Parallel semantics

- two different qualified conversations may run concurrently if resources disjoint;
- same composer/conversation WRITE resource serializes;
- read-only observation may continue while another site is sending;
- human foreground lease wins.

## Acceptance

- no send on unqualified profile/code/contract drift;
- exact draft readback before send;
- duplicate prevention survives restart;
- timeout never automatically resends;
- wrong-target fixture always blocks;
- account/conversation drift invalidates binding;
- response capture returns typed COMPLETE/STREAMING/FAILED state;
- all effect receipts are Core-bound and inspectable;
- live provider/device qualification remains explicit per provider/account profile.

---

## FILE: `PR68_RELEASE_ACTIVATION_RECONNECT_RU.md`

# PR68 — Release Artifact + Qualified Activation + Reconnect

## Thesis

Закрыть безопасный путь от merged/tested code до production-qualified installed version без подмены CI device qualification-ом и без self-update, который может оставить AgentOS без stable controller.

## Existing owners

- `local-agent/self_renew.py`: fetch exact merge, detached worktree, tests, staged desktop version receipt.
- `content-lab/release_updater.py`: exact asset/binding, isolated qualification target, data rehearsal, pointer/rollback mechanics.

PR68 объединяет их через release contract; не создаёт третий updater.

## 1. Release artifact builder

Versioned artifact must include:
- source commit/tree;
- all shipped file hashes;
- dependency/runtime versions;
- desktop/backend protocol versions;
- migration/schema compatibility declaration;
- capability manifest;
- build/test provenance;
- artifact digest;
- reproducible verification command.

Artifact cannot be inferred from mutable checkout after build.

## 2. Stable controller boundary

Activation authority lives outside candidate version. Candidate cannot declare itself healthy and delete predecessor.

Stable controller owns:
- active pointer;
- predecessor pointer;
- activation intent;
- STOP receipt;
- qualification receipt;
- health deadline;
- rollback.

## 3. Production activation prerequisites

Required exact bindings:
- predecessor installed receipt;
- candidate artifact digest;
- source commit;
- installation/device id;
- durable Core STOP epoch/receipt;
- no unresolved conflicting install resource;
- device qualification receipt matching candidate + target profile;
- migration/rehearsal result;
- explicit local policy/grant for `INSTALL_UPDATE`.

Missing any gate → STAGED/WAITING, not activated.

## 4. Atomic activation

- write activation intent;
- verify predecessor still active;
- switch stable pointer atomically;
- launch/reconnect candidate through stable controller;
- perform independent health/readback;
- commit activation receipt only after health;
- otherwise rollback pointer to predecessor and record failure.

Canonical user data must not be copied/mutated by candidate without qualified migration contract.

## 5. Post-update reconnect/resume

After success:
- re-open Core connection/identity;
- verify adapter/backend bundle hashes;
- reconnect browser bridge;
- revalidate provider/site code digests;
- reopen durable goals;
- inspect PR64 lane states/resources;
- requeue only NOT_APPLIED/safe work;
- UNKNOWN effects stay reconciliation-required;
- rebuild H1 based on new capabilities.

## 6. Rollback

Rollback must remain possible if:
- process fails startup;
- health contract fails;
- native protocol mismatch;
- capability registry cannot load;
- required file/hash missing;
- post-update reconnect fails before acceptance.

Rollback itself creates durable evidence and does not erase failed candidate receipts.

## Acceptance

- candidate cannot self-authorize production activation;
- exact predecessor and STOP receipt are mandatory;
- wrong device/artifact/commit receipt blocks activation;
- pointer switch is atomic;
- health failure restores predecessor;
- restart mid-activation reconciles intent/pointer instead of blind switching;
- successful activation resumes compatible goals and lanes without duplicate effects;
- unresolved UNKNOWN site/Git/install effects remain blocked;
- all previous versions/data remain recoverable according to retention policy.

---

## FILE: `PR69_UNIFIED_MISSION_LIBRARY_TIMELINE_RU.md`

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

---

## FILE: `ACCEPTANCE_MATRIX_PR64_PR69.json`

```json
{
  "schema": "voice-agentos.pr64-pr69-acceptance.v1",
  "baseline_main": "06fbd2f31776690a2b15888d8ab0dff9dd47961f",
  "prs": [
    {
      "pr": 64,
      "title": "Durable Parallel Execution V9",
      "gates": [
        {
          "id": "64A",
          "name": "Concurrent disjoint execution",
          "criteria": [
            "at least 3 disjoint durable jobs can be RUNNING concurrently",
            "max_parallel is operator-bound with conservative default",
            "same mutable WRITE resource never overlaps"
          ]
        },
        {
          "id": "64B",
          "name": "Resource-scoped unknown",
          "criteria": [
            "UNKNOWN preserves resource reservation",
            "unrelated resources continue",
            "legacy unbound unknown remains conservative-global"
          ]
        },
        {
          "id": "64C",
          "name": "Restart-safe lanes",
          "criteria": [
            "goal stores durable lane identities",
            "restart does not duplicate enqueue/effect",
            "expired owner requires reconciliation"
          ]
        },
        {
          "id": "64D",
          "name": "First useful evidence",
          "criteria": [
            "meaningful result triggers immediate ProgressDelta",
            "frontier reranks before all lanes finish",
            "obsolete lanes cancel only when safe"
          ]
        },
        {
          "id": "64E",
          "name": "STOP",
          "criteria": [
            "STOP fences new parallel admission",
            "queued lanes cancel before dispatch",
            "running/unknown lanes retain correct reconciliation state"
          ]
        }
      ]
    },
    {
      "pr": 65,
      "title": "Capability Canary REGISTERED Goal Resume",
      "gates": [
        {
          "id": "65A",
          "name": "GapSpec",
          "criteria": [
            "gap is durable and typed",
            "gap carries effect/verifier/resources",
            "gap cannot grant authority"
          ]
        },
        {
          "id": "65B",
          "name": "Reuse before generation",
          "criteria": [
            "registered/dormant candidates searched first",
            "compatible old skill can requalify",
            "duplicate builders may be cancelled after winner"
          ]
        },
        {
          "id": "65C",
          "name": "Canary promotion",
          "criteria": [
            "STAGING CANARY REGISTERED transitions are explicit",
            "canary binds artifact+contract+target",
            "failure never registers"
          ]
        },
        {
          "id": "65D",
          "name": "Waiting goal resume",
          "criteria": [
            "waiting goal survives restart",
            "REGISTERED wakes only compatible goals",
            "scope/grants revalidated before resumed effect"
          ]
        }
      ]
    },
    {
      "pr": 66,
      "title": "Provider-Neutral System-2 Registry",
      "gates": [
        {
          "id": "66A",
          "name": "Uniform contract",
          "criteria": [
            "provider request/result schemas independent of Codex",
            "result/artifact hashes verified",
            "provider output has no effect authority"
          ]
        },
        {
          "id": "66B",
          "name": "Durable providers",
          "criteria": [
            "request can be resumed/polled after restart",
            "provider failure isolated",
            "secrets not persisted"
          ]
        },
        {
          "id": "66C",
          "name": "Parallel fanout",
          "criteria": [
            "multiple qualified providers can run via PR64 lanes",
            "mutable session resources serialize",
            "first-useful/quorum policy can cancel redundant safe calls"
          ]
        }
      ]
    },
    {
      "pr": 67,
      "title": "Qualified Effectful AI-Site Runtime",
      "gates": [
        {
          "id": "67A",
          "name": "Exact site identity",
          "criteria": [
            "account/workspace/conversation/session binding explicit",
            "drift invalidates binding",
            "unknown identity blocks send"
          ]
        },
        {
          "id": "67B",
          "name": "Draft readback",
          "criteria": [
            "composer fingerprint exact",
            "prepared draft independently read back",
            "human takeover blocks effect"
          ]
        },
        {
          "id": "67C",
          "name": "Send-once reconciliation",
          "criteria": [
            "EffectIntent precedes dispatch",
            "timeout never blindly resends",
            "UNKNOWN reconciles using outgoing evidence"
          ]
        },
        {
          "id": "67D",
          "name": "Response capture",
          "criteria": [
            "response identity and stream/final state typed",
            "artifacts are hashed",
            "restart preserves pending response read"
          ]
        }
      ]
    },
    {
      "pr": 68,
      "title": "Release Artifact Qualified Activation Reconnect",
      "gates": [
        {
          "id": "68A",
          "name": "Artifact provenance",
          "criteria": [
            "artifact digest and source tree pinned",
            "shipped file hashes verifiable",
            "mutable checkout not authority"
          ]
        },
        {
          "id": "68B",
          "name": "Activation gates",
          "criteria": [
            "predecessor receipt required",
            "STOP receipt required",
            "device qualification and INSTALL_UPDATE grant required"
          ]
        },
        {
          "id": "68C",
          "name": "Atomic activate rollback",
          "criteria": [
            "stable controller owns pointer",
            "health failure rolls back",
            "restart mid-activation reconciles"
          ]
        },
        {
          "id": "68D",
          "name": "Reconnect resume",
          "criteria": [
            "Core/browser/providers rebound",
            "goals/lanes reopened",
            "UNKNOWN effects are not retried"
          ]
        }
      ]
    },
    {
      "pr": 69,
      "title": "Unified Mission Library Timeline UI",
      "gates": [
        {
          "id": "69A",
          "name": "Unified workspace",
          "criteria": [
            "Library Conversations Repos Context Missions available from one surface",
            "existing transport reused",
            "UI is projection only"
          ]
        },
        {
          "id": "69B",
          "name": "Relations",
          "criteria": [
            "typed relations/backlinks/collections durable",
            "provenance attached",
            "large sets paginated"
          ]
        },
        {
          "id": "69C",
          "name": "Mission timeline",
          "criteria": [
            "H2 H1 H0 and parallel lanes visible",
            "provider/effect/evidence/STOP/UNKNOWN events visible",
            "restart shows same lane identities"
          ]
        },
        {
          "id": "69D",
          "name": "Control safety",
          "criteria": [
            "STOP independent and always available",
            "operator controls call typed Core operations",
            "no arbitrary shell/SQL/UI selector authority"
          ]
        }
      ]
    }
  ]
}
```

---

## FILE: `IMPLEMENTATION_DAG_PR64_PR69.json`

```json
{
  "schema": "voice-agentos.pr64-pr69-dag.v1",
  "baseline_main": "06fbd2f31776690a2b15888d8ab0dff9dd47961f",
  "nodes": [
    {
      "id": "PR64",
      "depends_on": [],
      "produces": [
        "resource-aware concurrent Core",
        "durable parallel lanes",
        "scoped unknown reconciliation",
        "first-useful-evidence cancellation"
      ],
      "must_preserve": [
        "STOP",
        "legacy serial safety",
        "campaign leases",
        "goal revisions"
      ]
    },
    {
      "id": "PR65",
      "depends_on": [
        "PR64"
      ],
      "produces": [
        "GapSpec",
        "dormant search",
        "canary promotion",
        "REGISTERED wake/resume"
      ],
      "must_preserve": [
        "explicit merge/install grants",
        "artifact hashing",
        "device gate"
      ]
    },
    {
      "id": "PR66",
      "depends_on": [
        "PR64"
      ],
      "produces": [
        "System2 registry",
        "uniform provider jobs",
        "parallel provider fanout"
      ],
      "must_preserve": [
        "Codex compatibility",
        "provider no effect authority",
        "secret hygiene"
      ]
    },
    {
      "id": "PR67",
      "depends_on": [
        "PR66"
      ],
      "produces": [
        "qualified browser-site provider",
        "exact send-once",
        "response stream contract"
      ],
      "must_preserve": [
        "site_adapter owner",
        "human foreground lease",
        "UNKNOWN reconciliation"
      ]
    },
    {
      "id": "PR68",
      "depends_on": [
        "PR64",
        "PR65"
      ],
      "produces": [
        "release artifact",
        "production activation contract",
        "rollback",
        "reconnect/resume"
      ],
      "must_preserve": [
        "stable controller",
        "predecessor",
        "STOP/device receipts",
        "data integrity"
      ]
    },
    {
      "id": "PR69",
      "depends_on": [
        "PR64",
        "PR65",
        "PR66",
        "PR67",
        "PR68"
      ],
      "produces": [
        "unified workspace",
        "relations/backlinks/collections",
        "live mission timeline"
      ],
      "must_preserve": [
        "UI projection only",
        "pagination",
        "independent STOP"
      ]
    }
  ],
  "parallelizable_research": [
    [
      "PR65 design/tests",
      "PR66 provider contract research"
    ],
    [
      "PR67 frozen fixture corpus",
      "PR68 artifact-format research"
    ],
    [
      "PR69 UI mock/data-query design"
    ]
  ],
  "merge_order": [
    64,
    65,
    66,
    67,
    68,
    69
  ]
}
```

---

## FILE: `CODEX_TASKS_PR64_PR69.json`

```json
{
  "schema": "voice-agentos.pr64-pr69-codex-tasks.v1",
  "baseline_main": "06fbd2f31776690a2b15888d8ab0dff9dd47961f",
  "tasks": [
    {
      "pr": 64,
      "id": "64.1",
      "task": "Introduce generic canonical job-to-resource admission binding using existing workflow_state leases."
    },
    {
      "pr": 64,
      "id": "64.2",
      "task": "Evolve policy/claim from global serial to bounded resource-aware max_parallel with default serial compatibility."
    },
    {
      "pr": 64,
      "id": "64.3",
      "task": "Add worker-pool/supervisor execution and concurrency/race tests."
    },
    {
      "pr": 64,
      "id": "64.4",
      "task": "Add durable goal parallel lane admission/checkpoint/restart model."
    },
    {
      "pr": 64,
      "id": "64.5",
      "task": "Implement scoped UNKNOWN and first-useful-evidence cancel/replan."
    },
    {
      "pr": 65,
      "id": "65.1",
      "task": "Persist typed GapSpec and waiters."
    },
    {
      "pr": 65,
      "id": "65.2",
      "task": "Search registered/dormant repo capabilities before generation."
    },
    {
      "pr": 65,
      "id": "65.3",
      "task": "Implement STAGING→CANARY→REGISTERED contract and receipts."
    },
    {
      "pr": 65,
      "id": "65.4",
      "task": "Wake/revalidate/replan waiting goals after compatible REGISTERED event."
    },
    {
      "pr": 66,
      "id": "66.1",
      "task": "Implement provider-neutral registry/descriptors and request/result schemas."
    },
    {
      "pr": 66,
      "id": "66.2",
      "task": "Wrap existing Codex relay as first plugin without regression."
    },
    {
      "pr": 66,
      "id": "66.3",
      "task": "Add headless/API/local plugin interfaces with zero-spend fixtures."
    },
    {
      "pr": 66,
      "id": "66.4",
      "task": "Integrate durable fanout/hedging with PR64 lanes."
    },
    {
      "pr": 67,
      "id": "67.1",
      "task": "Audit existing site_adapter and bridge site methods; keep one runtime owner."
    },
    {
      "pr": 67,
      "id": "67.2",
      "task": "Strengthen exact identity/composer/readback/human lease contract."
    },
    {
      "pr": 67,
      "id": "67.3",
      "task": "Complete send-once/NOT_APPLIED/UNKNOWN reconciliation and frozen fault corpus."
    },
    {
      "pr": 67,
      "id": "67.4",
      "task": "Implement typed response streaming and PR66 browser_site plugin integration."
    },
    {
      "pr": 68,
      "id": "68.1",
      "task": "Build immutable release artifact/provenance manifest from exact merged source."
    },
    {
      "pr": 68,
      "id": "68.2",
      "task": "Implement stable controller production activation prerequisites and intent."
    },
    {
      "pr": 68,
      "id": "68.3",
      "task": "Atomic pointer activation, independent health, rollback/restart reconciliation."
    },
    {
      "pr": 68,
      "id": "68.4",
      "task": "Reconnect Core/browser/providers and resume compatible goals/lanes."
    },
    {
      "pr": 69,
      "id": "69.1",
      "task": "Add typed canonical relations/backlinks/collections model and API."
    },
    {
      "pr": 69,
      "id": "69.2",
      "task": "Unify Desktop navigation across Library/Conversations/Repos/Context/Missions."
    },
    {
      "pr": 69,
      "id": "69.3",
      "task": "Add mission H2/H1/H0/parallel lane/provider/effect/evidence timeline."
    },
    {
      "pr": 69,
      "id": "69.4",
      "task": "Add safe operator controls and scale/pagination/responsiveness tests."
    }
  ]
}
```

---

## FILE: `RISK_FAULT_MATRIX_PR64_PR69.json`

```json
{
  "schema": "voice-agentos.pr64-pr69-risk-fault.v1",
  "risks": [
    {
      "id": "R1",
      "area": "parallel-core",
      "fault": "two writers claim same mutable resource",
      "required_result": "one admission blocked; no concurrent effect"
    },
    {
      "id": "R2",
      "area": "parallel-core",
      "fault": "worker crashes after dispatch before receipt",
      "required_result": "lane/resource UNKNOWN or reconciliation-required; no blind retry"
    },
    {
      "id": "R3",
      "area": "parallel-core",
      "fault": "STOP races with multi-admission",
      "required_result": "transaction/epoch prevents post-STOP new dispatch"
    },
    {
      "id": "R4",
      "area": "capability",
      "fault": "candidate code changes after tests",
      "required_result": "digest drift blocks promotion"
    },
    {
      "id": "R5",
      "area": "capability",
      "fault": "REGISTERED event delivered twice",
      "required_result": "idempotent wake/replan"
    },
    {
      "id": "R6",
      "area": "provider",
      "fault": "provider returns wrong request id or stale result",
      "required_result": "reject binding"
    },
    {
      "id": "R7",
      "area": "provider",
      "fault": "one provider hangs while another succeeds",
      "required_result": "first useful evidence advances goal; safe redundant call cancelled"
    },
    {
      "id": "R8",
      "area": "ai-site",
      "fault": "account/workspace changes after prepare",
      "required_result": "send blocked"
    },
    {
      "id": "R9",
      "area": "ai-site",
      "fault": "send timeout after server accepted message",
      "required_result": "UNKNOWN; reconcile before any retry"
    },
    {
      "id": "R10",
      "area": "update",
      "fault": "candidate starts but health fails",
      "required_result": "stable controller restores predecessor"
    },
    {
      "id": "R11",
      "area": "update",
      "fault": "power/process loss during pointer switch",
      "required_result": "reconcile active/predecessor/intent deterministically"
    },
    {
      "id": "R12",
      "area": "ui",
      "fault": "UI busy during STOP",
      "required_result": "independent STOP transport still fences Core"
    },
    {
      "id": "R13",
      "area": "ui",
      "fault": "timeline pagination/reload",
      "required_result": "no loss/reordering of canonical durable event identity"
    }
  ]
}
```

---

## FILE: `SOURCE_OF_TRUTH_PR64_PR69.json`

```json
{
  "schema": "voice-agentos.pr64-pr69-source-of-truth.v1",
  "created_at": "2026-10-06",
  "repository": "BobIvans/scaling-chrome-extensions",
  "implementation_baseline": "06fbd2f31776690a2b15888d8ab0dff9dd47961f",
  "baseline_note": "main immediately after merge PR #63; future Codex must refresh live refs before coding",
  "canonical_pack_path": "docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd/",
  "root_entrypoints": [
    "CODEX_PR64_PR69_START_HERE.md",
    "CODEX_START_HERE.md",
    "MASTER_CONTEXT.md"
  ],
  "secondary_entrypoint": "docs/automation/PR64_PR69_RND_POINTER.md",
  "existing_owners": [
    "content-lab/automation_core.py",
    "content-lab/workflow_state.py",
    "content-lab/campaign_runtime.py",
    "content-lab/goal_runtime.py",
    "content-lab/native_adapter.py",
    "local-agent/fast_decision.py",
    "local-agent/persistent_mission.py",
    "local-agent/mission_kernel.py",
    "local-agent/core_client.py",
    "local-agent/site_adapter.py",
    "local-agent/self_renew.py",
    "content-lab/release_updater.py",
    "desktop/app.py",
    "desktop/library.py"
  ],
  "do_not_duplicate": [
    "Core jobs queue",
    "workflow resource leases",
    "Goal runtime",
    "site adapter runtime",
    "release updater",
    "Desktop transport",
    "canonical Library"
  ],
  "next_pr": 64,
  "planned_last_pr": 69
}
```

---

## FILE: `CODEX_ONE_LINE_PR64_PR69.txt`

```text
Open current main of BobIvans/scaling-chrome-extensions and read docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd/CODEX_START_HERE_PR64_PR69.md plus MASTER_CONTEXT_PR64_PR69_RU.md, refresh live refs/CI, preserve the merged Fast Decision V8 + Persistent Mission V8 owners, then implement PR64 Durable Parallel Execution V9 first: make the existing Core/workflow_state/campaign/goal stack execute disjoint durable lanes concurrently with resource-scoped leases/UNKNOWN reconciliation, restart-safe lane checkpoints, first-useful-evidence reranking/cancellation and STOP fencing while keeping conservative serial compatibility; do not create a second queue/resource manager/mission DB, do not start PR65 effects before PR64 acceptance is proven, and never claim device/production qualification without exact receipts.
```
