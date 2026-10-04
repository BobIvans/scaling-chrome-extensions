# Интеграция: расширять существующее, не строить второй control plane

## Что действительно прочитано
Три документа перечислены в `repository_document_reads.json` с blob SHA и URL. Это не полный аудит кода, не current main commit pin и не проверка CI. Их содержимое — документированный status, не результат нашего запуска.

## SCE
Сохраняем владельцев `content-lab/repo_context.py` (inventory/cursor), `repo_source.py` (static chunks/imports/SCC), `context_review.py` (review ledger), existing Core queue/leases/cancel/reconciliation и `content.sqlite3`.

Desktop должен подключаться к выделенному локальному service/API с теми же owners. Tauri — возможная оболочка, а не основание переписать всю систему на Rust. Native Chrome transport может остаться legacy adapter, но не обязательным путём GUI нового app.

Documented constraints: 20 entries — размер страницы/порции scan, не 20 документов на всю библиотеку; 8 MiB blob limit и 32 MiB Git inventory output limit дают explicit ERROR; export имеет 10 text chunks/24k byte planning budget/80k document budget. Миграция: streaming inventory/blob ingest, bounded memory, resumable spool и user-configurable handoff budget. Не удалять timeout/security/resource checks просто ради слова unlimited. Scanned/stored/exported coverage показываются отдельно.

Code intelligence сейчас, согласно документу, Python/static; JS TEXT_ONLY, dynamic/external edges unresolved. Поэтому Tree-sitter/SCIP — optional bounded migration с pins/packaging/offline cache, а не уже существующий полный call graph.

## Studious
Поддерживаемые inspection entrypoints в прочитанном README: `flashloan-bot status --json`, `flashloan-bot capabilities --json`. Их здесь не запускали. `paper-shadow` может требовать внешних verified dependencies; режим paper не означает отсутствие сети. Live/signing/sending не включать в этот R&D pack.

Qualification authority остаётся в Studious. App читает structured status/receipts и вызывает только registered approved template после отдельного preflight. Не изобретать universal `run_qualification_suite` команду без сверки существующих CLI/tests/workflows.

## Контракты следующего PR
Точечные changes ниже сначала сопоставить с current exact commit и code owners. Имя функции из backlog не доказательство missing implementation. Никакие GitHub записи/PR/merge этим ZIP не выполнены.
