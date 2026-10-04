# План реализации

## 0. Gap audit и интеграционные договорённости

Записать actual repository/remote identity, checkout SHA, AGENTS.md и доступные проверки. Найти existing schedule_tick, supervisor, Core dispatcher, SQLite write owner, registered templates, task/job/checkpoint store, updater и capability registry через rg. Исторический SHA из sources/evidence — только контекст. Заполнить contracts/CODE_AUDIT_TEMPLATE.json с фактическими путями, символами, gaps и reuse/change решением. Имена из функционального каталога ниже являются proposed responsibilities, а не обнаруженными функциями.

Проверить №11–17: immutable context/manifest; backups и data migration; provenance/claims; policy/effect ledger; desktop STOP/accessibility; registered execution; two-tab task binding. Не переписать scheduler потому, что его прежнее API неудобно. Доработать existing public service/API и UI projections. Общая schema меняется одним coordinator через versioned migrations, forward compatibility проверяется для existing jobs.

## 1. Foundation WS-025 + WS-026

Через existing canonical store добавить schedules/revisions, occurrences, lease epochs, reservations и events. Уникальные ключи защищают occurrence, operation intent и callback revision. Проверка policy/source/capability versions происходит при admission и снова перед effect commit. Acquire всех конфликтующих ресурсов и бюджета — одна транзакция, либо ничего. Capacity baseline учитывается один раз; shared cache физически учтён отдельно от worker peak memory.

Canonical resource IDs строятся по Windows физической идентичности; строки path.casefold не достаточны для junction/UNC. Unknown alias получает conservative scope conflict. Read/read параллелен только для закреплённого immutable input. Repo metadata, integration branch, updater, DB mutations и desktop focus сохраняют единственного writer. Resource ordering/atomic acquire предотвращают deadlock; contention приводит к waiting reason с aging.

Schedule revision имеет IANA timezone, правила gap/fold, UTC cursor и catch-up policy. Windows wake trigger только будит Core; он не запускает независимый worker. Job eligibility, reserve, insert occurrence и cursor advance проходят атомарно. Дубли wake/tick/restart не создают повторный job. Изменение schedule оставляет исторические occurrences и проверяет пересечение новых intentions с queued effects.

## 2. WS-023: verified code и merge reconciliation

Owner создаёт изолированные worktree с pinned base и разрешённым output scope. Repo ingestion не запускает hooks/install scripts. Registered verifier запускает только утверждённые templates, сохраняет environment/tool/fixture digests и raw artifacts. Independent review связывает criterion с фактическим diff. Один integrator последовательно принимает patches, пересчитывает overlap и проверяет final tree. Изменение base/head/grant инвалидирует применимые receipts.

Observer принимает webhook, polling и ручное «я применил» как signals. Проверяет правильные repo/account/target ref, PR identity, head и merged state; сравнивает фактический final diff/дерево для merge/squash/rebase. Patch-id может быть вспомогательным сигналом, не sole proof. Remote update uncertainty получает UNKNOWN_EFFECT; fresh read выполняется до новой write попытки. Последующий revert оставляет исторический merge receipt, но актуальная feature coverage снимается.

## 3. WS-024: release → installed → usable

ReleaseBinding использует resolved tag commit, asset ID и digest реально полученных bytes, builder/toolchain/dependency provenance и scope. target_commitish/latest/tag name сами по себе proof не дают. Если byte-for-byte reproducibility недостигнута, записать GAP и policy outcome, а не заявить воспроизводимость. Изменение verifier/updater требует отдельной qualification и не может само расширить grants.

Exact candidate попадает в уникальный staging root. Registered acquisition/extraction проверяет completeness, traversal, symlink escape и disk budget. Backup owner предоставляет проверенную копию authoritative DB; rehearsal сравнивает schema/counts/relationships, чтение old/new records и compatibility существующих checkpoints. Описать post-switch writes: запрет, compatible shared schema либо доказанный перенос при rollback. Простое возвращение binary поверх несовместимой DB недопустимо.

