# F-23: детерминированный Laya advisory router

## Подтверждённый gap

На проверенном F-22 head существовал строгий `occ.goal-proposal.v1`, но UI не мог
предложить следующий безопасный класс обработки. Свободный текст нельзя было
использовать как execution authority, а confidence не имел формальной границы.

## Реализация

`advisory-router.mjs` повторно проверяет канонический proposal и возвращает
`occ.advisory-route.v1` с одним из маршрутов:

- `ANALYZE_SELECTED_CONTEXT`;
- `BUILD_JOB_ARTIFACTS`;
- `REVIEW_REGISTERED_ACTION`;
- `MANUAL_REVIEW`.

Правила детерминированы для RU/EN/LV. Prohibition labels намеренно исключены из
положительного matching. Несколько семейств правил, отсутствие совпадения и
чувствительные эффекты fail closed в `MANUAL_REVIEW`. Каждый результат содержит
`action_authority=false` и `dispatch_allowed=false`; confidence остаётся только
диагностикой.

UI показывает совет лишь после доверенного click. Router не меняет выбранный
режим и не вызывает Native Host, durable queue, shell, браузерное действие или
сеть. Прежняя кнопка запуска сохраняет повторную валидацию и отдельный confirm.

## Проверка

Версионированный held-out fixture содержит 12 RU/EN/LV случаев, включая
чувствительный, неоднозначный и неизвестный запросы. Router правильно классифицирует
12/12, compact English goal-only baseline — 6/12. Отдельные тесты проверяют строгую
схему, каноничность, запрет authority и отсутствие dispatch surfaces в production
модуле.

## Границы

F-23 не создаёт job, не запускает worker/CI, не связывает voice transcript с целью
и не добавляет новый owner SQLite/library/job queue. Зарегистрированный action
только предлагается для просмотра; его template/parameters/effect должны быть
проверены отдельной следующей функцией до любого выполнения.
