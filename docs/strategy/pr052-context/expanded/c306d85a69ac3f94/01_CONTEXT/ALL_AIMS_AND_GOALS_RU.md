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