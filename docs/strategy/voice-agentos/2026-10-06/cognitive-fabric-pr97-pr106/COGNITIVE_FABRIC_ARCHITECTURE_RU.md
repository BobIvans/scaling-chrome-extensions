# Cognitive Fabric Architecture

## CognitiveProvider
Fields: provider_id; transport (deterministic/local/service/SIWC/API/CLI/ACP/browser); modalities; tools/search/code support; max context; latency/cost/quota/privacy; reliability by TaskClass; health; auth profile; session capabilities.

## CognitiveRequest
role (ROUTER/RESEARCHER/STRATEGIST/CODE_ENGINEER/CRITIC/VISION/SUMMARIZER); GoalContract excerpt; active subgoal; JIT ContextPack; bounded question; allowed tool IDs; output schema; token/latency budget; prohibited effects; evidence refs.

## CognitiveProposal
May contain conclusions, hypotheses, requested evidence, semantic action proposals, searches, code changes, uncertainty/confidence, verifier suggestions, citations/artifacts. It never directly grants effects.

## Session state
provider/account/workspace/conversation/session; role; last ContextPack; last accepted turn; pending request; result artifact; coverage; stall/failure; quota/usage.

## Idle intelligence
Cheap idle cycles may dedupe/tag, reconcile temporal facts, detect stale summaries, compile procedures, prefetch likely context and update reliability priors. They never auto-promote code/capabilities without replay/canary evidence.
