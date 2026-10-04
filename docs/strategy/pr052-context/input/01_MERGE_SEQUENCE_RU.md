# Фактическая последовательность merge

Репозиторий: [BobIvans/scaling-chrome-extensions](https://github.com/BobIvans/scaling-chrome-extensions). Снимок main: `7253c40398905967ade0541717bcbfac25fec5b9`.
Дата всех строк ниже — 04.10.2026; время Europe/Riga (UTC+3). `merged_at` взят из GitHub;
каждый merge SHA также проверен как ancestor текущего main и совпадает с first-parent историей.
GitHub PR number и roadmap package number — разные пространства нумерации.

| Порядок | GitHub PR | Roadmap | Время Рига | Merge SHA |
|---|---|---|---|---|
| 1 | [38](https://github.com/BobIvans/scaling-chrome-extensions/pull/38) | 001 | 13:04:33 | `426f60b077fb` |
| 2 | [39](https://github.com/BobIvans/scaling-chrome-extensions/pull/39) | 002 | 13:29:52 | `57885d4ede3a` |
| 3 | [40](https://github.com/BobIvans/scaling-chrome-extensions/pull/40) | 003 | 13:46:27 | `3abd9e6b37d9` |
| 4 | [41](https://github.com/BobIvans/scaling-chrome-extensions/pull/41) | 004 | 14:32:08 | `9fbadef2714f` |
| 5 | [44](https://github.com/BobIvans/scaling-chrome-extensions/pull/44) | 009 | 15:51:12 | `8414ce4bda66` |
| 6 | [42](https://github.com/BobIvans/scaling-chrome-extensions/pull/42) | 005 | 16:14:49 | `e6af765dcb94` |
| 7 | [45](https://github.com/BobIvans/scaling-chrome-extensions/pull/45) | 008 | 16:44:34 | `1a528efc08f5` |
| 8 | [43](https://github.com/BobIvans/scaling-chrome-extensions/pull/43) | 007 | 17:06:57 | `b56ab2561975` |
| 9 | [46](https://github.com/BobIvans/scaling-chrome-extensions/pull/46) | 006 | 17:31:11 | `eb99d1c2cbc0` |
| 10 | [47](https://github.com/BobIvans/scaling-chrome-extensions/pull/47) | 012, 013 | 18:27:18 | `8ad12c9f3e43` |
| 11 | [48](https://github.com/BobIvans/scaling-chrome-extensions/pull/48) | 018, 019 | 18:55:34 | `d897598af606` |
| 12 | [50](https://github.com/BobIvans/scaling-chrome-extensions/pull/50) | 014, 015 | 19:21:37 | `b0a06f26106c` |
| 13 | [53](https://github.com/BobIvans/scaling-chrome-extensions/pull/53) | документы общего roadmap | 19:32:00 | `ccf73e747e67` |
| 14 | [49](https://github.com/BobIvans/scaling-chrome-extensions/pull/49) | 016, 017 | 20:49:14 | `eda82b4a1a54` |
| 15 | [51](https://github.com/BobIvans/scaling-chrome-extensions/pull/51) | 012, 013 | 21:24:13 | `7253c4039890` |

В roadmap это: **001 → 002 → 003 → 004 → 009 → 005 → 008 → 007 → 006 →
012/013 → 018/019 → 014/015 → документы #53 → 016/017 → continuation 012/013**.
Нет наблюдаемого merge завершённых 010/011; 020/021 остаётся open draft #52.
#51 — продолжение 012/013, а не новый roadmap package.

PR009 был отдельным ChatGPT-importer slice, а Python PR006 и JS/TS PR007 не требуют
merge друг друга. Их перестановка сама по себе не доказывает defect. Более поздние
пакеты имеют общий dependency DAG, поэтому ранний merge может доставить только часть
функций и оставляет full acceptance открытым. Переставлять или отменять merge только
ради числового порядка оснований нет.

Исходные машинные доказательства: `evidence/MERGE_TIMELINE.json`,
`evidence/raw/github_prs.json`, `evidence/DEPENDENCY_EDGES.json`.
