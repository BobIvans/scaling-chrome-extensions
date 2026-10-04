# RND-29 — Critical-token ASR arbitration

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Ошибки в repo name, path, number и отрицании важнее общего word error rate.

## Архитектурное изменение
Команда имеет stable transcript prefix; domain vocabulary; второй ASR только на спорном span; low confidence не даёт финансовый effect.

## Конкретный эксперимент
RU/EN code-mixed команды: merge/not merge, main/branch, dry-run/live; фоновые голоса и поздние исправления.

## Критерий принятия
Semantic slot error и false command activation измеряются отдельно; не делать cloud-audio hedge без согласия.

## Функции
- `identify_critical_voice_slots()`
- `request_selective_asr_check()`
- `reconcile_transcript_hypotheses()`
- `freeze_confirmed_intent_revision()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-002 REQ-015 REQ-020 REQ-021. Первичные источники/технические предпосылки: S06. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
