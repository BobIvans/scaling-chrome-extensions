# PR70 — Universal Surface Graph V10

## Purpose
Merge WebMCP/CDP/DOM/AX/extension/UIA/native/vision observations into exact SurfaceGraph; introduce surface identity and observer ladder.

## Depends on
PR64–PR69 canonical wave plus all earlier merged owners. Re-audit current main first.

## Implementation rule
Extend canonical owners; do not create duplicate queues/stores/effect ledgers. New observations/actions need exact identity, resources, provenance, receipts, verifier and FailureEdge.

## Acceptance
- Exact tab/window/document identity
- Observer ladder is deterministic
- WebMCP manifests are untrusted data
- Vision fallback has fixture corpus

## Required tests
- deterministic unit/fixture coverage;
- restart/replay or drift test where applicable;
- no authority from page/model/source text;
- explicit negative tests for wrong target/low confidence/human conflict;
- update strategy audit only after code evidence exists.
