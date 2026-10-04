# PR-010+011: единая библиотека источников и provenance graph кода

## Итог и граница поставки

Пользователь выбирает scope и импортирует TXT, папки, архивы, локальные специальные
Git payloads, ChatGPT/Telegram exports или наблюдаемый чат. Оригиналы сохраняются
дословно, извлечения получают собственные версии. Из поиска можно открыть тот же
диапазон прежней версии после перезапуска. По выбранному Git snapshot пользователь
получает Python/JS/TS-граф, unresolved ledger, связанные tests/contracts/owners,
полные SCC membership и все continuation parts. Цель связывает источники, код и
проверки; заметка или новая классификация не переписывают пользовательские слова.

Объединение убирает границу двух поставок: SourceAddress применяется и к цитате
чата, и к import edge, и к evidence smell. Одна schema migration, единый query
scope, один criterion ledger и один итоговый code PR. Сохраняются исходные шесть
WS и все их criteria, 20 tasks, 27 features, 6 goals и 4 decision records.

Это scoped фундамент продукта. PR-012 owns общий durable repo engine/полную repo
выдачу/delta/CAS; PR-013 — PDF/Office/OCR/media/web/GitHub adapters; PR-014 — AI
packet/semantic retrieval/backup/restore; PR-015 — installer и установленный
desktop; PR-016 — voice/Laya; PR-017 — AI UI delivery; PR-018 — release/update;
PR-019 — long campaigns; PR-020 — Studious bridge; PR-021 — итоговую qualification.
Внутри этого PR поиск/import/graph pages доходят до конца собственного результата.
Оставление repo listing LIMIT 20 в другом owner не оправдывает обрезанный поиск.

## Исходная точка и обязательный аудит

Вложенный roadmap сообщает historical main
`9fbadef2714fae92e516a80b52d29cb9824b0e44`, merged PR #38–41 и open #42–44 на
момент своего снимка. Здесь не выполнена новая GitHub проверка. Эти сведения —
история. Проверить actual branch/HEAD/AGENTS, CI required gates, production owners,
schema version, реальные heads №5/6/7/8/9. Записать результат в BASELINE.json.

Не переносить как новый дефект старый whole-index/large blob blocker: roadmap
указывает уже существующие streaming blobs/index verification. Не считать PR006
group dialect и PR007 static dialect совместимыми без adapter. Не считать DOM
capture, generic TXT importer и reverse offsets уже выполненными №009. Его
контракт локального ChatGPT JSON сохраняется, старые IDs/revisions не меняются.

Historical candidate paths: content-lab/content_lab.py (source/items/FTS),
content-lab/repo_context.py (raw snapshot/selection), content-lab/repo_source.py
(Python AST/SCC), actual repo_manifest/repo_groups/JS adapter files, Core service
и текущая desktop/capture UI. Новые filenames в METHODS.json — proposed handlers;
если owner уже есть, расширять его вместо параллельного service/store.
Перед diff заполнить CURRENT_VS_PLANNED current_symbol/path/receipt для каждого WS.

## Общий слой идентичностей

1. Source logical identity живёт в namespace/profile/repository/source key.
   Для folders устойчивый явный source key предпочтителен; сходный текст или
   одинаковый hash не доказывают rename. Без такого key rename — новый origin и
   явная candidate lineage, а не guessed identity. Legacy raw chunk IDs сохранять.
2. Raw object — неизменяемые bytes с measured SHA256/size; в рамках допустимого
   store dedup bytes допустим, но не объединяет origins/evidence families.
3. Original revision binds source + raw hash; extraction revision binds original
   + extractor/version/options. Изменение CRLF/metadata меняет original даже если
   normalised text тот же. Observed_at не входит в logical source identity.
4. SourceAddress binds scope, source/revision, raw hash, coordinate system,
   half-open range [start,end), extraction revision и mapping quality.
   RAW_BYTES работает по original bytes; DERIVED_UTF8_BYTES — по derivation bytes;
   JSON_POINTER — semantic locator с extraction. UNKNOWN mapping не получает
   выдуманного raw span. Python line-only legacy anchors помечать LINE_ONLY.
5. Перед чтением проверить auth scope → существование revision → immutable hash
   → bounds/coordinate mode → range hash. Hash не заменяет scope authorization.
   STALE/MISSING/TOMBSTONE не переключают ссылку на latest похожую цитату.
6. Canonical identity helper брать у текущего owner. PR006 group digest и PR009
   compact fidelity digest различаются; новый контракт имеет собственную version
   и adapter mapping. Не унифицировать старые hashes пересериализацией.

