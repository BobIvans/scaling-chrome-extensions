# Laya Mental Frames V6 — Predictive Cognitive Railway

Frames are typed public decision contracts, not hidden chain-of-thought.

## M0 — State Compression Frame
Question:
What is the smallest faithful description of the current verified world state?
Output:
`StateVector` with goal gap, exact surface, active lanes, blockers, freshness and unresolved effects.

## M1 — Next-Need Prediction Frame
Predict the *kind* of thing required before progress:
- FACT
- FRESH_FACT
- SOURCE
- SURFACE
- TOOL
- PROCEDURE
- PLAN
- CODE
- VISUAL_INTERPRETATION
- USER_INTENT
- AUTHORITY
- VERIFICATION
- RECOVERY

This is the central V6 frame.

## M2 — Prerequisite Forecast Frame
Predict the next 1–3 prerequisites if the current intended action succeeds.
Example:
`download Drive file → parse artifact → retrieve relevant paragraphs`.
This enables prefetch in parallel.

## M3 — Context Debt Frame
Score missing/stale/contradictory context.
If debt is low, do not retrieve more.
If debt is high, fetch only the highest-value missing evidence.

## M4 — Cheapest Resolver Frame
Candidates:
- deterministic code;
- cache/procedure;
- Library/graph lookup;
- Laya;
- local classifier/embedding;
- local LLM;
- local VLM/OCR;
- ChatGPT-plan inference;
- Grok session/Build;
- metered API;
- human.

Select cheapest candidate above calibrated success threshold.

## M5 — Opportunity Frame
Ask:
Is there a safe useful parallel observation/research lane that unlocks later progress?
Examples:
- prefetch repo symbols;
- capture Drive docs;
- query RPC health;
- inspect authenticated DEX dashboard read-only;
- prepare a ContextPack while Grok thinks.

## M6 — Surface Semantics Frame
Map exact:
account → workspace → conversation/document/app → control/tool.
Prefer structured tools/API/CDP/DOM/AX/UIA before pixels.

## M7 — Evidence Quality Frame
Classify evidence:
PRIMARY_EXACT
PRIMARY_OBSERVED
SECONDARY_TRUSTED
MODEL_CLAIM
HEURISTIC
UNKNOWN

Consequential decisions cannot rely only on MODEL_CLAIM.

## M8 — Contradiction Frame
When sources disagree:
- freshness issue?
- scope mismatch?
- version mismatch?
- data latency?
- model hallucination?
Route to exact verification before synthesis.

## M9 — Action Outcome Forecast Frame
Given bounded ActionCandidate:
predict expected state delta and verifier.
Reject action if expected delta cannot close/unlock a goal gap.

## M10 — Drift Frame
Compare current Surface/Tool/Procedure identity with last successful execution.
If unchanged → deterministic replay.
If drifted → AI repair lane.

## M11 — Cognitive Escalation Frame
Escalate intelligence only after identifying the unresolved edge.
Send one bounded CognitiveRequest, not the entire mission.

## M12 — Cognitive Return Critic Frame
Check returned proposal:
- answered requested edge?
- cites/points to evidence?
- requests new context?
- proposes executable semantics?
- contradicts policy?
- can be replaced by deterministic route next time?

## M13 — Procedure Compilation Frame
After success:
Can the trajectory be compiled into a semantic recipe?
If yes:
record inputs, surface identities, tool/control anchors, postcondition, verifier, failure/drift signals.

## M14 — Research Experiment Frame
If question is empirical, create ExperimentSpec rather than free-form chat.
Example:
“Which currency pairs show persistent cross-source divergence?”
→ sources, samples, freshness, metrics, stop conditions, reproducible output.

## M15 — Human Interruption Frame
Ask user only if:
- human intent is materially ambiguous;
- missing credential/consent;
- effect authority is missing;
- two human targets cannot be safely disambiguated.

Do not ask because the agent is technically unsure.

## M16 — Meta-Learning Frame
After repeated rounds:
- which frame was unnecessary?
- where did Laya misroute?
- which model call could become a cache/procedure?
- which evidence source predicts success best?
Changes require replay/canary before production.