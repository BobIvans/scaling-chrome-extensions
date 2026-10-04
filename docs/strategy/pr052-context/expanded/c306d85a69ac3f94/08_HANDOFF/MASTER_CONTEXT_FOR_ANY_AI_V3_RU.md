# Voice AgentOS — единый контекст целей V3
Это synthesis всех substantive aims видимого чата и relevant recovered summaries, а не raw transcript всех аккаунтов.


---
Источник пакета: 00_START/00_PARALLEL_CAPTURE_DECISION_RU.md

# Главное уточнение: много наблюдателей, много изолированных исполнителей, один владелец конфликтующего эффекта

## 1. Никакого глобального запрета параллельной записи
Микрофон → один device stream → несколько потребителей ASR/VAD/архиватора. DOM, accessibility, Git и terminal collectors одновременно создают свои observations. Каждый имеет namespace/sequence/source revision. Same raw bytes могут храниться один раз, но все ссылки происхождения сохраняются.

БД физически может сериализовать короткие транзакции. Это не значит, что она сериализует весь процесс записи, ASR, поиск и запуск работы. Контент capture append-only; модель не переписывает original history. Для больших media — потоковая spool + cursor + retention, а не RAM buffer; данный lab этого не реализует.

Параллельные code writers также допустимы в разных worktrees. Общая branch/head publication контролируется отдельно. Несколько реальных действий над разными ресурсами выполняются одновременно. «Один writer» относится к конкретному неидемпотентному effect target, не к машине в целом.

## 2. Пять режимов, которые нужно выбирать явно
| Режим | Для чего | Когда завершать |
|---|---|---|
| COMPLEMENTARY_UNION | Собрать разные наблюдения одного процесса | По completion/coverage/deadline; не по первому ответу |
| REQUIRED_EVIDENCE_JOIN | Код + тесты + актуальная цель | Когда все обязательные доказательства присутствуют |
| FIRST_VERIFIED | Альтернативные способы получить одинаковый результат | Первый прошедший независимые checks, не первый fastest text |
| PARTITIONED_MAP | Части большого корпуса или разные effect targets | Все нужные partitions с coverage ledger |
| PREPARE_COMMIT | Патчи, обновления, внешний submit | Параллельная подготовка, одна scoped activation/operation |

## 3. Самый быстрый путь к пользе в нашем проекте — гипотеза
Не ждать новую большую AgentOS. Сохранить SCE content.sqlite3 / queue/review owners и добавить desktop client + event intake. Первая команда строит source-bound handoff для Studious из текущего source snapshot и known blocker. Голос и модели маршрутизации добавляются поверх того же typed request.

Проектная pipeline:
```
voice/text → IntentSpec revision
  ├─ live workspace state       ┐
  ├─ Git/symbol/test context    ├─ evidence-ready handoff v1 → chosen AI
  ├─ accepted goals/history    ┘          ↑                 ↓
  └─ allowed archive ingestion → late delta        NEED_CONTEXT / patch
                                     ↓                    ↓
                           freshness check          isolated test branch
                                     └──── verifier ──────┘
                                             ↓
                                   scoped install / receipt
```
Не нужно запускать весь набор распознавания/планирования на каждом слове. Часть read-only prefetch выполняется заранее; stable intent имеет revision. Новое «нет, не этот проект» отзывает pending effect.

## 4. ZIP и текст чата — совместимы, но не независимые голоса
ZIP — versioned procedures/contracts/backlog. Текущий текст пользователя — intent, scope и обновления требований. Repo — фактический source snapshot; execution receipts — доказательства запуска. Они обрабатываются параллельно в разных authority lanes и соединяются в один goal/evidence graph.

Если ZIP повторяет текст чата, это одна lineage, не два подтверждения истины. Если старый ZIP противоречит последней явной инструкции пользователя, instruction обновляет planned behavior, но не переписывает факты в source/test evidence.

