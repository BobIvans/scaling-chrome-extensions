# Universal Long-Horizon Laya Agent — Goal Continuation Kernel V2

## Цель

Система должна принимать практически любой наблюдаемый кусок данных как новый source state и продолжать достигать пользовательскую цель дольше одного model turn:

`GOAL → OBSERVE/INGEST → STATE → FRONTIER → LAYA ROUTE → PLAN → ATOMIC EFFECT → VERIFY → CHECKPOINT → REPLAN → ...`

Laya — быстрый System-1 router/ranker, а не генератор свободного плана и не permission authority. Grok/Grok Build/другой generative provider предлагает новые планы, гипотезы, код и tool candidates. Registered executors являются руками.

## Three-horizon mental frame

### H2 Strategy horizon

Milestones и альтернативные ветки на десятки шагов вперёд. Это гипотезы, а не уже разрешённые действия.

Пример:
1. понять repo;
2. найти root cause;
3. подготовить patch;
4. проверить;
5. PR;
6. merge;
7. build;
8. install;
9. qualify.

### H1 Near frontier

Следующие 3–20 candidate actions с dependencies, expected information gain, cost, risk, resources и verifier.

Laya быстро ранжирует frontier.

### H0 Atomic next step

Только один effectful шаг (или bounded batch независимых read-only шагов) допускается к фактическому исполнению. Перед каждым effect H0 пересобирается из текущего evidence.

Так можно принять от Grok длинный 20-шаговый план, но не исполнять слепо все 20 шагов после изменения мира на шаге 2.

## Почему Laya может быть быстрее человека

Laya получает компактный `DecisionState`, а не весь raw corpus. В нём:
- цель/acceptance;
- текущие milestones;
- open gaps;
- candidate action summaries;
- latest evidence delta;
- resource/target availability;
- error/no-progress signals;
- budgets/deadlines.

Она может batch-классифицировать:
- какой frontier item наиболее полезен;
- какие read-only ветки можно параллелить;
- нужен ли новый context;
- является ли ответ AI completion claim или action proposal;
- нужен ли tool gap;
- достигнут ли no-progress;
- должен ли loop abstain/replan.

## Any-source principle

Любой вход сначала превращается в `AnySourceEnvelope`:
- voice/text;
- Grok message;
- attachment;
- clicked link;
- downloaded file;
- repo snapshot/delta;
- test/CI output;
- terminal result;
- GitHub receipt;
- API response;
- Windows app observation;
- image/media derivative;
- user correction.

Raw data сохраняется отдельно. Laya получает bounded decision projection.

## Пример: документ внутри Grok conversation

1. Observer видит attachment и сохраняет element/message/conversation identity.
2. Runtime создаёт `ArtifactCandidate`.
3. Laya отвечает на typed questions: relevant? open/download? expected value? ambiguous?
4. Policy разрешает только preconfigured read/download scope.
5. Browser executor получает UI lease и заново проверяет exact tab/account/conversation/message/element.
6. Выполняется `open_allowed_link` или `download_allowed_artifact`.
7. Download monitor подтверждает final file, origin, MIME, size и hash.
8. Raw artifact попадает в canonical library.
9. Parser создаёт derivatives + coverage/gaps.
10. GoalState обновляется.
11. Frontier перестраивается.
12. Laya выбирает: спросить Grok, прочитать ещё документ, проверить repo, запустить test, создать skill gap, ждать события или завершить.

Если attachment открывает новую вкладку, она получает отдельный SourceBinding; это не автоматически новый action target.

## Multi-step instructions from Grok

Grok может вернуть:
- `PlanProposal`;
- DAG;
- checklist;
- code task;
- exact source requests;
- future milestones.

Importer обязан:
1. сохранить original response;
2. выделить candidate steps;
3. связать каждый step с capability ID либо `GapSpec`;
4. построить dependencies/resources/verifier;
5. пометить future steps как TENTATIVE;
6. ранжировать H1;
7. допускать только H0;
8. после каждого evidence delta инвалидировать stale future assumptions;
9. продолжать без нового user prompt, пока действует сохранённый GoalGrant и нет STOP/BLOCKED/UNKNOWN.

## Autonomous continuation states

- `RUNNING`
- `WAITING_FOR_EVENT`
- `WAITING_FOR_QUOTA`
- `WAITING_FOR_RESOURCE_LEASE`
- `NEEDS_CONTEXT`
- `NEEDS_REPLAN`
- `CAPABILITY_GAP`
- `NEEDS_BINDING`
- `BLOCKED`
- `UNKNOWN_EFFECT`
- `PAUSED_BY_USER`
- `ACCEPTANCE_VERIFIED`
- `STOPPED_BUDGET`
- `STOPPED_NO_PROGRESS`

## No-progress controller

После каждого цикла вычислять `ProgressDelta`:
- закрытые acceptance clauses;
- новые verified evidence refs;
- уменьшение open gaps;
- новая capability;
- новая source coverage;
- changed blocker.

Если N итераций не дают meaningful delta:
1. прекратить повторение текущего route;
2. запросить альтернативный planner proposal;
3. расширить context только в пределах scope;
4. попробовать другой qualified transport/executor;
5. сформировать CapabilityGap;
6. либо STOP_NO_PROGRESS с конкретным blocker.

## Parallel speedup

Можно параллельно выполнять независимые:
- repo reads/indexing;
- source downloads;
- tests;
- static analysis;
- history/CI reads;
- alternative research;
- context prefetch.

Нельзя параллельно писать в один mutable composer/tab, Git branch, install target или другой exclusive resource.

Foreground UI automation ждёт resource lease; background read lanes продолжаются. Это сохраняет старый сценарий «продолжай работать, пока я пишу в Chrome».

## Stop / resume

STOP fence находится вне Laya/provider. Resume создаёт continuation, связанную с предыдущим run, и выполняет только eligible unfinished work после reconciliation.

## Universal goal definition

Поддержка «любой цели» означает:
- система может принять любую цель как `GoalSpec`;
- найти известные capabilities;
- декомпозировать через planner;
- создать GapSpec для неизвестного;
- квалифицировать новый tool;
- продолжить исходную цель.

Это НЕ означает бесконтрольный arbitrary shell/click. Реальные эффекты существуют только через registered + qualified executors.
