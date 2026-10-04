# Следующий пакет №5

ZIP №3 строится отдельно: LAYA4-010, полный captured context export, offline
index, verified parts и rebuild ZIP после сбоя. Статус известен только по
сообщению пользователя. Этот пакет не предполагает его completion/merge.

| Номер | Работа | Состояние |
| --- | --- | --- |
| ZIP-001 | Scan controller, pages и pause/continue | Input prepared; implementation not verified |
| ZIP-002 | Manifest и source-to-chunk range index | Input prepared; implementation not verified |
| ZIP-003 | Payload archive, offline index, export recovery | User-reported in progress in other chat |
| ZIP-004 | CLI streaming inventory и atomic ledger | This prepared input; partial LAYA4-003 |
| ZIP-005 | Formats, explicit gaps и eligibility | Next candidate; LAYA4-004 |
| ZIP-006 | Related Python code/tests/contracts и SCC groups | Candidate; LAYA4-008 |
| ZIP-007 | JS/TS resolver/provenance, small separate PRs | Candidate; LAYA4-005/006/007 |
| ZIP-008+ | Desktop/import/search/Task/Grok/update/voice/Core/Web3 | Existing full queue preserved |

Не перенумеровывать ZIP-003/004, чтобы не пересечься между чатами. Перед ZIP-005
получить actual result либо сохранить статус UNVERIFIED; не выдумывать PR links.
LAYA4-004 должен использовать existing outcomes для LFS pointers/payload gaps,
links/submodules, encodings, oversized/protected paths, без исполнения source.
Не расширять его до large blob streaming, graph или desktop.

Открыто после часового PR-004: registered long-running repo inventory job
в existing Core с Native START/STATUS/cancel/reconciliation, streaming exact
Git index binding, real Windows device qualification. Номера ZIP для этих
follow-ups пока не назначены; whole LAYA4-003 остаётся открытой.
Все 160 roadmap tasks доступны в plan/ROADMAP_DISPOSITION.json и исходном
ALL_TASKS_V5.json, вся дальнейшая очередь — previous/PR_001_NEXT_ZIPS_RU.md.
