# ROADMAP-PR-012+013 implementation progress

This change adds an independent, bounded read path for repository history and
path delta. `durable.repo.history` and `durable.repo.delta` use keyset cursors
over the existing SQLite `repo_snapshots` and `repo_entries` owner. A frame
contains at most 50 records; `next_cursor` continues until explicit `eof`.
The cursor binds namespace or exact head/base snapshot identities, and the
delta reports additions, deletions, modifications, and uniquely provable
same-byte rename peers. No total snapshot/path count is configured.

The Native profile chooses the repository and namespace; callers cannot pass
filesystem roots. The installer carries `repo_history.py`. Desktop validates
the DTOs and can atomically export complete snapshot and delta JSONL with
checksum receipts; a cancelled export does not publish a partial directory. The existing
`durable.repo.get` summary still shows a small preview, including its
`display_truncated` flag. Use the new delta pages for complete path history.
Delta rejects an incomplete head/base and accepts an optional exact
`baseSnapshotId` for historical comparisons. Continuation binds that base.

## Validation

`python3 -m unittest test_repo_history -q` covers 26 snapshots, 25 changes
in one revision, continuation to EOF, rename peer, request scope, cursor
misbinding, incomplete snapshots, explicit historical bases, long Unicode
paths, and Native dispatch against real Git and SQLite.
`desktop.tests.test_repo_history_client` covers reply validation and export.
Existing Desktop transport tests and package manifest verification passed
locally; Tk UI needs a Windows/Xvfb run. Device and CI
qualification are separate from this local test.

An operator opt-in (`desktop_scan_enabled`) exposes the existing `repo_scan_runs`
ledger to Desktop when its schema is already installed. The UI offers START,
STATUS, STEP, PAUSE, CONTINUE and CANCEL with revision/cursor fencing; an
installed client can reopen and recover status. This is manual page stepping,
not a background scheduler. The Native adapter refuses Desktop mutation by
default, and no Desktop schema migration occurs. A deadline or window close
may interrupt the active page, which must be retried from the committed cursor.

## Open stages from the combined package

- WS-002: finish Core job integration, background execution/progress on the
  installed Windows host, and installed-device qualification. Desktop currently
  controls the existing scan ledger one page at a time.
- WS-003: migrate existing summary and selection/export consumers to bounded
  traversal; the old `snapshot_changes` summary still materializes graph data.
- WS-006: content addressed derived cache, full delta ranges, and selective
  evidence invalidation require the upstream static graph and storage contract.
- WS-009/010/011: document/OCR, media/ASR, and web/RSS/GitHub importer adapters
  await the shared source address/importer owner. Their acceptance cases remain
  open. A history page is not evidence that external importers exist.

The combined package's 101 source criteria remain open until independently
qualified. Current main does not yet contain the planned PR-010/011 contracts;
this branch is an integration stage and should not be merged as package
completion.
