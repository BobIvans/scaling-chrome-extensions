# PR74 — Universal Action Compiler & Executor Ladder

## Purpose
Compile semantic action to safest WebMCP/MCP/API/COM/CLI/CDP/DOM/UIA/vision executor with typed verifier.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Structured interface outranks click
- Every effect maps to local effect class/resources
- No arbitrary generated command authority
- GapSpec emitted when no route

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
