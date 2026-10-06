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
