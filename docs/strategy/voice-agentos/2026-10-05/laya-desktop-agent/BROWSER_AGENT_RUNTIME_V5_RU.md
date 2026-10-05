# Browser Agent Runtime V5 — literal Chrome UI + AI-site-agnostic execution

## What is now added as executable shell

V5 adds a real Chrome Side Panel under `one-click-context/agentos/`. The panel is not a mock:

- enumerates current-window HTTP(S) tabs after explicit optional `tabs` permission;
- lets the user choose the active or any listed tab;
- requests host permission for the selected origin only when Observe is pressed;
- reuses existing `artifact-inventory.js`, `capture-regions.js`, and `content.js` to capture the selected page/chat;
- connects to the existing `com.one_click_context.codex` native host;
- feature-negotiates future `agentos.*` native commands;
- can issue existing durable STOP when available;
- can submit the captured context plus typed mission to the existing local Codex host as a bounded System-2 fallback;
- exposes explicit effect-class checkboxes instead of inferring write/merge/install authority from natural language.

The side panel is declared through Chrome's MV3 `side_panel` manifest key. Chrome 114+ supports Side Panel; Chrome 116+ can open it in response to a user gesture. This project already targets Chrome 116+.

## Why the literal Chrome UI matters

The operator can keep any AI website visible in the main tab and keep Voice AgentOS beside it:

`AI site page | Voice AgentOS side panel`

The side panel is provider-neutral. A tab URL/title is only a candidate/display hint. Exact action binding must still come from a qualified site adapter/runtime observation.

Grok, ChatGPT, Claude, Gemini, Perplexity, custom internal AI sites, or a future provider can all be treated as source tabs. Writing/sending requires a qualified adapter contract for the exact site/session.

## Generic AI Site Adapter contract

Each site adapter must provide independently versioned operations:

1. `discover_identity` — origin/account/workspace/conversation/branch/session fingerprint.
2. `observe_turns` — incremental message/stream/branch capture with coverage.
3. `inventory_artifacts` — links/files/code/download candidates.
4. `observe_composer`.
5. `prepare_draft`.
6. `verify_draft`.
7. `send_once`.
8. `reconcile_send`.
9. `read_response`.
10. `detect_human_takeover`.

A generic semantic adapter can provide OBSERVE candidates. It must abstain from effectful actions when identity/effect semantics are ambiguous.

## Native V5 commands to implement

The side panel already feature-detects these. Codex should extend the existing native host rather than inventing a second host:

- `agentos.info`
- `agentos.target.bind`
- `agentos.target.observe`
- `agentos.mission.preview`
- `agentos.mission.run`
- `agentos.mission.inspect`
- `agentos.mission.pause`
- `agentos.mission.resume`
- `agentos.stop`
- `agentos.library.capture`
- `agentos.provider.send`
- `agentos.provider.read`
- `agentos.capability.resolve`
- `agentos.update.inspect`

The host `hello` response should advertise them as `agentosCommands`.

## Generic provider strategy

Provider routes are plugins, not hard-coded product branches:

- WEB_TAB_GENERIC / site-specific qualified web adapter
- HEADLESS_CLI
- ACP
- API
- LOCAL_MODEL
- MANUAL_HANDOFF

The same System2 request/result envelope applies to all.

## AI says "merged"

This text is a MODEL_CLAIM only. Required path:

1. extract claim (repo/PR/branch/head if present);
2. GitHub executor/observer finds actual PR;
3. verify repo/base/head/current merge state;
4. if merged, obtain remote merge/change identity;
5. fetch/clone/update an isolated local checkout;
6. compare expected source commit/tree;
7. build artifact;
8. tests/qualification;
9. stage candidate with canonical `release_updater.py`;
10. canary + installed readback;
11. activate only through stable controller;
12. reopen/resume the exact previous GoalState;
13. rebind browser/provider sessions as needed.

Downloading a ZIP from GitHub UI is allowed as a separate qualified transport, but Git clone/fetch through a registered Git adapter is normally more deterministic. The UI workflow should offer both when appropriate.

## End state

After Codex completes V5, the user can work literally beside any supported AI website, select it from the side panel, observe it, bind it for effects when qualified, write a free-form mission, monitor H2/H1/H0/Laya/System2/executor/verifier states, and allow safe capability/update loops without leaving Chrome.
