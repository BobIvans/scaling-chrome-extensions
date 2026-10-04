# Proposed v1 contracts

schemas/ используют JSON Schema draft 2020-12, closed fields, version const, hash syntax и строгие enum. Это DTO проекта; версия underlying canonical Core schema выясняется при checkout. Schema validation проверяет форму, а смысл проверяют actual registry/compiler/admission owners.

Identity chain: InputRevision → IntentSpec(revision) → CompiledPlan(semantic hash) → Core task/operation → ImmutablePacketRef(manifest SHA) → TargetBinding(revision/digest) → SendAttempt → observed receipts → finalized TaskResult → optional PortableSkill. Ни один hash из fixture не имеет права служить current actual receipt.

Ключевые semantic validators, обязательные сверх JSON Schema:

1. Input previous revision существует и new revision монотонна; raw original и corrected refs immutable. Canonical plan одинаков для одного semantic input при pinned versions; modality/provenance не входят в semantic hash.
2. Critical slots должны быть RESOLVED перед admission. MISSING/UNCERTAIN/CONFLICT либо неиспользуемый slot должен быть явно разобран template validator; null amount для нефинансовой capability не равен guessed amount. Negation/mode/units проверяются независимо.
3. DAG unique IDs/acyclic/missing refs/capability versions/known effect validation. Scope refs разрешаются current grant owner, permissions не выводятся из proposals.
4. Target BOUND означает достаточную реально наблюдаемую identity; null fields допускаются формой для unsupported environments, но не разрешают auto-send. Semantic target digest строится из наблюдаемых identity с pinned canonicalizer, не transient tab ID.
5. Packet count/manifest IDs/part ordinal/content/size/hash сверяются с полным immutable manifest. No maxItems общего corpus. Ограниченный размер IPC frame/page не лимитирует общее число частей.
6. SEND_ARMED фиксируется до adapter call. local_send_invocations <=1 — per attempt guarantee, не remote exactly-once. Внешний call не входит в SQLite transaction. Recovered armed attempt остаётся unknown до evidence. Новый attempt допускается после достаточного no-effect evidence, не после expired lease.
7. Вся цепь согласована по task/intent revision/plan/scope/target/packet/attempt. Admission выполняет CAS current revision и cancel/lease/qualification checks; возможный remote commit сохраняет uncertainty.
8. Capture start/end ranges ordered, gaps explicit; один physical capture owner; model unavailable не блокирует keyboard control. Qualification subject/code/environment/dependencies/corpus match current route. Fixture scope не qualifies physical device/UI.
9. Result finalized true и exact task/packet/attempt/conversation; idempotent import/current head CAS. Schema rejects executable extra fields; findings refs могут содержать произвольный текст только как data. DONE не runtime receipt.
10. Part receipt_kind отражает actual evidence grade. UI filename != remote hash; attach != received; received != used. Model-reported use даже для exact IDs не доказывает внутреннее прочтение. Source revision update invalidates read/use coverage по версии.
11. Skill promotion проверяет exact code/dependencies, normal/unseen/fault corpus, independent outcome. Credential refs не raw values; observed steps не расширяют scopes. Drift computes dependency closure; growth grant needs separate scope decision. Negative capsules immutable.

DTO header evolution: reader rejects unknown major versions, records supported minor capabilities, migrations сохраняют old event provenance. Одинаковый naming не означает compatible contract: integration receipt должен связать producer/consumer versions и handlers.
