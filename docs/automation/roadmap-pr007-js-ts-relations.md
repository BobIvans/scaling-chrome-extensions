# PR007: статический JS/TS контекст из сохранённого снимка

`repo_js.py` добавляет read-only CLI анализа `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`,
`.tsx`, `.mts`, `.cts`. Он читает существующий SQLite capture, проверяет inventory,
диапазоны chunks, revision, SHA256 и Git blob OID, затем публикует отдельный
derived bundle. Рабочие файлы, Git, сеть, project dependencies и конфигурации
компилятора в анализе не используются. Raw chunks, IDs/revisions, Python analysis,
группы и PR003 ZIP остаются прежними владельцами данных.

```powershell
python -I -X utf8 C:\OCC\content-lab\repo_js.py `
  --operator-profile C:\OCC\native-profile.json `
  --repository sce `
  --snapshot-id ACTUAL_64_HEX_SNAPSHOT_ID `
  --output C:\OCC-exports\js-context-new
```

Профиль должен разрешать именно этот namespace, alias, store и repository
profile. Snapshot ID берётся из завершённого capture. Output — новый абсолютный
каталог вне source, store и установленного Content Lab. Поставляются Python
sibling modules, `repo_js_parser.cjs`, `js-parser/` и `js-contracts/`; installer
сохраняет этот layout. Нужны установленные Python и Node. `npm install` для
анализируемого репозитория не требуется.

По умолчанию нужны факты PR005 из `repo_entries.analysis.format_eligibility`:
`occ.format-eligibility.v1`, classifier `utf8-controls-strict-lfs3.v1`. Проверяются
полная схема, canonical decimal strings, snapshot/path/ordinal/mode/OID/size,
disposition и file hash. Разрешены INDEXED/nonlink blob, raw RECORDED и text
ELIGIBLE + UTF8_TEXT_CANDIDATE/EMPTY. NOT_RUN raw integrity заменяется независимой
проверкой actual chunks; FAIL не превращается в успех.

Stored PR005 facts содержат внутренний `_binding`. При наличии installed owner
адаптер вызывает его `facts_status()` и `project_facts()`, затем проверяет public
wire schema и source identity. Owner загружается только по точному trusted
application path; его SHA256 входит в interpretation. Private metadata без
соответствующего owner даёт явный gap. Known ineligible format остаётся полностью
учтённым в eligibility, хотя его syntax outcome содержит fallback.

Старые captures без этих фактов дают `ELIGIBILITY_FACTS_UNAVAILABLE` и PARTIAL.
Для них есть явный операторский `--legacy-capture-guard`: существующий indexed
text capture + strict UTF8, без нового format detector. В interpretation
записывается `LEGACY_CAPTURE_GUARD_UNVERIFIED_PR005`, а
`eligibility_policy_verified=false`. Этот флаг не обходит присутствующие, но
невалидные/неподходящие PR005 facts.

Публикуются четыре файла:

| Файл | Содержимое |
| --- | --- |
| `JS_ANALYSIS.jsonl` | Один outcome на каждый JS/TS candidate, включая gaps; function/class spans |
| `RELATIONS.jsonl` | Все найденные syntax references, exact и unresolved, с IDs/revisions и evidence |
| `INTERPRETATION.json` | Exact parser/helper/adapter/schema hashes, options, Node и input binding |
| `ANALYSIS_STATUS.json` | Проверенные counts/hashes и независимые completeness flags |

AST parser — vendored `@babel/parser` **7.28.5**, MIT. Byte-identical runtime
bundle, package metadata и лицензия проверяются по фиксированным SHA256 перед
запуском; tarball SHA256/SHA512 находятся в `content-lab/js-parser/PIN.json`.
Reviewed runtime bundle самодостаточен: dependency `@babel/types` из metadata
upstream не загружается нашим runtime. Parser/helper запускается из install area
по одному файлу, с очищенными NODE_OPTIONS/NODE_PATH/credential variables.
Node executable выбирается один раз до `--version`; путь внутри scanned source
или data store отклоняется до исполнения. Child использует этот же absolute path.
Captured source передаётся как ограниченный private frame. Он никогда не
import/eval/transpile/emit/execute. Fatal diagnostics дают PARSER_FAILED без
предварительных edges или symbols.

UTF16 positions переводятся линейной таблицей в raw UTF8 offsets. BOM, CRLF,
русский текст, surrogate pairs и escaped literals сохраняются. Каждый диапазон
`[byte_start,byte_end)` проверяется по исходному slice SHA256 и UTF8 boundaries.
Exported declaration spans включают `export`; anonymous declarations имеют
имя `<anonymous>` и не получают semantic binding claim.

`RELATIVE_SOURCE_EXACT_V1` ищет только точный case-sensitive путь в этом manifest
и выбранном source root. Поддерживаются ESM default/named/namespace/side-effect,
re-exports, `import type`, `export type`, inline type specifiers и TS import-type
queries. Нужен явный source extension. TS/TSX/MTS/CTS caller с `.js/.jsx/.mjs/.cjs`
получает TYPE_RESOLUTION_POLICY_REQUIRED; `.js→.ts` substitution не угадывается.
Alias/workspace/package/extensionless/asset/query/fragment/escaping references,
CommonJS и dynamic imports сохраняются с typed unresolved reasons.

