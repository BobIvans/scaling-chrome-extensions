# Remote Hermes qualification before production

1. Build official-image derivative and verify `gateway run` starts on configured `API_SERVER_PORT`.
2. `GET /v1/capabilities` must advertise `browser_extension_control.enabled=true` and the expected protocol version/capability allowlist.
3. Register only against an existing authenticated session and verify the one-time WebSocket ticket expires/rejects replay.
4. Verify Cloud Run WSS reconnect/re-register because service WebSocket requests are bounded by configured request timeout (max 60 minutes).
5. Verify OCC reconnect never replays a previously approved mutating browser action.
6. Verify CORS exact extension origin; never use wildcard in production direct mode.
7. Verify Supabase broker remains JWT-protected and fail-closed until its three server secrets exist.
8. Verify container recreation does not destroy the canonical project/research memory: long-lived state must be recoverable from OCC Library/Supabase/GitHub.
9. Keep `max-instances=1` for the first controller qualification; only scale out after controller/session routing is externalized.
10. Test PERSONAL CHROME MODE separately from isolated CLOUD BROWSER MODE. Never import the user's personal Chrome password/cookie store into cloud browser qualification.