Бинарный источник может быть RAW_AVAILABLE и EXTRACTION_UNSUPPORTED. Учёт entries,
полнота raw bytes, извлечение, graph analysis и packet inclusion — независимые
метрики. Pending/blocked исключают статус processing_complete; fully_accounted
допускает explicit gaps. Captured unsupported original не является parsed text.

## WS-001: адреса, поиск, метки и views

Сначала расширить read API immutable revisions и добавить boundary validator.
Exact ID/path/quote lookup не требует AI/network. FTS остаётся текущим owner;
source metadata и FTS generation должны публиковаться согласованно. При FTS
external-content проверить существующие transactions/triggers, выполнить rebuild
при migration и сверить MATCH с independent source listing. Не использовать
FTS tokenizer offsets как будто это raw byte offsets.

SearchRequest содержит query mode, namespace/profile, project allowlist, source
types, topic/goal/status, time field/range, version selector и stable cursor.
Scope ограничивает кандидатов до snippets/ranking/count; global bm25 corpus
statistics способны смешать scope, поэтому qualifier проверяет выбранную
изоляцию индексов/скоринга. Самого post-filter недостаточно. Cursor binds query
digest + scope + catalog/index generation + stable order (rank,source,revision,
hit anchor). При изменении generation вернуть CURSOR_STALE, а не перескочить хвост.
Не держать долгую DB transaction весь UI-сеанс. Старые generation хранить до
expiry или дать явный restart query. Каждая page bounded, общий result — полный.

Exact quote ищется по declared layer: literal raw decoded text либо extracted
UTF8. NFC/NFKC, case folding, LF conversion — отдельный normalised view с reverse
map. HTML/JSON entity decoding может давать one-to-many segments; selected match
возвращает несколько source ranges или UNKNOWN, никогда invented contiguous span.
Timeline хранит source_event_at, captured_at, inferred_event_at отдельно, с
uncertainty/timezone provenance. Unknown event time — отдельная группа.

Label observation: facet/value/rule-or-model version/source anchor/evidence class;
ручной overlay: editor/revision/supersedes/explicit unset. Reindex инвалидирует
derived observation, но сохраняет manual correction. Конфликт и revert доступны.
Project ACL/retention — независимые trusted fields, tag не расширяет доступ.
Taxonomy version хранит alias map; historical labels не переименовываются молча.
Сохранённый view — versioned query + scope, без копирования originals.

## WS-007: registry, TXT/folders/archives и специальные bytes

Reuse source owner + existing job/extractor queue. Ввести adapter registry с
support matrix/schema/extractor digest, pure input/output, declared resource
limits. Не запускать команды из unknown importer fields. New fields сохраняются
в raw envelope. Extension/MIME disagreement хранится как observation.

Состояния per entry: DISCOVERED → CAPTURING → RAW_COMMITTED → EXTRACTING →
DERIVED_COMMITTED. Side outcomes EXCLUDED/UNSUPPORTED/MISSING/ERROR/DEFERRED;
операции имеют PAUSED/CANCELLED/SOURCE_DRIFT/RECOVERY_REQUIRED. Ledger disposition
и importer outcome раздельны: imported raw может иметь unsupported extraction.
Checkpoint: operation ID+request digest+scope+input fingerprint+adapter/options
versions+confirmed object hashes+cursor+fencing token, когда текущий owner его
предоставляет. Same ID/different request — конфликт. Resume не принимает другой
upstream revision молча. Cancel сохраняет committed bytes и не публикует staging.

Текст читать потоком, сохранять BOM/CRLF/nulls/invalid bytes без исправления.
UTF8/UTF16 BOM/явно выбранная Windows-1251 квалифицируются fixtures. Не угадывать
неоднозначную encoding как точную: RAW_AVAILABLE + ENCODING_UNKNOWN, оператор
может выбрать decoder revision. Обратная карта учитывает byte boundaries;
unsupported/oversize parse оставляет raw и явный next action.

Folder inventory: immutable run manifest и per-entry outcomes; walk symlinks
только по явной policy scope, default metadata-only. Missing between enumerate
and open отличается от excluded. Rename/delete сохраняют previous revisions;
not observed в этом scope не доказывает физическое удаление во всём namespace.

Archive: контейнер сначала сохраняется как original. Member identity включает
container revision, ordinal и original name bytes/decoder; duplicate entry names
не overwrite. Nested containers, empty entries, повторные bytes и attachments
создают собственные provenance edges. Проверять traversal/absolute/drive/UNC,
Windows reserved names, separator normalisation, symlink, decoded-name collisions
до записи; staging должен быть в выбранном scope. Budget для expansion/ratio/depth/
CPU/disk — configurable, остановка даёт ledger + continuation/blocked state.
Encrypted/unknown format сохраняет original и unsupported/key-required gap.
Повторная распаковка не повышает independent corroboration count.

