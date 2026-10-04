# PR-018 + PR-019: release, durable campaigns и следующий R&D brief

Когда registered campaign запускается, каждый node теперь получает canonical Core job,
immutable input binding, resource fence и сохранённый результат. После restart planner
видит эти же jobs; повтор не создаёт второй job/effect. После сбора, отрицательного
experiment и stage-only update следующий brief сохраняет исходные goals/criteria и
реальные отрицательные результаты. Draft можно получить до установки приложения.

Это реализация компонентов шести workstreams. Исходные 45 task cards и 147 criteria
сохранены без сокращения. Все 147 source criteria остаются OPEN до соответствующих
integration/device/independent-verifier receipts; успешный unit test не закрывает
автоматически большой product criterion. №018/019 — номера roadmap packages, не
GitHub PR numbers. Полный перечень: `pr018-019-criterion-status.json`.

## Владельцы и готовые функции

| Область | Реализация | Фактическая граница |
| --- | --- | --- |
| State/resource ledger | `workflow_state.py` | Existing `content.sqlite3`, version guard, transactional CAS/events, atomic capacity reservation, resource epochs, effect intent/UNKNOWN/reconciliation |
| Schedule | `durable_schedule.py` + existing tick/supervisor | Versioned daily IANA wall time, DST gap/fold, bounded catch-up ledger, canonical enqueue in same transaction, restart/backward clock/history/capacity wait |
| Campaign | `campaign_runtime.py` | Immutable validated DAG, registered templates, input hash fences, dependency admission, deadline/attempt/admission budgets, refresh with selective successful receipt reuse |
| Queue controls | `native_adapter.py`, bridge, `campaign-ui.mjs` | Scoped inspect/advance/pause/resume/STOP, 20-row page with continuation; aliases only, no incoming paths/argv/manifests |
| Final Git observation | `workflow_runtime.observe_merge` | Real merge/squash/manual/cherry-pick trees, per-path mode/blob mapping incl deletes, final detached worktree tests, fresh target and repository identity |
| GitHub observation | `workflow_github.py` | Existing authenticated GET/CI transport; actual PR/head/base/repo, latest CI rerun on exact current result commit, local Git mapping and fresh remote ref; no remote writes |
| Update | `release_updater.py` | Exact ZIP/file binding, path/alias/link rejection, stage/readback, copied SQLite integrity/schema rehearsal, isolated test pointer/canary/rollback/restart reconciliation |
| R&D | `workflow_runtime.py` | Registered real experiment, preserved negative trial; UNKNOWN/correlated claim projection; immutable goal/criterion brief; bounded no-progress/time/iteration loop |
| Offline replay | `qualify_workflow.py` | Four real Core jobs, one canonical SQLite DB, negative experiment and new draft; no activation or external transfer |

Function inventory is generated from actual Python AST: `pr018-019-functions.json`.
New backend cases: `pr018-019-executable-cases.json`; browser cases in
`one-click-context/tests/campaign-ui.test.mjs`. The 66 original design scenarios are
retained separately, not blanket reported as 66 completed application tests.

Core remains serial (`max_parallel=1`, `money_budget=0`). The planner never starts a
worker process, model, provider action or background daemon. Resource/capacity rules
admit existing jobs; they are not measured host telemetry. Optional `policy.max_queued`
is explicit temporary operator admission capacity; no default 1000 total queue ceiling.
There is no new total repository/file/node ceiling. 20 is UI page size. Existing Native
wire, command output, timeout and selected-context budgets remain bounded and errors
are explicit. Large DAG validation is iterative; full campaign metadata currently loads
in memory, so RAM/SQLite/disk determine capacity. This does not promise unlimited RAM.

## Запуск безопасного offline replay

From a current source checkout and a NEW absolute output directory:

```powershell
python content-lab/qualify_workflow.py --output C:/OCCData/pr018-019-offline-20261004
```

The directory must not already exist. It contains `profile.json`, `policy.json`,
`campaign.json`, exact fixture input/binding, isolated stage-only installation, the
actual store and `REPLAY_RECEIPT.json`. The negative experiment is intentional:
Core execution of a research task may succeed while its experiment outcome is
NEGATIVE_OR_FAILED; that does not qualify the hypothesis or close the criterion.

For a registered real campaign, an operator-owned policy defines `campaigns[alias]`:
absolute manifest path + SHA-256, allowed templates, input files + SHA-256, explicit
capacity and lease seconds. Manifest schema is `occ.campaign.v1`; every node owns id,
template, dependencies, registered input names, resource modes and demand. Use the
replay-generated files as a runnable contract example and adapt only through reviewed
operator configuration. CLI:

```powershell
python content-lab/campaign_runtime.py --profile C:/OCCData/native-profile.json inspect --campaign research
python content-lab/campaign_runtime.py --profile C:/OCCData/native-profile.json advance --campaign research
python content-lab/automation_core.py --store C:/OCCData/store work --policy C:/OCCData/policy.json
python content-lab/campaign_runtime.py --profile C:/OCCData/native-profile.json pause --campaign research
python content-lab/campaign_runtime.py --profile C:/OCCData/native-profile.json resume --campaign research
python content-lab/campaign_runtime.py --store C:/OCCData/store cancel --campaign research
```

