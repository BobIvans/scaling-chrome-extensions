# PR-008: Desktop stdio и Windows shell

Вход: `ROADMAP_PR_008_DESKTOP_STDIO_WINDOWS_RU_2026-10-04(1).zip`, SHA-256
`04e4182c262d40683d25ba3af6db249b53a5500a9c7a73ca5738ce825ca112dc`.
Проверенная база: `9fbadef2714fae92e516a80b52d29cb9824b0e44`. AGENTS.md в checkout нет.
Дополнительно интегрирован main `8414ce4bda6618e58dea64093bc9a22a7161c5e7`.
Пакет №8 адаптирован к текущим owners после merges №1–4 и PR009 original-source fidelity; archived sources не
заменяют текущий код. Номер пакета не является GitHub PR number.

## Результат

Локальное Tk-окно подключается без Chrome к существующему профилю и corpus,
показывает путь данных, ищет источники, читает выбранные items и атомарно сохраняет
`TASK_DRAFT.txt` с целью, scope и критериями. Полный manifest сохранённого repository
snapshot можно потоково выгрузить отдельной кнопкой, проходя настоящие pages до EOF.

В этом слое нет общего ограничения числа файлов, частей, страниц или объёма repo.
20 строк — размер metadata page; 20 search matches — bounded top results; 10 items
и 48000 bytes — существующий пакет выбранного контекста. SQLite/disk/CPU и время
конкретного запроса определяют фактическую производительность. Desktop не меняет
полный scan/ZIP64-export owners и не обещает бесконечную память/context window AI.

## Владельцы и функции

| Функция | Код | Проверенная граница |
| --- | --- | --- |
| `durable.info` | `content-lab/native_adapter.py` | Actual read capabilities, budgets, namespaces, store readiness; metadata до Core, без init/migration |
| `--desktop-stdio` | тот же dispatcher | Read allowlist, один loaded profile/policy для dispatch и response binding; legacy browser wrapper сохранён |
| Existing readonly SQLite | `automation_core.read_connection` | `mode=ro`, `query_only`; existing search/context algorithms; UI без SQL |
| Manifest readonly route | `repo_manifest.page/read_view` | Existing immutable snapshot/profile binding; no schema init |
| Direct subprocess | `desktop/client.py` | Configured Python `-I -X utf8`, fixed argv, shell=False, environment without provider secrets |
| Strict IPC | тот же client | UTF8, duplicate/nonfinite/trailing JSON, operation/schema/identity/digest, combined pipe budget |
| Cancel/timeout/close | client + Tk | Child reaped/pipes closed; bounded event queue; no Tk calls from workers |
| UI lifecycle | `desktop/state.py`, `app.py` | requestId/generation/query/namespace/identity fences; stale results discarded |
| Draft projection | `desktop/draft.py` | Exact selected items, owner digest vs output-file hash; staged directory + atomic no-replace publication |
| Complete metadata projection | `save_manifest`, `manifest_pages` | One page in memory, JSONL to disk, advancing cursor, stable batch/total, all rows to EOF |
| Windows launch/preflight | `Launch_Windows.ps1`, `preflight.py` | Runtime/Tk/backend/config readiness; actual runtime/path diagnostics |
| Shell staging/uninstall | `package.py`, `OWNED_FILES.json` | Hash-verified owned files; reject unknown/reparse/overlapping roots; preserve backend/profile/corpus/outputs |

Initial reads: info, repo.list, search, context. Manifest is advertised only when
current dispatcher/module and existing repository schema are present and is
qualified by real-Git/SQLite/browser-vs-desktop integration tests. №5 coverage and
№6/7 parsers are not advertised from roadmap metadata. Their implementations
remain separate parallel packages. No second store, FTS, queue or scheduler.

Profile identity hashes the same loaded profile and policy used for the request.
Store identity binds canonical database path plus device/inode, stable across
ordinary writes/restarts; replacement DB or changed profile forces a handshake.
Adapter SHA describes the installed module. Complete backend bundle identity
stays null/UNKNOWN_BUNDLE until a verified bundle manifest exists.

Local draft metadata preserves exact context/source revisions/hashes,
scope=SELECTED_ITEMS, canonical_task_id=null, corpus_total=UNKNOWN and DATA_ONLY.
It never advances provider sent/read/task/merge state. Full metadata export
includes every snapshot row, including gaps/binary dispositions; its receipt
does not claim raw bytes or global raw validation. Source paths/titles are data.

Atomic publication supports Windows and Linux. Windows uses no-overwrite rename;
Linux uses RENAME_NOREPLACE. Earlier outputs, including a concurrently created
empty folder, survive. A failed write/cancel leaves no published successful draft.

## Проверки

Repository gates after integrating current main: 256 Content Lab, 46 Native Bridge, 8
qualification adapter, 112 extension tests passed. Desktop: 22 tests discovered,
21 passed locally, 1 Tk display test skipped locally. CI runs that Tk test through
Xvfb on Ubuntu and directly on Windows, and verifies owned-file hashes.

New real fixture: 76 tracked files, including binary data, EN/RU/CRLF text; all
entry/part pages saved to EOF; context and manifest domain DTOs equal legacy
browser dispatcher DTOs. The owner namespace grammar includes `chatgpt:code`; retained ChatGPT original
imports project through the same read owner without migration. Corpus hash/schema retained through read/startup/uninstall.
Independent wire fixtures from the input ZIP cover malformed encoding/framing,
operation/protocol/profile changes and exact owner digest. Fault helpers exercise
stdout/stderr floods, combined-budget overflow, timeout, cancellation and one
in-flight read. Disk-full/conflict/race fixtures retain earlier outputs.

Executable tests: `desktop/tests/test_desktop.py`, `desktop/tests/test_app.py`.
Machine receipt: [PR008 implementation result](runs/PR008_IMPLEMENTATION_RESULT_2026-10-04.json).
Actual GitHub run/head/merge evidence is also recorded in the PR description.

## Windows setup и продолжения

[Установка и запуск](../../desktop/README_RU.md). Shell staging copies only owned
files into a new version directory. Config chooses an already installed current
backend/runtime/profile; old source excerpts are not an installer.

Actual Dell Latitude 5400 / Windows 11 installation, Chrome-closed operator
actions, keyboard accessibility, peak memory/latency and Windows descendant
cleanup remain NOT_RUN on the user's device. Hosted Windows CI is code/runtime
evidence and cannot replace that device receipt.

Open followups: №9 TXT/large-source import with existing provenance/CAS; standalone
runtime installer; canonical task/write intents/reconciliation; installed-device
qualification; existing long-inventory Core followups; voice/Grok/updater and
parser/resolver expansion. ACTION5-02/03 and TAB4-01 remain partial at roadmap
level, even with this package implemented.

Primary references used for subprocess/threads/read-only connection behavior:
[Python subprocess](https://docs.python.org/3/library/subprocess.html),
[Tkinter threading model](https://docs.python.org/3/library/tkinter.html#threading-model),
[SQLite URI connections](https://docs.python.org/3/library/sqlite3.html#how-to-work-with-sqlite-uris).
