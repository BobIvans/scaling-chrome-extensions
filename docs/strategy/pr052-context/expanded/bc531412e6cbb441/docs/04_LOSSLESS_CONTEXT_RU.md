# Полнота данных без обещания бесконечного prompt

## Разделить пять понятий

**Source universe** — что вообще доступно: выбранный Git commit, папка, экспорт аккаунта, список PR, конкретные attachments. **Raw completeness** — сохранены ли все байты объектов этого scope. **Extraction completeness** — получен ли текст/структура из каждого объекта. **Review coverage** — какие spans реально анализировались. **Prompt coverage** — какие spans отправлены в конкретный запрос модели.

Один общий `complete=true` для этих пяти понятий недопустим. Полный список имён без байтов — inventory, а не raw archive. Полный raw archive без исторических веток — не весь Git history. Текст PDF не равен исходному PDF; чат без доступных attachment bytes не становится полным мультимодальным архивом.

## Предлагаемые слои хранения

1. Append-only original blobs, content-addressed by SHA-256. Дедупликация содержимого не удаляет разные source paths/versions/relationships.
2. Manifest: origin, полный сырой path, версия, timestamps, bytes/hash, права, parser version, status и reason.
3. Derived projections: plain text, Markdown, transcript, symbols, embeddings, graph. Все перестраиваются из оригиналов.
4. Retrieval/context bundles: references на spans + запрос + причины включения + missing evidence + tokenizer/model budget.
5. Review and run receipts: кто/что/какую версию обработал, итог и ссылки на проверку.

Долговременное production-хранилище должно остаться у существующего SCE owner. CAS-format приложенного утилитарного архиватора — переносимый offline-export, не замена live SQLite.

## Нет произвольного лимита документов

Сканирование и индексация идут страницами; размер страницы ограничивает RAM/transaction time, а не всю библиотеку. При исчерпании диска или parser-budget задача получает PAUSED/ERROR с cursor и списком незавершённого, а не молча «успешна». UI виртуализирует список. Поиск использует pagination и отдельный счётчик total; top-k retrieval не подменяет полный архив.

Для AI создаются bounded части с byte spans и token accounting. Размер 300k/400k — не магическое обещание, он проверяется по конкретной модели, доступному контексту, системным/tool сообщениям и резерву ответа. В этом ZIP exporter считает BYTES, не токены. `token_count=null` намеренно честнее приблизительного числа, названного точным.

## Особые случаи

Git LFS: сохранить pointer и отметить внешний payload unresolved до отдельного разрешённого fetch. Submodules: gitlink OID не равен содержимому дочернего repo. Symlinks: сохранять ссылку, не следовать автоматически за границы источника. Dirty workspace: хранить отдельно от pinned Git snapshot, не смешивать незакоммиченные файлы с commit SHA. ZIP: проверять имена/размеры/вложенность; не распаковывать untrusted paths прямо в рабочую директорию. Binary/non-UTF8: сохранять raw; последующая extraction может оставаться `UNSUPPORTED`.

Скрытые файлы и нестандартные suffix обязательно попадают в inventory. Фильтры приватности не удаляются: локальный original tier и разрешённая к отправке sanitized view имеют разные manifests. Полный локальный архив может законно содержать твои секреты; отправлять их модели для полноты не нужно.

## Что реализовано в архиваторе

Файлы копируются потоково в CAS, byte hash проверяется, original path хранится также base64. В режиме Git читается закреплённое дерево, включая tracked dotfiles и raw blobs, без checkout/import. Режим folder сохраняет все обычные файлы выбранного root и metadata ссылок, но не является атомарным snapshot файловой системы.

UTF-8 export включает `ALL_TEXT.txt`, произвольное число `part-*.txt`, `chunks.jsonl` с точными payload offsets и `coverage.jsonl` для всего inventory. `verify-text` проверяет восстановление каждого text-source по SHA. Заголовки служат презентацией; для восстановления используется индекс, поэтому строки внутри документа не могут подменить границы файлов.

Повторный сбор заново перечисляет источник, переиспользуя verified CAS objects. Это **rescan-resume**, не cursor resume неизменного живого каталога. История старых objects остаётся, но старые manifests автоматически не версионируются: для сохранения отдельного snapshot используй новую output-папку. Production durable cursor ещё нужно интегрировать в SCE.
