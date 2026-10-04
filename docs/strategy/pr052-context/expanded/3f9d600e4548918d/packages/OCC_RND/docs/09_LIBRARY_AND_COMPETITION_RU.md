# Библиотека: что заимствовать и чем отличаться

Цель пользователя — Drive-подобная организация оригиналов и Notion-подобный доступ к смыслу плюс локальное выполнение исследовательских задач. Не надо переписывать синхронизацию, rich-text editor, terminal, browser engine и agent framework одновременно.

## Три стратегии

**A. Собственное evidence-ядро, существующий editor.** Изучить AFFiNE/AppFlowy как редакторные/workspace references и возможные интеграции. [S27,S28] Решение об embedding/fork требует отдельного licence/maintenance review. Преимущество — меньше редакторной работы; риск — зависимость от чужой модели данных и upgrades.

**B. Собственная простая библиотека.** File tree, preview Markdown/text, tags, FTS, provenance, jobs и VS Code handoff. Предлагаемый старт для текущей цели. Сначала достигаем «найти исходник→проверить код→получить receipt», а не полный визуальный конкурент Notion.

**C. Headless library API + разные клиенты.** Desktop для личного ПК, optional browser capture и CLI для серверного runner используют одного owner. Это сильнее разделяет data/automation/UI, но дороже в первоначальном versioning/IPC.

## Предлагаемое отличие продукта

Не просто «все файлы с чатиком», а **evidence-to-action library**: у любого вывода есть исходные байты и версия; у любой задачи — полномочия и проверка; у любой автоматизации — воспроизводимый trace; у любой заявленной готовности — результат реального теста; у каждого пропуска — причина и next data request.

Пример: пользователь выделяет три старых обсуждения и repo snapshot. Система показывает что идея A уже реализована, B есть только в proposal, C проверялась на старом SHA, а D блокируется установкой. Она формирует не новый общий roadmap на 2 000 PR, а один проверяемый вертикальный срез с тестом и evidence contract.

## Knowledge graph без бесконечной сложности

Начать с малых типизированных связей: `message proposes requirement`, `requirement mapped_to symbol`, `symbol verified_by test`, `test produced receipt`, `receipt observed_on revision`, `proposal supersedes proposal`, `source supports/contradicts claim`. Сохранять первичные факты отдельно от автоматически извлечённых гипотез отношений.

Семантические embeddings — вспомогательный индекс; сначала lexical/path/exact symbol search. Поиск по смыслу не должен заменять точное попадание по `qualification_report.py`, SHA или номеру PR.

## Отрицательная память

Хранить не только «что получилось», но и failed commands, причины, environment, patch/revision, ложные предположения и действия, которые не надо повторять. Перед новым plan выбирать релевантные неудачи. Их отсутствие в свежем prompt — частая причина повторной работы; это проверяемая гипотеза для нашего benchmark, не универсальный рекламный тезис.
