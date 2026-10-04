# PR-010+011: точная библиотека источников и общий граф Python/JS/TS

Выбранные файлы, архивы и чаты сохраняются как оригиналы с независимыми версиями
извлечения. Поиск и граф открывают конкретный исходный диапазон; ручные метки и
редакции целей сохраняются после reindex/restart. JS/TS resolver и Python adapter
дают typed provenance edges, полный unresolved ledger и все parts больших SCC.

Заполнить перед публикацией по фактическому diff:

- Current base/head и реально изменённые handlers.
- Migration/legacy IDs/source byte fidelity и rollback rehearsal.
- Реальные focused/integration/CI results и references на receipts.
- Parser pin/support matrix/holdout precision+recall и Windows result либо NOT_RUN.
- Незакрытые source criteria и downstream owners; не объявлять весь продукт ready.

Этот файл — шаблон description. Финальный PR description переписать по итоговому
поведению реализации, удалить инструкции/незаполненные пункты и не указывать
непроведённые проверки как зелёные.
