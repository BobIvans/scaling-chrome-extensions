# PR-003: полный переносимый ZIP контекста с возобновлением

Target: `BobIvans/scaling-chrome-extensions`. Source task: `LAYA4-010`,
dependency: фактически implemented raw manifest slice `LAYA4-009` из №2.
Примерно 60 минут focused implementation плюс required verification.
Это подготовленный PR-input; live HEAD, код exporter, GitHub PR/merge/CI не
проверены. В приложенном №2 статус также `PREPARED_IMPLEMENTATION_BRIEF`.

## Пользовательский прирост и честная граница

После одного локального запуска весь **captured INDEXED** набор выбранного
verified batch оказывается в одном ZIP. Он переносится на другую машину,
открывается после распаковки через `INDEX.html`, содержит original entry ledger,
byte ranges, raw chunks и явные gaps. Любой исходник связан со всеми его parts,
а part — с точным source ordinal/path. При restart не нужно повторно сохранять
уже проверенные raw parts. Нет фиксированного максимума файлов/частей корпуса.

Captured bytes и all tracked bytes — отдельные свойства. 4 gaps в примере
остаются gaps; экспорт не делает unsupported/protected/oversize data captured.
Снятие 32 MiB Git inventory / 8 MiB source limits остаётся последующим ZIP-004/005.
ZIP64 позволяет использовать формат больших архивов; размер и скорость реальных
корпусов определяются storage/resource budgets и фактическими измерениями.

Основной путь здесь — **foreground CLI**, продолжающий writer №2. Этот часовой
PR не включает long native call, отдельный scheduler, новый store или desktop
shell. Offline index — UI этого среза. Встраивание одного scan→manifest→archive
клика в desktop рассматривается позднее при наличии transport/worker evidence.

## Точная связь с приложенным №2

| №2 / сохраняемый контракт | Что использует №3 |
| --- | --- |
| `BATCH.json`, `occ.repo-manifest-batch.v1` | Exact binding, batch_id и byte hashes metadata |
| `REPO_MANIFEST.jsonl`, `occ.repo-entry-manifest.v1` | Все 50 fixture entries, dispositions, source hashes/OID |
| `PARTS_INDEX.jsonl`, `occ.repo-part-index.v1` | Все 78 fixture chunks, source_start/source_end, revision |
| part_id = repo_chunks.revision | Generated `parts/<part_id>.bin`, без переименования source IDs |
| `automation_core.digest` | Тот же spaced sorted JSON digest для binding/revision |
| `VALIDATION.json` writer №2 | Global proof, не INFO/page-only NOT_RUN |
| Native `INFO/ENTRIES/PARTS` | Совместимость; raw bytes/ZIP туда не добавляются |
| UI query pagination | Никакого total cap; все pages доступны, tail не пропадает |

PR-002 не имеет готового installed writer в своём ZIP. Coding-агент сначала
проверяет actual checkout/результат №2. Fixture `BATCH.example.json` имеет
synthetic proof scope; приложение не принимает его за реальную DB qualification.
Валидатор примера работает с synthetic fixture явно. Нужна actual verified
metadata projection из current SCE и authorised namespace/repository/profile.

## Owners и минимальный diff

| Candidate path | Изменение |
| --- | --- |
| Actual `content-lab/repo_manifest.py` или существующий аналог | Reuse frozen metadata iterator/validation/CLI profile checks |
| `content-lab/repo_archive.py` — предлагаемый sibling | Foreground build/resume/status, lock, raw stage, ZIP и static index |
| `content-lab/repo_context.py` | Reuse existing SQLite schema/authorization; менять лишь при доказанном gap |
| `content-lab/test_repo_archive.py` | Real DB/CLI and injected crash/disk-full/recovery cases |
| `content-lab/test_repo_manifest.py`, existing context tests | Actual regressions; не переписывать №2 |
| `docs/automation/...` — actual export docs | Scope, flags, directory layout и recovery evidence |

Эти пути — suggestions, не ограничение на количество touched files. Выбрать
минимальный coherent diff на actual HEAD. Native bridge/UI allowlists не нужно
менять для standalone foreground export. `repo_chunks.raw` и existing
`content.sqlite3` остаются source owner; staging — удаляемая/rebuildable output
projection, не второй source ledger. Нет job host или process daemon.

## CLI и выбор источников

