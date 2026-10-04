# Что исправлять после первых 21 PR

**Нужен ремонт оставшегося foundation и интеграции #52; подтверждённой причины
откатывать уже слитые PR по их номеру нет.** Аудит выполнен 2026-10-04T18:41:29.973503+00:00; снимок SCE
main — `7253c40398905967ade0541717bcbfac25fec5b9`. Исходная V3 — strategy/R&D archive; сама она не является
receipt выполнения 21 PR. Нумерованный delivery roadmap найден в более позднем
`ROADMAP_PR_010_021_BIG_PACKAGES_RU_2026-10-04…zip` и девяти отдельных ранних ZIP.

Найдены и прочитаны 16 относящихся к roadmap ZIP: PR001…009, общий roadmap 010…021
и шесть объединённых implementation packages 010/011, 012/013, 014/015, 016/017,
018/019, 020/021. Все оригиналы плюс приложенная V3 сохранены побайтно.
`sources/SOURCE_INDEX.json` содержит имена, источник, member count, размер и SHA-256.

## Подтверждённые результаты

1. **Roadmap 010/011 остаются foundation gap.** Общий SourceAddress/read contract
   для существующих raw owners отсутствует в проверенном main. `context_library.py`
   адресует revision/source_key/start/end, `source_ledger.py` адресует version_id/ordinal,
   repo refs используют собственный dialect. Их наличие не равно одному source contract.
   Поиск отдельного `source_address.py` в main/истории не нашёл merged implementation.
   Часть library/search уже работает; её следует расширить, сохраняя raw bytes и IDs.
   `repo_js.resolve` явно возвращает COMMONJS_NOT_QUALIFIED, NON_RELATIVE_POLICY_NOT_QUALIFIED
   и TYPE_RESOLUTION_POLICY_REQUIRED, что подтверждает открытый resolver scope №011.

2. **PR #52 конфликтует с текущим main в девяти файлах.** Это воспроизведено
   `git merge-tree --write-tree` на exact main и head `3c6bf81e1345f91454ae87cccec2c3cd7c3d84a6`.
   Главная причина — обе стороны добавляют собственные новые branches/modules
   в общие Core/Native/Desktop owners. Выбор целиком ours/theirs потеряет функции.
   Рецепт для каждого файла находится в `03_PR52_CONFLICT_REPAIR_RU.md`.
   Старый зелёный CI #52 проверяет его собственный head, а не ещё не созданный
   интегрированный результат. Companion Studious #565 также остаётся unmerged.

3. **Текущая навигация содержит более старые состояния.** Верх root handoff говорит,
   что #51 merged, ниже таблица/next-stage ещё направляют к незавершённому #51;
   старый общий table обозначает #49 open. Точный code checkpoint — общий SourceAddress
   и оставшийся lifecycle, а не повторное создание слитого ledger. Dated snapshots
   и original plans менять задним числом не нужно: обновляется current index.

4. **Merge опережал full dependency acceptance.** №018/019 слиты до №014/015 и №016/017;
   №012/013 начали поставлять до завершения №010/011. Это допускает независимые
   implementation slices; исходные документы именно так их описывают и сохраняют OPEN
   критерии. Для полного продукта сначала нужны contracts 010/011 → 012/013, затем
   совместимая downstream интеграция. Реальный найденный merge blocker сейчас — #52.

5. **Device/product acceptance остаётся отдельной работой.** Source ledgers сохраняют
   322 criteria для 014/015, 220 для 016/017, 147 для 018/019 и 1133 broad criteria
   в 020/021. Наборы пересекаются; их нельзя складывать как уникальные требования или
   считать закрытыми по числу passed tests. Реальная Dell Windows 11 установка,
   microphone/hotkey/tab/STOP, полный import corpus и полезность/стоимость не подтверждены
   этим аудитом. Эти требования сохранены в FIX-005/006.

## Проверки именно текущего main

490 Content Lab tests — PASS. Desktop: 45 discovered, 42 passed, 3 skipped из-за
недоступного display в этой среде. Native bridge: 47 PASS, qualification adapter:
8 PASS, extension: 121 PASS. Итого 708 passed, 3 skipped, 0 failed.
Обе проверки source integrity и Desktop owned-file verification прошли.
Полные команды, logs и scope находятся в `evidence/raw/tests_*`.
Это Linux/local evidence; актуальные GitHub CI observations сохранены отдельно.
Ни source-preservation, ни unit tests не подменяют физический Windows pilot.
На последней GitHub сверке main SHA не изменился; его общий CI run 37224308831
ещё IN_PROGRESS. Два context-platform jobs и core Ubuntu уже SUCCESS, core Windows
на сохранённом job observation ещё IN_PROGRESS. Текущий main не объявляется полностью
green по CI до завершения run. PR52 exact old-head run SUCCESS, но PR52 всё ещё
open/draft/mergeable=false. Итоговый snapshot — `evidence/raw/final_state.json`.

## Что содержится в пакете исправлений

`MASTER_CONTEXT.md` и `CODEX_START_HERE.md` дают прямую передачу Codex.
`plan/FIX_PLAN.json` описывает шесть work items с owners, зависимостями и acceptance.
Сначала обновить evidence и интегрировать #52; foundation 010/011 можно готовить
независимо. Полное downstream закрытие ждёт общие contracts и пригодные receipts.
Это не обещание шести новых GitHub PR: продолжать существующий #52 и делать
coherent foundation PR, сохраняя все source tasks и criteria.

Огромный master ZIP 387402728 bytes был источником V5 extracts, но полностью
не копировался в первоначальный numbered roadmap и в этом аудите не прочитан.
Приложенная V3 сохранена целиком: 539 members и все её идеи остаются доступными;
587 карточек V3 и 164 feature cards V5 — разные catalog scopes, а не одинаковое
число implemented функций. Полное account/chat-history coverage не заявлено.

В этом запросе не менялись remote branches, PR states и application code.
ZIP — проверенный audit и implementation handoff; исправления ещё предстоит выполнить.
