# PR-007: JS/TS syntax → проверяемые source relations

Архивный `repo_source.analyze` использует Python AST. Для `.js/.mjs/.cjs/.ts/.tsx/.jsx`
он возвращает `JS_TEXT_ONLY_NO_SYNTAX_CLAIM`. `import_graph` добавляет
`JS_DEPENDENCIES_NOT_PARSED`; Python SCC уже существует и переиспользуется №6.
Новый часовой срез строит отдельную derived JS/TS projection из captured bytes.
Это позволяет сохранить raw partitions и передать planner typed edges позже.

## Scope и потребители

Основные source tasks: LAYA4-005 (AST/limited resolver) и LAYA4-006 (JS provenance
records). LAYA4-007 (owners/tests/contracts/capability UI) здесь получает только
явные contract boundaries; функциональность этого слоя не реализуется.
Whole LAYA4-005/006/007 остаются открытыми, как и все 160 source tasks.

№5 owns eligibility/formats/gaps; №6 owns Python groups/SCC/continuations.
№7 owns JS/TS syntax-derived records. `RELATIONS.jsonl` имеет отдельный JS dialect
`occ.repo-static-relation.v1`; полученный №6 использует `occ.repo-group-relation.v1`
и принимает только Python topology. Automatic JS integration в его policy нет. №3 получен как input и описывает export сохранённых chunks;
analysis №7 не переписывает chunk boundaries или exporter payload.

## ADR перед выбором parser

Сравнение candidates в research/PARSER_ADR_RU.md: TypeScript Compiler API,
Babel parser, Tree-sitter. Official API docs поддерживают parsing без исполнения
source code. Это не evidence подходящего memory/runtime на Dell Windows.
В этой упаковке candidates не установлены, runtime measurement NOT_RUN, pin=null.
В actual implementation выбрать exact artifact по measured corpus/features,
записать license, lock/tarball hashes, helper hash, Node/Python/platform versions.

Если выбирать TypeScript createSourceFile, использовать explicit ScriptKind для
JS/TS/JSX/TSX/MTS/CTS, plain syntax traversal; Compiler API <7 branch сверить по
exact installed version. Official wiki отдельно предупреждает о другом API 7.1.
Нельзя брать `latest` автоматически и считать старый helper compatible.
Babel с нужными JSX/TS plugins тоже требует pinned options/version. Tree-sitter
needs pinned grammars/bindings и Windows packaging qualification.

Выбранный parser/helper загружается только из installed trusted application
directory; execution cwd — install area, не scanned repo. Clear NODE_OPTIONS/
NODE_PATH/Git credential env и разрешать только reviewed parser module path.
AST — untrusted source data; найденные names/commands не получают execution rights.
Не emit/transpile/eval и не выполнять исходный module или package script.

## Immutable inputs

1. Проверить existing operator profile, exact namespace/repository alias/profile
   и snapshot. Требовать actual `get_snapshot.complete` proof; complete snapshot
   может содержать exclusions/errors. Отсутствующие bytes становятся file outcome.
2. Через cursor ordered by stable path читать каждый relevant entry; no fetchall,
   no path list cap=20/39. Per-file raw bytes реконструировать из existing chunks
   с contiguous `[start,end)` и hashes/revision proof; лимит existing MAX_FILE=8 MiB
   остаётся явным. Working tree и сеть в анализе не используются.
3. Consume №5 eligibility projection, exact schema/version/hash. Known №5 schema — occ.format-eligibility.v1, classifier utf8-controls-strict-lfs3.v1,
   store key analysis.format_eligibility; actual implementation всё ещё проверяется. Возможный legacy
   opt-in guard: indexed captured bytes, strict UTF8, JS extension, baseline
   exclusions; его version=LEGACY_CAPTURE_GUARD_UNVERIFIED_PR005. Не закрывать
   format completeness и не утверждать, что LFS/protected policy №5 согласована.
4. Один JS_ANALYSIS outcome на каждый JS/TS candidate entry, включая gap.
   Other-language entries имеют отдельные counts и остаются в original manifest.
   Missing/ambiguous actual facts = явный ELIGIBILITY_FACTS_UNAVAILABLE/UNKNOWN.

