# Добавленные функции PR007

Основные пользовательские возможности: CLI анализа captured JS/TS, точные spans, импорты/реэкспорты, conservative source resolver, type/dynamic gaps, stable IDs, immutable byte proof, atomic publication, проверяемый reuse, resource control и offline parser packaging.

Ниже перечислены все именованные функции и методы новых application Python modules. Тестовые методы и функции стороннего vendored Babel в этот список не входят.

| Module | Function / method | Действие |
| --- | --- | --- |
| `repo_js.py` | `boundary()` | Граница для воспроизводимого fault injection в тестах. |
| `repo_js.py` | `within()` | Проверяет принадлежность пути выбранному source root. |
| `repo_js.py` | `resolve()` | Разрешает literal source path по manifest или возвращает typed gap. |
| `repo_js.py` | `checked_span()` | Проверяет byte range, UTF8 boundaries и SHA256 evidence. |
| `repo_js.py` | `symbol_identity()` | Создаёт стабильный ID declaration по path/kind/name/occurrence. |
| `repo_js.py` | `relations()` | Строит проверенные refs, logical IDs и revisions. |
| `repo_js.py` | `analyze_entry()` | Проверяет eligibility/raw bytes, вызывает AST и формирует file outcome. |
| `repo_js.py` | `Projection.__init__()` | Открывает ограниченный writer для staged JSONL. |
| `repo_js.py` | `Projection.append()` | Добавляет запись с byte/hash/count proof и явным stage budget. |
| `repo_js.py` | `Projection.flush()` | Сбрасывает ограниченный buffer, проверяя deadline/progress. |
| `repo_js.py` | `Projection.close()` | Закрывает и fsync-ит projection. |
| `repo_js.py` | `Projection.proof()` | Возвращает hash/размер именно сформированных байтов. |
| `repo_js.py` | `checked_bundle()` | Проверяет состав, hashes и matching interpretation опубликованного bundle. |
| `repo_js.py` | `build()` | Оркестрирует read-only capture, все file outcomes и atomic directory publication. |
| `repo_js.py` | `main()` | Обрабатывает CLI, compact progress/results и blockers. |
| `repo_js_input.py` | `installed_fact_owner()` | Загружает совместимый PR005 owner из точного trusted application path. |
| `repo_js_input.py` | `extension()` | Определяет case-sensitive source extension. |
| `repo_js_input.py` | `schema_valid()` | Проверяет полученную wire schema без внешней зависимости. |
| `repo_js_input.py` | `eligibility()` | Потребляет owned PR005 projection; проверяет policy и source binding. |
| `repo_js_input.py` | `read_snapshot()` | Открывает scoped immutable SQLite read transaction с completeness/raw proof. |
| `repo_js_input.py` | `reconstruct()` | Восстанавливает один captured UTF8 file с chunk/revision/SHA256/Git OID proof. |
| `repo_js_input.py` | `snapshot_digest()` | Потоково связывает весь manifest и eligibility с interpretation. |
| `repo_js_runtime.py` | `stable_digest()` | SHA256 compact canonical JSON для JS dialect. |
| `repo_js_runtime.py` | `budget()` | Проверяет operator overrides без общего corpus/time/output ceiling. |
| `repo_js_runtime.py` | `rss()` | Измеряет working set Windows/POSIX, без hard RSS cap claim. |
| `repo_js_runtime.py` | `Control.__init__()` | Создаёт foreground deadline, counters и resource observations. |
| `repo_js_runtime.py` | `Control.pulse()` | Проверяет global deadline, измеряет память и выдаёт progress. |
| `repo_js_runtime.py` | `parser_pin()` | Проверяет exact vendored parser, metadata и license bytes. |
| `repo_js_runtime.py` | `parser_environment()` | Очищает preload/module/credential environment для child. |
| `repo_js_runtime.py` | `node_path()` | Выбирает и фиксирует установленный Node executable. |
| `repo_js_runtime.py` | `interpretation()` | Связывает actual parser/helper/adapter/schema/owner/options/input provenance. |
| `repo_js_runtime.py` | `parse_file()` | Обслуживает bounded one-file parser protocol, timeout/cancel и cleanup. |
| `qualify_repo_js.py` | `qualify()` | Проверяет actual AST outputs по 200 labelled cases и считает precision/recall/dynamic gaps. |

| Trusted Node helper function | Действие |
| --- | --- |
| `byteMap()` | Линейно переводит UTF16 позиции в raw UTF8 offsets, включая BOM/astral. |
| `extract()` | Извлекает refs/declarations из AST без исполнения source. |
| `readExact()` | Читает ровно заданный bounded private input frame. |
| `span()` / `keep()` / `ref()` | Внутренние функции `extract`: evidence hashes, output budget и typed reference records. |

Итого: 33 именованных Python functions/methods и 6 именованных Node helper functions. Код запускается через foreground CLI; отдельного UI/Native JS endpoint в этом PR нет.
