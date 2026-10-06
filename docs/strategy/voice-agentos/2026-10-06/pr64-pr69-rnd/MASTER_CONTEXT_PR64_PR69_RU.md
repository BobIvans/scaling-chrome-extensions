# Voice AgentOS R&D: PR64–PR69 — MASTER CONTEXT

Дата фиксации: 2026-10-06  
Репозиторий: `BobIvans/scaling-chrome-extensions`  
Implementation baseline: `main@06fbd2f31776690a2b15888d8ab0dff9dd47961f` — после merge PR #62 (Fast Decision V8) и PR #63 (Persistent H2/H1/H0 Mission Runtime V8).

## 1. Цель пакета

Этот пакет — канонический R&D/implementation handoff для следующей шестёрки PR. Он не заменяет старый Voice AgentOS master-roadmap, а конкретизирует ближайшую линию развития после #62/#63:

`#64 Durable Parallel Execution V9` → `#65 Capability Canary → REGISTERED → Waiting Goal Resume` → `#66 Provider-Neutral System-2 Registry` → `#67 Qualified Effectful AI-Site Runtime` → `#68 Release Artifact + Qualified Activation + Reconnect` → `#69 Unified Mission/Library Timeline UI`.

Главная продуктовая цель остаётся прежней: локальный AgentOS — мозг, память, authority, mission runtime и lifetime Library; Chrome — скрытый capability driver; Windows UIA — второй UI driver; Laya — быстрый System-1; System-2 providers — сменные reasoning/coding workers; Core — единственный владелец effect authority, durable jobs, STOP, leases, reconciliation и evidence.

## 2. Что уже реально есть в baseline

- `local-agent/fast_decision.py`: настоящий concurrent prefetch через `ThreadPoolExecutor`, измерение latency, utility ranking, `parallel_plan()` для safe disjoint lanes.
- `content-lab/goal_runtime.py`: durable GoalState, H2, H1, один H0, revisions, ProgressDelta, effect/dependency gates.
- `local-agent/persistent_mission.py`: reopen goal, checkpoint pending System-2/Core job, restart resume, rebuild frontier.
- `content-lab/campaign_runtime.py` + `workflow_state.py`: DAG dependencies, READ/WRITE resource leases, capacity/demand, SAVEPOINT admission, UNKNOWN reservation/reconciliation.
- `content-lab/automation_core.py`: canonical jobs/STOP/cancel/reconciliation/worker, но политика всё ещё требует `max_parallel == 1`, а `Core.claim()` глобально сериализует RUNNING/NEEDS_RECONCILIATION.
- `local-agent/site_adapter.py`: уже есть важный effectful substrate — local registry, qualification digest, exact site binding, prepare, outbox, `effect_begin`, `send_once`, `reconcile_operation`, UNKNOWN effect handling. PR67 обязан завершать/квалифицировать этот owner, а не строить второй adapter runtime.
- `local-agent/self_renew.py` и `content-lab/release_updater.py`: verified staging и isolated qualification activation существуют; unattended production activation намеренно заблокирован.
- `desktop/app.py` / `desktop/library.py`: локальные UI surfaces существуют, но нет unified mission + Library + relations/backlinks + live parallel-lane timeline.

## 3. Главный обнаруженный архитектурный разрыв

У нас уже есть **parallel observation/planning/admission primitives**, но ещё нет **end-to-end durable parallel execution**.

Текущая ситуация:

1. Fast Decision может выбрать несколько независимых lanes.
2. Campaign runtime способен enqueue несколько независимых nodes и зарезервировать disjoint resources.
3. Persistent Mission умеет переживать restart, но хранит по сути один pending System-2/Core job path.
4. Core worker остаётся глобально serial: `validate_policy()` требует `max_parallel == 1`; `claim()` отказывается запускать новый job, если любой job RUNNING или NEEDS_RECONCILIATION.

Следовательно PR64 — не косметическая оптимизация. Это мост от «параллельно придумали/запланировали» к «параллельно исполняем, crash-safe, resource-safe, restart-safe, first-useful-evidence driven».

## 4. Канонические invariants PR64–PR69

Ни один из PR не имеет права нарушить следующие правила:

