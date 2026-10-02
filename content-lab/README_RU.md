# OCC Content Lab: бесплатный локальный первый шаг

Долговечная синхронизация и jobs поверх этого же SQLite: [AUTOMATION_RU.md](AUTOMATION_RU.md).

Локальный intake, Laya/voice proposals и сохраняемые review-сессии:
[context-review-ledger.md](../docs/automation/context-review-ledger.md).

Этот Python-прототип дополняет экспорт OCC. Он импортирует выбранные UTF-8
TXT/код/JSON, статический HTML и SRT/VTT, записывает источник и хеши, устраняет
повторный импорт и делает поиск SQLite FTS5. Скрипты захваченной страницы не
исполняются. Импортированный текст имеет статус данных, а не разрешения действовать.
Работа расширения и существующего agent relay не изменяется.

## Запуск без API и дополнительных Python-пакетов

Python 3.11+ со SQLite FTS5:

```bash
python content-lab/content_lab.py ingest --file capture.txt --store ./local-content --source-url https://example.test/source
python content-lab/content_lab.py ingest --file subtitles.srt --store ./local-content
python content-lab/content_lab.py search --store ./local-content --query "qualification OR блокер"
python -m unittest discover -s content-lab -p 'test_*.py' -v
```

В `local-content/items/<id>.json` сохраняются текст, input/text SHA-256, источник,
время, extractor и ограничения полноты. SQLite хранит те же receipts и индекс.
Повторная запись с тем же содержимым, источником и конфигурацией не дублирует
FTS. Изменение ASR-модели или настроек создаёт другую identity.
Предел текста — 2 200 000 байт; молчаливого усечения нет.

## Выбранный ChatGPT export

F-17 разбирает только явно выбранный локальный `conversations.json`, без cookies,
аккаунта, browser automation или сетевого доступа:

```bash
python content-lab/content_lab.py ingest-chatgpt \
  --file /selected/conversations.json --store ./local-content --namespace personal
python content-lab/automation_core.py --store ./local-content \
  search --namespace chatgpt:personal --query "qualification blocker"
```

Каждое текстовое сообщение получает стабильные `conversation_id`, `message_id`
и `source_key`; identity версии зависит от текста, роли и позиции в mapping, но
не от порядка JSON или времени повторного импорта. Неизменный второй импорт даёт
`new_versions=0`. Изменённое сообщение создаёт новую immutable version и двигает
только его current head; удалённые сообщения/разговоры становятся missing, история
не удаляется. Текущий scoped search использует существующие `sync_heads`, а
`items/content_fts` остаются единственным владельцем текста и индекса.

Лимиты: export до 64 MiB, до 1000 разговоров/100 000 текстовых сообщений,
100 000 non-text parts и 64 MiB извлечённого текста суммарно; одно сообщение —
до 2 200 000 байт. Image/audio/file asset pointers не загружаются: metadata-only
inventory в том же `content.sqlite3` различает `PRESENT`, `MISSING` и
`UNSUPPORTED`, хранит версии метаданных и текущий/missing head. Content bytes
не считаются присутствующими; права остаются `UNVERIFIED`, retrieval запрещён.
CLI receipt содержит только counts/hashes, не текст чатов или asset pointers.
В репозитории тестируются только синтетические fixtures.

## Необязательная транскрипция CPU INT8

Создай отдельное окружение и установи faster-whisper из его официального
[репозитория](https://github.com/SYSTRAN/faster-whisper). После проверки получившейся
версии сохрани полный lock. Один раз явно скачай CTranslate2-модель
[SYSTRAN/faster-whisper-small](https://huggingface.co/SYSTRAN/faster-whisper-small)
в отдельную папку; для русского нужна multilingual-модель, не `small.en`.

```bash
python content-lab/content_lab.py transcribe --file ru_sample.wav --model-dir ./content-lab/models/whisper-small --store ./local-content --language ru --threads 4
```

Модель загружается из локальной папки: `model.bin`, `config.json`, `tokenizer.json`,
`preprocessor_config.json` обязательны. `local_files_only=True`, CPU INT8, один
worker, beam=1. Автоматической загрузки модели нет; наличие tokenizer предотвращает
удалённый fallback. Сегменты содержат секунды начала/конца; результат остаётся
BEST_EFFORT. Receipt включает хеши модели, параметры, elapsed time, audio duration
и real-time factor. Эти метрики появятся только после реального inference.

В этом PR ASR проверен fake backend-тестом. Реальной записи и проверки качества
на Dell ещё нет. Лимит аудиофайла — 64 MiB; синхронный ASR не имеет hard deadline
или memory sandbox. Начни с записи 60–120 секунд и запускай под внешним supervisor.
Для одиночной записи VAD и diarization пока не включены.

## Следующие эксперименты

1. **ASR-CPU:** те же 3–5 минут RU/LV/EN для faster-whisper small/turbo,
   [Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) и
   [Parakeet v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).
   Сравнить WER/CER по ручному эталону, задержку, пиковую RAM и сохранность имён/чисел.
   Это список кандидатов, не доказанный SOTA-рейтинг и не результат нашего замера.
2. **HTML:** [Trafilatura](https://trafilatura.readthedocs.io/) вместо базового parser
   на 20 разрешённых страницах; сверить полезный текст и метаданные. Динамический
   чат сначала экспортируется OCC; extractor не получает скрытую историю.
3. **Документы:** [Docling](https://github.com/docling-project/docling) для PDF/OCR,
   таблиц и офисных файлов; проверить порядок чтения и exact values на 10 примерах.
4. **Retrieval:** сравнить текущий FTS с
   [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
   на 20 вопросах RU/EN к выбранному corpus, измерить recall@5 и RAM.
5. **Сбор:** явный адаптер разрешённых RSS/URL и
   [yt-dlp](https://github.com/yt-dlp/yt-dlp) для доступных субтитров/своего медиа.
   Сейчас CLI принимает только локальные файлы. Он не сканирует автоматически
   чаты, не передаёт cookies, не подключается к Muse и не обходит ограничения сайта.

Hugging Face Spaces подходит для публичной демонстрации на синтетических данных.
Бесплатное оборудование засыпает при простое; это не постоянно работающий daemon.
Muse/OpenAI/Laya могут получать отдельно выбранные receipts через будущий адаптер.
Здесь нет общего произвольного shell-tool и нет записи в web3 runtime.
