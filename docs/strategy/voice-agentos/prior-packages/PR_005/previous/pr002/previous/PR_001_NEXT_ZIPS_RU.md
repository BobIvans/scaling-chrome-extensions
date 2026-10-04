# Очередь продолжения стратегии после первого PR

Сейчас создан только ZIP-001. Таблица ниже — порядок кандидатов, а не список
опубликованных PR, новых файлов или уже выполненных функций. Новые пакеты
формируются на actual HEAD и evidence предыдущего PR; очередная реализация
не включает весь master backlog.

Следующий пакет: **ZIP-002 — manifest всех chunks и обратный source-to-range
индекс** поверх snapshot/cursor, полученного в PR-001. После него ZIP-003
собирает полный portable context archive с atomic resume. Это последовательные
части широкого «собрать весь repo», а не отмена исходной цели.

| Следующий пакет | Пользовательский прирост | Source task IDs | Scope / граница |
| --- | --- | --- | --- |
| ZIP-002 | Manifest всех chunks и source-to-range индекс | LAYA4-009 | Детерминированный JSONL ledger + bounded reader; доказать source↔chunk ranges и hashes. Полный ZIP builder ещё отдельно. |
| ZIP-003 | Portable ZIP, offline index и atomic resume export | LAYA4-010 | Staged parts, content hashes, crash/disk-full recovery; portable relative links. Использовать manifest ZIP-002. |
| ZIP-004 | Streaming Git inventory | LAYA4-003 | Tree выше прежнего 32 MiB output limit; NUL-safe entries, bounded buffers и explicit resource budgets. |
| ZIP-005 | Форматы, gaps и source eligibility | LAYA4-004 | LFS pointer/payload, links/submodules, encoding/oversize/protected cases и прозрачная eligibility projection. |
| ZIP-006 | Связанные Python code/tests/contracts группы | LAYA4-008 | Reuse current static graph/SCC; oversized group continuations, unresolved links. Проверить полезность по frozen task corpus. |
| ZIP-007 | JS/TS resolver и provenance edges | LAYA4-005, LAYA4-006, LAYA4-007 | Разделить по parser/alias/provenance adapters после code audit; это направление может требовать нескольких PR. |
| ZIP-008 | Desktop transport и Windows packaging spike | ACTION5-01, ACTION5-02, ACTION5-03, TAB4-01 | Выбрать shell/typed IPC к тем же owners; install/reconnect/closed-Chrome receipt. Сначала минимальный proof. |
| ZIP-009 | Original/source revisions и import fidelity | ACTION5-04, ACTION5-05, ACTION5-06 | Один формат/importer за PR; attachments/branches/gaps сохраняются. При миграции единый owner. |
| ZIP-010 | Search, точные ranges и ручные labels | ACTION5-07, ACTION5-08, ACTION5-09, LAYA4-013, LAYA4-014, LAYA4-015 | Frozen retrieval cases, source links, manual override. Объём среза определить по existing search API. |
| ZIP-011 | Task/result roundtrip и долгий контекст | LAYA4-016, LAYA4-017, LAYA4-018, ACTION5-10, ACTION5-11, ACTION5-12, ACTION5-13, ACTION5-14, ACTION5-15 | Reuse V4 task/review code; проверить actual missing criteria; не переписывать already delivered cycle. |
| ZIP-012 | Привязка указанных Grok/GitHub targets | TAB4-02, TAB4-03, TAB4-04 | Target discovery и changed-account/chat/repo canary. Начать с manual transfer уже готового small TASK. |
| ZIP-013 | Grok UI transfer observations и recovery | TAB4-05, TAB4-06, TAB4-07, TAB4-08, TAB4-09, TAB4-19 | Draft/part receipts и unknown-send reconciliation на целевом устройстве; limits измерить отдельно. |
| ZIP-014 | Merge observer и staged candidate qualification | TAB4-10, TAB4-11, TAB4-12, TAB4-13 | Exact repo/final tree/CI evidence, declared local tests. Merge не означает installed capability. |
| ZIP-015 | Installed update и rollback | TAB4-14, TAB4-15, TAB4-21, ACTION5-16, ACTION5-17 | Build/source manifest, data migration rehearsal, actual installed receipt и canary. Разбить после updater owner audit. |
| ZIP-016 | Текст → registered capability plan | ACTION5-18, ACTION5-21, ACTION5-22, ACTION5-23, ACTION5-24 | Typed intent/slots, text STOP, unsupported capability → конкретный R&D brief. Один action adapter за PR. |
| ZIP-017 | Голос поверх проверенного текстового пути | ACTION5-19, ACTION5-20, TAB4-16, LAYA4-022, LAYA4-023 | Push-to-talk + RU/EN correction; fixed action registry. Laya JSON остаётся proposal до actual adapter qualification. |
| ZIP-018 | Restart schedules и qualification parallelism | ACTION5-25, ACTION5-26, PAR3-004, PAR3-006, PAR3-007, PAR3-008 | Catch-up/leases/budgets/fault receipts поверх existing Core. Один controlled serial pilot прежде broad parallel scheduling. |
| ZIP-019 | Web3 read-only/replay/paper bridge | ACTION5-27, ACTION5-28 | Exact Studious entrypoints + immutable dataset/config + sender-free replay/paper receipt. Не исполнять обычные найденные функции. |
| ZIP-020 | R&D feedback и usefulness qualification | ACTION5-29, ACTION5-30 | Negative trials, holdout/costs и source-linked next brief; device/corpus metrics и реальная польза. |

