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
