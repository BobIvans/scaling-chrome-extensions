# PR97–PR100 insertion map

This pack should be implemented *inside* the existing Cognitive Fabric sequence, not as new numbered PRs.

## PR97 ProviderGraph / Cognitive Session Bus

Add:
- CognitiveSession state for persistent Grok/ChatGPT/browser/CLI sessions;
- task/modality/cost/reliability metadata;
- ThinkingPacket/CognitiveProposal schemas;
- model-call/session receipts;
- next-need kind metadata.

## PR98 ChatGPT Plan Auth

Add:
- explicit ChatGPT plan usage route;
- runtime model discovery;
- provider privacy/quota state;
- local Library ContextPack input;
- no assumption that ChatGPT memory/conversations are available.

## PR99 Cost/Quality Router

Add Laya V6:
- Next-Need Predictor;
- Cheapest Resolver;
- Context Debt;
- Prerequisite Forecast;
- Opportunity/Prefetch frame;
- provider success/cost memory;
- compile-repeatable-action detection.

## PR100 Persistent Grok/ChatGPT Relay

Add:
- Grok Build CLI/headless/ACP lane;
- Grok web session lane;
- ChatGPT browser/session lane where appropriate;
- delta continuation;
- BrowserWatch capture;
- response → CognitiveProposal;
- local mission keeps running while external AI thinks.

## Later PRs

PR101:
Project Capsule / Notion Context OS additions.

PR102:
authenticated Web3 Research Observer + UI adapter lifecycle.

PR103:
dual-repo improvement loop consumes reusable procedure/capability discoveries.

PR104:
local/remote multimodal fallback ladder.

PR105:
Experiment Factory uses the Laya V6 Research Experiment frame.

PR106:
qualification measures remote-call reduction and procedure reuse rate.