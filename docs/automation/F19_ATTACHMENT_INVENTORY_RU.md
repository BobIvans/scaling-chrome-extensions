# F-19: metadata-only inventory вложений

## Подтверждённый gap

F-17 уже читал явно выбранный локальный `conversations.json`, но non-text parts
только увеличивали `skipped_non_text`. Состояние pointer, метаданные прав и
стабильные хэши не сохранялись. DOM inventory расширения остаётся отдельным
read-only owner видимых access points; дублировать его в Content Lab не нужно.

## Реализация

`content-lab/content_lab.py` теперь инвентаризирует только non-text parts внутри
выбранного export. Явный allowlist содержит `image_asset_pointer`,
`audio_asset_pointer` и `file_asset_pointer`:

- `PRESENT` — bounded asset pointer присутствует в metadata;
- `MISSING` — разрешённый тип объявлен без pointer;
- `UNSUPPORTED` — тип не разрешён либо pointer/content type не проходит bounds.

Запись `occ.attachment-inventory.v1` содержит `metadata_sha256`, hash pointer,
валидированный declared content SHA-256 при его наличии и `rights_status`.
Отсутствие доказательства прав всегда означает `UNVERIFIED`,
`retrieval_allowed=false`, `bytes_present=false` и
`network_fetch_performed=false`. Inventory не открывает URL, не обращается к
file-service и не считает metadata доказательством наличия байтов.

`attachment_versions` и `attachment_heads` добавлены в существующий
`content.sqlite3`: повторный import дедуплицируется, изменённая metadata получает
новую immutable version, исчезнувший part становится missing head без удаления
истории. `items/content_fts`, `sync_heads/sync_versions`, job queue и Chrome
library records остаются прежними owners.

## Границы

CLI публикует только counts по состояниям и export hash; chat text и asset
pointers в receipt не выводятся. Metadata message attachments вне content parts,
загрузка байтов, проверка лицензии/авторства и OCR/ASR не входят в F-19.
Лимит — 100 000 non-text parts на import и 4096 UTF-8 байт на pointer.
