# MASTER CONTEXT — ROADMAP PR-012 + PR-013 / GitHub PR #51

**Название:** Полный жизненный цикл источников: durable repo jobs, полная
пагинация, delta/CAS, документы/OCR, сохранённые media/ASR и web/RSS/GitHub history.
Исходный английский title: **Unified source lifecycle: durable repo jobs,
delta/CAS and provenance-aware importers**.

Репозиторий: `BobIvans/scaling-chrome-extensions`.
Продолжение: [GitHub PR #51](https://github.com/BobIvans/scaling-chrome-extensions/pull/51),
ветка `codex/pr012-013-source-ledger-continuation`.
Предыдущий stage: [GitHub PR #47](https://github.com/BobIvans/scaling-chrome-extensions/pull/47), merged.
**№012 и №013 — номера roadmap packages; они не означают GitHub pull/12 и pull/13.**
Один общий parent scope сохранён; #47 уже поставил частичную реализацию,
#51 продолжает её. Создавать повторный PR для уже слитого #47 не требуется.

## Цель и исходные требования

Windows 11 / Dell Latitude 5400 / 16 GB: локальная библиотека должна сохранять
и учитывать весь выбранный корпус, закреплять версии источников и точные
координаты, переживать interruption/restart и предоставлять полный traversal
до EOF. Переиспользовать immutable bytes, сохранять все origins, обновлять
только затронутые производные и evidence. PDF/Office/OCR, сохранённые audio/video,
web/RSS и GitHub history получают общий source/importer lifecycle и provenance.

Пользователь требует сохранить стратегию целиком. Page/frame/part/memory budgets
определяют размер порции и backpressure; общий потолок 20 документов, 39 parts
или произвольного размера repo не допускается. Resource exhaustion должен
оставлять явный error/gap/pending и continuation, а не скрытый пропуск.
Все 101 исходных критериев сохраняются, включая broad/downstream scope.
Узкий тест либо merge одного stage не закрывает их автоматически.

## Source of truth

1. Текущие инструкции пользователя и применимые repository `AGENTS.md`.
   При этой сверке tracked `AGENTS.md` и инструкции в workspace ancestors не найдены;
   Codex повторно проверяет их при новом checkout.
2. **Требования этого объединённого пакета:** неизменные `input/` и exact ZIP
   `originals/ROADMAP_PR_012_013_COMBINED_RU_2026-10-04.zip`.
   `input/sources/ORIGINAL_CARDS.json`, оба ORIGINAL_PR briefs/prompts,
   `input/CRITERION_COVERAGE.json` сохраняют полный текст и IDs.
   `input/IMPLEMENTATION_RU.md`, `WORKSTREAMS.json`, `PR_PLAN.json` и unified contract
   задают согласованную архитектуру combined package.
3. **Более широкий roadmap и ownership:**
   `docs/strategy/voice-agentos/roadmap/source_master/strategy_v5/`,
   `roadmap/briefs/PR_010.json`–`PR_021.json`, `roadmap/plan/DELIVERY_DAG.json`,
   `roadmap/coverage/ALL_*_TO_PR.json`. Они сохраняют общий backlog и upstream/downstream
   связи; текущий запрос остаётся о №012/013.
4. **Факт реализации:** свежий Git checkout, handlers/schema/tests, actual PR/head,
   checks и соответствующие runtime/device receipts. Старый план, PR body или
   pending patch не заменяет проверку текущего кода.
5. **Навигация после сверки:** эти два Markdown файла, `audit/CURRENT_VS_PLANNED.json`,
   `audit/REPOSITORY_AUDIT.json`, `audit/CRITERION_STATUS.json`,
   `verification/LOCAL_VALIDATION.json`. Все записи датированы; перед новой работой
   обновить live heads. Изменение этих статусов не меняет оригинальные требования.

`input/CURRENT_VS_PLANNED.json` исторически имеет PLAN_ONLY и no completion claims.
Свежий audit намеренно находится отдельно. `input/EXECUTE_THIS_PR_RU.txt` сохраняет
первоначальную команду реализации; сегодня её выполнять с учётом merged #47 и
существующей #51. Полные оригинальные карточки важнее краткой таблицы ниже.

**Доступные bytes:** этот приложенный combined ZIP сохранён полностью:
19 файлов, 6 workstreams, 10 tasks, 15 features, 15 feature-audit records,
6 goals, 2 decisions, 101 criteria и 15 acceptance cases. Его SHA-256:
`bd4ff79d06bbdd581617ad12455e53ba0a2bf0c664519ebfe72082ab4f6b06a3`.
Два исходных крупных ZIP названы в `input/PROVENANCE.json`. Существующий
`voice-agentos` tree хранит ранее переданный ZIP №010–021 и V5 extracts; полный
387 MB `ALL_IN_ONE_PRODUCT_ROADMAP_RND_RU_2026-10-03.zip` в этом combined input
отсутствует. Не утверждать, что все старые чаты/media/master bytes также вложены.
Не уменьшать требования из-за этой границы: отмечать конкретный missing input.

## Что уже выполнено

Аудит main: `ccf73e747e6743ead68040e3eb6837b3a5233fbc`.
Исходный head #51 при сверке: `83f6337ccf725da443a673fc84d623bed04a3c29`.
Main с полной Voice AgentOS документацией интегрирован в #51 локальным merge
`27cb446fc803df63d485ad376c1954bed30b30f7`; исходные кодовые изменения #51 сохранены.
Новый documentation commit будет потомком этого SHA. Эти SHA — снимок,
не указание игнорировать более свежий remote head.

| Область | Подтверждённый код / расположение | Оставшийся scope |
|---|---|---|
| №001–004 | GitHub #38–41 merged: scan ledger, manifest/ranges, ZIP64/resume и streaming Git inventory | Не писать эти foundations заново; проверить интеграцию и full device/scale scope |
| #47, WS-003 | `repo_history.py:snapshots/delta`, Native `durable.repo.history/delta`, Desktop paged reads и JSONL export; merge `8ad12c9f3e43d03cc8c7c6a4de1d9de083fe74bf` | Остальные summary/selection/export consumers и bounded graph memory |
| #47, WS-002 | Опциональные Desktop START/STATUS/STEP/PAUSE/CONTINUE/CANCEL поверх `repo_scan_runs`; revision/cursor fences | Manual stepping ещё не background Core execution |
| #51, WS-006 substrate | `source_ledger.py`: FILE/MEDIA originals; namespace/kind/stable key, aliases, raw SHA, versions, observations, staged 64 KiB parts; `versions/raw_parts/read_part/delta_parts` | Единый SourceAddress, raw-owner reconciliation, extraction cache и selective evidence invalidation |
| #51 migration/Windows | Additive old-origin migration, installer включает source ledger; two-pass exact-byte capture и Windows file-identity fix | Installed Dell/Windows и большой corpus не квалифицированы |
| №014/015 #50 | Merged context library/packets/recovery/runtime; зарегистрированные Core context jobs, search/read spans, STOP | Context raw owner и #51 raw owner ещё требуют общей адресации |
| №018/019 #48 | Merged workflow/campaign/lease/release substrate в том же Core | Его наличие не доказывает importer job/history критерии №012/013 |

Здесь повторно выполнены **13 existing tests: 9 source-ledger + 4 repo-history,
PASS**, old Voice AgentOS source-integrity проверил 1826 members, Desktop package
verify прошёл. `verification/LOCAL_VALIDATION.json` привязывает это к checkout
и hashes проверенного кода. Это Linux/local evidence ограниченного scope.
При API-сверке CI исходного head #51 ещё `in_progress`; live CI обновить после
публикации нового head. Windows hosted CI, installed Windows/Dell, UI usefulness
и full criterion acceptance — разные статусы. Device gate: **NOT_RUN**.

## Что осталось по всем шести workstreams

| WS | Полный следующий scope | Dependencies / evidence |
|---|---|---|
| WS-002 | Registered repo/capture job в существующем Core; idempotent immutable intent; progress; lease fencing; durable checkpoint; pause/resume/cancel/restart; terminal drift | Existing scan/inventory owner; R01/R02/R03, installed background/UI |
| WS-003 | Полная выдача snapshots/selections/delta/export до EOF; bounded summaries/graph traversal; complete last source/part; atomic recovery при disk-full/crash | Использовать #47 pages и №002/003 exporter; R04/R05, selection/export и scale receipts |
| WS-006 | Общая raw/version/address модель; namespace-aware CAS без потери origins; parser/model/config/policy cache keys; declared commit/dirty/history/LFS/submodule scopes; range delta/lineage; dependency-based STALE/RECHECK_REQUIRED | №010 identity/address и №011 proven graph; R06/R07, clean vs incremental equivalence |
| WS-009 | PDF/DOCX/XLSX/PPTX magic/MIME registry; ленивые extract jobs; page/cell/slide coordinates; tables/numbers/signs/units/merged cells; OCR-derived confidence; corrections как новая revision | Минимальный ImporterV1 + SourceAddress; D01/D02, support matrix и marked corpus |
| WS-010 | Сохранённые media originals и ASR/transcript revisions; ordered time spans, UNKNOWN speaker/unintelligible ranges; model/config/hash; cancel/resume; RU/EN/code-switch corpus и реальные cost/resource measurements | Общий importer/Core; M01/M02; не live microphone |
| WS-011 | Web/RSS revision/Observation, raw responses/provenance; GitHub PR/issues/reviews/checks/workflow attempts до EOF; stable identity/dedup, backoff/cursors, partial freshness и explicit gaps | Read-only adapters + current API verification; W01/W02; старый CI fetch не весь history importer |

Полный текст приёмки и source IDs: `input/WORKSTREAMS.json` и
`input/CRITERION_COVERAGE.json`. `audit/CRITERION_STATUS.json` сохраняет каждый
из 101 exact criteria с owner, existing code hints и next evidence. Все broad
criteria пока **OPEN**; component tests не являются 101 closure receipts.
Cross-source citation/restart X01 и Dell 16 GB cold/warm X02 остаются отдельными
обязательными cases. Не скрывать неисполненный scope за словом «substrate».

**Проверенные остатки в текущем коде:** `repo_context.list_snapshots` всё ещё
использует `LIMIT 20`; `snapshot_changes` загружает оба entries set в arrays,
строит graph и возвращает preview `[:20]`. У #47 есть отдельный полный paged read
path: заменить реальные consumers, сохранив compatibility там, где preview
объявлен явно. `source_ledger.delta_parts` — точные fixed 64 KiB byte-part ranges,
а не минимальный semantic diff. `versions` пока имеет простой anchor cursor;
строгий pin/filter/version-bound contract из стратегии ещё требует проверки.

## Архитектура и владельцы

- Один `content.sqlite3`: `automation_core.connection`, `content_lab.py` и текущий
  schema owner. Не создавать новую authority DB, scheduler, executor или Git reader.
- Existing raw dialects: ChatGPT `import_raw_blobs` и node provenance в
  `content_lab.py`; `context_sources/context_raw_parts` в `context_library.py`;
  `source_origins/source_versions/source_observations/source_raw_objects/source_raw_parts`
  в `source_ledger.py`. Один файл DB ещё не означает единый source/CAS contract.
- `automation_core.Core`, enqueue/claim/heartbeat/cancellation и `workflow_state.py`
  остаются owner Core execution/STOP. `context_runtime.submit/query/run_job`
  показывает существующий путь интеграции context jobs, а не повод дублировать его.
- Repo owner: `repo_scan.py`, `repo_inventory.py`, `repo_context.py`, `repo_source.py`,
  `repo_manifest.py`, `repo_history.py`, `repo_archive.py`, `repo_groups.py`, `repo_js*.py`.
- Transport/UI: `native_adapter.py`, `agent-bridge/durable.mjs`, `desktop/client.py`,
  `desktop/app.py`. Сохранить current context/workflow handlers при интеграции.
- Shipping: `agent-bridge/Install.ps1`, `desktop/OWNED_FILES.json`, package/backend
  hashes и `context_runtime.SHIPPING`; actual shipping changes требуют сверки
  всех owners. Эта передача не изменяет runtime implementation.

Source identity, byte object, immutable version, Observation, Extraction и search
item имеют разные роли. SourceAddress закрепляет source/version/extraction и
coordinate precision EXACT/APPROXIMATE/UNKNOWN. Невозможный mapping остаётся UNKNOWN.
Alias/rename не стирает historical path. LFS pointer ≠ fetched payload.
Completed raw capture ≠ extracted/searchable/qualified importer result.
Cache eviction удаляет derived, сохраняя reachable original evidence.
Существующий `max_parallel=1` не менять без measured admission gate.

## Коллизии и границы исходной стратегии

`input/00_START_HERE_RU.md` разрешает importer №016 dependency cycle:
**минимальный ImporterV1 вводится здесь**, extension №016 не prerequisite.
WS-005 graph prerequisite принадлежит №011, WS-007 importer foundation — №010;
их нельзя ошибочно создавать как дополнительные workstreams №012/013.
Ограниченный raw CAS reuse входит сюда; broader storage/GC/backup остаётся у
canonical owner/№014/015. Старые prose №28/32/37 и иные historical numbers
сохранены verbatim; актуальную нумерацию определять по DAG/source IDs.

GitHub history importer этого пакета read-only; code release/PR-write workflows
имеют других owners. Stored media scope не включает microphone/hotkey voice intent.
Внешние credentials/grants и arbitrary protocols не появляются автоматически.
Одновременно полные future requirements не удаляются из более широкого backlog.

## Следующий конкретный этап для Codex

**Продолжать #51: unified versioned SourceAddress и read adapters поверх трёх
существующих raw dialects, затем durable Core repo/capture lifecycle.**
Это необходимый №010 foundation внутри зависимого №012/013, а не объявление
полного №010 завершённым и не отвлечение на все соседние packages.

1. Refresh main и #51; сравнить с `audit/REPOSITORY_AUDIT.json`. Если #51 уже merged,
   начать оставшийся stage от свежего main, сохранив parent ROADMAP-PR-012+013.
   Не применять archived pending patches слепо и не force-push.
2. Зафиксировать ADR/schema для SourceAddress/ImporterV1 и compatibility adapters:
   ChatGPT originals, #50 context spans, #51 FILE/MEDIA raw parts. Сохранить old
   IDs/bytes/revisions, namespace, scope и observations. Migration additive,
   idempotent, version-gated, с rehearsal на populated DB copy.
3. Добавить bounded exact read/search/versions/observations traversal до EOF;
   citation после restart открывает ту же revision/range/hash. Бинарный original
   возвращает raw/explicit unsupported extraction, а не ложный text item.
4. Зарегистрировать применимые длительные repo/capture operations в текущем Core:
   immutable request digest и intent; единый job ID; committed checkpoint; fencing;
   background continuation и отдельные CANCEL/BLOCKED/SOURCE_DRIFT outcomes.
   Terminal cancel/STOP не позволяет late worker публиковать version/head.
5. Подключить typed Native/Desktop reads/job progress с существующим profile;
   UI не вводит arbitrary SQL/argv/roots. Сверить installed shipping owners.
6. Подтвердить независимыми fixtures exact bytes/RU/EN/BOM/CRLF/binary, distinct
   origins/shared bytes/rename, bad namespace/hash/ranges, >20 versions и большой
   parts tail, ack loss, cancel/STOP/restart/drift, old schema/migration replay.
   Записать scoped receipts, полный остаток и текущий CI SHA.

Затем последовательно закрывать full WS-003 consumers, WS-006 cache/invalidation,
WS-009, WS-010, WS-011 и cross-adapter/migration/Windows gates из оригинального
`IMPLEMENTATION_RU.md`. Не останавливаться после первого stage, считая combined
package готовым. Один итоговый coherent continuation PR предпочтителен;
прошлый #47 уже merged и не должен скрывать оставшиеся критерии.

## Что читать и как проверять

Порядок подробно дан в [CODEX_START_HERE.md](CODEX_START_HERE.md).
Сначала source integrity, затем existing runtime suites согласно текущим workflows.
Минимальный local baseline этой передачи:

```bash
python docs/strategy/pr012-013/verify_integrity.py
python docs/strategy/voice-agentos/verify_integrity.py
cd content-lab
python -m unittest test_source_ledger test_repo_history -v
```

Полные gates — `.github/workflows/deterministic-core.yml`: Content Lab tests,
Desktop/Xvfb/Windows, package verify, Node bridge, qualification adapter и
extension regressions. Изменённый code требует соответствующих tests и actual-head
CI; сохранность ZIP сама по себе runtime acceptance не доказывает.
Actual installed Windows 11/Dell scale/fault/UI измерения сохранять отдельно
с peak RSS, CPU/time/disk, page counts и responsive progress, без придуманных thresholds.

Обновлять `audit/CURRENT_VS_PLANNED.json`, `audit/CRITERION_STATUS.json` и stage
receipts; использовать `input/RESULT_TEMPLATE_RU.md` как checklist результата.
Каждый закрытый criterion получает независимый oracle, input hashes, exact code
SHA и applicable scope. Остальные остаются OPEN с owner/next action. Rollback
отключает новый read path/features, не удаляет immutable originals/history.
