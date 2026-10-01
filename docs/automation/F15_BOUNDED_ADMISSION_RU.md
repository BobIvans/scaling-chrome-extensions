# F-15: ограниченная постановка задач и supervisor

База: OCC PR #15, `7e1350c184b6376b5d03aa72e9270d2eefe58396`.
PR сначала добавил admission текущего слота. Следующий commit добавляет bounded
supervisor, lease и аварийную reconciliation. Это не установка фоновой службы.
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

`schedule_tick.py` не регистрирует себя в Windows Task Scheduler, не содержит
цикла и не запускает worker. Авторизация и запуск существующего worker —
отдельное действие.

## Bounded supervisor

`content-lab/schedule_supervisor.py` может повторно вызывать admission в одном
локальном процессе. Его конфигурация ограничивает `poll_seconds`, `max_seconds`
(не более суток), `max_ticks` и продолжительность lease. Пример
`content-lab/supervisor.example.json` выключен по умолчанию.

Предпросмотр проверяет файлы и текущий слот, но не создаёт lease/job:

```text
python content-lab/schedule_supervisor.py --supervisor <supervisor.json> --schedule <schedule.json> --profile <absolute-profile.json>
```

Ограниченный запуск требует одновременно `enabled: true` и явный `--apply`:

```text
python content-lab/schedule_supervisor.py --supervisor <supervisor.json> --schedule <schedule.json> --profile <absolute-profile.json> --apply
```

В той же SQLite создаётся только control lease для `schedule_id`. Jobs и события
по-прежнему создаёт `automation_core.enqueue`. Второй supervisor блокируется.
Чистое завершение по limit/STOP/interrupt освобождает lease. Interrupt прекращает
процесс, но не является постоянным STOP расписания и не отменяет jobs.

Если процесс или tick завершился с неизвестным исходом, lease остаётся. После
истечения lease новый supervisor отвечает `SUPERVISOR_NEEDS_RECONCILIATION`.
Оператор сначала проверяет, что прежний процесс действительно остановлен, затем
явно очищает только истёкший lease:

```text
python content-lab/schedule_supervisor.py --supervisor <supervisor.json> --schedule <schedule.json> --profile <absolute-profile.json> --reconcile-stopped
```

Активный lease удалить этой командой нельзя. Если enqueue успел закоммититься,
следующий tick повторит тот же slot task_key и получит существующий job.
Supervisor не принимает argv/command, не выполняет payload и не запускает worker.

## Точная семантика stop

Stop запрещает admissions, начинающиеся после записи stop-флага. Уже принятая
control-транзакцией постановка может завершиться после stop. Stop не отменяет
созданные jobs, не убивает процессы и не отзывает уже выполненные действия.
Для конкретного job используется существующий `durable.cancel` / `Core.cancel`.
Нельзя отображать STOPPED_FUTURE_ADMISSIONS как доказательство остановки worker.

## Проверка и границы

Первый commit добавил 20 contract tests (реальный SQLite для control,
но fake enqueue) и 5 интеграционных тестов для canonical queue:
replay, конкурентная постановка, cancelled replay, stop и отсутствие catch-up.
Supervisor добавляет 11 проверок: строгие bounds, preview/disabled, clean limits,
interrupt, single lease, expired reconciliation, unknown effect, lost lease,
STOP и два тика через реальную canonical queue. Полный test discovery и exact-head
workflow Linux/Windows проверяются на каждом опубликованном SHA.

Не доказаны и не запускаются: установленный Chrome/Native Messaging, голос,
Laya, API inference, установленный 24/7 service, market observation, paper profitability,
qualification, signer/sender или live execution. Расходы по умолчанию нулевые.
Источники и пользовательская история в PR не публикуются.
