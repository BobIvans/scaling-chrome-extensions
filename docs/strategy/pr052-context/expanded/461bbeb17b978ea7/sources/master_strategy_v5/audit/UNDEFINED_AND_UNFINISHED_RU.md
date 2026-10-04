# Что ещё не определено и не закончено

Редакция V5, 2026-10-04. Автор новых выводов и предложений: assistant. Аудит выполнен по актуальной V4: 164 продуктовые карточки, 130 задач, общая стратегия, Laya/repo-chunker, сценарий двух вкладок и implementation/STATUS.json. Исходные записи и их статусы сохраняются; этот документ добавляет решения и условия выпуска.

**Направление продукта уже описано. Главный оставшийся пробел — конкретные контракты, которые позволят собрать несколько будущих компонентов в одно проверяемое приложение.** Например, «desktop без Chrome» не определяет протокол процесса и формат установки; «backup» не определяет согласованный snapshot каталога; «Grok отправил» не определяет, каким наблюдением это доказать после перезапуска.

Здесь нет нового подтверждения реализации. В V4 зафиксированы локальный commit `5574ab768b39605d4631651a1e8f2451483344db` и 381 пройденный Linux regression test. Публикация, GitHub CI новой ревизии, установка на Windows, Grok UI, Laya и production updater имеют отдельные незавершённые статусы. Добавление карточек в ZIP их не меняет.

## Четыре разных вида незавершённости

| Вид | Что он означает | Пример | Что закрывает пробел |
|---|---|---|---|
| Пробел определения | Инвариант есть, конкретный контракт ещё не выбран | Каким каналом desktop обращается к существующему Core | Версионированное решение, API/schema, эксперимент и зафиксированный результат |
| Пробел реализации | Поведение уже описано, рабочий компонент ещё не построен | Одна кнопка проходит все страницы repo inventory | Код в существующем owner, проверка полноты, cancel/resume |
| Пробел квалификации | Компонент или прототип есть, целевой сценарий ещё не доказан | Установленная Windows-сборка; отправка в реальный выбранный чат | Квитанция на конкретной версии приложения, адаптера и устройства |
| Пробел источников | Нужного исторического источника либо текущих данных нет | Недоступный прежний чат; фактические capabilities установленной Laya | Полученный первоисточник с происхождением; до этого UNKNOWN |

Нельзя закрыть четвёртый вид дополнительным текстом. Нельзя закрыть третий локальным тестом другого устройства. Нельзя считать решение реализованным после выбора архитектуры.

## Реестр 24 решений

Все DEC5 записи имеют статус `PROPOSED_NOT_DECIDED`: это рабочие предложения, а не тайно принятые настройки пользователя. В `DECISION_REGISTER.json` у каждой записи есть варианты, рекомендуемый старт, причина, эксперимент, критерии принятия, роли и точные ссылки на существующие feature/task IDs.

