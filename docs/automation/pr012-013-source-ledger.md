# PR-012+013 continuation: immutable local originals

`content-lab/source_ledger.py` records a local FILE or MEDIA origin separately
from its byte version and each observation. It uses Content Lab's existing
`content.sqlite3` connection and adds tables; it does not create a second
database, executor or network authority. An explicit CLI call captures a regular
file into 64 KiB immutable parts. Source identity is namespace/kind/stable
operator key (the absolute URI by default); `--source-key` preserves identity
across a rename while recording both path aliases. Version identity includes
exact raw SHA and declared scope, and an
intent key replays the same observation after a lost reply.

The raw object is only marked COMPLETE after a second full read and a matching
hash, file fingerprint, part count and byte total. A process interruption leaves
STAGING parts, which the same bytes can verify and reuse. A changed source
starts a distinct raw version. The version/head/observation are published in
one final SQLite transaction. `versions` and `raw_parts` traverse to EOF with
bounded pages; `read_part` verifies the requested bytes against its digest.
`delta_parts` compares two versions of the same source/scope, returning exact
ADDED/REPLACED/DELETED 64 KiB part ranges with a pair-bound continuation token.
Its scope is fixed-size byte parts, so an insertion may change many subsequent
parts; it does not claim minimal text changes or semantic media segments.

Example for an explicitly selected local original:

```bash
python -I content-lab/source_ledger.py --store /absolute/store \
  --namespace docs --kind FILE --path /absolute/source.pdf \
  --intent-key 0123456789abcdef0123456789abcdef
```

This is an original-capture substrate. It does not extract PDF/Office text,
perform OCR or ASR, fetch URLs, register Core jobs, write search items or
invalidate criterion evidence. The older ChatGPT import keeps its specialized
`import_raw_blobs` tables; a shared CAS migration/reconciliation remains open.
Do not treat a captured binary as searchable or a successful importer result.

Local tests use exact binary bytes, two origins with one raw object, two path
aliases for one stable key, 23 versions, delta continuation and scope,
an interrupted stage and replay, source mutation, corruption, namespace scope,
and the installed-style isolated Python CLI. Device, large-corpus peak RAM and
the full combined acceptance matrix remain open.