## Как пользоваться очередью

Для ZIP-002..006 сначала проверить owners и выбрать один проверяемый контракт.
Для дальнейших broad directions потребуется additional slicing; таблица не
обещает выполнить весь набор перечисленных tasks за один час. Перед build
заморозить input/output, критерии и candidate touched paths, затем дать
implementation prompt на actual baseline. Не назначать новые GitHub PR numbers
до их создания и не перескакивать на UI send/installed claims без evidence.

Desktop packaging можно исследовать независимо от full chunk export, а
manual TASK/result cycle V4 переиспользовать уже сейчас при наличии его кода.
Это техническая независимость работ; пакет не запускает параллельных агентов
или production scheduler.

## Что сохранено из большого master

В `sources/roadmap_v5/` находятся исходные 160 task cards, 164 feature definitions,
28 goal groups, 24 decisions и 10 milestones, а также latest implementation
brief и expanded roadmap. Это overlapping каталоги, их counts не складываются
как число уникальных code capabilities. `plan/ROADMAP_DISPOSITION.json` содержит
по одной записи на каждую из 160 tasks и ссылку на полный исходный каталог.
Для каждой указан SCOPED_INPUT или OUTSIDE_PR001; ни одна широкая task не
помечена выполненной этим пакетом. Связи goals/features/milestones остаются
в preserved registries, включая темы, не вошедшие в таблицу первых кандидатов.

Большие original ZIP, бинарные objects и весь исторический корпус ~970 MB
распакованного содержимого не продублированы. Master ZIP остаётся исходником;
его precise hash, size и selected byte-preserved members доступны в provenance.
Missing V4 code/current HEAD/Windows/Laya/provider observations остаются gaps.

## Связь с web3 стратегией

PR-001 позволяет учитывать код `studious-pancake` как pinned input без запуска
бота. PR-002/003 дадут source-linked context handoff для следующих исследований.
Далее existing registered qualification commands можно связать с библиотекой
через отдельный read-only/replay/paper adapter: данные → frozen config →
evidence → unmet criterion → следующий code brief. Future arbitrage/market feeds
и live execution выбираются в самостоятельном Studious PR на его actual code,
а не появляются автоматически после merge context controller.
