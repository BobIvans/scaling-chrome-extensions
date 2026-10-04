# PR-004: полный inventory через ограниченный поток

Проблема в архивном `repo_context.start_scan`: `git()` использует
`subprocess.run(... stdout=PIPE, stderr=PIPE)`, потом проверяет `MAX_TREE=32 MiB`.
`start_scan` дополнительно строит `entries=[]` для всего tree. Получается полное
накопление вывода до проверки, затем ещё один список. Новый opt-in CLI читает
tree по NUL records, пишет disk stage и публикует полный ledger атомарно.

## Контекст и граница результата

Canonical owner остаётся Content Lab `content.sqlite3`, где уже есть
`repo_snapshots`, `repo_entries`, `repo_chunks`, `repo_heads`. CLI запускается
пользователем и заканчивается после enumeration; это не новый background runtime.
Долгая операция не размещается внутри 10-second Native call. Новый путь
явно выбирается переданным `inventory_budget`; Native `start_scan` по умолчанию
остаётся на старом reader до квалификации отдельного Core job.

CLI может создать inventory из >32 MiB output. Затем existing
`durable.repo.scan(repository, snapshotId)` обрабатывает persisted pages.
Native request содержит только snapshotId, не stdout и не весь список файлов.
PR-001 controller можно использовать, только если actual implementation умеет
переиспользовать тот же snapshot; иначе использовать existing manual pages.
Не менять proposed PR-001 request schema незаметно. `get_snapshot.complete`
определяется existing cursor/count/PENDING/raw proof после capture; READY CLI
не выставляет cursor=total и не двигает repo_heads.

Второе ограничение найдено в `index_matches_head`: оно строит два полных sets
из `ls-tree` и `ls-files` с тем же 32 MiB reader. Эта функция используется
`verify_binding`, а не enumeration/capture pages. Её нужно stream/stage сравнить
в следующем отдельном срезе с точным raw-path/mode/OID/stage matching.
До него нельзя заявлять large-repo review binding или полную LAYA4-003 готовность.

## Данные и immutable identity

1. Валидировать actual operator profile, alias, namespace и store outside source
   existing функциями. Сохранять Git isolation env из archived `repo_context.git`:
   no inherited Git configuration, no replace objects, no lazy fetch, no shell.
   Не использовать `git status`, checkout/filter/import/source executable.
2. HEAD прочитать один раз. Tree: `rev-parse <pinned-head>^{tree}`. Exact command
   перечисления: `git -c core.fsmonitor=false -C ROOT ls-tree -r -z -l --full-tree HEAD`.
   Аргументы argv, HEAD pinned; никаких pathspec и filtering source_roots при inventory.
3. Snapshot ID = existing `automation_core.digest({'alias':alias,'profile':profile,
   'head':head,'tree':tree})`. JSON separators/defaults этой функции важны;
   новый canonical encoding изменил бы ID и разрушил совместимость.
4. Decode только ASCII metadata до первого TAB; всё после него — raw path bytes.
   Не `splitlines`, не текстовый subprocess, не нормализовать newlines/unicode.
   `-l` size decimal для blob, `-` для nonblob; missing blob size (`BAD`
   в квалифицированном Git) — existing ERROR/BLOB_SIZE_UNAVAILABLE metadata,
   а не dropped entry. Иные malformed size tokens — stream failure. OID width сверять с
   actual pinned object format (40/64); mode/kind pair валидировать.
5. Ordinary supported path проходит existing `source_path`. Unsupported raw
   bytes/path сохраняются existing `git-path-hex:<lowercase hex>` и EXCLUDED
   reason; placeholder обратим и не collides с supported path, где colon запрещён.
   Табличные/переносные имена — данные. Links/submodules, protected names,
   missing size и per-blob cap оставляют existing classification semantics.
   Формат/eligibility policy переносится отдельно в ZIP-005.

## Ограниченный reader

Предложение проекта, а не встроенная гарантия Python: два reader threads либо
portable equivalent с bounded queues. Stdout read не больше 64 KiB, queue ≤8
blocks; stderr дренировать независимо, хранить только bounded diagnostic tail.
Main loop берёт blocks с коротким timeout, проверяет monotonic deadline/cancel,
парсит incremental NUL records и вставляет ≤256 rows и ≤256 KiB normalized row data за batch.

Если queue full, reader применяет backpressure и всё ещё видит stop flag;
на failure main должен продолжить bounded drain/discard либо закрыть pipes
после stop child, чтобы не оставлять producer thread заблокированным.
Не вызывать `wait()` пока ребёнок может ждать заполненный pipe. Не использовать
полное `communicate()` как замену потока: оно накапливает output в memory.
All EOF markers и reader exceptions передаются явно, без игнорирования ошибок.

Per-record guard ≤65,536 bytes — resource safety limit, а не corpus limit.
Пустой промежуточный NUL record, malformed header, invalid oid/size или final
unterminated record — typed failure всего inventory. EOF — только delimiter
boundary, обе pipes drained, child reaped exit=0; успешная часть stream не успех.
Config limits см. `contracts/INVENTORY_BUDGET.example.json`; peak buffers bounded
независимо от total files. Deadline охватывает reader/stage и checks между
batches; перед publish проверить remaining budget. SQLite busy waits/interrupt
также bound, иначе дедлайн оказался бы только Git timeout.