| ID | Что нужно конкретизировать | Предлагаемый старт | Как проверить выбор |
|---|---|---|---|
| DEC5-01 | Desktop транспорт, упаковка и владелец процесса | Per-user локальное приложение; существующий Core за типизированным stdio IPC; один store | Установка и запуск с закрытым Chrome, повторное подключение клиента, блокировка второго writer |
| DEC5-02 | Формат области действий и доверия | Версионированные profiles по источникам, адресатам, действиям и расходам; исходники не изменяют profile | Корпус обычных разрешённых действий и попыток сменить цель через контекст |
| DEC5-03 | Долговременная идентичность вкладки | Provider + account/workspace + conversation identity; временный tab ID только handle | Рестарт, другой аккаунт, тот же tab ID с другим чатом, несколько похожих вкладок |
| DEC5-04 | Квалификация Grok UI адаптера | Версия DOM-контракта и corpus; наблюдение черновика, отправки и неоднозначности | Canary на выбранном пользователем чате; сбой до/после Send; дрейф controls |
| DEC5-05 | Envelope нескольких документов и лимиты транспорта | Provider-neutral manifest; лимиты берутся из квалификации; разные статусы передан/получен/прочитан | Различные бюджеты, частичная загрузка, повтор/пропуск части, reconstruction hashes |
| DEC5-06 | Поддерживаемый JS/TS resolver | Статический parser, версия config/alias/workspace resolver, явные unresolved edges | Эталон monorepo, aliases, ESM/CommonJS, generated files и ошибочный синтаксис |
| DEC5-07 | Разбиение связных групп | SCC + цель + тесты/контракты; oversize SCC делится с bridge manifest | Пакет со слишком крупным циклом, стабильность IDs, отсутствие потерянных межчастных связей |
| DEC5-08 | Область Git snapshot | Чистый закреплённый commit первым; dirty/history/LFS/submodule отдельными opt-in слоями | Смешанный Git fixture с binary, symlink, LFS pointer, submodule и локальными изменениями |
| DEC5-09 | Хранилище, объектная модель и disk pressure | Существующий SQLite для metadata + CAS оригиналов; write checkpoint и reservation | Сбой записи, повторный импорт, нехватка диска; alias/origin сохраняются |
| DEC5-10 | Совместимость схем и миграции | Versioned migrations; rehearsal на копии; jobs pinned к старой schema/profile | Падение миграции, downgrade, неизвестное поле импортера, восстановление snapshot |
| DEC5-11 | Полный backup | Согласованный SQLite snapshot + referenced objects + manifest; восстановление в новое место | Восстановление при записи/import и обнаружение отсутствующего blob |
| DEC5-12 | Retention и удаления | Originals по умолчанию сохраняются; производные имеют собственные сроки; tombstone propagation | Удаление source с несколькими aliases, derivatives, backup и уже переданными проекциями |
| DEC5-13 | Быстрый share без утечки всей библиотеки | Выбранная export projection, redaction ledger, source/range hashes; original остаётся локально | Числа/цитаты после redaction, вложенный секрет, получатель/пакет изменились перед Send |
| DEC5-14 | Поиск по архиву жизни | FTS/filters first; optional rerank; временные версии, противоречия и bounded ranges | Замороженный корпус реальных вопросов с проверяемыми source spans и hard negatives |
| DEC5-15 | Таксономия автометок | Независимые фасеты + происхождение/confidence; human overlay имеет приоритет | Повторная разметка, разные языки, ошибочная метка и её исправление человеком |
| DEC5-16 | Очередность импортеров и fidelity | Git/папки/явные exports первыми; schema per importer; originals отделены от извлечений | Правки и branches чата, цитаты, PDF/OCR failure, аудио с временными offsets |
| DEC5-17 | Голосовые critical slots | Push-to-talk; единый capture; typed intent; явное unknown для repo/chat/действия | RU/EN/code-switch, похожие repo, собственный TTS, потеря микрофона, исправление intent |
| DEC5-18 | Доступность и focus arbitration | Полный keyboard/text путь; локальный STOP вне ASR; уступка реальному вводу пользователя | Keyboard-only, screen reader, потеря focus, зависший worker и остановка |
| DEC5-19 | Каталог новых исполнимых возможностей | IDs, typed args/effects, resources, permissions, verifier; объявление не включает capability | Изменённые аргументы/права, missing dependency, stale installed build, invalidated skill |
| DEC5-20 | Release/updater trust и фактическая активация | Один разрешённый source channel, точный candidate SHA, staging и previous-version restore | Merge/squash/rebase, дрейф ветки, asset mismatch, миграция, interrupted activation и rollback |
| DEC5-21 | Scheduler, бюджеты и reboot | Существующий owner; resource-class admission, leases, no-burst catch-up | Sleep/reboot, backlog, исчерпание бюджета, offline provider, конфликт shared resources |
| DEC5-22 | Когда автономный цикл обязан завершиться | Замороженные критерии, конечные лимиты итераций/времени/расходов; next brief по blocker | Цикл без прогресса, повтор failed proposal, changing criteria, unknown внешнего эффекта |
| DEC5-23 | Как считать полезный успех | Раздельные stage outcomes, все started attempts в denominator, manual assistance явно | Ручной baseline и fault corpus; сравнение времени/качества на одинаковых задачах |
| DEC5-24 | Граница SCE ↔ web3 qualification | Read/replay/paper/shadow adapter к существующему bot owner; отдельные live permissions | Идентичность job и рынка, stale anchor, insufficient evidence, stop/recovery; AI claim не заменяет receipt |

## Что уже определено, но ещё требует реализации

Повторно обсуждать эти цели целиком не нужно. Можно двигаться по существующим критериям и связанным DEC5 решениям.

