# PR97–PR100 insertion map — Laya Parallel Supervisor V8

V8 does not create new PR numbers.

## PR97 ProviderGraph / Cognitive Session Bus
Add:
- LaneRegistry contract for AI_THINKER and provider lanes;
- persistent GrokSupervisor session;
- exact provider/session identity;
- async request/status/result events;
- SupervisorPacket state.

## PR98 Provider auth
Add:
- authorized Grok/ChatGPT/provider session lifecycle;
- health/quota telemetry;
- TaskPacket privacy/outbound-artifact controls.

## PR99 Cheap/Fast cognitive router
Add:
- event-triggered Grok escalation policy;
- EvidenceFanIn listener;
- Laya re-ranking on first useful evidence;
- predicted safe prefetch;
- cancel obsolete lanes;
- reject stale Grok results.

## PR100 Persistent Grok/ChatGPT relay
Add:
- Grok supervisor protocol;
- concurrent local lane execution while provider thinks;
- bounded delta updates;
- TaskPacket/attachment relay;
- response → CognitiveProposal → local critic → ActionCandidates;
- session timeline.

## Hard prerequisites
Do not fake V8 on serial execution. Real behavior also depends on still-planned:
- PR64 durable resource-aware parallel Core execution;
- PR70/71 SurfaceGraph + Shadow Workspace;
- PR89 fresh-context verified rounds;
- PR91 Dev Workbench/process lanes.
