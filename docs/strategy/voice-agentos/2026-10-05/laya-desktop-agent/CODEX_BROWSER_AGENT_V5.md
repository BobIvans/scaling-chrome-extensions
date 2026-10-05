# Codex — Browser Agent Runtime V5 implementation brief

V5 is not documentation-only: `one-click-context/agentos/sidepanel.html` + modules are an executable Chrome shell already added to the repository. Preserve and extend them.

## First run

1. Run existing extension/unit/browser tests.
2. Run `node --test one-click-context/tests/agentos-sidepanel-core.test.mjs`.
3. Load extension unpacked and confirm Chrome side panel renders.
4. Confirm tab enumeration, explicit origin permission and Observe capture on at least one generic page/chat.
5. Confirm existing native host hello and durable STOP/Codex fallback still work.

## Then implement missing runtime

### Native bridge
Extend existing `agent-bridge/host.mjs` and current install packaging. Advertise `agentosCommands` in hello. Do not create another native host.

### Canonical dispatcher
Add the smallest runtime layer that maps agentos.* commands into existing owners:
Core, action_runtime, context_library, campaign_runtime, repo modules, release_updater.

### Generic AI sites
Implement adapter registry with:
- generic observe-only adapter;
- versioned qualified adapters for effectful send/readback;
- adapter-generation/qualification workflow for a new AI site.

Do not hard-code the architecture around Grok. Grok is just one provider plugin.

### Literal side-panel mission monitoring
Extend side panel to show:
- bound identity;
- Context Cart;
- repo revision/scan/pack;
- Goal/acceptance;
- H2/H1/H0;
- Laya decisions and confidence;
- System2 provider/role/session;
- parallel lanes;
- active resource leases;
- capability gap/promotion;
- evidence/receipts;
- updater stage;
- STOP/Pause/Resume/Human takeover.

### Provider says merged
Implement `SELF_RENEWAL_AI_SITE_WORKFLOW.json` exactly as verification→Git sync→build/test→stage→canary→installed readback→activation→mission resume. Provider prose never closes merge/install criteria.

### Any AI site
Unknown site starts OBSERVE_ONLY. If user requests write/send, create a SiteAdapterGap. System2 may propose adapter code; qualify it on a frozen site corpus before enabling writes.

### Tests
Cover permission denial, tab closure/reuse, origin drift, account/chat drift, human takeover, download danger/interruption, native disconnect, provider malformed result, merge claim false, repo/head drift, candidate update failure, rollback, restart/resume and STOP.

Do not remove current capture/library/Codex features while integrating V5.
