# 48 проверяемых R&D-экспериментов

Все статусы ниже — NOT_RUN_RND_HYPOTHESIS. Тесты приложенного архиватора — отдельная синтетическая проверка, не выполнение этих production-экспериментов. Числовые admission thresholds ещё не выбраны; это намеренно не выдано за настройку готового runner.

## EXP-001 · Полный корпус >20 / >1000 документов
**Гипотеза:** Потоковый manifest убирает пропуски без роста RAM пропорционально total text.

**С чем сравнить:** Текущий single context_pack против multipart

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G03, G05.

## EXP-002 · Большой blob без 8 MiB потолка
**Гипотеза:** Raw streaming сохраняет large objects, даже когда parser временно отложен.

**С чем сравнить:** Текущий MAX_FILE против raw-first

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G05.

## EXP-003 · Точный путь через разные ОС
**Гипотеза:** Raw path bytes + display alias позволяют переносить inventory без коллизий Unicode/case.

**С чем сравнить:** Только строковый нормализованный path

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G05.

## EXP-004 · LFS/submodule completeness
**Гипотеза:** Раздельные scope flags предотвращают ложное полное покрытие при pointer-only архиве.

**С чем сравнить:** Один общий complete=true

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G05.

## EXP-005 · Прерывание на каждом checkpoint
**Гипотеза:** Durable cursor и atomic objects позволяют продолжить сбор без потерь или двойного head update.

**С чем сравнить:** Повтор full scan без persisted cursor

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G03, G05.

## EXP-006 · Ветки прошлых чатов
**Гипотеза:** Branch-aware importer сохраняет идеи из альтернативных ответов, которые теряет линейный export.

**С чем сравнить:** Только current branch transcript

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** Новая проектная гипотеза; не утверждение существующего benchmark.

## EXP-007 · Вложения и сообщения-ссылки
**Гипотеза:** Attachment manifest с missing-state лучше защищает полноту, чем markdown с недоступной ссылкой.

**С чем сравнить:** Отсутствие отдельного attachment inventory

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** Новая проектная гипотеза; не утверждение существующего benchmark.

## EXP-008 · Байт-контекст vs token budget
**Гипотеза:** Отдельный prompt compiler сохраняет raw полноту и предотвращает скрытый model-side cutoff.

**С чем сравнить:** Деление только по символам или размерам файла

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S03, G03.

## EXP-009 · Повторные ZIP и version lineage
**Гипотеза:** CAS dedup сокращает хранение одинаковых bytes, сохраняя все source paths/versions.

**С чем сравнить:** Удаление дубликатов целых документов по похожему title

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** Новая проектная гипотеза; не утверждение существующего benchmark.

## EXP-010 · Dirty workspace vs commit
**Гипотеза:** Два явных snapshot scope предотвращают ошибки анализа незакоммиченных изменений как части SHA.

**С чем сравнить:** Чтение working tree с прежним commit label

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G05.

## EXP-011 · Нужна ли вообще модель
**Гипотеза:** Точные aliases/registry покрывают частые команды дешевле LLM без ухудшения результата.

**С чем сравнить:** Always-LLM

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S02, S30.

## EXP-012 · Калибровка на собственных outcomes
**Гипотеза:** Held-out calibration снижает cost-weighted routing errors по сравнению с raw confidence.

**С чем сравнить:** Исходный confidence без calibration

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S03, S04.

## EXP-013 · Иерархическое пространство действий
**Гипотеза:** Family→skill routing надёжнее плоского выбора из сотен labels при одинаковом бюджете.

**С чем сравнить:** Flat action catalog

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S03, S04.

## EXP-014 · Чувствительность к именам labels
**Гипотеза:** Перестановка/переименование опций обнаруживает label bias до выдачи реальных capabilities.

**С чем сравнить:** Одна фиксированная форма вопроса

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S03.

## EXP-015 · Эскалация по цене ошибки
**Гипотеза:** Cost-aware abstention уменьшает вредные вызовы без always-expensive reasoning.

