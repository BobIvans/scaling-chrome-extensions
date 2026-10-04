# Как разделить работу между параллельными чатами

Этот чат ведёт **ZIP-003 / LAYA4-010**: captured raw payloads → portable ZIP,
static offline index, stage/resume, verification и archive receipt.
Чат «Create First PR Zip» создал ZIP-001 и ZIP-002. Мы прочитали их актуальные
пакеты; оба документа заявляют PREPARED_IMPLEMENTATION_BRIEF, не actual merge.
Реализация из другого чата может быть новее — её нужно подтвердить ссылкой/receipt.

| Чат / роль | Пакет | Задача | Статус по доступным файлам | Передать дальше |
| --- | --- | --- | --- | --- |
| Create First PR Zip | PR-001 | scan controller / LAYA4-002 с related inputs | Package prepared; code/merge UNKNOWN | Actual SHA + scan result, если implemented |
| Create First PR Zip | PR-002 | manifest/range index / scoped LAYA4-009 | Package prepared; code/merge UNKNOWN | Actual SHA + BATCH/schema/validation result |
| Этот чат | PR-003 | ZIP/offline index/resume / scoped LAYA4-010 | Package prepared при выдаче | Этот ZIP, затем actual exporter receipt |
| Следующий выбранный пользователем чат | PR-004 | streaming inventory / LAYA4-003 | PLANNED_NOT_ASSIGNED | Master + actual progress table + №3 result |

Параллельно можно готовить документы №3/4. Исполнение №3 требует фактического
writer/data contract №2. При одновременном code build использовать отдельные
branches/worktrees, указать base SHA; общий repo_manifest owner сверить после
merge №2. Не делать один shared branch/writer на две независимые реализации.
Все номера PR-00N — package sequence; GitHub PR number записывать отдельно.

У меня нет автоматического доступа к живому ходу другого чата. Таблица
`plan/CHAT_ROUTING.json` — snapshot статуса, а не автоматическая синхронизация.
Передавать между чатами готовый ZIP, ссылку на PR или filled implementation
receipt; запись «готов» должна уточнять PACKAGE_READY, CODE_TESTED или MERGED.

Текст для другого чата:

> Продолжай только ROADMAP-PR-002 в BobIvans/scaling-chrome-extensions.
> Другой чат готовит PR-003 (LAYA4-010), поэтому не дублируй ZIP/resume exporter.
> После реализации передай actual base/head SHA, PR URL/status, implemented
> BATCH/entry/part schema, команды проверок и незакрытые критерии.

Текст для нового implementation-чата №3:

> Реализуй ROADMAP-PR-003 из этого ZIP. Начни с EXECUTE_THIS_PR_RU.txt.
> PR-002 result приложен отдельно; сначала сверить его actual SHA/контракты.
> Scope: foreground full captured export, atomic parts/resume, portable ZIP
> и offline index. Не повторять scan/manifest код. Сохрани actual result receipt.

Минимальная шапка статуса для любого чата: repo | package_id | source_task_id |
stage PACKAGE_READY/CODE_IN_PROGRESS/CODE_TESTED/PR_OPEN/MERGED |
actual base/head | GitHub PR URL | evidence | next unmet criterion.
`plan/CHAT_ROUTING.json` и `receipts/IMPLEMENTATION_RESULT_TEMPLATE.json` дают
машиночитаемые формы; их заполнение вручную не запускает workflow/Laya.