LFS pointer hash/size отличаются от заявленного payload oid/size. Доступный local
payload проверяется против oid/size; mismatch остаётся gap. Submodule commit/path
не является bytes его tree; external fetch здесь автоматически не выполняется.
Symlink metadata не выдаётся за target content. Уже захваченные repo_chunks не
перекраивать ради graph/import integrations.

## WS-008: ChatGPT/Telegram exports и full-scroll

Existing ChatGPT importer №009 сохраняет raw original/extraction revisions и
structural nodes. Добавить adapters Telegram export и CaptureEnvelope для
наблюдаемых DOM fragments. Stable identity: service/export scope, conversation,
message/node ID, edit revision; similarity текста не склеивает branches/authors.
Одинаковое сообщение в top/middle/bottom вызывает observations одной версии,
edited body создаёт новую версию. Unknown ID требует explicit adapter-local
identity/uncertainty; одинаковые реплики разных message IDs не удаляются.

Author role/user ID и quoted span speaker — разные поля. Unknown speaker остаётся
UNKNOWN. Original raw text доступен даже при неполном quote parser. Branch graph
сохраняет parent/children/current-node как наблюдения; missing parents/cycles и
удалённые nodes имеют gap, не repaired topology. Attachment metadata сохраняется
даже при missing payload. HTML export — inert data, script не выполняется.

Scroll checkpoint содержит target binding revision, conversation identity,
adapter/layout version, seen-ID set/locators, observed boundaries и gaps.
Повтор page/scroll без новых сообщений не означает end-of-history. COMPLETE
только в explicit observed scope при проверенном end marker и comparison с
доступным authoritative export; remote/unobserved completeness UNKNOWN.
Login wall/layout drift/branch inaccessible дают PAUSED или gap. Resume после
смены вкладки/аккаунта/чата — TARGET_DRIFT, не запись в прежний source.
Чтение capture не отправляет сообщения. Delivery принадлежит PR-017.

## WS-012: цели, заметки, contradictions и evidence dashboard

GoalRequest сохраняет exact user text/digest/source addresses/language и authored
interpretation. RU/EN перевод — отдельная revision с provenance, а не overwrite.
Неизвестный target/term остаётся вопросом. Requirements получают стабильные IDs и
frozen revisions; edits сохраняют predecessor. Notes создаются в своём source
kind, own text и exact source refs; редактирование не мутирует imported original.

Contradiction — минимум две claims/source revisions + applicability interval +
relation/reason + operator resolution revision. Новая информация не удаляет старое
решение. Evidence family от quote/summary/copy grouping исключает ложное увеличение
подтверждений. Surface proposition отличается от measured outcome.

Requirement→source→code→test→result links typed. Static test import ≠ observed
coverage. Код найден ≠ implemented, merged claim ≠ integration verified, installed
≠ usable. Guard выдаёт PASS/FAIL/UNKNOWN/STALE с receipt refs, invalidation inputs,
scope и next action. При смене revision/build/config устаревают только зависимые
receipts; replay projection детерминированно. Critical missing criterion исключает
achieved. Dashboard показывает denominator и открытые/отложенные критерии.
Сейчас создать query/UI минимум этих overlays; execution activation и installer
обслуживаются их downstream owners, не подменяются status кнопкой.

## WS-004: квалифицированный статический JS/TS resolver

Прочитать parser ADR и implementation №007. Выбрать exact parser artifact/version
по JS/TS/JSX/TSX syntax, memory/offline Windows packaging и licenses; pin=null
пока измерения не выполнены. Нельзя объявить текущий latest подходящим. Parser
traversal синтаксиса не исполняет scanned module, config JS, hooks/install scripts.
Trusted helper загружается отдельно от snapshot, только declarative config читается.

Support matrix по явно frozen resolver modes: TS_NODE16, TS_NODENEXT, TS_BUNDLER,
NODE_CJS, NODE_ESM, limited CUSTOM_DECLARED. Учитывать import-vs-require context,
nearest package type, paths/baseUrl, declarative extends, workspace package names,
imports/exports/subpaths/conditions, extension substitution, tsconfig references,
rootDir/outDir declaration remapping только в квалифицированном subset.
Неподдерживаемый config/condition даёт CONFIG_UNSUPPORTED, а не guessed alias.
Файлы читаются из frozen manifest, а не произвольного host node_modules. Не
подставлять external package absent target. Type-only edge отделяется от runtime.

