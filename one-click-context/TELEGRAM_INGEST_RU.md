# Локальный импорт Telegram и необязательная транскрипция

Это добавление к существующему OCC Agent Relay. База — ветка
`renewal/occ-1.0-agent-relay`, SHA `d654050458f3118e5b916ff837243e6055865fd7`.
Её PR #7 остаётся отдельной незавершённой квалификацией Chrome/Hermes.

## Первый запуск без AI и сети

Из корня репозитория, Python 3.11+:

```sh
python one-click-context/tools/telegram_export_ingest.py --export /path/to/export/result.json --out /path/to/new-output --authorized-export
```

Используйте только собственные материалы или экспорт, обработка которого разрешена.
Флаг подтверждает выбор пользователя, но сам не создаёт прав на чужие сообщения.
Поддерживаются экспорт отдельного чата и объект `chats.list` из экспорта аккаунта.

Выход: `records.json`, `transcript.md`, завершающий `READY.json` с SHA-256 файлов.
Откройте `transcript.md` существующим file picker OCC и сохраните обычным способом.
`records.json` — формат адаптера, не замена формата основной базы библиотеки.

Сохраняются chat/message IDs, текст rich-text entities, даты, автор, название чата,
reply/forward provenance, хеш сообщения и версия производной записи. Точные повторы
в одном результате объединяются; изменённые записи сохраняются раздельно.
Оригинальный экспорт нужно оставить у себя: нормализация не заменяет исходные байты.

Существующая папка результата не перезаписывается. При повторном запуске в неё
возвращается BLOCKED/exit 2. Это защита от перезаписи, не полноценная очередь с
exactly-once исполнением. READY.json записывается последним; частичный результат
без корректного READY нельзя считать завершённым.

## Голосовые записи

По умолчанию голосовые отмечаются NOT_REQUESTED: модель не загружается.
Для ASR заранее установите проверенную версию faster-whisper и локальный
CTranslate2 checkpoint с model.bin, config.json и tokenizer.json. После подготовки:

```sh
python one-click-context/tools/telegram_export_ingest.py --export /path/to/export/result.json --out /path/to/new-asr-output --authorized-export --local-model /path/to/reviewed-checkpoint --language ru
```

Адаптер использует CPU/int8, два потока, один worker, VAD и local_files_only=True.
Он не скачивает модель по имени. Идентификатор результата включает версию SDK,
хеш трёх файлов checkpoint и язык. Сегменты содержат start/end/text; текст ASR всегда
помечен TRANSCRIBED_UNVERIFIED. Отдельно сохраняется SHA-256 исходного аудио.

Официальные источники:
- https://github.com/SYSTRAN/faster-whisper
- https://telegram.org/blog/export-and-more
- https://telegram.org/tos/content-licensing

## Ограничения

Это offline-адаптер к доверенной неизменяемой папке экспорта, не сервер для
враждебных загрузок. Ограничены размер, число сообщений и сегментов. URL, абсолютные
пути, выход через `..` и media symlinks отклоняются. Не гарантируется безопасность
против параллельного враждебного изменения всей локальной файловой системы.
Нет жёсткого дедлайна ASR: для unattended worker нужен отдельный лимит времени/ресурсов.

Метка PRIVATE_PROJECTS не классифицирует медицинские/иные чувствительные данные.
Выберите допустимые источники до запуска и храните результат приватно. Текст
сообщений — UNTRUSTED_DATA, а не разрешение выполнять найденные команды.

Не реализованы: выгрузка Telegram аккаунта по API, экспорт скрытой истории ChatGPT,
обработка любых вложений, real-time подписка, UI-кнопка автозапуска, task extractor,
публикация, кодогенерация, торговля и 24/7 deployment.

## Проверки

```sh
python -m unittest discover -s one-click-context/tests -p test_telegram_export_ingest.py -v
```

В контейнере 18 synthetic/offline тестов прошли. Проверены provenance, версии,
коллизии chat IDs, пути, форма сегментов, границы записи и локальный вызов SDK через
тестовую подстановку. Реальный acoustic inference и качество русской речи НЕ
проверялись: аудио и модель не запускались. Полный Chrome/Hermes smoke не выполнялся.

В существующий workflow OCC добавлен только этот offline test step. Перед merge
нужны exact-head CI/review и отдельный тест на разрешённой аудиозаписи пользователя.