## Stage и atomic publish

Создай private uniquely named temp directory под operator store вне repo.
Stage — disposable SQLite DB; authoritative metadata туда не переносится.
Установи bounded cache (например 2 MiB), temp_store=FILE, journal_mode=DELETE,
page quota из budget. Учитывай все stage files и main journal/WAL reserve.
Disk-full либо quota failure заканчивается typed failure; snapshot не появляется.
Строки stage: ordinal PK, path UNIQUE, mode/kind/oid/size/state/reason,
raw_path BLOB для integrity check; main projection использует current columns.

Проверь count=N, min ordinal=0/max=N-1 (отдельно N=0), unique path и exact
content/metadata stream digest. Большой `fetchall`, whole Python list/set или
глобальный JSON response здесь запрещены. Обход и INSERT SELECT streaming.

После успешного EOF child полностью остановлен/reaped. Перепроверь HEAD pinned
и scope. `ATTACH` private stage до `BEGIN IMMEDIATE`; transaction сначала
повторяет scoped existing-id check. Если valid snapshot уже опубликован —
reuse; проверять entries count/ordinal integrity. Не менять captured состояния
существующего snapshot. Если он неполный — CONTEXT_INCOMPLETE, не чинить молча.

В новой ветке вставь snapshot cursor=0,total=N и все stage entries с exact
ordinal в existing tables. Простые INSERT; duplicate failure откатывает всё.
Проверь counts внутри transaction. Не update repo_heads/sync_heads/repo_chunks.
Commit публикует обе authoritative tables вместе. Readers видят either старое
состояние, либо весь новый inventory. ATTACH не переносит authority stage DB;
target всё время existing content.sqlite3. После commit — detach/remove stage.
При crash target transaction rollback выполняет SQLite; незавершённый stage
не является published snapshot. Следующий запуск начинает tree stream с нуля.

## Recovery и lifecycle

Timeout/stderr overflow/cancel/parser error/nonzero child: stop child group
по supported platform, drain bounded, wait/reap, join reader threads, только
затем delete stage и return FAILED/CANCELLED receipt. Cleanup deadline 5 seconds.
Если остановка не подтверждена — PROCESS_STOP_UNCONFIRMED, stage сохранить как
unpublished и запретить restart того же процесса, пока оператор не проверил
процесс через existing recovery procedure. Не убивать arbitrary old PID:
он мог быть переиспользован. Orphan cleanup требует known run ownership и
confirmed old process stop. Windows process cleanup проверяется отдельно;
Linux-only результат не считать installed Windows evidence.

Предыдущий COMPLETE snapshot сохраняется при любой ошибке. HEAD drift до
publish = SOURCE_DRIFT без new snapshot. HEAD может измениться сразу после
check — immutable tree всё ещё exact, existing scan_page дополнительно
проверяет HEAD. Не утверждать, что future working tree навсегда pinned.

Повторный CLI с тем же profile/HEAD reuse только valid existing identity.
Новый profile/HEAD = другая identity, не overwrite old snapshot. Два concurrent
CLI stages разрешены только в рамках existing single-writer policy: publish
сериализует transaction и duplicate handling. Нет отдельной task queue.
Interrupted enumeration не byte-resumable. Повторное чтение Git с начала —
осознанно; это не PR-003 resume проверенных payload parts/ZIP сборки.

## Ресурсы и проверки

`tools/make_large_git_fixture.py` создаёт отдельный synthetic Git repo:
160,000 tree entries с одним blob и длинными именами, без worktree checkout.
Reproducible ls-tree output >32 MiB. Не нужно включать huge dataset в ZIP.
`fixtures/stream_golden/` — небольшая смесь 55 metadata records, tail после
20/39, tab/newline/nonUTF8, empty-size blob, symlink, gitlink и oversize blob.
Oracle проверяет fixture/parser semantics; это не реализация SCE reader.

В actual repo добавь tests из 16 acceptance cases. Cold/warm измерения:
40,000 и 160,000 files; отдельно stdout bytes, stage disk peak, application
RSS peak, Git child RSS, timeout, duration, preserved tail/ordinals. Memory
growth оценивай на том же устройстве; proposed application peak ≤64 MiB и
growth ≤16 MiB при 4x corpus — критерии квалификации, не наблюдённые числа.
Если измерения недоступны, write NOT_RUN и не удаляй legacy limit.

Required regression checks после focused tests в actual checkout:
`python -B -m unittest discover -s content-lab -p 'test_*.py' -v`
`node --test agent-bridge/*.test.mjs`
Plus actual AGENTS-required checks. New code touches Python owner только;
JS/UI tests расширять при actual changes или обнаруженной regression.
Это package build не запускал application runtime tests и не наблюдал CI/merge.

## Review scope

Ожидаемые touches: new `content-lab/repo_inventory.py`, bounded opt-in hunk
в `repo_context.start_scan`, focused `test_repo_inventory.py`, documentation.
Native adapter/bridge/PR-003 exporter logic не переписывать. Сверить sibling
module imports на current main и изменения параллельного чата.
Minimum hour slice считается готовым только с CLI streaming+atomic publication
и собственными доказательствами; если не успел, покажи actual failing evidence.
Все оставшиеся LAYA4-003 критерии и broad roadmap остаются в backlog.
