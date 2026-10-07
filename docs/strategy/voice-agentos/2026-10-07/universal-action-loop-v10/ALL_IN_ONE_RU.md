# Universal Action Loop V10 — repo handoff

See the full R&D ZIP in this folder.

## Runtime truth
Current code has browser/UIA observation, bounded generic read-navigation, screenshot capture, Library/Drive ingestion, Laya/FastDecision, durable Goal state, text-only AI-site send/reconcile and Codex relay. It does **not** yet have a generic screenshot→AI→typed action→execute→reobserve→verify loop, multimodal unknown-AI-site automation, WebMCP/CDP owner, Shadow Workspace, generic Artifact Broker/Drive-UI fallback, Dev Workbench/Flashloan Ops, or full device qualification.

## Universal fallback
1. registered/domain capability
2. WebMCP/API
3. CDP/DOM/accessibility
4. qualified site adapter
5. Windows native/UIA
6. screenshot/vision typed action proposal
7. human only when intent/authority/credential/target cannot be safely resolved

## Screen-to-action
Bind screenshot to exact surface/world revision. Give the model screenshot + geometry + optional DOM/AX/UIA candidates + goal gap. Model returns only CLICK/TYPE/SCROLL/etc proposal with semantic target, confidence and expected state delta. Local Core validates target/effect/human lease/resources, executes, recaptures, and verifies. Never blindly retry unknown effects.

## Minimal UI
Observe · Context · Do · STOP. Detailed Goal/Lanes/Surfaces/AI Sessions/Evidence/Actions/Approvals/Artifacts/Processes/Timeline live in Mission Cockpit.

## Intended out-of-box commands
- Find everything we know about X.
- Continue this in Grok/ChatGPT with text/docs/images.
- Figure out how to get X from this unknown site.
- Do X in this accessible Windows app.
- Continue flashloan qualification.
- Implement the missing capability and continue.
- Do it the way I showed you last time.

## Roadmap insertion
PR67: unknown/multimodal AI-site runtime.
PR70/71: SurfaceGraph/Shadow Workspace.
PR74: universal ActionCompiler with vision fallback.
PR77: vision/recovery replay corpus.
PR78: minimal local UI/Mission Cockpit.
PR84: dynamic WebMCP/CDP/tool discovery.
PR97–100: provider selection, TaskPacket, persistent Grok/ChatGPT relay, Laya Execution Brain.
PR104: multimodal broker.

## Research basis
Current computer-use systems demonstrate screenshot-feedback loops with structured click/type actions while the application performs execution and verifies outcomes. Chrome WebMCP exposes structured JSON-schema tools and is intended to improve agent actuation reliability. OmniParser demonstrates screenshot-to-structured GUI grounding. Cua demonstrates exact background Chromium tab control through CDP without moving the physical cursor.
