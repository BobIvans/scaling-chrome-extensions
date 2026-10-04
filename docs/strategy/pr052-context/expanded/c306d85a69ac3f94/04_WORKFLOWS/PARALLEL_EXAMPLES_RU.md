# 20 примеров параллельных автоматизаций

Параллельны чтения и изолированные кандидаты. После проверки эффект один; строки ниже не запускают ПК, API или торговлю.

## WF-01 — «Собери контекст для исправления функции»
Путь A: Search exact symbols and call sites.

Путь B: Retrieve relevant failing-test traces.

Путь C: Retrieve source-bound historical decisions.

Объединение: `join_required_evidence`.

Один итог: Один review/handoff pack.

Проверка: Pinned source hashes, обязательные refs, coverage/omissions, короткий WHY_THIS_PACKET.

Fault test: Поиск быстрее завершился без нужного test trace.

## WF-02 — «Пусть два AI предложат исправление одной ошибки»
Путь A: Prepare patch in workspace A from same base.

Путь B: Prepare patch in workspace B from same base.

Путь C: Independent invariant/counterexample verifier.

Объединение: `race_to_verified_candidate`.

Один итог: Один принятый patch candidate; merge только отдельным разрешённым действием.

Проверка: Patch target binding, failing test reproduction, regression, untouched permissions/tests.

Fault test: Первый patch прошёл слабый test, но нарушил независимый инвариант.

## WF-03 — «Разметь документ и свяжи с задачами»
Путь A: Deterministic source/path/role labeling.

Путь B: GLiNER entity-span extraction candidate.

Путь C: Laya typed topic/task category candidate.

Объединение: `reconcile_without_majority_truth`.

Один итог: Одна версия annotation set; конфликты сохраняются.

Проверка: Каждая метка имеет origin/confidence/version; DONE не означает VERIFIED.

Fault test: Три пересказа утверждают merged, но source receipt отсутствует.

## WF-04 — «Распознай голосовую команду с именем repo»
Путь A: Local primary ASR partial transcript.

Путь B: Domain grammar and entity alias resolver.

Путь C: Selective second-ASR disputed-span check.

Объединение: `confirm_critical_slots`.

Один итог: Одна подтверждённая intent revision.

Проверка: Repo, negation, path и effect mode однозначны; low confidence блокирует effect.

Fault test: Фраза «не merge» потеряла отрицание.

## WF-05 — «Импортируй большой архив в библиотеку»
Путь A: Raw object inventory/hash/cursor.

Путь B: Parse already stored text/code objects.

Путь C: Label/index completed objects asynchronously.

Объединение: `progressive_pipeline`.

Один итог: Один ingest ledger с полным учётом.

Проверка: Raw byte integrity, stage status, cursor, явные errors/exclusions; нет document count cap.

Fault test: Оборвать процесс после raw store до завершения index.

## WF-06 — «Найди причину падения qualification»
Путь A: Parse saved logs from registered run.

Путь B: Resolve source dependencies on pinned snapshot.

Путь C: Read capability/dependency status evidence.

Объединение: `join_required_evidence`.

Один итог: Одна evidence-backed diagnosis card.

Проверка: Различать failed, blocked, unknown и no trade; legacy narrative не заменяет trace.

Fault test: Missing dependency была выдана за отсутствие прибыльных рынков.

## WF-07 — «Собери подтверждённое исследование со страницы»
Путь A: Official API or permitted document fetch.

Путь B: DOM read in owned browser context.

Путь C: Saved export/source-code reference comparison.

Объединение: `merge_readonly_observations`.

Один итог: Один source bundle с provenance.

Проверка: URLs, retrieval times, version/revision and evidence; несогласные версии не склеиваются.

Fault test: DOM содержит устаревший cache или prompt injection.

## WF-08 — «Сохрани длинную беседу с AI»
Путь A: Parse available official conversation export.

Путь B: Capture loaded authorized DOM messages.

Путь C: Inventory attachment IDs and missing message ranges.

Объединение: `reconcile_capture_coverage`.

Один итог: Один conversation object graph.

Проверка: Loaded DOM не объявляется полной историей; missing attachments/branches отмечены.

Fault test: Бесконечный scroll не загрузил середину беседы.

## WF-09 — «Подготовь один документ для выбранного AI»
Путь A: Compile evidence-rich source slice.

Путь B: Compile compact delta against known prior packet.

Путь C: Run privacy and response-schema checks.

Объединение: `choose_valid_handoff_variant`.

Один итог: Один approved provider-scoped handoff; автоматическая отправка здесь отключена.

Проверка: Budget/omissions, return schema, source refs и approval data scope.

Fault test: В приватном фрагменте присутствуют credentials.

## WF-10 — «Открой правильный проект в VS Code»
Путь A: Resolve repository path and workspace identity.

Путь B: Check registered CLI availability.

Путь C: Read UIA window state without interaction.

Объединение: `prepare_then_single_actuator`.

