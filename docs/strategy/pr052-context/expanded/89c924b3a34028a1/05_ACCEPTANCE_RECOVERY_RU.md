# Проверки и критерии приёмки

Все исходные acceptance строки в coverage/CRITERION_LEDGER.json сохранены дословно. Для каждой записаны workstream, owner, source completion owner, test intent и next evidence. Ни одна строка не закрыта созданием документа. Сценарии fixtures/SCENARIOS.json требуют будущей реализации application tests; их наличие не доказывает выполнение.

Registered verifier сохраняет repo/source commit/tree/overlay, verifier/template version, environment и fixture hashes, result artifacts и applicability. CI для worker head не закрывает final integration tree. Применимость reused evidence должна быть отдельным объяснённым решением, обычно fresh run. Branch protection и required checks учитываются по actual repository settings coding-чата.

Fault injection выполняется на isolated data/device test target. Replay содержит durable events и actual active state, проверяет каждый переход вокруг dispatch/migration/activation/receipt. Expected outcomes сравниваются по evidence/effect counts, не по красивым status labels.

## Windows/Dell qualification

Снять Windows build, device/installation IDs, CPU/RAM/disk baseline, UI responsiveness и STOP latency. Сравнить serial baseline и разрешённые concurrency уровни на одном immutable workload: peak RAM, CPU/IO, duration, failures, foreground delay, leases/effects. Задать thresholds перед pilot; resource profile активировать только после pass. Невозможность measurements оставляет serial default и DEVICE_RECEIPT_REQUIRED.

Проверить keyboard-only start/pause/cancel/resume, локальный STOP и выбранный screen reader. Отсутствие ASR не мешает базовому пути. Sleep/wake, kill/restart и power-loss markers сверяются с actual process/build/data. Canary проверяет пользовательскую функцию на устройстве; unit/CI/mock receipts не заменяют её.

## Merge readiness против runtime readiness

Code gates: actual diff, scope, registered tests, CI итоговой revision, compatibility migration, source ledger и explicit gaps. Runtime update gates: release provenance, exact installed predecessor updater, baseline STOP, scoped grant, exact device/target, migration recovery. Usable gates: registry+binding+installed digest+device qualification+grant/revocation freshness. Новая capability не расширяет старый grant сама.

## Сборка ZIP

python tools/validate_package.py <путь-к-распакованному-пакету> проверяет hashes/JSON/schema fixtures/ID coverage и dependency refs. Это проверка документа; application tests и device tests имеют статус NOT_RUN. PACKAGE_VALIDATION.json перечисляет именно эти ограниченные проверки.

Отдельные исходные критерии features/goals/decisions и WS сохранены в coverage/FEATURE_GOAL_DECISION_WS_LEDGER.json. Они пересекаются с task criteria и не увеличивают число независимых функций. Встроенный полевой validator DTO проверен; внешний полный jsonschema validator в среде недоступен.
