# FAST-Q2: локальный адаптер qualification

Этот CLI-срез продолжает существующий `agent-bridge`: одна зарегистрированная
задача вызывает установленный FAST-Q1 `flashloan-checks`. Chrome Native Messaging
и Codex JobHost сохраняют свои существующие границы; новый CLI не расширяет их
разрешения и пока не добавляет кнопку в установленное расширение.

Сначала установите версию studious-pancake с FAST-Q1 в отдельном Python 3.13
окружении. Запускайте адаптер тем же Python, чтобы он использовал соответствующий
console script. SHA и рабочие каталоги задаются оператором в CLI, вне запроса
модели. Пример запроса: `qualification-request.example.json`.

```bash
/absolute/bot-venv/bin/python agent-bridge/qualification_adapter.py \
  --request agent-bridge/qualification-request.example.json \
  --repo-root /absolute/bot-checkout \
  --output-root /absolute/qualification-runs \
  --expected-sha YOUR_40_CHARACTER_COMMIT_SHA
```

Без `action_id` поддерживается только точное совпадение нескольких фраз:
«проверь готовность бота», «запусти qualification campaign», `run qualification`,
`check bot readiness`. Другие запросы возвращают NEEDS_CONTEXT. Параметры shell,
дополнительные JSON-поля и незарегистрированные действия отклоняются.

`--laya-shadow` включает локальную advisory-рекомендацию multilingual Laya.
Она не изменяет разрешённое действие. При первом использовании SDK может
скачивать веса; устанавливайте/фиксируйте версию Laya и revision отдельно.
Отсутствие SDK не включает платный fallback. Базовый путь работает без модели.
API Router соответствует ранее подготовленному OCC demo; второй inference
service, scheduler или библиотека контекста не создаются.

Проверяются версия ответа CLI, request ID, Git SHA, каталог результатов,
sender-free ограничения и факт завершения диагностики. BLOCKED внутри успешного
ответа сохраняется как BLOCKED. INSPECTED не превращается в QUALIFIED.
Результат печатается как `occ.qualification-adapter-receipt.v1` и сохраняется
в `OUTPUT_ROOT/adapter_requests/REQUEST_ID/adapter_receipt.json` вместе с manifest.
Повтор с тем же запросом и операторскими параметрами возвращает сохранённый
результат без повторного inference или CLI. Изменение текста/SHA под тем же ID
отклоняется. Незавершённый запрос требует сверки перед повтором; terminal BLOCKED
также не запускается повторно автоматически. Это файловые квитанции, не второй
scheduler или отдельная библиотека контекста. Их можно импортировать через
существующий импорт файла.

Тесты: `python -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py'`.
Реальное Laya inference, holdout evaluation, установленный Chrome/remote WSS и
интеграция UI остаются отдельными экспериментами. Наличие этого CLI не закрывает
полный FAST-Q2, универсальную маршрутизацию или production qualification.
