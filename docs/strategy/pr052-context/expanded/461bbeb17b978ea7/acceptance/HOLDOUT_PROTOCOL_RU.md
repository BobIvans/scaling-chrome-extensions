# Parser/resolver holdout и independent oracles

Source gate LX4-03 взят из PR007 spec: >=200 labelled fixtures, >=98% precision
supported local-static edges, 100% known dynamic forms unresolved. Starter corpus
этого ZIP меньше, поэтому gate NOT_RUN. Нельзя заменить holdout повтором starter.

1. До измерения freeze parser/helper/artifact/license/platform/options hashes и
   support matrix. Выбрать qualified declarative resolution mode per fixture.
2. Freeze >=200 labelled cases, disjoint training/debug/holdout paths и family IDs.
   В корпус включить JS/TS/JSX/TSX, mts/cts, Unicode/CRLF, relative extensions,
   aliases/extends/project references, workspace/exports/imports/conditions,
   import vs require, shadowing, dynamic, missing/external, bad syntax/case,
   generated/unavailable target, config drift и >2MiB source с import в хвосте.
3. Human-reviewed labels с source anchor/target-or-reason/rule и hashes; второй
   независимый reviewer/oracle разрешает disagreements до прогона. Trusted frozen
   TypeScript resolver может быть differential oracle для qualified subset,
   но если он является resolver-under-test, не считается независимым подтверждением.
   Ни один oracle не исполняет scanned source или dynamic config.
4. Единица precision — predicted qualified static-local edge occurrence с exact
   target и source occurrence identity. TP/(TP+FP); denominator 0 => UNDEFINED,
   gate FAIL/UNKNOWN. Recall TP/(TP+FN) и unsupported fraction отдельно. Все
   occurrences accounted; unsupported не удалять из общего denominator coverage.
5. Dynamic correctness: expected dynamic count, marked unresolved count и falsely
   resolved targets. Последнее должно быть 0. Wrong parse span даже при верном
   target является отдельной ошибкой fidelity.
6. Измерить offline install/parser packaging и max RSS/latency на реальном Dell
   Windows 11. Установка trusted pinned parser отличается от dependency install
   исследуемого repo; hooks/imports scanned repo запрещены.
7. Опубликовать inputs/labels/outputs hashes, errors, excluded families, whole
   attempt outcomes и limitations. Не подбирать threshold задним числом.

Package validator проверяет fixture oracle files и ссылки; не запускает parser и
не присваивает измеренные precision/recall.
