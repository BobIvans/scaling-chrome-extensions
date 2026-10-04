# PR006 — полный список функций

Добавлены 32 module-level functions/class methods в `content-lab/repo_groups.py`. Вложенные callbacks входят в соответствующие функции; новые Native endpoints не добавлены.

| Function | Возможность |
| --- | --- |
| `boundary` | Граница fault/visibility проверок. |
| `Resources.__init__` | Явные необязательные resource budgets; по умолчанию без corpus/time cap. |
| `Resources.check` | Cooperative deadline check. |
| `Resources.add` | Учёт нормализованных данных graph/ledger без усечения. |
| `policy_view` | Strict frozen policy и roots внутри operator profile. |
| `source_id` | Стабильный source ID без snapshot/global ordinal. |
| `group_id` | Стабильный SCC/group ID по membership. |
| `unmapped_eligibility` | Диагностическая whole-source projection для неизвестных facts. |
| `eligibility_view` | Чтение фактического PR005 owner и проверка source binding/version. |
| `read_eligibility_input` | Проверка явного normalized operator adapter/schema/hash/scope. |
| `verify_eligibility` | Полный ledger/qualification hash/state/type consistency. |
| `saved_analysis` | Проверка сохранённого AST по точным whole-source bytes. |
| `is_test` | Явная filename rule для evidence type теста. |
| `declared_view` | Strict trusted declared links с endpoint hash binding. |
| `plan_sources` | Deterministic Python graph/SCC, memberships, revisions, typed relations и gaps. |
| `raw_ref` | Reference immutable chunk IDs/hashes/ranges с whole-source text gate. |
| `segment` | Logical/revision IDs, raw budgets и prev/next identity одного segment. |
| `segments` | Потоковое разбиение references до EOF без total cap. |
| `plan_database` | Disposable private disk index с bounded SQLite cache. |
| `reference_rows` | Потоковое чтение parts из authoritative SQLite owner. |
| `fill_plan` | Полный uniqueness-indexed reference plan на диск. |
| `verify_plan` | Независимый readback всех sources/parts/chains/relations. |
| `table_rows` | Deterministic JSONL iteration с явным закрытием cursor. |
| `write_jsonl` | Streaming fsynced JSONL writer. |
| `page_name` | Generated-ID-only local navigation filenames. |
| `link` | Escaped HTML link/label. |
| `write_navigation` | Полная portable group/source/segment navigation с bounded pages. |
| `verify_files` | Readback JSONL против проверенного плана. |
| `verify_navigation` | Проверка всех сохранённых HTML hashes. |
| `verify_output_proofs` | Повторная проверка terminal artifact hashes перед публикацией. |
| `publish` | Scoped CLI owner: verified frozen input, disk staging, atomic directory publication/reuse. |
| `main` | Compact receipt CLI и typed failure path. |

Изменены existing `repo_source.import_graph` и `components`: cooperative progress/resource checks с сохранением прежних default semantics. Installer включает новый sibling. Full manifest, classifier, raw capture и portable ZIP остаются существующими владельцами.
