# ChatGPT API внутри приложения: ограниченные tools, полная provenance

Официальный function-calling интерфейс позволяет модели предложить вызов описанного инструмента; приложение выполняет инструмент и возвращает результат. [S30] Это не автоматический доступ API к твоему диску или рабочему столу. Для computer-use действует тот же принцип внешней среды исполнения. [S31]

Подписка ChatGPT не является балансом API; API usage отдельно учитывается/оплачивается. [S32] В профиле приложения нужны явные monthly/per-job budgets и перед вызовом оценка размера передаваемого контекста. Не фиксировать в коде название «самой новой модели»: список approved моделей и их budgets — versioned configuration.

## Предлагаемая read-first поверхность

`library.search(query, cursor)`, `library.read_span(source_id, revision, byte_start, byte_end)`, `repo.snapshot_status(snapshot_id)`, `jobs.propose(capability_id, inputs, source_refs)`, `jobs.status(job_id)`, `reports.create_request(goal, source_refs)`.

В `schemas/openai_tools.responses.json` приведён строгий декларативный пример. Он не подключён к сети и не исполняет запросы. Не давать модели `run_any_shell(command)` или доступ к keyring. Даже строгий JSON проверяется server-side: permissions, roots, effect types, exact versions и limits нельзя вывести из одной JSON Schema.

## Четыре различных JSON

1. **Laya/Jev prediction request** — только state/questions; получает предположение о классе задачи.
2. **Workflow proposal** — DAG с capability IDs, inputs и evidence requirements; наша собственная schema, не endpoint Laya.
3. **Operator policy/profile** — локальная reviewed конфигурация полномочий/путей/argv; не пишет модель.
4. **Execution receipt** — результат executor/verifier; не пишет planner.

Смешение этих файлов опасно: готовая форма JSON не означает готовую автоматизацию. В `workflows` планы помечены `PROPOSAL_NOT_EXECUTED`; отсутствие adapter/capability должно давать BLOCKED, а не fallback на свободный shell.

## Облако и приватность

Key хранится вне библиотеки/контекста/репозитория, через защищённое хранилище ОС. Каждый source имеет privacy/export scope; prompt preview показывает, какие именно байты/сводки уходят наружу. Imported document может содержать prompt injection — это untrusted data, не команды. Никакие instructions из README/страницы не меняют права job автоматически.

Для больших корпусов: snapshot/index → targeted spans → explicit missing refs → retrieval loop → final bundle со списком просмотренного/непросмотренного. При смене SHA предыдущий report остаётся историческим, не становится автоматически актуальным.
