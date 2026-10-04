# PR-002: полный manifest и двусторонний индекс диапазонов

**Target:** `BobIvans/scaling-chrome-extensions`. **Scope:** metadata projections
всех entries/chunks из существующего COMPLETE snapshot, их validation и bounded
native browsing. Оценка — примерно час focused build; проверки определяют done.
Пакет подготовлен; нового integrated code/PR/CI этой итерацией не создано.

## Пользовательский прирост

После scan видно, какие файлы учтены, какие chunks принадлежат каждому исходнику,
где находятся gaps и как перейти от части к исходнику. Полный source inventory
и ограниченная порция для AI больше не используют один показатель полноты.
Для Studious это даёт проверяемый code context для следующего research brief,
без исполнения ботом функций или транзакций.

| Input | Output | Проверяемое свойство |
| --- | --- | --- |
| COMPLETE pinned snapshot | `REPO_MANIFEST.jsonl` | Одна строка на каждый `repo_entries` ordinal, включая gaps |
| Existing INDEXED `repo_chunks` | `PARTS_INDEX.jsonl` | Один record на raw chunk, exact source byte ranges и content hash |
| Identity + counts + output hashes | `BATCH.json` | Deterministic scope/binding, local coverage, policy versions |
| Streaming validation | `VALIDATION.json` | Exact reconstruction для всех INDEXED sources; gaps не становятся captured |
| INFO/ENTRIES/PARTS API | UI summary и paged browsing | Нет tail omission, row/byte cap относится только к одной page |

Native INFO/pages не создают файл на произвольном UI-supplied path. Writer CLI
получает output path от оператора отдельно и использует тот же source owner.
Full portable ZIP и payload files ещё не выдаются; это следующий PR-003.

## Предусловие и зависимость от PR-001

Нужен фактически complete snapshot: cursor==total, ledger count==total и
PENDING==0. Corrupt chunk bytes/ranges/revision блокируют verified projection.
Автоматический scan controller из ZIP-001 полезен, но факт подготовки его
архива не является merged prerequisite. Можно использовать COMPLETE snapshot,
полученный прежними manual `durable.repo.scan` pages. Не выполнять scan скрыто
из manifest API и не дописывать controller в этот diff.

Исходная LAYA4-009 зависит от LAYA4-002/004/008. Мы берём отдельный raw-index
срез: current dispositions читаются без нового format policy, groups/graphs не
генерируются. Поэтому частичная реализация не закрывает всю LAYA4-009/M5-02.

## Owners и candidate touched files

Сохранённый source snapshot: `da6abf4c006e4e7d26fe45ef30fa9d07a356f396`.
Reference local V4 `5574ab768b39605d4631651a1e8f2451483344db` документирован
исторически; source этого commit и actual main не проверены этим пакетом.
Coding-агент сначала фиксирует actual base и действующие API/CI/AGENTS.

| Файл / owner | Существующее основание | Минимальное изменение |
| --- | --- | --- |
| `content-lab/repo_context.py` | Snapshot/entry/chunk tables, `load_snapshot`, byte proof | Reuse authorization/schema; consistent manifest projection helpers |
| `content-lab/repo_manifest.py` (предлагаемый sibling) | Same SQLite owner, no second store | Pure iterators, streaming writer/validator, CLI; если аналог уже есть, расширить его |
| `content-lab/native_adapter.py` | Strict `FIELDS`, operator repo profile | INFO/ENTRIES/PARTS endpoint и scoped compact response |
| `agent-bridge/durable.mjs` | Command allowlists, isolated adapter, limits | Manifest command в hello/fields |
| `one-click-context/library/durable-ui.mjs` | Capability negotiation/request generation | Advertise supported manifest command |
| `one-click-context/library/repo-review-ui.mjs` | Paged snapshot view и stale reply guard | Manifest state, query binding и cross-navigation |
| `one-click-context/library.html` | Existing repo controls | Small manifest view/button, не новый desktop shell |
| `content-lab/test_repo_context.py` / new focused test | Real Git/SQLite/native fixtures | Count/range/identity/proof/migration cases |
| Existing bridge/UI tests | Native roundtrip and page fixtures | Strict fields, serialized byte cap, stale navigation |

