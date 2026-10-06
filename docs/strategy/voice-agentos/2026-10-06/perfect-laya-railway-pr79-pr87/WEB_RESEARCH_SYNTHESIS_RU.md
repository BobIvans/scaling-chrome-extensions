# External R&D synthesis

## Structured web tools first
Chrome WebMCP exposes named tools with JSON Schema. AgentOS should discover structured tools and prefer them over pixel actuation. Tool/page output remains untrusted evidence.
Sources: https://developer.chrome.com/docs/ai/webmcp ; https://developer.chrome.com/docs/ai/agents

## Accessibility-tree deltas
Vercel agent-browser exposes compact AX snapshots, interactive refs and structural deltas. Use one full baseline then bounded deltas, revalidating refs before effects.
Source: https://github.com/vercel-labs/agent-browser

## Hybrid Desktop AgentOS
Microsoft UFO²/Desktop AgentOS research reinforces merging native/browser/structured interfaces rather than treating screenshots as the only state.
Source: https://www.microsoft.com/en-us/research/project/agents-for-productivity/publications/

## Procedural memory at two levels
LEGOMem reports orchestrator memory helps decomposition/delegation while agent memory improves execution. Store both mission blueprints and executor procedures.
Source: https://www.microsoft.com/en-us/research/publication/legomem-modular-procedural-memory-for-multi-agent-llm-systems-for-workflow-automation/

## JIT context and harmonic memory
GAM uses a JIT-memory principle. ACON optimizes long-horizon compression. Memora balances abstraction with exact specificity/cue anchors. Keep raw lifetime data local; compile small task packs with provenance.
Sources: https://huggingface.co/papers/2511.18423 ; https://www.microsoft.com/en-us/research/publication/acon-optimizing-context-compression-for-long-horizon-llm-agents/ ; https://www.microsoft.com/en-us/research/publication/memora-a-harmonic-memory-representation-balancing-abstraction-and-specificity/

## Counterfactual action search
Microsoft Computer-Using World Model predicts next UI state for candidate actions and uses simulated action search. AgentOS should implement the contract first with deterministic state-delta previews, later optional learned predictors.
Source: https://www.microsoft.com/en-us/research/publication/computer-using-world-model/

## Demonstrations / trajectories
OpenCUA/AgentNet and UI-Mate reinforce trajectory datasets and in-context demonstrations. Teach mode should compile semantic procedures, not fragile coordinates.
Sources: https://github.com/xlang-ai/OpenCUA ; https://huggingface.co/papers/2608.15930

## Self-evolution must be bounded
Agent0 demonstrates curriculum/executor co-evolution; Echoverse builds evolving environments; AgentRx focuses on trajectory failure diagnosis. Railway/capability changes must pass replay/canary gates before production.
Sources: https://huggingface.co/papers/2511.16043 ; https://www.microsoft.com/en-us/research/blog/echoverse-deep-evolving-environments-for-computer-use-agents/ ; https://www.microsoft.com/en-us/research/group/agentic-innovation/publications/

## Vision fallback
UI-TARS demonstrates strong screenshot-driven GUI control, but our local design should prefer structured interfaces for speed/precision and use vision when structured observation is missing.
Source: https://github.com/bytedance/UI-TARS-desktop
