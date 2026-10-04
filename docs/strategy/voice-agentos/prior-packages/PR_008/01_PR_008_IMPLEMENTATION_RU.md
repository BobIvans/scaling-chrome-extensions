# PR-008: desktop-клиент к существующему Native owner

**Scope:** минимальное локальное окно на Windows 11 для подключения, поиска и
выгрузки выбранного контекста без Chrome. Это transport/install spike из очереди
№7 и `ACTION5-01/02/03, TAB4-01`. Ориентир — час focused build; actual проверки
определяют завершение. Новый код этим design ZIP ещё не внедрён.

## Конкретный результат

Пользователь открывает launcher, выбирает уже установленный backend/profile,
видит путь данных и версию, ищет источник, выбирает результаты и сохраняет
TASK_DRAFT.txt с целью/областью/критериями и exact selected context binding.
Окно работает при закрытом Chrome. Desktop использует один existing store и
тот же Native dispatcher. Local draft не создаёт canonical task/review/job.

Это частичный срез. Исходный ACTION5-02 требует ещё import TXT и полноценного
installed-device receipt; ACTION5-03 — write intent/reconciliation. Эти criteria
сохранены открытыми. Windows receipt здесь NOT_RUN. Native/Core long scan из
№4, полный archive №3, grouping №6 и JS analysis №7 не переименованы готовыми.

## Основание и выбор host

Прочитаны ZIP №5/6/7. Source reference SHA:
`da6abf4c006e4e7d26fe45ef30fa9d07a356f396`. Historical V4 `5574ab7` известен по
status, current main/PR head не наблюдались. В master уже есть Tkinter prototype
`context_studio_v2/app.py`, но его snapshot/pipeline/vendor backend отдельный:
переиспользовать widget patterns, не переносить competing store.

Предлагается Tkinter + stdio для первого measurement slice: существующий Python
backend не требует ещё одной network bridge или browser rendering runtime.
Tk доступность и версии проверяются preflight; это рекомендация для эксперимента,
не финальное закрытие DEC5-01. Большой desktop shell и self-contained installer
выбираются после receipt. Primary docs находятся в docs/PRIMARY_REFERENCES_RU.md.

## Existing operations и candidate touched paths

| Path / existing owner | Минимальная правка |
| --- | --- |
| content-lab/native_adapter.py | durable.info; opt-in desktop output dialect; common loaded-profile dispatch |
| agent-bridge/durable.mjs | Advertise durable.info for existing browser when supported; legacy wire retained |
| desktop/client.py (candidate) | One child/request, strict input/output, budgets, generation fence |
| desktop/app.py (candidate) | Tk main-thread state and controls; worker queue for IPC |
| desktop/preflight.py, desktop/Launch_Windows.ps1 | Config/runtime/Tk/backend checks and diagnostics |
| Existing native/unit + new focused client tests | Scope, fault framing, identity, browser regression |
| Desktop docs/config/package manifest | First-run, source hash, owned shell files, preserved data |

Сначала найти actual equivalents. Public owner matrix в
`docs/OWNER_OPERATION_MAP_RU.md`. Corpus remains existing content.sqlite3;
Core remains job owner. Desktop не читает SQLite напрямую и не создаёт worker.
UI/config/draft files не являются вторым source/task journal.

## IPC: один процесс на запрос

Native adapter уже читает bare JSON до EOF через stdin и выдаёт JSON reply.
Direct desktop route не использует Chrome four-byte framing. Trusted startup
configuration определяет absolute Python/adapter/profile paths. UI requests
не содержат executable, argv, SQL, store path или policy. Installed siblings
используют тот же import layout; scanned repository modules не импортируются.

Фиксированный argv: `[python, -I, -X, utf8, adapter, --profile, profile,
--desktop-stdio]`, shell=False, windowsHide/CREATE_NO_WINDOW где доступно.
Environment ограничен необходимыми platform keys + UTF8; output encoding UTF8
strict. One request writes bounded JSON then closes stdin. stdout and stderr
drain concurrently with shared budget, чтобы stderr pipe не блокировал child.
Не применять unbounded communicate/whole-output accumulation; retained stderr
diagnostic ограничен и не выводит source text/profile contents.

Reference limits: input 16,000 bytes, output+stderr 192,000 bytes, timeout 10,000
ms, one inflight read. Handshake сообщает actual budgets; выбирается минимум
advertised и qualified client budgets. Пер-request бюджет не является лимитом
числа repository files/parts. Unknown/unsupported long operations disabled.

On timeout/close stop and reap only this adapter child, close/drain pipes with
bounded cleanup. No UI callback после generation change. No worker is launched
by these read commands. Windows process cleanup must be measured separately;
fixture timeout does not prove installed Windows orphan handling.

## Handshake, профиль и совместимость

