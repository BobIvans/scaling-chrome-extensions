# Operation → owner → transaction → DTO

| Операция | Existing owner | State / граница | Output |
| --- | --- | --- | --- |
| durable.info (proposed) | native_adapter.operator_profile + installed descriptor | File reads only, before Core/DB init | protocol/capability/profile/store identity |
| durable.repo.list | native_adapter.dispatch | Trusted repositories mapping | configured aliases/namespaces |
| durable.search | automation_core.search | existing FTS + sync_heads read | top matches, bounded result |
| durable.context | automation_core.context_pack | current sync_heads/items read | exact selected items/digest, bounded packet |
| durable.repo.coverage (optional №5) | actual repo facts owner | bounded read view, no backfill/proof | facts summary/page, schema qualified |
| durable.repo.manifest (optional №2) | actual raw manifest owner | existing captured snapshot read | metadata pages; no whole-payload Native frame |
| Save TASK_DRAFT.txt | desktop file projection | Staged output chosen by operator | draft + metadata/file hash; canonical task ID null |
| durable.record / review/task mutations | existing content/review/task owners | Existing CAS/journal | OUTSIDE this read-only slice |
| scan/export job or qualification | existing Core | Job/lease/cancel/reconciliation | OUTSIDE this foreground desktop IPC slice |

Browser and desktop use one command implementation and same configured data
root; wrappers may have different transport metadata, domain result same.
No competing SQLite, direct UI SQL, executor, sync-head cache or corpus copy.
Transient widget selection/request fence is UI state. Config stores connection
paths/version choice; draft files are outputs, not authoritative task state.

Reference source uses native_adapter dispatch to instantiate Core even for some
reads. New info must return before this initialization. Data reads in the pilot
require a ready installed store; startup does not create another empty corpus.
Do not introduce DB migrations. Validate browser/desktop same-head fixture.

ACTION5-01 owner matrix is provisional until pinned to actual implementation SHA.
V4 task owner code may have advanced beyond archived reference; preserve it and
mark unsupported desktop operation as GAP. Nonexistent adapter names are not
advertised because roadmap/catalog lists them.
