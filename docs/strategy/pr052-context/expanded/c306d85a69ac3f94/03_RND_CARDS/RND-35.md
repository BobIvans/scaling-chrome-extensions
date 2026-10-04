# RND-35 — Two-speed ingestion

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Быстро сохранить raw, а тяжёлую разметку выполнить отдельным восстанавливаемым этапом.

## Архитектурное изменение
Статусы DISCOVERED/RAW_STORED/PARSED/INDEXED/REVIEWED; intake cursor и verification очереди; потоковые blobs вне RAM.

## Конкретный эксперимент
Большой смешанный corpus + interruption; приоритет новым файлам активного проекта.

## Критерий принятия
Нет исчезнувшего хвоста/тайного лимита; recoverable errors; сохранение raw не означает полный поиск по нему.

## Функции
- `register_ingestion_stage()`
- `resume_ingestion_cursor()`
- `stream_large_source_objects()`
- `schedule_progressive_enrichment()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-004 REQ-005 REQ-007 REQ-032. Первичные источники/технические предпосылки: S10. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
