Title: Add derived JS/TS syntax analysis with conservative source-linked relations

JS/TS currently remains text-only in repository context. This change adds an
operator-selected analysis CLI over verified captured bytes, with AST spans,
static import/re-export references and versioned provenance in a separate
derived bundle. It preserves existing raw chunk identities and partitions.

The first resolver policy matches explicit relative source paths only. Dynamic,
CommonJS, aliases/workspaces and TypeScript extension substitution remain
explicit unresolved cases. Exact source-file matching does not assert runtime
or imported-symbol binding. It consumes the checked PR005 eligibility schema with independent raw-byte proof.
The checked PR006 policy accepts Python edges only, so JS relations remain a
separate dialect pending a versioned consumer adapter.

Validation: replace this paragraph with actual parser artifact/version,
application test results, precision/recall/unresolved counts and device evidence.
Input ZIP checks are fixture/data validation; application implementation, Windows
install and CI results are not supplied by this package. Parent roadmap tasks
remain open for resolver modes, mixed graph queries and owner/UI qualification.