`JobHost` уже routes `durable.*` и advertises `DURABLE_COMMANDS`; не менять
его без наблюдаемого gap. Existing review/task/Core states и selected export
остаются у своих owners. Projection files — производные metadata, не новый ledger.

## Детерминированный формат

`REPO_MANIFEST.jsonl` идёт по existing entry ordinal. Для INDEXED row указывает
file SHA, byte size, parser kind, chunk_count и locator `{file_ordinal}`.
Не помещать тысячи part IDs в одну строку. Для EXCLUDED/ERROR row сохранять
original mode/OID/size/reason, доступный hash либо null. Нет fabricated hashes.

`PARTS_INDEX.jsonl` ordered by file ordinal, chunk ordinal. Поля: snapshot_id,
file_ordinal/path, chunk_ordinal, logical_id, revision, part_id=revision,
source_start/source_end (half-open byte interval), byte count, part SHA256,
file SHA256, text eligibility и declared dependency status. Existing revision
проверяется формулой `automation_core.digest([logical_id, file_hash, sha(raw),
byte_start, byte_end])`; это не только hash content. Null item_id показывает
raw-only chunk; presence text item требует отдельной text integrity проверки,
если данный путь заявляется text-exportable.

Empty source сохраняет один chunk `[0,0)` с SHA256 пустых bytes. Nonempty
chunks имеют положительную длину; ranges contiguous/nonoverlapping и заканчиваются
на file size. UTF8 offsets считаются по bytes, даже на многоязычной long line.
Reversible unsupported-path metadata из existing ledger сохраняется как data;
UI renders `textContent`, а не HTML. Link/submodule targets не обходятся.

JSONL: UTF8, compact sorted keys, `allow_nan=False`, одна LF после каждой записи;
JSON escapes сохраняют tabs/newlines/quotes в именах. Existing identity/revision
digest использует **фактический** `automation_core.digest`, чьи JSON separators
в reference source отличаются от compact JSONL. Не менять revision algorithm
из-за другого file serialization. Sample identities в fixture синтетические.

## Batch identity и proof scopes

`BATCH.json` связывает snapshot_id, namespace/alias, repo/tree SHA, profile digest,
manifest contract/export policy, goal_revision, grouping policy и parser-policy
scope. В raw whole-repo slice goal_revision=null, groups=`RAW_CHUNK_MAPPING_V1`,
graph dependencies=`NOT_GENERATED`; new parsing не выполняется. Parser kind
переносится из analysis, а historical scanner build version может быть UNKNOWN.
Эти значения явно входят в binding; не использовать fake goal/build revision.

`batch_id=automation_core.digest(binding)` служит identity. Exact serialized
output SHA каждого JSONL хранится отдельно в output records BATCH. Пока full
streaming validation не завершилась, global validation=NOT_RUN/UNVERIFIED.
После успешного writer run `VALIDATION.json` даёт proof counts/hashes и scoped
PASS. Native PARTS page может проверить только возвращённые chunk rows, а не
остальной corpus. `index_complete`, `raw_exact_for_indexed`, `text_exportable`,
`all_tracked_bytes_exportable` и `ai_packet_included` — разные показатели.

Complete inventory с errors/exclusions разрешено показать как accounted,
но `all_tracked_bytes_exportable=false`. AI delivery/acknowledged/read/used
остаются NOT_PERFORMED/UNKNOWN. Граф связей не заменять пустым resolved array.

## Streaming projection и запись

Открыть один SQLite read view и использовать ordered cursor/`fetchmany`, не
fetchall raw blobs всего repo. Для каждого INDEXED file incremental SHA256
reconstruction проверяет его chunks/ranges/revision и Git blob OID (hash `blob <size>\0` + captured bytes,
по object format из длины stored OID); hash raw chunk сравнить
с serialized PARTS_INDEX row. SQLite view должна быть одна для counters,
entries и chunks. Profile/alias/namespace checks выполняются по trusted
operator profile как в existing native adapter.

