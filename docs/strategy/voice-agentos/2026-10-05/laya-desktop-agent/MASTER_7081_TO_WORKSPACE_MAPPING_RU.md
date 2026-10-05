# 7 081 master → Universal Workspace V3 mapping

The V3 design intentionally preserves earlier concepts rather than replacing them.

Recovered/known source intent:
- selected context → selected Grok → saved response;
- response → ActionProposal → critic/compiler/executor/verifier;
- selected links/documents/attachments → open/download/ingest;
- long campaigns/checkpoints/recovery/no-progress;
- GapSpec → skill/tool creation → resume;
- background work while user uses Chrome;
- repo chunking/graph/context packs;
- labels/corrections;
- portable handoffs;
- work-session continuation;
- provider-neutral typed actions.

Earlier named workflow concepts carried forward:
- `AUTO-GL-01/02/03/07/08/09`
- `AUTO-EASY-04`
- `AUTO-OBS-16`
- `AUTO-PARALLEL`
- `AUTO-V3-4`
- `AUTO-V3CAT-005 chunk_to_any_action`
- `AUTO-V3CAT-135 continue while user works in Chrome`
- `AUTO-VOICE-04/10/11/16`
- `AUTO-WORK-SESSION`
- Library Navigator
- Chunk Workspace
- Context Cart
- `chat_history_to_open_loops`
- `repo_feature_pack`
- `NEXT_CONTEXT_REQUEST`
- `SKILL_PROPOSAL`
- staged `SCAN→CLASSIFY→COMPARE→PROPOSE→EXECUTE→VERIFY`

V3 adds a combinatorial inverse-scenario lattice and Notion-like product shell so these are not isolated workflows.

## Coverage strategy

It is impossible and unnecessary to enumerate every future human goal as a separate JSON file. Coverage is achieved by composing:

`Goal type × Source state × Context strategy × Capability state × Target state × Effect class × Resource state × Progress state × Time/budget state × Verifier state`.

Unknown combinations still enter the same Goal/Gap/Capability loop.

Therefore the source 7,081 routes remain historical evidence and test inspiration; the runtime is driven by reusable schemas/ontologies/workflows rather than 7,081 hard-coded if/else branches.