**С чем сравнить:** Единый confidence threshold для всех задач

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S01, S02.

## EXP-016 · Unknown не становится False
**Гипотеза:** Многозначная evidence-логика уменьшает ложные решения при missing/stale данных.

**С чем сравнить:** Булевое ready/not-ready без причины

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G04, G06.

## EXP-017 · Distillation успешного trace
**Гипотеза:** Повторяемый workflow после компиляции в проверенный skill требует меньше модельных вызовов.

**С чем сравнить:** Каждый запуск планируется заново

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S06.

## EXP-018 · Независимый verifier
**Гипотеза:** Проверка реальных postconditions ловит больше ложных успехов, чем self-report исполнителя.

**С чем сравнить:** Только exit0 или ответ LLM

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S06, G07.

## EXP-019 · Budgeted model disagreement
**Гипотеза:** Выборочный critic полезнее постоянного model parliament по cost per verified outcome.

**С чем сравнить:** Всегда один агент и всегда несколько агентов

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S02.

## EXP-020 · Prompt injection из источника
**Гипотеза:** Effect/policy boundary блокирует инструкции из imported text независимо от router confidence.

**С чем сравнить:** Смешивание документа и системных инструкций

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S30, S31.

## EXP-021 · Финализация ASR перед действием
**Гипотеза:** Ожидание stable transcript уменьшает неверные действия при самокоррекции.

**С чем сравнить:** Действие по первому partial transcript

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S18, S19.

## EXP-022 · Отрицание и исправление суммы
**Гипотеза:** Slot-aware подтверждение критичных параметров сокращает ошибки команд с «не» и числами.

**С чем сравнить:** Только средний WER

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S18, S19.

## EXP-023 · Repo/API entity lexicon
**Гипотеза:** Локальный словарь aliases улучшает intent parsing RU+English без изменения оригинальной транскрипции.

**С чем сравнить:** Общий ASR текст без entity mapping

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S18, S19.

## EXP-024 · Feedback loop от собственного TTS
**Гипотеза:** Изоляция playback/capture предотвращает повторные команды, услышанные от самого агента.

**С чем сравнить:** Один постоянно активный микрофонный поток

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** Новая проектная гипотеза; не утверждение существующего benchmark.

## EXP-025 · Контроль без голоса и мыши
**Гипотеза:** Общий typed API позволяет выполнить ту же задачу клавиатурой/switch input без отдельной логики.

**С чем сравнить:** Voice-only control

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S12, S15.

## EXP-026 · NVDA task completion
**Гипотеза:** Semantic labels и управляемый focus уменьшают число вмешательств на реальной задаче библиотеки.

**С чем сравнить:** Визуально исправный UI без screen-reader test

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S15.

## EXP-027 · UIA перед координатным кликом
**Гипотеза:** Семантический locator устойчивее к размеру/положению окна для поддерживаемого приложения.

**С чем сравнить:** Абсолютные screenshot coordinates

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S12, S13, S14.

## EXP-028 · Minimal locator repair
**Гипотеза:** Локальный repair с postcondition безопаснее полного перепланирования при UI drift.

**С чем сравнить:** Свободный повторный обход desktop

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S05, S06, S08.

## EXP-029 · Lexical + semantic retrieval
**Гипотеза:** Hybrid retrieval улучшает recall без потери exact path/SHA матчей.

**С чем сравнить:** FTS-only и embedding-only

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S23.

## EXP-030 · Старое предложение vs свежий код
**Гипотеза:** Version-bound requirement graph уменьшает повторные PR по уже реализованной функции.

**С чем сравнить:** Поиск только по текстовой похожести

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G01, G04.

## EXP-031 · Память отрицательных попыток
**Гипотеза:** Retrieval прошлых failed traces сокращает повтор одинакового неудачного исправления.

**С чем сравнить:** Хранение только удачных outputs

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** Новая проектная гипотеза; не утверждение существующего benchmark.

## EXP-032 · Evidence debt next-query
**Гипотеза:** Выбор следующего запроса по ожидаемой ценности даёт больше решённых blockers на единицу данных.

