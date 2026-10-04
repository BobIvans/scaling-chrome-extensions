# Voice AgentOS — Tech Stack Shortlist (2026-10-03)

## Desktop shell
- Tauri 2 + Rust core + TypeScript UI
- Python sidecar for AI/agent libraries
- Local IPC over stdio / named pipes / localhost loopback

## Voice
- Silero VAD or equivalent lightweight VAD
- Qwen3-ASR-0.6B-hf (multilingual experiment)
- NVIDIA Parakeet-TDT-0.6B-v3 Q8 GGUF (local ASR experiment)
- Domain vocabulary biasing for repo/project terms

## Fast decision layer
- Laya / laya-multilingual / laya-typed-decisions
- Typed schemas only; no free-form text on fast path
- Confidence-based escalation to larger models

## Local context & memory
- Immutable content-addressed object store (SHA-256)
- SQLite/DuckDB for metadata/events
- SQLite FTS5 or Tantivy for lexical retrieval
- LanceDB for vector + FTS + metadata/multimodal retrieval
- Graphiti for temporal context graph
- Optional screenpipe capture adapter for ambient PC history

## Repository intelligence
- Git CLI / libgit2
- Tree-sitter AST index
- Symbol/import/call/test graph
- Aider-style repo map as a compact context view
- Ripgrep for exact search
- Static-analysis adapters by language

## Coding
- OpenHands Software Agent SDK
- Pluggable model adapters: OpenAI / Grok / Claude / Gemini / local
- Git worktrees/branches for isolated changes
- Docker/WSL sandbox where appropriate
- Test-first patch validation

## Browser
- Direct HTTP/API when available
- MCP tool
- CDP / Playwright
- BrowserCode for agent-written reusable browser scripts
- Vision browser agent only as fallback

## Windows
- PowerShell / Win32 / COM first
- Windows UI Automation
- Microsoft UFO² experiment for multi-app workflows
- Agent-S / vision-control fallback for unstructured GUI

## Durable orchestration
- Temporal for long-running workflows and crash recovery
- DAG executor for parallel read-only tasks
- Event log + resumable checkpoints

## Interop
- MCP resources/tools
- MCP Tasks for long-running tool calls
- Skills over MCP for portable skills
- Local REST/WebSocket API for non-MCP clients

## Security
- Capability manifests
- Per-skill allow/deny scopes
- Secret references, never raw secrets in model context
- Approval gates for destructive/financial/account actions
- Atomic plugin install + rollback
- Full execution receipts
