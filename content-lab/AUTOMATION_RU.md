# Детерминированный контур OCC

Порядок: **сбор и дедупликация → библиотека → долговечная очередь → patch/test/CI/retry**.
Голос, browser relay и Laya подключаются после этого через зарегистрированные действия.

`automation_core.py` расширяет существующий `content.sqlite3` из Content Lab.
`items/content_fts` остаются владельцем текста; `sync_heads/sync_versions` добавляют
актуальную версию и историю, `jobs/job_events` — задания и переходы. JSON в `items/`
является восстанавливаемой проекцией SQLite. Второй индекс не создаётся.

## 12 функций и доступ

| Функция | Доступ сейчас | Результат |
|---|---|---|
| Сканирование экспорта | `sync` | Ограниченный набор локальных UTF-8/HTML/subtitle файлов |
| Дедупликация | `sync` | Повтор не добавляет версию; разные источники сохраняют происхождение |
| История правок и пропусков | `sync_versions/sync_heads` | Удалённое исключено из текущего поиска, история сохранена |
| Поиск в проекте | `search --namespace` | FTS с фильтром namespace до выдачи |
| Чтение актуального источника | `context --id` | Старый или чужой ID отклонён |
| Пакет контекста | `context` | До 10 источников, digest, явный byte budget |
| Долговечное задание | `enqueue --task-key` | Повтор возвращает job, конфликт payload/policy блокируется |
| Один writer и lease | `work` | Атомарный claim между процессами |
| Checkpoint и восстановление | `get`, `jobs` | Последний подтверждённый этап после перезапуска |
| Остановка | `cancel` | Флаг отмены и остановка дочернего процесса |
| Подготовленный patch и тесты | `work` | Отдельный worktree, pinned base/patch, зарегистрированный argv |
| CI и bounded retry | `work` | Все required checks на exact SHA; до 3 подготовленных попыток |

**Функция 13 — типизированный Native JobHost adapter.** `agent-bridge/host.mjs`
сохраняет прежние временные Codex jobs и по отдельному операторскому opt-in
принимает `durable.search/context/enqueue/get/cancel`. Эти пять команд обращаются
к тому же SQLite owner через `native_adapter.py`, без второго индекса/очереди.
Host не запускает `work` и не удаляет долговечные jobs при disconnect.
Инструкция настройки и схемы — в `agent-bridge/README_RU.md`.

Существующая Chrome библиотека (`library.html`, localStorage) пока не
синхронизирована с SQLite. **Следующая функция 14** — карточки долговечной очереди
и поиск/context через этот контракт в UI. Голос и browser actions следуют после
этой интеграции. Проверка adapter не является тестом установленного Windows Chrome.

## Запуск без модели

Python 3.11+ со SQLite FTS5 и Git. Хранилище размещается вне исходной папки.
Для каждой выбранной папки используется собственный namespace.

```sh
python content-lab/automation_core.py --store ../occ-data sync --namespace occ --root ../selected-exports
python content-lab/automation_core.py --store ../occ-data search --namespace occ --query "qualification blocker"
python content-lab/automation_core.py --store ../occ-data context --namespace occ --id ITEM_ID
```

Полный scan атомарно обновляет heads. Ошибка чтения или бюджета сохраняет прежние
heads. Скрытые папки, `node_modules` и скрытые файлы пропускаются; symlink входа
отклоняется. HTML — статический best-effort текст. JSON — содержимое файла, а не
обещание разобрать все сообщения платформы. Ничего не скачивается из сети.
Удаление файла создаёт missing-статус без удаления исторического payload.

`policy.example.json` — шаблон операторского профиля. Заполните абсолютные пути,
точный чистый `base_sha`, проверенные patch hashes и разрешённые пути. Job принимает
**только ID профиля и зарегистрированных патчей**, не команду из чата.

```json
{"kind":"sync","source_profile":"exports"}
```

```json
{"kind":"patch_test_ci","repo_profile":"occ","patch_ids":["first","corrected"],"max_attempts":2}
```

```sh
python content-lab/automation_core.py --store ../occ-data enqueue --policy policy.json --task-key goal-001 --job job.json
python content-lab/automation_core.py --store ../occ-data work --policy policy.json
python content-lab/automation_core.py --store ../occ-data jobs
python content-lab/automation_core.py --store ../occ-data get --policy policy.json --id JOB_ID
python content-lab/automation_core.py --store ../occ-data cancel --policy policy.json --id JOB_ID
```

Один `work` проверяет ожидающие CI snapshots и исполняет максимум одно доступное
задание. Его вызывает выбранный локальный scheduler; автозапуск не устанавливается.
Старый task key не запускает новый scan. Для очередного планового scan нужен новый
ключ, например `exports-20261001T0800`.

