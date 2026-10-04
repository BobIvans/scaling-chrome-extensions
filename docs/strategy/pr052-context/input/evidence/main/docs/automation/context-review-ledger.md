# OCC intake и сохраняемые review-сессии

Git-backed full-repository indexing и законченный repo/review UI описаны в
[context foundation](context-foundation.md). Existing bounded inbox intake ниже
сохраняется; для полного Git inventory используется новый cursor owner в том же
store. Generic client base_repo_sha остаётся UNBOUND, Git binding проверяется отдельно.

Интеграция двух ZIP от 2026-10-02 в `BobIvans/scaling-chrome-extensions`.
Точные хеши входных архивов и карта реализованного/оставшегося:
[occ-package-reconciliation.json](occ-package-reconciliation.json).

## Владельцы

`content-lab/content_lab.py` остаётся владельцем `content.sqlite3`, immutable
source items, FTS и локального CPU ASR. `automation_core.py` владеет source heads
и единственной очередью. Существующие schedule tick/supervisor и qualification
bridge не заменены. Новые таблицы содержат только проекции intake и review metadata;
второй DB/FTS/queue/scheduler не создаётся.

## Intake

Явно выбранная локальная папка служит workspace/store. В `inbox` оператор кладёт
выбранные материалы; опциональный `--repo` разрешает только статическое чтение.
Workspace и repo не могут пересекаться. Reports/inbox/store links отклоняются.

```bash
python content-lab/occ_local.py init --workspace /local/occ-store
python content-lab/occ_local.py once --workspace /local/occ-store --repo /local/reviewed-repo
python content-lab/occ_local.py pause --workspace /local/occ-store
python content-lab/occ_local.py resume --workspace /local/occ-store
```

За вызов: до 2000 scan entries на root и восьми новых/изменённых файлов;
файл до 4 MiB. Одинаковое содержимое отмечается `duplicate_of`, повтор без
изменений не создаёт новых записей. `reports/latest.json`/`.md` содержат хеши,
статусы, keywords и простые Python AST counts; исходный private text в DB/FTS/report
этим intake не сохраняется. Один старый материал выбирается из известного индекса,
а не из всей пользовательской Library. Существующий Content Lab import отдельно
может сохранять выбранный текст для поиска.

Изменения определяются по size/mtime; одинаковые metadata могут скрыть замену.
Удалённые записи этим collector не tombstone-ятся. PDF/HTML/images/audio остаются
`NEEDS_*`, DOCX извлекается только из main-body paragraphs. Filename exclusions
не являются полноценным secret detector. Python AST counts — статические признаки,
не доказанные баги. Link checks не являются sandbox против hostile concurrent
filesystem mutation. Reports — восстанавливаемая проекция; DB commit предшествует
их записи. Ошибка записи report не откатывает уже сохранённый metadata index.

## Review ledger / import

Выбор для semantic review берётся из актуальных `sync_heads` существующего owner,
а не из intake keywords. Session identity включает namespace, sorted source
item IDs/input hashes, goal hash, export bundle/hash и optional base repo SHA.
Session immutable; timestamps хранятся отдельно. Цель сохраняется только как хеш.
Экспорт — metadata identity существующего canonical context pack; этот PR не создаёт
второй файловый export service. Исходные immutable items остаются в canonical store.

```bash
python content-lab/context_review.py --store /local/occ-store --namespace project \
  create --ids CURRENT_ITEM_SHA256 --goal "Review selected sources"
python content-lab/context_review.py --store /local/occ-store --namespace project list
python content-lab/context_review.py --store /local/occ-store --namespace project \
  import --file /local/REVIEW_RESULT.json
python content-lab/context_review.py --store /local/occ-store --namespace project \
  get --session-id SESSION_SHA256
```

Native API использует существующий opt-in `durableCore`, operator profile и namespace
allowlist. Installer копирует новый `context_review.py`; путь/store выбирает профиль,
а не Chrome/model/source text. Добавлены:

| Команда | Поля помимо `type`/transport `requestId` |
| --- | --- |
| `durable.review.create` | `namespace`, `ids`, `goal`, optional `baseRepoSha` |
| `durable.review.import` | `namespace`, `review` |
| `durable.review.list` | `namespace`, optional `limit` (1–20) |
| `durable.review.get` | `namespace`, `sessionId` |

