# PR-001: один запуск сканирует весь выбранный snapshot

**Репозиторий:** `BobIvans/scaling-chrome-extensions`. **Цель:** управляемый
проход всех scan pages с сохранением cursor, паузы и отмены. Код самого
web3-бота `studious-pancake` в этом PR используется только как возможный input.

Пакет готов к передаче coding-агенту. GitHub PR не создан, новый application
code не внедрён, runtime/device tests этого изменения ещё не запускались.
PR-001 — локальная последовательность этих пакетов, не upstream PR number.

## Почему это первое изменение

Входной master содержит V5, а не только V1/V3. Его
`strategy_v5/NEXT_IMPLEMENTATION_BRIEF_RU.txt` выбирает M5-02: полный repo
учёт по одному действию. Сохранённый `repo_context.py` уже умеет pinned tree,
SQLite cursor, pages и byte partitions; `RepoReviewSession.scan()` вызывает
ровно одну порцию. Первый прирост связывает эти primitives в controllable run.

V5 broad slice включает LAYA4-002/003/004/008/009/010. Вместе с новым graph,
streaming reader и export/recovery это больше одного часа. Поэтому здесь
закрываем отдельно проверяемую controller acceptance LAYA4-002 и owner
preflight LAYA4-001. Проекции counts/legacy gaps используют часть LAYA4-004;
полный format policy остаётся открытым. Windows criterion LAYA4-002 не закрывается
Linux tests. M5-02 и широкие feature cards остаются PARTIAL даже после этого PR.

## Сценарий и границы

| Действие | Наблюдаемый результат |
| --- | --- |
| Выбрать существующий operator repo alias | Проверен namespace/profile; UI не передаёт root или shell command |
| «Собрать весь repo» | START закрепляет snapshot/intent; STEP вызывает bounded page до terminal state |
| Pause | Текущее действие может завершиться; следующая page не начинается после committed pause |
| Закрыть UI и открыть снова | STATUS возвращает сохранённую identity/cursor; кнопка Continue доступна без auto-start |
| Continue | Возобновляет RUNNING для того же pinned snapshot с новой control revision |
| Stop | CANCELLED сохраняется; late reply не меняет control state и не создаёт новый pump |
| Изменить HEAD/profile | SOURCE_DRIFT/BLOCKED; старый ledger сохранён, commits не смешиваются |
| Завершить inventory processing | Полный ledger и проверенные INDEXED bytes; gaps видны отдельно |

UI кнопка в этом PR живёт в существующем library view. Controller и DTO должны
быть пригодны для будущего desktop клиента, но независимый desktop installer
и работа с закрытым Chrome относятся к M5-01. Закрытие этого UI прекращает
автоматические новые requests; run data сохраняется. Это resume, не daemon.

Вне PR: raw portable context ZIP, source-to-part batch index, unlimited Git
enumeration, oversize streaming, LFS download, JS/TS resolver, voice/Laya,
Grok send, updater, schedules/parallel workers, live trading. Все эти направления
сохранены в backlog и в очереди следующего ZIP.

## Baseline и существующие owners

Справочные source bytes извлечены из приложенного snapshot на
`da6abf4c006e4e7d26fe45ef30fa9d07a356f396`. Их hashes сверены с preserved entries.
Документ V4 сообщает local `5574ab768b39605d4631651a1e8f2451483344db` и 381
historical local tests; здесь это сохранённые claims, а не текущий прогон или
подтверждение GitHub main. V4 code files не материализованы как этот commit.

Первый шаг агента — записать actual HEAD, прочитать текущий AGENTS/CI, найти
действующие symbols. Если 5574ab7 отсутствует, отметить это evidence gap;
если актуальный main ушёл вперёд, переносить намерение на актуальные owners.
Архивные source файлы — reference-only; не overwriting patch.

| Owner / файл текущей baseline | Уже есть | Требуемый небольшой прирост |
| --- | --- | --- |
| `content-lab/repo_context.py` | `db_for`, `start_scan`, `scan_page`, `get_snapshot`, `verify_roundtrip_db` | Control metadata и atomic guarded page; reuse cursor/chunks |
| `content-lab/native_adapter.py` | `FIELDS`, `operator_profile`, `dispatch`; alias/profile validation | Strict action endpoint и compact DTO |
| `agent-bridge/durable.mjs` | `DURABLE_COMMANDS`, `fields`, limits и isolated subprocess | One new command в allowlist; прежние limits |
| `one-click-context/library/durable-ui.mjs` | COMMANDS, hello capability filter, request generation | Объявить support endpoint; refs только cache |
| `one-click-context/library/repo-review-ui.mjs` | `RepoReviewSession`, stale version guard, existing view | Sequential pump, control actions, restore STATUS |
| `one-click-context/library.html` | Repo scan buttons и status view | One start, Pause/Continue/Stop и доступный progress |
| `content-lab/test_repo_context.py` | Real Git/SQLite/native fixtures | Multi-page lifecycle, page replay, cancel/drift/compatibility |
| `one-click-context/tests/repo-review-ui.test.mjs` | UI→NativeClient→JobHost integration fixtures | Full controller roundtrip + late replies/control accessibility |
| `agent-bridge/durable.test.mjs` | Bridge/protocol tests | Strict fields и advertised command, если нужно |

