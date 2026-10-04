# Исправления и уточнения предыдущих ответов

1. PowerShell, MCP и OpenHands могут запускать один и тот же pytest/Python. Это не три независимых метода проверки. Нужен реестр failure domains и diversity по underlying dependencies.
2. CDP и Playwright не должны одновременно нажимать в одной вкладке. Browser contexts [S03] изолируют browser session, но не один внешний аккаунт. Нужны foreground/resource leases и один write actor.
3. Majority/consensus нескольких AI не является verifier. Патч/вывод подтверждается task-specific evidence и независимыми checks.
4. Транзакционный откат для «любого действия» не существует как универсальная гарантия. Локальный SQLite commit в lab атомарен; публикации, платежи и внешние side effects требуют idempotency/reconciliation [S02].
5. 33ms Laya не гарантия всей voice pipeline и не замер Dell. Model card [S06] описывает ограничения/разную accuracy; small typed router не идеальный classifier.
6. Task/skill formats нельзя считать автоматически доступными в любом AI web tab. MCP extensions проверены в current specification [S16], поддержка negotiated per client.
7. Полный static call graph не следует из Tree-sitter AST. В SCE документировано Python/static и JS TEXT_ONLY; unresolved edges должны оставаться видимыми.
8. «20 entries» в SCE docs — scan page size, не общий library cap. Но другие explicit size/export caps есть и требуют streaming migration, а не удаления safety checks.
9. CI green, model DONE, build attestation, installed qualification и live market result — разные evidence types. Bot README прямо описывает ограничения.
10. Предыдущий файл `06_SOURCES.md` с заголовком Verified сохранён как historical artifact. Его неперепроверенные performance/version assertions не переиспользуются как проверенные факты. Текущий source registry отдельный.
11. Инструкции workflow JSON этого ZIP — наш canonical format, не подтверждённый native Laya import API. Автоматического исполнения или автоподключения привилегий от импорта нет.
12. Исходные полные личные архивы, прошлые ZIP и весь repo здесь не собраны; полный inventory ограничен фактически доступными файлами. Требования текущего чата собраны, а missing data указаны.

13. V3: single writer НЕ означает один recorder и не запрещает реальные disjoint effects. Multiple producers append concurrently; code writers могут быть в разных worktrees. Только одна conflicting external operation должна иметь одного effect owner.
14. screenpipe по текущему README source-available с отдельными license/telemetry условиями, не blanket unrestricted open source/offline.
15. Актуальная Laya model card предупреждает об action.act_probability и confidence; это не security authority.
