# LAYA R&D V2 — Chunk Library / Workflow UI / Context Orchestration

Главный апгрейд после MEGA pack — сделать **Chunk Operating System** центральным ядром Laya.

Не просто разрезать repo/chat/doc на куски, а хранить каждый chunk как объект со стабильным ID, источником, lineage, зависимостями, freshness, qualification, risk и связями с PR/tests/chats/docs.

Новый основной путь:

`SOURCE → INGEST → NORMALIZE → CHUNK → ENRICH → LINK → INDEX → LIBRARY → CONTEXT CART → CONTEXT PACK → AI/CODEX/WORK → RESULT → VERIFY → RECEIPT → MEMORY UPDATE → INVALIDATE/REBUILD`

Без этого Library — архив. С этим Library становится операционной памятью агента.

Главный UI: три панели — **Library Navigator / Chunk Workspace / Context Cart**.
