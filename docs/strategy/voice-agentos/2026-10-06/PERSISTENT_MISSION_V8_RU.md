# Persistent Mission Runtime V8

This layer turns the merged App-centric AgentOS V7 capabilities into a durable decision loop.

## Implemented in this PR

- Core goal runtime persists runtime checkpoints and can list goals.
- Goal state accumulates closed acceptance clauses.
- Desktop/native adapter exposes goal CHECKPOINT/LIST and read-only scoped action-job inspection.
- Local Core client exposes checkpoint/list/job_get.
- PersistentMissionController:
  - creates/reopens one canonical goal;
  - derives H2 milestones from acceptance clauses;
  - builds H1 frontier from current evidence/no-progress state;
  - uses deterministic utility with optional Laya frontier choice;
  - admits exactly one H0 through canonical goal_runtime;
  - executes only existing owners: Library search, browser context gather, MissionKernel;
  - persists pending System-2 and Core job IDs;
  - resumes pending work after local-app restart;
  - writes ProgressDelta and rebuilds frontier;
  - preserves explicit effect scopes.
- Automate+ now runs through the persistent controller instead of only an in-memory bounded loop.

## Still not complete

This does not claim total automate-anything completion. Remaining high-value gates after this PR:
- device-qualified Laya install/benchmark;
- full generic effectful AI-site adapter qualification;
- provider-neutral System-2 registry beyond existing routes;
- production self-activation and post-update reconnect/resume;
- richer Library relations/backlinks/collections UI;
- Studious Pancake paper/simulation campaign runtime;
- full Windows installed fault/device campaign.

The browser archive/UIA/browser UI/capability candidate/PR-CI-merge foundations already merged in PR #61 remain canonical owners.
