# UI specification — Repository Workbench + AI Targets + Mission Loop

## Main window: Repository Workbench

Add a first-class panel rather than hiding repo intelligence behind raw IDs.

### Repository controls

- **Открыть локальный репозиторий**
- **Скачать / клонировать GitHub repo**
- **Обновить до выбранного commit/ref**
- **Первичное полное сканирование**
- **Продолжить / пауза / отмена**
- repo alias, local path, remote URL, pinned HEAD/tree, snapshot ID
- capture progress: files/bytes/indexed/partial/blocked/deferred/errors
- explicit receipt link

### Context pack controls

- **Полный logical TXT pack**
- **Связанные файлы**
- **Tech debt**
- **Ошибки / broken paths**
- **Важные файлы**
- **Test impact**
- **Runtime path**
- **Delta с прошлого snapshot**
- **Domain focused**
- **Открыть Context Pack**
- **Показать coverage / gaps**
- **Отправить pack в выбранный AI target**

Every pack screen must show:
- pinned repo/snapshot/HEAD;
- mode;
- included logical groups;
- excluded/deferred/blocked items;
- byte/file/source coverage;
- exact source locators;
- part count + receiver budget;
- manifest SHA-256.

## AI Targets panel

Replace raw CDP ID entry as the primary UX.

Controls:

- **Обновить вкладки**
- **Выбрать активную вкладку Chrome**
- table: window, tab title, origin, provider guess, active/focused, target handle
- **Bind выбранную вкладку**
- exact identity display: origin/account/workspace/conversation/branch/provider/adapter contract
- **Observe only**
- **Проверить identity**
- **Отправить выбранный pack**
- **Прочитать ответ**
- **Auto mission loop**
- **Human takeover**
- **STOP**

Never display a target as SAFE merely because title contains Grok. Binding must use runtime-observed identity and be invalidated when account/chat/branch/epoch changes.

## Mission panel

Input:
- editable text command;
- PTT/voice transcript;
- goal;
- acceptance criteria;
- selected repo/snapshot;
- selected Context Pack;
- selected AI target;
- execution mode: OBSERVE_ONLY / PREVIEW / RUN_REGISTERED.

Buttons:
- **Preview plan**
- **Run mission**
- **Gather more context**
- **Ask selected AI for next action**
- **Create missing capability request**
- **Continue after verification**
- **Pause**
- **STOP**

Timeline:
`INPUT → CONTEXT → LAYA_DECISION → PLAN → EFFECT_INTENT → EXECUTOR → VERIFIER → AI_RESPONSE → NEXT_DECISION`.

Each node is clickable and shows hashes/refs/receipts without secret values.

## Laya Inspector

Show the exact state digest and typed questions, not hidden free-form prompts:
- question ID/type;
- options/rubric/proposition;
- probabilities;
- selected answer;
- confidence/abstention threshold;
- deterministic policy decision after the model answer.

Operator can force ABSTAIN / request more context. Operator cannot use the panel to silently expand grants.

## Capability Registry

Display:
- capability ID/version;
- effect class;
- required slots;
- executor;
- verifier;
- qualification state;
- supported providers/resources;
- dependency digests;
- last invalidation reason.

Unknown user request opens a Development Request card instead of arbitrary execution.