| Ветка | Уже определённый результат | Что осталось построить или подтвердить |
|---|---|---|
| Полный repo-chunker | Сохранить каждый выбранный entry, все ranges, provenance и omissions; возобновлять до конца | Auto-loop cursor, streaming крупных объектов, JS/TS graph, многотомный manifest, delta equivalence, упаковку/Windows qualification |
| Library | Единый owner, исходники отдельно от извлечений, версии и поиск без обязательной модели | Объектную модель, importer API, facets/timeline, privacy projection, backup/restore, миграции |
| Две вкладки | Документ в указанный чат; ответ и PR связаны с задачей; неизвестная отправка не повторяется | Реальную идентификацию вкладки, квалифицированные DOM controls, scoped send, extraction результата, authenticated version evidence |
| Проверенное обновление | Квалифицировать итоговый SHA, staged install, сравнить capabilities, миграция и откат | Release producer/format, installer/updater, independent device receipt, resume compatible jobs |
| Voice/Laya | Один intent/DAG для текста и голоса; Laya advisory, typed executor | ASR/capture, adapters установленной Laya, slot arbitration, доступный STOP, устройство пользователя |
| Параллельность | Разделять immutable research и конфликтующие effects; один owner на target | Resource identity, admission, lease/fencing, budget accounting, measured Windows pilot; текущий Core остаётся max_parallel=1 |
| Web3 R&D | Registry гипотез, replay, paper/shadow и evidence раздельно от live | Сверку текущего bot owner, typed campaign adapter, provider budgets/data lineage и независимую qualification конкретных стратегий |

Пока не подтверждены фактический merge новой ревизии, installed build, полная передача repo в Grok, получение им всех частей и результат пользовательской функции на Dell. «Всё в одном ZIP» означает единый доступный пакет продолжения, а не эти завершённые состояния.

## Что можно делать сейчас без новых вопросов пользователю

Рабочие значения DEC5 используются для prototypes, schemas и fixtures. Изменения, зависящие от ещё не выбранного адресата, аккаунта, данных, расходов или прав, остаются подготовленными до конкретизации этих полей. Это позволяет писать полезный код без предположения, что любой будущий текст уже разрешает любую операцию.

1. **Repo lane:** зафиксировать текущие scan/export contracts; построить auto-loop с cancel/resume и completeness fixture; отдельно подготовить static JS/TS resolver и SCC oversized policy. Не ждать Grok или ASR.
2. **Library lane:** описать CAS/alias/range schema и migration/backup corpus; сделать facets/human overlays и локальный поиск на выбранных exports. Не подключать всю личную историю автоматически.
3. **Tab lane:** определить TargetBinding DTO, immutable document envelope и adapter test corpus; реализовать bind/read/draft отдельно от Send. Реальная доставка — собственная квалификация позже.
4. **Update lane:** подготовить candidate/release/capability DTO, migration rehearsal и exact-SHA verifier; установка не зависит от присутствия AI в чате.
5. **Voice/accessibility lane:** typed intents, keyboard-only UI и независимый STOP; ASR меняет только capture/slots и получает тот же downstream contract.
6. **Qualification lane:** единая outcome schema, fixed corpus и baseline; web3 adapter читает собственные receipts существующего bot owner, а не запускает вторую торговую систему.

Параллельное проектирование этих lanes полезно. Выполнение не разделяет один mutable store, UI target или installed version между независимыми писателями. Production parallelism не включён этим документом.

## Порядок принятия решений

Сначала закрыть DEC5-01/02/08/09/10: они задают владельцев, идентичность входа и устойчивое состояние. DEC5-06/07 позволяют довести chunker; DEC5-14/15/16 развивают локальную библиотеку. DEC5-03/04/05 принимаются по реальному qualified browser target. DEC5-19/20 нужны до самообновления. DEC5-17/18 и DEC5-21/22/23 принимаются по корпусу и устройству. DEC5-24 зависит от независимой сверки текущего web3 owner.

Для принятия DEC5 записи нужны выбранный вариант, версия контракта, evidence/result эксперимента, известные ограничения и дата. Предложение не становится DECIDED само из-за появления нового ZIP. Локальный пример не становится DEVICE_QUALIFIED. Недоступные исторические идеи сохраняют missing-source status до получения источника.
