# Зависимости и owners

External packages: №11, №12, №13, №14, №15, №16, №17. Их наличие в roadmap не доказывает поставку кода. Требуемый input проверяется по exact version/receipt. Полный original source task DAG сохранён; source criterion с downstream dependency остаётся OPEN.

| Owner | Единственная область записи | Контракт с объединённым PR |
| --- | --- | --- |
| Existing SQLite/Core | authoritative jobs/events/schema | CAS revision и lease epoch; один migration coordinator |
| Git owner/integrator | worktree metadata/final branch | actual base + diff + final-tree verification |
| Desktop writer | session focus/input/clipboard | общий desktop mutex; разные tabs не независимы |
| Existing updater | active installation | staged binding, recovery marker, canary/rollback |
| Policy/effect ledger | grants, reservations, unknown effects | не наследовать более широкий scope из update/AI |
| Evidence/backup registry | lineage, restore, capability contracts | provenance и device-specific receipts |

Внутренний DAG: foundation WS-025 → WS-026; WS-023 использует leases/verifier; WS-024 использует WS-023 + data/registry prerequisites; WS-027 объединяет WS-023/024/025/026 и input из №16/17; WS-028 создаёт briefs независимо от installation, полный improvement loop ждёт gate WS-024. Это implementation ordering, не замена оригинальных зависимостей criteria.

В старых boundary briefs остались номера из прежнего плана. Здесь №32 → WS-023/PR-018, №33 → WS-024/PR-018, №34 → WS-025/PR-019, №35 → WS-026/PR-019; ссылка №34/35 — внутренние stages №19. Read-only history старого №20 относится к WS-011/PR-013; backup №23 — WS-014/PR-014; registry №26 — WS-017/PR-015. Авторитетный lookup: sources/plan/INTERNAL_36_WORKSTREAMS.json и briefs, а не номер в старом prose.

Merge/install/usable разделены. Разработка этого ZIP не включает runtime разрешение внешнего эффекта. Grant из пользовательского задания проверяется на конкретный scope и актуальную revision; дополнительные approvals не запрашиваются повторно, если уже действуют. Провайдерные и финансовые действия из PR-020 подключаются только через его собственные qualification gates.

Parallel chats передают: actual base SHA, proposed DTO revisions, owner, touched paths, source IDs, test receipts, unresolved effects. Один integrator согласует schema и final revision. Этот ZIP не утверждает автоматическую видимость соседних чатов.
