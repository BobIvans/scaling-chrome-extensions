# PR-006: связанные Python-группы и продолжения контекста

Target `BobIvans/scaling-chrome-extensions`, scoped `LAYA4-008`.
Это prepared input для примерно часа focused build плюс проверки. Current HEAD,
actual implemented №2/№5, remote CI/merge этим пакетом не подтверждены.

## Что получает пользователь

Выбранный snapshot становится каталогом logical groups: Python cycle остаётся
одной группой, с source hash/ID для каждого member, ссылками на тесты/контракты
и планом всех связанных captured parts. Oversized group получает bounded
segments с переходами назад/вперёд. Raw bytes сохраняют mapping №2. Поиск
нужного кода перестаёт зависеть от того, попали ли его соседи в одну page.

Группировка — статическая интерпретация кода. Exact captured-byte coverage,
text eligibility, graph completeness, AI read и observed test coverage имеют
отдельные показатели. `LOCAL_STATIC` не означает runtime dependency или coverage.
Все 160 broad tasks сохранены, этой упаковкой ни одна не выполнена.

## Scope и границы параллельных пакетов

| Пакет | Владелец задачи | Связь с №6 |
| --- | --- | --- |
| №2 | raw manifest/range mapping, LAYA4-009 slice | Exact base_batch_id/source/part metadata |
| №3 | portable captured export, LAYA4-010 slice | Raw bundle остаётся immutable; grouping — отдельный overlay |
| №4 | streaming Git inventory, LAYA4-003 | Code build на actual common base; long Native/Core follow-ups отдельно |
| №5 | formats/gaps/source-wide eligibility, LAYA4-004 | Нужен exact qualified-text/code input, имена DTO сверить |
| №6 | Python grouping, LAYA4-008 slice | Stable IDs, SCC segments, evidence-tagged related links |
| №7 | JS/TS parser/provenance, LAYA4-005/006/007 | Отдельный scoped follow-up, JS/TS gaps здесь видимы |

№5 известен только по user-provided progress excerpt. Там binary chunk может
случайно декодироваться как UTF8 и LFS pointer выглядит text. №6 не исправляет
classifier повторно: читает whole-source eligibility у owner №5. Unmapped or
unknown source eligibility => diagnostic-only/ELIGIBILITY_UNMAPPED, не parse
fallback из отдельного text chunk. Historical scan metadata без version/hash
mapping не доказывает новую qualification. Stable text/code flags в synthetic
fixture — **proposed adapter view**, не якобы установленная PR005 schema.

## Existing code и smallest diff

Сохранённый `repo_source.py` имеет `analyze`, `import_graph(rows, roots)` и
итеративный `components(nodes, edges)`. `repo_context.selection` уже строит
static closure и предлагает filename-related tests/contracts, но его selected
API bounded (10 inputs/items на page), а disclosures relevant/omitted имеют
truncation indicators. Эти budgets относятся к запросу; grouping corpus
нуждается в отдельном full ledger, не в увеличении случайного числа.

| Candidate owner/path | Минимальное изменение |
| --- | --- |
| `content-lab/repo_source.py` | Reuse Python graph/SCC; deterministic row/edge order and eligibility filter |
| actual `repo_manifest.py`/writer | Reuse authorised full metadata readers and frozen byte proof |
| `content-lab/repo_groups.py` (если аналога нет) | Pure group planner, IDs, bounded segments, derived writer/CLI |
| actual №5 eligibility owner | Read adapter mapping only; no competing classifier |
| `content-lab/test_repo_groups.py` | Real DB/CLI, independent SCC and identity/budget/eligibility cases |
| current docs/regression tests | Smallest actually needed changes; no imposed touched-file count |

Existing content.sqlite3/repo_entries/repo_chunks/analysis — source owners.
Derived JSONL/output directory rebuildable; нового store, scheduler, CLI shell
executor или graph package dependency не нужно. Archived source da6abf4 / local
V4 5574ab7 — reference, не actual HEAD. Сначала прочитать actual AGENTS/CI.

## Eligibility и topology