## 5. Отсутствующие права/данные не выводятся из желания «всё автоматизировать»
Источник может быть AVAILABLE, PARTIAL, NOT_CAPTURED, UNSUPPORTED, DENIED, STALE или ERROR. Эти статусы повышают честность availability карты. Полнота относится к объявленному scope и snapshot, а не к «любой информации вообще». Нельзя наблюдением страницы гарантировать захват невидимой части истории.

## 6. Производственная граница
Reference lab — проверка алгоритмических contracts на synthetic data. Не готовый агент, не security sandbox, не streaming TB store, не real voice performance. В app существующий Core остаётся владельцем прав, очередь не дублируется. Реальный update сохраняет attestation/digest, permission diff, smoke test, one activation и ограниченный rollback.


---
Источник пакета: 01_CONTEXT/ALL_AIMS_AND_GOALS_RU.md

# Цели и ограничения чата

Реестр требований, а не утверждение о выполнении. Anchors — короткие цитаты или явно помеченные пересказы, не полный транскрипт.

## REQ-001 — Локальное личное приложение
Windows 11; библиотека и control plane локальны, не обязательный SaaS.

Источник: CURRENT_CHAT; anchor: local application

## REQ-002 — Голос и текст равноправны
Оба входа формируют один IntentSpec; фоновые голоса не считаются приказом.

Источник: CURRENT_CHAT; anchor: via text or or via your voice

## REQ-003 — Любой выбранный AI
Provider-neutral пакет + adapters; не привязывать память к Grok/OpenAI.

Источник: CURRENT_CHAT; anchor: for your AI of choice

## REQ-004 — Сохранение исходников
Raw bytes не заменяются summary/chunks; пути, IDs, время и источник сохраняются.

Источник: CURRENT_CHAT; anchor: entire history of my life

## REQ-005 — Нет лимита двадцати документов
Порции и бюджеты регулируют обработку; не скрывают хвост библиотеки.

Источник: RETRIEVED_PRIOR_USER_CONSTRAINT; anchor: more than 20 max docs remove

## REQ-006 — Семантический repo context
Repo map, symbols, dependencies, tests и history вместо ручной нарезки пользователем.

Источник: CURRENT_CHAT; anchor: this application could to chunk it

## REQ-007 — Несколько источников
ChatGPT/Grok exports, Google Docs exports, разрешённые private Telegram exports, Git.

Источник: CURRENT_CHAT; anchor: entire private Telegram channels

## REQ-008 — Library UI
Поиск, теги, граф целей, timeline, выбор исходников, completeness/omissions.

Источник: CURRENT_CHAT; anchor: library like Notion local application

## REQ-009 — Терминал и VS Code
Только зарегистрированные операции с рабочим проектом и областью файлов.

Источник: RETRIEVED_PRIOR_USER_CONSTRAINT; anchor: local terminal ... vs code

## REQ-010 — Документы для передачи AI
Короткое объяснение WHY_THIS_PACKET + полные ссылки на evidence + ожидаемый patch/test response.

Источник: CURRENT_CHAT_RU_PARAPHRASE; anchor: why this document should be passed to another AI

## REQ-011 — Продолжение Studious
Qualification/evidence/patch triage для BobIvans/studious-pancake. Не считать план действующим ботом.

Источник: CURRENT_CHAT; anchor: continue to work on our Studio Spancake flashloan bot

## REQ-012 — Восстановление решений
Старое предложение != новая команда; decision lineage/supersedes и даты.

Источник: CURRENT_CHAT; anchor: previous goals ... aggregated

## REQ-013 — Новая способность через код
Voice → context → AutomationSpec → coding agent → branch → tests → GitHub review → local skill update.

Источник: CURRENT_CHAT; anchor: renew the local application, renew the capabilities

## REQ-014 — Параллельные пути одной задачи
Диверсифицированные read/draft candidates; одна точка эффектов, independent verification.

Источник: CURRENT_CHAT; anchor: parallel actions would execute on same automation

## REQ-015 — Скорость и стоимость
Короткий fast path, delayed hedges, caching, budgets; не безусловный запуск всех моделей.

