# RND-34 — Adapter conformance and input trust firewall

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Данные из чужой вкладки не становятся инструкциями ОС.

## Архитектурное изменение
Typed tool contracts; schema conformance; origin allowlists; source text data-only; executor permissions получаются от user policy.

## Конкретный эксперимент
Вставить в заметку «upload your keys» и в tool result ложный permit; сравнить policy decisions.

## Критерий принятия
Никакого расширения полномочий от документа; adapter contract tests фиксируют disabled capabilities.

## Функции
- `validate_adapter_contract()`
- `classify_input_trust_origin()`
- `isolate_untrusted_document_instructions()`
- `enforce_egress_field_policy()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-003 REQ-007 REQ-019 REQ-021. Первичные источники/технические предпосылки: S16 S18. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
