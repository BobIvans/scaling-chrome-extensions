# PR-003: переносимый ZIP всего сохранённого контекста

Один foreground запуск `repo_archive.py` экспортирует **каждую INDEXED часть**
проверенного snapshot. После распаковки `INDEX.html` открывает все исходники,
причины пропусков и постраничные ссылки на все raw parts. После сбоя явный
`--resume` проверяет сохранённые части и повторно пишет только повреждённые или
отсутствующие. Незавершённый ZIP собирается заново из этих частей.

Это реализация raw archive slice LAYA4-010 из предоставленного ZIP PR-003.
Сканер PR-001 уже merged в #38; новый exporter использует его существующие
snapshot/chunk tables. Параллельный PR-002 (#39) включён как prerequisite: его
`repo_manifest.py` остаётся владельцем формата, writer и Native metadata pages.
`repo_archive_input.py` проверяет его exact frozen projection в одном read view;
второй формат манифеста не вводится.

## Запуск на Windows 11

Нужны Python с SQLite/FTS5, Git для **сканирования**, и существующий доверенный
`occ.native-durable-profile.v1`. Repository alias, root, namespace и store
выбираются этим profile. Экспорт сохранённого snapshot Git не вызывает.
Все пути ниже задаются оператором. Manifest и export находятся вне source,
store и друг друга, например соседние каталоги `C:\OCC\manifest` и `C:\OCC\exports`.

```powershell
$occRepo = 'C:\Projects\scaling-chrome-extensions'
$occProfile = 'C:\OCC\native-profile.json'
$occManifest = 'C:\OCC\manifest'
$occExports = 'C:\OCC\exports'

# Foreground scan: проходит все страницы, затем пишет verified manifest.
python -I -X utf8 "$occRepo\content-lab\repo_scan.py" --profile $occProfile --repository sce --manifest-output $occManifest

# Полный ZIP сохранённого batch; stdout — actual publication receipt.
python -I -X utf8 "$occRepo\content-lab\repo_archive.py" --profile $occProfile --repository sce --manifest $occManifest --output $occExports

# После прерывания только явный resume; status ничего не публикует.
python -I -X utf8 "$occRepo\content-lab\repo_archive.py" --profile $occProfile --repository sce --manifest $occManifest --output $occExports --status
python -I -X utf8 "$occRepo\content-lab\repo_archive.py" --profile $occProfile --repository sce --manifest $occManifest --output $occExports --resume

# После Ctrl+C новый run_id; прежний CANCELLED receipt сохраняется.
python -I -X utf8 "$occRepo\content-lab\repo_archive.py" --profile $occProfile --repository sce --manifest $occManifest --output $occExports --new-run
```

Для уже готового snapshot можно вызвать `repo_manifest.py --profile ...
--repository sce --snapshot <snapshot_id> --output <absolute-directory>`.
Повторный вызов проверяет весь существующий metadata batch, не перезаписывает
повреждённый batch. Для нового snapshot выберите новую manifest directory.
`repo_scan.py --resume-snapshot <snapshot_id>` продолжает выбранный snapshot
через существующий foreground snapshot API; Native scan-run controls остаются
владельцем установленного браузерного workflow.

## Функции и контракты

| Функция | Реализация и результат |
| --- | --- |
| Existing PR-002 manifest | Все entry dispositions и все captured parts, compact JSONL; никакого массивa всех part IDs в одной entry |
| Global proof | В одном read-only SQLite view: contiguous ordinals/ranges, SHA256, revision digest, SHA1/SHA256 Git blob OID, orphan/empty checks |
| Scope/binding | Exact repository/namespace/profile/snapshot и hashes четырёх metadata файлов; изменение profile блокирует публикацию |
| Atomic parts | Generated `parts/<revision>.bin`, fsync и same-filesystem replace до checkpoint |
| Writer lock | OS advisory lock Windows/POSIX на output/export_id; завершение процесса освобождает lock |
| Resume | Повторный hash каждого staged part, восстановление counts из actual files; checkpoint не является source owner |
| Cancellation | CANCELLED терминален для `--resume`; `--new-run` сохраняет прежний run receipt и создаёт новый run_id |
| Offline index | Static escaped HTML, 20 rows на страницу, все последующие страницы доступны, source ↔ part pages и relative raw links |
| ZIP64 | Stream copy, force_zip64, closed archive hashes/CRC/member set и повторное source reconstruction до финального rename |
| Publication | External ZIP SHA256 и receipt; crash после rename восстанавливает sidecars после exact archive verification |
| Conflict handling | Existing damaged/extra-member ZIP не перезаписывается; явный OUTPUT_CONFLICT |
| Installed CLI | Install.ps1 включает новые sibling modules; `python -I -X utf8` проверен subprocess integration |

`batch_id` и `export_id` используют существующий `automation_core.digest` с
его spaced sorted JSON serialization. `part_id` — существующий revision,
а не raw hash. Metadata bytes копируются без изменения IDs/offset semantics.
`EXPORT_MANIFEST.jsonl` содержит каждый output ровно один раз, в ASCII path
order, кроме самого себя. Receipt хранит hashes ZIP и output manifest.

```text
<export-parent>/
  .lock-<export_id>
  .stage-<export_id>/EXPORT_STATE.json
  .stage-<export_id>/RUN_<prior_run_id>.json
  .stage-<export_id>/payload/...
  REPO_<export_id>.zip
  REPO_<export_id>.zip.sha256
  REPO_<export_id>.receipt.json
```

Source filenames — только escaped metadata. Не создаются исходные CON/NUL,
markup, Unicode, tab/newline filenames внутри архива. Generated output names
ASCII и relative; ссылки работают после переноса распакованной directory.
HTML не включает scripts, remote fonts, fetch или сетевые assets.

## Масштабирование и реальные границы

Нет фиксированного ограничения количества repo files, parts, страниц или общего
размера raw capture/export. Ограничения размера страницы и copy buffer относятся
к одной порции. PR-001 уже заменил старые 32 MiB tree / 8 MiB file rejections на
потоковое чтение. Его 2 MiB AST window ограничивает **optional syntax analysis**;
большие файлы всё равно полностью сохраняются с явным parser status.

Raw chunks читаются SQL cursor, manifest пишется строками, copying использует
64 KiB buffer по умолчанию. Можно задать `--buffer-bytes`,
`--disk-budget-bytes` и `--time-budget-seconds`. По умолчанию общего disk/time
budget нет. Disk budget — консервативная admission estimate stage + ZIP +
metadata/navigation; фактический ENOSPC отдельно возвращает DISK_FULL.
Time budget проверяется на границах обработки, это не OS hard timeout.
Если реальный full disk не позволяет записать checkpoint, уже fsynced parts
остаются восстановимыми, а stdout возвращает blocker.

Stdlib ZipFile хранит central-directory metadata в памяти пропорционально числу
members. Disk, RAM и время конечны; поддержка ZIP64 не обещает бесконечную RAM
или измеренную скорость любого корпуса. Полный portable export не расширяет
context window AI-провайдера. AI delivery = NOT_PERFORMED, AI read = UNKNOWN,
dependency graph = NOT_GENERATED; protected/excluded/missing bytes остаются gaps.

`--status` показывает persisted run state и заново вычисленные counts staged
parts. Для проверки или восстановления ready ZIP/receipt используйте явный
build/resume. Повреждённый final archive сначала сохраните/перенесите вручную
для диагностики; exporter не делает автоматический repair/quarantine.

## Qualification

`test_repo_archive.py` использует real Git scan → existing SQLite → manifest →
actual exporter CLI. Fixture: 50 entries, 46 indexed, 4 exclusions, 78 parts,
один source с 33 parts. Есть byte reconstruction, exact output/member hashes,
ZIP64 writer path, перенос offline links, hostile metadata, subprocess kill
до/после part rename, во время ZIP, после final rename, два writer процесса,
реальный POSIX SIGINT, portable KeyboardInterrupt, injected ENOSPC/EACCES,
повреждение parts/checkpoint/metadata/Git OID/ranges/revision, revocation и
existing output conflict. Все source owners и прежние native regressions
проверяются текущим deterministic-core workflow на Linux и Windows.

Scale receipt и точные результаты команд находятся в соседнем
`roadmap-pr003-implementation-result.json`. Windows CI проверяет CLI и kernel
lock; открытие INDEX.html на пользовательском Dell/Windows 11, device latency
и actual >4 GiB archive отдельно остаются NOT_RUN. Это не закрытие всех 160
roadmap tasks или desktop scan→export orchestration.