**С чем сравнить:** Просто максимальный объём нового контекста

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** Новая проектная гипотеза; не утверждение существующего benchmark.

## EXP-033 · Качество document extraction
**Гипотеза:** Raw-backed converters лучше выявляют missing tables/sections, чем только готовый Markdown.

**С чем сравнить:** Plain text extraction без coverage ledger

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S24, S25, S26.

## EXP-034 · Приватность при cross-source search
**Гипотеза:** ACL-aware retrieval не возвращает private spans в публичный context bundle.

**С чем сравнить:** Фильтр только после генерации ответа

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S30.

## EXP-035 · Installed package identity
**Гипотеза:** Проверка source/installed hashes обнаруживает ложные квалификации другого кода.

**С чем сравнить:** Совпадает только package name/version

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G09, G10.

## EXP-036 · Канонический qualification loop
**Гипотеза:** Desktop adapter к существующему owner уменьшает расхождение verdicts по сравнению со вторым runner.

**С чем сравнить:** Новый собственный qualification engine

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G07, G08, G09.

## EXP-037 · PIT shared feed fanout
**Гипотеза:** Общий point-in-time feed уменьшает дублирование RPC и inconsistent state между workers.

**С чем сравнить:** Каждая стратегия собирает state сама

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S33, G06.

## EXP-038 · Unit-safe net edge
**Гипотеза:** Явная модель единиц и embedded costs обнаруживает ложноположительный arbitrage PnL.

**С чем сравнить:** Сложение fee/slippage из разнородных источников

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G06.

## EXP-039 · Conflict-aware candidate scheduling
**Гипотеза:** Координатор учитывает shared accounts/capital и уменьшает бесполезную конкуренцию своих workers.

**С чем сравнить:** Независимая отправка всех кандидатов

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S33, S34.

## EXP-040 · Holdout после выбора стратегии
**Гипотеза:** Time-separated frozen holdout отсеивает случайные победы среди множества trials.

**С чем сравнить:** Выбирать лучший replay без нового теста

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G06.

## EXP-041 · CLI capability coverage
**Гипотеза:** Static candidates + installed tests дают более точную карту реальных команд, чем список функций.

**С чем сравнить:** Все definitions считаются доступными командами

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G10.

## EXP-042 · Observation vs realized fill
**Гипотеза:** Отдельные labels исключают объявление modeled edge реализованной прибылью.

**С чем сравнить:** Один общий pnl field

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G06, S34.

## EXP-043 · Неизвестный side effect и retry
**Гипотеза:** Reconciliation-state предотвращает двойное действие после timeout.

**С чем сравнить:** Автоматический повтор любого failed task

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G07.

## EXP-044 · Windows sleep/crash recovery
**Гипотеза:** Leases и повторная проверка evidence позволяют восстановиться без ложного DONE.

**С чем сравнить:** Только process status in memory

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** G03.

## EXP-045 · Least-privilege process boundary
**Гипотеза:** Reviewed profiles и sandbox блокируют запись/сеть вне разрешённой области даже при неверном плане.

**С чем сравнить:** shell=False как единственная защита

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S31, G03.

## EXP-046 · Sanitized export reproducibility
**Гипотеза:** Две manifests raw/share сохраняют проверяемую полноту без отправки secret contents.

**С чем сравнить:** Публично отправлять raw ради полноты

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** Новая проектная гипотеза; не утверждение существующего benchmark.

## EXP-047 · Token/API cost admission
**Гипотеза:** Предварительный budget и reserved output allowance предотвращают незаметный перерасход на R&D.

**С чем сравнить:** Непрерывные запросы по наличию API key

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S30, S32.

## EXP-048 · Версионирование learned skills
**Гипотеза:** Pinned adapter/tests с rollback переживают dependency/UI update лучше mutable latest skill.

**С чем сравнить:** Автообновление production по свежему release

**Доказательства:** versioned inputs/config, raw logs, независимая проверка результата, held-out negative cases. **Источники:** S04, S05.
