# PR-016 + PR-017: единый Core action runtime

Текст или исправленный voice transcript создаёт ревизию intent и проверяемый
план. Явный Enqueue добавляет `action_plan` в существующую очередь Core.
Те же SQLite, jobs, lease и глобальный writer обслуживают пакет, попытки Send,
coverage, результаты и версии skills. Desktop и Native Host используют один
dispatcher; пользовательский текст не выбирает executable, shell или grants.

Это реализуемый opt-in baseline объединённого PR, а не закрытие всей стратегии.
В `FUNCTIONS_IMPLEMENTATION.json` сопоставлены все 50 запланированных функций.
`CRITERION_COVERAGE.json` сохраняет точные 220 исходных критериев: все остаются
OPEN до собственного evidence и необходимых device/UI receipts. Source ZIP и
baseline SHA закреплены в `SOURCE_PROVENANCE.json`.

## Запуск текста

1. Обновите выбранную установку backend и desktop из этой ветки. Обновите
   `expected_adapter_sha256` существующего desktop connection и переподключитесь.
2. В существующую operator policy добавьте только секцию `actions` из
   `policy.example.json`. Выберите реальный разрешённый namespace. Для `prepare`
   скопируйте зарегистрированные repositories из Native profile без изменений.
   Не заменяйте имеющиеся sources/repos/reports/CI-настройки этим примером.
3. Откройте «Текст / голос → действия». Выберите capability, namespace, исходные
   source IDs и критерии. Plan preview сохраняет intent, Enqueue — очередь.
   Исправление создаёт новую revision и отменяет старые неисполненные jobs.
4. Запустите существующий worker; панель сама не запускает исполнитель:

```powershell
python content-lab/automation_core.py --store 'C:\OCC\store' work --policy 'C:\OCC\policy.json'
```

Для headless ввода есть CLI того же dispatcher:

```powershell
python content-lab/action_cli.py --profile 'C:\OCC\native-profile.json' INFO
python content-lab/action_cli.py --profile 'C:\OCC\native-profile.json' CREATE --payload docs/automation/pr016-017/input.example.json
```

Запишите возвращённые `intent_id`/`revision` в JSON payload для ENQUEUE. `work`
обрабатывает один job; используйте имеющийся supervisor для повторного запуска.
Known commands — literal aliases или явный зарегистрированный capability.
Неизвестная команда создаёт `development_request` с authority PROPOSAL_ONLY.
Critical slots заполняет пользователь; автоматический NLU extractor не заявлен.
`не send`, `не отправ…`, `dry-run`, `preview-only` блокируют AI_MESSAGE;
для него всегда нужен `slots.mode = "SEND"`. Другие режимы не подразумевают Send.

## Пакет и доставка

`packet` берёт только явно выбранные текущие eligible text sources namespace;
исторические, отсутствующие и исключённые источники не обходят existing classifier.
Native PACKET_START/APPEND/SEAL позволяет отдельно собрать большой multipart
пакет. Один APPEND должен поместиться в 16 000-byte native frame; это предел
одного сообщения, а не числа частей или общего пакета. Ordinal/hash CAS исключает
тихую замену части. SEALING замораживает append, полный manifest hash вычисляется
вне writer transaction, повторный seal восстанавливает прерванный процесс.

Browser route опционален: локальный Chrome CDP + измеренные semantic DOM selectors.
Нет встроенных предполагаемых Grok selectors. Обязательны наблюдаемые account,
workspace, conversation URL, выбранный tab, focus и adapter contract. См.
`QUALIFICATION_RU.md`. Без этого остаётся локальный пакет и ручная передача.

После BIND закрепите `binding_id` в operator grants targets и AI_MESSAGE в
effects, переподключитесь и создайте новый intent после изменения policy.
Send принимает sealed packet ID, binding ID и явный SEND. Все intents/packets
закреплены за policy и revision; изменение policy требует нового плана.

Попытка сохраняет PREPARED и отдельный неизменный prompt с goal/criteria/source
hashes. До внешнего Send транзакционно фиксируются SEND_ARMED и invocations=1.
Любой сбой после arming сохраняет uncertainty. Нет автоматического повторного
click. RECONCILE читает историю, CONTINUE требует доказанного наблюдения всех
предыдущих попыток и явного подтверждения остановки старого процесса. Отсутствие
сообщения в неполной истории означает EFFECT_UNKNOWN. Duplicate match — CONFLICT.
STOP закрывает новые admissions/arms, отменяет queued jobs и сохраняет возможный
remote effect; уже начатый внешний вызов невозможно отозвать транзакцией SQLite.
Resume admission не воскрешает старые jobs. Закрытие панели прекращает capture,
но не является Core STOP — нажмите STOP для остановки Core.

