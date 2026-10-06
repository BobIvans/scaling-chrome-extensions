# Authenticated Web3 Research Observer V6

## Goal

Research data visible in user-authorized web3 apps when public APIs are absent, incomplete or lagging.

## Strict boundary

Read-only qualification/research profile.
Do not:
- extract private keys or seed phrases;
- bypass wallet/session authorization;
- auto-sign wallet prompts;
- submit transactions;
- infer live-trading authority.

## Observation hierarchy

1. documented API/RPC;
2. WebMCP/MCP/structured page tool;
3. CDP network responses/XHR/WebSocket observations when permitted;
4. semantic DOM/accessibility;
5. page-export/download;
6. screenshot/local vision fallback.

## Typed Web3Observation

- app_origin;
- account/session fingerprint (non-secret);
- wallet public address only when already displayed and policy allows;
- chain;
- protocol;
- page/market/pool/pair;
- timestamp;
- source event timestamp if available;
- field schema;
- values;
- units;
- raw payload hash;
- URL/document;
- observation route;
- coverage;
- warnings.

## UI Research Adapter lifecycle

Unknown web3 app:
observe → Laya predicts fields/tool candidates → strong AI only if needed → generate read-only extractor → fixture from captured page/network data → replay → canary → register.

Future visits:
registered extractor runs without LLM unless drift is detected.

## Research examples

- pool liquidity changes;
- displayed APY/fee bands;
- pair/market tables;
- quote/price divergence;
- new protocols/routes;
- route availability;
- dashboard alerts;
- liquidation/borrow state displays;
- docs/changelog collection.

Every observation becomes evidence, not execution truth.
Final flashloan feasibility is checked with RPC/simulation/paper layers.