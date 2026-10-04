# RND-51 — Late arrivals and evidence watermarks
**Статус:** new; proposed R&D, не установленная интеграция.

## Зачем
Источники приходят с разной задержкой; временной порядок не является причинностью.

## Устройство
Per-producer monotonic seq + source version + observed/ingested time; gaps и watermarks; late evidence не отбрасывается.

## Эксперимент
Перепутать arrival order, повторить событие, сменить source version.

## Acceptance
Никакого last-arrival-wins для истории решений; timestamps не склеивают разные commits.

## Функции
- `track_producer_watermark()`
- `detect_capture_sequence_gap()`
- `associate_causal_source_version()`
- `reprocess_late_evidence_revision()`

Requirements: REQ-033 REQ-038. Sources: S14.
