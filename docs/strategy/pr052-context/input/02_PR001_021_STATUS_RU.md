# Сопоставление всех первых 21 roadmap packages

| Roadmap | Назначение | GitHub | Наблюдаемый статус |
|---|---|---|---|
| 001 | Полный repo scan | #38 | MERGED_IMPLEMENTATION_SLICE |
| 002 | Полный manifest и byte-range index | #39 | MERGED_IMPLEMENTATION_SLICE |
| 003 | ZIP64 export и atomic resume | #40 | MERGED_IMPLEMENTATION_SLICE |
| 004 | Streaming Git inventory | #41 | MERGED_IMPLEMENTATION_SLICE |
| 005 | Format eligibility и gaps | #42 | MERGED_IMPLEMENTATION_SLICE |
| 006 | Python SCC/groups | #46 | MERGED_IMPLEMENTATION_SLICE |
| 007 | JS/TS static relations | #43 | MERGED_IMPLEMENTATION_SLICE |
| 008 | Desktop stdio / Windows shell | #45 | MERGED_IMPLEMENTATION_SLICE |
| 009 | ChatGPT originals/revisions/node fidelity | #44 | MERGED_IMPLEMENTATION_SLICE |
| 010 | Единая библиотека источников: точный поиск, версии, метки, цели и импорт файлов/чатов | нет завершённого отдельного PR | NO_COMPLETE_DEDICATED_IMPLEMENTATION |
| 011 | Полный граф кода: JS/TS resolver, Python SCC, owners, tests, contracts и code smells | нет завершённого отдельного PR | NO_COMPLETE_DEDICATED_IMPLEMENTATION |
| 012 | Repo engine до конца: Core jobs, streaming, полные страницы, delta, CAS и resume | #47, #51 | MERGED_IMPLEMENTATION_SLICE |
| 013 | Импорт документов и внешних источников: PDF/Office/OCR, media, RSS/web и GitHub history | #47, #51 | MERGED_IMPLEMENTATION_SLICE |
| 014 | Долговременный контекст: AI packets, NEED_CONTEXT, retrieval, backup/restore и sync | #50 | MERGED_IMPLEMENTATION_SLICE |
| 015 | Полноценный Windows desktop: installer, единый Core, capabilities, templates и STOP | #50 | MERGED_IMPLEMENTATION_SLICE |
| 016 | Текст и голос → действия: IntentSpec, Laya, ASR, corrections и planner/retriever/critic | #49 | MERGED_IMPLEMENTATION_SLICE |
| 017 | Выбранные AI-вкладки и навыки: Grok delivery, outbox, recovery и demonstration replay | #49 | MERGED_IMPLEMENTATION_SLICE |
| 018 | Код → проверенный PR/merge → установленное обновление с canary и rollback | #48 | MERGED_IMPLEMENTATION_SLICE |
| 019 | Долгие параллельные кампании и R&D: scheduler, leases, budgets, resume и next briefs | #48 | MERGED_IMPLEMENTATION_SLICE |
| 020 | SCE → Studious: datasets, qualification, replay/paper и новые web3 research packs | #52 | OPEN_DRAFT_CONFLICTING |
| 021 | Закрытие продукта: Windows scale/fault qualification, польза, стоимость и все критерии V5 | #52 | OPEN_DRAFT_CONFLICTING |

17 из 21 номеров имеют хотя бы один merged implementation slice. Это не 17 полностью
квалифицированных product packages. 010/011 имеют foundations в baseline/#43/#46/#50/#51,
но полного отдельного завершения не найдено. 020/021 — существующий SCE #52 и companion
[Studious #565](https://github.com/BobIvans/studious-pancake/pull/565), оба open draft.

Для первого десятка полный остаток читать в original source plans и actual receipts;
для 010…021 все 36 workstreams и next evidence сохранены в `evidence/HISTORICAL_WORKSTREAM_STATUS.json`.
Статусы OPEN_PR_PARTIAL этого исторического файла не являются current GitHub states.
Свежий слой `evidence/PR001_021_STATUS.json` устанавливает текущее состояние merge,
не переписывая исходные requirement statuses.
