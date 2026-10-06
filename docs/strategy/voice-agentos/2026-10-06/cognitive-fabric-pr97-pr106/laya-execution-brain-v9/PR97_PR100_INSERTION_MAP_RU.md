# PR97–PR100 insertion map — Execution Brain V9

No new PR numbers.

## PR97
Add TaskClass-level provider/tool success priors, latency/quota/health, `world_revision` on CognitiveSession requests/results, and route-feedback receipts.

## PR98
Add provider usage/quota telemetry, modality/tool capability discovery and cost/plan-opportunity metadata.

## PR99 — primary Brain implementation
Add ExecutionBrainState, belief/unknown state, Goal Frontier, adaptive memory selector, contextual Value Router, empirical routing stats, route regret, predictive prefetch, anytime cancellation, tool-set minimization and procedure-promotion signal. Existing utility scoring may seed priors; verified outcomes update them.

## PR100
Add `world_revision` to every supervisor/task packet, stale-result rejection, event-triggered Grok review, provider-result usefulness feedback and strong-call→procedure learning receipt.

Real benefits also require durable parallel Core, Surface/Shadow Workspace, Artifact Broker, fresh-context rounds, local Auditor and Dev Workbench/Qualification Ops.
