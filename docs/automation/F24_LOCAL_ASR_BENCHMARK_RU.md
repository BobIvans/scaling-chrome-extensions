# F-24: локальный RU/LV ASR benchmark

## Подтверждённый gap

`content_lab.py::transcribe_file` уже владел локальным CPU INT8 inference и
запрещал model download через `local_files_only=True`, но не существовало строгого
набора consented cases, WER/action scoring, p95/RAM receipt или правила сохранять
неизмеренное как unknown. Реальных пользовательских audio fixtures и локальной
модели в репозитории нет.

## Реализация

`asr_benchmark.py` принимает только ограниченный `occ.asr-benchmark-suite.v1`:

- `owned_or_licensed=true` и `benchmark_use_authorized=true` обязательны;
- 1–100 RU/LV cases с относительным локальным audio path;
- ручной transcript reference и необязательная зарегистрированная action phrase;
- duplicate keys/IDs, неизвестные поля/языки, symlink/path traversal, oversized и
  изменившиеся inputs блокируются до inference;
- audio SHA-256 и фиксированный набор model-file SHA-256 сверяются с фактическим
  receipt существующего ASR owner.

Report вычисляет Unicode word-level WER, exact accepted-phrase action accuracy,
nearest-rank p95 end-to-end latency и sampled peak process RSS. Если action cases
отсутствуют или RSS нельзя прочитать, соответствующее поле равно JSON `null` и
перечислено в `unknown_measurements`. Ноль используется только как измеренный ноль.

Тексты эталона и hypothesis не записываются: case receipt содержит hashes, counts,
errors и metrics. Benchmark не импортирует transcript в library/SQLite, не ставит
job, не вызывает provider/network и не dispatch-ит action. Все результаты имеют
`action_authority=false` и `dispatch_allowed=false`.

## Проверка и границы

Контракт проверяется временными synthetic bytes и fake backend для RU/LV: WER,
action accuracy, p95/RSS, privacy, consent, schema/path bounds, audio/model binding,
atomic report и fail-closed backend receipt. Это не реальный ASR quality result.

В этом проходе не было разрешённого пользовательского audio, установленной локальной
модели или device run на Dell, поэтому реальные WER/action accuracy/p95/RAM остаются
неизвестными. Никакие модели не скачивались и inference provider/local model не
запускался. Existing `content.sqlite3`, library records и durable job queue не
изменены.
