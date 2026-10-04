# RND-40 — Cross-AI exchange contract

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Отправлять моделям один task contract, а не одинаково весь личный архив.

## Архитектурное изменение
Task ID, snapshot, context digest, allowed sources, expected response schema; chosen provider receives redacted scoped slice; return patch not direct merge.

## Конкретный эксперимент
Два model adapters + manual exported document; импорт неправильного snapshot и test claim.

## Критерий принятия
Одинаковая target binding; private data не уходит неразрешённому provider; imported DONE не закрывает задачу.

## Функции
- `compile_provider_scoped_handoff()`
- `validate_ai_return_contract()`
- `bind_ai_patch_to_snapshot()`
- `merge_model_evidence_without_effects()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-003 REQ-010 REQ-013 REQ-021. Первичные источники/технические предпосылки: S16. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
