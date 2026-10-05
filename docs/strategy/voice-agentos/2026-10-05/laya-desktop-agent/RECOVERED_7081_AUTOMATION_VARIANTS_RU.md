# Восстановленные сценарии из 7 081-master — НЕ терять при реализации

Этот документ исправляет слишком узкую формулировку PR #55. Выбранная вкладка Grok — лишь один transport внутри более общего automation loop.

## Подтверждённые старые workflow IDs

Следующие сценарии уже существовали в 7 081-master и должны быть сохранены как source-of-intent:

- `AUTO-GL-01` — выбранный контекст → выбранная вкладка Grok → библиотека знаний.
- `AUTO-GL-02` — Grok предлагает действие → реальный зарегистрированный исполнитель.
- `AUTO-GL-03` — неизвестная операция → новый инструмент → продолжение исходной задачи.
- `AUTO-GL-07` — непрерывное наблюдение и несколько независимых задач.
- `AUTO-GL-08` — обрыв после внешнего действия → reconcile → продолжение.
- `AUTO-GL-09` — голос/текст → быстрый известный путь или provider-neutral Grok turn.
- `AUTO-EASY-04` — выбранный Grok → код/PR → проверенный merge → обновление.
- `AUTO-OBS-16` — Context → выбранный Grok → изменение → новая способность.
- `AUTO-PARALLEL` — контекст → выбранный UI-чат Grok Build → проверенное обновление с параллельными read/research branches.
- `AUTO-V3-4` — «Я внедрил — проверь и продолжи».
- `AUTO-V3CAT-005` — `chunk_to_any_action`: chunk → action → neighbours → action cart → policy → execute/approve → verify → receipt.
- `AUTO-V3CAT-135` — «Продолжай работать, пока я пишу в Chrome»: background context reads + code proposals; foreground GUI route ждёт lease, не крадёт focus.
- `AUTO-VOICE-04` — «Отправь пакет в выбранный Grok и сохрани ответ».
- `AUTO-VOICE-10` — «Подключи возможность из этого GitHub repo».
- `AUTO-VOICE-11` — «Этого навыка нет — создай его».
- `AUTO-VOICE-16` — «Стоп; затем продолжи только незавершённое».
- `AUTO-WORK-SESSION` — запись выбранной рабочей сессии и продолжение.

## Старые browser/tool операции, которые должны войти в runtime

Master уже предусматривал:

- `capture_selected_chat`
- `observe_selected_source`
- `collect_selected_links`
- `open_allowed_link`
- `download_allowed_artifact`
- `fill_bound_draft`
- `upload_bound_parts`
- `submit_bound_prompt`
- `read_bound_reply`
- `reconcile_send`

Это означает, что attachment/document/link внутри Grok conversation — полноценный source/action route, а не новая идея.

## Старый GatherSpec

Browser gathering должен работать по bounded `GatherSpec`:

- selected tabs/origins;
- allowed link depth;
- byte/time/quota budget;
- document/media types;
- output namespace;
- freshness rule;
- stop condition.

Link graph сохраняет parent turn/span, element/anchor, href, redirects, destination origin, timestamp, raw hash, parser version и extraction loss.

`Open`, `Download`, `Submit` — разные эффекты. Нельзя считать кнопку read-only только потому, что она похожа на ссылку.

## Старый document/attachment contract

PDF/DOCX/TXT/code/ZIP и другие доступные artifacts должны сохраняться как raw originals. Parsed derivatives ссылаются на exact original hash/page/range. Missing/encrypted/unavailable attachment остаётся explicit gap.

Virtualized chat capture должен отдельно учитывать:
- materialized windows/scroll;
- message identities;
- branches;
- attachments;
- top/bottom anchors;
- unloaded sections;
- partial streaming revisions.

## Старый agent loop

Provider response → original source → typed `ActionProposal` / `KnowledgeResult` / `GapSpec` / `PatchCandidate` / `ToolCandidate` → critic → compiler → registered executor → independent verifier → RuntimeReceipt.

Unknown operation → `GapSpec` → isolated implementation → tests/heldout → versioned capability → исходная задача возобновляется с checkpoint.

## Старый long-run contract

Campaign:
- хранит child runs и durable checkpoints;
- умеет quota wait;
- умеет restart/wake recovery;
- не повторяет UNKNOWN effect до reconciliation;
- сохраняет успешные ветки, если другая ветка упала;
- останавливается на accepted goal, exhausted budget, unavailable access, no-progress или STOP;
- pause admissions и STOP текущего run — разные операции.

## Правило V2

Нельзя реализовать только `selected_tab_roundtrip` и считать исходную идею закрытой. Он является одним узлом универсального Goal Continuation Kernel.