Run the existing Core worker once for each admitted job, or use its existing supervisor
as configured. Future admission pause permits already admitted jobs to finish. STOP
persists cancellation, does not become a success receipt and does not resurrect jobs.
The local `--store ... cancel` path works even if the manifest/execution policy is gone;
it is local CLI authority, not a Native request path. Refresh requires the old/new
registered policies and exactly the next manifest revision; active/unknown jobs block
refresh. Native exposes no arbitrary manifest upload or refresh mutation.

Browser: update extension plus Native bridge/backend together, configure existing
`durableCore` per `agent-bridge/README_RU.md`, and add the permitted aliases to the
native profile `campaigns` list. Library → campaign fieldset → inspect/admit/pause/
resume/STOP. The Windows installer copies new siblings as well as current main's
Python-group/JS-parser modules. Buttons use trusted clicks and replies are fenced by
alias/request generation. Desktop stdio stays on its existing read allowlist; campaign
mutations use browser Native or local CLI. The old pinned `renew_windows.ps1` does not
install this branch automatically.

## Schedule contract

`schedule_tick.py` and its existing supervisor accept `occ.durable-schedule.v2`:
schedule_id, revision, enabled, registered template, IANA timezone, HH:MM local_time,
start_date/end_date, gap_policy SKIP/SHIFT_FORWARD, fold_policy FIRST/SECOND/BOTH,
catch_up SKIP/LATEST/BOUNDED and catch_up_limit. Europe/Riga fixtures exercise both
2026 spring gap and autumn fold. Windows CI installs pinned `tzdata==2025.2`.
UTC occurrence identity includes schedule revision/local day/resolved instant.
Skipped gaps and missed/skipped/capacity-wait occurrences stay in the ledger. No
implicit future activity is configured by shipping this code. Daily schedule edits
preserve historical receipts and cancel superseded unstarted work; active work remains
pinned. STOP prevents future admission, not proof that every active process stopped.

## Update and evidence limits

Only STAGE_ONLY, BOUNDED_QUALIFICATION and QUALIFY_EXISTING profiles exist. Activation
requires a matching `QUALIFICATION_TARGET.json` with mode TEST_ONLY and disjoint root.
Production unattended activation is unavailable. The asset is policy-bound by exact
bytes/file hashes and source identifiers, not independently authenticated producer or
reproducible-build evidence. Receipts explicitly mark OPERATOR_BOUND_UNVERIFIED.

SQLite backup/rehearsal works on a copy; schema changes block. The candidate pointer
switch uses an atomic file replacement. A cross-store installation owner marker remains
for reconciliation if its worker is lost. Actual process power-loss after pointer switch
is tested; recovery observes the pointer and files before any subsequent qualification.
Pointer rollback is ROLLBACK_POINTER_RESTORED_UNQUALIFIED, not verified predecessor
usability. Device qualification always remains false in isolated fixture receipts.
Registered canary commands are trusted operator commands (not an OS sandbox); no
untrusted downloaded script gains execution permission from source content. Live
production DB migration/rollback and durable directory flush on target hardware still
require qualification. The pure usability predicate checks exact binding equality;
there is no new production capability grant service.

GitHub metadata transport tests use a controlled requester; local Git tests use real
objects/worktrees and registered commands. Fetched private Git objects require operator
prefetch; token environment is used only for registered authenticated GETs and is not
inherited by command children. Mapping fails when changed proposal paths differ on the
final tree; a legitimate conflict resolution requires renewed proposal evidence.
Cancellation can leave a fenced verification worktree for explicit cleanup; it never
starts unfenced cleanup after lease loss.

## Проверки и оставшаяся стратегия

Local Linux: 405 Content Lab tests (84 new), 121 extension tests (5 new), 47 bridge,
8 qualification-adapter passed. Desktop: 23 discovered, 22 passed, one Tk/display
case skipped because this runner lacks a display/Xvfb. Desktop owned files verified;
Chrome package built and ZIP verified. CI includes actual-head Ubuntu + Windows core,
Xvfb/Windows Desktop tests, bridge, adapter and extension. CI outcome is reported in the
PR; local test evidence does not stand for Windows installation.

Offline four-node replay used actual SQLite/Core commands: collect → negative trial →
stage-only update → next brief. Receipt: `runs/PR018_019_OFFLINE_REPLAY_2026-10-04.json`.
Every outcome remains linked to its immutable input/config/result digest. No installed
or usable production capability is claimed by the replay.

External roadmap packages 11–17 must supply compatible canonical task/intent, tab,
policy/registry, backup/evidence and qualification adapters. Their roadmap presence does
not establish implementation. Open source criteria explicitly include manual assertion
UI/tab receipts, independent closure/producer proofs, fairness/performance telemetry,
full external campaign fault pilot, actual Dell Windows 11 keyboard/screen-reader/voice
qualification, qualified production predecessor/migration/rollback and downstream send.
See `pr018-019-workstream-status.json` for specific owners/gates; no source criterion
was removed or marked closed by this package.
