# Разделение параллельных чатов

| Чат / пакет | Scope | Известный статус | Не дублировать в №6 |
| --- | --- | --- | --- |
| Create First PR Zip · №1/2 | Scan controller, raw manifest/ranges | Source ZIPs read; actual code/merge UNKNOWN | Scan/manifest rewrite |
| Create First PR Zip · №4 | Streaming inventory | USER_REPORTED scope; exact package not supplied | Inventory/Core long task/scale verifier |
| Этот чат · №3 | Portable captured ZIP/resume | PACKAGE_READY, проверка input/fixture PASS; code/merge UNKNOWN | Archive/resume implementation |
| «Сборка ZIP 5» · №5 | Source formats/gaps/whole-file text eligibility | USER_REPORTED in-progress; exact DTO UNKNOWN | Binary/LFS classifier повторно |
| Этот чат · №6 | Python groups/SCC/test-contract refs | PACKAGE_READY при выдаче; runtime NOT_RUN | Scope данного ZIP |
| Следующий чат · №7 | Один JS/TS/provenance adapter slice | PLANNED_NOT_ASSIGNED | New parser до выбора scope |

№6 сейчас — подготовка отдельного ZIP, code build не запущен. Пакеты можно
проектировать параллельно. Code №6 сверяет actual №2 и №5 state, меняет owners
в отдельной branch/worktree, затем rebase по merged base. Не использовать одну
shared branch или два writers для одного output directory.

Живые действия другого чата автоматически не видны. Передавать actual ZIP,
PR URL/head SHA или filled receipt. `plan/CHAT_ROUTING.json` — snapshot статуса,
не запущенный coordinator/scheduler. Number PR-006 — package sequence; GitHub
PR number отдельный nullable field. PACKAGE_READY/CODE_TESTED/MERGED различать.

Текст для №5:

> Продолжай только formats/gaps/source-level eligibility (LAYA4-004).
> №6 готовит Python groups/SCC. Передай actual source-wide text/code eligibility
> fields/schema/version/digest, handling binary/LFS, analysis revision binding,
> head SHA/PR URL и проверочные результаты. Не дублируй group planner.

Текст для implementation-чата №6:

> Реализуй только ROADMAP-PR-006. Начни с EXECUTE_THIS_PR_RU.txt.
> Сверь actual №5 adapter; exact schema сейчас не считается известной.
> Reuse Python graph/SCC, stable logical IDs, complete group raw refs и
> evidence-tagged related tests/contracts. Заполни actual result receipt.

Current canonical progress: repo | package_id | task_id | package/code/merge
state | actual base/head | typed contract revision | evidence | next gap.
