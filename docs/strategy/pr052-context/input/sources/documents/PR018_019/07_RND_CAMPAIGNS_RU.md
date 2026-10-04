# R&D и кампании

Immutable manifest содержит campaign/goal IDs, source commit/snapshot/hash, completeness/omissions, contract versions, nodes/edges, join policy и budget. Node input — content reference/selection manifest, не принудительная копия всего corpus в prompt. Branch results содержат lineage и baseline digest, несопоставимые trials остаются incomparable.

Source → Claim → Hypothesis → Experiment → Result → Gap → Brief — адресуемые records. Primary-source locator и observed hash имеют freshness/date, unavailable источник отмечается UNKNOWN. Пересказ/summary ссылается на raw source и не создаёт независимое evidence. Negative result не удаляется и помогает выбрать следующий эксперимент.

Candidate ranking сохраняет utility, information_gain, blocker_reduction, cost, uncertainty и configurable weights с версией. Unknown quantity остаётся unknown; никакой выдуманной вероятности прибыльности. Laya/AI может выбрать только candidate IDs из разрешённого списка или abstain. Workflow JSON в examples — предложенный внутренний контракт, не документированная native Laya import schema. Адаптер должен проверить фактический формат Laya перед подключением.

NextBrief содержит gap classification, original goal/task refs, evidence_delta, selected input hashes, rationale, owner, dependencies, acceptance, recovery, proposed change scope, estimated cost, stop conditions и supersedes. Generation key = gap IDs + evidence_delta_digest + goal revision + planner/template version. Те же inputs возвращают существующий draft; новые факты создают revision. Предложение новых aims сохраняет старые IDs и links, не переписывает исходные слова пользователя.

Кампанию можно объявить завершённой по её criterion policy, failed/deferred или budget/no-progress stop. Наличие следующего brief не запускает его отправку или код автоматически. Bound loop фиксирует iteration cap, elapsed deadline, transfer cap, cost ceiling и max no-progress iterations; progress — новые проверенные criteria/evidence, не количество сгенерированных файлов. При UNKNOWN_EFFECT loop остановлен для reconciliation, независимые разрешённые reads могут продолжаться.

Shared context/evidence cache не равен общей записи. Каждый worker отдаёт proposed result по return contract; финальная запись, UI send, schema change и install идут через существующих owners. Завершение worker не означает принятую интеграцию. Полная campaign история, deferred и failures экспортируются с index.json и hashes для нового чата.
