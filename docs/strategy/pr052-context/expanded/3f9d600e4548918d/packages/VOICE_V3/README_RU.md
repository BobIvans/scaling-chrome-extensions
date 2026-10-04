# Voice AgentOS — Parallel Capture V3
Дата: **3 октября 2026**. Расширенный R&D/context package + offline reference code.

## Начать
`00_START/00_PARALLEL_CAPTURE_DECISION_RU.md` — ключевое уточнение пользователя и новая схема.
`08_HANDOFF/FIRST_DOCUMENT_TO_ANY_AI_V3_RU.txt` — первый документ выбранному AI.
`08_HANDOFF/MASTER_CONTEXT_FOR_ANY_AI_V3_RU.md` — общий контекст целей.
`12_EXPERIMENTS/ROUTE_PREDICTIONS_RU.md` — прогноз быстрых путей и сравниваемые профили.

## Содержимое
**40 требований; 54 R&D-направления** (18 исходных + 36 новых/уточняющих), **32 workflow specifications; 273 proposed function entries; 28 primary source records; 89 passing offline unit tests.**
Исходный ZIP с 8 файлами сохранён byte-for-byte. Source reads двух пользовательских repositories ограничены тремя документами; full-code audit и CI verification не проводились.

Числа описывают пакет, а не установленное приложение. Workflow JSON — canonical app-level design, **не native Laya import**. Не выполнено ни одного GitHub write, browser/API/voice action или bot trade.

## Важное
Сбор/запись: multiple producers одновременно. Code proposals: multiple isolated worktrees. Независимые действия: одновременно при непересекающихся ресурсах. Один effect owner нужен только для конкретного конфликтующего неидемпотентного изменения. Одно и то же сообщение в ZIP/чате/summary не становится несколькими независимыми доказательствами.

Reference lab — synthetic data only, не production security boundary и не live recorder. Windows, Dell, speech, external models, self-update и реальный Studious qualification остаются NOT_RUN.

Полнота доступного контекста: `01_CONTEXT/CONTEXT_COVERAGE.json`. Полный raw chat export, вся личная история и другие ранее упомянутые архивы не доступны здесь; этот ZIP не выдаёт их за включённые.

## Проверка
Из корня: `python -B verify_package.py`.
Из `06_REFERENCE_LAB`: `python -B -m unittest discover -s tests -v`; `python -B capture_demo.py --output capture-demo-output`.
Оффлайн-команды ничего не скачивают, не запускают приложение в фоне и не изменяют GitHub.
