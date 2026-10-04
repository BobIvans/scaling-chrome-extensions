# 16 workflow-планов — декларативное R&D

Это собственная schema `occ.rnd.workflow.v1`, НЕ Laya/Jev state/questions и не совместимый native bot request. Планы не подключены к scheduler/executor. Наличие `nodes` не означает реализованных adapters; `ready_for_automatic_execution=false` обязательно.

Некоторые capabilities уже представлены CLI в данном ZIP (полный сбор, verify, text, catalog, chats); другие требуют интеграции с существующим SCE owner или разработки. `schemas/CAPABILITY_CANDIDATES.json` показывает это различие. JSON не должен сам разрешать выполнение.

Для каждого узла production-версия должна назначить отдельный reviewed профиль, точную schema входов/выходов, области записи/сети, budget, таймаут, idempotency и проверяемую postcondition. Generic строка в prototype-плане не является acceptance implementation.

`python tools/validate_workflows.py` проверяет структуру, ссылки на capability IDs, зависимости и запрет live в этих R&D-файлах; это НЕ выполнение workflow.
