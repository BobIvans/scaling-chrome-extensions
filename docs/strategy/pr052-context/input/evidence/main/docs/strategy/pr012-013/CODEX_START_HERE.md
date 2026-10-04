# CODEX START HERE — ROADMAP PR-012 + PR-013 / GitHub PR #51

**Unified source lifecycle: durable repo jobs, delta/CAS and provenance-aware importers.**
Repo `BobIvans/scaling-chrome-extensions`, active continuation
[PR #51](https://github.com/BobIvans/scaling-chrome-extensions/pull/51), branch
`codex/pr012-013-source-ledger-continuation`. Roadmap №012/013 — не GitHub №12/13.
#47 уже merged; весь combined package остаётся partial.

## Начало

1. Прочитать applicable `AGENTS.md`, этот файл и
   [MASTER_CONTEXT.md](MASTER_CONTEXT.md). Сохранить current user scope №012/013.
2. `git fetch origin`; проверить live main и head/state #51. Продолжать существующую
   ветку; если merged — только remaining stage от свежего main. Сравнить actual code
   с `audit/REPOSITORY_AUDIT.json`, сохранить более свежие изменения и не force-push.
3. Из root проверить оба preservation packages:
   `python docs/strategy/pr012-013/verify_integrity.py` и
   `python docs/strategy/voice-agentos/verify_integrity.py`.
4. Прочитать **весь** scoped input, а не только эту навигацию:
   `input/00_START_HERE_RU.md`, `IMPLEMENTATION_RU.md`, `PR_PLAN.json`,
   `contracts/UNIFIED_SOURCE_CONTRACT_V1.json`, `WORKSTREAMS.json`,
   `ACCEPTANCE_CASES.json`, `CRITERION_COVERAGE.json`,
   `sources/ORIGINAL_CARDS.json`, оба `ORIGINAL_PR_012/013_BRIEF.json` и
   `ORIGINAL_PR_012/013_PROMPT_RU.txt`, `PROVENANCE.json`, `PARALLEL_HANDOFF.json`.
   Plan-only `input/CURRENT_VS_PLANNED.json` — historical, текущий статус в `audit/`.
5. Прочитать `audit/CURRENT_VS_PLANNED.json`, `audit/CRITERION_STATUS.json`,
   `verification/LOCAL_VALIDATION.json`,
   `docs/automation/roadmap-pr012-013-progress.md`,
   `docs/automation/pr012-013-source-ledger.md` и
   `docs/strategy/voice-agentos/handoff/NEXT_STAGE.md`.
   Upstream foundations: `voice-agentos/roadmap/briefs/PR_010.json`, `PR_011.json`,
   DAG, точные related V5 cards. Full unrelated №010 backlog остаётся у своего owner.

## Первый implementation checkpoint

**Unified SourceAddress + точные read adapters для ChatGPT, context spans и
FILE/MEDIA ledger; затем зарегистрированный durable Core repo/capture lifecycle.**

- Owners: `content_lab.py`, `source_ledger.py`, `context_library.py`,
  `context_packets.py`, `context_runtime.py`, `automation_core.py`, `workflow_state.py`.
- Reuse repo owner `repo_context/repo_scan/repo_inventory/repo_history/repo_archive`;
  не переписывать готовые inventory, ZIP64, history/delta pages.
- Сначала ADR/contract и additive migration rehearsal; единые source/version/
  observation/extraction distinctions. Не создавать второй DB writer/scheduler.
- Bounded page traversal до EOF, exact pinned revision/namespace/range/hash;
  binary original явно отличается от derived text. Исторические references читаются
  после migration и restart, UNKNOWN mapping остаётся видимым.
- Core intent/request digest, committed cursor, lease fence, pause/resume,
  STOP/cancel/restart/drift и job progress; manual Desktop STEP этим не считается.
- Native/Desktop integration и shipping manifests при runtime changes.
- Acceptance: same bytes/two origins, stable-key rename, changed bytes/new version,
  corrupt hash/namespace/range, >20 versions/parts tail, old DB, double START/ack loss,
  partial crash, terminal cancel/late worker, scope drift. Новый extraction adapter
  не объявляется готовым по успешному raw capture.

## Полный порядок после checkpoint

1. WS-002 Core lifecycle и независимые R01–R03.
2. WS-003 оставшиеся full-page selection/summary/export consumers, atomic fault recovery
   и R04–R05. Старые `LIMIT 20`/`[:20]` consumers audit обязателен.
3. WS-006 limited CAS/derived cache, declared scopes, graph-based invalidation и R06–R07;
   full №011 graph gate нельзя заменить narrow fixed-part delta.
4. WS-009 PDF/Office/OCR и D01–D02; WS-010 saved media/ASR и M01–M02;
   WS-011 read-only web/RSS/GitHub history и W01–W02.
5. Cross-source exact original X01, installed Dell Windows scale/fault X02,
   additive migrations, flags/rollback и compatibility handoff №010/011/014/015/016.

Сохранять minimal ImporterV1 здесь; №016 extension не prerequisite.
Проверять актуальные primary docs перед выбором изменяемых parser/ASR/API dependencies.
Внешние API tests выполнять только с существующими authorized profiles.

## Evidence и завершение

Сначала rerun relevant existing tests; full required gates определяет
`.github/workflows/deterministic-core.yml`. Проверить actual-head CI.
Local 13 tests в этой передаче — scoped baseline; Windows installed NOT_RUN.
Ни один из 101 broad criteria здесь не отмечен DONE по одному component test.

После каждого проверенного stage обновить current-vs-planned, criterion ledger,
changed functions/schema, independent receipts и next actions. Original `input/`
и `originals/` immutable; не переписывать их status поля и не удалять требования.
Весь parent scope остаётся OPEN, пока полного applicable evidence нет.
Current request подготовил передачу стратегии; выполнение кода — следующий
запрос Codex. Merge gate в исходной стратегии не означает, что эта передача уже
слила #51 или закрыла весь №012/013.
