# Новые запланированные функции №6

| Функция | Проверяемый результат |
| --- | --- |
| 1. Adapter к source-wide eligibility №5 | Binary/LFS/ineligible bytes не используются для code/text interpretation |
| 2. Python static graph reuse | Qualified endpoints, exact hash/line anchors, unresolved statuses сохранены |
| 3. Logical SCC groups | Цикл остаётся единым logical group, unknown sources видимы |
| 4. Stable source/group IDs | Unrelated addition не перенумеровывает старые logical IDs |
| 5. Related tests/contracts | Static imports, declarations и name candidates имеют разные evidence classes |
| 6. Full group membership ledger | Одна row на каждый source entry, gaps включены |
| 7. Bounded group-part planning | Every captured raw chunk referenced once, empty/binary preserved, no tail cap |
| 8. Neighbour/cross-group references | Prev/next segments и relation locator для перехода к соседним sources |
| 9. Derived export / offline navigation | Versioned sidecar catalog, generated relative links и scoped proof |

Это scope будущего code PR, не девять уже внедрённых функций. Broad strategy
и 160 original tasks сохранены в source registries. Existing Python graph
не выдаётся за вновь реализованный parser. Related-test import не значит
observed coverage; capability discovery/activation здесь отсутствует.

Следующий №7 по исходной очереди: scoped JS/TS resolver/provenance, LAYA4-005/006/007.
Сначала выбрать один adapter и actual gaps после №6, чтобы часовой PR оставался
управляемым. Не включать все три broad tasks в один обещанный час автоматически.

Отдельные follow-ups, reported из №4: registered Core job для long Git inventory
и scalable index verification; exact implementation/docs не наблюдались здесь.
Foreground grouping не закрывает эти направления. После actual №5 result
нужен interop regression №5→№6 и explicit qualified code/text map.
