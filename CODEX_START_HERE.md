# Codex Start Here — ROADMAP PR-016+017 / исходный GitHub PR #49

**Цель:** продолжить «PR-016 + PR-017: Core voice/delivery/skills baseline and
full Codex strategy handoff» в `BobIvans/scaling-chrome-extensions`.
**Ветка:** `codex/pr016-017-codex-continuation-20261004`.
**Сохранённый progress:** exact source head #49
`9a4fd3acb4ac66a14a55656f60a4d0727a378fcd`, весь выполненный код и полный ZIP.
**Первый implementation stage:** typed roles и resumable mixed-effect
`repo → canonical immutable packet → selected-target delivery` через существующий Core.

## 1. Установить текущее состояние

Прочитай применимые `AGENTS.md`; зафиксируй status/branch/HEAD и сохрани чужие
изменения. Fetch текущие main/#49/#51 и сравни их с fork point, поскольку другие
сессии могут продвигать repository. На Windows включи `core.longpaths`:

```sh
git config core.longpaths true
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin main codex/pr016-017-intent-voice-delivery-skills codex/pr012-013-source-ledger-continuation
```

Работай на указанной continuation branch. Для нового Windows checkout:

```sh
git -c core.longpaths=true clone --branch codex/pr016-017-codex-continuation-20261004 https://github.com/BobIvans/scaling-chrome-extensions.git
```

Старый PR #49 attached к другой branch; commits новой ветки его автоматически
не обновляют. Сначала live-check его status/CI. Если #49 уже merged либо обновлён,
сравни diff и интегрируй необходимый upstream с сохранением обоих progress.
Не повторяй baseline. Эта передача не выполняла merge, retarget или новый PR.

## 2. Читать контекст и исходную стратегию

1. Root `MASTER_CONTEXT.md`: package/PR identity, source priority и полный общий roadmap.
2. `docs/strategies/pr016-017/handoff/CONTINUATION_PROGRESS.md` и `.json`:
   fresh audit, owners/hashes, точные tests/CI, выполненное и remaining.
3. `docs/strategies/pr016-017/NEXT_IMPLEMENTATION.md`: полный первый этап;
   `PACKAGE_MASTER_CONTEXT.md`, `EXECUTION_AUDIT.md`, `FUNCTION_AUDIT.json`,
   `VALIDATION.json`: полный inherited scoped handoff.
4. В `docs/strategies/pr016-017/source/`: `01_PR_DESCRIPTION_RU.md`,
   `02_IMPLEMENTATION_RU.md`, `03_FUNCTIONS_RU.md`, `contracts/`, `schemas/`,
   `plan/PR_PLAN.json`, `plan/DEPENDENCIES.json`, `plan/CURRENT_VS_PLANNED.json`,
   `acceptance/CRITERION_COVERAGE.json`, `acceptance/ACCEPTANCE_CASES.json`,
   `04_WINDOWS_QUALIFICATION_RU.md`, `05_MIGRATION_ROLLBACK_RU.md`.
5. Runtime runbooks в `docs/automation/pr016-017/`: `README_RU.md`,
   `QUALIFICATION_RU.md`, `FUNCTIONS_IMPLEMENTATION.json`, `CRITERION_COVERAGE.json`.
6. Полный backlog в `source/sources/numbered_roadmap/`, exact master extracts в
   `source/sources/master_exact_members/`, все nested originals в `archives/`.
   Общая стратегия из #53: `docs/strategy/voice-agentos/`, её root handoffs
   сохранены в `docs/strategies/pr016-017/UPSTREAM_*_PR53.md`.

Чтение порциями допустимо; это не сокращение scope. Сохраняй все task/feature/
decision/goal IDs, original criterion wording и deferred/revisit cards.
Исторические source statuses не переписывай как current progress.
Отдельный 387 MB master не был приложен; его selected extracts и hash сохранены.

## 3. Реализовать следующий этап поверх готового кода

Baseline owners: `content-lab/action_intent.py`, `action_runtime.py`,
`browser_cdp.py`, `automation_core.py`, `workflow_state.py`, `native_adapter.py`;
`desktop/voice.py`, `actions_ui.py`, `client.py`; `agent-bridge/durable.mjs`.
Actual packet owners merged #50: `context_library.py`, `context_packets.py`,
`context_runtime.py`, `context_recovery.py` внутри `content-lab/`.

Выполни весь `NEXT_IMPLEMENTATION.md`: versioned EvidenceBundle/PlanProposal/
CriticVerdict; typed producer/output references и per-step effect admission;
durable step inputs/outputs/checkpoints в той же SQLite; canonical packet bridge;
resumable mixed-effect Core job; Desktop/Native preview/status/correction/resume.
Перед effect перечитывай revision/STOP/policy/source/target/lease authority.
SEND_ARMED/possible-send crash остаётся UNKNOWN до reconciliation, без blind resend.

Используй one canonical SQLite/Core queue/jobs/leases/writer/STOP и installed
capability/grant/version gates. Actual SourceAddress/#51 prerequisite фиксируй
на конкретном зависимом adapter; независимые typed planning части продолжай.
Source content и AI responses остаются data/proposals, не создают grants.
Не добавляй arbitrary ceilings числа repo bytes/files/documents/parts; pagination,
backpressure и resource budgets должны обеспечивать continuation до EOF.

После этого продолжай полный remaining пакет: actual provider upload/history/
finalization, parameterized portable skills/selective requalification, installed
Laya, Windows/Dell device corpus и все applicable original criterion receipts.
Каждый scoped code stage подтверждай своим evidence. 220 criteria остаются OPEN
до criterion-specific verification; fixtures/CI не заменяют real device/UI.

## 4. Проверки, актуализация handoff и завершение

До code changes проверь сохранность:

```sh
python docs/strategies/pr016-017/verify_context.py
python docs/strategy/voice-agentos/verify_integrity.py
python -I -X utf8 desktop/package.py verify --shell desktop
```

После implementation: independent cases из `NEXT_IMPLEMENTATION.md` и исходного
acceptance, включая real Git/SQLite to EOF, >20 sources, stale/foreign/cycle refs,
restart на каждом step, correction/STOP/drift и lost-send-ack без duplicate.
Затем применимая регрессия действующего `.github/workflows/deterministic-core.yml`:

```sh
python -m unittest discover -s content-lab -p 'test_*.py' -q
python -m unittest discover -s desktop/tests -p 'test_*.py' -q
python -I -X utf8 desktop/package.py verify --shell desktop
node --test agent-bridge/*.test.mjs
python -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py' -q
node --test one-click-context/tests/*.test.*
git diff --check
```

Tk tests на Linux требуют Xvfb; display skips обозначать явно. Изменённые shipping
files включить в installers/owned manifest/backend digests. Обновляй progress,
function/criterion evidence, validation и next stage без изменения source bytes.
Publish/code PR/merge выполняй по текущей пользовательской инструкции coding-сессии;
перед merge сверяй tested head и actual exact-head CI. Old-head checks не authority
для нового commit. Current branch alone не запускает все PR workflows автоматически.

Если задача относится ко всему roadmap без конкретного package, используй
`docs/strategy/voice-agentos/handoff/NEXT_STAGE.md` (SourceAddress/source-ledger
integration), сохраняя отдельный scope 016/017. Предыдущий root START #49 целиком:
`docs/strategies/pr016-017/handoff/PR49_CODEX_START_HERE.md`.
