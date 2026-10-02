# OCC-CONTEXT-FOUNDATION-01

Первый vertical slice: настроенный Git repo → полный инвентарь HEAD → выбор
source/finding → запрос AI → импорт review → состояние и следующий запрос.
Baseline: `23d14fa351e56c89b916c6853f955d562335e8f1`. Приватный входной ZIP,
goals и chats в Git не включены.

## Владельцы и scope

| Часть | Владелец | Результат |
| --- | --- | --- |
| Git inventory/cursor/versions/bytes | `content-lab/repo_context.py` | Tables в existing `content.sqlite3` |
| AST/chunks/imports/SCC | `content-lab/repo_source.py` | Static parsing; scanned code не импортируется |
| Immutable review ledger | `content-lab/context_review.py` | Existing create/import/list/get + отдельный Git binding |
| Operator scope и transport | `native_adapter.py`, `agent-bridge/durable.mjs` | Paths выбирает профиль; bounded native messages |
| Repo/review UI | `library/repo-review-ui.mjs`, existing durable view | Files/findings, coverage, import и next request |
| CI | `deterministic-core.yml` | Exact event head, Ubuntu/Windows, main push и docs paths |

Milestone: OCC-CONTEXT-01/02, OCC-REVIEW-01, source-binding часть
OCC-EVIDENCE-01 и CI часть OCC-OPS-01. Criterion evidence verifier, task compiler,
registered offline audit job, voice→queue и installed browser execution остаются
следующими изменениями. Existing Core queue/leases/cancel/reconciliation,
recorder и normalizer сохранены. Studious CTX-FIX-01 относится к другому repo.
Draft PR #7/#25–32 не являются завершением этих следующих этапов.

## Настройка и UI

Установите existing host по `agent-bridge/README_RU.md`. Добавьте необязательное
`repositories` в operator profile: пример `content-lab/native-profile.example.json`.
Старые профили работают. Alias задаёт absolute root, namespace, source_roots и
exclusions; namespace должен быть разрешён профилем, store находится вне repo.
Документ AI эти настройки не устанавливает.

В библиотеке: подключить host → получить repos → выбрать alias → начать/продолжить
scan до COMPLETE → выбрать файл/finding → задать goal, scope, acceptance → export.
Один запрос обрабатывает 20 entries. Новый процесс продолжает SQLite cursor того
же HEAD/profile. Для нового SHA выбрать текущий HEAD; SOURCE_DRIFT не требует
отката main. UI листает весь ledger, включая exclusions/errors, а не первые 2000.

Git CRLF conversion может дать DIRTY при равном HEAD: сравниваются фактические
байты. Используйте checkout с `core.autocrlf=false`, а не ослабление проверки.
Offline smoke использует тот же adapter, без установленного Chrome:

```bash
python -I -X utf8 content-lab/native_adapter.py --profile /absolute/native-profile.json < request.json
```

```json
{"type":"durable.repo.scan","repository":"sce"}
```

Scan с `snapshotId` продолжает pinned cursor; без ID выбирает текущий HEAD.
`durable.repo.get`: repository, snapshotId, offset; 20 entries на страницу.

## Полнота, bytes и dependencies

