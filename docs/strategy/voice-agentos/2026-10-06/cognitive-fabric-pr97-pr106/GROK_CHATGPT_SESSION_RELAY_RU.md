# Grok Build / ChatGPT / API Session Relay

## Grok Build
Prefer native CLI/headless/ACP for code/workspace tasks: launch in exact registered workspace, use browser-auth session or scoped xAI API key, persist session identity, ingest plans/tools/logs/artifacts, and keep Core resource/effect gates authoritative.
Support Grok web Build Mode as a persistent visual/build conversation surface when continuity in the browser matters.

## ChatGPT
Support official Sign in with ChatGPT for eligible open-source/local applications when the user explicitly authorizes plan usage. This is a cognitive provider; it does not grant access to ChatGPT conversation history/memory. Local Library remains context authority.
Fallbacks: ordinary API profile (separate billing), browser ChatGPT session for a specific existing thread, or local model.

## Relay protocol
choose role → build bounded ContextPack → choose session → send → observe completion → archive raw answer → extract CognitiveProposal → verify artifacts/citations where applicable → compile next local action → if needed send only delta + unresolved gaps.
