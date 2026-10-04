# F-18 — версия записи Chrome ↔ SQLite

## Подтверждённый gap

Браузерная библиотека сохраняла плоские records и при несовпадающем ID только
блокировала весь restore. Native SQLite owner не принимал явную версию,
родительскую версию или tombstone, поэтому edit/delete нельзя было безопасно
перенести через существующий durable transport.

## Реализация

`one-click-context/library-store.mjs` строит строгий
`occ.library-record.v1`: namespace/source key, `revision`, `parentRevision`,
tombstone, content hash и provenance. `durable.record` передаёт только эту запись
в разрешённый оператором namespace. `content-lab/content_lab.py` применяет её
транзакционно к тому же `content.sqlite3`:

- `items/content_fts` остаются владельцем immutable текста;
- `sync_heads/sync_versions` остаются текущим searchable head и историей;
- `library_record_heads/library_record_versions` хранят только CAS lineage,
  tombstone и provenance для браузерной записи;
- exact replay возвращает `UNCHANGED`; пропущенная/устаревшая родительская
  версия и другой payload под тем же revision блокируются;
- tombstone сохраняет provenance, скрывает head из search и не несёт text.

Новая очередь, база, worker, модель или автоматический background sync не
добавлены. Передача выполняется только после уже существующего opt-in подключения
Native Messaging и в namespace из native profile.

## Проверка и границы

Synthetic fixtures покрывают create/edit/replay, stale edit, same-revision
conflict, tombstone и попытку stale resurrection, provenance, content SHA-256,
namespace scope и реальный Node → isolated Python → SQLite roundtrip. Один native
record ограничен 8 000 UTF-8 bytes текста и общим 16 000-byte request; chunked
large-record transport и UI массовой синхронизации не входят в F-18. Windows
Chrome installation не выполнялась.
