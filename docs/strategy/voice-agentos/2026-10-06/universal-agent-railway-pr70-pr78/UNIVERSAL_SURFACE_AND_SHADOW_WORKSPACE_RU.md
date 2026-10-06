# Universal SurfaceGraph + Shadow Workspace

## Surface identity
OS: process_id, hwnd, executable, window class/title, UIA root.
Browser: profile/session, windowId, tabId/CDP targetId, origin, URL, document token, account/workspace/conversation identity.
Page: DOM/AX digest, WebMCP manifest digest, frames/controls.
Optional visual: screenshot digest + parsed controls.

Edges: NATIVE_WINDOW_FOR_TAB, DOCUMENT_IN_TAB, FRAME_IN_DOCUMENT, CONTROL_IN_SURFACE, TOOL_EXPOSED_BY_SURFACE, SHADOW_OF, SAME_ACCOUNT, SAME_CONVERSATION, DERIVED_FROM.

## Observer ladder
WebMCP → CDP DOM/AX/network/download → existing extension archive/DOM → Windows UIA/native API → OCR/visual grounding → raw screenshot evidence.

## Shadow browser modes
- BACKGROUND_EXACT_TAB: background CDP route when it does not steal focus.
- DUPLICATE_READ_TAB: same authenticated profile for read/research, separate document state.
- ISOLATED_AGENT_TAB: exploration/synthesis tab.
- SAME_CONVERSATION_WRITER: exactly one writer lease; never simultaneous sends from duplicated composers.

## Windows
Prefer background native API/COM/CLI; UIA only when safe/non-disruptive; otherwise yield foreground. Optional virtual/PiP desktop can be added later.

Resource identity must include site/account/conversation/composer, not only tab ID.