Normalized PR005 adapter должен ответить отдельно: tracked disposition,
captured bytes state, text_exportable, code_analysis_eligible, reason, revision.
Binding к namespace/repository/snapshot/source hash, classifier version и
output digest обязателен. Для Python parse eligible source saved analysis
должен соответствовать exact raw revision и parser policy. Если actual schema
имеет другую форму, реализовать явный минимальный adapter, не переназывать DTO
соседнего PR и не сохранять guessed schema как факт.

Построить module candidates с actual configured source_roots. Graph topology
accepts unambiguous Python static imports с qualified endpoints. Missing,
ambiguous, dynamic, parse-failed, stale analysis, ineligible target и JS/TS
dependencies имеют UNRESOLVED row с source/hash/line/status. Symbol/source imports
не требуют загрузки analysed modules или пакетов. Resolver расширения и runtime
intelligence остаются отдельными tasks. Candidate links по filenames и contracts
не входят в SCC. Direct test imports — те же qualified Python edges с role
`STATIC_TEST_IMPORT`, test execution/coverage при этом `NOT_MEASURED`.

Использовать existing iterative SCC, детерминированно сортируя nodes и edges.
Каждый entry имеет одну membership row. Graph-capable Python nodes входят в
SCC, остальные — metadata singletons с reason. Groups for ERROR/EXCLUDED entries
содержат только metadata; для captured binary/LFS raw refs сохраняются, text
payload eligibility false. Unknown edge не удаляет source из inventory.

Graph O(V+E) memory у existing helper сохраняется. Это не infinite-size claim:
configurable memory/time budget даёт explicit GRAPH_RESOURCE_BUDGET blocker
без усечённого verified catalog. Out-of-core graph и scale verifier №4 — отдельно.

## Evidence для соседних tests/contracts

| Relation | Evidence | Участие в SCC | Что можно утверждать |
| --- | --- | --- | --- |
| PYTHON_STATIC_IMPORT | Saved parser/resolver + import start-line/file hash | Да | Статически найденный local edge |
| STATIC_TEST_IMPORT | Тот же static edge из test path | Да | Тест импортирует source; runtime coverage NOT_MEASURED |
| OPERATOR_DECLARED_CONTRACT | Trusted mapping с exact endpoints/hashes/revision | Нет | Оператор декларирует contract relation |
| HEURISTIC_TEST_CANDIDATE | Filename/path rule с recorded rule version | Нет | Кандидат на related test, не подтверждённая связь |

Endpoint внутри frozen snapshot; declared target outside/EXCLUDED/stale hash
=> explicit DECLARED_TARGET_UNAVAILABLE/DECLARED_MAPPING_STALE. Не fabricate
missing group/source. Owner `UNSPECIFIED`, пока trusted owner map не supplied.
Related link показывает provenance и hash/range anchor; `IMPORT_START_LINE_ONLY`
честно отмечает, что existing analysis содержит lineno, а не full syntax span.
Не выдумывать byte coordinates entire import. Ни registered, ни installed
capability не следует из найденной функции/теста/owner link.

## Stable IDs и revisions

`source_id = digest({schema:'occ.repo-logical-source.v1',namespace,repository,path})`.
Existing raw part logical/revision IDs не меняются. `group_id = digest({schema,
planner_version,sorted member source_ids})`. Singletons используют ту же формулу.
Нет global ordinal/snapshot SHA в logical IDs. Добавление unrelated source
может изменить display ordering/entry ordinal, но сохраняет IDs прежних groups.
Если actual dependency меняет SCC membership, новый group_id корректен.

`group_revision` включает group_id/member file hashes, relevant static edges,
unresolved/declared links и policy revisions. Grouping batch binding включает
base_batch_id, snapshot/profile/eligibility digest, parser/resolver/planner
versions, roots/map hash и budgets. Global batch identity может измениться при
новом snapshot, logical source/group IDs остаются стабильными. Digest uses
actual automation_core serialization, не compact JSONL serialization.

## Bounded reference segments без потери хвоста

№6 планирует **references существующих raw chunks**, не перекраивает captured
bytes и не отправляет текст в AI. Каждая INDEXED part назначается одному member
group и одному primary segment ровно один раз. Related snippets в будущем могут
повторяться как annotations; они не увеличивают unique raw coverage.

