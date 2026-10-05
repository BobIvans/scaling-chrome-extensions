# Laya Desktop Agent / Repo Intelligence — R&D handoff

Date: 2026-10-05  
Target: `BobIvans/scaling-chrome-extensions`

This package turns the existing Context Library / Voice AgentOS pieces into one operator-facing product loop:

`local repo / GitHub repo → complete capture → logical groups → selectable TXT/MD/JSON packs → Laya typed decisions → selected AI tab or Grok Build transport → response/evidence import → next verified action → repeat`.

## Product promise after implementation

The local Windows app must let the operator:

- add/open a local repository or clone a GitHub repository;
- run an initial **whole-repository** capture with complete accounting;
- create logical context packs instead of one raw dump;
- later choose focused views such as interconnected files, tech debt, broken/error paths, high-value files, tests, runtime path, or delta;
- inspect and explicitly select a Chrome/Grok/Grok Build tab;
- bind that exact tab identity and observe it read-only before any send;
- speak/type a mission;
- let Laya classify/rank typed next steps while never granting authority;
- let registered executors perform approved local/browser/Git actions;
- read back results and compile an evidence document for the next AI turn;
- stop, take over manually, or leave ambiguous effects as UNKNOWN.

## Important separation of roles

**Laya is not the hands.** Laya is the fast typed decision/ranking/abstention layer. It emits `choice`, `score`, and `noul` decisions with DATA_ONLY authority.

**The hands are registered executors**: repo capture/compiler, browser/CDP/extension transport, Git/GitHub, Windows UI Automation where needed, file writers, and other explicitly registered capabilities.

**Grok/Grok Build is a planner/generator**, not an authority source. Its response is imported as an AI claim and must be routed through deterministic policy, verifier and receipts before external effects.

## Reuse current owners

Do not create a second Core, database, queue, scheduler, scanner or browser effect engine. Reuse current owners already in the repository, including `repo_context.py`, `repo_groups.py`, `context_packets.py`, `context_handoff.py`, `automation_core.py`, `action_intent.py`, `action_runtime.py`, `browser_cdp.py`, `native_adapter.py`, `desktop/app.py`, `desktop/actions_ui.py` and the current Windows install/launch path.

## Read next

1. `CURRENT_STATUS_RU.md`
2. `UI_SPEC_RU.md`
3. `REPO_CHUNKING_MODES_RU.md`
4. `SELECTED_TAB_GROK_LOOP_RU.md`
5. `DOWNLOAD_REPO_OPEN_UI_RU.md`
6. `LAYA_QUESTIONS_CATALOG.json`
7. `LAYA_DESKTOP_WORKFLOWS.json`
8. `FUNCTION_BACKLOG.json`
9. `CODEX_IMPLEMENTATION_BRIEF.md`
