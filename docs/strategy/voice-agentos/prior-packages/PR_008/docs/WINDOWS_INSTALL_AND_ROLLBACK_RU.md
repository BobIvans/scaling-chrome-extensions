# Windows 11 pilot: launcher, preflight и сохранение данных

Target device: Dell Latitude 5400, Windows 11, 16 GB RAM. Device status NOT_RUN.
Runtime versions record the actual installed Python/Tk/backend; no invented pin
or installation receipt. Qualified supported Python version must match actual
backend requirements and Tk availability.

Pilot prerequisites: existing backend installation, operator profile and ready
content.sqlite3, configured absolute Python executable with Tk. If absent,
SETUP_REQUIRED with actionable text; zero-setup installation is an open followup.
Current Chrome host Install.ps1 is a separate pathway with extension ID/Node/
Codex/C# dependencies. Desktop launcher uses Python directly and can run with
Chrome closed without installing that host pathway.

Candidate deployment files:

| Shell-owned | External, retain on uninstall |
| --- | --- |
| desktop app/client/preflight code + version manifest | Existing native backend and sibling modules |
| launcher and optional user shortcut | Operator profile/policy |
| local connection config and shell diagnostics | Corpus/SQLite/raw blobs/jobs/review/task data |
| per-version shell directory | User-selected draft output directories |

BackendRoot/ProfilePath/PythonPath are selected at install/configure, then bound
by preflight/handshake. No UI-supplied argv/SQL/executable in RPC. Backend source
comes from current qualified installation; archived sources are study references.
Config default data path is never a second fresh store. Show handshake store
identity and compare it to the browser/native profile fixture.

Launch_Windows.ps1 resolves its shell root via PSScriptRoot, uses literal paths,
checks script/config/version manifest, runs preflight then desktop via configured
Python and argument array. Do not encode goals/queries into shell commands.
Unicode paths/paths with spaces are required fixtures. Missing Python/Tk/backend/
profile, denied file access and protocol mismatch produce useful local errors.

Diagnostics: observed Python/Tk/OS versions, app source SHA, adapter SHA, profile/
store identity, capabilities/budgets and typed failure codes. Raw text/query,
profile contents and credentials are not logged. Write diagnostics only to a
shell-owned directory; offline index remains a manual fallback.

Versioned shell upgrades install beside current shell. No backend/data migration
or profile rewrite in this PR. Rollback selects prior shell and re-handshakes;
protocol mismatch stays blocked, do not silently revert backend. Owned-file
manifest is verified before removing a shell version; reject unknown/reparse
paths and never remove an external backend/data/output root. Uninstall behavior
must be demonstrated with corpus sentinel and subsequent browser read.

Receipt needed: all three pilot actions with Chrome closed, repeated launch,
paths with spaces/Unicode, current corpus visible in both clients, keyboard/
timeout cleanup, measured peak memory/latency. Unit fixtures do not replace
installed-device observations. Full self-contained runtime bundle, packaging
signing, installer and updater remain separate followups after this measurement.