Canonical source/part ordering inside group: stable source path, chunk ordinal.
Default raw-reference budget в fixture 4096 bytes; reference frame budget 8192
UTF8 bytes; max refs 16 на segment — configurable per segment, не cap corpus.
Считать serialized JSON bytes включая IDs/hashes/headers/neighbours; не считать
characters/tokens. Runtime policy freeze before planning. Empty chunk `[0,0)`
не пропускается. If immutable raw part больше budget или single reference
frame не помещается, explicit PART_BUDGET_TOO_SMALL/REFERENCE_ROW_TOO_LARGE
вместо обрезания. Оператор может выбрать больший budget; actual exact subrange
adapter нужен отдельно для более мелких text slices, chunks №2 не мутируются.

Каждый segment имеет prev/next IDs внутри group, budget totals и related-link
locator. Oversized SCC остаётся одним logical group с несколькими segments.
Last `next=null` только после полного mapping своего group. Groups/parts/pages
не имеют фиксированного total ceiling. Scalar GROUPS header с JSONL locators
избегает huge arrays всех members/edges в одной native response.

## Outputs и integration

| Artifact | Содержимое |
| --- | --- |
| GROUPS.json | Child batch binding, counts, versions и artifact hashes |
| GROUP_HEADS.jsonl | Stable group_id/revision, kind/reason/owner, counts, locators |
| GROUP_MEMBERS.jsonl | Все entries → one group, exact hashes/format view |
| GROUP_PARTS.jsonl | Все primary raw part references, segments/budgets/prev/next |
| RELATIONS.jsonl | Typed static/declared/heuristic links с provenance |
| UNRESOLVED.jsonl | Unknown/unsupported/stale/ineligible links and next action |
| COVERAGE.json | Complete membership/raw reference proof; text/graph/AI раздельно |
| INDEX.html + group pages | Static local navigation, generated relative links |

GROUPS header is written last after derived output verification/atomic directory
publication (reuse №2 writer). Original BATCH/REPO_MANIFEST/PARTS_INDEX are
referenced/copy-preserved and не переписаны. При future embedding в №3 portable
ZIP новый grouping digest/format создаёт новый archive output, не меняет уже
verified old checksum. Group-aware native picker/AI packet delivery не входят.

Proposed CLI (actual names сначала reconcile):

```bash
python -B content-lab/repo_groups.py --profile /absolute/native-profile.json --repository sce --manifest /absolute/verified-manifest --policy /absolute/group-policy.json --output /absolute/group-output
```

Trusted profile controls roots/store; policy только typed planner settings/map.
No arbitrary argv/source code execution. Output outside repo/store/input. stdout
компактный receipt; весь каталог локально streaming. In-memory SCC имеет явный
resource budget. Body/frame budgets не объявлять unlimited или менять Native
16k/192k/10s constants ради huge response.

## Шесть шагов и actual qualification

| Шаг | Минуты | Done output |
| --- | --- | --- |
| 1 | 5 | Actual owners + №5 adapter map + frozen source/policy |
| 2 | 12 | Qualified Python graph, unresolved ledger, minimal related links |
| 3 | 15 | SCC/stable IDs + complete membership + bounded segment plan |
| 4 | 8 | Atomic derived writer/CLI + small offline group navigation |
| 5 | 15 | Real DB/CLI, independent SCC/identity/budget/eligibility tests |
| 6 | 5 | Required gates, coherent diff, result receipt + next unmet criterion |

18 acceptance cases находятся в plan/ACCEPTANCE_CASES.json. Device opening,
same-budget usefulness comparison и measured large-corpus memory требуют
реальной evidence; synthetic fixture не закрывает их. Предлагаемые focused
commands для actual checkout:

```bash
python -B -m unittest discover -s content-lab -p 'test_repo_groups.py' -v
python -B -m unittest discover -s content-lab -p 'test_repo_context.py' -v
python -B -m unittest discover -s content-lab -p 'test_repo_manifest.py' -v
```

Required gates — по actual CI. В template все runtime cases NOT_RUN. Graph
fixture с labelled expectations и независимой mutual-reachability oracle
проверяет data package, не application helper or UI. Срез не закрывает весь
LAYA4-007/008, optional JS/TS/provenance, broad M5-02 или будущую автоматизацию.
