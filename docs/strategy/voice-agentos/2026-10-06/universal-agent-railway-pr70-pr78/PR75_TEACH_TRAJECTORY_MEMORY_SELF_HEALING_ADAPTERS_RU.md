# PR75 — Teach + Trajectory Memory + Self-Healing Adapters

## Purpose
Demonstration recorder, semantic recipes, replay, drift localization and canary repair.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Teach creates immutable trajectory
- Recipe derived without secret capture
- Replay validates semantic postconditions
- Failed adapter can be repaired/versioned/canary promoted

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
