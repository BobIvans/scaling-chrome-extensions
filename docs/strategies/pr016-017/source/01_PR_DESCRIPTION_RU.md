# ROADMAP-PR-016-017: Текст и голос → проверяемый план → выбранный Grok-чат → надёжная доставка → переносимые навыки

Пользователь задаёт цель текстом или push-to-talk, видит точные repo/destination/effect slots, исправляет их и запускает один план через существующий Core. План подготавливает все части контекста, привязывается к выбранному аккаунту и диалогу, сохраняет отправку до внешнего действия и импортирует только связанный завершённый ответ. Продемонстрированный сценарий становится версионированным навыком после проверки новых входов и сбоев.

Сейчас исходный roadmap описывает intent/voice и browser delivery отдельными пакетами. Этот PR объединяет WS-018, WS-019, WS-021, WS-022 и WS-020, чтобы correction, STOP, target identity, outbox и replay использовали общие operation/revision/fence contracts. Текущее наличие handlers надо установить по фактическому checkout; исторические snapshots не являются текущими доказательствами.

## Поведение после полной scoped приёмки

- Known command компилируется детерминированно; planner, retriever, critic и Laya возвращают отдельные типизированные proposals. Unknown capability формирует development request.
- Text и окончательный voice transcript дают одинаковую семантику плана. Push-to-talk владеет одним capture stream; keyboard/text путь и STOP работают при отказе ASR.
- TargetBinding хранит наблюдаемую account/workspace/conversation identity и ревизию. Tab ID служит временным указателем. Неоднозначность, новый чат или смена аккаунта блокируют дальнейший effect.
- Immutable packet и все part IDs входят в durable outbox. Draft, upload evidence, send observation, response observation и context-use claims различаются.
- Crash после возможного Send сохраняет EFFECT_UNKNOWN. Истёкший lease не разрешает повторный click; исход сверяется по history/operation evidence либо остаётся unresolved.
- Skill содержит только разрешённые наблюдаемые steps, версии зависимостей, recovery и qualification receipts. Drift и permission growth инвалидируют затронутые версии.

## Проверки

Runtime tests: NOT_RUN в этом ZIP. При реализации требуются golden parity/correction cases, fault injection вокруг Core transactions и Send, large multipart delivery с resume, Windows mic/keyboard/focus qualification, actual selected UI canary и skill unseen/fault replay. Полный список cases и матрица всех исходных критериев находятся в acceptance/.

## Интеграция

Переиспользовать SQLite/Core/jobs/leases/registry/grants/STOP из PR-015 и packet/retrieval contracts из PR-014. Media codec/ASR imports использовать через PR-013. Миграции additive и в одном canonical store. Feature flags вводят text, voice, bind/draft, delivery и skills по мере квалификации.

PR-018 владеет patch→worktree→PR/CI→merge→release/install/rollback. Здесь можно подготовить и передать development request; чужой AI-ответ не подтверждает merge или установленное обновление. PR-019 владеет долгими campaign scheduling; здесь его Core primitives переиспользуются.

Ограничения: Laya local interface и реальные UI controls/upload limits требуют наблюдения на выбранном устройстве и аккаунте. Schema JSON в архиве — контракт приложения, не обещание нативного импорта в Laya. Общая продуктовая готовность остаётся scope PR-021.
