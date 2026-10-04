# Проверки и квалификация

qualification/TEST_CASES.json — именованный plan cases; каждый case содержит workstream, setup, action, expected и required environment. Все execution statuses пока NOT_RUN. Проверки структуры этого ZIP отдельно в verification/PACKAGE_CHECK.json.

Suites:

1. Unit: typed DTO/status mapping, point-in-time/freshness boundaries, units/fees rounding, atomic/delayed constraints, solver constraints, criterion accounting. Проверяют semantics, не повторяют реализацию строка-в-строку.
2. Integration: actual registry/owner bridge, immutable datasets, Core jobs/restart/cancel, artifacts и all-trial ledger. Fixture провайдера воспроизводим; real acquisition suite отдельная.
3. Stateful/fault: meaningful calls/depth/transitions, minimized failures; 429/401/disconnect, disk full/crash, source drift, duplicate result, unknown effects и stale leases.
4. End-to-end: final user verticals через installed shell и qualified adapters. Mock AI/UI не подтверждает Grok/Laya/devices.
5. Scale: >20 entries, deterministic tail sentinels и sizes above historic bounds; set equality/hash restoration; RAM/I/O/responsiveness, no silent truncation. Stopping at measured resource boundary leaves explicit pending items.
6. Windows: actual Dell Windows 11 installation/close Chrome/non-cwd/STOP/sleep/offline/reboot/restore/mic denial/focus/canary/rollback. Установочная подпись/permissions/updater определяются current product owner.
7. Utility: frozen corpus paired baselines/ablation, all-attempt costs, raw data/sample size и evidence families.
8. Closure: complete ID and criterion preservation, source dependencies, final revision applicability, blocked/deferred/stale handling, delivered/installed/usable distinction.

Перед implementation зафиксировать обязательные suites и target thresholds по baseline/corpus. Hard correctness failures: lost source/criterion, future input leak, wrong target effect, unauthorized mode escalation, repayment shortfall accepted, zero useful campaign calls accepted, double count opportunity/independent sample, blind retry unknown effect, cancelled resurrection, missing cost treated zero и stale receipt treated current.

Running repository tests: обнаружить actual project scripts/AGENTS.md; вписать exact commands в qualification/ACTUAL_COMMANDS.json. Здесь не выдуманы python module/pytest selectors/npm scripts. Выполнить meaningful targeted tests; затем required repository gates и integration cases на compatible final revisions. Новые faults оправдывают дополнительный прогон. Existing failures сохранять с baseline evidence, не выключать assertions ради зелёного CI.

Receipt fields: test case ID, source/build/device/adapter/config/dataset hashes, start/end UTC, invocation, exit/domain result, verified property, raw log/artifact digest и observed gaps. Fixtures и receipt schemas сами не доказывают запуск. Provider API key/user session values в raw logs не включать.

Повтор/restart/cancel/source-drift имеют отдельные expected outcomes во всех workstreams. Интеграционный matrix охватывает providing и consuming packages, а не только локальные helpers. Обязательные missing device/API evidence остаются named blockers, независимо от числа passing Linux tests.
