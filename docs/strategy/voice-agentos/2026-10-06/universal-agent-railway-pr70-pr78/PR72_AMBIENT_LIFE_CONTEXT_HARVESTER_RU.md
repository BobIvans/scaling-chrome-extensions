# PR72 — Ambient Life Context Harvester

## Purpose
SourceAdapter registry, any-MIME raw preservation, Drive OAuth onboarding, downloads/AI chats/folders/connectors and automatic labels.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Raw artifact preserved without extractor
- Incremental checkpoints/dedup
- Source pause/delete/sensitivity controls
- Drive onboarding no longer requires hand-edited token env only

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