Raw files, snapshot ID, repo entries/chunks, file_hash и revisions immutable.
Не подключать новые JS boundaries к existing `partition`: смена partitions
переименовала бы stored part IDs и нарушила №2/№3. Symbol spans derived отдельно.

## Syntax и точные ranges

Supported extraction: ESM import/default/named/namespace/side-effect, `import type`,
`export {..} from`, `export * from`, `export type`. AST function/class declarations
имеют spans; advanced symbol ownership, callable resolution и observed test
coverage — follow-ups. Re-export edge указывает file reference; существование
exported name/type не подтверждено: symbol binding = NOT_TYPECHECKED.

Для статического literal сохранить decoded specifier и evidence range полного
quoted literal `[byte_start,byte_end)`. Для dynamic expression сохранить AST
expression/call range и unresolved reason, specifier=null при computed value.
Диагностики parser или recovered/error nodes делают whole-file PARSER_FAILED:
не публиковать provisional exact edges из повреждённого AST, retain text fallback.

Parser JS offsets обычно отсчитываются по строке UTF-16. В contract только raw
UTF8 byte offsets. Построить linear mapping или measured equivalent, учитывать
BOM bytes, CRLF и surrogate pairs; не strip BOM без offset adjustment.
Для каждой relation/symbol проверить raw slice hash и допустимые boundaries.
Нельзя использовать UTF-16 offset как byte index или повторно кодировать строку
с newline normalization. Ranges — evidence bytes, не весь parsed module.

## Resolver: literal source path, не runtime обещание

RELATIVE_SOURCE_EXACT_V1 работает только в pinned manifest. Candidate path =
normalize POSIX dirname(source)+relative specifier; `..` допускается только
в пределах выбранного scope. Никаких filesystem lookup, tsconfig/package scripts,
node_modules, package.json main/exports, basename matching или extension guessing.
Case-sensitive path identity берётся из Git, без OS path canonicalization.

JS/mjs/jsx static literal с explicit supported extension и ровно одним eligible
manifest target -> LOCAL_STATIC_EXACT_PATH, evidence=JS_TS_STATIC_SYNTAX,
resolution_scope=MANIFEST_SOURCE_PATH_ONLY. Для TS/TSX/MTS/CTS sources runtime
extensions `.js/.jsx/.mjs/.cjs` -> TYPE_RESOLUTION_POLICY_REQUIRED, даже если
в manifest есть одноимённый `.js`. TypeScript может substitute `.ts/.d.ts`:
не угадывать compiler modes. Explicit `.ts/.tsx/.mts/.cts` source path допускает
только source relation, не claim об actual runtime loader.

`require`, import-equals, dynamic import (включая literal), templates/computed,
aliases/#imports/workspaces/bare packages, extensionless/directory, JSON/assets,
queries, URLs, path case mismatch и scope escape имеют отдельные unresolved.
Exact file match не доказывает binding импортированного symbol или module exports.
Target known but ineligible/missing bytes -> TARGET_NOT_ELIGIBLE, не exact edge.
Type-only refs выделены как TYPE_ONLY и не добавляются в runtime SCC adjacency.
Mixed import — VALUE_OR_MIXED, без type resolution. Dynamic refs не входят SCC.

## Provenance и stable identities

Каждая relation: scoped source path/hash, evidence byte range/hash, syntax form,
specifier, dependency kind, nullable target/hash, resolution status/reason,
parser id/exact version/artifact hash, adapter/resolver/options/eligibility versions.
Source refs ведут в существующий file/chunk range index №2, не копируют bytes.

Logical edge_id = digest([domain,namespace,alias,source_path,syntax_form,
specifier,occurrence]) по canonical JSON contract; без total graph ordinal,
snapshot ID или enumeration order. occurrence — порядок одинакового form/specifier
в одном source. Edge revision = digest([edge_id,snapshot_id,source_hash,target_hash,
range,range_hash,interpretation_digest,status,reason]); cache key включает source,
manifest/eligibility/resolver options, а не один file_hash.
Symbol logical IDs по path/kind/name/occurrence; duplicate anonymous symbols
имеют явную uncertainty, не invented stable semantic identity.

