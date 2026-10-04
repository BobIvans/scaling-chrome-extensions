# PR-018-019: проверенное обновление приложения и восстанавливаемые R&D кампании

Сейчас AI-ответ, зелёные тесты рабочего branch и скачанный release могут описывать разные ревизии. Долгая кампания после сна или restart может потерять связь с исходным snapshot, владельцем ресурса и судьбой внешнего эффекта. Объединённая поставка должна связать каждый переход с точным input, owner, revision и receipt.

Пользователь запускает кампанию по текстовой цели. Core фиксирует контекст, допускает независимые ветви с учётом ресурсов, собирает реальные patches и через одного integrator проверяет итоговое дерево. Merge observer подтверждает результат merge/squash/rebase или ручного commit. Updater получает связанный с этой ревизией asset, проводит rehearsal, переключает версию только на безопасной границе и подтверждает installed state. Device canary определяет пригодность конкретных capabilities. Прерванная кампания сначала сверяет неизвестные эффекты, затем продолжает валидные узлы. Следующий brief формируется из фактических gaps, включая negative trials, без потери прежних goal IDs.

## Изменения в одном PR

- WS-023: worktree/source fence, registered verification, final-tree CI, merge observer и manual assertion reconciliation.
- WS-024: build/release provenance, exact asset staging, migration rehearsal, quiescence, installed receipt, canary и проверенный rollback.
- WS-025: durable schedules, occurrence identity, Europe/Riga DST, offline catch-up, budgets и checkpoint eligibility.
- WS-026: canonical resource identities, atomic leases/reservations, fencing, conflict graph и измеряемый admission.
- WS-027: immutable campaign DAG, shared evidence/cache, branch joins, selective invalidation, serial effect commit и доступная очередь.
- WS-028: claim lineage, primary-source references, experiment proposals, bounded improvement loop и next PR briefs.

## Пример результата

Worker A прошёл тесты на head H1, затем base изменился. H1 не становится пригодным к установке: integrator создаёт новое итоговое дерево H2, повторяет применимые проверки и фиксирует fresh receipts. После squash результат M может отличаться от H2 по SHA; observer проверяет фактическую связь изменения и итоговое дерево. Release из более нового commit R квалифицируется на R. Только asset digest R + installed receipt + device qualification + действующий grant могут дать usable.

## Критерии закрытия

Покрыты все исходные критерии выбранных задач; широкие downstream критерии сохраняются OPEN до нужных receipts. Проверены duplicate/reordered events, base drift, power loss, отмена, unknown effects, stale fencing, DST, budget и selective resume. На Windows подтверждены keyboard STOP, recovery и доступная очередь. Тесты интегрированного дерева записаны отдельно от worker tests и canary.

## Проверки и статус документа

Это проект описания будущего PR. Выполнена только проверка целостности и покрытия данного ZIP. Поля actual tests, CI, commit, installed build и device qualification заполняет coding-чат после исполнения; здесь они NOT_RUN/UNKNOWN. Число пакетов не означает фиксированное число часов работы.
