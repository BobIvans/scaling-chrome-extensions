# Расширенная дорожная карта всех сохранённых целей · V5

Архив сохраняет прежние идеи и добавляет определение достижения: 28 групп
пользовательских результатов, 24 открытых проектных решения и 30 новых action
cards. Все 164 унаследованные продуктовые карточки включены в карту целей;
130 прежних задач остаются в общем backlog. Записи перекрываются и не являются
числом уникальных или уже работающих функций.

Главный следующий результат — одна команда для полного учёта repo, manifest
всех частей и связанных code/tests/contracts groups. Ручной task cycle уже
написан в scoped local V4. Одновременно можно готовить desktop упаковку,
импортеры, поиск и discovery указанных вкладок. Реальную передачу, обновление и
голос проверять по отдельным device/adapters receipts.

## Что означает «достигнуто»

У каждой цели есть исходные feature IDs, наблюдаемый сценарий и приёмка.
Переход от proposal к usable требует exact source/build, выполненных критериев,
подходящего устройства, квалифицированного adapter и действующего scope.
«Документ написан», «модель сказала готово», «PR merged» и «скачано» являются
разными событиями. Этот V5 меняет документы и каталог, не runtime.

План не требует внедрять 160 задач одним PR. Один ZIP держит всю стратегию;
один запуск будущей кампании выполняет разрешённые этапы с checkpoint,
ограничениями и конкретными blockers.

## Результаты и порядок

M5-01/M5-02 можно разрабатывать параллельно. M5-03 не ждёт Grok.
Для M5-04 сначала достаточно маленького canary TASK существующего V4.
M5-05/M5-06 требуют фактических внешних и installed evidence.
Text accessibility начинается в первых UI; голос расширяет уже работающий путь.
Нумерация не означает жёсткое ожидание всех прежних milestones.


| Gate | Пользовательский результат | Delivery prerequisites |
| --- | --- | --- |
| M5-01 | Доставить существующий task cycle и выбрать desktop основу | Pinned owners и baseline |
| M5-02 | Учесть и разбить весь выбранный repo одной кнопкой | Pinned owners и baseline |
| M5-03 | Сделать локальную библиотеку полезной для ежедневного контекста | M5-01 |
| M5-04 | Квалифицировать передачу в указанный Grok Build чат | M5-01 |
| M5-05 | Связать изменение с фактическим merge и staged candidate | M5-04 |
| M5-06 | Установить обновление с canary и проверенным откатом | M5-05, M5-03 |
| M5-07 | Преобразовать текст и голос в известные действия | M5-01 |
| M5-08 | Продолжать долгие и независимые задачи после offline/restart | M5-07 |
| M5-09 | Автоматизировать воспроизводимое исследование | M5-03, M5-07 |
| M5-10 | Квалифицировать долговременный контекст и повторяемую пользу | M5-03, M5-07 |

## M5-01 · Доставить существующий task cycle и выбрать desktop основу

Установить согласованную сборку, открыть библиотеку и задачу с закрытым Chrome; после restart найти тот же TASK.

Входные условия:
* Pinned repository/build identity и карта текущих owners.
* Доступный Windows test device; путь доставки кода с фактическим разрешением на публикацию.

Приёмка:
* Установщик не зависит от cwd и сохраняет один профиль данных.
* Task/manual delivery/result цикл доступен через текстовый интерфейс.
* Crash/reconnect и два клиента не создают competing writer.

Доказательства:
* Точный source/build manifest.
* Windows installation/start/restart receipt.
* Путь rollback данных и code version.

Восстановление: Без Windows evidence gate остаётся DEVICE_QUALIFICATION_PENDING. Публикация текущего локального commit отдельно заблокирована; документация не снимает этот статус.

Цели: GOAL5-01, GOAL5-12, GOAL5-28. Решения: DEC5-01, DEC5-09, DEC5-10, DEC5-18.

Work packages: G3-001, G3-011, TAB4-01, ACTION5-01, ACTION5-02, ACTION5-03.

## M5-02 · Учесть и разбить весь выбранный repo одной кнопкой

Выбрать repo, нажать «Собрать всё», видеть cursor/progress, остановить и продолжить; получить полный manifest и связанные части.

Входные условия:
* Фактический pinned SHA и существующие snapshot/native operations.
* Явный snapshot scope и ограничения диска/экспорта.

Приёмка:
* Каждый entry выбранного tree имеет отдельный outcome и reason; нет silent omission.
* Все INDEXED bytes восстанавливаются по manifest; диапазоны и chunk hashes согласованы.
* Связанные группы показывают resolved/unresolved/test/contract edges.
* Изменившийся HEAD создаёт новую версию; cancelled job не оживает после restart.

