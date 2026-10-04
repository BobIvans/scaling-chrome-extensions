# ROADMAP PR-001: whole-repo scan с сохранённым управлением

База: `da6abf4c006e4e7d26fe45ef30fa9d07a356f396` (актуальный GitHub main при начале работы).
В checkout нет AGENTS.md. Исторический `5574ab768b39605d4631651a1e8f2451483344db`
не найден в Git object database: `MISSING_BASELINE_EVIDENCE`. Реализация адаптирует
актуальных owners, архивные исходники не накладываются поверх новых.

Один клик **«Собрать весь repo»** последовательно обрабатывает все entries pinned
Git HEAD. **Пауза**, **Продолжить**, **Остановить** доступны во время STEP. Новый
UI получает authoritative STATUS из SQLite и не запускает STEP до явного Continue.
Номер PR-001 относится к входному пакету, не к номеру GitHub pull request.

## Изменение исходного scope по текущему запросу

Пакет `ROADMAP_PR_001_FULL_REPO_SCAN_RU_2026-10-04(1).zip` предлагал сохранить
32 MiB tree-output и 8 MiB blob caps. Текущий пользовательский запрос явно требует
обработку огромных репозиториев без этих ограничений. Поэтому оба cap удалены
посредством streaming. **20 — размер страницы и одного STEP, не предел файлов.**
Общего лимита числа файлов, байтов дерева, размера blob или длительности scan нет.
Это не обещание бесконечного диска/времени и не увеличение context window AI.

## Реализованные возможности

1. Автоматический последовательный full-repo pump с yield между страницами.
2. Потоковый NUL-delimited Git inventory непосредственно в SQLite, без списка
   всего дерева и без cap 32 MiB.
3. Потоковое чтение blob во временный файл и byte-preserving source fragments,
   без cap 8 MiB и без загрузки большого файла/длинной строки целиком в RAM.
4. Incremental SHA-256, UTF-8 validation, сохранение binary bytes; независимая
   проверка offsets, fragment revisions, file hash и размера для INDEXED blobs.
5. Существующие AST section IDs для файлов в окне 2 MiB; большие исходники полностью
   сохранены с явным `STREAMING_UTF8_TEXT_ONLY_NO_SYNTAX_CLAIM` либо binary scope.
6. Streaming secret heuristic, включая ключ/значение через границы блоков и
   значение длиннее блока. Protected names/operator exclusions сохраняются.
7. `repo_scan_runs` в прежнем `content.sqlite3`: intent/run identity, pinned snapshot,
   source-profile digest, state/revision, timestamps/reason и completion proof.
8. Strict `durable.repo.scanRun`: START, STATUS, STEP, PAUSE, CONTINUE, CANCEL;
   UI не выбирает root/store/argv/executable и не создаёт иной worker.
9. Idempotent START/STEP replay; один активный intent на alias/profile; lost reply
   восстанавливается через STATUS без повторной обработки следующей страницы.
10. Cursor/state/revision и page bytes фиксируются в одной SQLite transaction.
    Crash до commit откатывает страницу; per-file savepoint не оставляет
    частично записанного ERROR blob.
11. PAUSE/CONTINUE revision guards и CANCELLED tombstone. Отмена сохраняет данные
    и не оживляет intent при START replay. Новый явный intent может reuse cursor.
12. Source-drift/profile/namespace guards, проверка полного ordinal ledger и
    BLOCKED при нарушении. HEAD повторно проверяется перед commit длинной page.
13. Progress: total, ledger_entries, cursor, processed, pending, indexed, excluded,
    errors. Транзакционные ledger counters предотвращают полный GROUP BY на каждом
    STEP. Ordinal pagination убирает линейный OFFSET и cap 1 000 000 у offset.
14. Native progress markers/frames продлевают idle watchdog и ожидание queued
    controls; native requests/results остаются ограничены размером одного message.
15. Client/repository/run generations, один in-flight STEP, no-progress/timeout
    reconciliation; stale response не возобновляет pump.
16. Legacy scan/get/export, source/review records и текущие Core jobs сохраняются.
    Additive migration счётчиков проверена на прежних таблицах с реальными items.

## Native actions

Для всех действий обязательны `type: durable.repo.scanRun`, `repository`, `action`.
Неуказанные поля отвергаются. IDs — lowercase hex, числа — nonnegative safe integers.

