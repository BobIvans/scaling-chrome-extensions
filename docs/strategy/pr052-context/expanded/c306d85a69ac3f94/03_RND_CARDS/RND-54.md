# RND-54 — Whole-conversation strategy merge
**Статус:** new_detail; proposed R&D, не установленная интеграция.

## Зачем
ZIP, текст чата и recovered notes могут содержать дубликаты и противоречивые устаревшие планы.

## Устройство
Canonical requirement IDs + original refs; latest explicit user instruction overrides prior proposal; no auto-closing based on assistant claims.

## Эксперимент
Импорт legacy ZIP и текущего уточнения multi-recorder; сверить inherited single-writer language.

## Acceptance
Новая стратегия соблюдает multi-producer capture и сохраняет безопасные effect boundaries.

## Функции
- `ingest_strategy_artifact_graph()`
- `link_chat_requirement_to_archive()`
- `reconcile_strategy_precedence()`
- `compile_one_provider_neutral_master_handoff()`

Requirements: REQ-037 REQ-039. Sources: S16.
