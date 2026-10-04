# Проверенные первичные источники и выводы для implementation

TypeScript описывает moduleResolution как выбор правил поиска модулей под target
runtime/bundler. Проектный вывод: фиксировать mode/context/config в graph revision,
а неподдерживаемые правила учитывать как gap. [Документация](https://www.typescriptlang.org/docs/handbook/modules/reference).

Node.js описывает conditional exports для import/require и ограничения доступных
package subpaths. Проектный вывод: учитывать conditions и не подменять скрытый
subpath произвольным существующим файлом. [Документация](https://nodejs.org/api/packages.html).

SQLite требует согласованности external-content FTS index с content table.
Проектный вывод: проверить transactions/triggers/backfill текущего owner и отдельно
квалифицировать scoped search. [Документация](https://www.sqlite.org/fts5.html).

Это выбор дизайна, не проверка actual SCE runtime и не measured Windows pin.
