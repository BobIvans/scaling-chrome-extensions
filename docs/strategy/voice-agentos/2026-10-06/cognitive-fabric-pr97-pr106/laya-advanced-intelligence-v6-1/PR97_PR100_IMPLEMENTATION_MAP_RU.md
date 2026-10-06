# PR97–PR100 implementation map — V6.1

This revision adds no new PR numbers.

## PR97 — ProviderGraph / Cognitive Session Bus
- four intelligence tiers;
- provider/session capability metadata;
- CognitiveRequest / CognitiveProposal;
- session/model-call receipts;
- health/quota/capability state.

## PR98 — ChatGPT Plan Auth
- current official Sign in with ChatGPT flow;
- explicit plan permission;
- runtime restrictions/model discovery;
- secure local credential storage;
- no assumption of ChatGPT history/memory access.

## PR99 — Cheap/Fast Cognitive Router
Implement:
`Goal → Evidence → Surface → Resolver → Prefetch → Action → Verify → Recover → Learn`.

Most important:
- classify the next missing evidence/need;
- choose cheapest reliable resolver;
- safe prefetch;
- avoid strong calls for known procedures;
- compile repeatable expensive discoveries into procedures.

## PR100 — Persistent AI Session Relay
- Grok Build headless/ACP lane;
- Grok/ChatGPT browser-session lane;
- context deltas;
- safe local work continues while provider thinks;
- raw answer archival;
- CognitiveProposal → local verified action.
