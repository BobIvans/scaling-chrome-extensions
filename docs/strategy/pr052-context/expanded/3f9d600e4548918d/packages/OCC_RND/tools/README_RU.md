# Запускаемые инструменты: Python 3.10+, Git для Git-режима

Все команды запускаются вручную. Утилиты не вызывают OpenAI/Laya, не отправляют архив в сеть и не исполняют код из анализируемого repo. Исключение — явно запускаемый `windows/Acquire-Repos.ps1`: он скачивает публичные Git-репозитории и затем вызывает архиватор.

## Быстрый запуск на Windows

Открой терминал в распакованной папке ZIP. Используй свой установленный Python 3.10+ (`python`, либо замени на `py -3`).

```powershell
python -m unittest discover -s tests -v
python tools/desktop_archive.py
```

Desktop front-end предназначен для архивирования/проверки/экспорта, не для произвольного terminal control. Он не `.exe` и не production UI; Tk должен быть установлен вместе с Python. Voice/API/NVDA/Windows target tests пока NOT_RUN.

## Полный закреплённый Git snapshot

```powershell
python tools/archive_tool.py git `
  --source C:/Repos/scaling-chrome-extensions `
  --ref da6abf4c006e4e7d26fe45ef30fa9d07a356f396 `
  --out C:/OCCData/sce-20261003

python tools/archive_tool.py verify --archive C:/OCCData/sce-20261003

python tools/archive_tool.py text `
  --archive C:/OCCData/sce-20261003 `
  --out C:/OCCData/sce-text-20261003

python tools/archive_tool.py verify-text `
  --archive C:/OCCData/sce-20261003 `
  --out C:/OCCData/sce-text-20261003

python tools/archive_tool.py catalog `
  --archive C:/OCCData/sce-20261003 `
  --out C:/OCCData/sce-catalog-20261003
```

Путь output должен быть вне source. `text` требует новую/пустую output-папку, чтобы старые parts не перемешались с новым export. Размер фрагмента по умолчанию 262144 bytes, не число токенов. Нет лимита числа файлов/частей и нет отбрасывания конца большой строки.

Для скачивания обоих публичных repo без checkout и запуска их кода:

```powershell
./windows/Acquire-Repos.ps1 -RepoRoot C:/OCCRepos -ArchiveRoot C:/OCCData -Python python
```

Скрипт не сбрасывает существующие каталоги и не запускает пакетную установку. Старые SHA в примерах намеренно зафиксированы. Работа Git-прокси/интернета на твоём ПК не проверялась здесь.

## Обычная папка и dirty workspace

```powershell
python tools/archive_tool.py folder --source C:/MyDocuments --out C:/OCCData/documents-20261003
```

Собираются все обычные файлы, включая dotfiles и неизвестные расширения; ссылки не обходятся. **Не выбирать весь диск/домашний профиль автоматически.** Секреты могут попасть в локальные raw originals. Для dirty repo, где `.git` не нужен, лучше отдельная экспортируемая папка или Git-режим; folder-режим намеренно не скрывает `.git`.

## ChatGPT JSON export

```powershell
python tools/archive_tool.py chats --input C:/Exports/conversations.json --out C:/OCCData/chat-import-20261003
```

Сохраняет original.json и все mapping nodes, включая альтернативные ветки и metadata. Не скачивает отсутствующие вложения и не получает доступ к аккаунту. Parser JSON работает in-memory; для огромного JSON может потребоваться streaming parser. При ошибке оригинал остаётся, COMPLETE не выставляется. Не выдавать импорт одного export за гарантию всех прошлых разговоров аккаунта.

## Выходные файлы

`manifest.jsonl`: все обнаруженные paths, bytes/hash/type/status. `objects/`: raw CAS originals. `receipt.json`: scope/completeness. `ALL_TEXT.txt`: полная доступная UTF-8-проекция с source headers. `parts`: те же spans отдельно. `coverage.jsonl`: что попало в текст и что осталось raw. `symbols/commands/signals.jsonl`: статические candidates, не разрешение на выполнение.

## Recovery и известные ограничения

Каждый collect имеет exclusive `.writer.lock`. Обычное завершение/ошибка снимают его; после kill/power-loss сначала убедись, что writer действительно не работает, затем вручную архивируй/удали stale lock. `in_progress.json` запрещает считать предыдущий receipt новым успехом. Повтор collect повторяет enumeration и переиспользует hash-verified blobs. Для независимой истории manifests используй новую output-папку.

Folder scan не защищён от всех adversarial ancestor/reparse races и не является VSS/filesystem snapshot; нужен контролируемый источник, лучше immutable Git. CAS hashes — integrity, не authenticity/signature. Text verification загружает метаданные text-source в память; большого общего fixed cap нет, но физическая RAM конечна. Static AST parser читает один файл в память; unsupported/parse failure фиксируется, не означает «код проверен».

Процесс чтения Git в прототипе не имеет production job supervisor: зависший локальный Git требует ручного вмешательства. Нужны Windows Job Objects/timeout/cancellation/recovery в production, а не слепое расширение полномочий. Не запускать этот прототип как системный service с привилегиями администратора.
