# PR73 — Laya Railway V2

## Purpose
Adaptive typed question compiler with route/evidence/target/action/critic/progress passes and fail-closed thresholds.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Smallest sufficient question set
- Exact candidate IDs only
- Consequence-aware confidence gates
- Question versions replay-tested

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
