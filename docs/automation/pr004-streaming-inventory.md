# PR004 — потоковая Git-инвентаризация

Inventory перечисляет весь pinned Git tree без общего лимита файлов, вывода
или времени. RAM ограничивается buffers и SQLite cache; размер корпуса влияет
на диск и длительность. Operator CLI и существующие `start_scan`/scanRun START
используют один новый reader. Capture продолжает работать через существующие
страницы и chunks; inventory READY само по себе не означает capture COMPLETE.

Реализовано по `ROADMAP_PR_004_STREAMING_GIT_INVENTORY_RU_2026-10-04(1).zip`.
Первоначальный базовый commit: `da6abf4c006e4e7d26fe45ef30fa9d07a356f396`.
Во время работы PR001 #38 вошёл в main; изменения совместимы с его настоящими
scan-run transaction, state counters, byte capture и Native progress owner.
Новые metadata tables, worker, scheduler, Native endpoint не добавлены.

## Использование

```powershell
python -I -B C:\OCC\content-lab\repo_inventory.py --operator-profile C:\OCC\native-profile.json --repository sce
```

Profile, repository alias, namespace, store и policy проверяются тем же
`native_adapter.operator_profile`. Путь исходников не принимается из Native/AI
request. Store и private stage находятся вне source; symlinks в store/database
отклоняются. Installer включает новый sibling `repo_inventory.py`.

`--budget C:\OCC\inventory-budget.json` необязателен. Пример и schema находятся
в `pr004/`. По прямому требованию пользователя `timeout_seconds` и
`stage_max_bytes` по умолчанию `null`: искусственного corpus ceiling нет.
Можно явно установить timeout и stage quota; превышение завершится ошибкой.
Это осознанное изменение предложенного ZIP-контракта с legacy opt-in/cap.
Буферы: block ≤64 KiB, очередь ≤1 MiB, запись ≤64 KiB, batch ≤256 rows/256 KiB.
Лимиты buffers и Native frame/page не ограничивают общий размер репозитория.
Physical RAM/disk, Git/SQLite integer representation и scope/path policies
сохраняют свои реальные границы; приложение не обещает бесконечные ресурсы.

CLI stdout — один compact `occ.repo-inventory-receipt.v1`, schema в `pr004/`.
READY возвращает snapshotId/head/tree/total и inventoryComplete=true.
Новый snapshot имеет cursor=0, captureComplete=false; reused snapshot сохраняет
capture state, а captureComplete=null явно оставляет byte proof прежнему owner.
При запуске capture start_scan/scanRun используют существующую PR002 migration
restart_size_errors для повторения старых FILE_TOO_LARGE; inventory CLI её не выполняет.
Далее `durable.repo.scan` с этим snapshotId либо whole-repo START/STEP
продолжают capture; UI Pause/Continue/Stop остаются частью PR001.

## Целостность и ошибки

- HEAD читается один раз, tree разрешается из этого commit. Git isolation
  исключает inherited config, replace objects, lazy fetch, checkout и shell.
- Binary stdout разбирается по NUL; только первый TAB отделяет metadata.
  Проверяются mode/kind, SHA1/SHA256 OID width, size, EOF и child exit=0.
  Tab/newline/Unicode остаются exact bytes. Unsupported paths остаются
  обратимыми `git-path-hex:` metadata; links, submodules, protected names и
  missing-size markers сохраняют существующую disposition policy.
- Два независимых pipe reader дренируют stdout/stderr. Full queue создаёт
  backpressure; stderr tail и весь diagnostic budget ограничены. Reader
  exceptions и malformed/unterminated/duplicate records не дают успеха.
- Private SQLite stage имеет уникальные paths/ordinals, bounded cache/batches,
  optional quota с reserve для target WAL/journal и dirty cache. Независимый readback сверяет каждую projection и original
  record с точным SHA256 NUL stream. Stage — disposable data, не metadata owner.
- После EOF/reap публикуются snapshot и все entries одной transaction в
  `content.sqlite3`; перед публикацией повторно проверяется HEAD. Для scanRun
  START используется его текущая transaction: intent и inventory атомарны.
  Для CLI transaction принадлежит inventory owner. Нет `OR IGNORE` или repair.
- Valid existing identity переиспользуется после полного metadata сравнения
  без reset captured states. Missing/corrupt ordinals/metadata —
  CONTEXT_INCOMPLETE. Любой abort сохраняет прежние heads/chunks/revisions.
- Deadline/cancel проверяются при ожидании pipes, batches, readback и SQLite
  statements; busy wait ограничен остатком deadline. Child stop/wait/thread
  join имеют отдельный cleanup budget. POSIX использует owned process group;
  Windows — active owned child tree через taskkill. Старые PIDs не убиваются.
  PROCESS_STOP_UNCONFIRMED даёт BLOCKED и сохраняет unpublished stage: сначала
  оператор проверяет остановку, затем запускает новую enumeration с byte 0.

## Проверки и продолжение

`test_repo_inventory.py` проверяет реальные Git/SQLite boundaries, supplied
55-record golden stream на всех 4075 split cuts, SHA256/empty trees, full
160000-entry tree (45,600,000 stdout bytes), faults, deadline, backpressure,
cancel/restart, concurrent publication, reader visibility, scoped CLI и rollback
scan intent вместе с inventory. Все четыре CI suites остаются обязательными.

Воспроизводимая Linux resource qualification:

```bash
python -B content-lab/qualify_repo_inventory.py --output /absolute/new/fixture-directory
```

Cold означает первый новый процесс без eviction OS caches; warm — второй новый
процесс на том же fixture/store с validation/reuse. Linux worker `getrusage`
измеряет application и owned Git child peaks отдельно. В receipt сохранены
stdout bytes/hash, exact tail/ordinal, stage peak на batch checkpoints, duration,
main DB size, target sidecar peak, суммарный storage peak и версии. На 160k application peak около 20 MiB; рост с 40k около
1 MiB. Git child peak около 40 MiB, stage peak около 167 MiB.
Пик stage + target DB + WAL/journal на cold 160k — около 443 MiB;
это полный наблюдённый storage peak данного synthetic corpus.
Подробные числа: `runs/PR004_INVENTORY_RESOURCES_2026-10-04.json`.

PR001 уже устранил отдельный 32 MiB reader из Git index binding и добавил Native
progress. Этот PR их переиспользует; общий LAYA4-003 и 160-task roadmap не
объявляются завершёнными. Windows CI проверяет portable subprocess logic,
но installed Dell Windows 11/Chrome/native-host resource receipt остаётся
NOT_RUN. PR002 #39 также вошёл в main и проверен через actual manifest owner: staged
inventory → capture cursors 20/40/45 → manifest/range-index → deterministic reuse,
включая tail и восстановление старых FILE_TOO_LARGE. PR003 #40 вошёл в main: отдельный runtime test проходит от staged inventory
через capture 20/40/45 и immutable archive manifest до verified ZIP64,
восстановления байтов tail и повторного BUILD. Existing archive crash/resume
и binary/Unicode/empty payload regressions также проверяются текущими suites. Форматы/LFS/eligibility
продолжаются отдельно в PR005; новый inventory не объявляет exclusions captured.
