# Полезность и закрытие V5

Полный source universe: 160 task records, 164 feature cards, 28 goal groups и 24 decisions. Непосредственная implementation ownership объединённого пакета: 13 задач, 35 feature cards и DEC5-23/24; остальные owners 010..019 сохраняются, WS-036 проверяет их конечные критерии. Это перекрывающиеся записи, не 376 уникальных функций.

coverage/CRITERION_LEDGER.json содержит каждый original criterion всех четырёх catalogs и восьми WS, с namespace/kind/source ID/ordinal/exact text/hash, owner, OPEN, пустым evidence list и next evidence. Canonical IDs создаются package layer детерминированно; native source IDs не переименованы. Criterion text не заменяется кратким summary. Если источник содержит отдельные existing native criterion IDs, сохранить в native_criterion_id.

Каждый parent record существует даже при нулевом числе source criteria: такой record получает OPEN_DEFINITION_GAP, не automatic pass. Source counts различают records и criteria. mapping owner — proposal, не выполнение.

Закрытие selected release scope: frozen mandatory IDs → actual receipts → verified_property/environment/revision checks → current applicable PASS. Отдельно вычислять V5-wide completeness по всему ledger. NOT_RUN/FAIL/BLOCKED/UNKNOWN/STALE/DEFERRED любого mandatory criterion блокируют соответствующий qualified claim. Narrow release допустим только с explicit limits и полным OPEN_BLOCKERS; его нельзя назвать full V5 complete.

Не считать документы, size ZIP, merged PR count, invented функция names или исторические 381/4830 tests критериями usability/profit. Delivered source, current CI, built artifact, installed candidate, functioning device capability и market-mode qualification имеют отдельные receipts.

Метрики benchmark:

| Показатель | Выводимость |
| --- | --- |
| Success rate | verified accepted outcomes / all started attempts; unknown/cancelled/failed сохранены |
| Completeness | exact source-ID sets + raw byte hashes + explicit pending/unsupported |
| Latency | speech/text accepted → context ready → queue → dispatch → verifier; p50/p95 с sample size |
| Cost per accepted outcome | total known incurred cost / verified accepted count; zero count = undefined, unknown costs явны |
| Product ROI | измеренное manual time saving минус setup/maintenance/review/failure overhead |
| Market edge | hypothetical net в pinned numeraire и assumptions; realized PnL только по actual confirmed fills outside these modes |
| Evidence strength | distinct lineage families и scope, без повторного счёта common upstream/fixture/test wrappers |

qualification/BENCHMARK_PLAN.json замораживает варианты и поля; thresholds пока BASELINE_REQUIRED, не придуманные измерения. Actual runs заполняют separate result artifact. Paired trials должны сохранять порядок, seed, corpus и одинаковые compute budgets; независимый holdout не просматривается до freeze.

Final report: implemented functions and file paths; tests/environment/revisions; ready properties; open blockers per criterion; physical PR/merge evidence; install/canary/rollback receipts; utility raw results; next useful experiment. Следующий brief создаётся из конкретного missing criterion, owner, input dataset/source и acceptance, не из произвольного расширения roadmap.