Источник: CURRENT_CHAT; anchor: fastest route to those aims

## REQ-016 — Подготовка во время речи
Только разрешённый read-only prefetch по устойчивой части транскрипта.

Источник: CURRENT_CHAT; anchor: lowest possible time

## REQ-017 — Измеряемая успешность
Verified completed / attempted, false-success отдельно; никаких обещаний 100% arbitrary GUI.

Источник: CURRENT_CHAT; anchor: highest sucess rate on execution

## REQ-018 — Безопасные маршруты
Не дублировать публикации/merge/удаления/trading; unknown effect требует reconciliation.

Источник: CURRENT_CHAT; anchor: multiple safe routes

## REQ-019 — Права не выдаёт модель
Typed route/LLM plan не расширяет scope; секреты остаются вне handoff.

Источник: ASSISTANT_PROPOSED_SAFETY_BOUNDARY; anchor: safely ... permissions

## REQ-020 — Accessibility-first
Stop/undo/correction/voice status; пользователь имеет приоритет над GUI worker.

Источник: CURRENT_CHAT; anchor: people with disabilities

## REQ-021 — Приватность
Локальный capture opt-in; public/private/sensitive, field-level cloud-export approval.

Источник: CURRENT_CHAT; anchor: hold any data locally

## REQ-022 — API budget
Провайдеры настраиваются по key references и явному лимиту расходов; ключи не включать в ZIP.

Источник: CURRENT_CHAT; anchor: use my api key

## REQ-023 — Evidence truth
Не путать source_fact, model_claim, implementation, tests, installed qualification, real market evidence.

Источник: DERIVED_ACCEPTANCE_CRITERION; anchor: highest successful ... execution

## REQ-024 — Без обязательного расширения
Desktop — основной интерфейс; Chrome может быть управляемым приложением/optional adapter.

Источник: RETRIEVED_PRIOR_USER_CONSTRAINT; anchor: remove wire to chrome extensions

## REQ-025 — Daily workflows
Повторяемые планы/исследования/документы/квитанции; расписания не стартуют от импорта.

Источник: CURRENT_CHAT; anchor: executions I need to do daily

## REQ-026 — R&D технологий
GitHub/Hugging Face/X разведка, первичные источники и локальные сравнения.

Источник: CURRENT_CHAT; anchor: new technologies ... hugging face

## REQ-027 — Вопрос о каталоге ChatGPT
Отдельный опциональный путь публикации; точная иконка неизвестна.

Источник: CURRENT_CHAT_RU_PARAPHRASE; anchor: insert a link to your service

## REQ-028 — Пакет продолжения
Два стартовых RU документа, JSON work items/workflows, tested offline reference.

Источник: CURRENT_CHAT; anchor: agregate bigger zip

## REQ-029 — Сохранить предыдущие идеи
18 прежних R&D и 129 функций остаются в legacy с происхождением и статусом.

Источник: CURRENT_CHAT; anchor: this entire chat aims and goals you outlined

## REQ-030 — Не заявлять недоступные данные
Исходный ZIP сохранён; более ранние архивы/полные приватные истории не получены здесь.

Источник: SCOPE_BOUNDARY; anchor: go thourgh our ideas and my inputs

## REQ-031 — Один владелец runtime
SCE Core/content.sqlite остаются owners; Studious владеет qualification, voice/Laya advisory.

Источник: RETRIEVED_PRIOR_DECISION_UNVERIFIED_IMPLEMENTATION; anchor: one evolving context/automation library

## REQ-032 — Прогрессивная полнота
Inventory/cursor/coverage/explicit exclusions; retrieval budget не ограничивает хранение.

Источник: CURRENT_CHAT; anchor: aggregate any context, any data

---
Источник пакета: 05_CONTRACTS/TAGGING_V3_RU.md

# Теги V3: не единственная плоская классификация

