# Unified roadmap PR-014 + PR-015 implementation

A local source can now become an immutable, provider-neutral task packet through
the existing Content Lab SQLite owner. Selection keeps exact byte ranges and a
WHY_THIS_PACKET reason; share projections preserve originals, mask configured
protected literals and export hashed parts to an offline folder. Imported model
results remain AI_CLAIM proposals. No result text, DONE label or artifact hash
alone closes a criterion, creates a grant or runs an executable.

This is one implementation PR for WS-013–017. It adds working local paths while
keeping the complete strategy's criterion-level and physical-device gates open.
It is not a claim that all 322 original criteria have been qualified.

## Owners and contracts

| Workstream | Implementation | Scope and acceptance limits |
|---|---|---|
| WS-013 | `context_library.py`, `context_packets.py` | Raw BLOBs, immutable selection/packet/projection/delta, bound result quarantine and local typed reads; no network provider delivery or universal secret detector |
| WS-014 | `context_recovery.py` | SQLite Online Backup, all captured DB BLOBs, integrity/hash verification, copy-only migration rehearsal, tombstone overlay, explicit activation journal, data-only offline sync and conflict preservation; external originals, policies and credential stores excluded |
| WS-015 | `context_library.search_sources`, `context_benchmark.py` | Namespace/project/time scopes before snippets, exact ID/path/quote, historical corrections and conflict groups, synthetic 10k oracle; semantic relevance and production device performance remain unqualified |
| WS-016 | `desktop/library.py`, `desktop/install.py`, `Install_Windows.ps1` | Versioned per-user Python/Tk bundle, typed paged local workflow and independent STOP transport; no standalone signed EXE, physical Windows accessibility/performance pass |
| WS-017 | `context_runtime.py`, `automation_core.Core` | Operator-registered handlers/roots/destinations, build+grant+test-log qualification, persisted operation identity, Core queue/lease and durable STOP epoch; no money-moving or remote-send capability |

The serialization identity is `OCC_PYTHON_JSON_V1`: sorted compact Python JSON,
UTF-8 and nonfinite values rejected. It is **not RFC 8785/JCS**. Full original
hashes and raw byte offsets are distinct from preview text and derived legacy
ITEM_TEXT_UTF8 references. Split UTF-8 chunks remain raw-readable even when a
part cannot enter FTS. Offline imports rebuild eligible current items/FTS/heads
through the same owner. Pages/parts bound working memory, not total corpus or
part count. The export file manifest itself currently grows with file count;
this is an explicit outstanding large-export memory qualification gate.

## Setup and operation

See `desktop/README_RU.md` for the installed workflow. Add the example service
object under `policy.context_services.local`, preserving the existing policy
schema, `max_parallel: 1` and `money_budget: 0`; add `context_service: "local"` to
the native profile. Edit absolute roots, namespace, actions and destinations.
Old profiles retain the read-only desktop contract.

Run the fixed backend CLI `context_runtime.py --profile <absolute-profile>
initialize` for additive schema setup, then `qualify` to execute the independent
local context tests. The log hash, current shipping files and grant digest must
match before writes can enqueue and before a worker dispatches. UNKNOWN/STALE
qualification never becomes AVAILABLE_LOCAL. Local test proof does not become
Windows device proof.

Typed `durable.library` has `namespace`, `action`, `arguments` and, for writes,
`operationId`. Reads return a bounded DATA_ONLY DTO; writes enqueue a known
`context_service` job in the existing durable queue. Caller-supplied commands,
SQL, executables, environment, arbitrary destinations and unknown action fields
are rejected. Large result JSON is read from an operator-scoped local file, not
stuffed into the 16k IPC input frame. Desktop invokes only the fixed registered
Core worker entry point and checks the whole backend digest first.

The transport journal records IDs only. After ack loss, OPERATION resolves the
same persistent Core task key; a fresh ID is not an automatic retry. Staged
capture/packet/projection bytes can resume under the same identity when hashes
and STOP epoch match. Other interrupted effects stay reconciliation-required.
No imported model result is a reconciliation decision.

STOP has a separate client lock and control path. Only a committed
DURABLE_FENCED acknowledgement certifies the new-dispatch fence. Running effects
stay cancellation-requested and expired effects stay UNKNOWN/needs-reconciliation.
Resume refuses running/orphaned work and cannot restart old cancelled jobs;
old multipart intents are fenced by the persisted STOP epoch. Slow/locked store
or missing acknowledgement is STOP_UNCONFIRMED, never success. The keyboard
binding is local to the context window; global OS hotkey and physical Windows
latency/accessibility tests remain open.

## Recovery and boundaries

Online Backup pins a read generation while the normal writer can continue in
WAL. Raw capture parts, packet parts, importer BLOBs and repository chunks are
in the same snapshot. Backup reports captured DB bytes only; originals elsewhere
and credentials are not silently included. The local backup is unencrypted and
says so in its manifest. A restored copy pauses Core and fences running jobs;
credentials and policy must be reconnected explicitly.

Activation is a separate maintenance API requiring the operator's actual
process-stop check. It retains the previous DB and leaves a durable maintenance
marker on ambiguity. Fresh owners refuse to open a marked store. Activation
reapplies the current deletion ledger even if it changed after rehearsal.
Crash recovery chooses a verified database explicitly; device kill-injection at
every rename boundary is still an acceptance gate.

Tombstones hide current reads and block late capture publication. Physical purge
is explicit and refuses dependent packet retention. Existing external exports
and backups cannot be claimed erased. Offline sync has a data-table allowlist,
namespace/hash checks, atomic import and replay conflict handling; it contains no
jobs, executable policy, grants or credentials. Concurrent heads preserve both
revisions and a conflict row rather than overwrite local state. It is a portable
snapshot/event exchange, not a network collaborative editing protocol.

## Validation and remaining gates

`test_context_services.py` checks independent fixture bytes, hashes, exact source
scope, malformed result quarantine, immutable selections, >1000 parts, secret
canaries across part boundaries/metadata, crash/resume, stale result binding,
backup under a writer, restore tombstones, corrupt sync rollback, job identity,
qualification drift and STOP. Desktop tests additionally install a real bundle,
qualify/run its backend, complete the local source-to-export cycle, detect
backend drift, reject unsafe uninstall and verify separate STOP transport.

`context_benchmark.py` creates a deterministic 10k-source synthetic corpus and
checks independent exact expected keys, scope traps, missing matches and all
rows to EOF. Timings distinguish first and repeated query passes. The OS cache
is not flushed; these measurements are not cold-boot or semantic-quality proof.

`acceptance-status.json` retains all original 322 criterion IDs, their case
families and workstream mapping. Each remains OPEN until its own independent
criterion assertion and downstream gates pass. The attached family tests cannot
close broad tasks automatically. Required remaining qualification includes
physical Windows/Dell launch/install/upgrade/accessibility and STOP latency,
semantic relevance/production-scale performance, unknown external effect
reconciliation, trust-version evidence correction, version-aware editor
navigation, large-export memory, and full fault injection/retention/migration
coverage. Existing baseline functions and dependency PRs are not blanket-certified
by this package.
