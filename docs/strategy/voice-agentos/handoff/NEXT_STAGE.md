# Следующий этап: №010 source ownership и интеграция #51

## Problem / desired behavior

В #009 ChatGPT originals находятся в `import_raw_blobs`; #50 добавляет
context raw spans/packet documents; #51 — FILE/MEDIA raw parts и observations.
Они используют один SQLite owner, но ещё не образуют общий versioned SourceAddress
и importer/extractor lifecycle. Нельзя переименованием таблиц объявить это
завершённым №010 или делать второй store, терять revisions/bytes и дублировать
написанный код. Full PDF/OCR/ASR/web adapter в #51 отсутствует.

Первый deliverable: согласованный SourceAddress/read contract для существующих
трёх source dialects, реальные scoped adapters и paged traversal, с сохранением
byte hashes, original origin, version/extraction identity, exact range и явных
unsupported/not-captured outcomes. Добавить Core lifecycle только через
existing queue/lease/STOP, там где длительная capture действительно нуждается
в background execution.

## Read before editing

- `../roadmap/briefs/PR_010.json`: WS-001, WS-007, WS-008, WS-012.
- `../roadmap/briefs/PR_012.json`, `PR_013.json`: зависимые lifecycle/importers.
- `../roadmap/source_master/strategy_v5/catalogs/ALL_TASKS_V5.json`:
  G3-008, LAYA4-015/016, ACTION5-10/11, LAYA4-004/013/014,
  ACTION5-06/09 и связанные точные критерии.
- `content-lab/content_lab.py`, `test_import_fidelity.py`;
  #50 context modules/tests и `docs/automation/pr014-015/README.md`;
  #51 source ledger/tests и `docs/automation/pr012-013-source-ledger.md`.
- `automation_core.py`, `workflow_state.py`, `native_adapter.py`,
  `desktop/client.py`, installers и `OWNED_FILES.json`.
- Live PR #51 и текущий main: ветка обновлялась параллельно. Датированный
  pending patch читать как evidence, не применять автоматически.

## Sequence

1. Refresh PR/main state; получить отдельный checkout существующей #51.
   Resolve conflicts по смыслу: сохранить #50 context handler, campaign/research/
   action handler когда они уже присутствуют, общий STOP и все installed siblings.
   Review version timestamp/sequence regression #51 на Windows.
2. Документировать точный versioned SourceAddress schema и adapter outcomes:
   source identity ≠ raw object ≠ extraction ≠ capture observation ≠ text item.
   Старые exact raw bytes/IDs остаются читаемыми после additive migration.
3. Реализовать adapter read/search surfaces поверх owners. Неправильные namespace,
   range/hash/version отвергать; цитата открывает закреплённую revision после
   restart. Исторические heads и current FTS явно различаются.
4. Применимые длительные capture jobs — registered Core kind, immutable intent,
   bounded part work, lease fencing, persisted checkpoint, cancel/STOP и
   неизвестный исход с reconciliation. Отдельного executor не вводить.
5. Интегрировать Native/Desktop contract без передачи произвольных paths/SQL/argv
   из UI, обновить manifests/installers, проверить browser/Desktop compatibility.
6. После tests и актуального Ubuntu/Windows CI merge этого конкретного stage.
   Сохранить полный остаток №010 (ниже) с owners, не переименовывать его в DONE.

## Independent acceptance for this stage

- Exact BOM/CRLF/RU/EN/emoji/binary fixture roundtrip; hash/size и ranges сверяются
  с исходными bytes, не только с реализацией encoder.
- Ранее импортированный ChatGPT source, #50 local file и #51 FILE/MEDIA source
  адресуются без потери provenance или ошибочного объявления extracted text.
- Same content/distinct origins, rename/stable key, changed formatting/content,
  new extractor revision, unsupported binary и stale pointer имеют явные outcomes.
- Paged versions/observations/parts доходят до EOF, включая >20/>1000 хвост;
  frame/memory budget даёт explicit continuation/backpressure.
- Corrupt hash/range/namespace/version отклоняются. Source mutation during capture,
  interruption/restart, ack loss/same operation key и STOP fence не дают
  prefix-success, duplicate publication или silent fresh-ID retry.
- Additive migration rehearsal на populated старой DB и повтор после interruption;
  all old raw references and specialized ChatGPT tests remain valid.
- CI на актуальном SHA проходит; Windows hosted CI не заменяет installed Dell.

## Full remaining №010 backlog retained

WS-001: manual label override/re-extraction, versioned automated labels,
saved views, exact/paged search и full SourceAddress receipts.
WS-007: importer registry/extractor queue, streamed TXT/folder/checkpoints/
encodings, archive provenance/traversal/cycles/resources, unsupported originals,
attachments, verified local LFS payloads and submodule identities.
WS-008: ChatGPT/Telegram adapters, observed scroll continuation, full branches/
edit revisions/author/quote/time envelopes, missing attachments and unknown
branches; observed UI history не удостоверяет невидимую историю.
WS-012: versioned RU/EN goals, questions/terms/contradictions/notes overlays,
goal→source→code→test→result mapping и honest readiness states.

Дальше №011 resolver/provenance graph; №012/013 CAS/invalidation/format importers;
затем соответствующие downstream qualification. Два интегрируемых package
номера не означают, что все зависимости и исходные criteria закрылись.
