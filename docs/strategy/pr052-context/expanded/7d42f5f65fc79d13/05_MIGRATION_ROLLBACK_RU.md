# Core integration, migration и rollback

Перед schema change координатор сверяет существующие tables/owners и версии PR-014/015. Предлагаемые логические records: input revisions, intents/plans, target bindings, adapter qualification receipts, outbox/delivery attempts, part coverage, response imports, skill versions/dependencies, failure capsules. Их можно реализовать в текущих tables/events, если contracts сохраняются; названия не требуют второго store.

Additive migration в canonical SQLite: новые nullable поля, новые typed event payload versions, индексы unique(task+intent_revision+target_revision+packet+part+purpose) и unique(attempt_id). Idempotent result import key = provider/conversation/response identity + result revision/hash. Если identity недостаточна, импорт сохраняется unresolved до связанного task/packet evidence. Unique key для send intent не подменяет remote exactly-once.

Intent correction и revocation старых unexecuted jobs в одной transaction. Admission перечитывает revision/cancel/scope/qualification и fencing token. SEND_ARMED persisted до вызова adapter; recovered armed job не становится READY от restart/lease expiry. Unknown effects, old intents и old response heads никогда не стирать migration.

Backfill historical manual receipts с исходным evidence kind: OPERATOR_REPORTED/MANUAL, не превращать их в UI_OBSERVED/REMOTE_HASH_VERIFIED. Historical task/result IDs сохраняются; unresolved binding остаётся unbound. Schema upgrade не выдаёт grants и не квалифицирует adapters автоматически. Backup/restore canonical owner PR-014; test migration на копии с interrupted transaction/low disk/schema mismatch.

Feature gates proposed: text_intent, voice_capture, target_bind_draft, browser_delivery, demonstration_skills. Text path остаётся доступен при отключённом voice/UI route. Runtime activation требует actual prerequisites + compatible unexpired qualification receipts; fixture/mock readiness не включает реальные effects. Для Laya unavailable direct UI остаётся функциональным.

Rollback: сначала freeze effect admission, STOP new dispatch, snapshot unknown attempts и revoke writers. Disable affected flag/adapter, release resources, preserve durable rows. Не откатывать DB файлом, стирающим возможные внешние эффекты. Старый build запускается только при read/write schema compatibility; иначе retain schema и использовать совместимый recovery tool/build. Unknown attempts сверять до нового send; предыдущий receipt не маркировать failed ради retry. Repair skill выпускает новую version и сохраняет failure capsules.

Rollout: pure text/compiler → Windows capture/keyboard → bind/read/draft → selected harmless send canary/reconcile → multipart → skills. Один PR может содержать эти внутренние commits; runtime enablement различается по квалифицированным capabilities. Code/CI green даёт code readiness, а selected Dell/UI measurements — device/route readiness. Полный GOAL5-16 release/install chain — PR-018, общий closure — PR-021.
