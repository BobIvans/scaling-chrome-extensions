# Codex: ROADMAP PR-012 + PR-013 / GitHub PR #51

Для продолжения **Unified source lifecycle** открыть
[docs/strategy/pr012-013/CODEX_START_HERE.md](docs/strategy/pr012-013/CODEX_START_HERE.md)
и [MASTER_CONTEXT.md этого пакета](docs/strategy/pr012-013/MASTER_CONTEXT.md).
Ветка: `codex/pr012-013-source-ledger-continuation`; #47 уже merged,
#51 продолжает source lifecycle, полный scope остаётся OPEN.
Следующий checkpoint: unified SourceAddress/read adapters поверх текущих raw
owners, затем durable Core repo/capture jobs. Оригинальная общая навигация ниже
сохранена; номер ROADMAP №012/013 не является GitHub №12/13.

# Codex: начать здесь

Цель и источник требований: `MASTER_CONTEXT.md`.
Полная стратегия уже находится в `docs/strategy/voice-agentos/`; повторный ZIP
upload не нужен для всех материалов, предоставленных в этой передаче.

1. Прочитай repository instructions, `MASTER_CONTEXT.md`,
   `docs/strategy/voice-agentos/handoff/NEXT_STAGE.md`,
   `handoff/PACKAGE_STATUS.json`, `handoff/WORKSTREAM_STATUS.json`.
2. Выполни `git fetch origin`, проверь текущие main и PR #49/#51/#52,
   companion `BobIvans/studious-pancake#565` и их актуальные CI.
   Audit — dated snapshot. Уже merged код не реализуй повторно; активные
   ветки не переписывай и не force-push.
3. Проверь сохранность источников:
   `python docs/strategy/voice-agentos/verify_integrity.py`.
4. Читай `roadmap/briefs/PR_010.json`, `PR_011.json`,
   `roadmap/plan/DELIVERY_DAG.json`, полные task/feature records по исходным
   IDs, исходные acceptance и текущие owners. Старые номера prose не заменяют
   текущий workstream mapping.
5. Следующий этап — интеграция source ledger #51 с context/Core #50,
   единый versioned SourceAddress №010 и точные read/search adapters. Продолжай
   существующий PR/branch, если он актуален; если уже merged, реализуй только
   фактический остаток. Scope и acceptance подробно в `NEXT_STAGE.md`.
6. Сохраняй existing SQLite/Core/native/Desktop owners, compatibility,
   exact bytes/revisions и полный traversal до EOF. Обнови installer/owned
   manifests при shipping changes. Проверь scope/hash/ranges, restart,
   ack loss, STOP/cancel и source drift применимыми независимыми fixtures.
7. Прогони gates текущего workflow, проверь CI актуального commit и merge.
   Запиши changed functions, фактические receipts, остаток и следующий stage
   в `handoff/`. Полную стратегию не сокращай и не объявляй завершённой
   по одному merge/тесту/AI result.

Для любого следующего package читай соответствующий `briefs/PR_NNN.json`,
полный `prompts/PR_NNN_CREATE_BIG_ZIP_RU.txt`, исходные V5 records и
`coverage/`. Выполнять написание нового ZIP перед кодом не обязательно:
все предоставленные inputs теперь доступны непосредственно из repo.
