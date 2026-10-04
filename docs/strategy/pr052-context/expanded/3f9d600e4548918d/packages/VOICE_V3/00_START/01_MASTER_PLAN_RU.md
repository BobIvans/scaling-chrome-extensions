V3 УТОЧНЕНИЕ: multi-producer recording и независимые effect resources параллельны. Single writer относится только к одному конфликтующему effect target. Главная схема: 00_START/00_PARALLEL_CAPTURE_DECISION_RU.md.

# Voice AgentOS V2 — локальный компилятор контекста и безопасные параллельные маршруты

Дата: 3 октября 2026. Целевой пользовательский сценарий: личное приложение Windows 11, библиотека исходников/идей/кода и голосовой control plane для работы с выбранными AI и продолжения Studious-Pancake.

## Главное решение

Не «три агента одновременно меняют одну вкладку», а **несколько независимых путей подготовки → проверка → один эффект**.

```text
Голос / текст
    → версия намерения + область прав
    → pinned snapshot + критерии результата
    → выбор реально различающихся маршрутов
       ├─ exact source / symbols
       ├─ logs / measured execution
       └─ historical decisions / alternative candidate
    → независимый verifier
    → stop losers / confirm cancellation
    → повторная проверка target version и permissions
    → один effect broker
    → наблюдение результата / receipt / reconciliation
    → история и квалифицированный reusable skill
```

Имена API/MCP/PowerShell не определяют независимость. MCP — транспорт/контракт, а не отдельный источник корректности. Playwright и CDP могут управлять тем же Chromium. Несколько coding models могут повторять одну ошибку из общего context pack. Поэтому registry должен описывать общие зависимости и реальные co-failures.

## Три режима параллелизма

**Fan-out/fan-in:** несколько непересекающихся чтений нужны все. Пример: source, test trace, текущая requirement. Система объединяет evidence, не выбирает самый быстрый неполный ответ.

**Race-to-verified:** два разных кандидата решают один контракт. Не первый ответ, а первый результат, принятый независимым verifier. Для сложного patch «тесты прошли» — необходимое, но не достаточное условие; нужны bound task criteria и regression scope.

**Delayed hedge:** запасной read/candidate запускается лишь при превышении порога задержки или недостаточном evidence первого пути. Это кандидат на лучший speed/cost trade-off; выигрыш измеряется, а не обещается. Подход связан с tail-latency research [S01].

## Что никогда не гоняем наперегонки в общей среде

Публикация сообщения, GitHub merge, перевод средств, live trade, delete, DB migration, обновление прав, ввод в один foreground, команды с общим output directory/DB. Тесты тоже могут изменять files/DB или обращаться к сети: им нужны отдельные workspaces и проверенные ограничения.

Worktree — не sandbox [S04]. Browser context отделяет browser storage, но не последствия в одном remote account [S03]. Само имя действия read-only не делает недоверенный Python безопасным.

## Локальная библиотека без подмены полноты

Raw objects остаются исходниками. Chunks, summary, labels, embeddings и graphs — воспроизводимые представления. Каждый вывод связан с source URI, object hash, byte/message span, parser version и временем. Путь с переносом/переименованием не должен терять lineage.

Нет произвольного лимита на двадцать документов. Но конечные RAM/disk/API budgets остаются. Большие данные обрабатываются порциями с durable cursor, backpressure и явными error/exclusion records. Библиотека, индекс и один AI request имеют разные границы полноты.

Важный UI: `raw stored`, `indexed`, `selected for this pack`, `omitted with reason`. Кнопка «включить всё» не должна молча означать первые N документов. Полный repo export может состоять из томов с индексом, а рабочий handoff — из target slices и нужных зависимостей.

## Дополнительные intelligence layers

**Evidence deficit planner:** находит конкретно недостающий test trace, symbol, original decision или runtime observation. Он экономит вызовы модели, потому что запрашивает недостающий факт, а не увеличивает summary.

**Authority-aware labeling:** отличает голосовую команду пользователя от цитаты в webpage, AI-предложения, observed output и политики. Лейбл VERIFIED нельзя получить из слова «готово». Confidence — оценка извлекателя, не разрешение и не доказательство.

**Snapshot closure:** context pack связан с commit, actual dirty-file hashes, индексом и policy version. До применения нужно убедиться, что цель не изменилась. Это предотвращает работу хорошего патча по неверной базе.

**Conditional failure memory:** помнит «этот locator/adapter/version уже не работал» с условиями и сроком. Смена version вызывает requalification, а не вечную блокировку.

**Context optimizer:** сравнивает источники по полезности для verified outcomes. DSPy/GEPA — optional offline experiment [S11–S13], не автоматически принятая зависимость и не право модели переписывать production policy.

**Skill minimizer:** сокращает успешный workflow по повторным проверкам; не просто сохраняет длинную цепочку кликов. Больше использования должно уменьшать цену знакомой задачи, а не наращивать тысячи агентов.

## Самый короткий путь к полезности

Не начинать с universal visual agent и трёх тяжёлых локальных моделей. Первый вертикальный сценарий — **текст/голос → собрать handoff на текущую функцию Studious → показать кратко зачем → сохранить исходники/refs → импортировать ответ выбранного AI → проверить binding**.

После того как этот сценарий даёт measured benefit, добавить voice adapter к тому же IntentSpec, два альтернативных retrieval/candidate routes и single-effect broker. Затем новые навыки через isolated coding, verification и staged update. UI/vision — последний адаптер для задач без хорошего структурированного интерфейса.

На Dell стартовый эксперимент: один CPU-heavy worker, маленькое число concurrent model requests и background indexing с низким приоритетом. Это гипотеза для настройки, не измеренная оптимальная конфигурация. Никаких заявлений «33ms end-to-end» до измерений на устройстве. Карта Laya сама показывает зависимость качества/времени от checkpoint и input length [S06].

## Измерения вместо универсальных процентов

Для каждой категории задач фиксировать requested intent, supported/unsupported, attempted, verified outcome, blocked, failed, cancelled, unknown, false-success, human intervention. Публиковать coverage вместе с conditional success: иначе система может «улучшить процент», просто перестав делать сложные задачи.

Сравнивать serial / eager-parallel / delayed hedge при одинаковых input cases, resources и timeouts. Измерять p50/p95 time-to-verified и cost per verified success; включать failures/timeouts в отчёт. Co-failure и negative cases обязательны.

В абстрактном независимом примере P(хотя бы один успех) = 1 − произведение(1 − p_i). Если все пути зависят от одной плохой библиотеки/ошибочной команды, это вычисление неприменимо. Число агентов не гарантирует большую вероятность правильного результата.

## Что реально выполнено в этом ZIP

Сохранён исходный ZIP и его 8 файлов. Составлены 32 требования, 24 дополнительные R&D карточки (всего 42 с прежними), 20 workflow specs и 225 уникальных proposed functions (129 прежних + 96 новых). Проверены первичные документы S01–S19 и прочитаны 3 repo-документа.

Небольшой offline lab демонстрирует byte-preserving source store, bounded context с omissions, delayed read/candidate race, independent verifier и idempotent single SQLite commit. 41 unit test прошёл в среде сборки. Это не desktop app, не Windows qualification и не готовая Laya интеграция. API, микрофон, реальные repo tests, browser control и trading не запускались.

Полных исходных ChatGPT/Grok/Telegram/Google Docs архивов здесь нет. Цели текущего чата собраны в реестр; старый ZIP сохранён byte-for-byte. Полный transcript или «вся жизнь без потерь» этим пакетом не заявляются.
