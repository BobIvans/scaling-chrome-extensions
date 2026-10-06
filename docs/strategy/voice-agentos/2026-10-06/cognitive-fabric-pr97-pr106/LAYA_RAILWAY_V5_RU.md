# Laya Railway V5 — Cognitive Escalation + Next-Action Prediction

The Railway asks:
1. Is the next edge deterministic?
2. Is exact local evidence enough?
3. Can Laya/small local model classify it?
4. Is there a cached qualified procedure?
5. Is a strong model actually needed?
6. Which provider best matches modality/context/latency/quota/cost/privacy?
7. What is the smallest ContextPack it needs?
8. Did its proposal add evidence/actionable semantics?
9. Can the discovered route be compiled into a reusable low-cost capability?

DecisionState includes Goal/acceptance gap, H2/H1/H0, HorizonGraph subgoal, blocking uncertainty, context freshness/debt, SurfaceGraph, deterministic capabilities, procedures, ProviderGraph, active AI sessions, quota/usage, difficulty, modality, risk, latency/money/plan budgets, progress velocity, recent failures and human interruption budget.

P0 Need kind: FACT / SURFACE_STATE / TOOL / PLAN / CODE / VISUAL_UNDERSTANDING / USER_INTENT / AUTHORITY / VERIFICATION.
P1 Cheapest resolver: DETERMINISTIC_RULE / LIBRARY / PROCEDURE / LAYA / LOCAL_MODEL / SUBSCRIPTION_MODEL / GROK_BUILD / API_MODEL / HUMAN.
P2 Provider fit: TaskClass, modality, context fit, historical success, latency, quota, marginal cost, privacy.
P3 Context request: exact evidence subset only.
P4 Proposal critic: bounded question answered? grounded? executable semantic action? GoalContract respected? cheaper route better?
P5 Disposition: COMPILE_ACTION / STORE_EVIDENCE / ASK_FOLLOWUP / ESCALATE / DISCARD / BUILD_CAPABILITY.
P6 Learn cost: recurring model-discovered action should become cached procedure/capability.

Strong model escalation is justified only when expected gain in verified progress/success exceeds latency + monetary/plan cost + quota opportunity cost + privacy/risk.
