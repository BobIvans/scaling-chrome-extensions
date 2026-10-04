# Architecture V2

Voice/Text → Intent Compiler → Project Resolver → Local Context Library → Context Cart → Context Compiler → Context Pack → AI Router → Safe Executor → Verification → Receipt → Result back to Library.

Recommended local stack:
- Python 3.13
- SQLite + FTS5
- tree-sitter/native AST
- git CLI read operations
- FastAPI local daemon
- Tauri shell
- faster-whisper
- watchdog
- JSON Schema
- append-only run events

Performance rule:
`hash → diff → FTS → graph → filters` first.
Embeddings/LLM only after candidate set becomes small.
