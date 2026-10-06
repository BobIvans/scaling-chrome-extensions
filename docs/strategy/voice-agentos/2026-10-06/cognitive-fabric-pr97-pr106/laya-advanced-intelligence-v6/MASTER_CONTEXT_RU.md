# Master Context — Laya Advanced Intelligence V6

## New premise

Previous Railway versions mostly answered:
“What is the best next route/action?”

V6 adds a stronger question:
**“What type of missing cognition/evidence/capability is preventing the next verified progress, and what is the cheapest reliable way to obtain it?”**

Laya becomes a predictive controller over:
- context needs;
- evidence gaps;
- future action prerequisites;
- provider/tool needs;
- drift/recovery;
- procedure compilation.

## Universal loop

Observe
→ classify current world state
→ predict next missing need
→ predict likely next 1–3 state transitions
→ acquire the cheapest missing evidence/tool/cognition
→ compile bounded action candidates
→ execute
→ verify
→ update world state
→ decide whether to cache as procedure
→ continue.

## Why this matters

The app should not call a frontier model for:
- hash/dedupe;
- simple labels;
- known clicks;
- known downloads;
- exact repo commands;
- established extraction recipes;
- known web3 tables;
- routine context retrieval.

Expensive reasoning is reserved for:
- unfamiliar site/app;
- contradictory evidence;
- novel strategy;
- coding/design;
- ambiguous intent;
- vision with insufficient structured state;
- repeated failure/drift.

## Two loops, not one

### Fast Loop
Sub-second/seconds:
deterministic code + Laya + small local classifiers.

### Deep Loop
seconds/minutes/hours:
Grok Build / ChatGPT / Codex / other provider sessions.

Fast Loop continues gathering/verifying context while Deep Loop thinks.
When Deep Loop returns, its proposal is merged into the durable mission state.

## Mission authority

External models never own:
- goal;
- effect permissions;
- resources;
- wallet;
- shell;
- install;
- Git merge;
- acceptance closure.

They return proposals/evidence only.