# PR-009: selected ChatGPT JSON original and extraction history

The Content Lab importer keeps the exact bytes of each selected local JSON in
`content.sqlite3`, including BOM, CRLF and fields unknown to the adapter. A
source version binds `(namespace, source_key, raw SHA-256)`; an extraction binds
that version to the pinned fidelity/text/attachment adapter key. A repeated
version reuses the blob, source version and extraction. A second selected file
path adds an origin without copying the blob. Text item IDs and existing item
payloads remain compatible with `chatgpt-export.v1`; current raw lineage belongs
to the extraction, not to an old item's `export_sha256`.

```bash
python content-lab/content_lab.py ingest-chatgpt --file conversations.json \
  --store ./local-store --namespace selected --source-key export-main
python content-lab/content_lab.py inspect-chatgpt --store ./local-store \
  --version-id VERSION_ID --extraction-id EXTRACTION_ID --offset 0 --limit 50
python content-lab/content_lab.py read-chatgpt-original --store ./local-store \
  --version-id VERSION_ID --output ./recovered.json
```

`--source-key` is optional for older callers. Its compatibility value hashes
the canonical absolute input path, so a rename changes source identity. Use a
stable explicit key across locations when that is the desired lineage. An
existing output requires `--overwrite`. The original read verifies byte count
and SHA-256 before an atomic file publication. Inspection returns at most 100
node records and 1 MB of node metadata per page. An oversized individual node
is represented by its ID, byte count and digest with `metadata_omitted=true`;
the next page advances past it. Inspection never includes original JSON bytes.

The node ledger records every observed mapping key, including structural,
empty and non-text nodes, both branches, declared parent/children, JSON Pointer,
declared author fields and source message time. Gaps cover missing references,
inconsistent edges, missing current node and cycles. Pointers identify semantic
JSON locations, not byte offsets. Remote completeness remains unknown. An
attachment pointer is metadata; no payload retrieval or network fetch occurs.

Captured invalid input commits raw bytes with an `ERROR` extraction and leaves
message, attachment and conversation heads untouched. An input rejected during
regular-file capture has no original version. Transaction failure rolls back the
original, ledger, items, FTS and selected heads. A post-commit JSON receipt
failure returns `COMMITTED_WITH_RECEIPT_WARNING`; replay rewrites receipts from
the immutable stored item payload. Selected valid imports mark absent message
and attachment heads only inside conversations in that export, with reason
`NOT_OBSERVED_IN_SELECTED_EXPORT`. This is not remote deletion; other
conversations in the namespace remain present.

The selected JSON budget remains 64 MiB. Total mapping nodes and child references
are each capped at 100,000, and serialized ledger bytes at 64 MiB. These are
per-import memory and storage guards, distinct from repository inventory and
archive coverage, which has no fixed total file-count ceiling. The importer
parses one bounded JSON in memory and does not claim streaming/out-of-core JSON
or installed Windows device qualification. No new Native/desktop IPC route is
exposed. Source text, unknown fields and declared role are inert data.

The supplied 18 synthetic raw cases are checked through the actual importer
in `test_import_fidelity.py`, with failure injection and existing importer
regressions. CI runs the repository's four regression suites on Ubuntu and
Windows; the installed Dell/Chrome/native host remains a separate qualification.
