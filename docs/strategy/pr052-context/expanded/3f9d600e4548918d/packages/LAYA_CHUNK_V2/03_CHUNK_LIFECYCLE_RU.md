# Chunk lifecycle

`DISCOVERED → NORMALIZED → CHUNKED → LINKED → INDEXED → CURRENT`

Из CURRENT:
- source changed → STALE
- newer canonical owner → SUPERSEDED
- contradictory truth → CONFLICTED
- missing/failed evidence → BLOCKED
- validated evidence → QUALIFIED

## Repo rebuild
Git diff → changed files → reparse → preserve IDs for unchanged symbols → supersede changed chunks → create replacements → walk reverse dependencies → invalidate derived summaries/context packs.

## Derived content
Every summary/embedding/classification stores `derived_from[]`. Any stale source makes derived data stale.
