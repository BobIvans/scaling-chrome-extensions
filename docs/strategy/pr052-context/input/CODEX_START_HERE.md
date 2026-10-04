# Codex continuation — concrete remaining repairs

1. Распакуй ZIP в `docs/strategy/pr001-021-merge-repair/` текущего repo, сохрани оригиналы.
   Прочитай MASTER_CONTEXT, findings, merge sequence, FIX_PLAN и применимые AGENTS.md.
   Run `python docs/strategy/pr001-021-merge-repair/tools/verify_bundle.py`.
2. Fetch actual main и heads #52/#565, сопоставь со snapshot. Проверяй новые merged
   source-address/adapters прежде чем писать их повторно. Не перезаписывай чужую worktree.
3. FIX-001: current index отражает merged #49/#51 и остаток 010/011/012/013;
   historical source plans/snapshots остаются immutable.
4. FIX-002: продолжай существующий `codex/pr020-021-research-qualification` (#52)
   в isolated worktree. Интегрируй main и все 9 conflicts по named file recipes,
   сохрани Core action/context/campaign/STOP и added research routes. Обнови shipping
   manifest/hashes и exact owner pins. Validate meaningful integration gates.
5. FIX-003: выполнить полный сохранённый PR010_011 plan, начиная с shared SourceAddress
   и exact scoped raw adapters. Затем importer registry/search/labels/goals, JS/TS
   resolver/mixed graph. Не повторять source ledger #51 или static baseline #43/#46.
6. FIX-004/005: durable Core capture/repo jobs, all pages/cache invalidation и document/
   media/web importers; квалифицировать downstream contracts на общем build.
7. FIX-006: оставить реальные device/provider/semantic gates с owner и next evidence
   пока receipts отсутствуют; выполнять доступные code/CI work автономно. Не считать
   unavailable hardware proof выполненным по synthetic logs.
8. After each stage update actual implementation/criteria/next step, run current
   required gates and record final source/build/CI identities. Сохранить все 21 пакета
   и все исходные требования, без arbitrary total-corpus limits.

Начни с проверяемого integration checkpoint, затем продолжай foundation.
ZIP не содержит уже выполненного repair patch; conflicted projections — evidence only.
