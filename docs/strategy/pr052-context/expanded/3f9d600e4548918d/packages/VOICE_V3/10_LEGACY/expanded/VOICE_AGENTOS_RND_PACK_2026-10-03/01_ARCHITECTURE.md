# Architecture: Reliability-First Voice AgentOS

VOICE/TEXT
  -> Streaming ASR
  -> Intent + entity extraction
  -> Fast typed router (Laya-like)
  -> Context Compiler
  -> ActionSpec
  -> Capability Graph
  -> Executor selection

Executor ladder:
  0. Direct in-process function
  1. CLI / PowerShell / Git / native API
  2. MCP tool
  3. Browser CDP / Playwright
  4. Windows UI Automation / COM / Win32
  5. Specialist agent (UFO² / BrowserCode)
  6. Vision GUI agent (Agent-S style)
  7. Human confirmation / clarification

Every action:
  plan -> execute -> observe -> verify -> receipt -> memory update

Successful new trajectory:
  trace -> generalize -> generate skill -> tests -> register -> benchmark -> promote to fast path

Principle:
Never make 'one universal GUI agent' the primary executor.
Use GUI vision as the universal fallback, not the universal first choice.
