# Дополнительная проверка источников — 3 октября 2026

## Laya / Jev: применимость, не рекламная максимальная скорость
Laya [S06] — non-generative typed-decision модель. Собственная model card предупреждает о domain sensitivity, переуверенности, лимитах контекста и ненадёжном `action.act_probability`. Для RU/EN нужен соответствующий checkpoint и отдельный frozen benchmark. Не переносить GPU latency на Dell CPU и не считать confidence правом на действие.

Практическая схема из авторской документации Jev и integration guide LangChain [S20,S21]: обычный код описывает state, допустимые варианты и ветвления; модель возвращает решения; исполнитель выполняет действие. Предлагаем применить её к выбору следующего источника, метке текста и выбору уже квалифицированного навыка.

## Локальные варианты без обязательного тяжёлого Python runtime
`receptron/laya` [S22] предлагает Node/TypeScript + ONNX Runtime. `Trystan-SA/laya-candle` [S23] — Rust/Candle порт. Это кандидаты benchmark, не «одновременно установить все». Сравнивать одинаковые inputs/outputs/labels, warm/cold latency и resident RAM. Более быстрый порт не считается лучше, если он хуже сохраняет correct routing или урезает state.

## Запись рабочего контекста
Windows UIA events [S25] подходят для дешёвого event-driven наблюдения. screenpipe [S24] показывает близкую архитектуру capture/history и может быть optional adapter. Его текущий README описывает source-available commercial licensing и включённую по умолчанию telemetry: нельзя автоматически объявлять его unrestricted open source или полностью offline. Для нашего app предпочтительны свои scoped collectors; внедрение чужого capture backend требует review настроек/лицензии.

## Browser / code / AI
Git worktrees [S04] позволяют раздельную подготовку; не являются OS sandbox. Playwright contexts [S03] разделяют browser storage, не чужие записи одного внешнего аккаунта. xAI function calling [S26] — коммуникационный канал; наш host исполняет разрешённый tool, GitHub merge не возникает от одной пересылки документа.

## Смысл новых цифр
Числа tests/files/workflows в ZIP относятся к нашему offline артефакту. Числа latency/accuracy из README внешних проектов — не наши эксперименты. В package нет результата Windows/ASR/API/real-bot benchmark.