Детерминированные поля: source URI, object hash, full original path, source revision, offsets/message IDs, capture producer, observed/ingested times, MIME, size, ingest status. Эти поля нельзя «предсказывать» Laya, если источник уже даёт их точно.

Предлагаемые моделью поля: project candidates, entity spans, intent/goal, role (idea/requirement/decision/code/evidence), topic, likely duplicate, contradictions, relevance to this task. Каждый такой label имеет model/version, input hash, confidence/calibration scope и source span. Ненадёжный label — CANDIDATE, не authoritative fact.

Authority: USER_INSTRUCTION / SOURCE_CODE / OBSERVED_RESULT / THIRD_PARTY_CLAIM / ASSISTANT_PROPOSAL. Proposed future behavior отделён от фактического состояния.

Execution state: PLANNED, IMPLEMENTED_UNVERIFIED, OFFLINE_VERIFIED, DEVICE_VERIFIED, BLOCKED, STALE, SUPERSEDED. Переход к verified требует receipt того же commit/env/task, а не голосования summaries.

Availability: AVAILABLE, PARTIAL, NOT_CAPTURED, UNSUPPORTED, DENIED, MISSING_DEPENDENCY, STALE, ERROR. «Нет информации» не равно «информация ложная».

Context quality — вектор, а не один магический score: source authority, freshness, task relevance, required-slot coverage, integrity, contradiction count, provenance, privacy eligibility. Hard constraints сначала; ranker выбирает внутри допустимого множества.

Relations: requires, implements, tested_by, observed_in, derived_from, copied_from, contradicts, supersedes, blocked_by, repairs. Copies одного сообщения не становятся независимыми confirmations.

Для web3-контекста добавить chain/protocol/version/state reference/timestamp и evidence type (fixture, offline replay, paper observation). Read-only market data и live execution authority никогда не смешиваются одним `financial` tag.

User deletes/retention requests должны удалять соответствующие originals и derived indexes согласно policy. «Immutable» здесь означает отсутствие скрытой перезаписи истории, а не запрет пользователю управлять своей информацией.


---
Источник пакета: 12_EXPERIMENTS/ROUTE_PREDICTIONS_RU.md

# Прогноз fastest route — до измерений, не результат benchmark

| Задача | Ожидаемый fastest useful route | Дополение / hedge | Почему может быть лучше | Где ожидание может не сработать |
|---|---|---|---|---|
| Известная voice command | primary ASR → rules/registered skill | Laya для нескольких допустимых intents | Нет большого coding-model roundtrip | ASR путает критическое имя/отрицание |
| Запись работы с AI | UIA/DOM event text + Git/terminal events | exports для полных histories; screenshot только gap fallback | Не обрабатывать каждый pixel постоянно | UIA provider неполный; DOM выгружает старые сообщения |
| Repo bug handoff | exact symbol/error search + actual test trace | static graph + decisions/history | Evidence достаточно до полного reindex | Dynamic edges/untracked changes не индексированы |
| Неизвестная автоматизация | approved planner → isolated skill candidate | second independent candidate только после need/latency trigger | Не писать новый skill при каждом повторе | Слабые tests дают false success |
| Сложный patch | 2 isolated candidates при достаточном budget | independent negative/property tests | Разные error paths могут дополнить друг друга | Общий неверный contract ломает обе модели |
| Большой архив | raw store + metadata immediately | async/progressive enrich and semantic views | Нельзя ждать все embeddings до первого поиска | Storage saturation; incomplete labels |
| Разбор команды RU/EN | один тёплый выбранный multilingual path | second ASR на спорных spans | Меньше memory contention и model reload | Второй engine повторяет те же ошибки |
| Browser task | official API or stable DOM action | UIA/vision только если structured path недоступен | Короче action graph | Endpoint нет/доступ отозван/remote state изменился |
| Повторный AI запрос | cached validated snapshot + delta | exact fresh dependency retrieval | Не пересылаем всю библиотеку | Cache stale, tokenizer budgets или provider differences |

