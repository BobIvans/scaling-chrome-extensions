WEB3 QUALIFICATION R&D — 2026-10-03

Этот модуль добавляет проверяемый путь от данных к квалификации бота. В нём нет
подписи транзакций, отправки в сеть, автотрейдинга, RPC клиента или установленной
фоновой автоматизации. 28 workflow JSON — спецификации будущих адаптеров.
qualification.py — работающий локальный офлайн verifier пяти форматов артефактов.

Что именно уже работает

1. Проверка плана и зависимостей этапов: циклы, неизвестные адаптеры, неподдержанные
   критерии и дубликаты отклоняются.
2. Сравнение полного binding: exact Git revision; SHA256 config, input manifest,
   environment; network/genesis; block или slot anchor; finality; provider/model
   identity и version; точные версии toolchain.
3. Проверка сохранённых байтов по SHA256 и размеру; только пути внутри evidence root.
   Absolute/drive/UNC/traversal/symlink paths не принимаются. Реальные исходные пути
   репозитория при этом остаются в manifest и не используются как адрес для записи.
4. Инвалидация по plan hash, binding, истечению TTL, будущему времени, неверному
   порядку timestamps и неоднозначным нескольким receipts одного этапа.
5. inventory_diff.v1 сверяет path + ordinal + bytes + hash двух manifest без потери
   совпадающих basename. Это сравнение двух manifests, а не доказательство, что
   внешний источник уже перечислил всё: исходный source manifest надо получать
   проверенным inventory adapter.
6. junit_xml.v1 читает testcase, failure/error/skipped, обязательные названия,
   suite-level errors и сверяет агрегатные счётчики с реальными testcase records.
   Пустая suite, скрытая пропущенная testcase, skip и успех в произвольном boolean
   не подменяют выполненный тест. Название теста само не доказывает силу assertions.
7. economics_samples.v1 пересчитывает принятые candidates по целым atomic units:
   proceeds - principal - flash fee - swap fee - network fee - slippage reserve -
   other cost; сравнивает quote age и заданный min net. В producer contract proceeds
   означает сумму до перечисленных вычетов. Нельзя дважды вычитать уже удержанный
   fee. Конвертация разных активов, полнота cost model, реальность возможного fill
   и будущая прибыль этим арифметическим verifier не доказываются.
8. observation_window.v1 проверяет число записей, длительность, gaps, provider ids,
   источник/время, network/finality и нулевые recorded sign/send counters. Времена
   должны лежать в интервале процесса receipt. OFFLINE_REPLAY и
   REAL_MARKET_PAPER_OBSERVATION — разные типы данных. Нулевые поля журнала ещё не
   доказывают отсутствие внешнего signer: это надо обеспечивать execution sandbox.
9. stop_latency.v1 вычисляет latency из monotonic ns и проверяет запись запрещённых
   dispatch после trigger; требует перечисленные виды fault и количество probes.
10. Статусы этапа own_status и status с зависимостями разделены. Локальная проверка
    может пройти, а зависимости остаться NOT_RUN. Следующий этап тогда не eligible.

Смысл статусов

TRUE: заданные predicates выполнены на предоставленных согласованных артефактах.
FALSE: наблюдается провал теста/критерия, ненулевой exit code или нарушение SHA.
UNKNOWN: материал не позволяет судить — binding устарел/не совпал, артефакт отсутствует,
не тот producer/schema, время ошибочно, JSON/XML противоречив или источник неоднозначен.
NOT_RUN: для этапа не передан receipt. Это не FALSE и не успешный «пропуск».

Граница доверия

SHA256 подтверждает соответствие байтов указанному digest, а не честность того, кто
создал обе записи. pinned producer id/version/binary hash здесь проверяются только
как заявленные поля: процесс этого producer не запускается и подпись/attestation
не удостоверяется. Поэтому report ВСЕГДА содержит attestation_authenticated=false,
producer_authenticity=UNKNOWN, external_chain_truth=UNKNOWN, ready_for_live=false,
live_authorized=false. Никто не должен превращать configured_predicates=TRUE в
«бот безопасен, можно торговать». Будущий trusted collector должен самостоятельно
получать runner version/digest, argv, environment, stdout/stderr, точную revision,
source data и execution scope, с защищённым журналом и проверяемой подписью.

Не менять evidence directory во время проверки: hostile concurrent filesystem
mutation и полноценная cryptographic attestation не решены в этом прототипе.
Большие raw blobs хешируются потоково. JUnit XML, JSON plan/receipts и manifest
индексы сейчас находятся в памяти: для огромных campaigns нужна последующая
streaming/SQLite адаптация. Полноту лога при аварии надо устанавливать по отдельным
cursors/sequences. Это не «безграничная память» и не молчаливое усечение.

Запуск на Windows 11

Python 3.11+; дополнительные библиотеки не нужны. Из папки web3:

py -3 -m unittest discover -s . -p "test_*.py" -v

