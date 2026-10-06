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
