# Codex implementation brief — Laya Desktop Agent / Repo Intelligence

Target: current `main` of `BobIvans/scaling-chrome-extensions`.

Read the parent Voice AgentOS canonical master first, then this folder. Audit actual HEAD and existing owners before changing code.

## Objective

Turn existing repo capture/groups/context, local Desktop, voice/action compiler and browser action runtime into an operator-facing system with three connected experiences:

1. **Repository Workbench** — add/open GitHub/local repo, whole initial capture, logical TXT packs and focused projections.
2. **AI Targets** — friendly Chrome tab picker → exact binding → observe/send/readback on selected Grok/Grok Build/AI tab.
3. **Mission Loop** — voice/text mission → context → local Laya typed decisions → registered executor → verifier → feedback doc → next step.

## Implementation order

### PR-A — Repository Workbench + logical pack compiler
Implement LD001–LD011 + LD003/LD036 foundations. Reuse current repo scan/groups/store. Initial whole-repo accounting is mandatory. Add focused modes without copying source bytes to a second store.

### PR-B — Tab discovery + selected-target qualification
Implement LD012–LD020 + UI target list. Prefer existing extension/native bridge for friendly tab IDs; keep current CDP runtime as execution owner. Do not make title/URL classification equivalent to identity. Add fault tests for switched account/chat/tab, long virtualized conversation and human takeover.

### PR-C — Laya runtime + typed question catalog
Implement LD021–LD025. Use a pinned local model/runtime and record checkpoint digest. Laya answers are DATA_ONLY. A deterministic policy maps answers to registered workflow IDs. Add low-confidence/contradiction abstention tests.

### PR-D — Durable Mission Loop
Implement LD026–LD032 and timeline/inspector UI. One mission revision is pinned to repo snapshot + target binding. One admitted effect at a time. UNKNOWN blocks blind continuation.

### PR-E — Grok Build transport options
Implement LD033–LD035. Keep WEB_SELECTED_TAB. Add optional registered headless Grok Build CLI and ACP transports using same contracts. Fixed binary/argv/cwd and output parser; no arbitrary shell strings.

### PR-F — Installed app + device qualification
Implement LD037–LD042, Windows install/launcher integration and frozen device corpus. Verify Start Menu launch, repo clone/open, whole scan resume, pack export, tab picker/binding, voice mission, STOP, update/rollback readback.

## Required tests

- initial scan over a large repo with restart/resume;
- exact complete file accounting;
- logical grouping and TXT split determinism;
- stale snapshot and new HEAD invalidation;
- tech-debt/error pack evidence requirements;
- Chrome tab discovery permission scope;
- target identity switch/rebind;
- selector/contract drift;
- user typing/human takeover;
- crash after send + lost ack;
- two writers + lease/fence;
- STOP during prepare/send/read wait;
- Laya low-confidence/abstention;
- response asks to expand permissions;
- AI says DONE but verifier fails;
- Grok Build headless process exits/crashes/returns malformed streaming JSON;
- installed launcher works without repo checkout.

## Non-goals

- No second Core/database/scheduler/scanner.
- No unlimited arbitrary shell or browser execution.
- No automatic permission expansion from Laya or AI text.
- No claim that a device/browser/provider path is qualified until direct tests prove it.
- No raw whole-repo dump as the default AI packet; whole capture produces an index + logical parts.

## Done condition

The user can launch the installed local app, add a repo, capture it completely, press one of the logical pack buttons, select a visible AI tab, speak/type a mission, preview/run the registered plan, observe exact evidence and let the system gather/send/verify follow-up context until acceptance or a safe stop condition.
