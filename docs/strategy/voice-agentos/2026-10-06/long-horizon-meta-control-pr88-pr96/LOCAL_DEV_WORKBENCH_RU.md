# Local Dev Workbench — target contract

Do not fork VS Code first. AgentOS should own execution reliability and let VS Code remain an optional human editor/view.

Required runtime:
- registered workspace identities;
- typed CommandSpec (argv/cwd/env scopes/effect/resources/timeout/postconditions/verifier);
- Windows ConPTY for interactive sessions;
- noninteractive subprocess jobs;
- process tree/PID/start-time/executable binding;
- stdout/stderr streaming and bounded durable logs;
- STOP/cancel/process-tree termination;
- orphan/restart reconciliation;
- exact workspace/repo resource leases;
- Git/files/logs/process panels;
- `code --reuse-window` / exact file-line bridge;
- optional lightweight VS Code extension later.

No page/model output is sent directly to an unrestricted shell.
