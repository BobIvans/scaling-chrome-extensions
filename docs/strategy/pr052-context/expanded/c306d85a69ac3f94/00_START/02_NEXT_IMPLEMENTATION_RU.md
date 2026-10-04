V3 УТОЧНЕНИЕ: multi-producer recording и независимые effect resources параллельны. Single writer относится только к одному конфликтующему effect target. Главная схема: 00_START/00_PARALLEL_CAPTURE_DECISION_RU.md.

# Следующая реализация: 8 work items, не номера существующих PR

Сначала прочитать current code/exact commit. Документы репозитория уже указывают на существующие owners — повторно не создавать queue/store. В этом выполнении ветки, PR, merge не создавались.

## CTX-PAR-01 — Preserve existing owners + trustworthy context intake
Подключить desktop client к existing SCE service owner, не создавать вторую queue/database. На pinned current source проверить documented scan/export caps; добавить streaming progress/coverage/error ledger.

Приёмка: Raw bytes и provenance survive restart; more-than-20 не обрывается; no scanned code execution.

Связи: RND-23 RND-27 RND-35.

## CTX-PAR-02 — Goal-bound handoff and labeling
IntentSpec из текста, evidence requirements, authority-aware tags и provider-neutral HandoffBundle. UI показывает краткое WHY_THIS_PACKET, sources и omissions.

Приёмка: Required missing evidence возвращает NEEDS_CONTEXT; приватные источники не уходят provider без scope.

Связи: RND-24 RND-25 RND-36 RND-40.

## CTX-PAR-03 — Read/candidate races with real diversity
Failure-domain registry, serial/eager/hedged comparator, budgets и cancellation receipts. Вначале только чтение и подготовка artifacts.

Приёмка: First invalid answer rejected; co-failure recorded; loser cancel confirmed; deadline не приводит к effect.

Связи: RND-19 RND-20 RND-32.

## CTX-PAR-04 — Effect broker and resource ownership
Target revision, operation ID, single writer, leases/fencing and unknown-effect reconciliation. Existing Core must remain authority.

Приёмка: Same intent duplicate produces one local effect; external unknown не повторяется вслепую; foreground user wins.

Связи: RND-21 RND-22 RND-30 RND-33.

## CTX-PAR-05 — Studious evidence vertical
Registered inspection/test adapter, source-bound failure triage, exact-head evidence, независимые fix criteria. Не интегрировать signer/sender.

Приёмка: Одна команда создаёт проверяемый failure/context handoff; не выдает fixture/test green за market qualification.

Связи: RND-23 RND-24 RND-28 RND-37.

## CTX-PAR-06 — Voice and accessibility adapter
Push-to-talk/optional wake + critical-slot checks, separate stop path, live command preview, RU/EN project aliases.

Приёмка: Same typed input contract as text; false activation/negation errors measured; installed Dell receipt captured.

Связи: RND-29 RND-30.

## CTX-PAR-07 — Safe skill factory and updater
Unknown action → isolated candidate code → independent tests → reviewable package → permission diff → staged activation.

Приёмка: First run may use coder, known replay uses qualified skill; new permissions never auto-granted; no core overwrite while running.

Связи: RND-31 RND-38 RND-39 RND-41.

## CTX-PAR-08 — Offline optimization and portfolio learning
Контекстные ablations, skill minimization, held-out evaluation DSPy/GEPA candidates. Реальные traces снабжают offline optimizer.

Приёмка: No holdout leakage; promotion only on verified outcomes and unchanged policy constraints; rollback retained.

Связи: RND-26 RND-38 RND-42.

## Что отдавать coding AI первым
Первое изменение должно сделать рабочим только выбранный вертикальный сценарий. Не нужно одновременно добавлять Temporal, Graphiti, LanceDB, UFO, 5 моделей и новый shell runtime. 225 функций в backlog — карта возможностей, не требование создавать 225 пустых wrappers.

Документ `08_HANDOFF/FIRST_DOCUMENT_TO_ANY_AI_RU.txt` содержит scope и требования к ответу. В контекст следующей модели добавить исходный код exact snapshot, а не только этот план. Отсутствующий код должен вернуть NEEDS_CONTEXT, не придуманную реализацию.
