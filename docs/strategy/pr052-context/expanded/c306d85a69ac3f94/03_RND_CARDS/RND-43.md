# RND-43 — Multi-producer observation fabric
**Статус:** new_detail_of_capture; proposed R&D, не установленная интеграция.

## Зачем
Много способов записи одного процесса должны дополнять друг друга, а не ждать первого победителя.

## Устройство
Append-only streams с ключом session/producer/sequence; bytes dedup отдельно от observation identity; один логически связанный capture session.

## Эксперимент
Один channel отвечает мгновенно, второй поздно, третий обрывается после части данных.

## Acceptance
Сохранить ранние и поздние события; ошибку и неполноту явно отобразить.

## Функции
- `open_observation_session()`
- `append_source_observation()`
- `correlate_observation_streams()`
- `preserve_late_channel_evidence()`

Requirements: REQ-033 REQ-007. Sources: S24 S25.
