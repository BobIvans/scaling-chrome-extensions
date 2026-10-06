# Current code audit — implemented vs missing
Baseline for authoring: main@2868dc54249008bc010fdc48400aab4af3254709. Re-audit current main before coding.

## Implemented now
- canonical local Library with raw bytes, revisions/provenance, search, labels;
- streamed virtualized chat archive with coverage/gaps/order + TXT/metadata/raw JSONL;
- BrowserWatch, watched folders, previous conversation exports;
- Google Drive API/export ingestion: Docs→TXT, Sheets→XLSX, Slides→PPTX, Drawings→PDF, blobs→raw;
- browser tab list, UI inventory, exact document/element fingerprints, READ_NAV broker, human foreground lease;
- Windows UIA inventory/action fallback with dangerous generic actions blocked;
- Laya client/supervisor, FastDecision concurrent read prefetch, durable Goal/H2/H1/H0 and restart resume;
- capability candidate qualification + PR/CI/exact-head merge primitives;
- staged release/update primitives;
- AI-site effect primitive already has origin/account/workspace/conversation identity, composer/send fingerprints, draft prepare/readback, EffectIntent, send-once, outgoing reconciliation and response reading.
- Chrome manifest already has downloads permission and capture-specific downloads.

## Missing end-to-end
1. real durable resource-aware parallel workers (PR64);
2. canary→REGISTERED→waiting-goal resume (PR65);
3. provider-neutral System-2 (PR66);
4. universal effectful-site qualification/dynamic discovery (PR67);
5. qualified production activation/reconnect (PR68);
6. unified mission/library timeline UI (PR69);
7. SurfaceGraph/shadow background execution (PR70–71);
8. any-source/any-MIME ambient harvester (PR72, deepened by PR85);
9. adaptive Laya V2 (PR73), deepened into GoalContract/dialogue V3 by PR79–80;
10. universal executor ladder (PR74), deepened by PR82/84;
11. Teach/trajectory memory (PR75), deepened by PR83;
12. temporal ContextGraph/JIT composition (PR76), deepened by PR81;
13. failure localization/evals (PR77), deepened by PR86;
14. real Windows + flashloan qualification (PR78/87);
15. no generic any-download→artifact→hash→classify→extract→Library broker;
16. Drive API exists but no robust Drive UI fallback bound to exact Google account/file identity;
17. no WebMCP discovery/call owner;
18. no CDP accessibility-tree/delta observer owner;
19. no expected-value-of-human-question policy;
20. no counterfactual candidate-action preview before consequential execution.
