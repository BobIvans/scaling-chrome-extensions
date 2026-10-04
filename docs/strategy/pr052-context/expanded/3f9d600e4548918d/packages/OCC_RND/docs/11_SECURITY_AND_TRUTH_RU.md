# Безопасность, достоверность и границы обещаний

## Основная матрица статусов

`AVAILABLE` — файл/возможность найдены. `IMPLEMENTED` — есть код. `TESTED_FIXTURE` — тест пройден на синтетике. `TESTED_TARGET` — тест пройден на нужной установке/данных. `VERIFIED_OUTCOME` — независимая проверка подтвердила конкретный результат. `QUALIFIED_FOR_PROFILE` — выполнены зафиксированные требования конкретного профиля. Ни один из них сам по себе не означает «решает всё».

Источники доказательств различать: read code, unit test, integration test, local run, simulation, real-market observation, realized execution. LLM explanation и высокий router confidence — не отдельный вид фактического подтверждения.

## Не убирать защиту вместе с лимитами

Можно убрать общий искусственный потолок числа документов, сохранив размеры транзакций, process timeout, budget, boundaries, stop, permissions и секрет-фильтрацию при отправке. Полнота обеспечивается resumable processing и status ledger, а не бесконтрольным чтением всей RAM/диска.

Два режима: local raw archive и shareable projection. Проекция должна перечислять redactions/exclusions и hashes исходников, но не публиковать содержимое секретов. Secret-name heuristic приложенного инструмента недостаточен для публичной публикации; automated secure share пока не реализован.

## Unknown side effects

Если subprocess/UI action завершились с неизвестным итогом, состояние `RECONCILIATION_REQUIRED`. Повторить клик «купить», публикацию или отправку транзакции автоматически нельзя. Для safe retry нужна операция с idempotency key либо проверка фактического состояния и однозначный compensating action.

Модель не повышает concurrency, расход, доступ к новым root/URL, production target или signer. Policy change — отдельный reviewable artifact. Рекурсивно generated skills не могут самостоятельно подписывать свой admission.

## Sandbox и доступ к ПК

Worktree — не sandbox. `shell=False` — не sandbox. Python `-I` — не sandbox. UIA доступ к приложению — реальные пользовательские права. Для unknown code ограничивать сеть, filesystem, процессы и credentials в настоящей изоляции, проверенной на целевом host.

Не импортировать browser session/cookie backups в AI context по умолчанию. В старых идеях был Colab Chrome-profile archive; он может сохранять аутентифицированные сессии и должен иметь отдельный, более строгий threat model.

## R&D не равен working product

Приложенный desktop — прототип запуска архивных операций. У него нет production installer/signing/updater, полноценного cancellation/job-object layer, accessibility certification, rich library editor, терминала, ASR, API keys или торгового engine. Полнота roadmap — не полнота реализации.