Exact означает file-source reference. Symbol binding всегда NOT_TYPECHECKED.
TYPE_ONLY отдельно; только exact VALUE_OR_MIXED edges считаются потенциально
пригодными для runtime SCC. JS records имеют `occ.repo-static-relation.v1` и
не передаются автоматически Python planner PR006 (`occ.repo-group-relation.v1`,
PYTHON_RAW_REFERENCE_GROUPS_V1). Следующий consumer требует своей версии policy.

Logical edge ID использует compact canonical JSON, explicit domain, namespace,
alias, source path, syntax form, decoded specifier и occurrence внутри файла.
Snapshot/target/byte range/interpretation меняют revision, сохраняя logical ID.
Для ordered declaration symbols функция `symbol_identity()` возвращает аналогичный
path/kind/name/occurrence ID; опубликованная исходная file schema хранит spans.
Manifest/eligibility digest и hashes всех активных adapter modules входят в
interpretation. Проверяемый повторный build воспроизводит тот же bundle.

Лимита на число файлов или общий объём репозитория **нет**. По умолчанию также нет
общего time/output-size ceiling. Память зависит от текущего файла/AST/frame,
SQLite cursor и ограниченного projection buffer, а не от списка всех файлов.
Физические границы — диск, RAM и время.

Для отдельного AST вызова по умолчанию: raw input до 8 MiB, output до 1 MiB,
deadline 5 секунд, retained stderr 8 KiB/total 64 KiB, V8 old space 256 MiB,
cleanup deadline 2 секунды. Более крупный captured файл получает явный
FILE_PARSE_BUDGET; его raw capture и экспорт доступны без изменений. V8 heap
setting не является hard RSS cap. Parent/child working set измеряется в runtime
receipt stdout, без включения неповторяемых metrics в deterministic bundle.

`--budget C:\OCC\js-budget.json` принимает проверенные overrides, например:

```json
{
  "schema": "occ.repo-js-analysis-budget.v1",
  "file_timeout_seconds": 10,
  "global_timeout_seconds": null,
  "stage_max_bytes": null
}
```

Числовые global_timeout_seconds/stage_max_bytes — добровольные operator ceilings.
Per-file timeout/crash/frame overflow сохраняет outcome и может дать PARTIAL.
Global timeout, Ctrl+C, disk-full, corrupt raw или profile revocation блокируют
публикацию. Каждую секунду stderr выдаёт compact counters без source text.

Все записи сначала идут в private `.NAME.stage-RUNID` рядом с output. После EOF
проверяются входной count, сформированные byte hashes, interpretation и artifact
proofs; закрываются writer/child handles. Directory rename публикует весь bundle
атомарно. Kernel lock исключает одновременный build в один output. Existing
verified identical bundle можно reuse; другие options, corruption или лишний
member дают DERIVED_BUNDLE_CONFLICT без замены существующего каталога.

READY означает полный учёт и successful syntax projection, даже если существуют
unresolved references. `resolution_complete`, `syntax_complete`,
`eligibility_complete` и `eligibility_policy_verified` отдельны. PARTIAL может
иметь полный учёт files при известных file gaps. Незавершённый global traversal
никогда не получает projection_complete. BLOCKED stage сохраняет ограниченный
receipt; повторный запуск строит новый stage. Long-run checkpoint/cache resume
этого AST adapter — follow-up, отдельно от уже существующего PR003 ZIP resume.

Проверка: `python -B content-lab/qualify_repo_js.py` запускает actual adapter на
200 synthetic labelled cases, 20 families × 10 variants. Получены 67 true
positives, 0 false positives, 0 false negatives, precision/recall 1.0;
20/20 dynamic references unresolved, все 171 references, 190 symbols и 10 parser
failure files совпадают с labels. Это synthetic bootstrap, independent holdout
не предоставлен. No-reference inputs не подменяют denominator positive corpus.

ADR на Node v24.19.0/Linux: Babel cold module load ≈9.8 ms, 200 warm parses
≈56 ms, observed child peak ≈54 MiB. TypeScript 5.9.3: load ≈150 ms, parses ≈31 ms,
peak ≈88 MiB; сравнивались AST counts, его exact adapter не квалифицирован.
Для процесса на один файл выбран меньший самодостаточный Babel bundle. Tree-sitter
не измерялся; новая native grammar delivery не вводилась. Это локальный benchmark,
не результат Dell Windows.

Runtime tests покрывают CLI + real Git→SQLite capture, >39 files, strict facts,
default/explicit legacy, byte evidence, Node isolation, crashes/cancel/deadline,
disk failures, second process lock, corruption/refused overwrite, installed
isolated layout и одинаковые PR002 manifests/PR003 ZIP hashes до/после анализа.
Нагрузочный fixture: actual Git capture 2 001 synthetic JS files → 2 000 exact
source edges с неизменным raw ledger, explicit legacy guard.

Фактическая квалификация Dell 5400/Windows11/16GB, full 10k-file scenario,
UI Pause/Stop/2workers, actual installed Native registration, real-world holdout,
compiler-mode/CJS/workspace resolution, смешанный graph и owner/capability UI
остаются отдельными незакрытыми работами. Whole LAYA4-005/006/007 не закрыты.

Primary references: [Babel parser](https://babeljs.io/docs/babel-parser),
[TypeScript Compiler API](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API),
[TypeScript module resolution](https://www.typescriptlang.org/docs/handbook/modules/reference.html).