`JobHost` уже маршрутизирует `durable.*` и берёт hello commands из
DURABLE_COMMANDS. Изменять его только если проверка текущей версии выявит gap.
`NativeClient` находится в `one-click-context/library/agent.mjs`; его текущую
реализацию проверить на checkout. Прежние Core jobs/task/review owners сохраняются.
Список candidate touched files — ориентир, а не приказ менять каждый файл.

## Данные и переходы

Предлагается additive `repo_scan_runs` либо эквивалентная существующая owner
таблица в **том же** `content.sqlite3`. Это control metadata над read-only scan,
не второй job executor. В ней только `run_id`, `intent_key`, namespace/alias,
snapshot_id, profile digest, state, control revision, timestamps и reason.
Не копировать authoritative cursor/total/entry counts: они читаются из snapshot.
Идемпотентность — unique `(namespace, alias, intent_key)` и stable run ID.
Смена profile не создаёт случайно новую запись для повторения старого intent.

| Current state | Action | Next state / effect |
| --- | --- | --- |
| Нет run | START(intentKey) | RUNNING с сохранённым snapshot; empty/finished snapshot может сразу COMPLETE |
| Любое сохранённое | повтор START с тем же intentKey | Тот же run_id; ни новый snapshot, ни page не создаются |
| RUNNING | STEP(expectedCursor, expectedRevision) | Не более одной page; COMPLETE только по proof, BLOCKED/FAILED по явной причине |
| RUNNING | PAUSE | PAUSED после committed transition; cursor/bytes сохраняются |
| PAUSED | CONTINUE с current revision | RUNNING; перед новым STEP повторная source/profile проверка |
| RUNNING после reconnect | Явное Continue | Backend state не меняется; проверенная revision позволяет client pump начать STEP |
| RUNNING/PAUSED | CANCEL | CANCELLED; data остаются для inspection |
| CANCELLED | STEP/CONTINUE | No mutation / terminal response; отменённый run не возрождается |
| BLOCKED/FAILED | STEP/CONTINUE | No mutation; новый run требует нового явного intent после устранения причины |
| COMPLETE | STEP/CONTINUE | No page; return stored/current complete status |

`run_revision` увеличивается только при control transition, а cursor — при
committed page. Replayed PAUSE/CANCEL должны быть идемпотентны, а stale CONTINUE
не снимает более новую паузу/отмену. Новое явное START с **новым** intent может
reuse snapshot/cursor; предыдущая CANCELLED запись остаётся терминальной.
Разрешён не более один RUNNING/PAUSED driver intent на тот же alias/profile;
второй START при active run возвращает ACTIVE_SCAN_EXISTS с run reference.

Native endpoint action/fields и example envelopes находятся в
`contracts/SCAN_RUN_CONTRACT.json` и `fixtures/API_REQUESTS.json`.
Это proposal нового API; до build его нет в установленном приложении.

## Atomic STEP и uncertain reply

1. Начать существующий SQLite write transaction (`BEGIN IMMEDIATE`).
2. Внутри него проверить namespace/alias/profile/run state/control revision,
   snapshot ledger integrity и expected cursor; только затем читать новую page.
3. Если stored cursor больше expected cursor, вернуть текущий run без обработки
   следующей page. Если stored cursor меньше expected cursor — CURSOR_AHEAD.
4. При равенстве выполнить существующие read/partition/insert operations в
   той же transaction; commit одновременно фиксирует page cursor и terminal
   control transition. Не открывать nested independent transaction из wrapper.
5. Ошибка до commit откатывает page. Lost response после commit не откатывает
   SQLite: STATUS восстанавливает фактический cursor.

Можно вынести внутреннюю page operation в `_scan_page_db` и вызвать из legacy
`scan_page` и guarded STEP. Это implementation suggestion; выбрать smallest
current-code diff, сохраняя legacy behaviour и transaction ownership.

STOP не обещает мгновенный interrupt Git/SQLite. Одна уже начавшаяся page может
commit до CANCEL. Из-за serial Native Host ответ control может ждать завершения
page. UI сразу запрещает новую page и показывает «Остановка ожидается»; persisted
CANCEL остаётся подтверждённым только после backend receipt. При lost control
reply — STATUS до дальнейшего действия. Max page/native timeout не увеличивать
ради непрерывного loop. Не передавать arbitrary timeout из UI.