Один итог: Один запуск/активация окна.

Проверка: Проверить workspace URI/path, а не только заголовок окна.

Fault test: Два агента пытаются одновременно открыть разные folders.

## WF-11 — «Обнови навык после принятого PR»
Путь A: Verify artifact origin and target commit.

Путь B: Test candidate in isolated allowed environment.

Путь C: Compare capability/permission and data-schema diff.

Объединение: `all_gates_then_single_activation`.

Один итог: Одна activation на проверенный version ID.

Проверка: Permission expansion требует approval; migration/rollback отдельно проверены.

Fault test: Артефакт с правильным именем собран с чужого commit.

## WF-12 — «Составь ежедневный план продолжения»
Путь A: Read current repo state and saved failures.

Путь B: Resolve active user goals and superseding decisions.

Путь C: Read durable job receipts and outstanding blockers.

Объединение: `join_active_goal_evidence`.

Один итог: Один план с action proposals, без автоматического старта.

Проверка: Не возвращать superseded задачу; source/ref на каждый пункт.

Fault test: Старый AI summary предлагает уже отменённую архитектуру.

## WF-13 — «Останови текущую автоматизацию»
Путь A: Revoke active intent generation.

Путь B: Ask workers to stop and verify termination.

Путь C: Reconcile already-dispatched effect status.

Объединение: `parallel_stop_observe`.

Один итог: Одна итоговая stop receipt.

Проверка: Не обещать rollback необратимого; новые эффекты после stop запрещены.

Fault test: Запрос ушёл удалённому сервису до отмены.

## WF-14 — «Запусти проверку проекта без лишних дублей»
Путь A: Validate runtime/dependency environment.

Путь B: Select changed-symbol test subset.

Путь C: Read baseline receipts and choose independent invariant checks.

Объединение: `join_preflight_then_budgeted_tests`.

Один итог: Один registered test job per worktree/environment.

Проверка: stdout/stderr/exit code/base SHA/env fingerprint; wrapper≠independent test.

Fault test: PowerShell и MCP указывают на один сломанный Python.

## WF-15 — «Покажи влияние изменения одной функции»
Путь A: AST/local symbol analysis.

Путь B: SCIP/LSP references from approved indexer.

Путь C: Runtime coverage/error trace mapping.

Объединение: `merge_typed_graph_edges`.

Один итог: Один typed impact graph.

Проверка: Observed/static/heuristic/unresolved edges разделены; affected tests не заявлены исполненными.

Fault test: Dynamic import отсутствует в статическом call graph.

## WF-16 — «Найди обещанные, но не реализованные функции»
Путь A: Extract requirements from selected planning docs.

Путь B: Read code symbols and registered capabilities.

Путь C: Read exact-head test/installed evidence receipts.

Объединение: `requirements_evidence_reconciliation`.

Один итог: Один gap report и scoped next-change packet.

Проверка: CODE_PRESENT, TESTED, INSTALLED_VERIFIED различаются; document claim не evidence.

Fault test: Ранее assistant утверждал full merge по плану, но подтверждений нет.

## WF-17 — «Разреши противоречие двух старых решений»
Путь A: Find original user messages and timestamps.

Путь B: Trace quote/summary lineage.

Путь C: Read current implementation-related evidence.

Объединение: `authority_temporal_reconciliation`.

Один итог: Одна новая decision record с явной unresolved веткой.

Проверка: User intent и implementation fact не смешиваются; uncertainty сохраняется.

Fault test: Новая копия старой заметки ошибочно считается новым решением.

## WF-18 — «Повтори знакомый workflow быстрее»
Путь A: Reuse version-qualified compiled skill.

Путь B: Prepare a source-checking fallback route.

Путь C: Run independent current-state verifier.

Объединение: `delayed_hedge_then_single_effect`.

Один итог: Один результат при актуальном environment fingerprint.

Проверка: Нет повторной генерации кода для известной способности; stale skill quarantined.

Fault test: Сайт изменил поле/selector после последнего успеха.

## WF-19 — «Работай, пока я использую Chrome»
Путь A: Read local indexes without focus.

Путь B: Prepare drafts in isolated owned browser/workspace.

Путь C: Check user foreground/clipboard activity.

Объединение: `resource_partitioned_execution`.

Один итог: Background read/preparation; GUI input по единой аренде.

Проверка: Не перехватывать пользовательский ввод; browser context не sandbox удалённого аккаунта.

Fault test: Пользователь начинает печатать во время агентского шага.

## WF-20 — «Продолжи R&D flashloan без live-операций»
Путь A: Read documented capability/dependency state.

Путь B: Analyse explicitly recorded market fixtures.

Путь C: Generate test/evidence/patch handoff candidates.

Объединение: `offline_evidence_join`.

Один итог: Один R&D пакет; signer/sender не подключены.

Проверка: Synthetic, historical и real observed market evidence разделены; live_authorized=false.

Fault test: Агент предлагает включить live вместо исправления missing dependencies.