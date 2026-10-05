# Local Mini Controller V6 — primary operator UI

Primary UI is now the local Windows mini controller, not the Chrome extension UI.

The always-on-top translucent box has exactly three primary buttons: Observe, Automate+, STOP. Chrome extension remains an invisible page observer/transport. The V5 side panel remains useful for setup, diagnostics and qualification but is not the required everyday UI.

Observe: resolve active Chrome tab through the authenticated local bridge when available; trigger existing OCC capture; fall back to Alt+Shift+C; verify changed capture text; save it to local Inbox; submit it to canonical Library CAPTURE when operator policy allows.

Automate+: edit arbitrary goal and acceptance, review explicit effect scopes, ask local Laya typed questions when configured, submit known registered Core actions, monitor GitHub merges and expose capability/development gaps without inventing authority.

STOP: invoke canonical Core stop fence; no Laya/provider can override it.

Local bridge ownership: only the persistent Chrome background Native Messaging connection may claim the loopback endpoint. Other library/Codex native host processes cannot publish/steal the mini controller endpoint.

GitHub merge monitoring is read-only and free within GitHub REST limits. Public unauthenticated mode uses a safe polling floor above one minute; authenticated mode can poll faster. A merge event is evidence input, never automatic proof that installed code changed.

Self-renew pipeline: new merge -> exact merge SHA -> git fetch -> verify commit -> detached worktree -> configured tests -> optional versioned Desktop staging -> qualification/activation through stable controller -> mission resume. Current local-agent code implements through verified staging; unattended activation remains fail-closed until a device-qualified activation owner is wired.

Life context: watch_folders supports local AI exports, Downloads, R&D output folders and locally synced/exported Drive content. Cloud-only Google Docs require a Drive export/API/OAuth connector; .gdoc pointer bytes are not document contents.

Remaining V6 completion gates for Codex: generic effectful AI-site adapter runtime, automatic System-2 turn through an arbitrary selected AI site, direct mission state streaming to Mini, device-qualified release activation/restart/resume, and Google Drive cloud OAuth ingestion. Do not claim these are already working from the existence of docs or buttons.
