# ROADMAP-PR-020-021: Web3 research bridge и доказуемое закрытие продукта V5

Сегодня сохранённые Web3 aims, datasets и qualification-результаты не образуют подтверждённый сквозной путь от команды в desktop до воспроизводимого experiment receipt и финальной оценки продукта. Объединённый PR подключает SCE к действующим Studious handlers, сохраняет provenance рыночных данных, выполняет зарегистрированные replay/paper research packs и показывает конкретные критерии готовности, пользу и оставшиеся blockers.

Пример конечного поведения: пользователь выбирает research aim в desktop, получает план с фактическими handler/config/dataset/build identities, запускает допустимый replay, видит все trials и расходы, затем повторяет experiment из immutable inputs. Текстовая или голосовая команда использует один IntentSpec. Отказ API, stale quote, отмена или отсутствие Windows receipt отображаются отдельным исходом. Статус final qualification выводится из receipts и исходных criteria.

## Изменения

- WS-029: каталог реальных CLI/function/test entrypoints и bridge к qualification owner Studious.
- WS-030: market acquisition broker, immutable datasets, freshness, point-in-time anchors, provenance и независимые views.
- WS-031: replay/paper campaigns, flashloan repayment/boundary/stateful corpus, fees/slippage/latency и frozen holdout.
- WS-032: atlas и research packs circular/triangular, liquidation+swap, stable peg/wrappers.
- WS-033: offline intent/clearing solver и отдельные cross-chain/basis/funding capital/time experiments.
- WS-034: Windows 11/Dell scale/fault qualification, text/voice/UI, install/update/rollback и архивные семьи.
- WS-035: frozen retrieval/coding/research benchmarks, baseline/ablation и cost всех attempts.
- WS-036: criterion-level reconciliation всех 160 задач, 164 feature cards, 28 целей и 24 решений V5; исправление подтверждённых integration defects.

## Архитектура и compatibility

SCE владеет контекстом, orchestration, references и UI. Studious владеет рыночной логикой, acquisition и qualification execution. Реальный mapping owners/paths фиксируется до diff; прототипы из исторического master не становятся вторыми production stores. Версии DTO и migrations проходят через текущих owners Core/SQLite/updater.

Основной code PR создаётся в SCE. Если необходим companion diff Studious, оба physical PR связываются одним integration manifest с точными supported revisions. Один package не означает один GitHub diff для двух репозиториев.

## Приёмка

1. Каждый dispatch связан с проверенным handler и mode; неизвестный entrypoint остаётся GAP, domain BLOCKED не превращается в success из-за exit code 0.
2. Replay воспроизводим по inputs/seed/clock/build, future available-time не попадает во входы решения; stale anchors инвалидируют зависимые verdicts.
3. Экономика выражена в совместимых integer units, неизвестная обязательная стоимость блокирует экономический PASS; отрицательные trials сохранены.
4. Atomic и delayed-capital модели имеют разные repayment/settlement contracts; paper/model results сохраняют своё происхождение.
5. Большой corpus учтён целиком, все хвосты/omissions и origins сохранены; stop/restart/unknown эффекты проходят отдельные cases.
6. Windows install/canary/rollback подтверждены receipts на фактическом устройстве; отсутствие устройства оставляет соответствующие criteria NOT_RUN.
7. Полный ledger не теряет исходные IDs/criteria. DEFERRED, BLOCKED и UNKNOWN остаются открытыми. Release-qualified claim требует действительных mandatory receipts на final revision.

## Validation для будущего PR

В PR приложить actual test commands и outputs, exact repo/build/config/dataset hashes, replay digests, stateful call/transition counters, all-trial registry, provider acquisition receipt, benchmark raw attempts и Windows installation/recovery receipts. Эта спецификация содержит plan и package checks; она не заявляет, что эти runtime проверки уже прошли.

Секция результатов заполняется coding-agent по фактическому запуску: implemented functions, changed paths, test results, physical PR URL(s), merge/final SHA, limitations и named blockers. До такого запуска validation status остаётся NOT_RUN.
