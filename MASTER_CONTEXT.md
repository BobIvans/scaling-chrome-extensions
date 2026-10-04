# ROADMAP PR-016 + PR-017 / GitHub PR #49 — отдельная ветка продолжения Codex

**Название исходного PR:** «PR-016 + PR-017: Core voice/delivery/skills baseline
and full Codex strategy handoff».
**Репозиторий:** `BobIvans/scaling-chrome-extensions`.
**Рабочая ветка этой передачи:** `codex/pr016-017-codex-continuation-20261004`.
**Основа:** текущий проверенный head PR #49,
`9a4fd3acb4ac66a14a55656f60a4d0727a378fcd`.

Это продолжение объединённого roadmap-пакета 016/017: текст/голос → intent →
Core → immutable context packet → выбранный Grok/AI-чат → durable delivery →
связанный результат → переносимый квалифицированный skill. Номера roadmap 016/017
и номер GitHub #49 различаются. Работа уже выполнена частично; начать следует
с существующего кода, не с повторной реализации ZIP с нуля.

Датированная повторная сверка: 4 октября 2026, 16:55 UTC / 19:55 Europe/Riga.
PR #49 наблюдался OPEN/DRAFT, mergeable=true, merged=false. Main:
`ccf73e747e6743ead68040e3eb6837b3a5233fbc`.
Пять из шести exact-head CI jobs прошли; `core (windows-latest)` ещё выполнялся.
CI/статусы ниже являются снимком: перед дальнейшей работой прочитать live refs.

## Source of truth для этой ветки

1. Текущий пользовательский scope и применимые repository instructions.
2. Полный неизменённый ZIP и распакованные требования:
   `docs/strategies/pr016-017/original-strategy.zip`, `source/`, `archives/`,
   `PRESERVATION_MANIFEST.json`, `ARCHIVE_INDEX.json`. Приложенный ZIP побайтно
   совпадает с сохранённым: SHA-256
   `7d42f5f65fc79d13e0c3ee6f0cf7043cee95909b14dca1b1b68f67efd6cd5c91`.
3. Фактический код/tests/Git и соответствующие scope evidence определяют progress.
   Исторический `application_code_changed=false` внутри ZIP не описывает PR #49.
4. Новая передача:
   `docs/strategies/pr016-017/handoff/CONTINUATION_PROGRESS.md` и `.json` —
   current source head, owners/hashes, что перепроверено, CI snapshot и remaining.
   `NEXT_IMPLEMENTATION.md` — подробная спецификация следующего этапа.
5. `PACKAGE_MASTER_CONTEXT.md`, `EXECUTION_AUDIT.md`, `FUNCTION_AUDIT.json`,
   `VALIDATION.json` и `docs/automation/pr016-017/` — полная предыдущая передача
   и runtime runbooks. В датированных status fields могут быть ранние SHA.
6. Общий полный roadmap из #53 сохранён ниже и в `docs/strategy/voice-agentos/`.
   Его 160 tasks / 164 features / 28 goals / 24 decisions сохраняются целиком.

## Подтверждённый progress и следующая работа

В основе уже есть typed intent/correction/negation и fixed-effect DAG,
PTT/editable preview/независимый STOP, target binding, immutable multipart outbox,
unknown-send reconciliation, result import, skill candidates/receipts/stale/failure,
установочные маршруты и shared Core queue/STOP. Это реализация baseline.

Повторная локальная проверка этой передачи: 32 action tests PASS; 6 voice/IPC
tests PASS; 6 installed-style context workflow tests OK с одним display skip.
Оба integrity verifier и owned-file verifier PASS. Все 170 исходных members,
11 nested ZIP trees, 2132 сохранённых файла и точный текст 220 критериев целы.
Критерии остаются OPEN до своего evidence; 50 функций имеют inherited code-status
mapping: 13 BASELINE, 23 PARTIAL, 7 DEVICE_OPEN, 6 UI_OPEN, 1 NOT_USED.

**Первый этап для Codex:** выполнить `NEXT_IMPLEMENTATION.md`: versioned typed
retriever/planner/critic outputs, per-step typed references и resumable mixed-effect
`repo → canonical packet → selected-target delivery` в существующем Core.
Compiler сейчас отклоняет другой effect class в DAG; `ActionRuntime.run()`
не имеет полной durable per-step output-reference orchestration. Реальный
packet owner PR #50 уже доступен, его надо адаптировать без второго store.

