# PR76 — Temporal Context Graph & ContextPack Compiler

## Purpose
Typed temporal relations/backlinks and minimal goal-specific evidence packs.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Edges carry provenance/time
- Contradictions/supersession represented
- Bounded ContextPack references raw evidence
- Labels/FTS/graph/optional embeddings compose

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
