До изменения printable chunks бинарного source могли попасть в текстовый
контекст, а LFS pointer не различался с доступным payload. PR-005 вводит
versioned whole-source format facts, source-level text gate и read-only coverage
view для полного pinned ledger. Raw capture, text eligibility, metadata-only
entries и внешние payload gaps показываются отдельно.

Это шаблон: заменить validation фактическими командами/results после внедрения.
Design package checks не являются code tests; broad LAYA4-004 остаётся partial.
Долгие Native/Core операции, streaming index/large blobs, additional payload
acquisition и Windows qualification имеют открытые followups.