Готовые UI-кнопки review и голосовая команда к этим API не добавлены. Они доступны
через существующий NativeClient request surface и CLI. Host отключён по умолчанию.
Native input ограничен 16 000 bytes, output — 192 000. CLI review input — 128 000,
до 10 selected sources и 50 findings. Strict JSON отклоняет duplicate keys,
NaN/Infinity и неизвестные поля, включая `patches`, `argv`, `approval` и shell.

Схема `occ.review-result.v1` — адаптация donor template. Корневые поля:
`schema`, `session_id`, `snapshot_sha256`, `sources`, `base_repo_sha`,
`coverage`, `findings`. `sources` точно совпадают с сохранённой session;
`coverage` содержит `reviewed`, `not_reviewed`, `missing_dependencies`.
Каждый finding: `finding_id`, `classification`, `disposition`, `source_key`,
`source_sha256`, `criterion`, `evidence_refs`, `duplicate_of`, `supersedes`.
Fixture-образец: [context-review-result.example.json](context-review-result.example.json).

Одинаковый import idempotent. Изменённый результат — новая immutable version с
`supersedes`; повтор старой version не откатывает current head. При list/get/import
source heads проверяются заново: changed -> `STALE`, missing -> `NEEDS_CONTEXT`.
Проверяется состояние canonical store, не незасинхронизированные файлы диска.
Optional base repo SHA — binding metadata; этот ledger сам Git checkout не проверяет.

В `NEEDS_REVIEW` сохраняются классы `CODE_DEFECT`, `MISSING_EVIDENCE`,
`ENVIRONMENT_BLOCKER`, `PROPOSAL_ONLY`. CODE_DEFECT claims остаются
`STATIC_CANDIDATE`. `DONE` и даже supplied `TEST_RECEIPT` hash — недоверенные claims;
они не закрывают finding. Criterion-specific independent evidence verifier остаётся
следующим integration step. Никакой импорт не применяет patch и не enqueue-ит job.
Restart восстанавливает только metadata, без approvals/timers/ASR/browser grants.

## Laya/voice / ASR

`occ-config/laya_request.example.json` и `voice_tools.responses.json` — proposals;
`occ_proposal.py` валидирует bounded goals, source refs, repeats и confidence,
но всегда возвращает `REVIEW_REQUIRED`, `job_created=false`, `dispatch_allowed=false`.
`hourly` не регистрирует schedule. Paper campaign plan — design data; ни proposal
validator, ни existing job validator не принимают его как executable request.

`asr_cpu_experiment.py` вызывает существующий `transcribe_file`:

```bash
python content-lab/asr_cpu_experiment.py --input /local/voice.wav \
  --output /local/private-transcript.json --model-dir /local/whisper-small --language ru
```

Нужен отдельный opt-in faster-whisper venv и complete local model directory.
Downloads, новые runtime dependencies и model weights в CI отсутствуют. Existing
output не перезаписывается; changed input/model отклоняется, включая запись output
другим writer во время inference. Transcript в выбранном output содержит private
text; command stdout содержит только статус/хеш. Реальный Dell/ASR quality замер
не выполнялся. Existing recorder/cancel owner не изменён.

## Что ещё заблокировано

Второй ZIP предлагает `capture_selected_chat`/`ask_in_selected_chat` с durable
attempts и explicit send approval. На audited main такого executor нет. F29/F30
остаются draft (#31/#32), installed Windows Chrome/device receipt отсутствует.
Этот PR не копирует donor Playwright/browser profile/approval authority и не
включает sends. Unknown browser effects поэтому не retry-ятся этим кодом;
реальная selected-chat restart/reconciliation интеграция остаётся открытой.
Оригинальные donor suites (93 + 37) проверены отдельно; они не являются device
qualification и не означают, что donor web app перенесён целиком.

Current studious main содержит `scripts/run_occ_memory_qualification.py` ->
`src/occ_memory_qualification_bridge.py` -> `qualification_report.qualify_and_report`.
Существующий merged OCC #34 использует этот contract, exact operator-owned SHAs
и false authority fields. Historical #547 и его request не импортируются как
runtime. Старый script path отклоняется regression-тестом. Real installed bridge
не запускался; обновлённая OCC installation потребует operator profile с новым SHA.

Исходные private aggregated chats, historical FAST-Q receipts и Waves/RND planning
не публикуются как актуальное implementation evidence. Никакая profitability,
live trading, paid provider access или installed-device готовность не заявляется.
