# Запланированный прирост №9

| Функция | Проверяемый результат |
| --- | --- |
| Original bytes | Exact BOM/CRLF/Unicode/unknown fields roundtrip by version hash |
| Source/extraction revisions | Metadata edits и adapter-key change имеют собственную историю |
| Full observed-node ledger | Structural, non-text, empty и обе branches видимы |
| Topology gaps | Missing refs, mismatch, current-node absent и cycles не угадываются |
| Selected scope reconciliation | Импорт B не меняет heads невыбранного A |
| Atomic persistence | Original/derived commit в existing SQLite; retry не дублирует версии |
| Error original retention | Invalid captured JSON сохраняется с ERROR extraction |
| Original inspection | Bounded metadata и verified file read exact version |

Это будущие code changes; пакет не отмечает их IMPLEMENTED. Существующие text
revisions/attachment inventory повторно не выдаются за новые функции.

Следующий №10: search/exact ranges/manual labels. Сначала проверить existing
search/store APIs и выбрать один adapter; PDF/Office/OCR и все ACTION5-07/08/09
не обещать целиком за час. Для search нужна version linkage из №9; normalized
reverse offsets, correction overlay и document ranges требуют своих slices.

После №9 отдельно остаются: DOM scroll/virtualized restart/full export relation;
remote branch visibility; generic file disposition registry/folder checkpoints;
attachments payload/local-file rights; measured large JSON RAM; source precedence;
extraction history pagination/retention; user correction overlays и evidence stale
invalidation LAYA4-011. Остальные 160 cards сохранены целиком.