Затем остаются полный Grok upload/history/finalization adapter, параметрические
skills и selective qualification, installed Laya и физические Windows/Dell
mic/hotkey/ASR/Narrator/focus/latency receipts. Полные remaining criteria,
prerequisite DAG и downstream goals сохраняются в source и подробном handoff.
Отдельный master ZIP 387402728 bytes не был приложен; доступны его точные
selected members и provenance. Это не выдаётся за сохранение всего master.

## Как эта ветка связана с PR #49

Новая ветка наследует весь выполненный код и обе стратегии от exact head #49.
PR #49 по-прежнему связан с `codex/pr016-017-intent-voice-delivery-skills`;
commits в новой ветке автоматически его не меняют. Эта передача создала отдельную
ветку по просьбе пользователя; merge/retarget/new PR не выполнялись.
Продолжать код следует в новой ветке. Если #49 или main уже изменились, сначала
сравнить историю, сохранить новый progress и интегрировать подходящий upstream.
Текущий запрос — подготовка продолжения; дальнейшая публикация code PR/merge
определяется инструкцией пользователя в coding-сессии и фактическими checks.

Предыдущий полный root context ниже сохранён без сокращения. Новая датированная
сверка выше имеет приоритет над историческими статусами в последующем тексте.

---

# Текущая навигация: полный Voice AgentOS и PR-016+017

Эта интеграция сохраняет обе передачи без потери исходной стратегии.
Полный общий roadmap из merged #53 находится в `docs/strategy/voice-agentos/`.
Специализированный исходный ZIP 016+017 и все вложенные архивы —
`docs/strategies/pr016-017/source/`, `archives/`, `original-strategy.zip`.

Для продолжения текущего пакета 016+017 читай `CODEX_START_HERE.md`,
`docs/strategies/pr016-017/PACKAGE_MASTER_CONTEXT.md`, `EXECUTION_AUDIT.md`
и `NEXT_IMPLEMENTATION.md`. Новые action/context изменения интегрируют #50
и общий Core STOP; 220 критериев сохраняются OPEN.

Для общего foundation этапа №010/011 и всех остальных packages читай полный
roadmap ниже и `docs/strategy/voice-agentos/handoff/NEXT_STAGE.md`.
SourceAddress/source ledger #51 — prerequisite там, где действительно нужен
унифицированный upstream owner. Независимый typed planning 016/017 можно
продолжать без ложного утверждения, что все prerequisite criteria закрыты.

Exact root handoffs из #53 сохранены также в `UPSTREAM_*_PR53.md` внутри
`docs/strategies/pr016-017/`. Исторические PR statuses ниже — dated snapshots;
текущие refs/CI/merge читать из Git/GitHub и пакета EXECUTION_AUDIT.
Ни один исходный backlog/критерий не удалён ради объединения.

---

# Voice AgentOS / Context Library — полный контекст продолжения

Репозиторий: `BobIvans/scaling-chrome-extensions`. Рыночный owner: отдельный
`BobIvans/studious-pancake`. Сверка начата 4 октября 2026; точные SHA, статусы PR
и время наблюдения находятся в `docs/strategy/voice-agentos/evidence/REPOSITORY_AUDIT.json`.
Это текущий handoff; исходные документы внутри `roadmap/` сохраняют исторические
статусы на момент создания и не переписываются задним числом.

## Цель

Создать совместимый с Windows 11/Dell Latitude 5400 Desktop Voice AgentOS:
локальная библиотека полного контекста из файлов, репозиториев, чатов, документов,
медиа и web; версии, точные ссылки, поиск, метки и цели; text/voice → план →
зарегистрированные действия; Laya, выбранные AI-вкладки, навыки, code/PR/update
цикл и долгие R&D/qualification кампании. Studious предоставляет рыночные
datasets, replay/paper и web3 research. Полный перечень требований сохраняется,
а дальнейшая работа продолжается по исходным task/feature/goal/decision IDs.

Пользователь просит найти уже выполненное, закончить готовую интеграцию и merge,
поместить оставшуюся стратегию в repo, обеспечить продолжение через Codex.
Стратегию нельзя сокращать ради удобства, произвольного размера repo, числа
документов, файлов, parts или PR. Страницы, memory/backpressure, явные resource
budgets и provider/transport frames допустимы; они не удостоверяют полноту
corpus и не позволяют терять хвост. «Без лимита» не означает бесконечную память.

