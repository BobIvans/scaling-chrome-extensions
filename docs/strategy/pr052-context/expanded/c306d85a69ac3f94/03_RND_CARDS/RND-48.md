# RND-48 — Context request-response protocol
**Статус:** new; proposed R&D, не установленная интеграция.

## Зачем
Пакет может не знать заранее, какой dependency нужен следующей модели.

## Устройство
AI возвращает typed NEED_CONTEXT(symbol/path/date/reason), локальный compiler исполняет scoped retrieval и выдаёт delta.

## Эксперимент
Модель обнаруживает missing interface; сравнить весь repo resend с exact code dependency retrieval.

## Acceptance
Source-bound response, lower irrelevant bytes, незапрошенные private roots не раскрываются.

## Функции
- `parse_ai_context_request()`
- `resolve_requested_symbol_context()`
- `enforce_context_request_scope()`
- `return_context_delta_receipt()`

Requirements: REQ-040 REQ-003. Sources: S09 S16 S26.
