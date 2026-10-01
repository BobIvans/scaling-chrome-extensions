# Локальные задания Codex — OCC 0.5

Расширение передаёт только выбранный общий TXT и явно введённое задание локальному Codex CLI. Codex использует свою существующую авторизацию ChatGPT; ключи и cookies в расширение не копируются. Это расходует лимиты Codex и отправляет выбранный текст провайдеру AI. Supabase не используется.

## Установка Windows

1. Сначала экспортируйте важный старый session-снимок. Обновите существующее распакованное расширение до 0.5.0, сохранив путь установки.
2. На chrome://extensions/ включите режим разработчика и скопируйте ID One Click Context (32 буквы a–p).
3. Проверьте `node --version` и `codex login status`. Нужен установленный Node.js и Codex CLI с поддержкой `exec --ignore-user-config`. Если вход не выполнен, используйте официальный `codex login`.
4. Соберите Chrome-ready ZIP. Сохраните напечатанные `TREE_SHA256`, `ZIP_SHA256`
   и version; распакуйте именно этот ZIP. `TREE_SHA256` покрывает точные пути и
   байты установленного дерева, а ZIP hash отдельно идентифицирует архив.
5. Просмотрите Install.ps1, host.mjs и NativeHost.cs. Подготовка без регистрации:
   `./Install.ps1 -ExtensionId ВАШ_ID -ExtensionVersion 0.13.0 -PackageTreeSha256 TREE_SHA256 -Destination C:\OCCNativePrepared`.
6. Для установки сразу с регистрацией используйте новый незанятый каталог и те же
   exact ID/version/hash: `./Install.ps1 -ExtensionId ВАШ_ID -ExtensionVersion 0.13.0 -PackageTreeSha256 TREE_SHA256 -Register`. Скрипт компилирует launcher, записывает только HKCU\Software\Google\Chrome\NativeMessagingHosts\com.one_click_context.codex и разрешает единственный указанный ID. Существующая установка не перезаписывается.
7. Откройте библиотеку → «Квалификация установленного transport» и нажмите одну
   кнопку. PASS требует два разных host session ID и заканчивается revoke
   `nativeMessaging`; сохраните receipt. Для обычного подключения разрешение
   придётся выдать снова.
8. Откройте «Задания локальному Codex» → «Подключить локальный агент». Само подключение не отправляет документы в AI.
9. Выберите документы, введите задание, нажмите запуск и подтвердите передачу. После COMPLETE нажмите «Добавить ответ в библиотеку», проверьте ответ и скачайте TXT.

## Границы текущей реализации

- До 5 заданий в одном подключении, последовательно; 10 минут на задание; до 2 200 000 байт входа/ответа. Целостность проверяется SHA-256. Транспорт — локальные каналы Chrome Native Messaging, без HTTP-сервера.
- «Анализ»: sandbox read-only. «Создание»: sandbox workspace-write во временном каталоге задания. Используется официальный sandbox Codex; инструкция не является дополнительной гарантией изоляции чтения всей файловой системы. Пользовательская конфигурация инструментов не подмешивается.
- В библиотеку возвращается финальный TXT. Кнопка «Файлы результата» возвращает дополнительные файлы отдельно, с SHA-256: до 20 файлов / 2 200 000 байт суммарно, без перехода по ссылкам за пределы папки задания. Проверена на синтетических файлах. В текущей установке реальный тест создания файла прошёл после изоляции служебного окружения дочернего Codex и явного включения штатной Windows-песочницы. Анализ и создание доступны. Новые установки остаются с allowBuild=false по умолчанию до отдельной проверки; включать этот флаг следует только после успешного smoke в разрешённой среде.
- Удаление задания удаляет его временные файлы. Закрытие библиотеки/отключение останавливает канал. При аварийном завершении могут остаться файлы в папке jobs: проверьте её вручную. Нет обещания круглосуточной работы.
- Это не зеркало Chrome: нет доступа к cookies, токенам, медиа или всем вкладкам; нет debugger/all_urls. Автопереходы по вложениям, торговля и отправка сообщений не реализованы.
- Qualification проверяет package tree, exact host binding, два подключения и
  revoke; она не доказывает происхождение ZIP без отдельной сверки напечатанного
  `ZIP_SHA256` и не выдаёт browser-action authority.
- Возвращённый ответ — результат AI, а не исходный документ. Он требует проверки; полнота PARTIAL не повышается.

## Удаление интеграции

