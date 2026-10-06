# Ambient Life Context Harvester

Reuse BrowserWatch, streamed chat archive, conversation imports, Drive ingestor, folder watcher, canonical Library and labels.

## SourceAdapter
`discover() → SourceDescriptor[]`
`observe(cursor) → Change[]`
`materialize(change) → RawArtifact`
`derive(raw) → DerivedRecord[]`
`checkpoint()`

Adapters are data-only and never grant effect authority.

Planned adapters: browser page/chat/download; Drive/Docs/Sheets/Slides with OAuth onboarding; local files/downloads; repos; AI exports/live conversations; generic user-requested HTTP(S); media/PDF/docs/spreadsheets raw bytes + extractor projection; explicit email/Telegram/other connectors when configured.

Any-data principle: preserve raw bytes + MIME + origin + times + hash + source identity even when no extractor exists. Extraction/indexing is derived.

Labels deterministic first: source, mime, host, project, conversation, repo, status. Semantic labels are suggestions until policy applies them.

Every adapter has scope, pause, tombstone/delete, freshness and sensitivity controls.
