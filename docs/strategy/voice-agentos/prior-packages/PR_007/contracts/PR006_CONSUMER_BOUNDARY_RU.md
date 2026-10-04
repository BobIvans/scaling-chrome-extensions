# Проверенная граница с полученным №6

PR006 input получен. Scope/planner_version=PYTHON_RAW_REFERENCE_GROUPS_V1.
Original contract/policy сохранены в previous/PR_006_* без исправления его истории.
Текущие accepted topology relations: PYTHON_STATIC_IMPORT и STATIC_TEST_IMPORT.
Его schema=occ.repo-group-relation.v1; evidence IMPORT_START_LINE_ONLY/DECLARED_MAP_FILE.
Поэтому он НЕ принимает JS records этого PR автоматически.

№7 emits occ.repo-static-relation.v1 в собственном derived bundle RELATIONS.jsonl.
Это отдельный input dialect, не overwrite/append в PR006 RELATIONS.jsonl. Нужен
отдельный versioned JS consumer adapter и новый grouping policy после qualification.
Нельзя переименовать JS edge в PYTHON_STATIC_IMPORT, чтобы пройти old gate.

Source-ID join должен сохранять №6 algorithm:
automation_core.digest({schema:occ.repo-logical-source.v1,namespace,repository,path}).
Это old digest с default JSON separators; edge_id №7 имеет другой явный domain
и canonical JSON. Source IDs не вычислять алгоритмом edge IDs.

Future JS topology может принимать only qualified VALUE_OR_MIXED literal source
path edges, если новая planner policy явно задаёт такую семантику. TYPE_ONLY,
dynamic/unresolved и heuristic test names не runtime SCC. Missing symbol/runtime
binding у source-file refs visible. Python groups/IDs/budgets не меняются №7.

PR006 был подготовлен до получения №5 и содержит original unmapped preflight.
Новый actual map к №5 дан в contracts/PR005_ADAPTER_MAP.json этого пакета;
original PR006 preflight сохранён как historical input, не переписан silently.
Runtime integration, mixed graph и owner/UI qualification остаются NOT_RUN/follow-up.
