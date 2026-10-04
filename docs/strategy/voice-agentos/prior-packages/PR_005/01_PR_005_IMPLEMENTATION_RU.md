# PR-005: формат и доступность содержимого каждого исходника

**Target:** `BobIvans/scaling-chrome-extensions`; source task `LAYA4-004`.
Один час — ориентир для focused slice, не обещание пройти любой новый owner
audit или Windows qualification за этот срок. Этот ZIP задаёт implementation;
новый код ещё предстоит внедрить на actual HEAD.

## Пользовательский результат

После scan видны полный ledger и отдельные ответы: entry учтён; raw Git bytes
сохранены; whole-source text допустим; LFS payload присутствует/не проверен;
байтовая целостность проверена/не проверена. `COMPLETE` означает учёт snapshot
и не превращает errors, protected files или pointer contents в полный текст.

Поиск/AI export не должен брать printable fragment бинарного source как будто
это весь исходник. Python parse failure разрешает точный текстовый fallback;
наличие parser failure само по себе не делает source недоступным.

## Наблюдаемое основание

Byte-preserved исходники здесь относятся к `da6abf4c006e4e7d26fe45ef30fa9d07a356f396`.
Historical local V4 `5574ab768b39605d4631651a1e8f2451483344db` известен по status,
его полный code tree здесь не восстановлен. Actual main/PR-003/004 не читались.
Записи о №3/4 основаны на переданном пользователем тексте, а не live CI.

В archived `scan_page` raw binary chunks сохраняются как INDEXED. Каждый chunk
декодируется отдельно при создании `item_id`: часть non-UTF8 source может стать
text item. `analyze` различает decode/AST failure, но не LFS и NUL-text policy.
Symlink и submodule имеют одну legacy reason. Existing 8 MiB blob limit, whole
tree/index reads и 10-second Native timeout остаются известными ограничениями.
Полный audit: `docs/SOURCE_AUDIT_RU.md`; hash provenance: `provenance/SOURCES.json`.

## Scope и зависимости

№1 — scan controller, №2 — manifest/ranges, №3 — payload ZIP и resume,
№4 — streaming inventory CLI. №5 читает и дополняет тот же repo ledger.
Для локального slice достаточно usable existing snapshot/SQLite owners;
не требовать merge всех четырёх пакетов, если соответствующие функции уже есть.
No groups/resolver changes: они относятся к №6/7. Long-running Native/Core
route и index streaming имеют отдельные followup IDs в `parallel/FOLLOWUPS.json`.

Широкая `LAYA4-004` содержит дальнейшие policy/acquisition qualifications.
Canonical pointer detection без external acquisition — частичная реализация.
Полные 160 task cards сохранены без изменения statuses, including open work.

## Owners и минимальный diff

| Existing owner/path | Candidate change |
| --- | --- |
| `content-lab/repo_context.py` (`scan_page`, `selection`, existing SQLite) | Versioned facts, whole-source text gate, coverage queries, bounded legacy backfill |
| `content-lab/repo_source.py` / proposed `source_eligibility.py` sibling | Pure bytes/metadata classifier; installed module, no scanned-code imports |
| `content-lab/automation_core.py` (`search`, `context_pack`) | Shared current repo-item eligibility SQL predicate; generic imported items unchanged |
| `content-lab/native_adapter.py` | Strict `durable.repo.coverage` SUMMARY/PAGE, trusted repo profile |
| `agent-bridge/durable.mjs` | Add command/fields; preserve actual transport budgets |
| `one-click-context/library/durable-ui.mjs` | Capability negotiation and schema/byte budgets |
| `one-click-context/library/repo-review-ui.mjs`, `library.html` | Coverage view + stale-reply guard; source-level eligibility selection |
| Focused Python/native/UI test suites | Fault/legacy/format fixtures and byte-envelope regression |

First reuse any actual equivalent implementation. `JobHost` already routes
durable commands in the reference; change it only if current routing requires
it. No new DB/runtime scheduler. Source facts live under
`analysis.format_eligibility`, beside existing parser/import/symbol metadata.

## Atomic facts and whole-source text

Classify after immutable blob read and existing protected-data policy, before
creating new `items`/FTS rows. Store format facts and chunks in the same scan
transaction. Existing `state` remains INDEXED/EXCLUDED/ERROR/PENDING; derived
outcome provides more detail. Do not change chunk/revision hashing algorithm.

Whole-source UTF-8 decode must be strict. NUL or C0 controls other than TAB,
LF, CR, FF mean binary heuristic under this policy, even if valid UTF-8.
Class is evidence of this limited encoding policy, not a universal file-type
detector. File suffix alone never proves bytes are text. Empty, BOM/CRLF and
long lines preserve exact raw bytes. UTF16/non-UTF8 is raw-only in this slice;
transcoding would require a distinct derivative identity and later slice.

