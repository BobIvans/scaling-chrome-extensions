# PR78 — Mission Cockpit V2 + Windows/Flashloan Final Qualification

## Purpose
Final app UI plus real installed Windows and Studious Pancake qualification campaigns.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Six primary controls work end-to-end
- Cockpit shows surfaces/lanes/approvals/timeline/teach/replay
- Installed Windows fault campaign receipts
- Studious Pancake paper campaign demonstrates multi-source multi-lane AgentOS

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
