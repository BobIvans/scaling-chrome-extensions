# OCC V7: восстановленный путь context → review → проверенный отчёт

Base: `336a970ca222d513150d0183226a59d2da4bec8f` (merged #36).
Оба ZIP являются источниками требований и reference code; их private history не входит в PR.

## Результат

Library использует существующие `content.sqlite3`, Git inventory, review ledger и очередь.
Путь: выбранный repo/file → goal/scope/acceptance → JSON request → V4/V5 TXT →
bound review import → зарегистрированный report template → локальный worker →
readback файла → `SUCCESS_VERIFIED` только для свойства `LOCAL_REPORT_BYTES`.

`context_handoff.py` адаптирует supplied V4/V5 stateless contracts, сохраняя их версии.
Native host заново строит overlay из выбранной immutable session. Goal, scope,
acceptance и source revisions входят в session identity. Другая session/overlay,
dirty dependency, смена HEAD/index или отзыв repo profile не принимаются как актуальный ответ.
V5 replies сохраняются полностью в `review_bound_claims` той же базы и как
`PROPOSAL_ONLY` в canonical ledger. Claimed tests/DONE не закрывают findings.

`review_report.py` проверяет current repo binding, pinned review и coverage до и
после записи; читает действительные bytes с диска. Пропущенный, частичный,
неверный файл или смена review не дают SUCCESS. Existing output не перезаписывается.
Повтор с тем же task key возвращает прежний job; иной key сверяет тот же файл.
После lost lease очередь остаётся `NEEDS_RECONCILIATION`. Reconcile только читает
файл после явной проверки остановки процесса и не создаёт/повторяет эффект.

Queue UI теперь показывает bounded outcome/reason и следующий шаг. Report UI
показывает filename/hash/bytes. Native Messaging по-прежнему не запускает worker.
Кнопка «Использовать текст как цель review» переносит редактируемый транскрипт в
общий goal, сохраняя отрицания и числа; изменение goal очищает прежнюю session
в UI. STOP очищает voice input. Автоматического ASR/dispatch здесь нет.

## Восстановление Execute PRs

Сохранившийся неопубликованный набор был подготовлен на `23d14fa...`, до #36.
Применять его целиком поверх #36 означало бы заменить новый Git ledger старым
scanner и продублировать review owners. Восстановлены оставшиеся функции через
текущих owners; старые логи не считаются проверкой этого PR.
Причина отсутствия финального ответа внутри ChatGPT Work не установлена:
репозиторий SCE не содержит исходников или серверных журналов ChatGPT Work.
Этот PR восстанавливает незавершённую реализацию и устраняет скрытый outcome
в собственной очереди SCE; исправление внутреннего UI ChatGPT не заявляется.

## Настройка локального отчёта

1. Установить обновлённые native host siblings через `agent-bridge/Install.ps1`
   в новую выбранную папку; durable capability включить существующим способом.
2. В Library выполнить scan, выбрать файлы и задать goal/scope/acceptance.
   Экспортировать request, затем собрать TXT V4/V5. Вернуть JSON review через
   template. Для V5 import выбрать именно соответствующую review session.
3. Из текущего status взять полные `session_id` и `review_id`. Оператор добавляет
   в собственный policy следующий профиль (пути/IDs заменить реальными):

```json
{
  "reports": {
    "selected-review": {
      "namespace": "code",
      "session_id": "REPLACE_WITH_CURRENT_64_HEX_SESSION_ID",
      "review_id": "REPLACE_WITH_CURRENT_64_HEX_REVIEW_ID",
      "output_root": "C:/OCCReports",
      "repository": "sce",
      "repository_profile": {
        "root": "C:/Projects/scaling-chrome-extensions",
        "namespace": "code",
        "source_roots": [".", "content-lab", "agent-bridge"],
        "exclusions": []
      }
    }
  }
}
```

Это дополнение к существующему policy, с `money_budget=0`, `max_parallel=1`.
Профиль repository должен в точности совпадать с выбранным native operator
profile. Output folder создать отдельно от checkout/store и их родителей.
Изменение policy invalidates ранее queued jobs по policy hash; сначала сверить
существующую очередь. Добавить в `templates` native profile:

```json
{"review-report": {"kind": "review_report", "report_profile": "selected-review"}}
```

4. В report UI указать `review-report` и собственный стабильный task key.
   Вызов `durable.review.report` принимает только configured template и совпадающую
   session. Ни review, ни browser request не выбирают output path или shell.
5. Запустить локально существующий worker и обновить report status:

```powershell
python content-lab/automation_core.py --store C:/OCCData/content work --policy C:/OCCData/policy.json
```

Для потерянного lease сначала убедиться, что старый worker остановлен, затем:

```powershell
python content-lab/automation_core.py --store C:/OCCData/content reconcile-report --policy C:/OCCData/policy.json --id JOB_ID --process-stopped
```

`BLOCKED` с partial/wrong output требует рассмотрения файла; автоматического
overwrite, repair, browser click или повторного исполнения нет.

## Приёмка и оставшиеся этапы

| Пакет | Состояние после этого PR | Что ещё требуется |
| --- | --- | --- |
| AGG-T01 | Git-backed repo context уже merged #36; owners сохранены | Installed Chrome receipt |
| AGG-T02 | Canonical UI + V4/V5 host-bound handoff/import реализованы | Installed UI/transport qualification |
| AGG-T03 | Worker/report/readback/replay/reconcile реализованы и проверены локально | Operator profile и запуск на пользовательском ПК |
| AGG-T04 | Не запущен | Selected Windows PID/controls, UIA handler и device test |
| AGG-T05 | Shared editable final-text input реализован частично | Реальный ASR, RU/EN p50/p95/RAM и command/dictation split |
| AGG-T06 | Не запущен | Установленный Laya API и frozen comparison cases |
| AGG-T07 | Report replay/reconcile реализованы; общий recipe registry не завершён | Сначала успешные device actions AGG-T04/T05 |
| AGG-T08 | Не запущен | Измеримый gap и одинаковый experiment budget |

36 V7 task cards — план задач, не 36 созданных PR. Их reconciliation находится
в `occ-v7-task-reconciliation.json`; partial/device work не объявляется DONE.
Текущая база использует Git-tracked sources и честный UTF-8 byte bound; полный
semantic audit, exact tokenizer, universal PC automation, ASR/Laya inference и
все волны не заявляются завершёнными.

V4/V5 handoff и report handler требуют COMPLETE selected context. В реальном
checkout probe JavaScript goal-normalizer корректно отклонён из-за
`JS_DEPENDENCIES_NOT_PARSED`; это не «успешный полный review». Отдельный smoke
на выбранном mapping-документе создал 6649-byte отчёт, проверил SHA/readback и
same-key replay. Receipt явно обозначает empty-findings transport fixture,
а не semantic audit: `runs/OCC_V7_REAL_CHECKOUT_2026-10-03.json`.

Windows Chrome/native-host installation, microphone inference, UIA effects и
API calls: **NOT_RUN** в этом окружении. Device fixtures не подменяют receipt.
Этот PR не меняет `studious-pancake`; конкретные предложения переноса —
`studious-to-sce.md`. Private archives не публикуются, merge не выполняется.
