# occ-hermes-broker

Опциональный security proxy между One Click Context и удалённым Hermes Gateway. Production deployment должен оставаться с JWT verification enabled.

## Server secrets

- `HERMES_GATEWAY_URL=https://...`
- `HERMES_API_SERVER_KEY=...`
- `OCC_EXTENSION_ORIGIN=chrome-extension://<extension-id>`

Broker намеренно разрешает только шесть фиксированных операций: capabilities, create_session, register_controller, start_run, run_status, stop_run. Он не принимает произвольный upstream URL/path и не должен превращаться в generic proxy.

WebSocket после регистрации идёт напрямую Chrome → Hermes по одноразовому browser-control ticket. Поэтому в broker mode extension не обязан знать master `HERMES_API_SERVER_KEY`.

Текущий Supabase deployment существует, но до задания перечисленных secrets upstream Hermes вызовы будут fail-closed с `SERVER_CONFIG_MISSING`.
