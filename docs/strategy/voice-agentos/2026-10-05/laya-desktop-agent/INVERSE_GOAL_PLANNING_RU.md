# Inverse / Opposite Scenario Planning for Laya

## Why

A forward-only planner asks "what should I do next?" A stronger automation agent also asks:

- What opposite outcome would mean failure?
- What assumption, if false, destroys the plan?
- What is the cheapest observation that can falsify the current route?
- What action unlocks the largest number of downstream steps?
- What reversible action preserves the most options?
- What can run in parallel without stealing a mutable resource?
- What would a human do only because switching tools is annoying, and can the agent remove that switching cost?

The system therefore keeps two linked structures:
- **Goal graph** — postconditions we want.
- **Anti-goal graph** — states we must avoid or disprove.

Laya scores/ranks typed candidates; deterministic policy still controls effects.

## Mental frames

1. **Forward chaining** — next known step from current state.
2. **Backward chaining** — start from acceptance and find missing prerequisites.
3. **Pre-mortem** — assume the mission failed; rank likely failure causes.
4. **Counterexample first** — try to disprove completion/assumptions cheaply.
5. **Bottleneck first** — remove the constraint blocking the most downstream work.
6. **Information gain first** — choose the read/test that reduces uncertainty most.
7. **Fastest verified path** — minimize verified time-to-goal, not click count.
8. **Human attention minimization** — prefer work that avoids asking the operator for trivial context switching.
9. **Reversible first** — when value is similar, prefer easy rollback.
10. **Parallel exploration** — run independent read/test/research branches before committing.
11. **Exploit known recipe** — prefer qualified recipe over generative planning when equivalent.
12. **Capability growth** — if one missing tool blocks many goals, build/qualify it once.
13. **Freshness first** — invalidate stale evidence before spending on downstream work.
14. **Weakest evidence first** — verify the claim that would invalidate the most conclusions.
15. **Alternative route** — when a transport/provider is blocked, choose another qualified route.
16. **Wait is an action** — when quota/event/time is the bottleneck, checkpoint and wait rather than busy-loop.
17. **Stop is progress** — stop unsafe/no-progress loops early and preserve evidence.
18. **Option-value planning** — preserve useful future branches instead of overcommitting to one speculative plan.

## Candidate utility

Laya should produce component decisions, not a single opaque authority score:

- expected_goal_progress
- information_gain
- success_probability
- latency_class
- human_attention_cost
- compute/network_cost
- effect_risk
- reversibility
- downstream_unlock_count
- freshness_risk
- parallelizability
- confidence
- needs_more_context

A deterministic frontier policy combines these according to the mission profile.

Example default heuristic:

`utility = progress * success * (1 + info_gain + unlock_bonus) - latency - human_cost - resource_cost - risk_penalty - stale_penalty`

Irreversible or externally consequential actions still require their explicit effect gate regardless of utility.

## Opposite scenarios

Every major state dimension has a preferred and adverse pole:
clear↔ambiguous goal, sufficient↔missing evidence, stable↔drifted target, qualified↔missing capability, verified↔claimed result, progress↔stagnation, fresh↔stale sources, independent↔conflicting resources, available↔quota-blocked provider, reversible↔irreversible action, known↔UNKNOWN effect.

The JSON lattice in this folder turns those poles into reusable decision questions and recovery routes.
