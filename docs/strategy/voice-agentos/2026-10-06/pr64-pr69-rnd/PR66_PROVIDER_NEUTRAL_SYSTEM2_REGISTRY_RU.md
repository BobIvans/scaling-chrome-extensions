# PR66 — Provider-Neutral System-2 Registry

## Thesis

Mission runtime не должен знать «Codex» как единственный тип System-2. Нужен единый provider contract, в который могут подключаться local Codex relay, headless/ACP, HTTP API, local model и позднее qualified browser-site provider.

## Core rule

Provider возвращает proposals/results/artifacts, но не получает effect authority. Effects всегда проходят Core/H0/resource/effect contracts.

## Proposed owner

`local-agent/system2_registry.py` + plugin modules. Existing `control_bridge.codex_submit/codex_result` становится первым adapter, не удаляется.

## Provider descriptor

- `provider_id`;
- plugin kind/version/code digest;
- capabilities: REASON / RESEARCH / CODE / ARTIFACT / STREAM;
- transport class;
- mutable-session resource identity;
- context/input limits;
- qualification receipt;
- secrets/token env references by name only;
- cost/latency class supplied by local policy;
- allowed roles/modes.

## Uniform request

- request_id;
- goal_id/lane_id;
- role;
- instruction digest;
- context refs / bounded packet;
- requested output contract;
- artifact contract;
- deadline/budget;
- no direct effect scope grant.

## Uniform result

- provider_id/request_id;
- state: QUEUED/RUNNING/WAITING/COMPLETE/FAILED/CANCELLED/UNKNOWN;
- text/result digest;
- evidence refs;
- artifact descriptors with hashes;
- provider receipt/latency;
- finish reason;
- no `criterion_verified=true` unless independent verifier sets it elsewhere.

## Durable fanout and hedging

PR64 worker/lane model should support:
- launch provider A/B/C on disjoint sessions;
- first-useful-result or quorum policy;
- cancel redundant pending calls where transport semantics allow;
- keep COMPLETE results as evidence even if not selected;
- provider crash/restart poll by request id;
- mutable browser composer/session represented as WRITE resource.

## Plugins in PR66

Required:
1. `codex_relay` adapter over existing bridge.
2. one headless/subprocess/ACP-shaped plugin contract with test fixture (real external setup may remain NOT_RUN).
3. generic HTTP/API plugin interface using local policy and token env names; tests use local fake server/fixture, not external spend.
4. local-model plugin interface for process/loopback providers.
5. browser-site plugin type may be registered but effectful send remains qualification-gated until PR67.

## Selection

Laya/FastDecision may rank providers using measured latency/qualification/capability/cost class. Deterministic fallback must exist. A provider must not be selected solely because its page/model text says it is capable.

## Acceptance

- MissionKernel no longer hardcodes Codex semantics for System-2 lifecycle;
- existing Codex path remains compatible;
- two providers can run concurrently after PR64;
- provider result survives app restart;
- wrong request_id/result digest is rejected;
- provider secret values never persist in receipts;
- provider failure does not erase other lanes;
- mutable provider session conflicts are serialized by resource identity;
- disabled/unqualified provider cannot be selected for roles outside grant;
- zero-spend tests remain possible with fixtures/local fake providers.