```bash
python -B content-lab/repo_archive.py --profile /absolute/native-profile.json --repository sce --manifest /absolute/verified-manifest-dir --output /absolute/export-parent
python -B content-lab/repo_archive.py --profile /absolute/native-profile.json --repository sce --manifest /absolute/verified-manifest-dir --output /absolute/export-parent --resume
python -B content-lab/repo_archive.py --profile /absolute/native-profile.json --repository sce --manifest /absolute/verified-manifest-dir --output /absolute/export-parent --status
```

Команды — proposed interface, заменить actual path/IDs; приложение ещё предстоит
реализовать. `--manifest` содержит frozen `BATCH.json` и №2 metadata/proof.
`--profile` — trusted operator profile; UI/context текст не может подменять пути.
Output outside configured source root, store и input manifest; не следовать
symlinks/junctions. Пределы disk/time/buffer явные, configurable, не hidden cap
корпуса. Большой raw dataset не загружается в JS, JSON response или память целиком.

Перед payload read сверить repository/namespace/snapshot/profile binding,
batch digest, byte hashes двух JSONL и полную validity №2. Читать captured raw
через ordered SQL cursor по точным `(snapshot_id,path,chunk_ordinal,revision)`.
Каждая part проходит bytes/hash/range/revision binding. Ни Git, ни working-tree,
ни HTTP acquisition/AI call для export не нужны. Старый pinned snapshot разрешён
при действующем profile; новый HEAD сам по себе не переписывает historical batch.
При profile revocation export blocked. Manifest/output mismatch не исправляется
неявным переходом к другому snapshot или перепарсингом.

## Identity и layout

`export_id = automation_core.digest({schema,batch_id,metadata_sha256,format,
payload_policy,index_policy})`. Exact proposed binding см. EXPORT_CONTRACT.
Порядок/serialization fixed. IDs не включают machine absolute paths, timestamp
или случайный run_id. `run_id` отдельно создаётся один раз на explicit новый run;
staging/lock принадлежат export_id, checkpoint связывает текущий run_id.
Same-content output identity не означает детерминированный SHA ZIP container:
ZIP metadata/compression могут различаться; receipt подтверждает actual archive.

```text
<trusted-output-parent>/
  .stage-<export_id>/                 # private rebuildable files, не выдавать как ready
  .lock-<export_id>                   # process lock; held while writer active
  REPO_<export_id>.zip
  REPO_<export_id>.zip.sha256
  REPO_<export_id>.receipt.json
```

Пути выше описывают artifact layout. В ZIP входят `BUNDLE.json`, BATCH, обе
JSONL, validation, README, INDEX, paged navigation HTML, `parts/<part_id>.bin`
и `EXPORT_MANIFEST.jsonl`. Полный nested reference tree/history/source repo
не дублируется. Source filenames — metadata; extraction не создаёт CON/NUL,
длинные/hostile/несовместимые original paths. Generated paths только lowercase
IDs и безопасные ASCII filenames. Broken original names остаются reversible data.

## Atomic stage и checkpoint

Один process lock на canonical output/export_id обязателен. Reuse existing
portable lock helper при его наличии; иначе маленький OS advisory file-lock
adapter с Windows/POSIX тестами. Lock освобождается при process exit; PID-file
с heuristics/stale timeout не является достаточным доказательством остановки.
Не создавать второй writer после неизвестного timeout. `--status` read-only.

Для каждого chunk: создавай generated sibling `.tmp`; пиши bytes с incremental
hash; проверяй expected count/SHA/revision; flush и fsync; close; same-filesystem
atomic rename в final part path. Только после этого checkpoint учитывает part.
При crash между rename и checkpoint part находится сканированием/проверкой;
при crash раньше rename temp не считается committed. Не сохранять огромный
список всех parts в одном checkpoint: фиксированный summary, file metadata
и chunk inventory №2 дают rebuildable truth. Resume никогда не доверяет cursor
или флагу verified без повторного bytes/hash check completed outputs.

Checkpoint `EXPORT_STATE.json` в private staging — derivable transfer receipt,
не авторитетный source database. Он имеет schema/export_id/batch_id/run_id,
state/phase/counters/reason/last_committed_part. Пишется atomic replace. SQLite
raw data и frozen manifests позволяют восстановить counts. Missing checkpoint
при intact stage не означает потерю chunks. Corrupt state или неизвестный batch
=> явный blocker, не reset с другой identity.