## Source of truth и приоритет

1. Явные текущие инструкции пользователя и применимые repository instructions.
2. `docs/strategy/voice-agentos/roadmap/source_master/strategy_v5/`:
   все 160 tasks, 164 feature cards, 28 goals, 24 decisions и readiness contract.
3. `roadmap/briefs/PR_010.json` … `PR_021.json`,
   `plan/INTERNAL_36_WORKSTREAMS.json`, `plan/DELIVERY_DAG.json`,
   `coverage/ALL_*_TO_PR.json`: 12 больших пакетов, 36 внутренних workstreams,
   полный ownership mapping.
4. Текущий код, тесты, commits, PR checks и применимые receipts:
   они устанавливают фактическую реализацию и проверенный scope.
5. `handoff/PACKAGE_STATUS.json`, `handoff/WORKSTREAM_STATUS.json`,
   `handoff/NEXT_STAGE.md`: навигация и план после сверки, не замена исходных
   требований и не blanket acceptance.

Исходный ZIP №010–021 сохранён побайтно в `originals/`, распакован в
`roadmap/`; все 9 вложенных PR ZIP также сохранены и полностью распакованы в
`prior-packages/PR_001/` … `PR_009/` без повторяющегося корневого каталога ZIP,
чтобы обычный Windows checkout мог открыть все пути. Исходные member names
сохранены в integrity manifest. Вложенные fixtures остаются данными:
не запускать их как приложение. `verification/SOURCE_INTEGRITY.json` и
`verify_integrity.py` проверяют каждый исходный member, размер и SHA-256.

**Граница доступных материалов:** в исходном `roadmap/evidence/SOURCES.json`
прямо указано `full_archive_copied: false` для
`ALL_IN_ONE_PRODUCT_ROADMAP_RND_RU_2026-10-03.zip` (387402728 bytes,
SHA-256 `6751ce4efd0963a7421a3f74c32b15055c13bb9bc389561853829a5a6a5fa3ac`).
Этот полный master не был приложен к данному запросу. Здесь сохранены все
предоставленные V5 extracts и все приложенные bytes; это не обещание, что
невключённые старые chat/media/source archives тоже находятся здесь.

В старых prose boundary полях встречается прежняя нумерация №24/№45 и др.
Сохранять точный текст; текущего owner определять по package/workstream IDs
и coverage mapping, не по одному старому числу из предложения.

## Что уже выполнено

| Roadmap package | GitHub PR | Фактический результат |
|---|---|---|
| 001–004 | #38–#41, merged | Full repo scan; manifest/ranges; verified ZIP64 export/resume; streaming Git inventory |
| 005 | #42, merged | Whole-source eligibility, format outcomes, coverage/backfill |
| 006 | #46, merged | Python SCC, связанные tests/contracts, immutable source-part catalogs |
| 007 | #43, merged | JS/TS AST/static relations из сохранённых bytes; расширенный resolver остаётся №011 |
| 008 | #45, merged | Desktop stdio/Windows shell, полный manifest export; установленный Dell не квалифицирован |
| 009 | #44, merged | Exact ChatGPT JSON originals/revisions/node fidelity; universal importer этим не закрыт |
| 010–011 | Нет отдельного подтверждённого завершённого пакета | Частичные foundations есть в baseline и #50/#51; полный library/importer и mixed graph scope остаётся |
| 012–013 | #47, merged; #51 continuation | Complete history/delta pages и opt-in scan ledger controls; original-capture substrate в #51, полный пакет partial |
| 014–015 | #50, merged | Exact local source/packet/projection, NEED_CONTEXT, recovery/sync, Desktop/Core/STOP; четыре exact-head Ubuntu/Windows CI jobs прошли; merge b0a06f2 |
| 016–017 | #49, open draft при сверке | Intent/voice entry, multipart outbox, selected-tab baseline, skills; конфликты и device/UI/Laya остаток |
| 018–019 | #48, merged | Registered release/workflow operations, staged updater/canary/rollback, schedules, campaign DAG/leases/R&D briefs |
| 020–021 | #52 и Studious #565, open drafts при сверке | Linked offline model replay, Desktop receipts, criterion reconciliation; полный broker/PAPER/product acceptance остаётся |