Доказательства:
* Tree-to-inventory comparison и byte reconstruction.
* Fault corpus: interruption, duplicate reply, large/empty/binary/link/LFS/submodule/dirty cases.
* Windows responsiveness/RAM measurements и scope этого измерения.

Восстановление: Unknown source остаётся в ledger с next action. Полный inventory не равен полному inclusion в один AI packet.

Цели: GOAL5-02, GOAL5-03, GOAL5-04, GOAL5-05, GOAL5-11. Решения: DEC5-05, DEC5-06, DEC5-07, DEC5-08, DEC5-09.

Work packages: LAYA4-002, LAYA4-003, LAYA4-004, LAYA4-005, LAYA4-006, LAYA4-007, LAYA4-008, LAYA4-009, LAYA4-010, LAYA4-011, LAYA4-012, LAYA4-026.

## M5-03 · Сделать локальную библиотеку полезной для ежедневного контекста

Добавить файл/чат, найти точную фразу, исправить метку, собрать документ цели и восстановить библиотеку из backup.

Входные условия:
* Один canonical owner и source/version/extraction model.
* Небольшой corpus реальных пользовательских вопросов и ожидаемых source ranges.

Приёмка:
* Оригинал, extraction, summary и quote различаются по ID/версии.
* Search возвращает точный источник/диапазон и применимость по времени.
* Manual labels сохраняются после повторной обработки.
* Share projection содержит выбранное, а restore проверяет referenced objects и heads.

Доказательства:
* Importer fidelity cases и unsupported ledger.
* Frozen retrieval corpus с hard negatives.
* Export hashes, redaction ledger и restore comparison.

Восстановление: Недоступная ветвь/вложение остаётся gap. Сбой extractor не удаляет original и не создаёт ложную новую history.

Цели: GOAL5-06, GOAL5-07, GOAL5-08, GOAL5-09, GOAL5-10, GOAL5-11, GOAL5-23, GOAL5-26. Решения: DEC5-09, DEC5-10, DEC5-11, DEC5-12, DEC5-13, DEC5-14, DEC5-15, DEC5-16.

Work packages: LAYA4-013, LAYA4-014, LAYA4-015, LAYA4-016, LAYA4-017, LAYA4-018, LAYA4-020, LAYA4-027, ACTION5-04, ACTION5-05, ACTION5-06, ACTION5-07, ACTION5-08, ACTION5-09, ACTION5-10, ACTION5-11, ACTION5-12, ACTION5-13, ACTION5-14, ACTION5-15, ACTION5-16, ACTION5-17.

## M5-04 · Квалифицировать передачу в указанный Grok Build чат

Пользователь показывает две вкладки; маленький TASK попадает в выбранный чат; результат импортируется с тем же task/packet identity.

Входные условия:
* Конкретный выбранный пользовательский account/chat/repo target.
* Квалифицированный UI adapter и наблюдаемые limits; разрешённый action profile.

Приёмка:
* Переключение account/chat/repo не сохраняет старую валидную привязку.
* Draft сверяется до send; каждая часть учтена отдельно.
* После возможного send без ответа выполняется reconciliation до retry.
* Returned claim связан с TASK; ручное подтверждение отделено от наблюдаемого provider evidence.

Доказательства:
* Device/DOM contract version и canary traces.
* Changed-target и interrupted-send corpus.
* Delivery observations с part hashes и bound result.

Восстановление: UNKNOWN_EFFECT не повторяется как новый send. ChatGPT/Gemini используют тот же packet model, но каждый UI adapter требует собственной qualification.

Цели: GOAL5-11, GOAL5-12, GOAL5-13, GOAL5-19. Решения: DEC5-02, DEC5-03, DEC5-04, DEC5-05, DEC5-13, DEC5-18.

Work packages: TAB4-02, TAB4-03, TAB4-04, TAB4-05, TAB4-06, TAB4-07, TAB4-08, TAB4-09, TAB4-19, ACTION5-14, ACTION5-21.

## M5-05 · Связать изменение с фактическим merge и staged candidate

Пользователь говорит «merged»; приложение проверяет repo/PR/final revision и квалифицирует candidate в отдельной области.

Входные условия:
* Точная repo/PR identity и выбранный канал получения source.
* Зарегистрированные qualification commands и frozen acceptance.

