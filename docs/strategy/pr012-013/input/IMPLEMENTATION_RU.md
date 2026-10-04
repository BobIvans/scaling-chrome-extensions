# Архитектура и порядок реализации

## 0. Аудит актуального кода

Зафиксировать SHA/base, инструкции AGENTS, Python/JS package layout, migrations, таблицы sources/versions/chunks, Native transport и UI. Найти handlers `scan_page`, `list_snapshots`, `snapshot_changes`, `index_matches_head`, `verify_roundtrip_db`, ZIP export, Core job registry, importer registry, SourceAddress, existing media/web adapters и tests. Составить current-vs-planned с `path:line` и git SHA; не переносить старые названия в код по памяти. В исходном snapshot утверждается наличие streaming blobs, Native progress/START и отдельных ограничений `LIMIT 20`/`[:20]`; всё это перепроверить. Миграции включить только если текущая схема не выражает перечисленные identity/ledger invariants.

## 1. Общий контракт и идентичность

Один canonical Core/SQLite writer. Source = стабильная identity origin независимо от aliases и переименований; SourceVersion = immutable raw hash + declared scope/revision; Observation = отдельная фиксация времени/ответа с provenance; Extraction = versioned derived data. Repo HEAD и dirty overlay, web revision, media original и OCR correction не смешиваются. Ссылки SourceAddress V1 сохраняют revision и координаты (repo path/range; PDF page/rectangle; Office sheet/cell/slide/paragraph; media start/end; web URL/revision; GitHub entity/event). Если координата недоказуема — `UNKNOWN`, а не ложная точность.

Core job API принимает idempotency key и immutable request digest. `START` возвращает прежний job для совпадающего intent, `STATUS` возвращает committed cursor, `PAUSE`/`RESUME` сохраняют identity, `CANCEL` терминален. После process restart lease и fencing не позволяют старому worker опубликовать page. Только завершённая порция и её ledger фиксируются одной транзакцией; большие raw bytes публикуются через staging → hash/flush → metadata ref. Сначала audit существующих механизмов и адаптация к ним, не копирование инфраструктуры.

## 2. WS-002 — долгие Git jobs

Пользоваться существующим `repo_context` inventory и Core, зарегистрировать `repo_scan`/`repo_inventory` операции с pinned HEAD, profile, snapshot scope, cursor, total/accounted/pending/errors/excluded. Native отвечает быстро с job_id, UI опрашивает прогресс и управляет клавиатурой; disconnect/window close не отменяет job. Budget, batch size, stderr budget, timeout и cancellation проверяются между порциями. Исходный NUL-safe Git tree reader должен сохранять raw path bytes/reversible encoding, mode/OID/size и явный error при resource limit. Staged inventory публикуется COMPLETE только когда every tracked entry accounted. HEAD drift — отдельная terminal/blocking state; continuation требует новую revision, не подмену старой.

## 3. WS-003 — потоковая выдача и экспорт

Заменить corpus `LIMIT 20` и `[:20]` cursor pagination для snapshots, selections, delta paths. Порядок стабилен и фиксирован по snapshot/version + immutable key; cursor связывает фильтр, pin и last key, отвергает drift/tamper. Page/frame limit определяет только размер ответа. Streaming traversal до EOF reconciles total/accounted and text omissions (`budget`, `unsupported`, `protected`, `missing`, `selected_out`) без списков всего корпуса в RAM. Не дублировать уже существующие blob/index/roundtrip pipelines. Экспорт №002/003 потребляет page iterator; каждую часть атомарно публиковать с hash, manifest и портативными relative refs. ZIP fault/disk-full не объявляется successful; при resume проверить завершённые parts и восстановить недостающие.

## 4. WS-006 — snapshots, CAS и selective invalidation

