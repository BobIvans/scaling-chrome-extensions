# Grok Persistent Thinking Lane

## Purpose

Recreate the original idea:
a Grok Build/web session is “wired” to the local AgentOS so it can think over long horizons while AgentOS keeps observing/gathering/executing locally.

## Native lane

Prefer Grok Build CLI/headless/ACP for code/repo reasoning:
- exact workspace;
- `/goal` or headless task;
- streaming status;
- worktrees/subagents/workflows when useful;
- output artifacts;
- no direct stable-install authority.

Current Grok Build exposes TUI, headless and ACP modes; its current product also includes subagents, skills, worktrees, web search, terminal execution and background tasks.

## Web session lane

For Grok web/Build Mode:
- bind exact Grok account/conversation;
- BrowserWatch archives it;
- AgentOS sends a `ThinkingPacket`;
- Grok response/app/result is captured;
- output becomes `CognitiveProposal`;
- AgentOS verifies and chooses the next action.

## ThinkingPacket

- GoalContract excerpt;
- active subgoal;
- verified state summary;
- exact evidence references;
- unresolved question;
- permitted role;
- requested output schema;
- prohibited effects;
- maximum response/context budget.

## Delta continuation

Do not resend all context each turn.
Send:
- new evidence;
- verified actions/results;
- changed assumptions;
- unresolved gap.

The Library stores complete history.

## Parallelism

While Grok thinks:
- local Laya can classify;
- Library can retrieve;
- web3 read-only observers can gather;
- tests/simulations can run;
- another verifier provider may work.

Grok is a deep-thinking lane, not a global lock.