Ctrl+C до финальной publish фиксирует CANCELLED при ближайшей безопасной границе;
SIGKILL/crash виден как interrupted active checkpoint и требует explicit resume.
`--resume` не оживляет CANCELLED. `--new-run` после explicit operator action
создаёт новый run_id и может reuse точные verified parts того же export_id,
сохраняя предыдущий terminal receipt. Нет auto resume после открытия окна.
Disk full/permission error => BLOCKED, сохраняются complete parts и reason.

## ZIP assembly и crash windows

Сборка использует stdlib-compatible ZIP64, stream file copy с bounded buffer,
не `read_bytes()` всех payloads. Во временный ZIP пишутся только approved
generated files, без `.tmp`, locks, checkpoints и абсолютных paths. Не делать
unsafe append к повреждённому `.partial`. При сбое ZIP assembly запускается
заново из completed parts; **resume относится к parts**, не byte offset ZIP.

Закрыть ZIP, проверить duplicates/member set/CRC, content hashes и exact
reconstruction после открытия archive. Порядок: closed `.partial` verify →
fsync → atomic rename final ZIP → внешние checksum/receipt atomic writes →
checkpoint PUBLISHED. Ready определяется valid exact ZIP + matching receipt,
а наличие имени ZIP не равно completed run. Crash после rename до receipt:
resume проверяет существующий ZIP и восстанавливает sidecars без second archive.
Существующий damaged final не перезаписывать незаметно: blocker с explicit
repair/quarantine action, untouched earlier valid outputs остаются доступны.
Прерванный новый export не может удалить archive другого export_id.

`EXPORT_MANIFEST.jsonl` перечисляет каждый archive output, кроме себя (чтобы
избежать self-reference); правило явно в BUNDLE. Внешний receipt хранит SHA256
этого manifest и ZIP. Part payload hashes SHA256; part_id — existing revision,
не content hash. Two equal payloads разных logical chunks не сливаются по IDs.
Proof проверяет ranges contiguous, no overlap/gaps, source bytes/hash, chunk
revision и Git blob OID SHA1/SHA256 по original object format.

## Offline index

Без сетевых assets, JS fetch `file://`, external CSS/fonts и автоисполнения repo.
INDEX содержит цель full captured export, snapshot SHA, counts, graph status,
scope и links к metadata/entry pages. Entry page показывает every row/reason;
INDEXED source ведёт в paged part list. Part list показывает full byte range,
hash, text eligibility, link назад к source row и raw payload link. Все relative
links разрешаются после переноса распакованного каталога на другой machine root.
Каждая page bounded; число pages не ограничено. Groups/AI TASK links показываются
только если реально supplied contract их содержит; raw slice => NOT_GENERATED.
Для HTML использовать escaping/text nodes и generated href, hostile path никогда
не вставлять в attributes/JS. Binary/empty части доступны как raw bytes.

## План на один час

| Шаг | Минуты | Результат |
| --- | --- | --- |
| 1 | 5 | Actual SHA, implemented №2 mapping, owner/preflight receipt |
| 2 | 15 | Streaming raw stage, generated paths и atomic parts |
| 3 | 10 | Process lock, checkpoint, resume/status/cancel semantics |
| 4 | 12 | Static index, ZIP64 assembly, verification/publish/sidecars |
| 5 | 13 | Real DB/CLI faults, reconstruction и legacy regressions |
| 6 | 5 | Required gates, coherent diff, actual result и next handoff |

Если actual prerequisite/portable lock отсутствует, оценка меняется. Сохранить
конкретный gap и coherent unfinished scope; не заявлять whole PR done по таймеру.
Broad LAYA4-010 требует actual Windows opening receipt и connected workflow;
foreground qualified slice сам по себе не закрывает весь M5-02.

16 cases и evidence requirements — plan/ACCEPTANCE_CASES.json. Synthetic 50/78
fixture показывает portable bytes/ranges/index только. Он не тестирует real
exporter/lock/native/Windows/crash integration. Runtime result template имеет
NOT_RUN. Required gates брать из actual repo/CI; suggested focused commands:

```bash
python -B -m unittest discover -s content-lab -p 'test_repo_archive.py' -v
python -B -m unittest discover -s content-lab -p 'test_repo_manifest.py' -v
python -B -m unittest discover -s content-lab -p 'test_repo_context.py' -v
```

Existing Node/bridge gates выполнять если current CI требует или реально
затронута общая negotiation/UI; их historical green не доказывает новый exporter.
Device memory/latency/version измерить отдельно на реальной машине. Remote PR
number/URL/merge остаются null до наблюдения. Следующий пакет: ZIP-004, а automation
Web3/Grok/voice остаётся в исходных source registries.
