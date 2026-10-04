# Какие функции studious-pancake полезны SCE

Read-only audit: studious `67d3852cbc4cb1b24582df45adbf6a42d4da2af0`.
SCE base: `336a970ca222d513150d0183226a59d2da4bec8f`.
Это сравнение конкретных owners, не заключение о production readiness бота.

| Studious owner / функция | Что получает SCE | Текущий owner SCE / следующий шаг |
| --- | --- | --- |
| `src/qualification_report.py::_semantic_reason` | Проверка смысла результата вместо одного exit code | `review_report.verify_output` реализует byte-specific postcondition. Добавлять отдельный checker каждого будущего UI/export действия |
| `src/qualification_report.py::_checkpoint`, `_verify_completed_run` | Версионированные этапы, readback artifacts и integrity перед replay | `automation_core` сохраняет job/events; report reconciliation добавлен в этом PR. Для multi-step recipes хранить checkpoints в том же store |
| `src/fast_q_automation.py::_inspect_blocker`, `_owner_for`, `_prepare_repair` | Blocker → конкретный source owner/symbol/tests → ограниченный repair task | Расширять `repo_context` findings и `context_handoff`; сначала таблица mappings. Не импортировать market-specific blocker prefixes как общий router |
| `src/occ_memory_qualification_bridge.py::_verify_replay` | Request/profile binding и отказ от retry при неполном эффекте | Сохранить существующий `qualification_adapter` cross-repo API; `review_report` уже применяет этот принцип локально |
| `src/occ_durable_library.py::verify_current_version`, `history` | История source revisions и подтверждение current version | `sync_heads`, `sync_versions`, `review_results` уже владеют этим в SCE; не переносить вторую SQLite authority |
| `src/qualification_pr186.py::source_tree_identity`, `verify_signed_verdict` | Identity инструмента/сборки и независимое происхождение evidence | Будущий criterion verifier должен различать hash integrity и authenticated evidence. Imported SHA/claimed DONE не являются подписью или проверкой |

Практический следующий PR: registered checker registry + blocker-owner mappings
для одного действия на Windows. Input: exact action version, target snapshot,
source hashes, expected postcondition, cancellation epoch. Output: actual observation,
`PASSED/FAILED/UNKNOWN/BLOCKED/NOT_RUN`, hashes и минимальный next-context request.
Canary на установленном устройстве обязателен перед promotion этого действия.

Trading routes, wallet/sign/send, flashloan executors и market budgets должны
оставаться у Studious. SCE отвечает за context/task/UI orchestration и вызывает
уже существующий bounded qualification bridge для разрешённой диагностики.
