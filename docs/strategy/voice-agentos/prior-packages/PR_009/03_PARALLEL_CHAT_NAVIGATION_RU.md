# Координация №8 / №9 / №10

| Чат/пакет | Владелец среза | Что передать дальше |
| --- | --- | --- |
| №8, предыдущий разрабатывается | Desktop transport / Windows packaging spike по исходной очереди | actual touched paths, typed DTO, SHA, tests, installer/device gaps |
| Этот чат №9 | Backend local ChatGPT original/source/extraction revisions | IMPORT_FIDELITY_CONTRACT + actual SQLite owner/migration/CLI receipt |
| Следующий №10 | Один search/range/manual-label adapter | exact source-version refs и actual query/index owner |

Сообщение пользователя подтверждает работу над предыдущим пакетом, не merge.
Готовый exact ZIP №8 здесь не предоставлен/не прочитан. Не назначать ему DTO
по догадке; таблица отражает исходную очередь и ручную координацию, не live lock.
№7 brief прочитан; №6 создан в этой сессии. Actual implementations/CI не наблюдены.

№9 можно готовить в своей ветке на actual merge-base: backend import_fidelity
owner + focused tests. content_lab.py/Native boundary потенциально shared с №8:
перед изменением зафиксировать touched paths обоих branches, добавить sibling
helper, owner integration коммит выполнять после contract comparison. Не вводить
новый IPC action в №9. Packaging bundle/install manifest обновляется owner №8
после integration; нужен actual include-module test, чтобы helper не пропал.

Начало implementation чата:
«Реализуй только ZIP №9: EXECUTE_THIS_PR_RU.txt. №8 в параллельном чате.
Проверь actual base/AGENTS/Content Lab original owner, reuse existing importer,
не меняй desktop IPC. Передай diff paths, schema/version, tests, gaps и SHA
в IMPLEMENTATION_RESULT_TEMPLATE. Original bytes + error retention + selected
scope isolation обязательны. Пакет №9 не означает выполненный GitHub PR». 

Перед №10 передать заполненный receipt №9 и actual contract/schema. Без них
можно проектировать fixtures/query semantics, runtime consumption остаётся gap.
Не считать merge installed capability. Нет автоматического обмена между чатами:
эту таблицу/receipt нужно передать в нужный чат вручную.