Writer читает **captured** bytes в store, не working-tree. Изменившийся HEAD
не переписывает старый pinned batch: явно выбранный historical snapshot можно
просмотреть при действующем profile scope. Current HEAD freshness не выводится
из captured-byte proof. Unrelated writes не должны смешивать read views.

CLI proposal:

```bash
python -B content-lab/repo_manifest.py --profile /absolute/native-profile.json --repository sce --snapshot <64-hex-snapshot> --output /absolute/output-directory
```

Пример требует заменённых real profile/snapshot/output, handler ещё предстоит
реализовать. UI не получает возможность выбирать arbitrary filesystem root.
Output находится вне source repo; trusted CLI staging под output parent содержит
две JSONL и validation. После PASS написать BATCH последним и атомарно опубликовать
весь каталог. Нет SUCCESS artifact при disk-full/interrupt/hash mismatch.
Повтор на том же binding сравнивает existing output hashes, не перезаписывает
повреждённый каталог как valid. Basic publication здесь, полноценные checkpoints,
part payload bytes и ZIP recovery — PR-003.

## Bounded metadata API

Предлагаемый новый `durable.repo.manifest` принимает repository alias,
snapshotId и action INFO/ENTRIES/PARTS. ENTRIES/PARTS имеют offset/limit;
PARTS может иметь fileOrdinal, который меняет query scope. `nextOffset=null`
только после конца выбранного result set. При byte budget заполнении остановить
page до следующей row и вернуть continuation, не потерять row. Если даже одна
row не помещается — ROW_ENVELOPE_LIMIT, а не silent omission.

Response содержит batch binding, scope/filter, returned rows, total и nextOffset.
Native frame JSON с request wrapper обязан уложиться в 32,768 bytes этого
contract budget и actual 192,000-byte adapter limit; input 16,000 и timeout
сверяются с actual code. Row cap 20 — только одна page, не cap corpus/parts.
Полный verification не запускать повторно на каждую page: INFO сообщает
NOT_RUN для global proof, CLI/registered trusted verification отдельно.

PARTS с fileOrdinal даёт source→parts. Part row даёт part→source по точной
snapshot/file ordinal; existing `repo.get` может открыть page исходников.
UI query version включает repo/snapshot/action/file filter; late reply другого
scope не заменяет новую page. Raw bytes/new dependencies через этот endpoint
не выдаются; для payload export применяется отдельный PR-003 contract.

## План и проверки

| Минуты | Изменение | Done output |
| --- | --- | --- |
| 0–5 | Actual owner/precondition map | COMPLETE snapshot contract и smallest current-code diff |
| 5–20 | Entry/part iterators и streaming byte proof | Exact normalized ranges/IDs, original gaps |
| 20–30 | Metadata writer и basic atomic publication | Four artifacts с verified output hashes |
| 30–40 | Strict native pages и negotiation | Bounded rows/bytes, source-filter continuation |
| 40–50 | Small UI navigation + focused tests | Full entry/part tails, stale-query guard |
| 50–60 | Fault cases / required gates / handoff | Actual evidence и coherent PR description |

14 scoped cases находятся в `plan/ACCEPTANCE_CASES.json`. Golden corpus содержит
50 entries/46 INDEXED/4 gaps; один source имеет >20 parts. Packaged fixture
validator проверяет golden data и negative mutations; он не тестирует будущий
repo_manifest/native handler. Actual implementation tests должны включать
реальные SQLite и native subprocess roundtrip, исходные DB records и legacy APIs.

Прежние baseline команды для actual checkout (проверить CI):

```bash
python -B -m unittest discover -s content-lab -p 'test_repo_context.py' -v
python -B -m unittest discover -s content-lab -p 'test_repo_manifest.py' -v
node --test agent-bridge/durable.test.mjs
node --test one-click-context/tests/repo-review-ui.test.mjs
```

New focused test filename относится к планируемой реализации. Required broad
gates идут по actual CI; исходные команды сохранены в reference foundation docs.
No runtime PASS по старым 381 tests или целостности этого ZIP. Device tests
Windows NOT_RUN без actual receipt; broad LAYA4-009/M5-02 остаются PARTIAL.
