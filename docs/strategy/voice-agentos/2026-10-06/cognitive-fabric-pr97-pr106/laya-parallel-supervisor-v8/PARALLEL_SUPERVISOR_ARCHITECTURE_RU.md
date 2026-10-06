# Parallel Supervisor Architecture

## Roles

### Laya Fast Supervisor
Frequent and cheap:
- choose active acceptance gap;
- select safe lanes;
- rank new evidence;
- start predicted prefetch;
- cancel obsolete lanes;
- decide whether strong reasoning is justified;
- choose among code-generated ActionCandidates.

### Grok Deep Supervisor
Rare and event-triggered:
- challenge strategy;
- interpret unfamiliar protocols/apps;
- synthesize genuinely novel evidence;
- diagnose repeated failures;
- design non-trivial code/capability repairs;
- review a milestone or strategy pivot.

Grok never owns effect authority and never proves completion by itself.

### Lane workers
Typical kinds:
`TAB_OBSERVER, TAB_RESEARCHER, TAB_EXECUTOR, LIBRARY_RETRIEVER, DRIVE_HARVESTER, WEB_RESEARCHER, RPC_DATA, DEX_DATA, PROCESS, CODE_WORKER, AI_THINKER, AUDITOR`.

Each lane has exact resource scope, effect class, expected output and verifier.

### Local Auditor
Ground-truth authority:
- browser/app state;
- files/downloads;
- Git diff;
- tests;
- process/log state;
- RPC responses;
- simulation/paper receipts.

Only Auditor-accepted progress becomes trusted Goal progress.

## Event-driven evidence fan-in
Lane events such as `NEW_ARTIFACT, TAB_DELTA, RPC_SNAPSHOT, TEST_RESULT, SIMULATION_RESULT, AI_PROPOSAL, CONTRADICTION, SURFACE_DRIFT, NO_PROGRESS, UNKNOWN_EFFECT` enter one EvidenceFanIn.

Meaningful events cause immediate Laya re-ranking. Do not wait for all lanes.

## Grok escalation
Escalate on:
- hard goal with no qualified blueprint and high strategy uncertainty;
- unknown protocol/surface after structured observation;
- repeated verified no-progress;
- high-quality evidence contradiction;
- non-trivial code/capability gap;
- falsified strategy before pivot;
- high-value milestone/final strategic review.

Do not escalate for known procedure replay, simple Library/RPC/API reads, hashing, labels, known downloads, registered commands or known web3 extractors.

## Parallel tabs
Lease semantic mutable resources, not only tab IDs. Two duplicate tabs showing the same AI conversation still share one writer lease.

Safe read/research tabs may proceed while the user works in foreground. Foreground human ownership wins.

## Success rule
`Grok recommendation → local critic → code-generated candidates → Laya choice → Core admission → real-world verifier`.
Never `Grok prose → direct click/shell/wallet/Git effect`.