Scope-aware CommonJS учитывает lexical shadowing require/module/exports;
computed require/import записывается DYNAMIC_SPECIFIER. module.exports и
re-export фиксируются с typed span, но не считаются произвольным runtime graph.
ESM named imports ссылаются на module source; unresolved symbol/export отдельно.
Candidates, chosen rule, ordered conditions и config hashes публикуются.

Outcomes: RESOLVED_LOCAL, EXTERNAL, DYNAMIC, AMBIGUOUS, MISSING, UNSUPPORTED,
PARSE_FAILED, INELIGIBLE, STALE, RESOURCE_BLOCKED. Every import occurrence accounted.
UTF16 parser offsets преобразовать в byte coordinates с Unicode fixture; TSX
не анализировать как plain TS. AST 2MiB window из historical code не обещает
полного syntax scope: parse по полной захваченной source в budget, либо явный gap
и resumable/isolated alternative. Обрезанный prefix не получает full-graph статус.

Независимый holdout закрывает source LX4-03: минимум 200 labelled fixtures,
precision ≥98% для supported local static edges; known dynamic marked unresolved
100%; recall/unsupported/outcomes публикуются отдельно. Precision undefined при
нуле predicted positives, gate не проходит на empty resolver. Corpus в этом ZIP —
starter, не утверждение уже достигнутых 200 fixtures или holdout результата.
Добавить disjoint holdout с frozen labels/hash до прогона и qualified independent
oracle; parser-under-test не генерирует собственную ground truth.

## WS-005: общий graph, SCC, owners/tests/contracts и smells

Явно адаптировать PR006 occ.repo-group-relation.v1 и PR007
occ.repo-static-relation.v1 к новой versioned projection. Сохранять original
dialect payload/digest и anchor quality. Python line-only relation не получает
fabricated raw span. Для новых parser versions exact byte spans квалифицируются.

Node identities используют immutable source/revision; edge includes type,
language, source anchor/hash, parser/resolver/config digests, target or unresolved
reason, evidence class. STATIC_PYTHON/STATIC_JS_TS, DECLARED_CONTRACT,
HEURISTIC_CANDIDATE и OBSERVED_TEST_COVERAGE раздельны. Mixed-language linkage
через declared API/schema/contract не выдаётся за static language import.
SCC topology включает только qualified static-local dependency edges выбранной
policy; contract/heuristic/coverage links доступны related view, но не меняют SCC.
Type-only topology задаётся explicit policy version.

Reuse iterative SCC №006. Deterministic source/edge ordering; no directory ordinal
в group logical ID. Membership change корректно меняет group ID; unrelated file
и новый budget сохраняют IDs прежних групп. Graph revision binds snapshot,
eligibility, config, parser, resolver, adapters, policy digests. Rebuild одинаковых
inputs имеет одинаковый digest. GRAPH_RESOURCE_BUDGET даёт BLOCKED с полным raw
ledger, а не VERIFIED обрезанного графа. Out-of-core extension — если требуется
по actual measurement, не обещание бесконечной RAM существующего SCC.

Oversized SCC — один logical group с complete membership и несколькими bounded
reference segments. Не изменять existing raw chunk hashes/IDs. Если raw chunk
больше выбранного budget, вернуть PART_BUDGET_TOO_SMALL или использовать
qualified subrange ref с parent raw identity. Primary range coverage отделить от
repeated explanatory snippets. Сохранить crossing edges, prev/next refs и gaps;
последний next=null только после полной обработки group. Listing/query курсоры
поддерживают весь tail и restart по frozen graph generation.

Owner map из current AGENTS/CODEOWNERS/trusted registry имеет declared provenance;
filename guess — heuristic. Test direct import не доказывает runtime coverage.
Observed coverage needs registered receipt exact build/scope. Contract picker
показывает producer/consumer/schema owner, target path/range, missing endpoints.
UI даёт открыть каждый anchor и добавить tests/contracts в selection/packet
draft через current selection owner; final packet format — PR-014.

Smell candidate содержит rule/version, subject ranges, supporting facts,
counterexample/check plan, severity candidate, status CANDIDATE/CONFIRMED/REJECTED/
STALE, receipt refs. Начальные rules: large SCC, unresolved contract consumer,
duplicate implementation candidates, source claim without matching test evidence.
Большой SCC сам по себе не подтверждённый дефект. Не запускать imported arbitrary
test command. High_Risk_Bugs/Architecture_Flaws export различает candidates и
confirmed findings. Никакой найденной функции не присваивать enabled/installed.

## Service/UI вертикали и ошибки