Ключ immutable raw object — digest *байтов* плюс namespace/encoding metadata; многие origins ссылаются на него отдельно. Derived cache key включает raw hash, parser/model version, resolver config и policy. Commit/dirt/history/LFS/submodule overlays явно разделены; LFS pointer и fetched content — разные representations. Diff streams emit added/replaced/deleted ranges, rename lineage не уничтожает old path, diff не совпадающих scopes требует explicit unavailable/gap. Versioned dependency edges связывают extraction → chunks → graph/packet → criterion evidence. Изменения байтов, parser/config/policy и иных declared inputs помечают только затронутые derived/current applicability как STALE или RECHECK_REQUIRED; historical receipts неизменны. Для unresolved dynamic edge применять консервативный recheck. Проверить clean vs incremental semantic equivalence и measured RAM/CPU на 16 GB target; не увеличивать `max_parallel=1` без отдельного gate.

## 5. WS-009 — PDF/Office/OCR

Registry dispatch по magic/mime + explicit supported matrix для PDF, DOCX, XLSX, PPTX; unsupported/protected/embedded objects дают конкретный gap. Original immutable. Adapter version, dependency versions, config, raw hash образуют extraction identity. Text и table cells имеют page/slide/sheet/cell/range; таблицы хранят numbers, signs, units, merged-cell bounds и порядок. Scanned PDF OCR — отдельная derived rendition с uncertainty/confidence и original-page reference. Manual correction — отдельная revision; exact page/cell открыть через UI по сохранённой версии либо показать `UNKNOWN` там, где adapter не способен доказать mapping. Lazy extract job использует тот же Core checkpoint contract, не выводит COMPLETE после частичной page failure.

## 6. WS-010 — media/transcript

Сохранённые audio/video оригиналы import локально; external ASR разрешать только через существующий profile/grant. Chunked decode/transcription с ordered checkpoints; segments имеют monotonic `[start_ms,end_ms)` относительно точного media hash, model/config, speaker label с `UNKNOWN` при нехватке evidence. ASR и исправленный transcript существуют как разные versions; failure/unavailable span отражается в ledger. Корпус RU, EN, code-switch, silence, overlap, drift позволяет измерить timestamp accuracy, critical phrase/number errors, время и стоимость на реальных устройствах. Повтор не создаёт новую source version при неизменном raw hash; cancel/restart продолжают незавершённые spans.

## 7. WS-011 — web/RSS/GitHub read-only history

Каждый fetch — Observation с retrieval time, request target, response status, provenance, raw bytes hash и cursor; изменение страницы/PR создаёт revision, а не редактирует историю. RSS item сохраняет ссылку на первоисточник; репосты не считаются независимым подтверждением. GitHub PR/issues/reviews/checks/workflow attempts собираются с pagination до explicit EOF, rate-limit/backoff сохраняет cursor и partial freshness state. Восстановление после 429/network fail не пропускает страницу; retry dedup по stable remote identity + revision/observation. Контракт различает EMPTY_AT_EOF, PARTIAL, NO_MATCH_QUERY, INACCESSIBLE, RATE_LIMITED. Adapter versions и scopes явно измеряются, не обещают «всю историю» там, где API не предоставляет объект/права.

## 8. Интеграция и откат

Один migration coordinator. Расширения schema additive, idempotent и с version gate; миграцию на копии пользовательской базы проверить перед применением. Feature flags для job orchestration, pagination read path, derived cache и каждого importer; при откате read-path вернуться к прежнему handler, новые immutable originals/history не удалять. Dual-write authority запрещён. Freeze/update интерфейсов с №010/011/014/015/016 через `PARALLEL_HANDOFF.json`. PR description перечисляет отдельные receipts: unit/integration/fault/scale, CI, merge, Windows installed build; один зелёный тест не заменяет device gate.

## 9. Разумная последовательность commits

1. Audit/ADR + exact contracts + fixtures; 2. Core repo jobs; 3. paginated repo/history and exporter bridge; 4. raw/derived reuse and dependency invalidation; 5. document adapters; 6. media adapters; 7. web/RSS/GitHub adapters; 8. cross-adapter faults, migrations, Windows qualification and PR documentation. Один code PR закрывается только после всех scoped критериев. На основании приложенных ZIP нельзя обоснованно оценить часы или предсказать diff size; coding, CI и device qualification оценить отдельно после аудита.
