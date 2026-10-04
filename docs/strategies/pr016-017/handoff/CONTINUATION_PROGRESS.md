# Progress / продолжение ROADMAP PR-016+017 — исходный GitHub PR #49

Исходный PR: [#49 — Core voice/delivery/skills baseline and full Codex strategy handoff](https://github.com/BobIvans/scaling-chrome-extensions/pull/49).
Отдельная ветка: `codex/pr016-017-codex-continuation-20261004`.
Fork point: `9a4fd3acb4ac66a14a55656f60a4d0727a378fcd`; tree:
`940506feffe244b0131c5b6cab81fd241813d773`.
Сверка: 2026-10-04T16:55:03 UTC (19:55 Europe/Riga).
Точные machine-readable facts, hashes и CI URLs: `CONTINUATION_PROGRESS.json`.

## Что обнаружено и сохранено

PR #49 уже содержит implementation и предыдущий полный handoff. Приложенный
архив 8819240 bytes совпадает с `../original-strategy.zip` по SHA-256:
`7d42f5f65fc79d13e0c3ee6f0cf7043cee95909b14dca1b1b68f67efd6cd5c91`.
Все 170 members распакованы в `../source/`; все 11 уникальных nested ZIP —
в `../archives/`. Их 2132 файла / 45128005 bytes закреплены preservation manifest.
Nested duplicate archives сохраняют свои исходные refs и точные ZIP bytes.
В этой ветке source/archive/manifest/runtime bytes не изменяются.

Общий handoff из merged #53 также полностью наследуется: `docs/strategy/voice-agentos/`.
Его verifier подтверждает 1826 source files, 28056140 bytes и весь mapping
160 tasks / 164 features / 28 goals / 24 decisions. Эти два корпуса пересекаются;
количества не являются числом уникальных продуктовых требований.

Оригинальный отдельный 387402728-byte master ZIP отсутствует во входе, как явно
указано в provenance. Его selected extracts сохранены; остальная история не
объявляется прочитанной. Предыдущие audits и exact upstream #53 root handoffs
остаются на прежних путях. Root START до этой передачи сохранён отдельно в
`PR49_CODEX_START_HERE.md`; прежний MASTER полностью сохранён в новом root MASTER.

## Реализованное поведение и оставшийся scope

| Workstream | Actual owner / progress | Что продолжать |
|---|---|---|
| WS-018 intent | `content-lab/action_intent.py`: registry, `compile_intent`, `validate_dag`, `review_roles`, `LayaAdapter`; `action_runtime.py`: create/correct/admission | Полная typed role orchestration; mixed-effect steps, typed output refs и non-guessed critical slots; actual Laya |
| WS-019 voice | `desktop/voice.py`: Capture/WindowsHotkey/transcribe; `actions_ui.py`: preview/correction; independent Core STOP | Actual Dell mic/hotkey/ASR, release/sleep/unplug, focus/TTS, Narrator, latency/resource measurements |
| WS-021 targets | `content-lab/browser_cdp.py`: observe/canary/prepare/send/reconcile/read_result; immutable target checks в runtime | Реальный selected account/workspace/conversation canary и route receipts; uploads/clipboard/history/finalization coverage |
| WS-022 delivery | `action_runtime.py`: immutable parts/outbox/coverage, one local send invocation, crash/unknown reconciliation, correlated result import | Canonical PR014 packet integration, durable per-step recovery и mixed pipeline; actual upload/history/finalization evidence |
| WS-020 skills | `action_runtime.py`: record/qualify/invalidate/failure/invoke/optimize | Parameterized portability, scoped demonstrations, complete independent normal/unseen/fault checks и selective repair |
| Core/integration | `automation_core.py`, `workflow_state.py`, Native/desktop/durable bridge, both installers | Сохранить one canonical SQLite/jobs/leases/writer, shared STOP/capacity, installed dependency hashes и existing panels/routes |

Code inspection повторно подтверждает конкретный первый пробел:
`compile_intent()` требует одинаковый effect class для каждого step;
`ActionRuntime.run()` возвращает общий список outcomes, не реализуя полную
persisted per-step input/output dependency orchestration. `review_roles()`
валидирует data-only outputs, но не является сквозным pipeline.
Browser canary явно объявляет upload UNSUPPORTED; reconciliation по текущему DOM
не доказывает полную remote history; `data-finalized` требует actual UI contract.
Внешнее effect/device qualification из локальных fixtures не выводится.

Полный inherited function audit: 13 BASELINE, 23 PARTIAL, 7 DEVICE_OPEN,
6 UI_OPEN, 1 NOT_USED. Пути всех 50 записей существуют в checkout. Это повторная
проверка пути/ключевых owners; прежние code-status labels не преобразованы в
приёмку критериев. Все 220 original criterion IDs и wording неизменны и OPEN.

## Upstream и состояние PR

Main при сверке: `ccf73e747e6743ead68040e3eb6837b3a5233fbc`.
PR #49: OPEN, DRAFT, mergeable=true, merged=false; conflicts в этом head не
обнаружены по API. #47 (history/scan), #48 (release/campaign), #50 (context/Core/
Desktop) и #53 (общий roadmap handoff) merged. Их доступные owners уже находятся
в fork point. #51 source-ledger continuation остаётся отдельным OPEN/DRAFT;
его source/CAS/ASR/importer criteria не считаются выполненными только по названию PR.

