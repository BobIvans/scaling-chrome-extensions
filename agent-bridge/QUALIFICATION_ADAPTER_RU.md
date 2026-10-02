# OCC Memory → Qualification: native bridge

Этот слой реализует OCC-side часть связки с уже merged `studious-pancake` bridge. Он не создаёт второй qualification engine и не запускает live trading.

## Что добавлено

Native Host получает только зарегистрированную команду `qualification.inspect`:

```json
{
  "type": "qualification.inspect",
  "taskId": "qualification-001",
  "text": "Проверь готовность бота",
  "sourceRefs": [
    {
      "source_id": "chat:qualification-goal",
      "version": "2026-10-02",
      "sha256": "<64 hex>"
    }
  ]
}
```

Команда выключена по умолчанию. Она появляется в `hello.qualificationCommands` только когда оператор явно добавил `qualificationCore.enabled=true` в локальный `host-config.json`.

Текст команды и source content не выбирают Python, checkout, SHA, output path, bot script или timeout. Эти значения берутся только из reviewed operator profile. Source references являются metadata-only: в bot request передаётся только идентификатор, версия и SHA256; тело источника не становится argv или инструкцией.

## Operator profile

Скопируйте `qualification-profile.example.json` вне репозитория и замените placeholders. Профиль содержит:

- абсолютный путь текущего OCC checkout;
- ожидаемый OCC SHA и baseline SHA;
- абсолютный Python 3.13;
- абсолютный путь к каноническому `studious-pancake/scripts/run_occ_memory_qualification.py`;
- bot checkout и exact bot SHA;
- output root вне обоих checkout;
- bounded per-step timeout 1–30 секунд.

Adapter проверяет clean OCC checkout и exact HEAD. Bot script обязан находиться именно в `BOT_REPO/scripts/run_occ_memory_qualification.py`.

## Native Host config

После установки/review добавьте opt-in блок:

```json
{
  "qualificationCore": {
    "enabled": true,
    "pythonPath": "C:/Python313/python.exe",
    "adapterPath": "C:/OCCNativePrepared/qualification_adapter.py",
    "profilePath": "C:/OCCData/qualification-profile.json"
  }
}
```

Installer только копирует bridge/adapter. Он **не включает** qualificationCore автоматически и не создаёт профиль за оператора.

Native transport запускает:

```text
python -I -X utf8 qualification_adapter.py --profile <fixed operator profile>
```

с `shell:false`, без OPENAI/HF/API keys, PYTHONPATH и desktop IPC. Request передаётся через stdin. Stdout/stderr имеют общий лимит 512 KiB, native timeout — 210 секунд.

## Связь со studious-pancake

OCC adapter создаёт точный bot request:

```json
{
  "schema_version": "occ.qualification-action.v1",
  "request_id": "<taskId>",
  "action_id": "qualify_and_report",
  "text": "Проверь готовность бота"
}
```

и отдельный bot operator profile `studious-pancake.occ-qualification-profile.v1`. Затем вызывает только merged bot-side script `run_occ_memory_qualification.py`.

Ответ принимается только если:

- schema соответствует merged bridge;
- request/source refs/OCC base+head/bot SHA совпадают;
- verdict только `BLOCKED` или `PAPER_PASS`;
- `qualified=false`;
- `release_authorized=false`;
- `live_authorized=false`;
- `transactions_sent=0`.

`BLOCKED` — нормальный диагностический результат, а не transport failure. `PAPER_PASS` также не означает production qualification.

## Replay и неизвестный исход

OCC сохраняет свой receipt в:

```text
BOT_OUTPUT_ROOT/occ_adapter_requests/TASK_ID/
```

Повтор с тем же task/profile digest переиспользует завершённую квитанцию. Изменённый payload под тем же task ID отклоняется. Если child process завершился неизвестно, manifest становится `RECONCILIATION_REQUIRED`; тот же task ID не выполняется повторно автоматически.

## Прямой CLI smoke

Для теста без Chrome:

```bash
python agent-bridge/qualification_adapter.py \
  --profile C:/OCCData/qualification-profile.json \
  < agent-bridge/qualification-request.example.json
```

Успешный transport возвращает `{"ok":true,"result":...}`, даже если domain verdict — `BLOCKED`. Input/config/runtime failure возвращает только bounded `QUALIFICATION_REQUEST_FAILED`, без утечки локальных путей или stderr.

## Границы

Этот PR не:

- добавляет trading/signer/wallet permissions;
- запускает scheduler или worker;
- включает Laya/LLM inference;
- читает browser cookies/credentials;
- меняет durable SQLite owner;
- меняет UI;
- разрешает модели выбирать shell/argv/path/SHA;
- превращает source content в инструкции.

Проверки: `node --test agent-bridge/*.test.mjs` и `python -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py' -v`.
