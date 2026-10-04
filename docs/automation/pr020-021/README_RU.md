# ROADMAP-PR-020 + ROADMAP-PR-021 — единый пакет, офлайн-срез реализации

Реализован запуск пяти исследовательских моделей через существующий Core SCE с точным Studious owner, сохранением всех исходных критериев и чтением результатов в Desktop. Полный объединённый пакет остаётся **PARTIAL**. Неподтверждённые функции перечислены в `CAPABILITY_MAPPING.json`: все 47 исходных идентификаторов сохранены вместе с точными ограничениями реализации.

SCE владеет SQLite-заданиями, операторскими профилями, очередью, отменой, lease и контекстом. Studious владеет рыночными расчётами и JSONL trial ledger. Новый `studious_research` — зарегистрированный тип задания Core с одной попыткой. Задание содержит только имя профиля; argv, файлы, SHA, Python, timeout и output root принадлежат проверенному операторскому policy. Денежный бюджет — 0, `max_parallel=1`.

`research_bridge.run` вызывает фиксированный `scripts/run_research_qualification.py` через `Core.command` с `-I -X utf8`. Запрос сохраняется до запуска, output находится вне checkout и store. Studious проверяет чистый точный Git SHA до и после работы. Core сохраняет раздельно `process_exit_code`, `domain_status`, количества строк и вызовов, ссылки-хеши и verified property. Положительный exit code процесса здесь не используется; exit code 0 сам по себе не даёт успеха кампании.

При `MODEL_REPLAY_COMPLETED` Core ставит техническое `SUCCEEDED`. Это завершение офлайн-вычисления: `qualified=false`, `release_authorized=false`, `live_enabled=false`, `transactions_sent=0`. `PARTIAL`, `INVALID_CAMPAIGN`, drift, неизвестный исход и timeout не превращаются в успех. `useful_calls` считает завершившиеся проверки домена, включая полезные отрицательные исходы; FAILED-вызовы считаются отдельно в `handler_calls` и trial ledger.

После истечения lease никакого повторного market dispatch нет. `reconcile-research --process-stopped` допускает только readback применимого завершённого receipt с checkpoint запроса; отмена имеет приоритет. Если завершённого receipt нет, используется существующий `abandon-orphan` после подтверждения остановки процесса. Это явная проверка оператора, а не автоматическая догадка.

Desktop получает только scoped read-only `durable.research.jobs`. Кнопка «Исследования» показывает страницы по 20 строк и весь хвост, без общего лимита 20. SHA состояния списка блокирует смешивание страниц после изменений. Read path не создаёт Core, БД, схемы или worker. На экране отсутствуют policy, paths, lease tokens, команды и исходные данные. Штатный установщик копирует новые sibling-модули; на локальном тесте реально использован этот установленный layout с изолированным subprocess.

## Канонический реестр и закрытие

`CRITERION_LEDGER.json` перенесён из выданного объединённого архива без изменения байтов. Он содержит 1 133 точных критерия из 160 задач, 164 feature cards, 28 целей, 24 решений и 8 workstreams. Импорт проверяет ожидаемый хеш, уникальность ID, хеш точного текста и полноту количества. Таблицы qualification находятся в **той же `content.sqlite3`**. Отдельного state store или runtime нет.

Claim неизменяемый и связан с точными build/config/dataset/environment. Отчёт сохраняет OPEN, NOT_RUN, FAIL, BLOCKED, DEFERRED и CONFLICT. DEFERRED не уменьшает знаменатель. Несогласующиеся claims конфликтуют; устаревшие scope не применяются. Произвольный PASS отвергается. Проверенный replay-факт сохраняется отдельно и не закрывает произвольный семантический V5-критерий. `delivered`, `installed`, `usable` остаются неизвестными до применимых доказательств.

`product_qualification.benchmark` считает стоимость и время всех переданных начатых попыток, в том числе FAILED/CANCELLED/BLOCKED. Нулевой useful denominator остаётся неопределённым. Этот evaluator не удостоверяет входные метрики и не заменяет baseline/ablation benchmark.

## Как выполнить локальную проверку

Примените два подготовленных patch в соответствующие репозитории. Точные исходные base и owner commit указаны в handoff-пакете. Зависимости Studious установите в Python 3.13 environment согласно его hash lock на Linux или version-pinned Windows profile. Owner checkout должен быть чистым, выходная папка — новой и вне обоих checkout:

```sh
python docs/automation/pr020-021/verify_linked_replay.py \
  --studious /absolute/studious-pancake \
  --source-commit 905976ebd3046121728161d42f2e781c01f53e10 \
  --python /absolute/python-environment/python \
  --work-dir /absolute/new-qualification-output
```

Driver реально запускает Core → Studious subprocess → проверку receipt → установленный Native adapter → Desktop client. Пять pack проходят дважды; по 47 записей в кампании, включая будущую запись и FAILED-вызов. Итого 470 строк, 450 полезных доменных проверок, пять точных пар trial digest. Затем все 1 133 критерия остаются OPEN. Это положительная проверка интеграции модели, а не доказательство реального рынка.

```sh
python content-lab/product_qualification.py --store /absolute/store import \
  --catalog docs/automation/pr020-021/CRITERION_LEDGER.json --sha256 <exact-file-sha256>
python content-lab/product_qualification.py --store /absolute/store reconcile \
  --catalog-sha256 <same-sha256> --scope /absolute/current-scope.json --output /absolute/new-report.json
```

Scope JSON содержит ровно `build`, `config`, `dataset`, `environment`. Профиль реального оператора создаётся только после проверки установленного Python, чистого checkout и фактических файлов. Для enqueue/work используются существующие команды `content-lab/automation_core.py`. Полный рабочий пример профиля и policy создаётся integration driver в выбранной внешней папке.

## Открытые части всей стратегии

| Workstream | Этот срез | Ещё нужны |
|---|---|---|
| WS-029 | Каталог реальных owners, REPLAY bridge, readback, cancel/orphan | Квалифицированный PAPER acquisition adapter и полный typed mode contract |
| WS-030 | Frozen JSONL, point-in-time revisions, freshness/anchor/lineage/dedup | Реальный broker, права доступа, общие quotas/backpressure и verified acquisition |
| WS-031 | Exact repeat, все trials, lender arithmetic, nonempty stateful arithmetic tests, common-unit costs | Фактический holdout, latency/size sensitivity, protocol runtime и PAPER campaign |
| WS-032 | Пять executable model branches, атомарность и rights assumptions | Нативные protocol/account decoding, atlas, реальные quotes/конвертация |
| WS-033 | Existing clearing solver + независимая проверка; delayed capital timeline | Native settlement, реальные venue/funding/hedge cashflows и campaign comparison |
| WS-034 | Штатные scale/archive tests, local installed siblings, package hashes | Dell Windows, all-family corpus, installed STOP/restart/update/rollback |
| WS-035 | Frozen all-attempt metrics evaluator | Реальные baseline/ablations, usefulness и task ROI |
| WS-036 | Все точные criteria, scope applicability, conflict/stale/deferred reports | Семантические criterion verifiers и применимые evidence после PR-010…019 |

Никакая открытая часть не исключена из acceptance. Два физических repository PR составляют один логический PR-020+021: рыночный owner нельзя переносить в SCE. Подготовлены связанные repository PR; рыночный owner опубликован отдельно и зафиксирован точным SHA. Статусы CI проверяются на GitHub; installed Dell остаётся NOT_RUN до фактической проверки устройства.
