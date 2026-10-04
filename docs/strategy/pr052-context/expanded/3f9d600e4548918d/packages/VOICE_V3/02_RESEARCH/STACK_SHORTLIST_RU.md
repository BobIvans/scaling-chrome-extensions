# Стек: что брать первым, что только исследовать

## Минимальная основа
Существующий SCE Python/Core/content.sqlite3 + stdlib asyncio/SQLite; Git source snapshots; точный поиск; существующие parser/review owners. Desktop shell — candidate Tauri 2 или лёгкий Python UI, но не обязательная перепись backend. В этом пакете ни одна оболочка не установлена.

MCP — optional provider/tool adapter [S16], не отдельный исполнитель и не второй scheduler. API/CLI/UIA/CDP относятся к разным каналам доступа, но иногда имеют общий failure domain.

## Селективные добавления
| Кандидат | Применение | Важная граница |
|---|---|---|
| Laya + optional local serving [S06,S07] | Короткие typed routing/label decisions | Benchmark RU/EN на устройстве; не security authority |
| GLiNER [S08] | Entity spans и кандидаты тегов | Не доказательство статуса implementation/execution |
| SCIP/LSP [S09] | References/definition graph | Language-specific indexer; не полный runtime graph |
| Docling [S10] | Structured document ingestion | Parser output не заменяет raw; OCR only when needed |
| DSPy/GEPA [S11–S13] | Offline оптимизация context/skills | Holdout separation, feedback hygiene, resource budget |
| Playwright [S03] | Owned browser contexts, структурированные действия | Не параллельный ввод в пользовательскую вкладку |
| UFO [S05] | Дополнительный Windows/GUI/DAG adapter | Не проверен на Dell; без второго owner для прав |
| OpenTelemetry [S14] | Timing, causal traces, failure domains | Span success не означает postcondition success |
| GitHub attestation checks [S15] | Проверка происхождения обновления | Trusted build != безопасный код |
| Agent Skills [S18] | Переносимый пакет инструкций/ресурсов | Права и версия skill проверяются независимо |
| LangGraph persistence [S19] | Исследование resumable model subgraph | Не дублировать existing durable Core |

Temporal/Graphiti/LanceDB/OmniParser/Agent-S/OpenHands/BrowserCode из legacy остаются кандидатами из прежнего обсуждения, не обязательными зависимостями и не прошедшими интеграционный тест в этом ZIP. Для каждой зависимости нужен отдельный acceptance test, pin, license/maintenance review и оценка RAM/CPU.

Стек — не гонка за максимальным числом библиотек. Первый speed gain ожидается от source selection, deterministic operations, fewer duplicate calls и incremental processing; его нужно подтвердить измерениями.
