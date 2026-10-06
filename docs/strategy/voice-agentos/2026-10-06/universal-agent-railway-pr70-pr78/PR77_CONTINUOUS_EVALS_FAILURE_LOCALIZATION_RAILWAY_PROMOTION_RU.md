# PR77 — Continuous Evals + Failure Localization + Railway Promotion

## Purpose
Local regression harness, interaction-edge failure ownership and replay/canary for rail/skills/adapters.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- FailureEdge identifies repair owner
- Old successes replay against new rail
- Promotion requires non-regression gates
- Metrics cover success, latency, intervention and uncertainty

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
