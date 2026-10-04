# RND-36 — Lineage-aware dedup and evidence diversity

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Пять пересказов одного сообщения — один источник, а не пять подтверждений.

## Архитектурное изменение
Exact hash dedup отдельно от semantic near-duplicate; relationship derived_from/quotes/copies сохраняется.

## Конкретный эксперимент
Несколько AI summaries одного поста + одно независимое наблюдение; проверить счёт evidence.

## Критерий принятия
Не склеивать разные версии цели; не повышать confidence количеством копий одной цепочки.

## Функции
- `trace_information_lineage()`
- `cluster_near_duplicate_claims()`
- `compute_independent_evidence_count()`
- `preserve_conflicting_source_versions()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-004 REQ-012 REQ-023. Первичные источники/технические предпосылки: S08. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
