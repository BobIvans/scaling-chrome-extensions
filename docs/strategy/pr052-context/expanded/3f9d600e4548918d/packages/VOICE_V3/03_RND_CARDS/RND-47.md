# RND-47 — Authority-separated tagging lanes
**Статус:** refinement; proposed R&D, не установленная интеграция.

## Зачем
Текст идеи, желание пользователя и фактический test receipt нельзя сводить одним уверенным labeler.

## Устройство
Lane A deterministic provenance; B user intent/requirements; C model proposals; D measured code/test state; сохранять conflicts.

## Эксперимент
Один AI говорит implemented, другой docs говорит planned, actual tests отсутствуют.

## Acceptance
Статус остаётся NOT_VERIFIED; majority summaries не порождает DONE.

## Функции
- `label_source_authority_lane()`
- `distinguish_intent_from_world_state()`
- `preserve_label_disagreements()`
- `require_evidence_for_status_promotion()`

Requirements: REQ-037 REQ-012. Sources: S06 S08.
