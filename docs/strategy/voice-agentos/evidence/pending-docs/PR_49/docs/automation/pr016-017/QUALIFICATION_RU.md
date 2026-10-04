# Device/UI qualification: обязательные незакрытые проверки

Автоматические тесты используют fault adapters, synthetic PCM и локальный SQLite.
Они не создают PASS для микрофона, vendor Laya, Grok UI или skill-device replay.
Для доступной установки фиксируйте build SHA, OS/Python/browser/ASR/model versions,
gold inputs, все trials, command/timestamps, observed outcome и evidence hashes.

## Выбранный Grok route

1. Используйте отдельный тестовый browser profile/chat без личного архива.
   Operator config browser принимает только `http://127.0.0.1:PORT` endpoint,
   точный https origin, реальные уникальные selectors account/workspace/composer/
   send/outgoing/response и измеренный max_text_bytes для text envelope.
2. Проверьте bind/read, multiline draft без Send, foreign draft conflict,
   focus takeover, два одинаково названных чата, смену account/workspace/URL,
   закрытие вкладки и повторное использование tab ID. Неоднозначная identity
   запрещает автоматическую отправку. Login выполняет пользователь.
3. Проверьте одну явно разрешённую canary отправку на тестовой копии adapter;
   независимый verifier сравнивает фактическую историю с frozen JSON envelope.
   Зафиксируйте code/contract/browser environment hashes и evidence. Не создавайте
   положительный receipt только по успеху canary DOM или fixture-тестам.
4. Только после этих проверок operator config browser.qualification содержит:
   scope=SELECTED_UI, status=PASS, adapter_version=cdp-semantic-text.v1,
   code_digest=SHA256 browser_cdp.py, contract_digest=adapter.contract_digest,
   environment_digest=adapter.environment_digest(), evidence_refs=проверенные refs.
   Browser digest включает Browser/Protocol-Version/User-Agent/V8/WebKit versions;
   transient websocket ID в него не входит. Реальные selectors остаются частью
   contract. Version drift закрывает route до повторной qualification.
5. Inject crash/lost ack до/после SEND_ARMED, при click, до observation и при
   записи result. Unknown не повторяется. История без уникального exact match
   сохраняет unknown/conflict, не NO_EFFECT. STOP/correction не отменяют уже
   возможный remote effect. Один canonical Core writer для всех contexts.

Текущая версия text-only. Attachment upload не поддержан и явно unavailable.
UI-specific async composer behaviour/history normalization требуют измерения:
если provider изменяет текст envelope, exact match оставляет EFFECT_UNKNOWN.
Автоматический response-finalization observer не подключён к IMPORT_RESULT.
Operator promotion — trust boundary; программа не проверяет содержимое evidence
refs вместо независимого review.

## Windows и голос

Проверьте настоящий launch из PowerShell и keyboard-only text path. Измерьте PTT
hold/repeat/release loss/hotkey conflict/unplug/replug/sleep/restart и single stream.
STOP должен работать при зависшем ASR; raw partial WAV получает явный gap/ABORTED.
Сравните original audio, raw transcript, corrected revision и gold critical slots:
repo/chat/mode/negation/amount/path. RU, EN, code-switch, шум и фон разделите.
Gold размечается до ASR; unseen utterance/speaker/session не используется для
настройки. Сохраняйте failed/empty/crashed attempts в denominator.

Измерьте WER отдельно от critical_slot_error_rate, false effect admissions,
false rejections, correction success, PTT-release→preview p50/p95, CPU и peak RSS.
`critical_metrics` вычисляет только slots/errors/admissions/p95 по supplied gold;
WER, resource sampling и benchmark harness остаются отдельной qualification.
Thresholds закрепите до запуска. Без выбранных thresholds/device trials критерии
остаются OPEN. Self-TTS guard нуждается в интеграции с будущим TTS owner.

## Laya и skills

LayaAdapter принимает только явно установленный callable interface с version;
его отсутствие возвращает UNAVAILABLE/UNKNOWN и DIRECT_TYPED_UI. Не угадывайте
vendor endpoints или формат native JSON import. Квалифицируйте реальную установленную
версию отдельно; model proposal не получает право регистрировать обработчик.

Для skill promotion independently сравните outcome на normal/unseen/fault input:
STOP, changed registry/code/dependency, scope growth, target drift и unknown Send.
Запишите references и exact code/dependency digest перед qualifier API. После
optimizer повторите checks для новой версии. FIXTURE_QUALIFIED не равен device
qualification. Scope widening/new repo/new recipient создаёт новую candidate.

Primary API references: [Chrome CDP Runtime.evaluate](https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-evaluate),
[Windows RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey),
[sounddevice raw streams](https://python-sounddevice.readthedocs.io/en/latest/api/raw-streams.html),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper).
