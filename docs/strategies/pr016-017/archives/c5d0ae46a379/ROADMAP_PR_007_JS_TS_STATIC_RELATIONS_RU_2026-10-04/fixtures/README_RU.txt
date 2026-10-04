200 synthetic labelled cases = 20 families × 10 variations, не 200 независимых форм.
Corpus code — данные; НЕ выполнять node fixtures/corpus/... или npm scripts.
EXECUTION_CANARY.js throws if executed; анализ должен только parse bytes.

LABELLED_CORPUS.json содержит expected references/symbols и exact raw ranges.
20 known dynamic labels unresolved; comments/strings не становятся imports.
RELATIONS.jsonl / JS_ANALYSIS.jsonl в derived_golden — example из labels/oracle,
не наблюдённый AST output. EXAMPLE_STATUS.json явно synthetic/NOT_QUALIFIED.
Qualified precision/recall null; AST adapter не установлен и не выполнялся.

Запуск package checks: python -B tools/verify_package.py.
Actual parser integration tests должны подавать raw bytes trusted installed
adapter, сравнивать actual outputs с labels и report precision/recall/unresolved.
При нуле predicted positive precision=null, не 1.0; supported recall отдельно.
Поддерживаемые exact path relations имеют MANIFEST_SOURCE_PATH_ONLY scope,
не TypeScript/Node/compiler/runtime binding. TS .js substitutions — gaps.

Rebuild corpus recipe: python -B tools/make_labelled_corpus.py regenerates source
labels. Expected derived data генерируется из labels, не заменяет AST tests.
Для полной LAYA4-005 qualification нужен independent real-world holdout и
actual Windows/offline/device receipt. Все application cases пока NOT_RUN.