У pump максимум один in-flight STEP. Перед каждым следующим request проверяются
client generation, selected repo, run identity и local stop/pause flag. Между
requests сделать event-loop yield. UI stale reply может обновлять только
проверенный run с соответствующей control revision; старая callback цепочка
не запускает новые requests. Не использовать один `busy=true` для disable STOP.
Disconnect всегда останавливает client pump. После reopen STATUS по alias
восстанавливает run; control data из браузерного cache не authoritative.

## Coverage и ограничения

| Поле | Значение в этом PR |
| --- | --- |
| `total` | Число entries pinned inventory, включая metadata/exclusions |
| `ledger_entries` | Число записей `repo_entries`; включает PENDING |
| `processed` | `total - pending`, только dispositions, уже вышедшие из PENDING |
| `cursor` | Committed ordinal position в прежнем snapshot |
| `indexed/excluded/errors/pending` | Projection существующих per-entry states |
| `inventory_complete` | cursor==total, complete ledger, pending==0 |
| `exact_for_indexed` | Existing roundtrip proof для INDEXED bytes |
| `all_tracked_bytes_exportable` | Independent old proof; false при gaps |
| `ai_delivery` | NOT_PERFORMED; scan не включает передачу/прочтение AI |

Existing INDEXED binary/non-UTF8 blobs имеют raw chunks, но могут не иметь text
items. Показывать parser/encoding warning, не превращать raw capture в text
coverage. LFS pointer может оставаться captured pointer с known format gap;
LFS payload qualification — следующий package. Link/submodule/unsupported-path
entries сохраняют existing metadata reason; targets не разыменовываются.

В этом PR сохраняются MAX_TREE=32 MiB, MAX_FILE=8 MiB, input=16,000 bytes,
output=192,000 bytes и existing timeout; сверить actual constants при preflight.
20 — page size, не cap total files. Limit error не создаёт COMPLETE run.
Не обещать bounded startup enumeration memory или поддержку всех path encodings:
их streaming qualification вынесена отдельно. Progress summary не содержит
full repo text и не растёт вместе со всем tree в одном native response.

## План focused session

| Минуты | Работа | Reviewable результат |
| --- | --- | --- |
| 0–5 | Actual base, owner/API/CI map, existing controller check | Pinned owner receipt и smallest diff scope |
| 5–20 | Additive control metadata + atomic guarded step | START/replay/control invariants в same SQLite |
| 20–30 | Native strict endpoint + hello/allowlists | Прежние clients остаются совместимыми |
| 30–45 | UI pump, progress, Pause/Continue/Stop, restore | Пользовательский multi-page loop работает |
| 45–55 | Focused fault + native/UI integration checks | Actual criterion evidence, не только mock assertions |
| 55–60 | Required gates, PR description, handoff | One coherent reviewable PR с outcome/remaining scope |

Это effort budget. Если actual owners/API требуют большого refactor, сохранить
scope этого PR и дать revised estimate. Не увеличивать scope desktop/export
ради заполнения часа. Проверки заканчиваются по критериям, не по minute counter.

## Проверки и definition of done

Подробные 12 acceptance cases — `plan/ACCEPTANCE_CASES.json`. Корпус из 45
реальных fixture files включён в `fixtures/repo/`, включая empty/binary/long UTF8
source. Он должен дать 3 page steps при size=20 и exact bytes roundtrip.
Git fixture создаётся во временной test области, не внутри пользовательского
repo. File count и SHA256 corpus доступны в `fixtures/TREE_EXPECTATIONS.json`.

Сохранённые базовые команды (уточнить по текущему CI):

```bash
python -B -m unittest discover -s content-lab -p 'test_repo_context.py' -v
node --test one-click-context/tests/repo-review-ui.test.mjs
node --test agent-bridge/durable.test.mjs
```

После focused cases выполнить обязательные repository checks для touched paths.
Сохранённые broad gates baseline:

```bash
python -B -m unittest discover -s content-lab -p 'test_*.py' -v
node --test agent-bridge/*.test.mjs
python -B -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py' -v
node --test one-click-context/tests/*.test.*
```

Готовность узкого PR: все 12 scoped cases verified, legacy compatibility
подтверждена, UI/native/SQLite roundtrip выполнен, нет silent stop-at-first-page,
duplicate page processing или resurrection cancelled intent. Base/head и
criterion receipts сохранены. Code review описывает actual implemented behaviour.
Windows keyboard/device performance требует отдельного receipt; пока его нет,
device_status=NOT_RUN. Широкая M5-02 сохраняет unmet export/graph/streaming gates.

При неполном результате перечислить criterion_id, outcome FAIL/UNKNOWN/NOT_RUN,
причину и smallest next fix. AI claim, old 381 tests или успешная проверка этого
ZIP не переводят runtime criterion в PASS.