## Patch/test/CI

Патчи заранее готовит оператор или отдельный исполнитель. Core не создаёт новый
произвольный код. Проверяются чистый checkout, exact base SHA, patch digest и
allowed paths. Test commands задаёт только policy. `shell=False`, API keys и
desktop IPC не наследуются, Git hooks отключены. Worktree не является OS sandbox:
не регистрируйте непроверенные исполняемые патчи/test commands. Каждая попытка
получает новый worktree; основной checkout сохраняется. Worktrees остаются для review.

`git_autocrlf` задаётся в профиле как настоящий boolean и закрепляет одинаковую
интерпретацию исходного checkout и worktree. Default — false; для CRLF checkout
выберите true после проверки его clean status. Patch применяется через Git index.
Глобальные пользовательские Git настройки не расширяют права и не меняют этот профиль.

После локальных тестов job получает `WAITING_CI`. Core не выполняет push, merge
или создание PR. Публикация проверенного commit остаётся отдельным операторским
действием. После неё F-16 transport читает GitHub check-runs только для
зарегистрированного repository и exact head, затем атомарно заменяет существующий
`ci.snapshot_file`:

```sh
OCC_GITHUB_TOKEN=... python content-lab/github_ci_snapshot.py \
  --policy policy.json --repo-profile occ --head-sha EXACT_40_HEX_COMMIT
```

Имя private token env, repository, required checks, таймаут и предел страниц
заданы policy, а не job/чатом. Поддерживается только `https://api.github.com`;
redirect блокируется. Token не записывается в snapshot или CLI output. При
отсутствующем/отозванном token, сетевой ошибке или превышении pagination bound
старый green snapshot заменяется `transport_status=BLOCKED` без checks, поэтому
Core не может принять его за успех. Transport не вызывает worker и не выполняет
push/PR/merge.

```json
{
  "schema":"occ.ci-snapshot.v1",
  "origin":"authenticated_github_check_runs_v1",
  "repository":"OWNER/REPOSITORY",
  "head_sha":"EXACT_40_HEX_COMMIT",
  "required_checks":["core (ubuntu-latest)","core (windows-latest)"],
  "transport_status":"OBSERVED",
  "checks":[
    {"name":"core (ubuntu-latest)","run_id":123,"head_sha":"EXACT_40_HEX_COMMIT","status":"completed","conclusion":"success"},
    {"name":"core (windows-latest)","run_id":124,"head_sha":"EXACT_40_HEX_COMMIT","status":"completed","conclusion":"success"}
  ]
}
```

Check names совпадают с policy, каждый check run относится к этому commit и
принадлежит GitHub Actions app. Repository и required set повторно связываются
Core с policy. Page text или модель не подменяют этот файл. Latest check-run ID
по имени заменяет прежний результат; неполный, чужой, pending или конфликтующий
ответ оставляет `WAITING_CI`. Старый `operator_github_actions_export` сохранён
для совместимости, но результат явно помечается как independently unauthenticated.
Полный отрицательный CI или failed test может выбрать следующий подготовленный
патч. Лимит — 3 попытки, concurrency — 1, money budget — 0. Неизвестная ошибка
не исправляется без нового подготовленного патча.

После истечения lease job становится `NEEDS_RECONCILIATION`; новый writer
блокируется, поскольку прежний процесс ещё может работать. Отмена такого job
не утверждает, что процесс остановлен. Проверив и остановив orphan процесс,
оператор освобождает очередь с сохранением результата BLOCKED:

```sh
python content-lab/automation_core.py --store ../occ-data abandon-orphan --policy policy.json --id JOB_ID --process-stopped
```

Это подтверждение относится к конкретной проверке процесса, не автоматическому
retry. V1 core не исполняет внешних эффектов.

## Проверки

```sh
python -m unittest discover -s content-lab -p 'test_*.py' -v
node --test agent-bridge/*.test.mjs
node --test one-click-context/tests/*.test.*
```

Python tests используют реальный SQLite, Git worktree и subprocess. Проверяются
cancel, concurrent claim, restart/replay и подготовленная failed/successful пара
патчей. CI snapshots в tests **синтетические**, не реальная публикация GitHub.
ASR/Laya inference, установленный Windows Chrome, browser relay, подпись, sender
и рыночные результаты не проверяются этим suite.
Native durable tests дополнительно запускают настоящий Python subprocess через
production `JobHost`, проверяют restart/replay, cancel, namespace/template scope,
stale IDs, отказ передачи путей/argv, полные byte limits и завершение транспорта.
