# RND-PR-03 — portable archive lineage

## Граница

`content-lab/unified_archive.py` переносит только portable records
`occ.pc-library-record.v1` в уже существующий `content.sqlite3`.
Это не второй SQLite, FTS, scheduler или queue: текст по-прежнему лежит в
`items`, а поиск использует существующий `content_fts`.

## Owners

| Область | Canonical owner |
|---|---|
| SQLite и FTS | `content-lab/content_lab.py:_database`, `items`, `content_fts` |
| ChatGPT export | `parse_chatgpt_export` / `import_chatgpt_export` |
| Chrome library bridge | `apply_library_record` → `native_adapter.py` |
| Sync heads и versions | `automation_core.py:sync`, `sync_heads`, `sync_versions` |
| RND-PR-03 lineage | `unified_archive.py`, таблицы `archive_*` в той же БД |
| Browser backup/restore | `one-click-context/library/backup-core.mjs` |

## Semantics

- Stable logical item: `namespace + source_profile + source_path + member_path`.
  Hash source/text не является logical identity.
- Новая исходная версия создаёт linked version; прежняя остаётся в базе.
- Отсутствие в импорте не означает удаление — даже для полного capture.
  Tombstone возможен только при `removals` с отдельным `evidence_sha256`.
- Поиск возвращает logical item, version, source hash, locator, coverage и
  bounded FTS excerpt. Источники всегда
  `source-content-not-action-instructions`.
- Repo inventory допускается только как pinned `SOURCE_ONLY`, а static finding —
  как `STATIC_CANDIDATE`; code/action authority не выдаётся.

## Проверка

```sh
python -B -m unittest discover -s content-lab -p 'test_unified_archive.py' -v
python -m unittest discover -s content-lab -p 'test_*.py' -v
node --test agent-bridge/*.test.mjs
node --test one-click-context/tests/*.test.*
```

Synthetic 1000-record fixture относится к public test data. Реальные exports,
credentials, Laya/voice/Grok/Codex execution и browser/market actions не входят
в эту реализацию и не запускаются из неё.