Packet owners #50: `context_library.py`, `context_packets.py`, `context_runtime.py`,
`context_recovery.py`. Их actual API/version/source/namespace/hash semantics
проверять до нового adapter. Независимый typed planning можно реализовать сразу;
не создавать новый packet/source owner ради отсутствующего unified SourceAddress.
Prerequisites PR-013/014/015 и полные external task dependencies читать в
`../source/plan/DEPENDENCIES.json`, scope evidence сверять с actual contracts.
ROADMAP next_package=18 историчен: #48 merged, но broad downstream acceptance открыт.

## Проверки именно этой передачи

| Проверка | Результат и область |
|---|---|
| `python docs/strategies/pr016-017/verify_context.py` | PASS: все original/nested bytes, 220 criterion wordings |
| `python docs/strategy/voice-agentos/verify_integrity.py` | PASS: весь inherited roadmap corpus и requirement owners |
| `python -I -X utf8 desktop/package.py verify --shell desktop` | PASS: owned-file hashes |
| `python -m unittest discover -s content-lab -p 'test_action*.py' -v` | 32/32 PASS: actual SQLite/Core/admission/installed-layout plus browser doubles |
| `python -m unittest discover -s desktop/tests -p 'test_voice_actions.py' -v` | 6/6 PASS: actual IPC, synthetic capture; physical mic NOT_RUN |
| `python -m unittest discover -s desktop/tests -p 'test_context_workflow.py' -q` | 6 tests OK; 1 local Tk-display skip, 5 executed |

Inherited full regression results в `../VALIDATION.json`/исходном PR body являются
предыдущими результатами, а не новой полной suite этой документационной передачи.
Runtime здесь не меняется; полный regression и новый exact-head CI нужны после
последующих code changes согласно действующим workflows.

На source head `9a4fd3a` наблюдались пять successful checks: Ubuntu core,
Ubuntu/Windows context-platform и Ubuntu/Windows source-integrity.
Windows core оставался IN_PROGRESS. URLs и точный snapshot в `.json`.
Новая ветка с новыми docs имеет другой head; old-head CI не выдаётся за её CI.
Текущие workflows запускаются на main/specific push branches и PR events;
само создание continuation branch не обещает automatic CI или новый PR.

## Следующий этап и завершение

1. Выполнить весь `../NEXT_IMPLEMENTATION.md`: typed role DTOs; per-step effect
   checks и output refs; persisted checkpoint/restart; canonical packet adapter;
   shared correction/STOP/source/target/lease fences; Native/Desktop preview/status.
2. Провести его independent cases: real Git/SQLite to EOF, более 20 документов,
   stale/foreign refs/cycles/permission growth, restart на каждой границе,
   correction/STOP/source drift и possible-send crash без duplicate invocation.
3. Обновить criterion-specific evidence и продолжить remaining UI/voice/Laya/skills
   workstreams. По успешному этапу не объявлять весь 220-criterion пакет завершённым.
4. Сохранить общий roadmap и future/deferred goals; upstream/downstream критерии
   остаются на своих owners. Qualification требует подходящего real evidence.

Продолжать следует на новой ветке. Старый PR #49 не меняется от её commits.
Перед каждым продолжением fetch/live-check #49/main/#51; новый upstream progress
сохранить. Если #49 уже merged, сравнить main с fork point и интегрировать только
необходимый continuation diff без дублирования baseline. Текущая подготовка не
сливает и не перенаправляет PR; следующий code PR/merge — отдельный результат
coding-сессии в рамках её инструкции.
