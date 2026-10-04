# RND-46 — Evidence-ready streaming handoff
**Статус:** refinement; proposed R&D, не установленная интеграция.

## Зачем
Не ждать «всю жизнь проиндексировали», прежде чем попросить AI исправить одну функцию.

## Устройство
Именованные required evidence slots; snapshot freeze; первая достаточная version; поздние данные — delta с parent digest.

## Эксперимент
Запросить patch до окончания full archive import; позже вернуть contradicting current source.

## Acceptance
Missing critical evidence блокирует ready; существенный delta отзывает stale patch.

## Функции
- `compute_minimum_evidence_frontier()`
- `freeze_handoff_revision()`
- `emit_late_evidence_delta()`
- `invalidate_result_after_material_delta()`

Requirements: REQ-038 REQ-010. Sources: S09 S16.
