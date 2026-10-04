# Порядок интеграции: один проверяемый вертикальный срез

Обозначения `DESK-01…DESK-08` — внутренние workstream IDs, НЕ реальные GitHub PR numbers. Не увеличивать старую нумерацию волн и не считать work item merged без read-back.

## DESK-01 — Полный source manifest и raw archive

Расширить `content-lab/repo_context.py` и существующий canonical owner. Все tracked paths, bytes/oid/hash, ошибки/exclusions. Разделить raw collection и parser. Непрерывная пагинация до completion; 20 остаётся размером страницы. Добавить чтение большого blob потоково. Acceptance: >1 000 paths, >8 MiB source, binary/Unicode/LFS/link, restart/error, no silent missing.

## DESK-02 — Multi-part context export

Новый versioned bundle contract поверх raw owner. Никакого API break старого `context_pack`. Bundle содержит список всех частей, source refs, ranges, exclusions, full-text projection и reconstruction test. Acceptance: 21/101/1001 documents, exact byte coverage, no truncation; модельный token budget проверяется отдельно.

## DESK-03 — Desktop library без Chrome

Тонкий shell к существующему owner: source picker, library search, repository tree, context cart, status/preview и jobs. Native messaging остаётся optional adapter. Acceptance: основной вертикальный срез выполняется без установленного extension и без browser session.

## DESK-04 — Реестр фактических возможностей

Построить candidates из AST/entrypoints/scripts/CI/config; человек/тесты превращают candidates в approved profiles. Каждая запись хранит code owner, source revision, exact effects, inputs, outputs, pre/postconditions, isolation and timeout. Acceptance: неизвестная/устаревшая команда блокируется; catalog нельзя напрямую исполнять.

## DESK-05 — Qualification из desktop

Переиспользовать `qualification.inspect` / существующий bot bridge. Не делать второй `qualify_and_report`. UI показывает domain BLOCKED отдельно от transport error, сохраняет receipt и связанные source refs. Acceptance: exact-SHA drift test, installed mismatch test, unknown-outcome retry blocked, zero transactions.

## DESK-06 — Voice/text routing

Deterministic aliases first, ASR quality corpus, Laya/Jev advisory experiment, schema/policy gates. Модель вызывает те же capabilities, что текстовый UI. Acceptance: negation, number correction, interruption, RU/EN repo names, out-of-domain abstention; ни один adversarial test не получает money/signing права.

## DESK-07 — Skill learning и демонстрации

Capture authorized trace → explain effects → replay in isolation → independent verifier → draft skill → review → promote. Acceptance: UI drift and repeat-run tests, idempotency/compensation, permissions cannot increase via learned skill.

## DESK-08 — Параллельная sender-free R&D-кампания

Общий PIT data feed, независимые strategy workers, resource budgets, single canonical results owner, frozen experiment manifest и holdout. Acceptance: stop/restart/source failure, quota/backpressure, dedup, no doublecount costs, negative results retained. Live execution остаётся вне этого среза.

## Что объединять в один PR

Один coherent vertical slice DESK-01+02 с тестами/миграцией может быть одним PR. Desktop, voice, Windows automation и live trading нельзя объявлять готовыми заодно. На каждый следующий PR нужен demonstrated gap из актуального snapshot, а не очередной копирующийся большой roadmap.

## Definition of done для каждого шага

Source SHA и evidence; применённый diff; unit/integration/target tests с командой/средой; миграция/recovery; откат; docs; список NOT_RUN. При расхождении old chat vs current code текущий pinned code и воспроизводимый тест имеют приоритет, но исходная идея остаётся в history.