For raw-only source: keep raw chunks, set new text item creation off for all
its fragments. Existing legacy text items stay historical, but source-backed
packet/export paths must use facts before selecting them. Current repository
search projection must skip ineligible source-backed hits; do not delete raw
items or relabel old review evidence. General non-repository imports keep their
own format policy. LFS pointers use metadata presentation, not source payload
claims. Recognized unsupported forms remain visible with reason.

## LFS and metadata-only modes

Implement minimal strict 3-line v1: exact version URL, lower-case SHA256,
canonical nonnegative decimal size and LF termination; size <1024 bytes.
Extended/legacy variants are explicit unsupported candidates. Malformed
recognized prefix is an explicit malformed candidate. An example embedded in
a README is ordinary text and does not identify that README as a pointer.
No filters, smudge, lazy fetch, LFS downloads or following links in this slice.

`lfs.payload_sha256/size` is declared by the pointer; availability NOT_CHECKED,
verification NOT_RUN. It does not prove the payload exists, is missing, or has
been exported. A later controlled local payload resolver can add VERIFIED/
MISSING/CORRUPT status using separate payload identity/evidence. Preserve
pointer raw bytes and Git OID throughout.

Mode 120000 distinguishes symlink metadata; mode 160000/kind commit distinguishes
submodule metadata. Unsupported raw path retains `git-path-hex:` data. A path
label is never used as an output path; UI uses `textContent`. Existing protected
filename/operator exclusions/text heuristic remain separate reasons. Ordinary
`wallet_logic.py` must survive the regression fixture. Protected name cannot
gain raw hash by silently reading bytes that were excluded at enumeration.

## Legacy/backfill and read-only Native

New reader returns facts UNKNOWN if the supported version is absent; do not
infer UTF8 eligibility from old `parser` or existence of one `item_id`.
Bounded CLI backfill uses ordered existing chunks only, incremental strict
UTF8 decoding across chunk boundaries, whole-source controls and source hash/
range validation. One source is committed atomically; corrupt capture gets an
explicit blocker, not eligible facts. Already valid same-bound facts are reused.
Policy/source changes require a new facts generation; keep old receipts.

Proposed command (implement/adjust to actual CLI owner):
`python -B content-lab/source_eligibility.py --profile <profile> --repository sce --snapshot <snapshot> --backfill`
Output is compact progress/result; no arbitrary app UI path or auto Git read.
Checkpoints in existing facts permit a restarted CLI to skip committed sources.
New schema migration has no new tables: absent JSON key is valid legacy.

SUMMARY executes one SQLite read view with aggregate counts, no full blobs,
roundtrip proof, snapshot diff graph or automatic classification. PAGE uses
keyset `ordinal > afterOrdinal`, binds snapshot/policy/query and returns bounded
rows. Classification PAGE requires complete inventory and supported current
facts for all terminal entries; otherwise FORMAT_FACTS_PENDING/CORRUPT_FACTS.
SUMMARY can disclose pending scan/facts counts. Never claim summary counts
prove raw integrity. `raw_integrity=NOT_RUN` until a bound PR-002/003 proof.

Counts and cursor ordinals in new wire DTO are canonical decimal strings,
parsed against SQLite signed-int domain without lossy JS Number conversion.
Old offset<=1,000,000 does not constrain this new reader. Limit<=20 is per page;
serialized envelope<=32,768 bytes and actual adapter output budget both apply.
If one row cannot fit, return ROW_ENVELOPE_LIMIT, not zero-row EOF success.
Filter changes reset cursor; cursor includes snapshotId/classifierVersion/query.
No mixed-policy pages, guessed continuation or tail truncation.

## Compatibility with №2/3/4

Preserve existing parser metadata and current disposition/reason. PR-002 raw
manifest/range IDs continue to mean exact Git bytes, including pointer bytes.
If adding format fields to export output, use a declared optional extension or
new schema/policy version and bind it into batch identity; keep original checks
valid. `GAPS.jsonl` is a metadata projection of all non-text/uncaptured/externally
unknown rows, ordered by entry ordinal. It does not become a second ledger.
PR-003 exports INDEXED binary raw parts; text-ineligible is not raw-ineligible.
Coordinate exact extension names with actual №2/3 contracts before code merge.

PR-004 inventory row order, NUL-safe path encoding and atomic complete state
remain its responsibility. Backfill/format pages consume published snapshot
only. Source gate changes cannot weaken protected data policy or alter existing
proof scopes. No claim of unlimited bytes: all encountered resource blockers
are recorded with current budget and retry requirement.

## Validation and reporting

`plan/ACCEPTANCE_CASES.json`: 18 scoped scenarios. The golden ledger covers 64
entries, 56 INDEXED, 6 EXCLUDED, 2 ERROR; raw capture is distinct from text and
LFS external payloads. Fixture output is independent expected data for future
tests, not generated app output. Run actual unit/native/UI suites; full receipt
has exact base/head, observed commands and Windows status. Package verifier
checks this deliverable and cannot close implementation acceptance.
