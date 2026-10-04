# Архивный source audit

Baseline: da6abf4c006e4e7d26fe45ef30fa9d07a356f396. Paths below refer to the
included source excerpts, not observed current main. Coding agent must inspect
actual equivalents and record differences.

| Source | Observed behavior | Consequence for №5 |
| --- | --- | --- |
| repo_context.py `start_scan` | EXCLUDED/ERROR retained; link/submodule share reason | Enrich derived mode facts without renumbering rows |
| repo_context.py `scan_page` | Each raw chunk decoded independently to make text item | Whole-source eligibility must gate new text creation/export |
| repo_source.py `analyze` | UTF8 decode and Python AST distinction only | Add limited binary-control and LFS recognition policy |
| repo_context.py `get_snapshot` | Complete snapshot triggers whole proof and changes; offset <=1,000,000 | New coverage route uses cheap read-only queries/keyset |
| repo_context.py `selection` | INDEXED + per-chunk item_id decides binary omission | Add source gate for direct and related source chunks |
| native_adapter.py | Trusted alias/profile/namespace and exact field allowlist | Reuse all scope checks for coverage command |
| agent-bridge/durable.mjs | 16,000-byte input, 192,000-byte output, 10,000-ms timeout | Coverage cannot start backfill/full validation |
| repo-review-ui.mjs | Display via textContent; selection checks INDEXED | Display source facts; disable ineligible text selection |

Other observed limits retained as open work: MAX_FILE=8 MiB, MAX_TREE=32 MiB,
whole index set comparison, full snapshot proof/delta memory, offset bounds,
list_snapshots LIMIT 20, selected path cap 10, source_roots/exclusions profile
count cap 50. These have different scopes. None is an allowed hidden full-repo
truncation; no claim this format PR removes them all. See FOLLOWUPS.json.

Current code for PR-004 is unavailable in this chat; its streaming CLI and
atomic SQLite scope are USER_REPORTED. PR-003 contract is likewise not read.
PR-002 package and its original queue were actually materialized/read here.
Historical auto-review publication status in source stays historical; the
current task creates an implementation ZIP and performs no repo publication.
