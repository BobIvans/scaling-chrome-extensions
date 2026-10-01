# F-27: фиксированный Hugging Face provider adapter

## Gap и owner

После F-26 существовал только OpenAI Responses backend. Для Hugging Face не было
owner, который запрещает динамический endpoint/model discovery и fallback после
исчерпания квоты. Новый backend-only owner — `content-lab/hf_chat_adapter.py`;
учёт остаётся у F-25 `provider_budget.py`, а browser/voice/Laya не получают token.

## Контракт

Endpoint закреплён на `https://router.huggingface.co/v1/chat/completions`, token
читается только из `OCC_HF_TOKEN` после новой атомарной reservation. Operator
profile содержит ограниченный registry `alias → exact model:provider`; суффиксы
`:fastest`, `:cheapest`, `:auto`, route без provider, caller URL, tools и stream
отклоняются. Это исключает неявный выбор другого provider/model внутри adapter.

Строгий request передаёт только messages, registered route, max_tokens и
`stream=false`. Ответ проверяет chat-completion object, exact response model,
один assistant choice и согласованную usage-сумму. Token и provider error text
не возвращаются. Успех остаётся `NEEDS_RECONCILIATION`, поскольку token usage не
доказывает фактическую стоимость.

401, 402 и 429 завершают один вызов без retry или fallback. Missing token/отмена
до send освобождают reservation; отмена после send, network uncertainty,
malformed/неожиданный ответ удерживают её до reconciliation. Replay reservation
не dispatch-ится повторно.

## Проверка и границы

По официальной документации HF router поддерживает OpenAI-compatible endpoint и
provider suffix, а включённые credits могут переходить к pay-as-you-go после
исчерпания. Поэтому adapter не называет квоты «бесплатными» и не переключает
model/provider: реальный call разрешим только отдельным положительным F-25 budget.
Тесты используют injected 200/401/402/429/cancel fixtures; token не читался,
реальный API не вызывался, signup/purchase/deploy не выполнялись.
