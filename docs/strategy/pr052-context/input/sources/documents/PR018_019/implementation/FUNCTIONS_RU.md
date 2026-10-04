# Планируемые функции

Названия предварительные: coding-чат сопоставит их с actual code и переиспользует existing symbols. Ни одна не объявлена построенной в этом ZIP.

| ID | Функция | Task | Ответственность |
| --- | --- | --- | --- |
| FN-001 | `observe_manual_implementation` | G3-007 | Поддержать ручное внедрение пользователем |
| FN-002 | `build_next_gap_brief` | G3-010 | Создавать следующий R&D brief по новым данным |
| FN-003 | `verify_change_artifacts` | UI3-013 | Проверить изменение по реальным артефактам |
| FN-004 | `reconcile_manual_merge` | UI3-014 | Превратить ручное «я внедрил» в проверку версии |
| FN-005 | `acquire_desktop_writer` | UI3-015 | Распараллелить подготовку и проверку с одним UI-писателем |
| FN-006 | `bind_merge_to_capability` | UI3-020 | Связать проверенный merge с обновлением и новой capability |
| FN-007 | `freeze_campaign_inputs` | PAR3-002 | Неизменяемые входы и общий manifest кампании |
| FN-008 | `canonicalize_windows_resources` | PAR3-004 | Каноническая идентичность ресурсов Windows |
| FN-009 | `build_effect_conflict_graph` | PAR3-006 | Граф конфликтов исполнения и будущей интеграции |
| FN-010 | `admit_resource_request` | PAR3-007 | Admission control для CPU, RAM, UI и провайдеров |
| FN-011 | `acquire_fenced_lease` | PAR3-008 | Атомарные leases, fencing и единственный DB writer |
| FN-012 | `reuse_evidence_cache` | PAR3-011 | Общий кеш доказательств и безопасное переиспользование |
| FN-013 | `prepare_write_worktree` | PAR3-012 | Worktree на отдельную write-задачу с одним Git-owner |
| FN-014 | `integrate_verified_patch` | PAR3-013 | Последовательный integrator с фактическим diff |
| FN-015 | `reserve_provider_budget` | PAR3-014 | Резервирование бюджета и ограничения backlog |
| FN-016 | `resume_valid_dag` | PAR3-016 | Resume с верификацией входов и остатка DAG |
| FN-017 | `verify_final_revision` | PAR3-017 | Независимая проверка AI-результата и ручного внедрения |
| FN-018 | `dispatch_bound_update` | PAR3-018 | Merge evidence → единственный updater → capability |
| FN-019 | `select_ready_with_aging` | PAR3-019 | Планирование по доступным возможностям и aging |
| FN-020 | `project_decision_journal` | PAR3-020 | Журнал решений и представление зависимостей |
| FN-021 | `control_accessible_queue` | PAR3-021 | Доступный контроль очереди; голосовой parity как отдельное расширение |
| FN-022 | `invalidate_claim_descendants` | PAR3-023 | Инвалидация устаревших исследовательских ветвей |
| FN-023 | `capture_implementation_assertion` | EVO3-005 | Checkpoint пользователя «я применил / merged» |
| FN-024 | `pin_target_revision` | EVO3-007 | Зафиксировать целевую ревизию и ручной путь commit |
| FN-025 | `resolve_merge_mapping` | EVO3-008 | Сопоставить merge, squash и rebase без SHA shortcuts |
| FN-026 | `run_registered_verification` | EVO3-009 | Проверять критерии на итоговой ревизии |
| FN-027 | `reconcile_observer_signal` | EVO3-011 | Observer и reconciliation сигналов без дублирования |
| FN-028 | `resolve_release_binding` | EVO3-013 | Связать release с исходниками и точным asset |
| FN-029 | `rehearse_candidate_migration` | EVO3-015 | Stage и репетиция миграции |
| FN-030 | `observe_active_installation` | EVO3-016 | Установка и независимый receipt устройства |
| FN-031 | `qualify_device_capability` | EVO3-018 | Qualification capability на конкретном устройстве |
| FN-032 | `compute_capability_usability` | EVO3-020 | Условие usable и привязка существующих workflows |
| FN-033 | `rank_next_evidence_gaps` | EVO3-021 | Следующий R&D документ из доказанных gaps |
| FN-034 | `coordinate_proposal_returns` | EVO3-022 | Координатор параллельных proposals |
| FN-035 | `bind_two_tab_result` | TAB4-09 | Связь второй вкладки с репозиторием и PR |
| FN-036 | `observe_merge_result` | TAB4-10 | Проверка merge и итоговой удалённой версии |
| FN-037 | `acquire_exact_candidate` | TAB4-11 | Получение точного commit в изолированную область |
| FN-038 | `qualify_candidate_revision` | TAB4-12 | Квалификация кандидата зарегистрированными заданиями |
| FN-039 | `diff_capability_contracts` | TAB4-13 | Сравнение возможностей и инвалидирование старых навыков |
| FN-040 | `prepare_recoverable_migration` | TAB4-14 | Пробная миграция и восстанавливаемое состояние |
| FN-041 | `activate_with_verified_rollback` | TAB4-15 | Атомарная активация и проверенный откат |
| FN-042 | `run_bounded_improvement_loop` | TAB4-17 | Ограниченный автономный цикл улучшений |
| FN-043 | `project_source_linked_brief` | LAYA4-028 | Следующий R&D brief из проверенных gaps и целей |
| FN-044 | `persist_schedule_occurrence` | ACTION5-25 | Зафиксировать durable расписание и offline catch-up |
| FN-045 | `evaluate_restart_eligibility` | ACTION5-26 | Продолжать work после restart с resource и checkpoint checks |
