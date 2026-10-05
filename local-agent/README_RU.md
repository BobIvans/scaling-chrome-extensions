# Voice AgentOS Mini — App-centric V7

Это основной локальный Windows UI. Chrome extension не является главным продуктом: он работает как скрытый browser-capability bridge.

## Основной controller

Три постоянные кнопки:

- **Observe** — локальное приложение просит hidden Chrome bridge захватить текущую вкладку, получает именно новый capture и отправляет его в canonical Library.
- **Automate+** — goal, acceptance, explicit effect scopes, Laya routing, System-2 relay, Library/Repos и текущая mission.
- **STOP** — Core-level stop fence независимо от Laya/LLM.

## One-time Chrome setup

После установки OCC extension и Native Messaging host один раз откройте context menu extension и выберите:

`Включить локальный AgentOS bridge для HTTP(S) сайтов`.

Chrome должен показать explicit permission prompt для:
- nativeMessaging;
- tabs;
- HTTP(S) origins.

После этого everyday управление выполняется из local app; Side Panel остаётся diagnostics/setup surface.

## Lifetime context

`watch_folders` может включать:
- AI export folders;
- Downloads;
- Telegram/chat exports;
- repo/R&D outputs;
- локально синхронизированные/экспортированные Drive folders.

Raw files всегда сохраняются в canonical Library.

Для JSON/JSONL export дополнительно выполняется best-effort conversation extraction:
- ChatGPT-style `mapping`;
- generic `messages[]`.

Производные conversation TXT получают provenance на raw export; raw source остаётся source of truth.

## Google Drive cloud

V7 содержит read-only Drive API v3 connector.

Он поддерживает:
- `files.list`;
- blob content через `files.get?alt=media`;
- Google Workspace documents через `files.export`;
- exact local hash;
- canonical Library capture.

OAuth material не хранится в Library.

В `settings.json`:

```json
"google_drive": {
  "enabled": true,
  "download_root": "%LOCALAPPDATA%\\VoiceAgentOSMini\\drive-cache",
  "folder_ids": [],
  "access_token_env": "",
  "refresh_token_env": "GOOGLE_DRIVE_REFRESH_TOKEN",
  "client_id_env": "GOOGLE_DRIVE_CLIENT_ID",
  "client_secret_env": "GOOGLE_DRIVE_CLIENT_SECRET",
  "max_files_per_poll": 100,
  "max_bytes_per_file": 10000000,
  "import_existing_on_first_run": false
}
```

For unattended access use Google OAuth offline access and a refresh token. Secrets remain environment-provided until secure onboarding is implemented.

## Laya → System-2

If `laya_endpoint` is configured, Automate+ runs typed Laya questions first.

Known registered Core capability is preferred.

When novel reasoning/tool design is needed, V7 can call existing local Codex through the same Native Messaging host using:
- `system2.codex.submit`;
- `system2.codex.status`;
- `system2.codex.result`.

The result is hash-verified and captured into canonical Library before the same mission continues.

`max_system2_cycles` bounds automatic continuation and repeated System-2 results stop the loop.

## GitHub merge watch / renewal

Public GitHub read-only polling is free within GitHub REST limits. The app uses ETag and a conservative interval.

An AI message saying “merged” is only a claim.

Required chain:

`GitHub observation → exact merge SHA → git fetch → detached worktree → tests → versioned stage → updater qualification → activation/rollback → mission resume`.

V7 local staging exists. Production unattended activation remains intentionally blocked until the full installed/device qualification contract is implemented.

## What is still not production-complete

See:
- `APP_CENTRIC_AGENTOS_V7_MASTER_RU.md`
- `V7_IMPLEMENTATION_MATRIX.json`
- `V7_REMAINING_FUNCTIONS.json`
- `V7_ACCEPTANCE_CAMPAIGN.json`

Main remaining areas:
- pinned Laya runtime;
- persistent H2/H1/H0 Core mission graph;
- qualified effectful adapters for arbitrary AI sites;
- tool candidate promotion;
- runtime PR/CI/merge pipeline;
- production updater activation;
- secure Drive OAuth onboarding;
- Windows installed end-to-end qualification.
