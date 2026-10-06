# Laya Railway V2 — Adaptive Typed Question Compiler

Static `laya_questions.json` is not enough for “achieve anything.” Laya must receive the smallest sufficient typed decision set over exact code-generated candidates.

## DecisionStateV2
Contains bounded Goal/H2/H1/H0, acceptance/prohibitions/effect scope, SurfaceGraph, relevant ContextGraph evidence/gaps/freshness, exact ActionCandidates, human leases, active parallel lanes, known capabilities/GapSpecs and recent FailureEdges/trajectory hints.

## Adaptive passes
A Route — always:
- `next_mode Choice`: USE_KNOWN_CAPABILITY / RETRIEVE_CONTEXT / OBSERVE_SURFACE / ACT / ASK_SYSTEM2 / BUILD_CAPABILITY / WAIT / STOP
- `needs_clarification Noul`
- `progress_value Score`
- `risk_level Score`

B Evidence — only if context needed:
- best_source Choice
- evidence_sufficient Noul
- freshness_required Noul

C Surface/target — only for action:
- target_surface Choice
- target_identity_exact Noul
- human_conflict Noul
- best_executor Choice

D Action:
- action_candidate Choice
- expected_postcondition Choice
- action_reversible Noul
- needs_approval Noul (policy remains authority)

E Critic gate — effectful only:
- wrong_target_risk Noul
- better_read_only_route_exists Noul
- semantic_match Noul
- EXECUTE / REOBSERVE / ASK_SYSTEM2 / ASK_HUMAN / STOP

F After step:
- meaningful_progress Noul
- closed_acceptance IDs
- next_parallel_lane_value Score
- obsolete_lanes

## Thresholds
READ ~0.70; routing/context ~0.78; mutable browser/UI ~0.88; send/publish/delete/merge/install >=0.93 plus deterministic identity/effect gate and configured approval. NONE/OTHER/clarify must always exist.

## Evolution
Railway versions are code/data. System-2 may propose question changes after failures, but production questions change only after PR77 replay/canary promotion.

“1-by-1” means one internal decision edge at a time. User states the goal once; Railway iterates until it needs human intent/approval or reaches acceptance.
