# PR-009: оригиналы и проверяемый импорт выбранного ChatGPT JSON

Пользователь получает exact original revision выбранного файла и самостоятельную
версию извлечения. Можно вернуть оригинал с теми же BOM, CRLF, Unicode и unknown
fields, посмотреть все наблюдаемые ветви/пустые nodes и понять причину каждого gap.
Импорт одного выбранного чата сохраняет heads других chats в namespace.

Это один срез ACTION5-04/05/06, ориентир 60 минут focused build плюс QA.
Полные задачи не закрываются: original/correction envelope, DOM full-scroll,
generic importer registry и arbitrary-folder checkpoint требуют следующих PR.

## Доказанная исходная точка

Byte-preserved content_lab.py из archived commit
`da6abf4c006e4e7d26fe45ef30fa9d07a356f396` уже:

- читает regular `.json`, допускает UTF8 BOM, отвергает duplicate keys/NaN;
- извлекает text из всех mapping nodes, сохраняет immutable items + sync_versions;
- сохраняет parent/node IDs у text items и attachment metadata/head histories;
- пишет items/FTS/heads одной transaction; item JSON receipts — после commit.

Наблюдаемые gaps: raw original hash есть, сам raw blob не хранится; structural,
empty и non-text nodes не имеют полного persisted ledger; conversation metadata
переписывается в head; unknown fields исчезают из extraction; message time/title
не входят в legacy text revision; namespace-wide absent update затрагивает
conversations вне выбранного файла. Это inspection archived code, не actual HEAD.

## Идентичности и immutable история

Raw blob: SHA256 исходных bytes, dedup один blob на hash в existing SQLite.
Source: `(namespace,source_key)`, stable operator key предпочтителен. Existing
CLI/callers без key допускают compatibility default из hash canonical local path;
rename создаёт новую source identity до explicit key, bytes dedup сохраняется.
Original version: namespace/source key/raw hash. Новые bytes => новая version;
повтор тех же bytes не создаёт duplicate version, новый origin добавляет lineage.

Extraction key binds fidelity adapter version, legacy text/attachment adapter
versions, validated policy/options digest. Extraction identity binds source
version + key. Canonical JSON новых fidelity IDs — sorted compact UTF8,
allow_nan=false; это явно иной helper, чем spaced automation_core.digest.
Не менять существующие compact chatgpt-export.v1 revision/item-ID formulas.

Metadata-only/raw formatting change создаёт новый original/extraction, text item
может остаться прежним. Повторное извлечение другим adapter key создаёт новую
extraction того же original. Old item.export_sha256 относится к его first stored
payload: свежий original доказывается extraction link, не rewrite old item.
Origin first_observed_at и head.last_observed_at не входят в logical IDs; append
history не превращается в mutating text revision. Parser error сохраняет raw
version + error outcome; message/attachment heads остаются предыдущими.

## SQLite owner и transaction

Reuse `content.sqlite3` и `_database/_insert_item`; existing owner из actual HEAD
имеет приоритет. contracts/DRAFT_OWNER_SCHEMA.sql — пять proposed tables в ЭТОЙ
DB, не отдельная база: raw blobs, source versions, origins, extractions, heads.
Original BLOB до 64MiB делает original+derived commit атомарным без filesystem
two-phase protocol. Лимит per selected input, не обещание unlimited archives.

В одном BEGIN IMMEDIATE: validate bound immutable capture, add raw/source/origin/
extraction, insert items/FTS/attachment versions, reconcile selected heads,
advance import head. Disk full/crash до commit откатывает всё. Parse/schema error
внутри уже captured budget создаёт raw + ERROR extraction без derived writes.
Receipt write failure после commit не отменяет durable DB state: return explicit
COMMITTED_WITH_RECEIPT_WARNING; regenerated receipts имеют те же item payloads.
Migrations выполняются до import transaction, idempotent; backup/rehearsal и
current writer ownership проверяются на actual code. SQL prototype in package
проверяет только structural FK/BLOB invariants на synthetic data.

Raw read: один regular-file open, descriptor fstat before/after, path identity
check symlink/device/inode where supported и size/mtime guard. Capture.hash и
stored raw обязаны соответствовать одному buffer. Concurrent write detection —
best effort local guard, не claim OS-level frozen file. Если guard ловит mutation,
NOT_CAPTURED без новой version; неизменность captured buffer проверяется hash.

## Честный node/branch ledger

