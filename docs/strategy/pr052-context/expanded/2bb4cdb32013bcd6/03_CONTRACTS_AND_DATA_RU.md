# Контракты и данные

Все schemas в contracts/ — proposed JSON Schema Draft 2020-12. Их versioned mapping к existing DTO обязателен до production writes; они не утверждают наличие этих names в текущем коде. Hash canonical JSON: UTF-8, sorted keys, separators без whitespace, allow_nan=false; amounts integer decimal strings, timestamps UTC RFC3339; object digest считается по raw bytes. Schema version и digest policy version включаются в signed/approved request scope при наличии такого механизма у current owner.

| Контракт | Writer / owner | Главные поля и инвариант |
| --- | --- | --- |
| HandlerManifest | Studious registry; SCE read-only projection | exact repo/build, callable CLI, input/output versions, modes/effects, qualified receipt, timeout/resource scope |
| BridgeRequest | SCE Core | request/run/attempt IDs, handler identity, pinned revisions, mode/profile, datasets, config, criteria, budget, idempotency key |
| Observation | Studious acquisition broker | raw sha, source/upstream lineage, observed/received/available, chain anchor, adapter revision, origin, completeness |
| DatasetManifest | Studious data owner | immutable ordered IDs, acquisition receipt, anchor/freshness policy, gaps/cursor, schema/manifest digest |
| ExperimentSpec | Studious qualification owner | hypothesis/mode, seed/clock/order, cost model, frozen split/criteria/stop, dataset/config/build hashes |
| RunReceipt | Studious domain owner; SCE imports links | process_exit, domain_status, campaign_executed, mode/profile/origin, artifacts, inputs, observed interval, counters, costs/gaps |
| CriterionEvidence | verifier owner | criterion ID/text hash, verified property, exact revisions/scope, artifact hashes, verifier/build, environment, lineage, result |
| Attempt/Benchmark | SCE accounting + registered verifier | every STARTED attempt, accepted/verified outcome, stages, resource/cost/unknown/intervention, variant/split |
| ReleaseScope | existing release/updater owner | mandatory criteria, final compatible revisions, installed build/receipts, scope, blockers, qualification conclusion |

READ_ONLY = provider/source reading; REPLAY = frozen offline temporal evaluation; PAPER = observations + hypothetical fills. PAPER profile may be PAPER or SHADOW. Environment/origin is independent: OFFLINE_FIXTURE and REAL_ACQUISITION cannot substitute each other. LIVE is outside declared bridge profiles in this package. Do not infer mode from file name or exit code.

Run lifecycle: PLANNED → STARTED → RUNNING → COMPLETED/FAILED/BLOCKED/CANCELLED/UNKNOWN. STALE is evidence applicability, not process completion. An interrupted process can be STOPPED with unknown external-effect status. Preserve both. Resume reuses exact request/checkpoint identity; computation may make a new attempt, observed external effect must reconcile first. Do not promise universal exactly-once behavior from idempotency alone.

Criterion states: OPEN, PLANNED, NOT_RUN, BLOCKED, FAIL, PASS, UNKNOWN, STALE, DEFERRED. PASS requires applicable verifier receipt for the exact property/environment/version. Source criterion-level properties may require several receipts. Feature/task/goal PASS requires all mandatory child criteria; DEFERRED stays open for full V5. No parent-wide promotion from one test.

UI separates process exit, domain verdict, acquisition origin, hypothetical economics and observed results. Unknown data shows named missing fields and next permissible step. Dataset disagreement retains both provider observations. Costs included in quote cannot be subtracted again; missing mandatory cost remains unknown, never default zero.

Schema validation confirms shape only. Actual artifact digests, callable command existence, freshness, authorisation/effects, process ownership, economic correctness, Windows install and receipt authenticity need their own verifiers. The package checker only checks this ZIP and source preservation.

Migration: pin current schema; extend tables through the canonical migration coordinator; preserve old receipts and original blobs; map legacy mode/status explicitly; backup rehearsal and interrupted migration cases before activation. The compatibility manifest records SCE revision + Studious revision + DTO/profile versions, not branch names alone.
