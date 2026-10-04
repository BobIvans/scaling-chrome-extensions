# Что добавлено
V1 сохранён как historical ZIP byte-for-byte: 18 направлений и исходный backlog.
V2: 24 направления RND-19–42, 20 workflow specs, 41 offline test.
V3: 12 уточняющих направлений RND-43–54, 12 новых сценариев WF-21–32, 48 новых proposed functions и 48 новых offline tests.

Итого: 54 направления (18 inherited + 36 detailed new/refinement cards), 32 workflow specs, 40 requirements, 273 proposed function entries; 89 unit tests. Это counts документации и lab, не число работающих desktop функций.

V3 реализует только offline subset: immutable multi-source observation journal, concurrent collection with explicit coverage/error, lineage-aware claim grouping, required evidence readiness, resource interference scheduling. 48 функций backlog — производственные integration work items, не алиасы всех методов lab.

В inherited lab исправлено закрытие SQLite connections; база синтетического demo и тесты остаются offline. Скрипты не скачивают модели, не открывают Chrome, не меняют repos и не запускают сделки.
