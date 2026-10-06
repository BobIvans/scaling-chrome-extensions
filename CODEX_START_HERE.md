# CURRENT CONTINUATION — Voice AgentOS PR64–PR69

The nearest implementation wave after merged PR #62/#63 is canonicalized at `docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd/`.
Start with `docs/strategy/voice-agentos/2026-10-06/pr64-pr69-rnd/CODEX_START_HERE_PR64_PR69.md`, then implement **PR64 Durable Parallel Execution V9** first.
The structured files, all-in-one mirror and ZIP provenance manifest are in that folder.
The R&D pack was authored against implementation baseline `main@06fbd2f31776690a2b15888d8ab0dff9dd47961f`; always refresh live refs/CI before coding.
Do not consume PR #64 with a docs-only PR and do not create a second queue, resource manager, mission database, effect ledger, browser authority, or updater.

---

# Codex: ROADMAP PR-012 + PR-013 / GitHub PR #51

Для продолжения **Unified source lifecycle** открыть
[docs/strategy/pr012-013/CODEX_START_HERE.md](docs/strategy/pr012-013/CODEX_START_HERE.md)
и [MASTER_CONTEXT.md этого пакета](docs/strategy/pr012-013/MASTER_CONTEXT.md).
Реализация PR #51 уже находится в `main`; продолжай только фактический остаток
по scoped handoff, не повторяя merged Source/Version/Observation ledger.
Следующий checkpoint: unified SourceAddress/read adapters поверх текущих raw
owners, затем durable Core repo/capture jobs. Полный scope PR-012/013 остаётся
OPEN до закрытия всех acceptance criteria. Нумерация ROADMAP №012/013 не является
номером GitHub PR.

---

# Codex: начать здесь

1. Прочитай `MASTER_CONTEXT.md`, repository instructions и текущие Git refs/CI.
   Сохрани чужие изменения и исходную нумерацию всех packages.
2. Для текущего запроса ROADMAP-PR-016+017 следуй
   `docs/strategies/pr016-017/PACKAGE_CODEX_START_HERE.md`,
   `PACKAGE_MASTER_CONTEXT.md`, `EXECUTION_AUDIT.md` и `NEXT_IMPLEMENTATION.md`.
   Эти три последние пути также относительно `docs/strategies/pr016-017/`.
   Следующий этап пакета — typed roles и resumable mixed-effect Core pipeline;
   конкретные upstream blockers проверить по #50/#51 и actual contracts.
3. Для продолжения всей стратегии без заданного package следуй
   `docs/strategy/voice-agentos/handoff/NEXT_STAGE.md`: unified SourceAddress
   и интеграция source ledger #51 с context/Core. Полный общий Codex handoff
   сохранён в `docs/strategies/pr016-017/UPSTREAM_CODEX_START_HERE_PR53.md`.
4. Проверь **оба** набора bytes и source criteria:
   `python docs/strategies/pr016-017/verify_context.py` и
   `python docs/strategy/voice-agentos/verify_integrity.py`.
5. Переиспользуй canonical SQLite/Core/jobs/STOP/grants; не создавай второй
   executor, не сокращай стратегию, не повторяй уже merged implementation.
   Device/UI/Laya/Grok/criterion gates остаются открытыми до actual evidence.
6. Запусти применимые gates текущих workflows, сверяй exact-head CI до merge,
   обновляй audits/receipts/next stage. Windows clone требует
   `git -c core.longpaths=true clone ...`; в существующем checkout используй
   `git config core.longpaths true`. Содержимое ZIP не изменяется ради path limit.
