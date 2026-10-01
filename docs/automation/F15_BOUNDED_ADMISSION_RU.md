# F-15: первый срез — ограниченная постановка задач по времени

База: OCC PR #15, `7e1350c184b6376b5d03aa72e9270d2eefe58396`.
Это реализация части WAVE-03 / F-15 / CAP-078, а не завершение всего F-15.
Ссылки на CAND-0771–0780 и CAND-1771–1780 в functions-wave33.json являются
тематическими соответствиями, не автоматическим закрытием двадцати карточек.
33 работы волны и 2000 кандидатов нельзя складывать без дедупликации.

## Поведение

Один запуск `content-lab/schedule_tick.py` рассматривает только текущий UTC-слот
и может поставить максимум один ранее зарегистрированный `sync` template.
Слоты: не чаще одного часа, максимум 24, суммарное окно не более суток.
Пропущенные слоты не догоняются. Повтор того же слота использует один task_key.
Транзакционное создание/replay job выполняет существующий
`automation_core.enqueue`; jobs, job_events, Core.cancel и writer lease не копируются.

Единственная новая таблица `bounded_schedule_controls` хранит binding/stop-флаг
в той же SQLite через `automation_core.connection`. Нового DB/queue owner нет.
Binding охватывает определение расписания, operator profile и policy. Изменение
этих данных под тем же schedule_id блокируется. `enabled` можно временно выключить;
это не снимает ранее записанный stop. Для другого согласованного расписания
нужен новый schedule_id. Копирование store или новый ID являются новым запуском,
а не глобальной exactly-once гарантией.

Разрешены только существующие зарегистрированные sync templates. План не принимает
shell/argv, source paths, credentials, новый job kind, network/market permissions.
В этой версии patch/test jobs не запускаются по расписанию.

## Использование

Нужен полный checkout стека #15 плюс этот срез, Python и настроенный абсолютный
operator profile из Native Host #14. Относительные пути профиля отвергаются.
Пример `content-lab/schedule.example.json` выключен по умолчанию. Выбрать реальную
дату UTC, ID и зарегистрированный template должен оператор, не текст источника.

Предпросмотр (без записи control/queue; stop state при preview не проверяется):

```text
python content-lab/schedule_tick.py --schedule <schedule.json> --profile <absolute-profile.json>
```

Явно разрешённая постановка только текущего слота:

```text
python content-lab/schedule_tick.py --schedule <schedule.json> --profile <absolute-profile.json> --apply
```

Постоянная остановка будущих admissions для этого schedule_id:

```text
python content-lab/schedule_tick.py --schedule <schedule.json> --profile <absolute-profile.json> --stop
```

Этот CLI не регистрирует себя в Windows Task Scheduler, не содержит бесконечного
цикла и не запускает worker. Внешний локальный таймер и supervision остаются
следующим срезом. Авторизация и запуск существующего worker — отдельное действие.

## Точная семантика stop

Stop запрещает admissions, начинающиеся после записи stop-флага. Уже принятая
control-транзакцией постановка может завершиться после stop. Stop не отменяет
созданные jobs, не убивает процессы и не отзывает уже выполненные действия.
Для конкретного job используется существующий `durable.cancel` / `Core.cancel`.
Нельзя отображать STOPPED_FUTURE_ADMISSIONS как доказательство остановки worker.

## Проверка и границы

Добавлены 20 локальных contract tests (включая реальный SQLite для control,
но с fake enqueue) и 5 интеграционных тестов для полной canonical queue:
replay, конкурентная постановка, cancelled replay, stop и отсутствие catch-up.
В локальном контейнере исполнены 20 contract tests; прямой clone GitHub недоступен.
Интеграционные тесты и регрессии должны проверяться существующим exact-head
workflow на Linux/Windows; его test_*.py discovery уже включает новый файл.
Статус CI следует читать по опубликованному SHA, а не из этого документа.

Не доказаны и не запускаются: установленный Chrome/Native Messaging, голос,
Laya, API inference, суточный worker, market observation, paper profitability,
qualification, signer/sender или live execution. Расходы по умолчанию нулевые.
Источники и пользовательская история в PR не публикуются.
