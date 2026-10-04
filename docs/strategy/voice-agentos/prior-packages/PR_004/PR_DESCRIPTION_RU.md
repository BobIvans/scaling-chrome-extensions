Title: Add bounded streaming Git inventory CLI with atomic snapshot publication

`start_scan` currently captures the complete `ls-tree` output before checking
the 32 MiB limit and then builds a second in-memory list. This change adds an
operator-selected streaming CLI: NUL-delimited records enter a temporary disk
stage, and a verified EOF with exit=0 publishes the entire inventory into the
existing Content Lab SQLite snapshot ledger in one transaction.

Snapshot IDs, entry dispositions and subsequent bounded capture pages stay
compatible with manifest/payload exports. Timeout, malformed output, stderr
overflow and disk exhaustion return explicit failures without exposing partial
inventory. The legacy Native entry point retains its existing limit; long Core
jobs and large-tree Git index binding remain separate LAYA4-003 follow-ups.

Validation: fill with actual commands/results and cold/warm large-tree resource
receipt after implementation. The input package's fixture checks do not prove
application correctness. GitHub SHA/PR/CI and runtime checks are not populated.