| Action | Обязательные дополнительные поля | Необязательные поля |
| --- | --- | --- |
| START | intentKey (32 hex) | — |
| STATUS | — | runId (64 hex) |
| STEP | runId, expectedCursor, expectedRevision | — |
| PAUSE | runId, expectedRevision | — |
| CONTINUE | runId, expectedRevision | — |
| CANCEL | runId, expectedRevision | — |

Результат — `occ.native-durable-result.v1`, поле `scan_run` с
`schema: occ.repo-scan-run.v1`; STATUS без сохранённого run возвращает null.
Cursor остаётся в `repo_snapshots`, байты — `repo_chunks`, dispositions —
`repo_entries`. `repo_entry_counts` — производная проекция, maintained by SQLite
triggers в той же transaction; при upgrade пересчитывается один раз. Финальное
raw proof независимо обходит фактические записи/chunks, не доверяет cache counts.
Completion proof в run хранит результат последнего успешного terminal transaction;
legacy get/export продолжает независимо проверять raw integrity при чтении.

Полный inventory может иметь errors/exclusions. Это не `all_tracked_bytes_exportable`
и не чтение AI; `ai_delivery` всегда `NOT_PERFORMED`. Links/submodules учитываются
как metadata; LFS pointer payload, ignored/untracked files и unsupported path
encoding не выдаются за прочитанные bytes.

## Проверка и evidence

[Машиночитаемый implementation receipt](roadmap-pr001-implementation-result.json)
связывает 12 исходных AC с фактическими test cases; AC-011 amended по текущему
запросу — прежние size caps должны успешно преодолеваться.

- `content-lab/test_repo_scan_run.py`: 45 source files, три commit pages 20/40/45,
  binary/empty/UTF-8/tail roundtrip, START/STEP replay, настоящий process exit до
  commit, новый native process, pause/cancel/drift/scope/old DB, ordinal gaps.
- Scale corpus: **125 000 entries, 38 500 000 bytes Git tree output**; весь inventory
  сохранён, native response bounded. Этот scale case отменяет processing после
  START; он не утверждает, что все 125 000 blobs были INDEXED.
- Existing regression полностью обрабатывает **2005 files**, включая хвост после
  restart. Новая проверка захватывает **9 000 013 bytes UTF-8** и **10 240 000 bytes
  binary** без прежнего 8 MiB cap, а длинный secret исключает без raw chunks/items.
- `one-click-context/tests/repo-scan-run.test.mjs`: sequential pump, held-page
  controls, late replies, disconnect/selection, no-progress/timeout, idle framing;
  реальный UI→NativeClient→JobHost→DurableBridge→installed adapter→Git/SQLite.
  Потеря STEP reply симулируется после реального commit, STATUS восстанавливает
  cursor 40; новое explicit Continue достигает 45.
- `agent-bridge/durable.test.mjs`: strict fields, progress watchdog, hostile logs,
  actual isolated Python process, hello command advertisement.

Обязательные gates совпадают с `.github/workflows/deterministic-core.yml`:

```bash
python -B -m unittest discover -s content-lab -p 'test_*.py' -v
node --test agent-bridge/*.test.mjs
python -B -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py' -v
node --test one-click-context/tests/*.test.*
```

## Установка и оставшийся scope

Обновите расширение и установленный native host/adapters вместе. Windows installer
копирует те же sibling files; отдельный updater в это изменение не входит.
Не используйте старую версию host для новой кнопки: она явно unavailable.
После reopen подключите host, выберите alias/получите repositories: STATUS покажет
последний scoped run; Continue требует явного клика. CANCELLED intent не возобновляется.

Текущая page (включая один очень большой blob) может завершиться до PAUSE/CANCEL.
Первичная enumeration атомарна; при interrupted START потребуется её повторить.
Закрытие/disconnect прекращает client pump; scan не является самостоятельным daemon.
Запрошенный source код не импортируется, не выполняется, не отправляется в AI;
сканер не делает fetch, hooks, install scripts, тесты изучаемого repo или trades.

Native frame limits, operator exclusions и ограниченное окно syntax analysis остаются
отдельными границами операций. Legacy selected AI export по-прежнему идёт частями;
это не whole-repo portable export или новый graph/JS parser. Broad milestone M5-02
остаётся PARTIAL: desktop shell, полный portable export/index, LFS payload handling,
voice/Laya/Grok/updater и квалификация на реальном Dell Windows 11 — следующие scope.
Физическое устройство пользователя: **NOT_RUN**. Ubuntu/Windows Actions проверяют
код и subprocess fixtures, а не установленное приложение на Dell.