Приёмка:
* Merge/squash/rebase устанавливаются по final tree/artifacts; один текстовый claim не закрывает gate.
* Candidate SHA и release assets связаны с проверяемой provenance.
* Независимые tests относятся к итоговой ревизии и объявленному scope.
* Capability diff показывает missing dependencies и расширение permissions.

Доказательства:
* Remote merge/commit observations.
* Source/build/assets manifest.
* Exact-revision criteria evidence и failure capsules.

Восстановление: Branch drift или absent CI/evidence сохраняют candidate pending. Новый текст/code не становится installed capability.

Цели: GOAL5-05, GOAL5-14, GOAL5-15, GOAL5-16. Решения: DEC5-19, DEC5-20, DEC5-22, DEC5-23.

Work packages: TAB4-10, TAB4-11, TAB4-12, TAB4-13, EVO3-008, EVO3-009, EVO3-010, EVO3-013.

## M5-06 · Установить обновление с canary и проверенным откатом

Staged release проходит migration rehearsal, active process переключается; новая capability подтверждается на устройстве, предыдущая версия доступна для restore.

Входные условия:
* Verified candidate и согласованный backup.
* Updater/launcher owner, quiescence и data compatibility policy.

Приёмка:
* Исполняемая версия не заменяется посреди действия без выбранной quiescence policy.
* Installed receipt фиксирует actual build; download/merge не считаются установкой.
* Canary подтверждает effect capability на нужном устройстве.
* Rollback/restore не теряет heads и делает affected skills STALE при несовместимости.

Доказательства:
* Migration rehearsal и restore receipts.
* InstalledVersion evidence, canary и interrupted-activation corpus.
* Affected-capability/skill graph.

Восстановление: Неуспешный canary quarantines новую capability; пригодный text/manual путь остаётся доступным.

Цели: GOAL5-16, GOAL5-22, GOAL5-23, GOAL5-28. Решения: DEC5-10, DEC5-11, DEC5-19, DEC5-20.

Work packages: TAB4-14, TAB4-15, TAB4-21, EVO3-014, EVO3-015, EVO3-016, EVO3-017, EVO3-018, EVO3-020, ACTION5-16, ACTION5-18, ACTION5-24.

## M5-07 · Преобразовать текст и голос в известные действия

Ввести или произнести цель, исправить repo/chat/действие, увидеть resolved plan, выполнить зарегистрированную automation и остановить её с клавиатуры.

Входные условия:
* Typed registry и операторские templates существующего Core.
* Text/keyboard controls; optional microphone/Laya adapters имеют свою qualification.

Приёмка:
* Intent остаётся связанным с исходной фразой и критическими slots.
* Unsupported intent возвращает capability gap и конкретный brief.
* STOP доступен вне ASR/model и сохраняет uncertainty внешнего эффекта.
* Показанная демонстрация становится reusable skill после normal/fault qualification.

Доказательства:
* Text/voice parity и correction cases.
* STOP/focus/screen-reader corpus.
* Capability/skill receipt с build/profile/resources.

Восстановление: Voice не блокирует текст. Arbitrary shell из doc/AI claim не заменяет зарегистрированный action contract.

Цели: GOAL5-17, GOAL5-18, GOAL5-19, GOAL5-22. Решения: DEC5-02, DEC5-17, DEC5-18, DEC5-19, DEC5-22.

Work packages: ACTION5-18, ACTION5-19, ACTION5-20, ACTION5-21, ACTION5-22, ACTION5-23, ACTION5-24, LAYA4-022, LAYA4-023, TAB4-16.

## M5-08 · Продолжать долгие и независимые задачи после offline/restart

Задать campaign, выбрать catch-up, приостановить и вернуться; независимые исследования используют shared immutable data, а UI/repo/update сохраняют своего writer.

Входные условия:
* Resource identities, leases/fencing и budgets.
* Qualified resume policy; baseline resource measurements на целевом PC.

Приёмка:
* Нет duplicate occurrence после sleep/reboot/timezone change.
* Unknown write/send не возобновляется как новый effect.
* Admission измеряет RAM/CPU/UI/provider budget; backlog ограничен.
* Cancel и real user input имеют приоритет, worker не держит бесконечный loop.

Доказательства:
* Occurrence/job ledger и restart/fault cases.
* Lease/conflict traces и measured PC profile.
* Success/unknown/intervention/cost outcomes по всем начатым attempts.

Восстановление: Текущий production serial policy остаётся до отдельного пилота. Параллельность разработки планов не является qualification product parallelism.

Цели: GOAL5-20, GOAL5-21, GOAL5-27. Решения: DEC5-18, DEC5-19, DEC5-21, DEC5-22, DEC5-23.

