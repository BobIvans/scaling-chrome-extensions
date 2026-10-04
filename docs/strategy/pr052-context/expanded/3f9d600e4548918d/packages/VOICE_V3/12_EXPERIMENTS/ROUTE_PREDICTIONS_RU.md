# Прогноз fastest route — до измерений, не результат benchmark

| Задача | Ожидаемый fastest useful route | Дополение / hedge | Почему может быть лучше | Где ожидание может не сработать |
|---|---|---|---|---|
| Известная voice command | primary ASR → rules/registered skill | Laya для нескольких допустимых intents | Нет большого coding-model roundtrip | ASR путает критическое имя/отрицание |
| Запись работы с AI | UIA/DOM event text + Git/terminal events | exports для полных histories; screenshot только gap fallback | Не обрабатывать каждый pixel постоянно | UIA provider неполный; DOM выгружает старые сообщения |
| Repo bug handoff | exact symbol/error search + actual test trace | static graph + decisions/history | Evidence достаточно до полного reindex | Dynamic edges/untracked changes не индексированы |
| Неизвестная автоматизация | approved planner → isolated skill candidate | second independent candidate только после need/latency trigger | Не писать новый skill при каждом повторе | Слабые tests дают false success |
| Сложный patch | 2 isolated candidates при достаточном budget | independent negative/property tests | Разные error paths могут дополнить друг друга | Общий неверный contract ломает обе модели |
| Большой архив | raw store + metadata immediately | async/progressive enrich and semantic views | Нельзя ждать все embeddings до первого поиска | Storage saturation; incomplete labels |
| Разбор команды RU/EN | один тёплый выбранный multilingual path | second ASR на спорных spans | Меньше memory contention и model reload | Второй engine повторяет те же ошибки |
| Browser task | official API or stable DOM action | UIA/vision только если structured path недоступен | Короче action graph | Endpoint нет/доступ отозван/remote state изменился |
| Повторный AI запрос | cached validated snapshot + delta | exact fresh dependency retrieval | Не пересылаем всю библиотеку | Cache stale, tokenizer budgets или provider differences |

Ни одного измеренного p50/p95 или verified success rate Dell в этом пакете нет. Скорость выдачи сырого первого ответа не является скоростью получения правильного контекста.

## Три сравниваемых профиля
P0 LOCAL_FAST: rules + exact/FTS + current source snapshot; один ASR; no ensemble default.
P1 QUALITY_PARALLEL: P0 + graph/history/retrieval complement, independent evidence checks.
P2 RECOVERY_HEDGE: P1 + delayed alternative source/model/candidate при gap/error/latency evidence.

Начальные лимиты эксперимента (не измеренная оптимальность): отдельный high-priority voice/control lane; один heavy local inference одновременно; до двух heavy worker candidates только при наличии RAM; небольшой ограниченный I/O pool. Подобрать реальные лимиты по p95 и peak memory на Dell; не выдумывать «загрузить все модели и будет быстрее».

## Как сравнивать
На одном фиксированном корпусе команд и одинаковом allowed data scope случайно чередовать P0/P1/P2. Отдельно учитывать warm/cold, network loss, backend outage, corrupted snapshot, missing context, repeated command, mixed RU/EN, interrupted user input. Не оптимизировать и отчитываться на том же holdout.

Метрики: first-useful-context latency; complete-evidence latency; verified task completion; source-span precision/recall на размеченных задачах; false status promotion; coverage known/unknown; cost per verified success; resource contention; external duplicate effects; user focus interruptions; correction latency.

Каждый маршрут получает co-failure matrix и marginal recovery score. Математика `1−product(1−p_i)` применима лишь при независимых событиях успеха и адекватном verifier. Для UIA/DOM одного сайта и двух wrappers одного Python такие предпосылки не даны.
