# Предлагаемая архитектура и контракты

Existing SCE core owns sources, revisions, blobs, tasks and export. Desktop, CLI и optional browser адаптеры вызывают один публичный сервисный слой. Поисковые и смысловые индексы — восстанавливаемые проекции. Внешние сервисы подключаются через capability contracts. Конкретные module paths определяются в P0.

| Сущность | Обязательное содержание | Инвариант |
|---|---|---|
| SourceRevision | source_id, revision_id, captured_at, origin, hash, availability | Новый источник не заменяет старую версию молча |
| EvidenceRef | source/version, path, range, byte hash, extraction version | Цитата разрешается к доступному первоисточнику |
| Goal/Decision | author, original span, interpretation, status, supersedes | Предложение модели не становится решением пользователя |
| ContextPack | task, snapshot, source refs, included/omitted/missing, budget, continuation | Усечение представления никогда не скрывает потерю данных |
| AIResult | request ID, base snapshot, status, outputs, tests, missing context | Слова DONE недостаточно для verified status |
| Capability | version, parameters, permissions, effects, verifier, resource keys | Возможности и доступы не расширяются самим proposal |
| ActionPlan | operation ID, snapshot, DAG, effects, resource keys, retry policy | Повтор логической операции сохраняет ID |
| ExecutionReceipt | inputs, tool/version, started/completed, observed effect, uncertainty | Неизвестный результат остаётся unknown до reconciliation |
| Experiment | hypothesis, baseline, dataset/snapshot, metrics, cost, stop rule | Отрицательный результат также сохраняется |

Состояния job: proposed → validated → queued → running → verifying → succeeded/failed/cancelled/unknown. Unknown не является failed: blind retry внешнего эффекта может создать дубль [S3]. Read-only ветки и независимые append-only observations допускают параллельность. Shared mutable resource координируется адресно; разные ресурсы могут выполняться одновременно.

Устаревание: изменение base commit, policy version, источника или контракта invalidates соответствующие preconditions. Затем требуется новая валидация. STOP запрещает новый dispatch и сохраняет судьбу уже начатых действий. Reconciliation должен иметь конечный результат либо явный unresolved блокер.

В пакет включены workflow design specifications; это проектный IR, не готовый формат импорта Laya. Команды, модели и providers намеренно не выдуманы: adapter_binding заполняется после проверки доступного интерфейса. Работа с разными Git worktree полезна для альтернативных патчей, но не заменяет process sandbox [S4].

Локальное хранение должно иметь backup/restore, disk-space checks и миграции. Если выбран SQLite WAL, учитывать single writer transaction и локальный host [S1]; не переносить рабочую WAL-БД на сетевой диск как простой путь к multi-device sync. Конкретную версию и исправления следует проверить при реализации.