Work packages: ACTION5-25, ACTION5-26, PAR3-004, PAR3-006, PAR3-007, PAR3-008, PAR3-014, PAR3-015, PAR3-016, PAR3-022.

## M5-09 · Автоматизировать воспроизводимое исследование

Выбрать research aim, собрать observations, выполнить зарегистрированный replay/paper case и получить следующий source-linked brief.

Входные условия:
* Actual SCE/Studious owner/entrypoint matrix.
* Dataset scope, exact raw provenance, frozen costs/units/holdout.

Приёмка:
* Mode READ_ONLY/REPLAY/PAPER и handler version фиксируются до запуска.
* Недоступные данные не подменяются найденными opportunities.
* Point-in-time inputs, negative trials и counterexamples сохранены.
* Next brief содержит unmet criterion/data gap и самый небольшой полезный experiment.

Доказательства:
* Dataset/freshness manifest.
* Exact-config experiment receipt и holdout.
* Coverage/gap report и next brief.

Восстановление: Unattended campaign добавляет gate M5-08. Paper/replay evidence не подтверждает live execution, прибыль или все будущие protocol adapters.

Цели: GOAL5-24, GOAL5-25, GOAL5-26, GOAL5-27. Решения: DEC5-16, DEC5-22, DEC5-23, DEC5-24.

Work packages: ACTION5-27, ACTION5-28, ACTION5-29, ACTION5-30.

## M5-10 · Квалифицировать долговременный контекст и повторяемую пользу

Увеличивать корпус, сохранять исправления и прежние versions; находить проверяемые ranges и выбирать следующую automation по её измеренной пользе.

Входные условия:
* Frozen corpus и manual baseline.
* Corpus-size profiles, retention/restore policy и selective invalidation graph.

Приёмка:
* Рост corpus не скрывает sources и не меняет semantics полноты AI packet.
* Реальные вопросы возвращают пригодные ranges и известные gaps.
* Failure capsules предотвращают неконтролируемое повторение прежних попыток.
* Новая стратегия не теряет прежние aim IDs и exact user sources.

Доказательства:
* Scale/retrieval/backup corpus и resource measurements.
* Manual vs automation outcomes с полным denominator.
* No-goal-left-behind diff и deferred register.

Восстановление: Универсальный infinite-context успех не заявляется. Corpus может расти; retrieval/transport/run имеют явные finite limits.

Цели: GOAL5-05, GOAL5-09, GOAL5-10, GOAL5-21, GOAL5-22, GOAL5-23, GOAL5-27, GOAL5-28. Решения: DEC5-11, DEC5-12, DEC5-14, DEC5-15, DEC5-21, DEC5-23.

Work packages: ACTION5-12, ACTION5-16, ACTION5-17, ACTION5-24, ACTION5-26, ACTION5-30, LAYA4-018, LAYA4-025, LAYA4-028, PAR3-023, PAR3-024.

## Параллельные направления разработки

| Направление | Можно готовить независимо | Общий ресурс при интеграции |
| --- | --- | --- |
| Repo chunker | Immutable fixtures, resolver и group planning | Один snapshot/store owner |
| Desktop | Packaging spike, keyboard UI и typed client | Существующие SQLite/Core операции |
| Source library | Extractors, taxonomy, retrieval corpus | Schema migrations и source heads |
| Selected tabs | Discovery, contract/fault corpus, mocked observations | Один writer UI/focus на устройстве |
| Update/capability | Provenance contract, staged fixtures и ABI cases | Один Git integrator и updater |
| Research/usefulness | Frozen data, replay cases и measurement corpus | Dataset provenance и admission budgets |

Независимые ветви пользуются pinned baseline и сохраняют source/evidence.
Сначала интегрировать общий schema/DTO contract, затем клиентов. Real PC execution
не становится параллельным от того, что документы подготовлены одновременно.

## Когда очередная итерация заканчивается

Заморозить aim/criteria/source revision и бюджет до запуска. Остановиться при
наблюдаемом успехе, отмене, exhausted budget, повторяющемся no-progress или
unknown external effect. Итог возвращает evidence либо named blocker с exact
next source/test request. Следующая итерация создаёт новую версию критериев;
неудачная старая попытка остаётся в истории.

Продолжение: `NEXT_IMPLEMENTATION_BRIEF_RU.txt`, `actions/DETAILED_ACTIONS_RU.md`,
`audit/UNDEFINED_AND_UNFINISHED_RU.md`, `goals/ALL_AIMS_RU.md`.

