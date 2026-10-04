# Зависимости, owners и передача

Объединённая external prerequisite set: ROADMAP-PR-010..019. Внутренняя зависимость 021→020 преобразована в WS-034/035→WS-029..033. Исходные task dependencies сохранены, broad task не закрывается до downstream acceptance.

| Пакет | Потребляемый контракт | Проверка перед dispatch |
| --- | --- | --- |
| 010+011 | source ranges, requirement registry, code graph | origin/version/range fidelity, actual owner paths |
| 012+013 | full repo jobs, importer/provider sources | complete cursor, restart/cancel, unsupported ledger |
| 014 | AI packet/retrieval/backup/restore | pinned packet/config/source identities, restored references |
| 015+016 | desktop/Core capabilities, IntentSpec/Laya/ASR | canonical writer, typed profiles, text controls, independent STOP |
| 017 | selected target/outbox/skills | binding schema, qualified device/UI adapter, reconciliation |
| 018 | final-tree release/install/update/rollback | actual candidate/build/installed identities and owner |
| 019 | scheduler/campaign DAG/leases/budgets/R&D | occurrence identity, fencing, restart policy, shared budget |

Current SCE paths in historical mapping: content-lab/repo_context.py, repo_source.py, context_review.py, native_adapter.py; agent-bridge/durable.mjs; one-click-context/library/repo-review-ui.mjs. Это anchors для audit, не требование создавать файлы по устаревшему пути. Studious exact qualification/broker/runtime paths устанавливаются из актуального кода, записываются в OWNER_MATRIX до новой реализации.

Proposal owner groups: SCE existing Core owns run refs/UI/job/evidence projection; Studious qualification owner owns mode/economic verdict; Studious acquisition owner owns immutable observation objects; SCE evidence owner evaluates criterion applicability; existing installer/updater owns activated code/migrations. Один SQLite migration coordinator, один UI/focus writer, один Git integrator, один updater. Модель/документ не становится runtime owner.

Один coherent SCE PR — primary delivery target. Companion Studious PR нужен только при реальном owner gap; связывать exact revisions/DTO fixtures/CI receipts, merge order и rollback boundary. До compatible deployed Studious build SCE can ship adapter disabled with named dependency; это scoped delivery, не final product closure. Нельзя скрывать companion requirement ради формального обещания одного PR.

Handoff соседнему чату: parent package, original IDs, actual base/HEAD, touched paths, reuse/extend/new decisions, proposed/current schemas, migrations coordinator, providing/consuming contracts, tests, blockers owner и next evidence. Код соседнего чата считается available только после observed compatible source state. Не брать в ownership функции 010..019 повторно; confirmed integration bug исправить у owner с regression и записать relation.

workflows/*.json — six orchestration design templates. They require mapping to actual registered commands and a verified Laya import schema before execution. Unresolved handler refs block dispatch. Ни native Laya workflow, ни установленный scheduler этим ZIP не созданы. Unattended длительность задаётся request и budgets; этот пакет не создаёт schedule или 24h run сам.