Ни одного измеренного p50/p95 или verified success rate Dell в этом пакете нет. Скорость выдачи сырого первого ответа не является скоростью получения правильного контекста.

## Три сравниваемых профиля
P0 LOCAL_FAST: rules + exact/FTS + current source snapshot; один ASR; no ensemble default.
P1 QUALITY_PARALLEL: P0 + graph/history/retrieval complement, independent evidence checks.
P2 RECOVERY_HEDGE: P1 + delayed alternative source/model/candidate при gap/error/latency evidence.

Начальные лимиты эксперимента (не измеренная оптимальность): отдельный high-priority voice/control lane; один heavy local inference одновременно; до двух heavy worker candidates только при наличии RAM; небольшой ограниченный I/O pool. Подобрать реальные лимиты по p95 и peak memory на Dell; не выдумывать «загрузить все модели и будет быстрее».

## Как сравнивать
На одном фиксированном корпусе команд и одинаковом allowed data scope случайно чередовать P0/P1/P2. Отдельно учитывать warm/cold, network loss, backend outage, corrupted snapshot, missing context, repeated command, mixed RU/EN, interrupted user input. Не оптимизировать и отчитываться на том же holdout.

Метрики: first-useful-context latency; complete-evidence latency; verified task completion; source-span precision/recall на размеченных задачах; false status promotion; coverage known/unknown; cost per verified success; resource contention; external duplicate effects; user focus interruptions; correction latency.

Каждый маршрут получает co-failure matrix и marginal recovery score. Математика `1−product(1−p_i)` применима лишь при независимых событиях успеха и адекватном verifier. Для UIA/DOM одного сайта и двух wrappers одного Python такие предпосылки не даны.


---
Источник пакета: 09_UPSTREAM/REUSE_EXISTING_OWNERS_RU.md

# Интеграция: расширять существующее, не строить второй control plane

## Что действительно прочитано
Три документа перечислены в `repository_document_reads.json` с blob SHA и URL. Это не полный аудит кода, не current main commit pin и не проверка CI. Их содержимое — документированный status, не результат нашего запуска.

## SCE
Сохраняем владельцев `content-lab/repo_context.py` (inventory/cursor), `repo_source.py` (static chunks/imports/SCC), `context_review.py` (review ledger), existing Core queue/leases/cancel/reconciliation и `content.sqlite3`.

Desktop должен подключаться к выделенному локальному service/API с теми же owners. Tauri — возможная оболочка, а не основание переписать всю систему на Rust. Native Chrome transport может остаться legacy adapter, но не обязательным путём GUI нового app.

Documented constraints: 20 entries — размер страницы/порции scan, не 20 документов на всю библиотеку; 8 MiB blob limit и 32 MiB Git inventory output limit дают explicit ERROR; export имеет 10 text chunks/24k byte planning budget/80k document budget. Миграция: streaming inventory/blob ingest, bounded memory, resumable spool и user-configurable handoff budget. Не удалять timeout/security/resource checks просто ради слова unlimited. Scanned/stored/exported coverage показываются отдельно.

Code intelligence сейчас, согласно документу, Python/static; JS TEXT_ONLY, dynamic/external edges unresolved. Поэтому Tree-sitter/SCIP — optional bounded migration с pins/packaging/offline cache, а не уже существующий полный call graph.

## Studious
Поддерживаемые inspection entrypoints в прочитанном README: `flashloan-bot status --json`, `flashloan-bot capabilities --json`. Их здесь не запускали. `paper-shadow` может требовать внешних verified dependencies; режим paper не означает отсутствие сети. Live/signing/sending не включать в этот R&D pack.

Qualification authority остаётся в Studious. App читает structured status/receipts и вызывает только registered approved template после отдельного preflight. Не изобретать universal `run_qualification_suite` команду без сверки существующих CLI/tests/workflows.

## Контракты следующего PR
Точечные changes ниже сначала сопоставить с current exact commit и code owners. Имя функции из backlog не доказательство missing implementation. Никакие GitHub записи/PR/merge этим ZIP не выполнены.