Для каждого mapping node ровно одна row; structural message=null не теряется.
States: STRUCTURAL_NODE, TEXT_EXTRACTED, NON_TEXT_ONLY, EMPTY_CONTENT. Message
author role/time/content type и declared child list сохраняются как наблюдённые
metadata; unknown fields остаются в raw envelope. JSON Pointer — semantic locator
в original version, не fabricated raw byte offset. В этом PR нет normalized-text
reverse offsets; их owner — №10/later format-specific adapter.

Parent и child refs проверяются в пределах conversation. Missing parent/child,
parent↔child mismatch, current_node absent и parent cycle получают отдельные gaps.
Iterative cycle check bounded by total node policy; не recursively follow graph.
Не repair/guess parents и не flatten current branch. LOCAL_NODES_ACCOUNTED
означает всё наблюдаемое в файле, remote completeness остаётся UNKNOWN.
Ненаблюдаемая удалённая ветвь не создаёт fictional message count.

Text сохраняет legacy part-join behaviour (join accepted strings with LF). Это
derived text, не exact raw JSON. Raw bytes остаются authority для roundtrip.
Role=user не доказывает авторство каждой цитаты в body; quotes opaque, no inferred
speaker. Structural node author UNKNOWN; source message timestamp не captured
timestamp. Unknown author у legacy-incompatible message => raw+ERROR, не guess.

Attachment pointer PRESENT/MISSING/UNSUPPORTED сохраняет legacy semantics:
bytes_present=false, network_fetch_performed=false, retrieval_allowed=false.
Declared hash valid syntax не означает measured payload SHA256. Array part_index
identity не promise attachment stability при insertion/reordering parts.

## Selection reconciliation

Список conversation IDs из текущего valid export — единственный scope отсутствия.
Existing sync/attachment/conversation heads вне списка остаются untouched.
Within selected conversations missing previous text/attachment heads receive
present=0 с receipt reason NOT_OBSERVED_IN_SELECTED_EXPORT. Это не deletion из
remote service. Structural-only/new empty node может убрать current text head
из selected view, но previous immutable item/raw history сохраняются.

Два overlapping import sources в одном namespace продолжают existing last valid
capture wins semantics для выбранного conversation. No source precedence engine
в этом PR; использовать отдельные namespaces, когда оператору нужна изоляция.
namespace-snapshot destructive replacement option не вводить.

## Бюджеты и CLI

Existing raw≤64MiB, conversations≤1000, text item≤2,200,000 UTF8 bytes,
total extracted text≤64MiB, attachments≤100000. Новый total mapping-node budget
100000 учитывает structural/non-text rows во ВСЕХ conversations. Derived ledger
UTF8≤64MiB; превышение после capture => raw retained, ERROR_LEDGER_BUDGET,
derived heads untouched. Symlink/I/O/read byte limit => NOT_CAPTURED. Нет silent
prefix/truncation. Bounded whole JSON parse — честный current design; streaming
parser/out-of-core blobs и memory/device qualification — later measured slices.

CLI reuse ingest-chatgpt; add optional stable --source-key. Proposed sibling
inspection route returns bounded scalar/page metadata. Read original writes
verified BLOB to explicit destination temp+fsync+atomic replace. Existing output
needs explicit overwrite; no stdout raw/huge IPC or new Native command in this PR.
Exact names/routes freeze on actual owner; draft semantics in contract remain.
Full import ledger can be exported foreground to verified sidecar JSONL/header,
without editing already published BATCH/ZIP checksums №2/3.

## Проверка и предел evidence

Fixture corpus includes 18 ordered scenarios, manual labels, exact originals,
expected node/attachment ledgers and identity/revision links. Independent checker
checks raw reconstruction in SQLite draft schema, FK/hash constraints, rollback
and package/fixture mutations. Он не реализует приложение и не присваивает PASS
runtime acceptance. Actual import/migration/CLI/device gates остаются NOT_RUN.

На implementation: focused tests реального importer/DB, затем current AGENTS/CI.
Baseline commands to confirm on actual repository: python -B -m unittest discover
-s content-lab -p 'test_*.py' -v; node --test agent-bridge/*.test.mjs. Required
quality gates дополняются current instructions, failures resolve before handoff.

Expected diff: content_lab.py + small import_fidelity.py if owner warrants it,
focused importer tests and owner docs. No Windows shell/install/IPC diff №8,
no Python/JS grouping rewrite №6/7. Follow-up №10 consumes exact version refs;
search metadata can be prepared in parallel, current runtime integration waits
for actual contracts and merge/CI evidence.
