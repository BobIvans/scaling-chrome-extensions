# RND-22 — Resource commutativity and foreground ownership

**Статус:** R&D specification, не реализованная интеграция. Новизна: `new`.

## Проблема
Не дать агентам бороться за мышь, буфер и одну вкладку.

## Архитектурное изменение
Для каждого node указать read/write resource sets; разные документы параллельны, общий foreground эксклюзивен; пользователь имеет приоритет.

## Конкретный эксперимент
Инъекция пользовательского ввода во время действия; два графа с общим файлом и отдельными browser contexts.

## Критерий принятия
Нет чужого ввода в выбранной вкладке; conflict graph сериализует общие mutable resources.

## Функции
- `infer_resource_access_sets()`
- `build_conflict_graph()`
- `acquire_foreground_lease()`
- `yield_to_user_input()`

## Safe parallel contract
Подготовка/чтение — кандидаты; общий mutable target — один committer. Unknown external outcome блокирует fallback effect. Заявленный skill scope не заменяет OS sandbox. Любые live/trading действия в этом пакете disabled.

## Измерения
Verified outcome; false-success; p50/p95; total attempts including failures/timeouts; human intervention; marginal recovery over baseline; source coverage; peak RAM/API budget. Показатели в карточке — план измерений, не результаты.

## Связи
Требования: REQ-014 REQ-020 REQ-024. Первичные источники/технические предпосылки: S03 S04. Предлагаемая комбинация — наш инженерный эксперимент, а не утверждение о готовом решении авторов источников.