Новый version/options/target manifest меняет derived revision/digest. Cold rebuild
и повторный ordered rebuild должны совпадать. Unrelated entry может менять
snapshot/graph revision, но не logical edge IDs уже известных refs. Не переносить
Python old edges в JS evidence class и не добавлять ложные byte spans к old
Python records, у которых archived analysis хранит только line.

## Derived bundle и limits

Новый CLI sibling `repo_js.py` читает existing DB read view и пишет staged folder
вне source на том же volume, что final output. Authoritative DB не меняется.
JS_ANALYSIS.jsonl: один outcome на relevant candidate; RELATIONS.jsonl: syntax
refs, включая unresolved; INTERPRETATION.json: actual pins/options; ANALYSIS_STATUS:
counts, hashes, proof scope, READY/PARTIAL/BLOCKED. `READY` означает complete
projection accounting, а не complete static resolution. `resolution_complete`
отдельно, eligibility readiness и unsupported cases отражаются явно.

Parser process по одной file, strict bounded input/output/stderr/deadline и cleanup.
No background worker, no new scheduler/Native command. Per-file timeout/crash/
output budget -> parser_failed file outcome, raw/text сохранились. Результат с
known parser failure может публиковаться PARTIAL с full accounted total, но не
объявляться успешно квалифицированным graph. Global abort/disk-full/cancel ->
BLOCKED, unpublished stage и previous bundle preserved. Partial global traversal
нельзя выдавать за полный inventory. Long restart/cache orchestration — follow-up.

Budgets в contracts/ANALYSIS_BUDGET.example.json. Нет total files cap; ≤8 MiB
передаваемых bytes на file — current capture guard, не whole repo limit.
Node V8 heap setting не является hard process RSS cap: измерять parent+child RSS.
Source LX4-06 для Dell5400/16GB: backend peak≤1.5GiB, progress≥1Hz,
Pause/Stop acknowledgement≤2s; в этом PR CLI cancel проверяется, UI/2workers
и complete 10k-file Windows scenario остаются NOT_RUN до device qualification.

После EOF и всех file outcomes verify ordered count/hash/version/read-snapshot
invariants; close children; publish staged directory atomically, refusing overwrite.
На одинаковом path/profile/snapshot existing verified output можно reuse только
при совпадении interpretation digest, schema hashes и content proofs.

## Corpus и фактические gates

В пакете 200 synthetic labelled cases: 20 family forms × 10 variations encoding,
comments/whitespace/prefix context. Есть JSX/TSX, types, parent paths, TS substitution
gap, CommonJS, dynamic, alias, workspace, fake imports in string/comment,
parse error, eligibility gap и source-scope escape. Labels написаны как AST
expectations и literal range checks; oracle не парсит JS и не доказывает extractor.

Source LX4-03: 200 labelled fixtures, ≥98% precision supported local-static edges,
100% known dynamic marked unresolved; recall и unsupported forms separately.
Этот synthetic corpus — bootstrap, не независимый real-world holdout. Qualification
report обязан показывать 20 family count, variants, empty denominator как null,
false positive/negative counts и holdout status. Нельзя получить artificial gate
путём игнорирования всех imports либо вывести precision=1 при нуле predicted edges.
Supported recall на positive corpus >0 и expected refs/outcomes все accounted.

16 future runtime cases: plan/ACCEPTANCE_CASES.json. Package validator выполняет
только labels/hash/schema/identity checks. AST application tests NOT_RUN.
В actual repo: focused JS adapter/resolver tests; then actual AGENTS gates,
`python -B -m unittest discover -s content-lab -p 'test_*.py' -v`,
`node --test agent-bridge/*.test.mjs`. No deployment/merge declared by package.

Expected diff: new repo_js.py, trusted parser helper/pins, focused tests, docs.
Owner UI, JS grouping integration, workspace/config resolver и mixed graph query
follow-ups отдельны. Не переписывать source files №5/№6 в parallel branches;
contracts сверены; теперь проверить actual owners и semantic regressions после integration.
