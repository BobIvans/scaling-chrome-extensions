# Scope, источники и открытые границы

Все source task/feature/decision/goal acceptance criteria сохранены буквально в acceptance/CRITERION_COVERAGE.json. Каждая строка имеет proposed owner, planned change, verification cases, evidence requirement и next action. Статус OPEN, current handler/evidence null: эта подготовка не утверждает проверку актуального кода.

Источники: оба предоставленных ZIP; task/decision/goal catalogs V5 из numbered roadmap; original feature cards из master; qualification/activation contracts из master. Внешняя проверка 2026-10-04: Microsoft RegisterHotKey, SYSTRAN faster-whisper README, официальная Grok Build overview. Ссылки/ограничения в evidence/EXTERNAL_SOURCES.json. Информация primary docs не доказывает installed capability или доступ выбранного аккаунта. Laya installed interface не найден/не прочитан; vendor import не утверждается. Grok browser controls не наблюдались в signed-in session.

Старые boundary ссылки №19/22/28/30/31/32 в workstreams относятся к прежней разбивке: media = WS-010/PR-013; immutable packet = WS-013/PR-014; voice = WS-019 внутри объединённого PR; target adapter = WS-021; durable send = WS-022; Git changes = WS-023/PR-018. Canonical IDs — WS и source task IDs. Эта таблица объясняет роли, не меняет исходные bytes или task DAG.

External package prerequisites остаются 013, 014, 015. Original task dependencies значительно шире package-level DAG; plan/DEPENDENCIES.json содержит каждое external task требование с completion owner из полного roadmap. Выполнять pure planning можно раньше, runtime/closure допускаются только по receipts каждого prerequisite.

GOAL5-16 release/source/assets, staged migration/rollback, installed registry не закрываются одним skill permission diff: primary completion owner PR-018 плюс PR-021. Остальные broad goals сохраняют downstream criteria до сквозной qualification. Полный backlog 160/164/24/28 сохранён в sources/numbered_roadmap; этот объединённый PR не равен закрытию всей стратегии.

Оценка часов не дана: actual diff/code ownership и Windows/UI measurements неизвестны. Один большой PR — желаемая единица поставки, не обещание часовой длительности. Device requirements сохраняются с owner и next evidence, даже если текущая среда позволяет проверить только fixtures.
