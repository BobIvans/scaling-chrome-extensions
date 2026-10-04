# ROADMAP PR-012 + PR-013 — продолжение GitHub PR #51

**Полный жизненный цикл источников: durable repo jobs, streaming/paging, delta/CAS и provenance-aware importers.**

Начать с [CODEX_START_HERE.md](CODEX_START_HERE.md), затем прочитать
[MASTER_CONTEXT.md](MASTER_CONTEXT.md). Активная ветка при подготовке:
`codex/pr012-013-source-ledger-continuation`,
[GitHub PR #51](https://github.com/BobIvans/scaling-chrome-extensions/pull/51).
Roadmap №012/013 и GitHub №47/51 — разные системы нумерации.

Все 19 файлов приложенного ZIP сохранены побайтно в `input/`, точный архив —
в `originals/`. Здесь 6 workstreams, 10 task cards, 15 feature cards и 15
feature-audit records, 6 goals, 2 decisions, 101 criterion и 15 acceptance cases.
`audit/` содержит отдельную актуальную сверку и полный открытый criterion ledger;
исходные плановые статусы в `input/` не переписаны.

Проверка сохранности: `python docs/strategy/pr012-013/verify_integrity.py`.
Полный более широкий roadmap и ранее переданные inputs находятся в
`docs/strategy/voice-agentos/`. Ограничения доступного master archive указаны
в `MASTER_CONTEXT.md`; отсутствующие исходники не объявляются сохранёнными.
