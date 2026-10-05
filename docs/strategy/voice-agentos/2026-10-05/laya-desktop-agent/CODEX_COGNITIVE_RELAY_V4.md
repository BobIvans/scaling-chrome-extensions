# Codex update — Universal Cognitive Relay V4

## Current target

Implement the user's desired command surface:

`type/voice arbitrary goal → optionally mention tab/link/repo/context → Laya System-1 routes → System-2 provider reasons/codes only when needed → registered executors act → verifier checks → capability self-growth/update if blocked → original mission resumes`.

## Critical distinction

Laya is not a Type-2 LLM. It is the fast typed controller deciding when to call a Type-2 provider, what role/question/context to send, and how to route the structured result.

## Read V4

- `COGNITIVE_RELAY_V4_RU.md`
- `UNIVERSAL_COMMAND.schema.json`
- `LAYA_COGNITIVE_RELAY_QUESTIONS_V4.json`
- `SYSTEM2_PROVIDER_PROTOCOL.json`
- `SELF_IMPROVEMENT_RELEASE_LOOP.json`
- `PARALLEL_RND_LANES.json`
- `UNIVERSAL_COMMAND_EXAMPLES.json`
- `FLASHLOAN_RND_MISSION_TEMPLATE.json`
- `COGNITIVE_RELAY_FUNCTION_BACKLOG.json`

## Runtime implementation order

### V4-A Natural language command surface
CR001–CR004. Add one prominent command box to Workspace/Missions. Support phrases such as `observe tab link: ...`. Parse target hints, but resolve exact identity through the existing browser binding owner.

### V4-B Laya↔System2 Cognitive Relay
CR005–CR012. Pin real Laya runtime. Implement typed System2 roles and provider session manager. Add selected web + Grok Build headless/ACP transports. Persist raw responses and typed parsed outputs.

Use Grok Build automation with fixed binary/argv/cwd; use `--session-id` / `--resume`, machine-readable output, and disable tool auto-update so Voice AgentOS remains the update authority.

### V4-C Parallel R&D
CR013–CR015, CR027–CR030. Build scheduler that launches independent research/repo/test/provider/simulation lanes and incrementally updates the mission frontier.

### V4-D Capability growth
CR016–CR021. First search/compose/wire existing code, then import or generate a tool. Qualification is mandatory before registration.

### V4-E Self-update
CR022–CR025. Extend canonical `release_updater.py`. Stable controller owns candidate promotion. PR/CI/merge/build/install/device receipts are separate. Merge is tied to exact expected head. Candidate never overwrites itself in-place.

### V4-F Flashloan R&D campaign
CR028–CR029. Implement domain template only as research/paper/simulation by default. Produce exact context/code/evidence packets for Grok/Codex and feed results back into repo missions.

### V4-G Device qualification
CR031–CR032. Frozen scenario:
1. user types `observe tab link: ... and build automation X`;
2. app binds exact Grok tab;
3. Laya decides System2 TOOL_DESIGNER is needed;
4. Grok proposes a capability;
5. candidate built/tested in isolation;
6. PR/CI/merge under configured scope;
7. versioned update staged/canary/readback;
8. app resumes the same mission;
9. new provider conversation/session may be used;
10. acceptance verified.

## Required controls

- No arbitrary shell from page/model text.
- No target selection by URL alone.
- No candidate code controls its own promotion.
- No merge without exact current PR/head/policy evidence.
- No installed-update claim from repo merge alone.
- UNKNOWN effect freezes retry.
- STOP remains outside Laya/System2.
