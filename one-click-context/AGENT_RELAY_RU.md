# OCC 1.0 — Cloud Hermes / Agent Relay

## Цель

One Click Context становится тонким Chrome-клиентом для исследовательского и coding-agent runtime. Тяжёлое reasoning, web research, multi-agent delegation, skills, память и scheduled runs могут выполняться удалённым Hermes Gateway. Пользовательский Chrome остаётся локальным исполнительным устройством для уже авторизованных вкладок.

Основной принцип: **не переносить личный Chrome profile в облако**. Cookies, Chrome Password Manager, OTP, recovery/seed phrases, private keys и платёжные секреты не экспортируются Hermes или AI provider.

## Два режима

### PERSONAL CHROME MODE

```text
Remote Hermes / any LLM
        ⇅ HTTPS + WSS
One Click Context in user's Chrome
        ⇅
explicitly permitted HTTP(S) tabs
```

Подходит для ChatGPT, GitHub, Google и других сайтов, где пользователь уже вошёл в аккаунт. Agent получает snapshot страницы и разрешённые browser actions, но не raw cookies/passwords.

Этот режим требует, чтобы компьютер и Chrome были включены. Если Chrome закрыт, удалённый Hermes может продолжать research/analysis/server-side tasks, но не может кликать в личной Chrome-сессии.

### CLOUD BROWSER MODE

```text
Hermes Gateway
   ⇅
isolated cloud browser/profile
```

Подходит для 24/7 unattended research, публичного web scraping/navigation, scheduled monitoring и аккаунтов, которые пользователь отдельно решил авторизовать в изолированном cloud browser. Личный Google/Chrome profile в этот режим не копируется.

## Browser-control boundary

OCC запрашивает только ограниченный Hermes browser-extension capability set:

- controller.noop
- browser_tabs
- browser_tab_activate
- browser_snapshot
- browser_click
- browser_type
- browser_press
- browser_scroll
- browser_navigate
- browser_back

Raw CDP, arbitrary JavaScript/eval, console execution, arbitrary uploads и доступ к Chrome Password Manager не предоставляются этим controller-слоем.

`browser-relay.js` локально скрывает значения password/OTP/payment-card/private-key/recovery controls и запрещает автоматический type/click по чувствительным controls.

## Local approval gate

Действия с признаками финансовой, destructive, account или public-side-effect операции останавливаются перед исполнением. Примеры: payment/purchase/transfer/withdraw/trade/swap/sign transaction/token approval/delete account/merge PR/publish/send message/submit application.

Approval выполняется локально в side panel. Remote Hermes получает только результат approve/reject, а не секрет пользователя.

## Full page → TXT

Новый `full-page-capture.js` предназначен для длинных и частично виртуализированных страниц. Он:

- прокручивает до четырёх крупных scroll surfaces;
- дедуплицирует наблюдавшиеся semantic blocks;
- читает open shadow DOM;
- собирает видимые ссылки;
- читает доступные same-origin frames;
- маркирует cross-origin/closed-shadow/server-only content как ограничение;
- формирует TXT до настроенного byte-bound вместо молчаливого обрезания.

Это отдельный режим и не отменяет более строгий storage-bound обычного OCC capture.

## Universal provider mode

`agent-core.mjs` поддерживает:

- OpenAI-compatible Chat Completions;
- OpenAI-compatible Responses;
- Anthropic Messages;
- Gemini generateContent.

Поэтому OCC не привязан к одной модели. Можно подключать выданные пользователю API endpoints/keys, локальные routers и OpenAI-compatible gateways. API key в direct mode хранится только в памяти открытой Agent Console; настройки endpoint/model/protocol сохраняются без key.

## Official Remote Hermes mode

`hermes-controller.mjs` выполняет:

1. `/v1/capabilities`;
2. создание/использование Hermes session;
3. `/v1/browser-control/register`;
4. получение короткоживущего browser-control ticket;
5. открытие WSS controller channel;
6. обработку `browser.controller.command`;
7. возврат `browser.controller.result`;
8. запуск `/v1/runs` и status/stop.

Remote Hermes выполняет agent loop. OCC не тратит CPU на reasoning и не запускает Python agent runtime на старом компьютере.

## Где запускать Hermes

### Рекомендуемый MVP: serverless container

