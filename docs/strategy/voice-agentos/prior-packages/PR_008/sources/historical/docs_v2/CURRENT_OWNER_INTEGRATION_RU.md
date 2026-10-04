# Текущий код и место интеграции

В этой итерации получены чистые локальные shallow checkouts и отдельно прочитаны GitHub refs. SCE: `da6abf4c006e4e7d26fe45ef30fa9d07a356f396`, 157 tracked entries. Studious: `d1c9f4bb54df9319697965ed7dbfb018698aeff3`, 2703 tracked entries. Это выбранные снимки для текущей упаковки, не обещание, что main останется таким после завершения работы.

В SCE проверены README, docs/automation/context-foundation.md, content-lab/repo_context.py, repo_source.py и context_review.py. Просмотр этих файлов подтверждает приведённое mapping; это ограниченный code read, не аудит всех функций и не повторный прогон всех repository tests.

| Возможность | Existing owner | Следующая доработка |
|---|---|---|
| Snapshot/cursor/Git bytes | content-lab/repo_context.py | Desktop вызывает scan до COMPLETE; streaming для oversize |
| Python AST/chunks/import graph/SCC | content-lab/repo_source.py | Correlated chunk views, labeled JS resolver, parser coverage |
| Search/catalog persistence | Content Lab + content.sqlite3 | UI queries, facets, user labels, index invalidation |
| AI request/results | content-lab/context_review.py | Handoff compiler, precise next-context requests, verified outcome adapter |
| Transport/operator scope | content-lab/native_adapter.py; agent-bridge/durable.mjs | Desktop transport к тем же owners |
| Repo UI | one-click-context/library/repo-review-ui.mjs | Переносимые компоненты интерфейса и desktop navigation |
| Queue/leases/cancel | Existing automation Core | Registered command adapters и durable jobs |

Текущие ограничения имеют разные значения: scan обрабатывает порции по 20; это не лимит корпуса. Blob больше 8 MiB получает явную ошибку. Repo export имеет ограниченную порцию текста с continuation; это транспортный/планировочный бюджет. Новая разработка должна сохранять видимость этих состояний и добавлять потоковый desktop-путь, а не просто менять число 20 на большое значение.

Переносимый прототип в `implementation/context_studio_v2` сохраняет полные Git bytes и JSON sidecar-каталог для испытаний. Он ещё не пишет в production content.sqlite3 и не подменяет existing ledger. Интеграционный следующий PR переносит UI orchestration и проверенные форматы к владельцам таблицы; source-of-truth остаётся один.

Studious chunking — чтение кода как данных. Ни один импорт исследуемого Python-модуля, тест бота, кампания или транзакция не нужны для получения контекстного пакета. Будущий capability discovery отделяет реальные CLI entrypoints от найденных обычных функций. Возможность автоматизировать тест/qualification получает typed arguments, declared effects, timeout, resource scope и observable verifier до допуска в auto mode.
