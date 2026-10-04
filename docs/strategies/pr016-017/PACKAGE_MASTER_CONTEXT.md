# Master Context — Voice AgentOS / ROADMAP-PR-016+017

Новая отдельная ветка продолжения от current PR #49 head `9a4fd3a`:
`codex/pr016-017-codex-continuation-20261004`. Fresh dated progress и CI/tests:
`handoff/CONTINUATION_PROGRESS.md` и `.json`. Начать с root `CODEX_START_HERE.md`;
весь предыдущий package context ниже сохранён, ранние SHAs являются snapshots.

## Цель

Продолжить стратегию в `BobIvans/scaling-chrome-extensions`: текст или голос →
проверяемый intent → существующий Core → полный immutable context packet → явно
выбранный AI/Grok-чат → durable delivery/reconciliation → связанный результат →
версионированный навык. Общий продукт также включает локальную библиотеку,
инвентаризацию репозиториев, R&D, release/update и длительные campaigns.
Не ограничивать общий scope количеством документов, файлов, частей, PR или
произвольной оценкой часов. Порционные budgets и реальные ограничения провайдера
должны быть явными, с continuation до EOF и учётом недоступных данных.

## Source of truth

1. Текущие Git HEAD/код/схема canonical SQLite и воспроизводимые tests определяют
   **реализованное поведение**. Старый snapshot не доказывает состояние main.
2. `docs/strategies/pr016-017/source/` — все 170 файлов приложенной стратегии,
   без редактирования исходных bytes. Здесь authoritative requirements,
   exact acceptance wording, исходные user decisions и полный вложенный backlog.
3. `docs/strategies/pr016-017/original-strategy.zip` — точная исходная копия ZIP.
   `PRESERVATION_MANIFEST.json` закрепляет hashes/размер каждого сохранённого файла.
4. `docs/strategies/pr016-017/archives/` — полное распакованное содержимое 11
   уникальных вложенных архивов. `ARCHIVE_INDEX.json` связывает каждый архив с
   extracted tree; одинаковые ZIP переиспользуют один tree по SHA-256.
5. `docs/automation/pr016-017/` — runtime runbook, function mapping и 220 строк
   критериев. Эти документы объясняют реализацию, но не заменяют исходную стратегию.
6. `docs/strategies/pr016-017/EXECUTION_AUDIT.md`, `FUNCTION_AUDIT.json`,
   `NEXT_IMPLEMENTATION.md` и `VALIDATION.json` — текущая передача работы.

При конфликте статусов сначала сверить build/refs, код и scope-matched evidence.
Исходные `application_code_changed=false`/`merged=false` в source — исторический
статус создания спецификации, а не состояние GitHub сейчас. Не исправлять source
ради нового статуса; обновлять audit/receipts. Аналогично, `next_package=18` в ZIP
историчен: GitHub #48 уже merged, его component acceptance также не равна product
closure. Roadmap №016/017 и GitHub PR #49 — разные системы нумерации.

## Что уже сделано

GitHub implementation PR: <https://github.com/BobIvans/scaling-chrome-extensions/pull/49>.
Исходный head: `b5b550c63d512842d687c8e4482031403a6b083e`.
В этой передаче интегрирован main с PR #47 (history/delta/scan) и #48
(release/campaigns), исходный integration main:
`d897598af6064d174bcd0df73f8b00cc79a4490e`.
Во время финальной проверки main продвинулся до
`b0a06f26106cb4739d8cf3465a4ad8941c328f40`: PR #50 (014/015 context/recovery/
Desktop) merged и также интегрирован. Action admission/STOP теперь используют
канонический `core_control` и общий queue capacity. Обе Desktop панели и оба
installers сохраняются; backend build digest включает action modules.
Финальное состояние и head брать из Git/GitHub, а не предполагать по этим SHAs.

| Область | Реализация | Граница |
|---|---|---|
| WS-018 intent | `content-lab/action_intent.py`, `action_runtime.py` | Typed registry, deterministic fixed-effect DAG, revisions, negation, proposals; полноценные роли/NLU остаются частичными |
| WS-019 voice | `desktop/voice.py`, `actions_ui.py` | Один capture, WAV, hotkey/ASR adapters, editable preview, независимый STOP; реальные Windows/Dell измерения открыты |
| WS-021 target | `content-lab/browser_cdp.py` | Opt-in local CDP, identity/focus/contract checks, qualification gate; фактический Grok account/UI не квалифицирован |
| WS-022 delivery | `content-lab/action_runtime.py` | Immutable parts/outbox, one local send invocation, unknown reconciliation, coverage, manual result import; uploads/history/finalization частичны |
| WS-020 skills | `content-lab/action_runtime.py` | Successful Core traces → candidates, qualification API, replay/stale/failure/optimizer; параметрический перенос и устройство открыты |
| Integration | `automation_core.py`, `native_adapter.py`, `desktop/client.py`, `agent-bridge/durable.mjs` | Общая SQLite/очередь/lease writer; action и campaign/history маршруты сосуществуют |

