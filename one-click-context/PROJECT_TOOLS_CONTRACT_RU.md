# Контракт проектных инструментов OCC

`runProjectToolLoop` из [PR #8](https://github.com/BobIvans/scaling-chrome-extensions/pull/8) является отдельной точкой входа для Responses. Его нужно импортировать из `project-tools.mjs` после принятия того PR. Browser planner продолжает использовать собственный список действий.

## Что уже реализовано в PR 8

| Часть | Поведение |
| --- | --- |
| Registry | Map из имени в definition, validate и run |
| Request | tools, store false, max_output_tokens, полный накопленный input |
| Response | Только завершённый ответ; текст, refusal, reasoning и function_call |
| Batch | Все имена, call IDs и аргументы проверяются до первого handler |
| Continuation | function_call_output сохраняет исходный call_id; output items сохраняются |
| Пределы | maxTurns и maxToolCalls; новая партия не исполняется без следующего turn |
| Отмена | Проверяется перед запросом и каждым handler, сигнал передаётся callback |
| Ошибка | Receipt сохраняет выполненные и возможно частично выполненные вызовы; повторов нет |

`definition` имеет формат Responses function tool, а не вложенную форму Chat Completions. `validate(args)` обязана быть чистой синхронной функцией и вернуть ровно true. Проверку JSON Schema и разрешение ссылок реализует владелец handler. Объект схемы в tools сам по себе не заменяет локальную проверку.

## Интерфейс вызова

```javascript
import {runProjectToolLoop} from './project-tools.mjs';

// request, registry и authorizeRequest предоставляет вызывающий runtime.
const result = await runProjectToolLoop({
  config: {
    protocol: 'openai-responses',
    endpoint: configuredEndpoint,
    model: configuredModel,
    maxTokens: 4096,
    apiKey: backendCredential
  },
  messages: [{role: 'user', content: selectedTask}],
  registry,
  request,
  authorizeRequest,
  signal: abortController.signal,
  maxTurns: 4,
  maxToolCalls: 8
});
```

Это пример интерфейса, не готовая команда запуска. Переменные должны быть определены вызывающим приложением. Секреты не должны попадать в документы, frontend bundle или receipt.

`request(requestData, {signal})` возвращает разобранный Responses payload. Модуль сам не выполняет fetch. `authorizeRequest({requestIndex, maxOutputTokens, signal})` обязана явно вернуть true перед каждым обращением к transport. Это точка подключения политики расходов и текущего scope; модуль не рассчитывает цену токенов.

`run(args, {callId, signal})` исполняется последовательно. Handler обязан сам проверять права действия и scope, обеспечивать свой timeout и наблюдать signal. Внешний AbortSignal не может принудительно остановить callback, который его игнорирует.

## Результаты и ошибки

Успешный протокольный цикл возвращает status completed или refused, text и receipt. Это не означает, что диагностируемый проект получил qualification. Например, handler может успешно вернуть ready false.

При исключении доступны error.code и error.receipt. Status returned означает, что callback вернул значение; это не доказательство доменного успеха. failed_or_unknown требует сверки возможного эффекта. После исчерпания лимита расходов или отмены прежние эффекты не откатываются. Полный журнал и восстановление между запусками должен сохранять будущий runner.

Модуль не предоставляет shell, файловые обработчики, Laya, подписку, платный transport, генерацию кода или готовые Web3-функции. Следующий интеграционный шаг — подключить один реальный handler и сохранить его receipt в job.

## Проверка

После применения PR #8 из каталога one-click-context:

```sh
node --test tests/agent-core.test.mjs
```

Локально подтверждены 18 тестов. Проверяются текст без вызова, native function_call-only, несколько вызовов, сохранение reasoning и phase, невалидная партия, повтор ID, неполный ответ, refusal, разрешение каждого запроса, лимиты, отмена и неизвестный эффект ошибки. Реальный API и браузерная интеграция не проверялись.

Контракт сверялся с [function calling](https://developers.openai.com/api/docs/guides/function-calling) и [reasoning continuity](https://developers.openai.com/api/docs/guides/reasoning). Короткий план подключения: [LOCAL_AUTOMATION_RU.md](LOCAL_AUTOMATION_RU.md).
