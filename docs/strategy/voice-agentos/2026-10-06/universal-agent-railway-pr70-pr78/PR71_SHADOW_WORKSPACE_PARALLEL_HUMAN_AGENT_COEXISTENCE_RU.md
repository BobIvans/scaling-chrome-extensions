# PR71 — Shadow Workspace & Parallel Human-Agent Coexistence

## Purpose
Background CDP, duplicate read tabs, shadow leases and exact conversation/composer writer resources.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- User can keep foreground while safe background browser lane runs
- Duplicate read tab cannot become concurrent same-conversation writer
- Human Take Over fences conflicting resource
- Shadow state survives mission restart

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
