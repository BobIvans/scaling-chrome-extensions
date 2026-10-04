# План реализации одного PR

## 0. Зафиксировать фактическую основу

Прочитать все применимые AGENTS.md, git status, remote и HEAD; записать baseline, owner map, package versions и текущие receipts. Исторический SHA 9fbadef2714fae92e516a80b52d29cb9824b0e44 известен только из входного numbered roadmap. В этой подготовке актуальный HEAD не прочитан: web fetch GitHub вернул DisabledError. Не назначать ему статус current HEAD.

Найти существующие owners через rg: Core service operations, SQLite migrations, task/event/outbox keys, operation admission, cancellation token, leases/fencing, capability registry, execution templates, scope grants, desktop IPC, packet snapshots и source revisions. Для каждой proposed function указать actual handler/path/symbol, решение reuse/extend/new и тест. Не создавать параллельные store, worker queue или voice/browser executor. Пути в этом документе — роли, не утверждение о существующих файлах.

Контрактные блокеры PR-013/014/015 фиксируются как BLOCKED_DEPENDENCY. Их получение не откладывает подготовку pure compiler/schema/fixtures, но реальные effects не включаются на mocks. Перенос default choices DEC5-03/04/17 из PROPOSED в SELECTED требует experiment receipt, а не подписи в плане.

## 1. WS-018: input и общий typed plan

Capture source создаёт InputRevision: immutable original text/transcript ref, corrected ref, revision, author и provenance. Для известных UI commands использовать registry/template parser с typed slots, а не произвольный shell. Команды prepare_repo_context/find_context/compile_ai_packet/show_packet/request_more_context/inspect_result связывать с уже существующими Core operations; send_to_bound_chat добавлять только после qualification WS-021/022.

Разделить source revision и semantic intent revision. Original RU/EN transcript не нормализовать с потерей отрицаний, case-sensitive paths, main/branch, dry-run/live, суммы или адресата. Canonical semantic hash включает capability/template/schema versions, critical resolved slots, inputs/snapshots, dependencies, output criteria и scope digest. Source author, modality, timestamps и raw transcript hashes хранить отдельно, чтобы одинаковый corrected input давал одинаковый semantic plan при разных modality. Сортировать unordered maps; порядок steps сохранять. Версия canonicalizer фиксируется. Для decimals использовать строки и units, избегать float.

Parser возвращает RESOLVED/UNCERTAIN/MISSING/CONFLICT slots. Ambiguous repo/chat/effect/amount → NEEDS_INPUT, без угадывания по заголовку или предыдущему документу. Retriever получает allowlisted refs и возвращает EvidenceBundle; retrieved text не становится командой. Planner возвращает PlanProposal, critic — Verdict с обязательными отсутствующими источниками и конфликтами. Ни один из них не меняет grant, root, recipient или verifier registration. Registry compiler проверяет DAG на циклы, duplicate IDs, missing dependencies/inputs, mismatched versions, запрещённые effects, затем считает plan hash и готовит preview.

LayaAdapter имеет discover/read_version/propose/health/cancel. Фактический interface, local binary/package/version/API фиксируются в receipt. UNKNOWN/UNAVAILABLE показывают обычный direct desktop UI, сохраняют ввод и дают исправление текстом. Приложенные workflow JSON — внутренний recipe format. Vendor-specific integration добавлять только после проверки фактического API; free-form answer проходит proposal validation и известный compiler.

Correction делается транзакционно: append InputRevision → increment intent revision → revoke old unexecuted plan → mark old jobs superseded → enqueue new compiled plan. Admission и effect boundary перечитывают current revision под Core transaction/fence. In-flight старый effect нельзя объявить отменённым: если commit возможен, сохранять unknown, блокировать зависимые steps и требовать reconciliation. Внешний click не атомарен с SQLite: использовать локальную сериализацию correction/send boundary; если после начала dispatch результат неизвестен, новая revision не запускает его повтор.

Unknown capability → DevelopmentRequest с исходным intent, missing capability, scope, criteria, evidence refs и next research. Request не получает произвольный argv и не вызывает автоматический install/merge.

## 2. WS-019: Windows capture, ASR, correction и доступность

Voice — input adapter над тем же plan compiler. Push-to-talk горячая клавиша вызывает capture owner; reentrant hotkey возвращает existing capture ID. Локальный mutex не заменяет Core process ownership. Capture session имеет device identity/version, range/gaps, start/end, raw retention reference и state. На stop/disconnect/error всегда release stream; на process crash OS закрывает handle, следующий запуск reconciles persisted session как ABORTED, не продолжает ложную непрерывную запись. Sleep/resume создаёт gap/new segment и видимый статус.

