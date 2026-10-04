# Предварительный ADR: parser выбирается по qualification

Decision status: PROPOSED_PENDING_MEASUREMENT. Package не установлен в этом
workspace. Exact pin/artifact hash=null. Нельзя назвать выбранный parser qualified.

| Candidate | Подтверждено official docs | Что измерить до выбора |
| --- | --- | --- |
| TypeScript Compiler API <7 | createSourceFile и AST traversal без type checker; отдельный API для 7.1 | JS/TS/JSX/TSX spans, diagnostics, startup/RSS, offline dependency pin |
| @babel/parser | JSX/TypeScript plugins, ranges, parser errors | Plugin/options pin, fatal/recovered error handling, exact UTF8 mapping |
| Tree-sitter + pinned grammars | Parse API и byte positions, bindings | Grammar version/license, native or WASM delivery, Windows load/RSS |

Architecture proposal: first benchmark TypeScript createSourceFile branch <7
или Babel, если installed packaging уже поддерживает его. Это рабочий порядок
проверки, не основанное на замере решение. Tree-sitter сравнить как альтернативу;
не тратить hour slice на новый native installer, если measured existing parser
покрывает заданный corpus и budgets. Если ни один не qualified, вернуть blocker.

Official licenses: TypeScript Apache-2.0; Babel MIT; Tree-sitter core MIT.
Проверять license exact package/grammars и dependency notices отдельно: core
license не доказывает полный dependency bundle. URLs в PRIMARY_SOURCES.json.

Измерение одинаковых 20 families / 200 variants: exact spans, syntax/error
coverage, real extractor outputs, startup/cold/warm duration, parent/child RSS,
offline Windows install. Record actual versions/pins, packages hashes и options.
Source LX4-03: ≥98% supported-edge precision, all known dynamic unresolved,
recall independently. Qualification не заменяется минимальной поддержкой,
которая отвергает все inputs. Synthetic vs holdout results указывать отдельно.

Новый parser не должен читать scanned tsconfig, project dependencies или source
package scripts. TypeScript moduleResolution сложнее literal source paths:
официальный resolver допускает .js→.ts/.d.ts substitution и mode-dependent
extensionless paths. RELATIVE_SOURCE_EXACT_V1 намеренно сохраняет эти случаи
как gap, пока конкретный compiler/runtime policy не pinned и не qualified.
