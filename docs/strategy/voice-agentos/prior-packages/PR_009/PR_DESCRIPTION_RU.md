# Шаблон будущего PR

Сохранение выбранного ChatGPT JSON раньше оставляло только извлечённые сообщения
и hash исходного файла. Добавлена exact original revision в existing SQLite и
versioned ledger всех наблюдаемых nodes/ветвей/вложений, включая empty/non-text
states и явные topology gaps. Импорт B больше не меняет heads невыбранного A.
Invalid captured input сохраняется как original с ERROR extraction без изменения
derived heads; storage failure откатывает transaction. Existing text IDs сохранены.

Validation: заполнить actual commands/results, migration/rollback/roundtrip/
scope isolation evidence, base/head SHA и CI. В этом пакете они NOT_RUN.
Limits: local ChatGPT JSON only, remote completeness UNKNOWN, attachment payload
не захвачен; broad ACTION5-04/05/06 остаются open. Не копировать «добавлена»
в опубликованный PR до фактического diff и проверок.