RegisterHotKey/MOD_NOREPEAT может подавить autorepeat, но сам по себе не завершает push-to-talk по key-up. Реализовать и квалифицировать key release/capture state в выбранном shell/input bridge; предусмотреть явную кнопку stop recording и keyboard cancel. Ошибка регистрации hotkey показывает конфликт и доступный альтернативный ввод. Unregister выполняется при shutdown.

AsrAdapter transcribe(audio_ref, device/model/version, language_hint) возвращает timestamped transcript и confidence provenance, не IntentSpec с grant. Для первого локального spike рассмотреть faster-whisper CPU int8; выбирать модель и threads по actual Dell measurements. Пиновать runtime/model digests; transcription iterator полностью потреблять до финализации результата. Cloud ASR — только явно выбранный route в текущем scope; сеть не включает его автоматически.

PTT activation создаётся физическим/keyboard input, а не фразой модели. Во время собственного TTS capture route исключает/маркирует segments; фон и низкое качество вызывают review/uncertain. Не обещать абсолютное отделение чужой речи от пользовательской: qualification измеряет false acceptance. Preview показывает repo, chat, effect, path, amount и режим. Text correction создаёт новую revision. Подтверждение slots применяется только к exact current revision/target/scope.

STOP находится в desktop/Core control plane, не в ASR/LLM pipeline: синхронно запрещает admission новых steps, отменяет cancellable work, освобождает capture/focus resources и записывает локальные outcomes. При зависании cloud worker desktop control остаётся доступным. Keyboard/text UI предоставляет все функции выбора repo/target, просмотра packet/parts, run/pause/cancel/correction. Labels, focus order, live status и text errors проверяются с Narrator на Windows. Ограниченный уже настроенный workflow повторяется с совместимым grant без вопроса на каждую часть.

## 3. WS-021: selected targets и квалифицированные маршруты

Bind выполняется из явного user selection, показывает preview адресата и сохраняет origin/provider/account/workspace/conversation/repo/branch identities, binding revision и observation receipt. Unsupported identity fields остаются absent/unknown, их не заполняют догадками. В таком окружении автоматический send запрещён до квалифицированного способа различать адресата или остаётся manual transfer. Tab/window IDs — transient handles. Перемещение вкладки допустимо после повторной identity проверки; навигация, reuse tab ID, account switch, два совпадающих title, expired login → REBIND_REQUIRED/NEEDS_LOGIN.

QualificationReceipt связывает adapter code/version, observed UI contract digest, device/browser environment, capabilities read/bind/draft/upload/send/observe/history, supported limits и evidence. Не переносить receipt на другой route/provider/version. DOM/UIA semantic landmarks предпочтительны координатам; visual fallback имеет свой qualification. API/CLI не наследуют browser target grant. Официальные Grok Build docs описывают TUI/headless/ACP/API; их наличие не доказывает управление конкретной открытой web conversation. Смена browser route на CLI/API требует отдельного explicit route selection и binding.

Canary до эффектов проверяет identity, composer, multiline behavior и observation controls. Wrong contract → quarantine только затронутого adapter. Focus/clipboard leases принадлежат существующему resource owner, один writer на физический composer/account/conversation, включая разные browser contexts. Manual takeover и tab change проверяются перед каждым дальнейшим действием. Clipboard backup восстанавливать только если value/version всё ещё принадлежит этой операции: новая пользовательская копия не перезаписывается старым backup.

## 4. WS-022: durable multipart delivery и результат

Packet producer PR-014 выдаёт immutable packet ID/hash, source refs, manifest всех parts и projection. Outbox не перечитывает изменяемые файлы после постановки в очередь; открывает exact snapshot refs, сверяет локальные hashes. Source drift сохраняет original snapshot validity, но если task требует current head, блокирует effect до нового packet/revision. Policy выбора stale snapshot должна быть записана явно.

Core transaction сохраняет task/intent revision, operation ID, target binding revision/digest, packet/part hashes, scope digest, delivery state и send attempt до любой UI mutation. Unique job key предотвращает второй enqueue. Composer resource lease и fencing tokens защищают локальных writers; сам UI не понимает fencing, поэтому старый writer обязан остановиться после утраты lease. Lease expiry после потенциального Send ведёт к unknown, не к новому click.