Все proposed методы перечислены в contracts/METHODS.json. Freeze actual route
names после audit; native/stdio frame bounds применяются к page, не к corpus.
Errors typed: SCOPE_DENIED, INVALID_RANGE, HASH_MISMATCH, UNKNOWN_MAPPING,
MISSING_ORIGINAL, TOMBSTONE, REQUEST_CONFLICT, SOURCE_DRIFT, TARGET_DRIFT,
CURSOR_STALE, SCHEMA_UNSUPPORTED, RESOURCE_BLOCKED, PARSER_UNAVAILABLE,
COMMITTED_WITH_RECEIPT_WARNING. Response содержит operation/ref/version,
durable state, retry/reconcile advice; raw/private text не попадает в logs.

UI минимум: Sources/import progress+entry gaps; Search/version+filters+next pages;
source range viewer; labels/views editor; chat branches/attachments; goals/questions/
contradictions/notes+coverage; Graph+owners/tests/contracts+group parts+smell details.
Keyboard navigation/open source после restart; отсутствие installer не заменяет
эти scoped product flows. Использовать existing client, не вводить отдельный UI
runtime лишь ради спецификации. Core unavailable даёт typed recoverable state.

## Migration, publish и crash recovery

Один migration coordinator, canonical DB owner. Сначала schema/compatibility audit,
backup/rehearsal старых DB fixtures, затем additive nullable tables/columns и
indexes. Новый source catalog связывает legacy item/sync/source IDs через mapping,
не rehash legacy records. Dual-read explicit schema adapter; старые clients не
получают неожиданно mutated payload. Backfill bounded checkpoint/idempotent;
FTS generations согласованы с source revision, heads CAS по expected revision.

Для small existing BLOB path сохранить его transaction. Для больших originals
использовать existing streaming owner; если extension needed, подтвердить write
protocol: temp chunks+verified hash+durable finalize → DB refs/entry head atomic
commit. Orphan raw object harmless и garbage-collect только без live refs;
DB никогда не публикует ref на незавершённые bytes. Crash после blob finalize/
до head commit resume проверяет bytes и переиспользует object. Crash после commit/
до receipt regenerates receipt из committed ledger. Migration/FTS/schema failures
не advance canonical heads. Optimistic conflict — показать/перечитать current head,
не слепой last-write overwrite manual labels/goal revision.

Rollback: сохранить старый build/schema backup; derived graph/index generation
можно rebuild, raw history не удалять. Old code с newer incompatible schema
останавливается с SCHEMA_UNSUPPORTED; не downgrade inplace. Restore backup только
через действующий owner с проверкой новых commits/conflict, без потери импортов
после backup. Rehearsal проверяет source address/labels/goal refs старых revisions.

## Проверки и условия закрытия

acceptance/ACCEPTANCE_CASES.json содержит concrete normal/fault/scale cases плюс
criterion-specific receipts для всех original tasks/features/goals/decisions/WS.
Coverage source criterion не равен завершённой task: cross-package prerequisites
сохранены; broad goals остаются OPEN до соответствующих downstream gates.

Focused application tests: original/import/DB/FTS, parser+resolver adapter, graph
identity/SCC, service/CLI, UI. Затем обязательные actual AGENTS/CI gates. Historical
baseline commands: python -B -m unittest discover -s content-lab -p 'test_*.py' -v;
node --test agent-bridge/*.test.mjs. Подтвердить их по current tree; не выдумывать
tests names/зелёные результаты. Negative/mutation cases ловят потерю хвоста,
namespace mismatch, altered hash, guessed dynamic edge, changed old raw IDs,
silent goal closure, lost manual tag, duplicate evidence family.

Windows 11 Dell qualification: pin installer/parser/helper/build, offline start,
Unicode/CRLF/long paths/Windows-1251; targeted worker crash/cancel/restart/disk-full;
RSS/CPU/disk/time-to-source, all started attempt outcomes. Linux synthetic fixture
не заполняет Windows receipt. До реального device результат NOT_RUN; downstream
PR015/021 остаются owners installed usability. Масштаб profiles задаются runbook:
41→1001→100000 entries, >20 hits/parts/chats, >2MiB source, oversized cycle.
Capacity stop explicit и resumable, unexplained omission=0. Пределы ресурсов
реального устройства допускаются и измеряются, произвольные общие cap — нет.

PR закрывает свой implementation scope после integration tests/mandatory CI и
reconciled criterion matrix. Status usable требует matching device evidence.
Unknown/stale/failed/deferred criterion не становится PASS через packaging или
merge. Нельзя сокращать scope из-за количества touched files/истечения часа.
Новая branch/PR описывает весь combined результат; GitHub PR number независим от
roadmap aliases. Полученное после merge доказательство записывается отдельно.
