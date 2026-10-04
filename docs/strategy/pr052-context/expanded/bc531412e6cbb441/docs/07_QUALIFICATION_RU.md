# Реальные команды бота и граница qualification

Источник: закреплённый `studious-pancake` SHA `67d3852cbc4cb1b24582df45adbf6a42d4da2af0`, [G08–G10]. Ниже команды обнаружены в коде; **в этой сессии не исполнялись**.

## Канонический вход

```powershell
python scripts/run_occ_memory_qualification.py `
  --request C:/OCCData/qualification-request.json `
  --operator-profile C:/OCCData/qualification-profile.json
```

`--request` и `--operator-profile` обязательны. Готовые shape-примеры лежат в `examples/`; пути надо заменить на проверенные локальные пути. Схема request — `occ.qualification-action.v1`, action — `qualify_and_report`. При PAPER_PASS wrapper возвращает 0, при диагностическом непрохождении — 3, при обработанной ошибке — 2. [G08]

Bridge делегирует `FAST-Q1-v3:src.qualification_report.qualify_and_report`, profile `offline_sender_free`. Модель не задаёт cwd, SHA, executable или права. [G09]

## Подкоманды, реально записанные в плане runner

| Шаг | Зарегистрированный argv после `flashloan-bot` | Смысл |
|---|---|---|
| status | `status --json` | Состояние установки/системы |
| capabilities | `capabilities --json` | Объявленные возможности |
| doctor | `config doctor --json` | Диагностика конфигурации |
| admission | `runtime-admission --command flashloan-bot.run --mode paper --json` | Допуск paper-команды |
| paper-shadow | `paper-shadow --journal-path {journal} --json` | Не более одного sender-free прохода после offline preflights |

`{journal}` — путь, назначенный runner, а не произвольная строка модели. Список взят из `PREFLIGHT_STEPS`/`PAPER_STEP` в `src/qualification_report.py`, прочитаны строки 1–240. Для более широкого каталога ещё нужен полный локальный snapshot и анализ остальных CLI/plugin путей. [G10]

Runner выставляет paper-only окружение и выключает live trading и перечисленные provider/flashloan adapters в своём вызове. Это нужно сохранить. [G10] Установка/пакет должны соответствовать reviewed checkout; правильное имя каталога или наличие файла не доказывает соответствие установленного console entrypoint.

## SCE-side без браузера

`agent-bridge/qualification_adapter.py --profile <fixed profile>` получает request через stdin; документация описывает прямой CLI smoke без Chrome. [G07] Лучше для первого desktop-среза вызвать этот adapter через фиксированный subprocess profile, а не дублировать bridge в UI.

Из той же документации известны проверки:

```text
node --test agent-bridge/*.test.mjs
python -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py' -v
```

Для Windows wildcard-поведение Node/shell нужно проверить на установленной версии. Не считать приведённую Unix-команду уже проверенным PowerShell-runbook.

## Что означает результат

`BLOCKED` — допустимый доменный итог диагностики. `PAPER_PASS` — не доказательство production, прибыли или разрешения подписывать транзакции. Adapter требует `qualified=false`, `release_authorized=false`, `live_authorized=false`, `transactions_sent=0`. [G07]

Отдельный файл `content-lab/occ-config/paper_campaign.plan.json` — proposal: `BLOCKED_NOT_STARTED`, несовместим с native adapter и не должен отправляться как Laya `/v1/systemone` request. [G06] Его 24 часа — желаемая длительность будущей кампании, а не выполненная работа.

## Следующий evidence loop

Desktop запускает один reviewed profile → сохраняет exact argv/SHAs/package hash/environment redactions → читает machine-readable receipt → показывает blockers → готовит context bundle только по релевантным участкам → получает предложенный patch → человек/изолированная CI проверяют patch → новая qualification. Никакого перехода paper→live на основании фразы AI «теперь готово».