NUL-delimited `git ls-tree` exact SHA сохраняется целиком до processing. Blobs
читаются по immutable OID; Git code, filters, hooks и shell не запускаются.
Lazy fetch из promisor remote отключён через `GIT_NO_LAZY_FETCH=1`
([Git contract](https://git-scm.com/docs/git/2.53.0.html)); missing objects имеют ERROR.
Cursor/chunks/порция коммитятся вместе; interruption откатывает порцию.
Enumeration limit — 32 MiB Git output с явной ошибкой, не усечением. Blob limit
8 MiB: oversize имеет ERROR. Empty files тоже получают partition.

Link/submodule, unsupported path, operator exclusion, credential filename и
secret-text heuristic имеют явные причины. `wallet_logic.py`/`session_model.py`
не теряются из-за подстроки. Heuristic не гарантирует нахождение всех secrets;
оператор проверяет pack. Untracked/ignored и index-only additions не входят в
HEAD blobs; отдельный GIT_INDEX binding выявляет staged drift.

Chunks покрывают каждый INDEXED blob byte-for-byte: BOM, CRLF, binary и длинные
строки. UTF-8 code points не режутся внутри символа. Logical ID:
alias/path/section/occurrence/fragment; revision отдельно включает file hash,
fragment hash и offsets. Вставка другого файла не перенумеровывает IDs. Rename
получает новый path identity и инвалидирует прежние heads.

Completion публикует только Git heads выбранного alias. Delta показывает
add/edit/delete/rename и affected dependents; previous entries/versions сохраняются.
Rename — inference по единственному совпадению OID/mode, не запись команды git mv.
Большие delta lists имеют counts/display_truncated. `inventory_complete` требует
cursor и все expected rows; roundtrip проверяет offsets/revisions/size/SHA.
Exclusions/errors учитываются, но не объявляются indexed byte coverage.
Corrupt/missing ledger/chunks блокируют export. Canonical item text сверяется
с raw source bytes. Это один store/FTS, не вторая библиотека.

Python roots: `.`, `content-lab`, `agent-bridge`. Relative/package imports —
static; несколько owners → AMBIGUOUS. External/dynamic/JS dependencies unresolved.
SCC — iterative DFS с finish order; regression сверяет все 4096 четырёхузловых
графов с independent reachability oracle. Visited set ограничивает closure при
циклах. Relevant tests предлагаются отдельно по имени и не считаются reviewed.
JS — TEXT_ONLY, syntax coverage не заявляется. Tree-sitter/tiktoken не добавлены;
optional dependencies потребуют ADR, pins, offline/cache и packaging решения.

## Export, review и актуальность

`durable.repo.export` использует existing review owner. Документ содержит goal,
accepted scope, acceptance, SHA, sources, dependency closure, relevant tests,
coverage, omitted fragments и review-result template. Pack: до 10 text chunks /
24 000 byte planning budget; complete document ≤80 000 bytes. Token count не
выдаётся за exact: UTF-8 length — conservative bound для byte-based tokenizers,
намного меньше 300k. Export SHA относится к sorted JSON до форматирования UI.
Binary bytes сохранены для roundtrip; в AI text pack они явно omitted.

Native весь request с envelope ≤16 000 UTF-8 bytes. UI preflight учитывает envelope
и duplicate JSON keys. Большой review можно импортировать existing CLI ≤128 000:

```bash
python content-lab/context_review.py --store /absolute/store --namespace code import --file review.json
```

Sessions/results переживают restart. Import идемпотентен; старый replay не
откатывает новый result head. `durable.review.get` с `includeContent=true`
показывает criteria/coverage/next request; summary не раскрывает goal/finding text.
Source/review рендерится через textContent/textarea. Поздний ответ прежнего
repo/selection/disconnected host отбрасывается.

Client baseRepoSha у generic review — UNBOUND metadata. Repo SHA берётся из
snapshot; каждый read отдельно проверяет HEAD, index и actual bytes выбранных
файлов и dependencies. Missing → NEEDS_CONTEXT; изменение → STALE. Удаление/
изменение native profile прекращает чтение прежнего root. Известные export gaps
не исчезают после optimistic coverage модели.

DONE/model claim или supplied TEST_RECEIPT hash не закрывает finding:
closed=false, evidence_verified=false. Repo bytes binding не доказывает конкретный
fix criterion. Next: rescan/export для stale/missing либо независимая criterion
проверка; approvals/timers/action authority не восстанавливаются.

## Проверки и next step

Regression: 2005-file restart/tail, interruption rollback, exact bytes, source
not executed, exclusions/oversize, corruption/completeness, AST/imports/SCC,
IDs, dependency/HEAD/index drift, rename/delete/addition, revoked profile,
missing promisor blob без lazy network fetch, import replay, transport и production
DOM wiring. NativeClient → real JobHost →
isolated Python → SQLite проверяется с restart. Реальный baseline отдельно:
**137/137 tracked entries INDEXED, 137 byte-exact roundtrips**.

```bash
python -B -m unittest discover -s content-lab -p 'test_*.py' -v
node --test agent-bridge/*.test.mjs
python -B -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py' -v
node --test one-click-context/tests/*.test.*
```

Local platform: Linux, Python 3.11+, Node. CI: Ubuntu/Windows, Python 3.13/Node24,
exact event head. Installed Windows Chrome/native host receipt: **NOT RUN**.
Chromium binary здесь отсутствует; DOM fixtures не называются browser qualification.
Оператор выполняет первый полный UI сценарий на ПК и сохраняет device receipt;
local ASR на Dell также требует отдельного замера.

Next: trusted criterion evidence → registered audit template в existing Core →
typed document/voice preview → installed Windows outcome receipt. Cloud backend,
generic shell runner, provider calls и trading этим milestone не включены.