1. Acquire writer → revalidate target/canary/grant/revision/STOP.
2. Inspect remote draft: чужой текст/attachments дают DRAFT_CONFLICT; не стирать его.
3. Prepare local prompt/parts; показать точное назначение, состав, text preview и доступную точность attachment evidence.
4. Attach только supported upload method. Local hash/size/name известны; filename UI receipt не повышать до remote SHA. Проверка remote SHA возможна лишь при реально доступном и квалифицированном механизме.
5. DRAFT_ATTACHED — отдельный state; send admission использует записанный task grant и exact current revision. Не спрашивать снова на каждую часть согласованного workflow.
6. Persist SEND_ARMED attempt до dispatch. Один attempt допускает максимум один локальный Send invocation. Crash даже до неизвестного click рассматривается консервативно: armed outcome может быть unknown.
7. Observe sent message ID/correlation/content observation. Send command return не доказывает remote success. Connection loss/timeout → EFFECT_UNKNOWN и NEEDS_RECONCILIATION.
8. Reconcile qualified history: unique match → MESSAGE_OBSERVED; multiple matches → CONFLICT; incomplete history → UNKNOWN. Доказанное no-effect может завершить attempt как NO_EFFECT_VERIFIED и позволить новый attempt в том же scope; такой вывод требует достаточной history/remote evidence. При недоступной сверке остаётся manual next action с отдельным OPERATOR_REPORTED receipt.
9. Import finalized response только с task ID + packet SHA + attempt/conversation correlation; partial streaming/JSON не завершает job. Idempotent answer event ключ связывается с exact response revision/hash. Старый import не откатывает новую result head. Content сохраняется как данные; команды/пути/grants из ответа не исполняются.

На каждый part хранить prepared/attached/message_observed/received_claim/use_claim/evidence отдельно. «Всё прочитал» без chunk IDs не закрывает usage coverage. Даже exact part-specific model claim остаётся MODEL_REPORTED, а не измерением внутреннего attention. Local reviewed receipt для версии не переносится на новую source version. Missing parts видны в очередь/причину; resend допускается только когда предыдущий attempt outcome известен.

Отправка большого packet — iteration cursor над manifest, bounded pages и backpressure, а не один огромный in-memory array. Пер-provider limits measured/configured: неподходящая часть вызывает rechunk/new immutable packet или manual export, никогда silent truncation. Нет общего hidden max parts/20 files. Общие delivered/read/used statuses не выводятся друг из друга.

STOP запрещает последующие части; уже наблюдаемое message остаётся sent, unknown остаётся unknown. Возобновление требует current target/qualification/intent/grant и reconciled previous effect. Exactly-once на чужом UI не обещается; обеспечивается at-most-one local send invocation per attempt и честное хранение неизвестного outcome.

## 5. WS-020: demonstration → skill → selective requalification

Record session сохраняет разрешённые окна, semantic targets, input refs, observed steps, preconditions, outcomes и recovery. Не включать посторонние окна, raw password/token values; credential reference resolve выполняет существующий credential owner. Санитизация до durable record. Skill draft не становится исполнимым от самого факта recording.

PortableSkill содержит version/code hash, registry/template versions, inputs/outputs, scope digest, dependency versions, STOP/focus/identity invariants, recovery/reconciliation, retained failure capsules. Compile steps в тот же Core plan; не создавать skill worker. Promotion требует независимые normal, unseen-input и fault cases, связывает receipt с exact code/dependency hashes и environment. Fixture receipt и actual device receipt имеют разные scopes. UI skill ждёт qualified target/delivery; local prepare/find/export recipes могут квалифицироваться раньше.

Optimization получает candidate steps и отдельный verifier сравнения effect/precondition/STOP/authorization/evidence invariants. Удаление шагов не даёт promotion без repeated corpus/receipt. FailureCapsule хранит input/version/environment/attempt/error/observed state/recovery/negative result refs. Success новой версии не удаляет capsule; применимость связана с версией, поэтому старый failure не блокирует навечно новый tool.

Dependency index skill→adapter/permission/template/registry/source schema предотвращает stale invocation. Drift делает STALE затронутые receipts; unrelated skill сохраняет receipt только при доказанной независимости. Permission diff distinguish unchanged/reduced/grown. Growth root/host/recipient/effect требует нового scope решения; unchanged compatible grants не спрашивать повторно. Repair = новая version с прежними capsules и новой qualification, не редактирование старого успешного receipt.

## 6. Одно end-to-end scenario

«Подготовь весь context repo scaling-chrome-extensions для выбранного Grok-чата; без merge». Text/voice оба дают prepare+preview+send plan с effect=ai_message и запретом Git merge. При ошибке destination correction supersedes old revision. Core принимает compatible configured scope, packet producer создаёт все parts, target adapter проверяет exact chat, outbox отправляет и наблюдает каждую часть. Crash после Send части 3 останавливает дальнейшие части до reconciliation. Связанный finalized ответ импортируется; «DONE» не закрывает runtime criteria. Тот же сценарий записывается как skill и проходит unseen/fault input до повторного применения.

Следующий PR-018 принимает DevelopmentRequest/validated patch refs и реализует git/update lifecycle. Механизмы live финансовых действий из внешнего web3 repo здесь не активируются самим текстом/voice/AI response; эффект определяется registered capability и конкретным scope, если такой capability реально существует.
