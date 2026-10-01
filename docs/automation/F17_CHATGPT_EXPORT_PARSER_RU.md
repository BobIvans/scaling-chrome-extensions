# F-17 — parser выбранного ChatGPT export

## Подтверждённый gap

До F-17 обычный `.json` импортировался одним текстовым blob. Изменение одного
сообщения меняло identity всего файла; стабильные conversation/message IDs,
message-level revisions и current/missing heads отсутствовали.

## Реализация

`content-lab/content_lab.py ingest-chatgpt` читает только выбранный локальный JSON
и записывает результаты в существующие `items/content_fts`, `sync_heads` и
`sync_versions` того же `content.sqlite3`:

- stable scope `chatgpt:<namespace>` и source key
  `chatgpt/<conversation_id>/<message_id>`;
- immutable revision identity по conversation/message/node/parent, role,
  content type и exact text;
- reorder export не создаёт версий, edit двигает один head, удаление помечает
  message/conversation missing, история остаётся;
- актуальный title/current node хранится по стабильному conversation ID;
- duplicate JSON keys/IDs, non-finite timestamps, symlink, mutation during read
  и превышение budgets блокируют import до data transaction;
- text остаётся данными без action authority; attachments/pointers не читаются
  и не загружаются;
- публичный CLI receipt содержит counts, byte totals и export hash, но не title,
  message IDs или текст.

## Проверка и границы

Synthetic fixtures покрывают повторный import без duplicates, JSON reorder,
одиночный edit с сохранением history, removed message/conversation, title update,
branch parent metadata, attachment skip, instruction-like text, invalid IDs/JSON,
CLI privacy и symlink rejection. Реальный пользовательский export не читался и
не публиковался. Parser не получает cookies, не открывает ChatGPT, не создаёт
очередь/worker и не вызывает модель/API.
