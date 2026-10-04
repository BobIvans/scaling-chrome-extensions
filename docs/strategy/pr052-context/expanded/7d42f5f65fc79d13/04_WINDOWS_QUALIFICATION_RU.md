# Windows / selected target qualification

Это runbook, не отчёт о выполненных Windows tests. Все поля измерений стартуют null; fixture не является Dell mic receipt.

## Подготовка

Зафиксировать Windows build, установленный app/core build SHA, Dell Latitude 5400 CPU/RAM, input/capture device identity, driver version, sample format, shell/browser/provider/adapter/UI contract version, ASR/model digests, threads, current grant/scope и test target identity. Реальный выбранный микрофон нельзя вывести из модели ноутбука. Canary выполняется в выделенном согласованном test conversation, с synthetic packet и harmless text; общий document не расширяет scope.

## Text и доступность

Keyboard-only: открыть desktop без Chrome, выбрать repo, найти context, подготовить packet, пройти все части, preview, bind target, исправить slots, run/pause/cancel, импортировать result. Narrator читает names/status/errors; focus order устойчив. Disconnect mic/kill ASR не ломают эту последовательность. Repeat настроенного workflow не задаёт одно и то же разрешение; change recipient/effect/scope фиксирует новый scope decision.

## Voice corpus

Собрать отдельные реальные audio clips и вручную размеченный gold text/slots: RU, EN, code-switch, repo aliases с похожими названиями, «не merge», «main»/«branch», «dry-run»/«live», numbers+units, ambiguous destination, паузы, шум, собственный TTS, чужая фоновая речь. Gold разметку сохранять до запуска ASR; tune split и held-out split разделить по utterance/speaker/session. Готовые текстовые templates в corpus/ — specification, не реальные звуковые samples и не benchmark ASR.

На каждую фразу: original audio ref, transcript revision, reference text, reference critical slots, ASR output, slot parser output, review/correction, admitted effect/no effect, timings и reason. Измерять WER=(S+D+I)/reference_words, critical_slot_error_rate=wrong_or_missing_gold_slots/all_gold_critical_slots, false_effect_admission, false_rejection, correction success, p50/p95 latency PTT release→preview, peak RSS и CPU. WER не заменяет slot errors. В denominator сохранять все попытки, включая crashes/empty transcripts; unavailable metrics указывать отдельно. RU/EN/code-switch и фон/TTS выводить отдельными группами.

Предлагаемый safety gate: zero observed wrong-target/negated/live effect admissions на qualification corpus; это результат данного corpus, не универсальная гарантия. Число trials и confidence intervals записывать. Latency/accuracy thresholds DEC5-17 согласовать и закрепить до qualification; если budget не выбран, criterion остаётся OPEN. Не обещать latency по чужому benchmark.

Hotkey: повтор при удержании, double press, конфликт registration, release event loss, explicit stop, capture process crash, unplug/replug, device switch и sleep/resume. Проверить один stream, handle release, видимые gaps, recovery и работающий keyboard STOP при ASR/network stall. Выключить/зависнуть ASR worker; проверить, что Core не принимает следующие effects после STOP. Already possible remote effect остаётся unknown.

## Target и delivery

Создать два test chats с одинаковым названием, два browser contexts, изменить account/workspace, переиспользовать tab ID, открыть новый conversation в прежней вкладке, move tab, user focus takeover и compose foreign draft. До upload и до Send проверять binding/canary. Unsupported observable identity = ручной маршрут, не guessed automatic send. Login выполняет пользователь; NEEDS_LOGIN сохраняет задачу.

Qualification stages: bind/read → multiline draft без send → attachment observation → один scoped canary send → history reconciliation → result import. Зафиксировать реальные provider limits и supported controls. Не посылать весь личный архив ради smoke test. Отдельно проверить crash до/после transaction commit, SEND_ARMED, possible click, message observation и response commit. Полная history/unique match, duplicate match и incomplete history имеют разные outcomes. Проверить cancel/STOP на каждой границе; local cancelled не означает remote cancelled.

## Scale

Synthetic immutable manifests с 1, 21, 257, 4097 parts и параметризуемым N: итерация всего manifest, bounded resident page, lossless ledger, repeated restart, missing final part, backpressure, quota/error pause. Это regression sample sizes, не потолки. Generate large packet без production browser send; actual UI throughput/limits квалифицировать отдельным test budget. Для объёма и больших parts журналировать bytes counts, expected/seen IDs, hashes, cursor и причины unavailable. Disk full не даёт partially committed runnable job.

## Skills

Записать prepare/find/export и отдельно qualified browser scenario. Replay новый repo/alias/part count на unseen input; fault: stale adapter, permission growth, lost focus, unknown send, STOP, secrets boundary. Independent verifier сравнивает outcome, а не наличие записи «DONE». Optimize step list, повторить negative corpus и invariants. После adapter change проверить selective invalidation и сохранность всех failures.

## Receipt

Заполнить templates/RESULT_TEMPLATE.json и templates/DEVICE_RECEIPT.json: exact versions, input hashes, cases, commands, start/end, all attempts, evidence files/hash, outcome, limitations, owner и next evidence. Отдельные статусы: package validated / code tested / device qualified / selected UI qualified / installed / usable. Незакрытые criteria не преобразуются в PASS от успешного ZIP validator.