Proposed durable.info uses existing trusted operator_profile validation but
returns before Core creation/DB initialization. It reports protocol version,
actual command capability list, native limits, namespaces, data-root identity,
profile digest and installed adapter SHA. Bundle digest may be UNKNOWN if no
verified installed manifest exists; module hash alone is not full build proof.
No credentials, templates/job payloads or raw profile contents in handshake.

With --desktop-stdio the success/error wrapper includes `adapter_context`
derived from the same loaded profile/policy used for this request. Refactor
common dispatch once; browser wrapper and public dispatch function stay compatible.
Do not hash one profile read and then dispatch using a second read: a changed
profile could bind a different store. Browser and desktop result DTOs come from
the same command owner; compare their selected payloads in integration tests.

The desktop mode rejects write/job-control commands before their owner executes.
Initial allowlist: durable.info, durable.repo.list, durable.search, durable.context.
Optional durable.repo.coverage/manifest readers only after actual handshake and
schema qualification; no hardcoded advertisement of №2/5/6/7 implementations.
Require an existing configured data store for data reads; absent backend/store
is SETUP_REQUIRED, no silent new empty library or schema migration by desktop.
Owner's idempotent initialization is tested against a ready store; no new
corpus mutation or migrations are introduced by this PR.

Legacy browser requests keep their current schema/DTO/argv. Old backend without
desktop mode/handshake reports PROTOCOL_UNAVAILABLE and leaves controls disabled
with an accessible update/setup instruction. Do not auto-copy older backend
source from this ZIP over the installed one. Handshake capability != installed
qualification, and build UNKNOWN cannot become verified from UI success.

## Reply identity and UI lifecycle

Client stores connection generation, requestId, expected operation, namespace,
query revision and handshake profile/store/adapter identity for each child.
Success is applied only if all still match the current UI and wrapper context.
Malformed JSON, duplicate keys, NaN, invalid UTF8, unknown fields, wrong operation,
protocol or profile identity yield typed error. Error wrappers may have null
adapter_context when setup failed before profile load; they never enable UI.

Tk owns all widgets on its main thread. Worker threads/process I/O put events
in a bounded queue; `after` drains updates. No Tk call from worker. Search
change/namespace change/reconnect/close increments generation/query fence.
One inflight read; buttons/keyboard stay usable and Cancel stops the child.
Retry reads starts a fresh request after handshake as needed. Future writes
require persisted keys and UNKNOWN reconciliation at existing task owner;
this read-only client does not claim ACTION5-03 write criteria passed.

## Search, selected context и draft

Current durable.search returns top matches with limit<=20 and no continuation.
Label TOP_MATCHES_BOUNDED, not complete corpus/query. No fake Next cursor. Repo
metadata pagination, when supported, follows real continuation to EOF; new UI
must not limit total files at 20. Current durable.context accepts 1..10 selected
IDs/maxBytes<=48,000. These are existing packet limits, not full-repo scope.
Large full source exports continue to use №2/3 owner; do not lift packet limits
by unbounded IPC or manufacture text eligibility in desktop.

Context SHA is existing automation_core.digest(items), whose encoding uses
ensure_ascii=False/sort_keys/default separators. It differs from output-file
SHA. Validate actual owner algorithm; preserve source IDs/revisions/hashes and
authority. Fixture exact text includes Russian/EN/BOM/CRLF cases as data.
Source eligibility policy from actual №5 remains backend-owned; missing facts
or stale ID returns explicit prerequisite/blocker. A UI does not override it.

Export selected context + goal/scope/acceptance into local UTF8 TASK_DRAFT.txt,
with metadata JSON and file hash. Stage in selected output parent, verify, then
publish atomically. Existing output conflict explicit; preserve earlier output.
Scope=SELECTED_ITEMS, canonical_task_id=null, corpus_total=UNKNOWN. No status
sent/read/used/merged is inferred. Disk full leaves recoverable draft failure;
backend corpus untouched. Filename/output folder chosen by operator; source
path/title is a label, never an executable command or automatic output path.

## Windows packaging gate и измерения

This pilot deploys shell/launcher/config beside an already installed compatible
backend/runtime. Existing browser Install.ps1 requires extension ID, Node,
Codex and C# compilation; direct desktop launcher does not reuse that route.
Preflight checks configured runtime, Tk, installed adapter/profile and backend
hash/capabilities, shows actual data path/version, and launches without Chrome.
No auto downloads, PATH mutation or registry registration in this slice.

Config/owned-file manifest and uninstall behavior are in Windows contract.
Use paths with spaces and Unicode in tests; repeat launch same store identity.
Close/uninstall shell preserves external backend/profile/corpus. Full standalone
runtime bundle and code signing/update remain separate receipt-driven tasks.

18 acceptance cases have independent expected fixtures. Packaging QA validates
this design; app/native/client/unit and Windows device receipts remain future.
Run repository-required checks on actual head and fill implementation receipt.
