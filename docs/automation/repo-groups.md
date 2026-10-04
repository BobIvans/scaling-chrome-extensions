# PR006 — Python groups and complete captured-part references

The foreground CLI creates a derived catalog from a verified PR002 manifest and
the existing Content Lab SQLite snapshot. Every tracked entry has one logical
source/group membership. Every captured raw part has one primary segment
reference, including empty and binary parts. Source payload stays in the
existing store; the base manifest and portable PR003 archive remain immutable.

There is no total source, group, part, segment, or processing-time ceiling.
The existing iterative graph uses O(V+E) memory. Raw references, navigation and
verification use disk staging and bounded pages. Available memory/disk and the
operator's optional resource policy still determine which corpus fits a device.

## Operator CLI

```powershell
python -I -B C:\OCC\content-lab\repo_groups.py `
  --profile C:\OCC\native-profile.json --repository sce `
  --manifest C:\OCC\captured-manifest `
  --output C:\OCC\groups
```

`--policy`, `--declared-map` and `--resources` accept absolute operator JSON paths.
Profile/alias/namespace/store/snapshot scope uses the installed archive/manifest
adapter. Output must be outside source, store and input directories. Installer
copies the new sibling module. No Native endpoint, worker or AI sender is added.

The snapshot must be captured and its authoritative bytes, Git blob OIDs,
identities, parts and ranges must pass the existing full manifest proof. The
CLI emits one compact receipt. Huge arrays are written as local JSONL, never
inserted into Native frames. Selected review/export APIs keep their semantics.

## Whole-source eligibility boundary

PR005 #42 appeared during implementation. The automatic adapter reads its
actual `repo_entries.analysis.format_eligibility` owner through
`source_eligibility.facts_status/project_facts`: schema
`occ.format-eligibility.v1`, classifier `utf8-controls-strict-lfs3.v1`.
It binds the full source identity, classifier version, owner build and streamed
projection digest. Code qualification requires whole-source ELIGIBLE text and
saved PYTHON_AST at both the fact and analysis boundary. No classifier is
reimplemented here.

Missing/unsupported historical facts keep sources and raw references with
FORMAT_BACKFILL_REQUIRED and `graph_scope=BLOCKED_ELIGIBILITY_UNMAPPED`.
Use the owner's explicit backfill CLI; grouping never performs repair-on-read.
Corrupt bindings fail before publishing. Binary/control-bearing/non-UTF8 and
LFS sources retain their raw references with text/code qualification false.

An optional `--eligibility` operator-normalized projection is also supported.
It supplies schema/version, owner, upstream digest, exact base-batch/snapshot/
profile binding, and SHA256-bound `SOURCE_ELIGIBILITY.jsonl`. Its schema is
`occ.repo-group-eligibility-input.v1`, a separate normalization boundary for an
explicit observed owner, not a replacement PR005 wire schema.

`ELIGIBILITY.json` example structure is in `pr006/ELIGIBILITY_INPUT.example.json`.
Each JSONL row is `occ.repo-source-eligibility-adapter.v1` with path,
file_sha256, captured_state, text_exportable, code_analysis_eligible,
format_kind, reason and revision. All paths must match the full ledger exactly;
hash/state mismatch, unknown schema, duplicate row, partial-source proof and
projection tamper fail. Whole-source eligibility never comes from a part's
text_eligible flag. The ZIP's proposed view remains synthetic test data.

For qualified Python sources the saved `PYTHON_AST` analysis is checked against
the exact persisted whole-source bytes using the existing bounded AST window.
Stale analysis fails. Parse-failed/outside-window sources keep their metadata
and references with explicit gaps. This check never imports source modules.

Actual PR005 capture → facts → automatic grouping/CLI is checked on the real
Git/SQLite fixture, including legacy absence and bound-fact corruption.

## Graph, identity and related evidence

The existing `repo_source.import_graph` and iterative `components` run in
deterministic order, with cooperative resource checks. Module candidates retain
ineligible paths to avoid hiding ambiguity. Only unambiguous local Python
imports whose endpoints are qualified participate in SCC. External, dynamic,
ambiguous, ineligible and JS/TS dependencies have explicit unresolved rows.

Source IDs bind namespace/repository/path, without snapshot or global ordinal.
Group IDs bind planner version and sorted member source IDs. Unrelated additions
keep existing IDs; changed SCC membership changes group ID. Group revisions
bind member hashes/qualification, relevant relations/gaps and frozen policy.
The child batch also binds base batch, profile, analysis/eligibility digests,
roots, declared map, planner/parser/resolver builds and resources.

| Relation | Topology | Evidence |
| --- | --- | --- |
| PYTHON_STATIC_IMPORT | Yes | Saved static import; start line only |
| STATIC_TEST_IMPORT | Yes | Qualified static import from a test path |
| HEURISTIC_TEST_CANDIDATE | No | Filename rule, explicitly a candidate |
| OPERATOR_DECLARED_CONTRACT | No | Trusted map with both endpoint hashes |

Declared links use `occ.repo-declared-relations.v1`; each link has from, to,
from_sha256, to_sha256 and kind=OPERATOR_DECLARED_CONTRACT. Missing/excluded
endpoints and stale hashes create gaps instead of fabricated targets. Ownership
remains UNSPECIFIED. Static links do not establish executed tests, measured
coverage, installed capability or AI read.

## Segments and publication

Default policy budgets one segment to 4096 referenced raw bytes, 8192 actual
compact UTF8 JSON bytes (including newline/headers/IDs/neighbours), and at most
16 references. All three are configurable per segment. These are not total
corpus limits. Prev/next chains continue until the real group EOF.

An immutable part larger than the chosen byte budget fails
PART_BUDGET_TOO_SMALL. A single nonfitting frame fails REFERENCE_ROW_TOO_LARGE.
There is no truncation or invented subrange. Part IDs/revisions/hashes/ranges
are preserved, and related links never duplicate primary raw ownership.

A private temporary SQLite index bounds the writer's cache and supports
uniqueness, readback and navigation. It is disposable derivable staging, removed
before publication; no metadata authority or persistent database is added.
Readback compares every reference to the existing SQLite owner and checks
membership, group identity, segment chains, frames and relation ledgers.

JSONL and HTML proofs are verified before GROUPS.json is written last. Files
are synced and a single directory rename publishes the complete catalog.
Kernel locking serializes writers for one output. A repeated identical result
is validated/reused; different input needs a new output path. Faults, disk full
or cancellation preserve prior output and source state. After process death,
unpublished stages are ignored; the next run starts a fresh plan.

| Output | Content |
| --- | --- |
| GROUPS.json | Child batch binding, counts, artifact proofs |
| GROUP_HEADS.jsonl | Group IDs/revisions/kind/reason/owner and counts |
| GROUP_MEMBERS.jsonl | Full entry/source/group and eligibility mapping |
| GROUP_PARTS.jsonl | Bounded primary raw references and continuation chain |
| RELATIONS.jsonl / UNRESOLVED.jsonl | Typed provenance and exact gaps |
| ELIGIBILITY_VIEW.jsonl | Frozen normalized whole-source qualifications and reasons |
| COVERAGE.json | Separate membership/raw/text/graph/AI dimensions |
| NAVIGATION.jsonl / INDEX.html / navigation/*.html | Portable escaped local navigation |
| Original four manifest artifacts | Byte-preserved base metadata |

`--resources` schema `occ.repo-group-resources.v1` has graph_input_bytes and
timeout_seconds, both default null. An explicit limit blocks with
GRAPH_RESOURCE_BUDGET; it never publishes a shortened verified catalog. The
byte budget counts normalized graph input/ledger data, not enforced OS RSS.
MemoryError is also a blocker. Out-of-core SCC is a separate future extension.

## Observed qualification and remaining work

Runtime tests build a real Git tree from the supplied raw fixture, capture it in
SQLite, verify the manifest and run the actual planner/CLI. Independent manually
labelled and mutual-reachability oracles check SCC, shuffled input and stable
IDs. The 70-entry fixture keeps its 3-node cycle, >20 continuations and full
tail. A separate 5000-node ring yields one SCC and >1000 segments without a
recursion or total-count ceiling. Fault tests cover stale analysis, map/hash/
range/member/head/relation/frame tamper, disk failure, process crash, lock
release, strict scope and portable links. Existing PR001–004 regressions remain
required on Ubuntu and Windows CI.

The actual combined repository checkout was also captured through Git → SQLite →
manifest → automatic PR005 facts → PR006 CLI: 418 entries, 407 groups, 1828
segments and all 2097 captured parts, with the four base metadata files byte
identical. The Linux observation took 2.46s to capture and 2.69s to group, with
26.3MB observed planner-process peak RSS; this is that checkout, not a bound for
other repositories or Windows device proof. See
`runs/PR006_CHECKOUT_QUALIFICATION_2026-10-04.json`.

Full details are recorded in `runs/PR006_IMPLEMENTATION_RESULT_2026-10-04.json`.
Installed Dell Windows 11/Chrome qualification and paired same-budget
usefulness/AI trials are not observed here. JS/TS
resolver/provenance, a Native group picker and AI packet delivery remain separate
adapters. This PR does not close broad LAYA4-008 or the 160-task roadmap.