Закройте вкладки библиотеки, отзовите optional-разрешение расширения и удалите только ключ `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.one_click_context.codex`, предварительно проверив, что его значение указывает на вашу установку OCC. Затем удалите выбранный при установке каталог. Авторизация Codex и остальные приложения этим не удаляются.

## Проверки

`node --test agent-bridge/*.test.mjs` — production transport/job functions, подменённый процесс AI; durable tests используют настоящий Python subprocess и SQLite.

`node agent-bridge/smoke.mjs ../native-host-smoke --live` — синтетический тест подготовленного exe с тестовым ID; реальный Codex, расходует один небольшой запрос. Это не доказательство подключения Chrome extension API. Тестовый host не регистрируется.

Изоляция запуска: удаляются только известные переменные родительской задачи/IPC и API-key overrides. CODEX_HOME и неизвестные managed-настройки сохраняются. execpolicy rules не отключаются. Windows использует windows.sandbox="elevated", процесс задания — read-only или workspace-write; режима bypass нет.

## Функция 13: доступ к долговечной библиотеке и очереди

Этот opt-in относится к `content-lab/automation_core.py`. Прежние `begin/run/list`
остаются временными Codex jobs. Новые `durable.*` не вызывают Codex, модель, сеть
или worker; отключение host не отменяет и не удаляет долговечную очередь.
Chrome UI ещё не вызывает эти команды: следующая функция 14 — подключение UI.

После review локальных профилей добавьте в `host-config.json`:

```json
{
  "durableCore": {
    "enabled": true,
    "pythonPath": "C:/Python313/python.exe",
    "adapterPath": "C:/OCCNativePrepared/content-lab/native_adapter.py",
    "profilePath": "C:/OCCData/native-profile.json"
  }
}
```

Это фрагмент существующего config: сохраните его `extensionId`, `nodePath`,
`codexPath`, `dataRoot` и проверенный `allowBuild`. Installer копирует Python
adapter с зависимостями внутрь выбранной установки; durableCore выключен по
умолчанию. Python 3.11+ / SQLite FTS5 устанавливает оператор. Для запуска из repo
`adapterPath` указывает на его `content-lab/native_adapter.py`.

`content-lab/native-profile.example.json` задаёт абсолютные store/policy paths,
список разрешённых namespaces и фиксированные job templates. Сам policy остаётся
операторским; `work --policy ...` вызывает отдельный операторский scheduler.
Изменённый policy или удалённый template не разрешают доступ к старому job.
Не регистрируйте шаблоны непроверенных исполняемых патчей/test commands.

| Native запрос | Ответ | Ограничение |
|---|---|---|
| `durable.search`, namespace, query, optional limit | `durable.items` | Разрешённый namespace; limit 1–20, query до 1000 символов |
| `durable.context`, namespace, ids, optional maxBytes | `durable.context` | 1–10 current IDs; текст до 48 000 UTF-8 bytes |
| `durable.enqueue`, template, taskKey | `durable.job` | Только зарегистрированный template; тот же ключ возвращает тот же job |
| `durable.get`, jobId | `durable.job` | Job совпадает с policy hash и одним template; без paths/logs/lease tokens |
| `durable.cancel`, jobId | `durable.job` | Та же scope; отмена сохраняется в SQLite |
| `durable.record`, mutation | `durable.record` | `occ.library-record.v1`, разрешённый namespace, CAS revision; text до 8 000 UTF-8 bytes |

Ответ помечен `schema: occ.native-durable-result.v1` и исходной `operation`.
Пример: `{"type":"durable.enqueue","template":"sync-exports","taskKey":"exports-20261001T1000"}`.
Request не принимает root/store/policy/argv/patch/worker overrides или новые
permissions. Дочерний процесс Python запускается по зарегистрированному
абсолютному пути с `-I -X utf8`, `shell:false`, без AI keys/HF tokens/PYTHONPATH
и без desktop IPC. Полный request — до 16 000 bytes; stdout+stderr — до 192 000
bytes, timeout — 10 секунд; stderr не возвращается в Chrome. При disconnect
transport child завершается, SQLite остаётся владельцем подтверждённых данных.

**Timeout/disconnect означает неизвестный исход операции.** Enqueue мог уже
сохраниться до обрыва ответа: повторите тот же template и **тот же taskKey**, затем
проверьте get. Новый ключ может создать второе задание. Cancel можно повторить;
RUNNING/NEEDS_RECONCILIATION остаётся таким до подтверждения остановки worker
согласно core policy. Adapter не утверждает, что сторонний worker уже остановлен.
