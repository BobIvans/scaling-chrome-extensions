# Remote Hermes для One Click Context — без постоянного VPS

## Архитектура

```text
OCC Chrome (local thin executor)
   ⇅ HTTPS + WSS ticket protocol
Hermes Gateway (Cloud Run / compatible container host)
   ├─ LLM provider/router
   ├─ research / extraction
   ├─ skills / memory / delegation
   ├─ runs / cron
   └─ optional isolated cloud browser
   ⇅
Supabase
   ├─ task/project state
   ├─ artifact index / provenance
   ├─ audit / approvals
   └─ limited Hermes broker
```

Для уже авторизованных личных сайтов действия выполняются в пользовательском Chrome. Cookies и сохранённые пароли не экспортируются Hermes. Если ПК/Chrome выключен, личная browser-сессия недоступна: для 24/7 задач используйте отдельный isolated cloud browser/profile и авторизуйте в нём только те аккаунты, которые действительно хотите отдать unattended automation.

## Hermes

Официальный Docker image: `nousresearch/hermes-agent:latest`. Gateway запускается командой `gateway run`. Для внешнего API нужны `API_SERVER_ENABLED=true`, `API_SERVER_HOST=0.0.0.0` и секретный `API_SERVER_KEY`. Browser extension control должен быть явно включён в `config.yaml`.

Для direct Chrome access CORS задавайте точным `chrome-extension://<id>`, а не `*`. В более защищённом варианте Chrome общается с Supabase broker, а master Hermes key вообще не попадает в extension.

## Cloud Run

Для PERSONAL CHROME MODE удалённому Hermes не нужен Chromium, поэтому 1 GiB RAM — разумная минимальная экспериментальная конфигурация. Cloud Run поддерживает WebSockets, но одно соединение ограничено request-timeout (до 60 минут), поэтому controller должен уметь reconnect/re-register после разрыва.

`deploy-cloud-run.sh` — шаблон, а не автоматически выполненный deployment. Он ожидает, что в Secret Manager уже существует secret `occ-hermes-api-key`.

Cloud Run filesystem ephemeral. Не считайте его источником истины для research/project memory: долговременное состояние держите в OCC Library + Supabase/GitHub. Позже, если Hermes session/skills должны переживать recreation контейнера без восстановления из control plane, добавьте отдельный persistent storage strategy.

## Provider routing

Не привязывайте Hermes к одному provider. Используйте built-in provider или `provider: custom` для OpenAI-compatible router. Бесплатные pools/credits меняются, поэтому provider policy должна иметь health/quota/fallback и не считать рекламируемый free quota гарантией.

## Security checklist

- real `API_SERVER_KEY` никогда не коммитить;
- remote Hermes только HTTPS/WSS;
- Chrome Password Manager/cookies/OTP/seed/private keys не синхронизировать;
- sensitive input блокируется локальным OCC relay;
- financial/destructive/public actions требуют local approval;
- extension host permissions выдаются пользователем отдельно;
- cloud browser не должен автоматически импортировать личный Chrome profile;
- Supabase broker не должен превращаться в arbitrary URL/path proxy.
