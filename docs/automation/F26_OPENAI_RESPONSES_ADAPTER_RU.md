# F-26: backend adapter OpenAI Responses

## Gap и owner

Native Host уже удалял `OPENAI_API_KEY` из browser-job окружения, но provider
backend отсутствовал. Новый owner — `content-lab/openai_responses_adapter.py`.
Browser/voice/Laya не принимают secret или endpoint: adapter читает только
`OCC_OPENAI_API_KEY` внутри backend после новой F-25 reservation, а URL жёстко
закреплён на `https://api.openai.com/v1/responses` без redirects.

## Контракт

Строгий request преобразуется в нативные поля Responses API: `model`, `input`,
`instructions`, `max_output_tokens`, `store=false`. Tools, произвольный endpoint,
неизвестные поля и coercion отклоняются. Ответ читается bounded и проверяет
`object=response`, exact model, completed status, typed `output` и согласованную
usage-сумму. Secret и provider error text не возвращаются в receipt.

F-25 reserve происходит до чтения ключа и transport. Нулевой budget блокирует
call. Missing key или отмена до send освобождают reservation; отмена после send,
network uncertainty, malformed success и успешный ответ остаются
`NEEDS_RECONCILIATION`. Успех содержит usage tokens, но OpenAI response не даёт
фактическую цену, поэтому расход нельзя выдумывать: он сверяется отдельно.
Reservation replay никогда не dispatch-ится повторно.

401 фиксируется как terminal authentication failure. 429 разделяет временный
rate limit/`slow_down` и credit/spend/usage quota; `Retry-After` ограниченно
парсится, но adapter не делает автоматический retry. Это соответствует официальным
рекомендациям не повторять billing/quota errors и ограничивать backoff.

## Проверка и границы

Тесты используют только injected transports с 200/401/429/cancel fixtures.
Реальный smoke не выполнялся: авторизованный provider budget равен нулю. Adapter
не подключён к browser UI или durable worker, не создаёт очередь/store и не
выдаёт execution authority.
