# PR-002: captured repository manifest and range index

A completed Content Lab repository scan can now be inspected or projected into
four deterministic metadata files. The existing SQLite database remains the
source of truth; projection does not read the worktree or execute repository
code. Native `durable.repo.manifest` advertises `INFO`, `ENTRIES`, and `PARTS`.

## Whole repository capture

The Git scanner streams the entire NUL-delimited tree into its existing ledger.
There is no application cap on the number of entries, tree-output bytes, or blob
size. The former 8 MiB blob rejection and 32 MiB Git-output rejection are removed.
When a scan is resumed, legacy `FILE_TOO_LARGE` entries are retried from the
earliest affected ordinal. Working-copy hashes and Git-index comparisons also
use block reads or temporary disk workspace.

Large blobs are spooled to temporary disk to determine their exact hash and
secret disposition before any chunks become visible. Capture then saves every
byte as at most 4096-byte chunks, keeping UTF-8 code points intact. The 8 MiB AST
workspace threshold changes analysis to `UTF8_STREAM_NO_AST` or
`BINARY_OR_NON_UTF8`; it does not omit bytes. Streaming secret detection preserves
protected-content exclusions even across block boundaries and arbitrarily long
field whitespace.

Native requests still have their existing 10-second lifecycle. For a capture
that takes longer than one native request, use the explicit local operator CLI,
which has no native request timeout:

```sh
python -B content-lab/repo_context.py --profile /absolute/native-profile.json --repository sce
```

Its output reports the pinned snapshot ID and progress. Resume the same capture
with `--snapshot <snapshot-id>`. Hardware, available disk space, and SQLite/Git
storage capacity determine practical scale. Source exclusions, links, submodule
metadata, missing objects, and unsupported path dispositions remain explicit.

## Metadata projection

```sh
python -B content-lab/repo_manifest.py --profile /absolute/native-profile.json --repository sce --snapshot <snapshot-id> --output /absolute/manifest-output
```

On Windows use absolute Windows paths for the profile and output. Output must
be outside both the source checkout and the SQLite store. Reinstall the native
host after updating to copy the new `repo_manifest.py` sibling.

| Artifact | Contents |
| --- | --- |
| `REPO_MANIFEST.jsonl` | One ordered row per original entry, including every exclusion/error and its original reason/mode/OID/size |
| `PARTS_INDEX.jsonl` | One row per indexed raw chunk: immutable IDs, source ordinal/path, half-open byte interval, byte count, hashes, and text eligibility |
| `VALIDATION.json` | Full reconstruction proof for indexed captured bytes, Git blob OIDs, part revisions, and linked text records |
| `BATCH.json` | Deterministic scope/policy binding, counts, and exact serialized output hashes; written last |

One SQLite read view covers inventory, chunks, and proof. The writer traverses
ordered cursors, never gathers repository raw bytes with `fetchall`. Missing or
duplicate parts, gaps/overlaps, corrupt revisions or text records, mismatched
Git blob OIDs, incomplete inventory, and orphan/non-indexed chunks prevent
publication. Empty files have one `[0,0)` chunk; empty trees have empty JSONL.
JSON escaping preserves Russian, quotes, tabs, and newlines in stored paths.

Files are staged under the destination parent, flushed, then published by whole
directory rename after proof passes. Interrupts or disk-full failures never
advertise a verified destination. Repeated export compares all four outputs;
a damaged existing destination is rejected and preserved. Full crash-resume
payload archives remain the PR-003 scope.

## Browsing and proof scope

The existing repository panel has separate manifest summary, all-files, and
all-parts controls, page navigation, file-to-parts, and part-to-source navigation.
Changed repository/snapshot/filter queries invalidate delayed replies. Rows use
`textContent`; source paths never become HTML.

The maximum 20 rows and 32768 bytes apply to **one native response frame**.
`nextOffset` advances only by emitted rows and reaches every tail, including
more than 20 parts in one file. A single over-budget row returns
`ROW_ENVELOPE_LIMIT`; it is never silently dropped. File filters use query-relative
offsets. Native callers cannot choose root, store, filesystem output, or argv.

Native INFO reports global validation `NOT_RUN`. PARTS verifies only its returned
rows. The CLI reports full captured-byte proof after it actually runs. Captured
historical bytes can be inspected under their active operator profile after
HEAD moves; this does not claim current worktree freshness. An inventory with
errors/exclusions may be complete while `all_tracked_bytes_exportable=false`.
AI packet inclusion/read status and generated dependency graphs remain separate.

## Verification and remaining scope

Real Git/SQLite fixtures cover 50 entries (46 indexed and four metadata gaps),
UTF-8/CRLF/BOM/binary/empty data, pagination tails, a blob above the former 8 MiB
limit, a synthetic streamed tree above the former 32 MiB ceiling, concurrent
SQLite writes, historical snapshots, corruption mutations, and filesystem
failure at each publication stage. NativeClient → JobHost → Python subprocess →
SQLite roundtrip exercises negotiation, navigation, restarts, and legacy review
exports. The installed Windows Chrome/native-host workflow requires a separate
device receipt; cross-platform CI does not substitute for that qualification.

LAYA4-009 and M5-02 retain their broader goals/groups/AI-packet work. This PR
implements the metadata/range-index slice and unrestricted-size capture path.