Дополнительно устранены merge conflicts; installer копирует action modules;
CLI возвращает success exit code и работает под isolated Python; прямой Core
CLI также находит installed siblings. Independent installed-layout regression
проходит Native CREATE → CLI ENQUEUE → Core worker → STOP без исходного repo в
Python import path. Подробные текущие результаты — `VALIDATION.json`.

Аудит всех 50 функций сохранён целиком: 13 BASELINE, 23 PARTIAL, 7 DEVICE_OPEN,
6 UI_OPEN, 1 NOT_USED (clipboard route отсутствует). Эти метки — состояние кода,
а не PASS исходных критериев. Все 220 критериев остаются OPEN до собственных
receipts; merge implementation baseline не закрывает полную стратегию.

## Что осталось

- Общий mixed-effect repo → packet → send DAG, typed planner/retriever/critic
  orchestration и полностью разрешённые critical slots без угадывания.
- Реальный installed Laya interface/version и его normal/failure/cancel receipts.
- Windows/Dell mic, ASR, key release, sleep/unplug/restart, Narrator, focus и
  latency/resource corpus. Synthetic PCM и Windows CI не заменяют устройство.
- Actual selected Grok target canary, adapter capabilities/limits, attachments,
  complete history, reliable streaming-finalization observer и correlated import.
- Parameterized portable skills, scoped demonstrations, full independent
  unseen/fault qualification, selective dependency requalification/repair.
- Проверка фактических контрактов PR-013/014/015; component presence не закрывает
  prerequisite. На момент исходной сверки #50 (014/015) и #51 (012/013 continuation)
  были draft/open. #50 subsequently merged и интегрирован; actual packet owners:
  `content-lab/context_library.py`, `context_packets.py`, `context_runtime.py`,
  `context_recovery.py`. Его полные strategy criteria всё ещё открыты.
  Повторно проверить refs и #51 перед зависимой реализацией.
- Все broad goals/downstream criteria, R&D и product closure из полного backlog:
  160 tasks, 164 features, 24 decisions, 28 goals. Не удалять deferred/revisit cards.

Сохранён весь контекст **предоставленного ZIP** и вложенных ZIP. Отдельный master
`ALL_IN_ONE_PRODUCT_ROADMAP_RND_RU_2026-10-03.zip` размером 387402728 bytes,
SHA-256 `6751ce4efd0963a7421a3f74c32b15055c13bb9bc389561853829a5a6a5fa3ac`,
не входит в предоставленный ZIP. Его exact selected members и provenance есть в
source; остальной исторический контент не объявлять прочитанным/сохранённым.
Это не блокирует выбранный 016/017 scope. Если нужен контент за его пределами,
получить master и проверить SHA, сохранив identity/источник.

## Архитектурные инварианты

Один canonical `content.sqlite3`, Core jobs, leases/writer и STOP; не создавать
второй executor/store ради voice, browser или skills. Additive migration и
recoverable cursors. User corrections/STOP/policy/target/source drift должны
fence исполнение. После потенциального Send неопределённый исход остаётся
unknown: lease expiry, retry, cancellation или restart не разрешают blind resend.
UI observation и модельные received/used claims — разные уровни evidence.
AI results/development requests — данные/proposals, не authority на grants,
install, merge или финансовые действия. Существующий feature flag/grants и
actual route qualification сохраняются; наличие сети не включает send автоматически.

## Следующий этап

Читать `CODEX_START_HERE.md`, затем `docs/strategies/pr016-017/NEXT_IMPLEMENTATION.md`.
Приоритет — typed role pipeline и resumable mixed-effect DAG в существующем Core,
с настоящими immutable packet owner contracts. Если upstream owner ещё отсутствует,
фиксировать BLOCKED_DEPENDENCY и выполнять независимую typed planning часть.
Device/UI gates сохранять открытыми до фактического evidence.
