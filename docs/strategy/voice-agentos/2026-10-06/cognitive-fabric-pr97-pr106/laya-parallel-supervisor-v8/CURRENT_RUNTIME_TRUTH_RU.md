# Current runtime truth

Baseline at authoring: `a492ed023a2297fe9ee0e88fe3337dfa5820f637`. Codex must re-audit current main before implementation.

## Already in code
- canonical local Library with captured files, search, labels/annotations, provenance/revisions;
- streamed virtualized-browser-chat archive with coverage/gaps/order;
- BrowserWatch enumerates allowed tabs and ingests changed captures;
- watched folders, prior AI export ingestion, Google Drive API/export ingestion;
- explicit tab-id operations, generic browser UI inventory and bounded READ_NAV;
- Windows UIA fallback and human foreground lease;
- Laya client/supervisor;
- FastDecision parallel read prefetch across Library/browser/Windows;
- FastDecision can describe safe parallel lanes;
- durable Goal/H2/H1/H0 and restart resume;
- text-only qualified AI-site bind/prepare/send-once/reconcile primitive;
- Codex relay and isolated capability patch/tests/PR/CI primitives.

## Important missing pieces
1. BrowserWatch processes multiple watched tabs sequentially; it is not a durable multi-tab lane scheduler.
2. FastDecision parallel planning is not true durable parallel Core execution.
3. PersistentMission still admits one main H0 at a time.
4. No canonical LaneRegistry binds one Goal to many tab/app/provider/process lanes.
5. No durable semantic resource lease such as `grok/account/conversation/composer`.
6. No persistent Grok supervisor checkpoint/heartbeat/delta protocol.
7. No event-triggered escalation policy from Laya to Grok.
8. No evidence fan-in that immediately re-ranks and cancels obsolete lanes.
9. No multimodal TaskPacket/attachment relay in the current text-only site adapter.
10. No provider-neutral persistent Grok/ChatGPT CognitiveSession runtime.
11. No WebMCP/CDP capability discovery owner.
12. No Drive UI fallback/generic Artifact Broker.
13. No read-only web3 dashboard adapter lifecycle end-to-end.
14. No AgentOS Dev Workbench/ConPTY for Studious Pancake.
15. No real Windows long-horizon qualification proving background coexistence.

Therefore “Grok thinks while Laya controls parallel tabs until the goal is verified” is still a target, not current behavior.
