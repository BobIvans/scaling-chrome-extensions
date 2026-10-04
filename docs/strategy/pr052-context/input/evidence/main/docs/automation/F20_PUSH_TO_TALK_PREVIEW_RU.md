# F-20: bounded push-to-talk и transcript preview

## Подтверждённый gap

На проверенном F-19 head расширение имело media artifact inventory и отдельный
локальный ASR experiment, но не имело владельца записи микрофона, push-to-talk UI
или редактируемого transcript preview. ASR experiment читает явно выбранный файл
и не является разрешением записывать микрофон или запускать action.

## Реализация

`one-click-context/library/voice-preview.mjs` — единственный новый voice owner.
Страница библиотеки вызывает `getUserMedia({audio:true,video:false})` только после
настоящего pointer/keyboard hold. Отпускание, потеря pointer capture, blur,
скрытие/закрытие страницы или 60-секундный timer останавливают запись и закрывают
все media tracks. Позднее разрешение после отпускания не начинает запись.

Audio ограничено 16 MiB, хранится только в памяти вкладки и может быть сохранено
отдельной явной кнопкой. Новое удержание/очистка/закрытие отбрасывает предыдущий
Blob и отзывает object URL. Нет автоматической записи в библиотеку, localStorage,
Native Host или SQLite.

UI показывает отдельные состояния для отсутствующего `mediaDevices`,
`MediaRecorder`, поддерживаемого WebM/Opus, разрешения, audio track, recorder
error, пустого результата и превышения byte limit. Transcript preview вводится
или редактируется вручную, ограничен 16 000 UTF-8 байт и всегда помечен
`EDITED_UNVERIFIED`/`EMPTY`.

## Границы

F-20 не вызывает Web Speech, ASR, AI/model/provider API, Native Host, durable
queue, browser handler или shell. Transcript не является goal/command и никуда
не передаётся. Настоящий микрофон, Windows Chrome permission prompt, codec и
device teardown не проверены в CI; tests используют только синтетические streams.
Локальный ASR benchmark и его явная связь с выбранным audio остаются отдельной
последующей функцией.
