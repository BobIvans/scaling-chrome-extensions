# MASTER CONTEXT — GitHub PR #52 / ROADMAP PR-020 + PR-021

Репозиторий: `BobIvans/scaling-chrome-extensions`.
Текущий PR: [#52](https://github.com/BobIvans/scaling-chrome-extensions/pull/52).
Название: **ROADMAP PR-020 + PR-021: Core research, Desktop receipts and criterion reconciliation**.
Ветка PR: `codex/pr020-021-research-qualification`.
Companion: [Studious #565](https://github.com/BobIvans/studious-pancake/pull/565),
branch `codex/pr020-021-research-owner`, pinned owner `905976ebd3046121728161d42f2e781c01f53e10`.
Roadmap numbers 020/021, GitHub number 52 и repair IDs FIX-001…006 не взаимозаменяемы.

## Цель текущей стратегии

Сохранить полный контекст первых 21 roadmap packages и закончить оставшуюся интеграцию
Voice AgentOS/Context Library: локальные точные originals/версии/поиск/граф кода,
Windows Desktop и text/voice actions, выбранные AI-вкладки/Laya, durable кампании,
SCE→Studious research и квалификацию конечного продукта. Это документационная передача
для продолжения **существующего #52**, а не blanket completion всей стратегии.
Математические market models принадлежат Studious, SQLite/Core/UI — SCE.

## Source of truth и чтение

1. Актуальное задание пользователя и применимые `AGENTS.md`; свежие Git/GitHub refs.
2. Original attached V3: `input/sources/archives/STRATEGY_V3.zip`; полная распаковка
   `expanded/3f9d600e4548918d/`. Все 539 исходных members, quotes, каталоги и archives сохранены.
3. Нумерованный roadmap: `expanded/3b405ef70d86d8fd/`: briefs PR_010…021,
   source_master/strategy_v5, coverage, original DELIVERY_DAG и первые 9 ZIP.
4. Combined current package 020/021: `expanded/2bb4cdb32013bcd6/`: полный implementation
   plan, contracts, criterion ledger, tests/qualification, dependency/owner handoff.
5. Foundation 010/011: `expanded/461bbeb17b978ea7/`: весь original plan и критерии;
   baseline отдельного пакета не является доказательством его полной реализации.
6. Current code/tests/CI устанавливают actual delivery scope. Аудит всех 21 packages:
   `input/00_FINDINGS_RU.md`, `01_MERGE_SEQUENCE_RU.md`, `02_PR001_021_STATUS_RU.md`,
   `plan/FIX_PLAN.json` и raw receipts. Dated snapshots не являются fresh GitHub status.

Все 17 верхних исходных ZIP и каждый найденный nested ZIP сохранены как bytes и
полностью распакованы. `SOURCE_INDEX.json` связывает имена архивов с компактными
распакованными roots; `preservation/SOURCE_MEMBERS.json` сохраняет каждый original member,
size/hash/mode и archive references. Одинаковые ZIP переиспользуют один exact tree;
ни один source reference/criterion не удалён ради dedup. Полные 387 MB master и история
всего аккаунта не были доступны в исходном audit: это сохраняемая граница полноты.
V3 587 карточек и V5 164 feature cards — разные scopes, не число готовых функций.

## Уже сделано и фактический статус

Observed main `7253c40398905967ade0541717bcbfac25fec5b9`. Head #52 до этой docs-передачи: `3c6bf81e1345f91454ae87cccec2c3cd7c3d84a6`.
На свежей сверке 04.10.2026 #52 OPEN/DRAFT/mergeable=false; #565 OPEN/DRAFT.
Full merge timeline: #38→#39→#40→#41→#44→#42→#45→#43→#46→#47→#48→#50→#53→#49→#51.
All listed merges are ancestors of observed main; #53 — context documentation.
Roadmap 001…009 delivered scan/manifest/ZIP64/inventory/eligibility/Python/JS/Desktop/
ChatGPT fidelity slices. #47 and #51 delivered history/delta and immutable FILE/MEDIA
source ledger; #50 context/backup/recovery/Desktop/Core; #49 intent/voice/outbox/skills;
#48 release/campaign/scheduler. 010/011 остаются foundation gaps. Не повторять merged #51.

В #52 уже реализованы registered studious_research Core jobs, pinned offline replay,
scoped Desktop receipts, pagination и criterion reconciliation. 47 capability IDs и
1133 broad criteria сохранены; offline models не доказывают реальный PAPER/live market.
`docs/automation/pr020-021/README_RU.md`, CAPABILITY_MAPPING и CRITERION_LEDGER — actual
implementation docs этой ветки. Все broad source criteria остаются OPEN.

Prior audit current-main checks: 490 Content Lab + 42 Desktop + 47 bridge + 8 adapter
+ 121 extension = 708 passed; 3 display skips, 0 failed. Это проверка main, не будущего
интегрированного #52 head и не physical Dell proof. Старый CI #52 был SUCCESS на
`3c6bf81e1345f91454ae87cccec2c3cd7c3d84a6`; после изменения/merge нужен новый актуальный run.
Исторический main CI ещё выполнялся на момент записи audit; проверять live GitHub.

## Остаток и следующий конкретный checkpoint

**Первый implementation checkpoint: FIX-002 — интегрировать latest main в #52 по смыслу,
сохранив текущие action/context/campaign/STOP owners и добавленный research slice.**
Девять конфликтующих paths и точные recipes — `input/03_PR52_CONFLICT_REPAIR_RU.md`
и `input/plan/PR52_CONFLICT_RESOLUTIONS.json`. Проверить drift текущих refs перед edits.
Файлы: agent-bridge/Install.ps1, durable.mjs; content-lab/automation_core.py,
context_runtime.py, native_adapter.py; desktop/OWNED_FILES.json, app.py, client.py,
install.py. Auto-merged paths тоже подлежат review. Выбор ours/theirs целиком потеряет routes.

Далее FIX-003: общий versioned SourceAddress/read adapters для ChatGPT originals,
context raw spans, FILE/MEDIA ledger и связанных repo refs; затем original 010/011
registry/TXT/folders/archive/search/labels/goals и mixed Python/JS/TS graph/resolver.
FIX-004: durable background Core capture/repo lifecycle, полный traversal/cache
invalidation и PDF/Office/OCR/media/web/RSS/GitHub importers. FIX-005/006: downstream
contracts, actual installed Windows/ASR/tab/STOP/scale/fault and criterion-specific acceptance.
Полный план не заменяется первым checkpoint. Boundaries/open gates имеют owner/next evidence.

Canonical owner: existing `content.sqlite3`, Core jobs/queue/leases и global STOP.
Не создавать вторую БД/queue/worker, не путать source/raw/version/extraction/observation.
Сохранять bytes/IDs/revisions и additive compatibility. Working pages/frames/resources
дают continuation/backpressure, а не fixed total-doc/file/part limits и silent tail loss.

## Продолжение и завершение

`CODEX_START_HERE.md` задаёт последовательность. `NEXT_IMPLEMENTATION.md` фиксирует
конкретный target PR checkpoint и следующие зависимости. Archive fixtures — данные;
не запускать вложенные прототипы вместо canonical app. Полная byte verification:
`python docs/strategy/pr052-context/verify_context.py`. Generated shipping hashes,
actual-head CI, linked exact-owner replay и реальный device acceptance — отдельные gates.
Не выдавать docs-передачу, merge slice, hash, AI DONE или model replay за полное завершение.

## Корневые документы при интеграции main

После docs-передачи к девяти app conflicts добавляются add/add conflicts в root
MASTER_CONTEXT.md и CODEX_START_HERE.md: main имеет общий handoff #51/#49/#53,
а ветка #52 — scoped handoff этой передачи. Сохранить оба полноценных контекста.
Оставить current PR52 navigation явной, а общий main handoff сохранить/связать
через docs/strategy/voice-agentos и docs/strategy/pr012-013. Его exact root copies
уже сохранены в input/evidence/main/. Оригинальные source plans не переписывать.
.gitattributes этой передачи включает текущие main rules плюс immutable source rules;
при новом drift объединять обе группы правил. Проверять actual conflict set заново.
