# Repo chunking / logical TXT modes

## Principle

The first onboarding of a repository should be **whole-repo accounting**, because the system cannot know what is important before it has enumerated the complete snapshot. Later interaction should normally use focused projections.

Canonical Git/source bytes remain authoritative. Logical chunks are views with exact references, never a replacement for the source vault.

## Modes

### WHOLE_REPO_INDEXED

Use for first import, architecture audit, unexplained global failures, migration, or periodic full qualification.

Output:
- full file accounting;
- canonical owners/entry points;
- import/dependency relations;
- symbols/tests/config/docs;
- unresolved edges;
- logical groups and receiver-bounded parts;
- overview + manifest + coverage receipt.

It must **not** be one enormous concatenated text file. It is a full index plus multiple logically connected TXT/MD parts.

### INTERCONNECTED_FILES

Seed from selected file/symbol/goal and expand by:
imports, reverse imports, tests, config contracts, schemas, callers/callees, declared relations, same SCC/component and evidence links.

Stop by graph/risk boundary, not arbitrary file count. Preserve frontier as omitted-but-related refs.

### TECH_DEBT_FOCUSED

Rank evidence of:
duplicate owners, stale contracts, TODO/FIXME/deprecated paths, missing tests, repeated failure history, unqualified effects, error swallowing, dead/stale code, old compatibility shims, large risky modules, unresolved graph edges and drifted external contracts.

Laya may rank/classify evidence. It does not declare debt without supporting source refs.

### ERROR_AND_BROKEN_PATHS

Seed from test/CI/runtime failures and trace:
error → failing test → symbol → dependencies → config/schema → upstream provider/transport.

Output a minimal reproduction/evidence cone plus unresolved alternatives.

### HIGH_VALUE_FILES

Score files by runtime reachability, fan-in/fan-out, entrypoint proximity, data/effect boundary, test coverage, change frequency/failure history and current goal relevance.

### TEST_IMPACT

Given changed files/goal, compute affected tests, fixtures, schemas, contracts and missing test surfaces.

### RUNTIME_PATH

Follow one capability from UI/voice intent through compiler/Core/executor/verifier/store.

### DOMAIN_FOCUSED

Use domain tags and evidence graph to produce a bounded pack for browser, repo intelligence, voice, GitHub, Web3 paper qualification, etc.

### DELTA_SINCE_SNAPSHOT

Only changed/added/deleted files plus all invalidated logical groups, tests, evidence and context packs.

## Pack contract

Every export contains:
`00_INDEX.md`, logical `*.txt`/MD parts, machine manifest, coverage receipt, exact source refs, gaps, questions, and a provenance digest.

Receiver limits affect **part size only**, never canonical capture completeness.
