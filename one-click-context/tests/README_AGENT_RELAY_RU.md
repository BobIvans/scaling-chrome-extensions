# OCC 1.0 Agent Relay — verification

Локально перед публикацией ветки были выполнены:

```bash
node --test tests/agent-core.test.mjs tests/hermes-controller.test.mjs
node --check agent-console.mjs hermes-controller.mjs agent-core.mjs browser-relay.js full-page-capture.js
```

Результат unit tests в рабочей среде: 8 passed / 0 failed.

Эти тесты не являются доказательством реальной совместимости с установленным signed-in Chrome или конкретным удалённым Hermes deployment. До merge требуется отдельный browser fixture/live qualification по checklist в `AGENT_RELAY_RU.md`.
