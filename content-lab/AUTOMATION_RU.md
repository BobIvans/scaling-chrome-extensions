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

Это **локальный CLI backend**. Существующая Chrome библиотека (`library.html`,
localStorage) пока не синхронизирована с SQLite. Native JobHost (`agent-bridge/host.mjs`)
сохраняет прежний контракт и не перенаправляет jobs автоматически в этот backend.
Следующий этап: search/context и enqueue/get/cancel через существующий host,
одна согласованная record schema, затем карточки очереди в UI.

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

После локальных тестов job получает `WAITING_CI`. Core не выполняет push, merge
или создание PR. Операторский GitHub adapter публикует проверенный commit и
атомарно обновляет `ci.snapshot_file` из фактического GitHub Actions ответа:

```json
{
  "schema":"occ.ci-snapshot.v1",
  "origin":"operator_github_actions_export",
  "head_sha":"EXACT_40_HEX_COMMIT",
  "checks":[
    {"name":"core (ubuntu-latest)","run_id":123,"head_sha":"EXACT_40_HEX_COMMIT","status":"completed","conclusion":"success"},
    {"name":"core (windows-latest)","run_id":124,"head_sha":"EXACT_40_HEX_COMMIT","status":"completed","conclusion":"success"}
  ]
}
```

Check names совпадают с policy, каждый запуск относится к этому commit. Вход —
**доверенный операторский export**, а не independently authenticated release proof.
Page text или модель не подменяют этот файл. Latest run ID по имени заменяет
прежний результат; неполный, чужой или конфликтующий export оставляет `WAITING_CI`.
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
node --test agent-bridge/host.test.mjs agent-bridge/client.test.mjs
node --test one-click-context/tests/*.test.*
```

Python tests используют реальный SQLite, Git worktree и subprocess. Проверяются
cancel, concurrent claim, restart/replay и подготовленная failed/successful пара
патчей. CI snapshots в tests **синтетические**, не реальная публикация GitHub.
ASR/Laya inference, установленный Windows Chrome, browser relay, подпись, sender
и рыночные результаты не проверяются этим suite.
