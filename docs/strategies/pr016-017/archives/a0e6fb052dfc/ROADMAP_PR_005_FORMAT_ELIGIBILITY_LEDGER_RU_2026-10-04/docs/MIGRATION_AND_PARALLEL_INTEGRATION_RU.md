# Совместимость, backfill и параллельная работа

Storage remains content.sqlite3. Add `analysis.format_eligibility`; keep all
existing JSON keys, table schemas, entry ordinals, raw bytes and revisions.
JSON null/absent facts is a legal old record and projects LEGACY_UNKNOWN.
Old readers ignore the new nested key; new reader cannot infer facts from parser.

One entry update is transactional. For new scan it joins the existing page
transaction; for backfill it commits after contiguous range/hash validation of
one stored source. Store a policy/source binding and terminal fault fact. A
crash before commit leaves that entry unchanged; restart processes it again.
Replayed valid fact with same input binding is reused. No backfill Git read,
working-tree byte substitution, blob fetch or normalization.

Backfill reads chunks in ordinal order with bounded buffers/incremental UTF8.
It must handle a multibyte character split between chunks. Validate raw SHA,
Git blob OID/object format, contiguous ranges, terminal size and chunk revision
using actual digest before asserting source facts. A bad source does not gain
ELIGIBLE status; retain CORRUPT_CAPTURE and failure details without raw content.
The complete facts view is bound to one classifier version and complete pinned
snapshot. If a policy generation is incomplete, SUMMARY reports this and PAGE
fails explicitly; do not present a mixture of generations as verified.

Existing ineligible text items are preserved as historical items. All current
source-backed selection/export/repository search paths filter using facts;
keep general imported content behavior. Old review/task receipts keep the
policy version they used; they are not retroactively requalified. The receipt
must say which current text paths are covered and which legacy standalone
consumer paths remain to update. A central source-backed text eligibility
predicate should be reused where a codebase already exposes one.

Reference `automation_core.search` joins current sync_heads to FTS, while
`context_pack` reads current items by ID. Add a shared SQL eligibility predicate
for repository items before LIMIT/context inclusion, bound to current
repo_heads/repo_chunks/entry facts. Ordinary imported items without repository
binding still pass their existing path. Avoid cyclic imports: keep the query
helper in its existing installed owner or a dependency-free sibling. Do not
post-filter only the first 10 hits and silently discard later eligible matches.
Unsupported/missing fact policy gives an explicit backfill-needed context
blocker; historical receipt/artifact reads keep their captured policy scope.

| Parallel package | Its write ownership | №5 integration rule |
| --- | --- | --- |
| №1 | Scan run/controller UI | Read counts/facts; retain responsive controls |
| №2 | Raw manifest/range projection | Optional versioned format extension; raw identity unchanged |
| №3 | Raw export/staging/ZIP/index | Binary raw stays exportable; pointer not payload |
| №4 | Git inventory publication/order | Facts only after published inventory; no competing inventory |
| №5 | Facts classifier/read-only coverage/text gate | Own analysis key + minimal scoped UI view |

All may touch repo_context.py or repo-review-ui.mjs; logical separation does
not remove file conflicts. Before applying №5 read actual diff/contract for
№2–4 if available, reconcile method names and assign one migration integrator.
Merge order follows implementation dependencies, not chat creation order.
Package construction itself neither starts parallel agents nor confirms work
in another chat. Hand off registry and exact result SHA/PR URL explicitly.

Rollback: revert new handlers/UI and keep additive facts data; old readers must
still function. Retain any modified text projection generation as historical;
do not restore raw exclusion policy or unsafely re-enable filtered text by
deleting data. Rebuild current text heads through the approved older policy if
a rollback of behavior is required, recording that policy in a new receipt.
