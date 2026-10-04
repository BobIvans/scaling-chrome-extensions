# Следующий этап: typed roles → resumable mixed-effect Core plan

## Точный пробел

Текущий compiler выполняет DAG только одного effect class; role validator/Laya
adapter существуют, но не составляют сквозной planner/retriever/critic pipeline.
Repo prepare, packet compile и send сегодня требуют отдельных intents/jobs и
ручной передачи refs. Нужен один проверяемый план с output references между
steps, сохранённым прогрессом и общей revision/STOP/policy/target authority.

Primary owners: WS-018 (F004–F006/F009), WS-022 (F031/F039/F040), WS-020 (F050).
Точные source criteria и required cases брать из
`source/acceptance/CRITERION_COVERAGE.json`, `ACCEPTANCE_CASES.json` и
`source/plan/DEPENDENCIES.json`; не заменять их новым сокращённым списком.
Этот этап расширяет implementation, а не закрывает весь пакет.

## Сначала проверить prerequisites

- `main`, PR #49, #50 и #51: какие контракты действительно доступны/merged?
- `content-lab/context_packets.py`, `context_library.py`, `context_runtime.py`
  и recovery owner из merged PR #50 (финальная интеграция b0a06f2):
  immutable snapshot/manifest/all-parts cursor, source versions, hashes и scope.
- Existing `repo_context.py`/scan owner и jobs: долгий scan должен сохранять
  checkpoint и heartbeat. Native timeout не становится общим corpus ceiling.
- `action_runtime.py` outbox/binding: pin exact target/packet/intent/policy revisions.

Если canonical PR-014/015 packet owner недоступен, явно записать
BLOCKED_DEPENDENCY для его adapter. Typed proposal validation и pure planning
выполнять независимо. Не создавать несовместимую вторую packet library или
подставлять mocks как activation evidence.
В этой передаче owner code уже доступен; проверить его version/API и
scope-matched receipts перед новым adapter. Сам merge #50 не закрывает все
source criteria PR-014/015.

## Изменения

1. Добавить versioned EvidenceBundle/PlanProposal/CriticVerdict contracts с
   закрытыми полями, pinned source/intent hashes и отдельной provenance ролей.
   Retrieved content остаётся данными; planner/critic не расширяют capabilities,
   grants, recipient/root или verifier. Missing/conflicting sources → NEEDS_CONTEXT.
2. Расширить существующий compiler registered steps и typed output references.
   Вычислять topological order/semantic hash, проверять missing producer, cycles,
   output schema/version и capability-specific critical slots. Effect проверять
   по каждому step и полному preview; не ослаблять SEND mode/negation fences.
3. В той же SQLite сохранять step input/output refs, immutable result hashes,
   state/revision/operation keys и recovery outcome. Использовать тот же Core job,
   single writer и lease heartbeat. Resume переиспользует только verified compatible
   outputs; stale/unknown prerequisites блокируют downstream.
4. Связать prepare → actual immutable packet → selected binding/send adapters.
   Перед каждым effect перечитывать current revision/STOP/policy/source/target.
   Persist SEND_ARMED до UI dispatch. Crash после возможного send не допускает
   автоматического повторения; dependent import ждёт reconciliation.
5. Сохранять результаты partial steps/failures для следующего research/candidate
   skill, не выдавая qualification автоматически. Mixed-effect skill требует
   отдельного normal/unseen/fault receipt с точными scope/dependency hashes.
6. Добавить preview/status/correction/resume в существующем Desktop/Native,
   продолжая keyboard/text path и независимый STOP. Отдельный role worker не
   должен стать вторым effect executor.

## Independent checks

- Text/final corrected voice дают одинаковый semantic plan; оригинальная запись
  и transcription provenance сохраняются отдельно. Negation/repo/path/branch/
  destination/mode не теряются при canonicalization.
- Missing evidence, stale proposal, foreign output ref, cycle, unknown capability,
  mismatched schema или permission growth блокируются до effect.
- Реальный Git/SQLite local replay: scan/prepare → packet → paged manifest до EOF.
  Проверить tail parts и источник более чем из 20 документов без silent truncation.
- Restart после каждого step commit, correction между draft/arm, STOP при
  зависшем planner/ASR, source/policy/target drift и Core lease loss.
- Fault browser fixture: send committed, ack потерян, restart → UNKNOWN без
  duplicate invocation; actual selected Grok qualification остаётся отдельным gate.
- Existing history/scan/campaign routes и installed siblings сохраняются.
- Один store/job/lease owner подтверждён фактическими SQL/IPC outcomes.

Fixture PASS прикладывается только к своему case/scope. Windows microphone,
Narrator, Laya, actual Grok UI и attachments не становятся PASS от local replay.

## Дальнейшие части сохраняются

После этого этапа: real provider upload/history/finalization adapter; parameterized
skills и selective requalification; Windows/Dell benchmark corpus; installed Laya;
upstream data/import/recovery prerequisites и downstream product qualification.
Полный backlog и оригинальная нумерация остаются в `source/sources/numbered_roadmap/`
и `archives/`. Не считать уже merged #48 подтверждением всех release/campaign goals.
