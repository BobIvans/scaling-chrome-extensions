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
