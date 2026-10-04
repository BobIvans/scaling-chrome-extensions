# F-14: локальная библиотека и долговечная очередь

В `library.html` откройте «Задания локальному Codex» и подключите установленный
Native Host. Ниже доступен раздел «Локальная библиотека и долговечная очередь».
Он включается только для методов, объявленных opt-in host в `hello.version=1`.
Прежний host без `durableCommands` сохраняет работу старого Codex UI.

1. Укажите метку установленного профиля. Это только разделитель локальных ссылок,
   не удостоверение host и не новое разрешение. При смене профиля используйте
   отдельную метку. Профиль оператора по-прежнему определяет доступные данные.
2. Введите разрешённый namespace и запрос. Выберите до 10 найденных источников
   и получите current context с provenance и SHA-256. Изменённый или чужой ID
   отклоняет существующий SQLite owner. Текст источника отображается как данные.
3. Введите зарегистрированное действие и стабильный task key. UI передаёт только
   template/taskKey: ни пути, ни policy, ни payload, ни shell command.
4. После timeout/disconnect нажмите «Сверить тем же ключом». Намерение сохранено
   до отправки enqueue; повтор использует прежний ключ и прежний template.
5. После подключения нажмите «Обновить известные задания». UI хранит до 20 ссылок
   на jobs, но не является полным списком SQLite queue. Сохранённая ссылка сама
   не подтверждает текущее состояние: его возвращает `durable.get`.
6. «Запросить остановку» вызывает `durable.cancel`. RUNNING с cancel_requested
   остаётся RUNNING до подтверждения owner. Закрытие канала не удаляет durable jobs.

Данные, версии, jobs, lease и cancel сохраняют существующих владельцев
`content-lab/content_lab.py`, `automation_core.py` и `native_adapter.py`.
Ни один новый UI путь не запускает worker, AI API, voice, browser automation,
произвольную команду или blockchain sender. Прежний ручной Codex режим остаётся
отдельным действием со своей авторизацией.

Проверки F-14 включают scoped search/context через реальную SQLite, restart/replay,
persisted cancel, failed reference persistence, unknown enqueue, поздние replies,
selection/cancel races, opt-in fallback и подключение production attachAgent.
DOM-проверки используют Node harness. Installed Windows Chrome и реальный
nativeMessaging transport на устройстве требуют отдельной квалификации.

Portable `scripts/package_chrome_ready.py` включает новый module автоматически.
Исторический `renew_windows.ps1` скачивает старый pinned revision; он не является
инсталлятором этой ветки. Для F-14 берите пакет/checkout проверенного PR revision.

Технический результат записывается в `docs/automation/runs/`. Следующий шаг
F-15 (bounded scheduler) начинается после локальных тестов и exact-head CI F-14.
