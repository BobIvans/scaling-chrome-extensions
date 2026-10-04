Golden данные синтетические. 50 entries: 46 INDEXED sources и 4 metadata gaps.
Исходные bytes для каждого INDEXED source находятся в raw/source_NNN.bin.
Manifest/source IDs не являются реальным production snapshot или Git commit.
Существующий revision digest сохранён в fixture формуле; это независимый
closed corpus для source-range checks, не integrated SCE runtime test.
tools/verify_golden.py проверяет полноту/bytes и отклонение десяти mutations.
При реализации создать actual SQLite/native tests с этими смысловыми случаями.