После интеграции PR-014/015 actions и context/campaign jobs используют общий
`core_control` STOP fence и canonical queue capacity. Action STOP запрещает новые
Core admissions; library/Core STOP также запрещает action admissions. Resume
использует текущий epoch CAS и блокируется при RUNNING/NEEDS_RECONCILIATION worker.
Legacy `action_control` сохраняется в store как историческая таблица, но не является
вторым control owner. Standalone Desktop installer включает обе панели/actions
и закрепляет action modules в backend build digest.

UI_OBSERVED подтверждает видимость отправленного сообщения, не использование
контекста моделью. IMPORT_RESULT принимает проверяемую корреляцию task/attempt/
packet/conversation и точные part hashes. Его `revision` — revision импортируемого
result head; intent revision остаётся в frozen prompt. `finalized` подтверждает
оператор: автоматическая проверка окончания Grok streaming ещё не подключена.
MODEL_REPORTED_RECEIVED/USED и done — утверждения модели, не authority на effects.

## Голос

Для optional PTT установите и квалифицируйте sounddevice/PortAudio и существующий
локальный faster-whisper CPU backend. Добавьте в operator actions.voice:

```json
{
  "capture_root": "C:\\OCC\\voice-captures",
  "device": null,
  "model_dir": "C:\\OCC\\models\\whisper-small",
  "content_lab_sha256": "SHA256_OF_SELECTED_CONTENT_LAB_PY",
  "language": "ru",
  "threads": 4
}
```

Выберите эти пути явно; программа не скачивает модель. Кнопка/Space и Windows
Ctrl+Shift+Space используют один capture. WAV пишется на диск блоками, OS lease
блокирует вторую запись, release/STOP/device loss/60s закрывают stream. После
рестарта прерванные записи видимы как ABORTED. ASR возвращает editable unverified
text, затем нужен обычный preview/Enqueue. Поздний transcript не заменяет более
новый ввод. Ошибка microphone/hotkey/ASR сохраняет текстовый путь.

Raw WAV и sidecar сохраняются в явно выбранном capture_root до ручного удаления.
Согласуйте retention перед включением; автоматический GC и raw-audio шифрование
здесь не реализованы. `tts_active` — guard для будущего TTS owner; текущий desktop
не имеет собственного TTS, фоновые голоса автоматически не классифицируются.
ASR идёт в отдельном UI worker; independent STOP имеет отдельный IPC-клиент,
но inference не получает hard CPU/memory timeout.

## Skills

SKILL_RECORD принимает только successful Core job traces текущей intent revision,
typed plan, preconditions, mandatory invariants и credential references. Raw UI
recording и перенос vendor skill format не заявлены. Candidate нельзя исполнить.
Доверенный оператор использует `ActionRuntime.qualify_skill` только после
независимых normal/unseen/fault checks; этот promotion API не опубликован в Native
dispatcher. Receipt закрепляет code/dependency hashes. FIXTURE_QUALIFIED пригоден
только для LOCAL_READ; effect recipe требует SKILL_DEVICE evidence.

Replay сохраняет capability, slots, sources, criteria и DAG. Goal text может
меняться. Параметрический перенос на новый repo/chat требует новой версии;
автоматическое расширение authority отсутствует. Registry/runtime digest и
operator dependency_versions сверяются на admission. Invalidation помечает
зависимые версии STALE. Failure capsules append-only и остаются в прежних версиях.
Optimizer удаляет лишь одинаковые pure-read шаги и создаёт новый CANDIDATE;
оптимизированная версия снова требует unseen/fault qualification.

## Остаток стратегии и rollback

Открыты: real Windows mic/ASR/hotkey/focus и latency corpus, installed Laya API,
actual Grok selected-account UI canary, file uploads/limits, complete remote
history/stream finalization, параметрические portable skills и полноценное
planner/retriever/critic orchestration. DAG поддерживает фиксированный effect
class; смешанный repo→packet→Send pipeline оформляется отдельными intent/jobs с
проверкой каждого шага. Clipboard route отсутствует. PR-013/014/015 в main не
имеют всех заявленных финальных контрактов; baseline использует доступные owners,
не объявляя эти prerequisites закрытыми.

Migration additive в том же `content.sqlite3`. Перед включением сохраните backup
store при остановленном worker. Для rollback: STOP, остановите worker, разрешите
unknown effects по журналу, затем отключите actions в policy. Старые items и
sync/jobs сохраняются. Не удаляйте action tables: там evidence и outbox. Старый
Core не сможет выполнить action_plan jobs; не запускайте их после downgrade.

Проверки и реальные ограничения перечислены в `VALIDATION.md`.