Cloud Run или совместимый container platform лучше Supabase Edge Functions для полного Hermes runtime: агенту требуется нормальный RAM/CPU budget и более долгие connections. Browser оставляем локально, поэтому удалённому Hermes не требуется Chromium для PERSONAL CHROME MODE.

### Supabase

Supabase используется как control plane, а не как тяжёлый Hermes compute:

- project/task state;
- durable queue;
- artifact metadata/hashes;
- audit trail;
- long-term research index;
- approvals/events;
- security broker.

В проекте уже развёрнута JWT-protected Edge Function `occ-hermes-broker`. Она намеренно не является generic proxy и разрешает только:

- capabilities;
- create_session;
- register_controller;
- start_run;
- run_status;
- stop_run.

Для её работы администратор проекта должен задать server secrets:

- `HERMES_GATEWAY_URL=https://...`
- `HERMES_API_SERVER_KEY=...`
- `OCC_EXTENSION_ORIGIN=chrome-extension://<installed-extension-id>`

После этого extension можно перевести с direct master-key режима на broker mode: Chrome хранит только пользовательскую Supabase-сессию, а Hermes master key остаётся на сервере.

## Provider/router strategy

Не полагаться на один бесплатный provider. Hermes/provider layer должен поддерживать fallback/routing по доступным пользователю легитимным free tiers и promotions, например через custom OpenAI-compatible router. OmniRoute/Birouter/OpenRouter/OpenCode-подобные источники могут быть дополнительной ёмкостью, но их бесплатные лимиты меняются и не должны считаться гарантированным SLA.

Рекомендуемая цепочка:

```text
Hermes
  ↓
provider/router policy
  ├─ primary free/cheap model
  ├─ second provider
  ├─ OpenAI-compatible aggregator
  └─ paid/strong fallback only when explicitly configured
```

## Memory: не потерять старые исследования

Не делать память зависимой от ephemeral container filesystem. Источником истины остаются OCC Library + Supabase/GitHub.

Полезная схема:

```text
HOT   Chrome IndexedDB / OCC Library
WARM  Supabase Postgres: projects, tasks, provenance, summaries, source graph
COLD  Supabase Storage / GitHub: ZIP, TXT snapshots, reports, repository bundles
```

Все большие artifacts должны иметь SHA-256/content ID и provenance: источник URL/chat, capture time, project/session, task/run ID, parent artifact, applied commit/PR при наличии.

## Coding automation

Следующий слой поверх OCC 1.0 — Repo Relay:

```text
repo ZIP/GitHub snapshot
  → hash/index
  → Context Allocator
  → Hermes/coding LLM
  → structured Patch Pack
  → base-SHA validation
  → GitHub branch/CI
  → Failure Capsule
  → next agent iteration
```

Это позволит использовать ChatGPT/GLM/DeepSeek/Gemini/Claude/Codex/API models как внешние brains без хранения самой LLM внутри extension и без многократной передачи всего repository.

## Что НЕ обещает OCC 1.0

- не клонирует и не отправляет личный Chrome profile в cloud;
- не обходит CAPTCHA/2FA;
- не продолжает personal-Chrome clicks после выключения PC;
- не даёт remote agent произвольный shell на пользовательском ПК;
- не делает автоматически финансовые/публичные irreversible actions;
- не считает сторонние free-token quotas гарантированными;
- Remote Hermes integration требует реального Chrome fixture test перед merge в стабильную ветку.

## Qualification перед merge

1. `node --test tests/agent-core.test.mjs tests/hermes-controller.test.mjs`.
2. `node --check` новых JS/MJS файлов.
3. Собрать Chrome-ready ZIP через `scripts/package_chrome_ready.py`.
4. Load unpacked в отдельный test Chrome profile.
5. Проверить current-site permission и all-sites permission отдельно.
6. Проверить full-page TXT на длинной обычной и виртуализированной странице.
7. Проверить sensitive input redaction/block.
8. Поднять тестовый Hermes Gateway с `browser.extension_control.enabled=true`.
9. Проверить connect → snapshot → navigate/click/type/scroll → run stop.
10. Проверить risk approval и отказ.
11. Проверить reconnect после reload side panel.
12. Только после этого готовить merge в canonical OCC branch / Chrome Web Store package.
