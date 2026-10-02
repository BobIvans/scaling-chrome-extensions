# F-21: независимая отмена voice-сессии

## Подтверждённый gap

На проверенном F-20 head существующие владельцы `agent-bridge/host.mjs` и
`durable-ui.mjs` уже отменяют только свои ephemeral/durable jobs и показывают их
состояния от host. Новый voice owner мог прекратить запись по release/blur/лимиту,
но не имел отдельного STOP/Escape, терминального cancel receipt или защиты от
позднего результата разрешения микрофона после явной отмены.

## Реализация

`one-click-context/library/voice-preview.mjs` остаётся единственным владельцем
локальной voice-сессии. Настоящий клик по `STOP voice` или доверенное нажатие Escape
увеличивает epoch сессии, очищает timer/chunks/Blob, закрывает media tracks, удаляет
ручной transcript и переводит сессию в `CANCELLED`. Поздние `getUserMedia`,
`dataavailable` и `stop` callbacks не могут восстановить отменённую запись.

UI показывает фактический `occ.voice-cancel-receipt.v1`: scope, терминальное
состояние, источник `UI`/`KEYBOARD`, timestamp и отрицательные признаки хранения
audio/transcript и dispatch действия. Receipt относится только к локальной
voice-сессии; он не подменяет receipts Native Host или durable queue.

## Границы

Путь отмены не вызывает ASR, Web Speech, provider/model API, Native Host, SQLite,
job queue, browser action или shell. Установленный Chrome, настоящий микрофон и
OS permission prompt не проверены в CI; тесты используют синтетические streams.
Отмена уже завершившегося внешнего действия и глобальная отмена jobs не входят в
F-21: их существующие владельцы сохраняются без изменений.
