# Координация №3 и №4

| Package | Repo / task | Known status |
| --- | --- | --- |
| PR-001 | scaling-chrome-extensions / LAYA4-001 | Prepared input; build/merge not observed |
| PR-002 | scaling-chrome-extensions / LAYA4-009 | Prepared input; build/merge not observed |
| PR-003 | scaling-chrome-extensions / LAYA4-010 | User-reported in-progress other chat; ZIP not received |
| PR-004 | scaling-chrome-extensions / LAYA4-003 | This prepared CLI subset; runtime NOT_RUN |

PR-003 пишет captured payload exporter/index/recovery. PR-004 пишет
`repo_inventory.py` + небольшой opt-in hunk `start_scan`. Ни один не меняет
snapshot identity, chunk IDs/revisions/ranges или repo_heads completion semantics.
Если №3 тоже трогает `repo_context.py`, разделить функции/hunks при integration,
потом выполнить semantic capture→manifest→ZIP roundtrip в actual checkout.
Сходство имени файла не требует переписывать работу другого чата.

PR-003 должен брать фактически complete snapshot, никогда staging rows.
PR-004 READY — только полный inventory; raw chunks ещё нужно обработать pages.
Право использовать verified saved payload parts при resume принадлежит №3.
Прерванный Git enumeration №4 начинается с нуля после stop/reap, old snapshot
preserved. Numbering закреплён. Статус другого чата не наблюдается автоматически.

Нужны для фактической сверки: PR-003 ZIP или committed diff + exact SHA,
MANIFEST/receipt и команды runtime tests. Пока этих inputs нет, interoperability
отмечается PARTIAL/NOT_RUN; архивный и пользовательский контекст не заменяет CI.
