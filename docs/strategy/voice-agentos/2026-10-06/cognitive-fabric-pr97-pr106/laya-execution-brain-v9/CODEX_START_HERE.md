# Codex Start Here — Laya Execution Brain V9

This is a focused addendum to PR97–PR100. Do not create another architecture layer or a new PR number just for V9.

Re-audit current main and implement missing foundational PRs first.

**PR99 should implement most Brain logic:**
- ExecutionBrainState;
- verified/belief state;
- Goal Frontier;
- adaptive memory selector;
- Value Router;
- routing feedback stats;
- route regret;
- predictive prefetch;
- anytime cancellation;
- tool-set minimizer;
- procedure promotion signal.

Tests must compare cheap vs strong route, stale Grok result, wrong memory selection, failed-branch recovery, first-useful-evidence cancellation, provider/tool reliability updates and process-vs-outcome verifier behavior.
