# Продолжение после №5

№6 сохраняет исходный planned scope: related Python code/tests/contracts и SCC
grouping (`LAYA4-008`). Его нужно адаптировать к actual №1–5 results; format
facts помогают включать text и показывать raw/gaps, а не терять неудобные files.
№7 — отдельные JS/TS resolver/provenance slices (`LAYA4-005/006/007`).
Полная inherited очередь №2–20: previous/pr002/previous/PR_001_NEXT_ZIPS_RU.md.

| Followup | Почему нужен | Статус |
| --- | --- | --- |
| PR004-F01 | Long inventory Native/Core job вместо timeout | OPEN / user-reported gap |
| PR004-F02 | Bounded Git index comparison | OPEN / user-reported gap |
| PR005-F01 | Stream large blobs вместо existing 8 MiB error | OPEN |
| PR005-F02 | Verify local LFS payload availability отдельно от pointer | OPEN |
| SCALE-F01 | Full proof/delta/listing/selection scale | OPEN |
| QUAL-F01 | Installed Windows memory/latency/accessibility | NOT_RUN |

Эти followups могут получить самостоятельные будущие пакеты после owner audit.
Номер следующего ZIP не перезаписывать молча: передавать PACKAGE_REGISTRY и
scope, original task IDs, exact base/head и observed PR URLs. №3/4 создаются
другими чатами по сообщению пользователя; их новые ZIP/links надо передавать
явно. Status одного design archive не подтверждает code/merge/CI другого.

Sources/roadmap_v5 хранит все 160 задач, 164 feature definitions, goal/decision/
milestone registers из master. Большие historical object bytes/master ~387 MB
compressed здесь не дублируются; original attachment остаётся source со своим
exact hash в provenance. Этот ZIP — scoped implementation handoff, не новый
полный master corpus. All unmet work remains in source registries.