Перед activation acquire installation lease, durable intent/recovery marker, scoped grant и свежие prerequisite receipts predecessor updater. Quiescence закрывает новые admissions и дожидается controlled boundaries; долгий job checkpoints либо activation deferred с причиной. Version directory/pointer меняется атомарно там, где это обеспечивает выбранная Windows упаковка; multi-file overwrite не считать атомарным. При запуске recovery наблюдает pointer, process/build digest и data schema, затем завершает конкретную попытку.

Installed receipt создаётся из независимого device observation. Canary выполняет исходный пользовательский сценарий на test target, учитывает device/build/OS/UI profile, keyboard STOP и recovery. Initial qualification session ограничен и не требует собственного уже полученного canary, но требует baseline STOP/scope/current target/effect limits. Unattended install требует квалифицированного predecessor updater. Rollback подтверждает восстановленные build/data/commands и сохраняет сведения о новых записях.

## 4. WS-027: campaign DAG

Manifest фиксирует goal IDs, source snapshots, omissions и immutable content refs; corpus хранится полностью, модель получает адресуемые selection views. Не помещать весь dataset в RAM или один prompt. Узлы имеют собственные contract versions, read/write scopes, dependencies, checkpoints и deadlines. Read-only proposals и drafts независимы от installed state; effect nodes ждут собственных gates.

Evidence cache key содержит source/input hashes + goal + parser/rules + capability version. От одного raw source производные claims не считаются независимыми подтверждениями. Branch compare использует единый baseline; join не суммирует зависимые trials как отдельные успехи. Join failure/pending/best-qualified/deferred правила явны. Запись final result идёт через одного owner с fresh fences; формального exactly-once для внешней системы без idempotency API не обещать.

Restart классифицирует завершённые receipts, corrupt checkpoint, stale source/policy/contract и unknown effect. Инвалидируются только зависимые descendants. Cancelled intent остаётся terminal для той revision. Истёкшая lease не означает отсутствия внешнего эффекта. Credits/quotas и reservations согласуются с provider receipt до release; unknown price не ноль. Backlog регулируется coalescing queued duplicates и superseded links, исходные намерения/контент остаются сохранены.

## 5. WS-028: evidence → experiment → next brief

Claim содержит source/ref/hash, span, lineage и verification status. Technology/media scouting идёт через registered read connectors; источник может быть unavailable/UNKNOWN. Повтор одного сообщения через разные пересказы группируется. Generated content не становится trusted instruction или новым grant. Планировщик формирует hypothesis, testable outcome, cost estimate, information utility, owner и stop conditions.

Brief различает missing code/evidence/release/device binding/access/data и сохраняет goal/task IDs, dependencies, acceptance, recovery, source refs и negative trials. Brief разрешён до release/install/usable; отсутствие receipts записывается как gap. Никакой implicit публикации, отправки в чужой чат или финансового исполнения. Для полного loop: max iterations/time/transfers/cost, progress fingerprint и no-progress threshold явно заданы. Повтор с тем же gap/evidence delta возвращает прежний draft; новая evidence даёт revision с supersedes.

## 6. Интеграционная приёмка и handoff

Пройти source criterion ledger и fixtures, compatibility существующих Core jobs, fault pilot scheduler/STOP/leases/updater/UI together. Product очередь доступна keyboard/screen reader, объясняет waiting owner/next evidence и STOP. На Dell снять baseline и уровни concurrency; serial production default сохраняется до квалификации. Точные thresholds фиксируются по измерениям, не по обещанию.

Один code PR содержит все шесть WS. Если hardware/provider gate недоступен, адаптеры и fixture-based tests могут быть готовы, но criterion остаётся OPEN. Перед merge проверить final integrated revision; после merge записать actual mapping и если target policy требует — повторить проверку merge result. Report включает built functions/paths и NOT_RUN device gates. Последующие №20/21 используют общий receipt protocol; этот PR не подменяет их web3/whole-product qualification.