1. **One authority:** SQLite/Core остаётся authority. UI, Laya, browser page, AI result и provider plugin — не authority.
2. **One writer per mutable resource:** один composer/tab, один Git branch/worktree, один install pointer, один wallet/effect owner — сериализуются.
3. **Parallel where disjoint:** Library READ, repo read-analysis, independent providers, independent simulations и разные immutable resources могут идти параллельно.
4. **STOP wins:** durable STOP запрещает новые admissions и fences running owners. Никакой local worker/provider не обходит STOP.
5. **Unknown is not retry permission:** UNKNOWN effect блокирует конфликтующий resource до reconciliation; не создаёт слепой повтор.
6. **Restart is normal:** каждый long-lived lane имеет durable identity/checkpoint и может быть inspected/resumed/reconciled после crash/restart.
7. **Evidence before claim:** «job finished», «AI said DONE», «page changed» или «PR merged» не равны product acceptance без independent evidence.
8. **No duplicate runtimes:** не создавать новый queue, новую mission DB, второй resource manager, второй updater или второй site adapter, если существующий owner можно расширить.
9. **Foreground human ownership:** браузер/Windows foreground mutation всегда уступает человеку.
10. **Device qualification separate:** CI/local tests не являются доказательством installed Windows/Chrome/account/device qualification.

## 5. PR sequence

| PR | Название | Главная цель | Blocker для следующего |
|---|---|---|---|
| #64 | Durable Parallel Execution V9 | Сделать parallel lanes реально исполняемыми и restart-safe | Нужен для безопасного fan-out System-2 и long missions |
| #65 | Capability Canary → REGISTERED → Goal Resume | Автоматически довести GapSpec/candidate до зарегистрированного skill и разбудить waiting goal | Нужен для self-growth |
| #66 | Provider-Neutral System-2 Registry | Единый durable request/result contract для Codex/web/headless/API/local providers | Нужен для multi-provider parallel reasoning |
| #67 | Qualified Effectful AI-Site Runtime | Закрыть exact identity/composer/send/reconcile/response contracts и device qualification path | Нужен для browser providers с effects |
| #68 | Release Artifact + Qualified Activation + Reconnect | Версионированный artifact, predecessor/STOP/device gates, activation/rollback/rebind/resume | Нужен для безопасного self-update |
| #69 | Unified Mission/Library Timeline UI | Library/Conversations/Repos/Context/Missions + relations/backlinks + lane timeline | Делает систему наблюдаемой и управляемой человеком |

## 6. Что НЕ входит в этот пакет

- PR70 Studious Pancake full parallel paper/simulation qualification — следующий domain campaign после PR69.
- Никакая торговля/live wallet effect не включается этим roadmap.
- Не утверждается DEVICE_QUALIFIED для Dell/Windows/Chrome/accounts.
- Не включается «автоматически merge/install everything» без явных grants и receipts.
- Не заменяется текущая canonical Library model context-ом.

## 7. Source of truth для Codex

Перед реализацией каждого PR Codex обязан прочитать:

1. Этот `MASTER_CONTEXT_PR64_PR69_RU.md`.
2. `CODEX_START_HERE_PR64_PR69.md`.
3. Документ конкретного PR.
4. `CURRENT_GAP_AUDIT_RU.md`.
5. `ACCEPTANCE_MATRIX_PR64_PR69.json` и `IMPLEMENTATION_DAG_PR64_PR69.json`.
6. Текущий `main`, текущие tests/workflows и live GitHub state — номера/SHA из этого пакета являются baseline snapshot, а не вечной истиной.

## 8. Definition of done для всей волны

Волна PR64–PR69 считается реализованной только если:

- parallel lanes не только планируются, но реально работают одновременно при disjoint resources;
- crash/restart/lease expiry/STOP/UNKNOWN не создают double effects;
- first useful evidence может re-rank frontier и отменить лишние lanes;
- missing capability способен пройти candidate → tests → canary → REGISTERED и waiting goal продолжится;
- System-2 provider заменяем без изменения mission semantics;
- effectful AI-site send имеет exact identity + draft readback + send-once + reconcile;
- production activation требует реальных predecessor/STOP/device receipts, умеет rollback и reconnect;
- UI показывает canonical live state, но не получает authority;
- все applicable CI gates green на exact PR heads;
- device gates остаются честно NOT_RUN/OPEN до реального устройства.