Синтетический пример (одной строкой):
py -3 qualification.py --plan examples/plan.SYNTHETIC.json --evidence-root examples --receipt examples/receipt_inventory.SYNTHETIC.json --receipt examples/receipt_unit.SYNTHETIC.json --receipt examples/receipt_cost.SYNTHETIC.json --receipt examples/receipt_observation.SYNTHETIC.json --receipt examples/receipt_stop.SYNTHETIC.json --now 2026-10-03T17:00:00Z --output REPORT.REPRODUCED.json

Только пример использует --now, чтобы повторить историческую проверку. В реальной
проверке не передавать --now: используется текущее UTC, старые receipts станут UNKNOWN.
Файл examples/REPORT.SYNTHETIC.json относится исключительно к сгенерированным fixtures;
он не является результатом запуска studious-pancake, SCE или настоящего рынка.
Без --receipt этапы показывают NOT_RUN. Код возврата: 0 — configured predicates TRUE,
2 — не все этапы квалифицируются, 3 — неверный входной план/JSON или путь отчёта. Даже код 0 не выдаёт
разрешение на live. --output сохраняет только НОВЫЙ файл ВНЕ evidence root и не может
совпадать с plan/receipt input. Повторный запуск требует нового имени отчёта.
Публикация использует atomic hard link рядом с временным файлом; файловая система
без hard links вернёт ошибку без перезаписи данных. CLI сам ничего не запускает.

Как довести до интеграции

A. Сначала выбрать фактическую цепочку и runtime по исходникам flashloan-бота,
   lockfiles и текущим контрактам/программам. В этой работе не выполнен полный аудит
   bot repo. Исторические записи про Solana не позволяют назначить EVM adapter.
B. Добавлять handlers в существующего владельца SCE automation_core.py и canonical
   очередь. Не создавать конкурирующий production scheduler с новой копией истины.
C. Laya ранжирует контекст, выбирает проверенный template и abstains при недостатке
   данных. Генерацию кода, shell/browser исполнение, проверку и live полномочия
   предоставляют отдельные явно типизированные capabilities; это не функции Laya.
D. Для каждого шага: exact inputs → isolated worktree → runner artifacts → verifier
   → receipt → status. Cache только по полному dependency fingerprint. Изменение
   кода/config/network/provider/model/toolchain лишает старый результат актуальности.
E. После offline replay — отдельное реальное paper observation без signer. Далее
   operational faults, stop/recovery, Windows device и release/rollback qualification.
   Canary/live остаются отдельными reviewed scopes с конкретным сроком, network,
   assets, action set и лимитами. В данном пакете эти исполнители отсутствуют.
F. MarginFi остаётся PAUSED по найденному историческому ограничению. Repayment
   сценарии lender-neutral; возобновление конкретного lender не предполагается.

28 workflow specifications

01 repo inventory; 02 reproducible build; 03 static smells; 04 unit/boundary cases;
05 fuzz+corpus; 06 stateful invariants; 07 pinned fork/local validator; 08 replay;
09 read-only market collection; 10 provider comparison; 11 oracle/quote freshness;
12 fees/costs; 13 route atomicity; 14 slippage/liquidity stress; 15 lender repayment;
16 actual market paper observation; 17 faults; 18 Dell Windows device qualification;
19 stop/pause; 20 release/migration/rollback; 21 canary plan; 22 live monitoring SPEC;
23 stale invalidation; 24 incident replay→regression; 25 qualification packet;
26 requirement coverage holes; 27 R&D experiment scheduling; 28 voice goal binding.

Каждый JSON содержит inputs, steps, outputs, dependencies, candidate criteria,
idempotency, Laya role и статус SPEC_NOT_EXECUTABLE. Исполним только qualification.py.
Поля min/max в examples — демонстрационные числа для tiny fixtures. Они не являются
торговыми лимитами, рекомендациями или нормативом достаточного тестирования.
EXPERIMENT_MATRIX.csv: 18 проектов экспериментов, actual execution для всех NOT_RUN.
Юнит-тесты verifier не считаются выполнением этих экспериментальных кампаний.

Проверенные первичные источники, 2026-10-03

https://eips.ethereum.org/EIPS/eip-1898
EIP задаёт blockHash и requireCanonical для ряда EVM state query методов. Нужно
проверять реальную поддержку выбранным provider. Number/«latest» не заменяют
зафиксированную идентичность состояния при сравнении нескольких источников.

https://ethereum.org/developers/docs/apis/json-rpc/
Справочник Ethereum RPC. Применим при подтверждённом EVM runtime конкретного бота.

https://solana.com/docs/rpc
Solana использует cluster-specific endpoints и commitment processed/confirmed/
finalized. Это отдельная модель данных; slot/program state не следует механически
подменять EVM block/contract терминами.

https://getfoundry.sh/forge/invariant-testing
Официальная индексированная документация описывает runs/depth и invariant targets.
Прямое открытие страницы инструментом вернуло unsupported markdown content-type;
получен индексированный текст первичного сайта. Приведённые здесь критерии coverage
и operational qualification — наш проектный выбор, а не цитата о гарантии безопасности.