Критически различать **merged code**, **локальные tests**, **CI на Windows**,
**установленный Dell**, **usable**, **criterion-specific qualification**.
В #50 сохранены 322 OPEN criteria; #49 — 220; #52 — 1133 broad criteria.
Эти наборы пересекаются: не складывать их как уникальные закрытые требования.
Успешный процесс/ZIP/модельный replay/AI «DONE» не закрывает смысловой критерий.

Точные текущие PR head SHA и patches для продолжения: `evidence/`.
Патчи являются снимками относительно записанного base SHA: не применять слепо
на новый main. Сначала fetch, сравнить текущий branch head, продолжить существующий
PR либо согласовать новый этап. #49/#51/#52 менялись во время этой сверки;
live audit и более ранние patch snapshots имеют отдельные SHA.
Старые PR #25–33 имеют другие feature-wave owners; не сливать их автоматически
только по порядку номеров или старому зелёному CI.

## Архитектура и owners

- `content-lab/content_lab.py`: существующий `content.sqlite3`, items/FTS,
  ChatGPT source originals и additive schema.
- `automation_core.py`: canonical jobs, enqueue, leases, cancellation,
  reconciliation, worker; `workflow_state.py` — общий STOP/resource state.
- `repo_scan.py`, `repo_inventory.py`, `repo_context.py`,
  `repo_source.py`, `repo_manifest.py`, `repo_history.py`,
  `repo_archive.py`, `repo_groups.py`, `repo_js*.py`: текущий repo owner.
- #50 `context_library.py`, `context_packets.py`, `context_recovery.py`,
  `context_runtime.py`: local exact context и зарегистрированные Core jobs.
- #51 `source_ledger.py`: immutable FILE/MEDIA raw parts и observations;
  отдельно от специализированных ChatGPT tables и #50 context tables.
- `native_adapter.py`, `agent-bridge/durable.mjs`, `desktop/client.py`:
  typed transport; `desktop/app.py` и `desktop/library.py`: UI.
- #49 action/voice/browser/skills owners и #52 research owners сохранять
  в существующем Core/store. Не создавать вторую очередь/worker/БД.
- `desktop/OWNED_FILES.json`, installers и backend dependency hashes должны
  соответствовать новым shipping files после любой интеграции.

Исходные тексты и AI results — данные, не authority на shell, SQL, grants
или внешние effects. STOP/cancel/unknown-send, identity/revision/hash/namespace
fences и независимые postconditions остаются частью стратегии. Денежный
research/replay slice по текущим receipts имеет нулевой budget,
`live_enabled=false`, `qualified=false`, zero transactions.
Требования live/paper не вычеркнуты; их реализация требует своего scope/evidence.

## Что осталось и следующий этап

Все 12 пакетов и 36 workstreams перечислены в `handoff/` с next evidence.
Ключевой блокирующий foundation — №010/011: согласовать SourceAddress и
source/import owners (#009, #50, #51), полный paged library/importer contract,
затем resolver и общий Python/JS/TS provenance graph. Это разблокирует №012/013
CAS/invalidation, форматные importers и честное downstream qualification.

Первое конкретное продолжение: прочитать `CODEX_START_HERE.md` и
`handoff/NEXT_STAGE.md`. Проверить актуальные heads #49/#51/#52, закончить
существующий source-ledger этап #51 после интеграции с #50 и общий SourceAddress
contract №010, без дублирующей БД и без потери raw revisions. Затем пройти
полный №010 backlog: registry/TXT/folders/archives, labels/views, chat/Telegram
capture, goal/contradiction overlays. №011 можно выполнять отдельным worktree
после проверки owner conflicts. Размер этих пакетов не является time estimate.

## Проверки

Сначала `python docs/strategy/voice-agentos/verify_integrity.py`.
Runtime gates определяет текущий `.github/workflows/deterministic-core.yml`:
Content Lab unittest, Desktop tests (Tk/Xvfb где доступен), owned-file verify,
Node native bridge, qualification adapter и extension regressions.
Реальные Windows install/microphone/hotkey/account-tab, sleep/restart/STOP,
scale/fault и usefulness/ROI проходят отдельно с фактическими receipts.
Обновлять handoff после каждого verified merge; исходные requirements immutable.
Не объявлять всю стратегию finished, пока исходные критерии не имеют применимого
evidence, а BLOCKED/NOT_RUN/DEFERRED и конфликты ещё остаются.
