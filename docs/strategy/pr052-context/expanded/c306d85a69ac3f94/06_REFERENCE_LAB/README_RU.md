# Offline reference lab — 89 synthetic unit tests

Python 3.11+; standard library only. Выполнено в Linux Python 3.13.5; Windows/Dell не запускались. Нет API, микрофона, ASR, Laya inference, реального браузера, репо-аудита или торговли.

Из `06_REFERENCE_LAB`:
```powershell
python -B -m unittest discover -s tests -v
python -B demo.py --output demo-output
python -B capture_demo.py --output capture-demo-output
```

## Проверяемые механики
`context.py`: исходные bytes/chunks/provenance + keyword handoff и явные omissions. Не streaming importer, не embedding/AST parser.
`race.py`: trusted coroutine candidates + delayed read/preparation hedge + supplied independent verifier + cooperative cancellation.
`ledger.py`: local SQLite revision/idempotency transaction; гарантия не распространяется на GitHub/сайт/блокчейн.
`observations.py`: multi-producer events, raw dedup с сохранением source observations, replay detection, complementary collection, errors/late arrivals, declared-lineage claim conflict preservation, required evidence readiness.
`resources.py`: offline conflict model над заранее canonical resource IDs; disjoint writes допустимы. Это не OS lock/fence manager, не path resolver и не security authority.

## Границы
Capture demo использует пять генераторов синтетических событий, не запись ПК. Bytes payload уже в RAM; large-media streaming не реализован. SQLite writes короткие, но всё равно синхронные; в production нужен отдельный I/O lane и existing store owner. Кооперативные trusted generators не заменяют killable process isolation.

Реальная privacy/authorization, encryption/secret scanning, storage quotas/retention, DPAPI/Keychain, third-party connector auth, source authenticity, dynamic graph, training и device benchmarking отсутствуют. Не помещать настоящие личные архивы/секреты в reference lab.

`readiness()` принимает externally-validated evidence slots от trusted coordinator. Это не «проверка мира» и не согласие исполнять операцию. `fuse_claims()` не присваивает VERIFIED фактам, сохраняет версии и conflicts. Source lineage не объявляется статистически независимой.

Синтетические sleep intervals нужны для тестирования порядка arrival, не являются замерами производительности. Никаких claim о 99% voice success или milliseconds на Dell из этих tests вывести нельзя.
