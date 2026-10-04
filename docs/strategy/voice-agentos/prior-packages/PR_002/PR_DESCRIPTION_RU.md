Title: feat(context): add complete repo manifests and chunk range lookup

Body template — заполнить после actual build:
Repo Review теперь имеет отдельный manifest всего COMPLETE pinned snapshot:
каждый source entry получает outcome, каждый captured chunk — content hash и
точные byte ranges. Бounded native pages и двусторонняя навигация позволяют
пройти весь индекс; streaming writer проверяет INDEXED-byte reconstruction
до публикации metadata bundle. Existing snapshot/chunk SQLite owner сохраняется.

Validation: [actual focused SQLite/native/UI/fault cases + required CI gates].
Actual base/head: [SHA]. Windows: [receipt или NOT_RUN].
Открыто: payload ZIP/resume, related dependency graph и per-goal packet coverage.
Незаполненный шаблон не является опубликованным PR или implementation claim.
