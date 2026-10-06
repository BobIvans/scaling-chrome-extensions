# Flashloan Execution Brain Example

Goal: **Find the highest-value next qualification experiment and run it.**

- Verified State: latest accepted campaign state, exact repo SHA, source-health receipts, prior simulation/paper results, open blockers.
- Goal Frontier: choose one open edge such as “is route family X failing because of stale quotes or execution constraints?”
- Evidence Memory: matching failures, route JSON, RPC state, quote history, simulator logs, code symbols.
- Value Router candidates: deterministic log classifier, RPC refresh, DEX dashboard read, replay simulation, Grok diagnosis, Codex code analysis.
- Parallel Anytime: start cheap independent reads first; Grok only when novelty/uncertainty threshold is met; cancel redundant lanes once exact evidence resolves the blocker.
- Verify: exact input version, RPC freshness, process/log receipt, structured simulation result, acceptance thresholds.
- Learn: repeated failure signature → deterministic diagnostic/recovery procedure.

The next campaign should become faster and use less Grok/API.
