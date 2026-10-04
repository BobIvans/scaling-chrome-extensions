# PR005: source format and text eligibility

PR005 adds versioned facts to the existing `repo_entries.analysis.format_eligibility` key. The SQLite ledger, scan lifecycle, streamed inventory, raw byte partitions and archive owners from PR001–004 remain in use. No total file, part, page or source-byte cap is introduced.

A new scan classifies the entire immutable source before creating text items. Strict UTF-8 and the C0 policy (all bytes below 32 except TAB, LF, CR and FF) determine text eligibility. Empty files, BOM, CRLF and long lines retain exact bytes. A Python parse failure can still supply exact text. Non-UTF8 and control-bearing sources retain every raw chunk and create no text items, including their printable fragments. This is an encoding/control-byte policy, not a universal file-type detector.

The classifier recognizes canonical, LF-terminated, three-line Git LFS v1 pointers shorter than 1024 bytes. The payload SHA/size is a declaration from the pointer; availability remains `NOT_CHECKED` and verification remains `NOT_RUN`. Malformed, extension and legacy candidates have separate reasons. A pointer example embedded in a document remains document text. No LFS download, smudge/filter invocation, link traversal or submodule recursion runs.

Excluded names, operator exclusions, protected-text heuristics, symlinks, gitlinks, reversible unsupported path labels and unavailable bytes remain ledger entries. Raw capture, text eligibility, inventory completion, byte proof and AI delivery/read status have separate fields.

## Existing snapshots and backfill

Absent or unsupported facts project `LEGACY_UNKNOWN` / `UNKNOWN`. Existing parser labels and text items do not establish source eligibility. Use the installed foreground CLI explicitly:

```bash
python -B content-lab/source_eligibility.py --profile /absolute/native-profile.json --repository sce --snapshot SNAPSHOT_ID --backfill
```

One invocation defaults to 100 changed sources and 67,108,864 captured bytes. These are adjustable batch budgets, not repository limits. Repeat until the summary is `READY`; committed same-bound sources are skipped. If one source exceeds the byte budget, raise `--max-bytes` explicitly. `--max-entries` controls the invocation's source count.

Only stored chunks are read. Each source's chunk sizes, ordinals, half-open ranges, revisions, final SHA-256 and original SHA1/SHA256 Git blob OID are checked before its facts commit. UTF-8 decoding spans chunk boundaries. An interruption rolls back the current source; earlier commits remain restart checkpoints. Corruption produces a bound `CORRUPT_CAPTURE` blocker and prevents ready pages. Raw bytes, revisions, historical text items and previous review evidence are retained.

Current `automation_core.search` filters repository hits with the shared predicate before its result limit. `context_pack` gives explicit source/backfill blockers. Selected files and their static dependencies use the same source facts. Review creation, report generation and handoff inherit the context gate. New repository review sessions record the classifier version. Existing historical receipt/artifact reads preserve their previous policy scope.

## Read-only coverage

`durable.repo.coverage` supports `SUMMARY` and `PAGE` (`ALL` or `GAPS`). It opens an existing database with SQLite `mode=ro` and `query_only`, in one read transaction. It does not initialize Core/schema, invoke Git, run backfill, read source BLOBs or perform a global byte proof.

`SUMMARY` reports scan/fact readiness and aggregate observations. `PAGE` requires a complete inventory and one supported, source-bound fact generation. Pending or corrupt facts fail explicitly. Counts, sizes and cursor ordinals use canonical decimal strings within SQLite's signed integer domain. JavaScript preserves them as strings/BigInt. Cursor binding includes snapshot, classifier version, query and last ordinal. There is no inherited million-row offset ceiling.

Each page has at most 20 rows and its full native envelope is at most 32,768 bytes. A byte-shortened page continues after its last included ordinal; a single oversized row gives `ROW_ENVELOPE_LIMIT`. `raw_integrity=NOT_RUN` in summaries and `all_tracked_bytes_exportable=null` when counts alone cannot establish a proof. LFS external completeness is unknown when pointers exist. AI delivery is `NOT_PERFORMED`, read status is `UNKNOWN`.

The extension shows the full format ledger and gaps, next/back controls, separate raw/text/proof fields, and disabled text choices for ineligible or unknown sources. It uses `textContent` for labels/reasons and rejects replies from changed snapshots, filters, repositories or native connections.

## Gaps and raw compatibility

An explicit metadata-only projection is available outside the source/store:

```bash
python -B content-lab/source_eligibility.py --profile /absolute/native-profile.json --repository sce --snapshot SNAPSHOT_ID --gaps-output /absolute/output/GAPS.jsonl
```

Each row binds the snapshot and classifier version. This is a projection, not another ledger. Existing PR002 manifest/part/BATCH formats and identities are unchanged; their historical `text_eligible` field describes the stored text-item projection, while current text use is governed by PR005 facts. PR003 still exports all INDEXED raw parts, including binary and pointer bytes. Tests compare all four manifest artifacts before/after backfill and reconstruct binary bytes from the portable archive.

## Verification and remaining scope

The checked-in 64-entry golden fixture includes 56 INDEXED, 6 EXCLUDED and 2 ERROR rows; 49 text-eligible sources and 15 gaps. Four fixture entries use explicit metadata/fault recipes; it is not an installed-device corpus. Native page union and GAPS output are compared with independent golden DTOs through EOF. Real Git/SQLite tests additionally exercise scanning, exclusions, large sources, native/installed sibling modules, corruption, concurrency and interrupted backfill.

The implementation receipt and full new/changed function inventory are in this directory. Exact published head, CI and merge evidence are attached to the implementation PR. Installed Dell Windows 11/Chrome qualification remains `NOT_RUN`; CI Windows qualification is recorded separately. LFS payload acquisition, additional encodings/derived extractors, generic historical artifact requalification and the wider LAYA4-004/M5-02 roadmap remain open. The existing physical CPU/RAM/disk and explicitly selected operator budgets still apply.
