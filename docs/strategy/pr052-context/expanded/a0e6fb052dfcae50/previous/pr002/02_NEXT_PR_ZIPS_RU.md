# Продолжение после PR-002

Следующий ZIP-003: полный portable context archive поверх verified metadata
из этого PR. Он должен получить payload chunks по точным snapshot/part identities,
писать staged parts с checkpoints, делать hash validation до atomic publication
и создавать offline index с relative source/part/gap links. Restart, duplicate
resume, disk-full и corrupted part проверяются отдельно. Ни число files,
ни количество chunks не ограничивать общим фиксированным потолком 20/39.

| Пакет | Следующий проверяемый прирост | Source tasks |
| --- | --- | --- |
| ZIP-003 | Payload ZIP, offline index и atomic resume | LAYA4-010 |
| ZIP-004 | Streaming Git enumeration за прежним output limit | LAYA4-003 |
| ZIP-005 | Полный format/eligibility ledger | LAYA4-004 |
| ZIP-006 | Related Python code/tests/contracts и SCC split | LAYA4-008 |
| ZIP-007 | JS/TS resolver и provenance adapters, отдельными срезами | LAYA4-005/006/007 |
| ZIP-008+ | Desktop/import/search/Task/Grok/update/voice/Core/Web3 | Полная очередь в previous/PR_001_NEXT_ZIPS_RU.md и source registries |

И ZIP-001, и ZIP-002 пока являются подготовленными implementation inputs;
actual build/merge/CI не наблюдались этим запросом. Перед следующим пакетом
проверить actual result предыдущих PR и вновь закрепить SHA/owners.

Все 160 source tasks и 164 feature definitions сохранены; broad dependencies
LAYA4-009 не переобъявлены закрытыми. Raw chunk map использует existing dispositions
и явный NOT_GENERATED graph, поэтому grouping/goal packet policy пока открыты.
Manifest-backed context пригоден для следующих Studious research briefs;
web3 execution требует своего registered qualification adapter и evidence.
