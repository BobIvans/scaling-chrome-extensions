# Исправление существующего GitHub PR #52

Title: ROADMAP PR-020 + PR-021: Core research, Desktop receipts and criterion reconciliation.
URL: https://github.com/BobIvans/scaling-chrome-extensions/pull/52
Branch: `codex/pr020-021-research-qualification`.
Main: `7253c40398905967ade0541717bcbfac25fec5b9`; PR head: `3c6bf81e1345f91454ae87cccec2c3cd7c3d84a6`; merge base: `b0a06f26106cb4739d8cf3465a4ad8941c328f40`.
GitHub сообщил mergeable=false; local merge-tree независимо подтвердил 9 paths.

До изменений получить актуальные refs; проверить AGENTS.md и сохранить чужую работу.
Использовать изолированный worktree текущей #52 и интегрировать actual main.
Не переносить весь старый patch на новую ветку как готовый результат.
`evidence/conflicted-projections/` — проекции неудавшегося merge с markers,
не готовые shipping файлы и не патч для применения. `evidence/pr52/` — exact-head
файлы предложения; `evidence/main/` — selected actual-main anchors.

### 1. `agent-bridge/Install.ps1`

Union the actual sibling files: preserve action_intent/action_runtime/browser_cdp/action_cli and source_ledger from current main; add research_bridge/product_qualification. Preserve existing context modules copied by the separate SHIPPING loop. Verify both installed layouts.

### 2. `agent-bridge/durable.mjs`

Keep durable.action and add durable.research.jobs; retain the union of the fields schemas and validation/transport branches. Do not widen unknown caller fields or remove existing history/scan/library routes.

### 3. `content-lab/automation_core.py`

Keep two distinct validate_job branches for action_plan and studious_research with each original strict schema and return. Preserve both execution branches, leases, cancellation and shared STOP. A union of field sets in one branch is incorrect.

### 4. `content-lab/context_runtime.py`

Union SHIPPING with action and research modules. Recompute build qualification against the final installed file set. Treat source_ledger inclusion as an explicit shipping decision whenever Desktop starts consuming it; current standalone capture is not evidence of Desktop support.

### 5. `content-lab/native_adapter.py`

Preserve both FIELDS entries and two complete dispatch branches, each with its own typed result key and return. Audit DESKTOP_READS/profile capability gates, research snapshot fencing, action authority and existing context/STOP controls.

### 6. `desktop/OWNED_FILES.json`

Regenerate every hash from final actual bytes using desktop/package.py manifest. Preserve all owned shell files. Never choose old hashes from one side or claim source_sha is a final tree digest.

### 7. `desktop/app.py`

Retain actions and context/library panels and add the research button/state logic. Exercise both branches after reconnect and preserve separate STOP/cancel UX.

### 8. `desktop/client.py`

Union request allowlists, capabilities and strict response DTO validation for action and research. Preserve namespace/profile scoping, pagination/snapshot fences and transport cancellation.

### 9. `desktop/install.py`

Union BACKEND_FILES with all action and research dependencies; align it with context_runtime.SHIPPING. Keep source_ledger/native compatibility explicit. Verify installed -I invocation, shared Core and manifest/build hashes.

## Автоматически merged участки тоже проверить

`.github/workflows/deterministic-core.yml`, Desktop README и новые job execution
branches могли объединиться текстово без конфликта. Проверить все изменения,
а не только 9 marker blocks. В #52 уже есть branch для research run; current main
содержит action run. Их совместная validation/dispatch, STOP и profiles должны работать.
Команда `desktop/package.py manifest` создаёт manifest по конечным bytes; использовать
актуальный CLI из этого repo и затем `verify --shell desktop`.

## Минимальные acceptance regression cases

1. Одна заполненная SQLite DB/policy: action, context, campaign, research co-exist.
2. Native/stdio request routes проверяют typed schemas и scope, current snapshot
   pagination до EOF; неизвестные поля и stale refs дают явный отказ.
3. Installed Native sibling layout и actual Desktop bundle работают под `python -I`:
   action INFO/CREATE/ENQUEUE + Core worker, research jobs + pinned replay,
   context qualification и независимый STOP. Вызовы используют existing fixtures
   и registered offline profiles без новых внешних effects.
4. STOP с любой панели запрещает новые jobs каждого типа; resume не оживляет
   cancelled jobs и не скрывает неизвестный effect/старый worker.
5. Все source bytes/criteria integrity tests, generated owned/build hashes и текущие
   Ubuntu/Windows exact-head CI gates проходят после conflict resolution.
6. Exact Studious owner остаётся compatible и pinned; rebase companion не заменяет
   pin без нового связанного replay. Merge SCE slice при отсутствии deployed companion
   оставляет именованную недоступную capability; product closure не объявляется.

Зелёный pre-integration CI `3c6bf81e1345f91454ae87cccec2c3cd7c3d84a6` не переносится на новый commit.
После fresh source/build drift ожидается новая qualification, а не отключение проверки.
