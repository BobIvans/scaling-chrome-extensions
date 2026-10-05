# Universal Cognitive Relay V4 — Laya System-1 + LLM System-2 + Executors

## Answer to the product question

Target UX after implementation:

The operator can type in the local app something like:

```
Observe tab: https://grok.com/...
Goal: research how to automate X, implement whatever missing capability is required,
test it, update this app safely, then continue the original mission until acceptance.
Mode: LONG_HORIZON
```

The UI parses this into a typed mission. A URL is only a discovery hint; runtime still resolves and binds the exact current browser tab/account/conversation before reading or writing.

## Cognitive architecture

Laya is **System-1**:
- cheap/fast typed classification;
- rank next frontier;
- decide whether more evidence is needed;
- decide whether an LLM/System-2 call is worthwhile;
- choose which role/provider to call;
- evaluate whether the returned answer is knowledge/plan/code/tool/context request;
- select safe parallel lanes;
- detect no-progress;
- detect capability gaps.

Grok/Codex/other LLM is **System-2**:
- decompose novel goals;
- reason across complex evidence;
- create research hypotheses;
- propose multi-step DAGs;
- design new automation;
- implement code in an isolated worktree;
- explain failures;
- propose alternative routes.

Executors are **hands**:
- browser;
- files;
- repo/Git;
- GitHub;
- local processes;
- Windows/UIA;
- provider transports;
- updater/installer.

Verifier is **reality**:
- browser readback;
- file hash;
- test result;
- CI;
- remote merge SHA;
- build artifact;
- installed readback;
- device/domain criterion.

## Universal Cognitive Relay loop

`USER_TEXT/VOICE → COMMAND PARSER → GoalSpec → DecisionState → Laya → {known recipe | System-2 request | context gather | capability gap | wait | stop} → executor → verifier → evidence delta → Laya → ...`

System-2 is never the loop owner. It is a callable reasoning service inside the durable Core loop.

## System-2 roles

The same provider may be called under different typed roles:

- PLANNER — propose DAG / prerequisites / alternatives.
- RESEARCHER — identify missing primary evidence and queries.
- CODER — produce code/test patch in isolated worktree.
- CRITIC — attack plan assumptions and completion claims.
- DEBUGGER — explain a concrete failure with source/test evidence.
- TOOL_DESIGNER — propose a missing capability contract + implementation.
- CONTEXT_EDITOR — decide what exact context is needed for the next call.
- EXPERIMENT_DESIGNER — design measurable R&D experiments.
- SYNTHESIZER — turn parallel evidence into a compact next-state summary.

Laya decides when and which role to invoke.

## "Observe tab link: ..." command

Natural-language command parser should support:

- `observe tab <url or title hint>`
- `bind active tab`
- `use this tab as source`
- `use this tab as action target`
- `watch this conversation`
- `download useful attachments`
- `send selected context to this tab`
- `ask Grok what to do next`
- `continue until verified`

A link/title only filters candidates. Exact target identity is produced by the browser adapter and persisted as TargetBinding.

## Capability self-growth

When Laya detects MISSING_CAPABILITY:

1. Search existing registered capabilities.
2. Try composition of existing capabilities.
3. Search current repo for dormant/unwired implementation.
4. Search approved GitHub/tool sources if allowed.
5. Ask System-2 TOOL_DESIGNER for a typed capability.
6. Create candidate in isolated worktree/sandbox.
7. Static checks, unit tests, fault tests, heldout tests.
8. If device/browser effect: canary on test target.
9. Create PR.
10. CI.
11. Merge only against exact expected head/policy.
12. Build versioned artifact.
13. Stage/install candidate separately.
14. Health/readback/device qualification.
15. Activate immutable capability/app version.
16. Resume the exact original mission checkpoint.

## Important self-update rule

The running stable controller must never overwrite itself in-place.

`stable controller → build candidate → staged version → canary/qualification → atomic pointer activation → rollback available`

The existing `content-lab/release_updater.py` is the canonical owner to extend.

## Provider-session continuation

For Grok Build, prefer structured transports for autonomous coding:
- visible selected web tab when continuity with the user's existing conversation matters;
- headless session with `--session-id` / `--resume` for durable automation;
- ACP for native application integration.

The mission stores provider session identity separately from the canonical GoalState. Provider sessions may be replaced without losing mission state.

## "Anything" contract

The app can accept arbitrary goals. It can only *execute* actions that resolve to registered effect contracts.

Unknown goal ≠ rejected goal.
Unknown capability → capability growth loop.

This creates open-ended extensibility without granting arbitrary page text/model output unrestricted shell/browser authority.

## Speed objective

Optimize **verified useful progress per unit of time and user attention**, not action count.

Laya should prefer:
- known recipes over expensive planner calls;
- parallel read/research/test work;
- highest information gain;
- bottleneck removal;
- capability with high downstream unlock count;
- headless/ACP provider transport over DOM when equivalent and qualified;
- compact exact context packets over full dumps;
- background work while user owns foreground UI;
- durable waits instead of polling;
- early no-progress detection.
