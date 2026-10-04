# Дополнительные параллельные сценарии V3

## WF-21 — Записывай мою работу с AI и репозиторием
Режим: `COMPLEMENTARY_UNION`.

Параллельно: voice intent transcript; visible DOM or UIA text; file/Git events; terminal test receipts.

Проверка: Per-channel source/version/sequence; не терять late events.

Запись результата: Наблюдения в отдельных append keys; общий контекст — отдельная derived view.

Fault injection: Один канал теряет связь после первых событий.

## WF-22 — Расшифруй команду без ошибки в repo name
Режим: `SELECTIVE_HEDGE`.

Параллельно: one microphone stream + primary ASR; secondary ASR on ambiguous critical span; repository vocabulary matcher.

Проверка: Critical slots and negation resolved; final intent revision.

Запись результата: Raw audio записывается один раз; hypotheses сохраняются отдельно.

Fault injection: Первый ASR перепутал not merge / merge.

## WF-23 — Разметь новый разговор
Режим: `COMPLEMENTARY_UNION`.

Параллельно: deterministic origin/time/hash tags; entity/goal model labels; source-linked code/evidence status check.

Проверка: Не promoted status без actual evidence.

Запись результата: Label proposals append-only; каноническая view сохраняет conflict.

Fault injection: Три пересказа одной идеи говорят DONE.

## WF-24 — Подготовь минимальный пакет для исправления
Режим: `REQUIRED_EVIDENCE_JOIN`.

Параллельно: pinned target function + dependencies; actual failure or blocker receipt; latest accepted scope/constraint.

Проверка: Минимальные required slots, отсутствие critical conflicts, current snapshot.

Запись результата: Первая immutable handoff version; отдельные delta после.

Fault injection: Полный импорт истории ещё идёт.

## WF-25 — Одновременно сохрани отчёт и подготовь код
Режим: `PARTITIONED_INDEPENDENT_EFFECTS`.

Параллельно: save unique report artifact; create patch in isolated worktree A; prepare independent source research.

Проверка: Resource read/write footprint intersection empty.

Запись результата: Разные effect resources могут commit параллельно.

Fault injection: Два исполнителя случайно выбрали один path.

## WF-26 — Дай AI недостающий интерфейс
Режим: `SCOPED_CONTEXT_RESPONSE`.

Параллельно: exact definition search; static references and tests; history for active revision.

Проверка: Requested symbol identity and source revision match.

Запись результата: Scoped response packet; никакого произвольного shell от модели.

Fault injection: Запрос от модели просит файл за allowed root.

## WF-27 — Объедини этот ZIP и весь текст цели
Режим: `COMPLEMENTARY_UNION`.

Параллельно: archive requirements; current user clarification; source docs and previous decisions.

Проверка: Preserve provenance/precedence; dedup lineage not erase history.

Запись результата: Новый versioned master spec; исходники не перезаписываются.

Fault injection: Legacy утверждает single writer для всей записи.

## WF-28 — Продолжи Studious qualification research
Режим: `REQUIRED_EVIDENCE_JOIN`.

Параллельно: local pinned repo graph; supported capabilities/blockers; selected prior goals/decisions; approved offline tests when available.

Проверка: Evidence bound to same source state, sender absent.

Запись результата: Handoff/research artifacts only; separate future code branch.

Fault injection: Readme proposal incorrectly read as runtime readiness.

## WF-29 — Проверь будущую версию навыка
Режим: `FIRST_VERIFIED_THEN_SINGLE_ACTIVATION`.

Параллельно: artifact origin and digest check; sandbox contract/negative tests; permission diff and compatibility review.

Проверка: All mandatory checks, version + code digest, approved capabilities.

Запись результата: Одна activation на version target; test candidates параллельно.

Fault injection: Новый skill требует доступ ко всему диску.

## WF-30 — Восстанови недостающие логи
Режим: `COMPLEMENTARY_UNION`.

Параллельно: durable process stdout receipt; test framework result file; approved CI job log download.

Проверка: Distinct source completeness, timestamp and run ID binding.

Запись результата: Не перезапускать исходную работу лишь ради получения логов.

Fault injection: Один log source пуст, второй содержит error tail.

## WF-31 — Продолжай работать, пока я пишу в Chrome
Режим: `PARTITIONED_INDEPENDENT_EFFECTS`.

Параллельно: context reads and indexing; code proposals in worktrees; one paused GUI route awaiting lease.

Проверка: No focus theft and scoped output writes.

Запись результата: Foreground only with user lease; background routes продолжаются.

Fault injection: Пользователь меняет active tab в середине GUI path.

## WF-32 — Проверь пару research snapshots для web3
Режим: `COMPLEMENTARY_UNION`.

Параллельно: approved market data source A; independent read-only source B; local protocol version/capabilities evidence.

Проверка: Chain/state/time/slot/commitment semantics compatible; stale/unknown explicit.

Запись результата: Readonly research only; no transaction signing/submission.

Fault injection: Быстрые ответы из разных моментов дают ложный edge.
