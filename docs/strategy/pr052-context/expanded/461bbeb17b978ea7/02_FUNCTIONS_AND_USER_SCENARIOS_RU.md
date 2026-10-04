# Функции и пользовательские сценарии PR-010+011

58 proposed handler responsibilities. Это список для реализации, а не отчёт о уже созданных функциях. Существующие handlers переиспользуются; имена уточняются после current code audit.

## WS-001 — Точный поиск и организация

| Handler responsibility | Пользовательский результат |
| --- | --- |
| `open_source_address` | Открыть точную версию/range с проверкой scope/hash/bounds |
| `map_extracted_range` | Получить обратные raw ranges или UNKNOWN |
| `search_exact_id` | Найти immutable source/revision по ID без модели |
| `search_exact_path` | Найти выбранный path/version внутри scope |
| `search_exact_quote` | Найти дословную цитату в declared text layer |
| `search_fts_page` | FTS с scope до snippets/rank и cursor до конца |
| `query_timeline` | Выбрать source/capture time с unknown bucket |
| `record_label_observation` | Записать версионированную rule/model метку |
| `set_manual_label` | Создать manual overlay с optimistic revision |
| `revert_manual_label` | Восстановить прежний overlay без удаления наблюдений |
| `save_view` | Сохранить query/facets/scope без копирования raw |
| `list_view_page` | Открывать все страницы сохранённого view |

## WS-007 — Файлы и происхождение

| Handler responsibility | Пользовательский результат |
| --- | --- |
| `register_import_adapter` | Закрепить schema/formats/options/version/limits |
| `start_selected_import` | Создать идемпотентную операцию выбранного scope |
| `checkpoint_import` | Сохранить cursor и committed object proofs |
| `resume_import` | Возобновить после сверки request/input/version |
| `cancel_import` | Остановить staging, сохранив committed originals |
| `capture_original_stream` | Сохранить exact bytes потоком до финального hash |
| `decode_text_revision` | Извлечь TXT с encoding/BOM/CRLF и reverse offsets |
| `inventory_folder` | Учесть каждого выбранного entry и изменения scope |
| `import_archive_members` | Сохранить контейнер/member ordinal/nesting и gaps |
| `verify_local_lfs_payload` | Сверить local payload oid/size отдельно от pointer |
| `record_submodule_or_link` | Сохранить metadata без заявления target bytes |
| `reconcile_entry_ledger` | Сравнить accounted/raw/extracted outcomes |

## WS-008 — История чатов

| Handler responsibility | Пользовательский результат |
| --- | --- |
| `ingest_chatgpt_revision` | Расширить существующий importer original/branch ledger |
| `ingest_telegram_export` | Сохранить messages/edits/authors/media refs |
| `record_capture_envelope` | Записать observed fragment и source/capture times |
| `merge_observed_message` | Дедуп по scoped message identity, сохранить edits |
| `checkpoint_scroll_capture` | Сохранить target/seen IDs/boundaries/gaps |
| `resume_scroll_capture` | Продолжить virtualized capture после restart |
| `query_branch_page` | Показать все наблюдаемые nodes/branches и missing |
| `reconcile_export_and_dom` | Сопоставить доступный export/DOM без guess |

## WS-012 — Цели и доказательства

| Handler responsibility | Пользовательский результат |
| --- | --- |
| `create_goal_revision` | Сохранить exact phrase/RU-EN/interpretation provenance |
| `record_question_or_term` | Сохранить unresolved target/term и next check |
| `edit_note_revision` | Редактировать note, не imported original |
| `record_contradiction` | Связать claims/revisions/applicability/resolution |
| `assign_provenance_family` | Не считать quote/summary/copy независимым evidence |
| `link_requirement_evidence` | Связать requirement/source/code/test/result typed |
| `evaluate_goal_gates` | Детерминированно оценить PASS/FAIL/UNKNOWN/STALE |
| `query_goal_coverage` | Показать denominator/open criteria/next evidence |

## WS-004 — Статический JS/TS

| Handler responsibility | Пользовательский результат |
| --- | --- |
| `freeze_parser_interpretation` | Записать parser pins/platform/config/support matrix |
| `parse_js_ts_source` | Получить AST symbols/imports/spans без исполнения repo |
| `resolve_relative_import` | Применить qualified mode/extension/case rules |
| `resolve_ts_paths` | Применить frozen declarative alias/config chain |
| `resolve_workspace_exports` | Разрешить workspace imports/exports/conditions |
| `resolve_commonjs_binding` | Отличить lexical require от shadowed/computed |
| `record_resolution_gap` | Сохранить dynamic/external/ambiguous/missing outcome |
| `qualify_parser_holdout` | Измерить precision/recall/coverage и Windows packaging |

## WS-005 — Общий graph и analysis

| Handler responsibility | Пользовательский результат |
| --- | --- |
| `adapt_python_relation` | Сохранить Python dialect и anchor quality |
| `adapt_js_relation` | Сохранить JS dialect и interpretation binding |
| `build_provenance_graph` | Построить typed graph из pinned qualified inputs |
| `query_graph_page` | Выдать все edges/nodes/gaps bounded pages |
| `build_stable_scc_groups` | Переиспользовать SCC и deterministic logical IDs |
| `plan_group_continuations` | Разделить oversized group с полным membership |
| `attach_owner_mapping` | Различить declared/heuristic owner provenance |
| `pick_tests_and_contracts` | Показать source anchors и включить related selection |
| `record_smell_candidate` | Rule/source/check/counterexample/status/receipt |
| `export_findings` | Сохранить candidates/confirmed/stale с точными ссылками |

## Пять обязательных вертикалей

1. Выбрать смешанную папку → увидеть все entries и gaps → прервать импорт → restart/resume → открыть прежний original → повторный импорт без duplicate versions.
2. Найти старую RU/EN цитату → выбрать revision → открыть exact range → исправить метку → reindex → manual correction остаётся, private scope не расширяется.
3. Импортировать ChatGPT branches и Telegram edits → прокрутить virtualized transcript → рестарт → сверить с доступным export → увидеть inaccessible branches/attachments.
4. Выбрать Python/TS workspace snapshot → graph + unresolved → открыть import/config anchor → выбрать test/schema owner → получить все parts большого SCC без изменения raw chunk IDs.
5. Сохранить точную цель → добавить note/contradiction → связать source/code/test → получить scoped guard → изменить build/source → зависимый receipt STALE и next evidence виден.

Один combined PR может содержать несколько внутренних commits; число функций не задаёт искусственного числа PR или часов. Функции общей automation, web3/live и финального installer остаются у следующих крупных пакетов.
