# Функции, запланированные в объединённом PR

Названия — proposed symbols. Здесь они описаны, а не реализованы. Coding-чат записывает actual paths/handlers и evidence после реализации.

| ID | WS | Proposed function | Вход → выход | State / error / recovery | Проверка |
|---|---|---|---|---|---|
| F001 | WS-018 | captureInputRevision | original source + corrected text → InputRevision | Append-only provenance/revision; INPUT_INVALID | INT-PARITY |
| F002 | WS-018 | resolveCriticalSlots | text + selected aliases → resolved/uncertain slots | No guessed repo/chat/effect/amount; NEEDS_INPUT | INT-AMBIGUOUS |
| F003 | WS-018 | routeKnownCommand | typed slots + pinned registry → template route | Deterministic route; unknown→development request | INT-REPEAT |
| F004 | WS-018 | retrievePlanEvidence | allowlisted source refs → EvidenceBundle | Missing mandatory refs→retrieval required; content untrusted | INT-RETRIEVAL |
| F005 | WS-018 | proposePlan | IntentSpec + evidence → PlanProposal | Separate author/version; cannot create grants | INT-ROLES |
| F006 | WS-018 | critiquePlan | proposal + criteria → Verdict | Reject missing source/scopes; goal unchanged | INT-ROLES |
| F007 | WS-018 | discoverLayaAdapter | installed interface → capability receipt | UNKNOWN/UNAVAILABLE→direct UI; no guessed vendor API | INT-LAYA |
| F008 | WS-018 | validateLayaProposal | proposal → typed known operations | Registry/template/grant checks before dispatch | INT-LAYA |
| F009 | WS-018 | compileIntentDag | validated intent → versioned steps/hash | Cycles/duplicates/missing/version mismatch rejected | INT-DAG |
| F010 | WS-018 | canonicalizeSemanticPlan | normalized semantic payload → SHA256 | Modality metadata separate; decimals strings, versions pinned | INT-PARITY |
| F011 | WS-018 | reviseIntent | correction + expected revision → new revision | Atomic revoke unexecuted old jobs; race→unknown/reconcile | INT-REVISION,ALL-RESTART |
| F012 | WS-018 | admitCurrentRevision | current Core state + grant → admitted/fenced | Recheck STOP/revision/qualification at effect boundary | INT-RACE |
| F013 | WS-018 | createDevelopmentRequest | unknown capability → bounded request | Linked exact intent/criteria; no arbitrary shell/install | INT-UNKNOWN |
| F014 | WS-019 | startPushToTalk | physical hotkey/device → CaptureSession | Single stream; reentrant call returns same ID | VOICE-ONE |
| F015 | WS-019 | stopCapture | stop/release → final segment or aborted | Always release device handle; explicit stop fallback | VOICE-RELEASE |
| F016 | WS-019 | recoverCaptureLifecycle | crash/sleep/device change → gaps/new session | Persisted incomplete ranges do not become valid audio | VOICE-GAPS,ALL-RESTART |
| F017 | WS-019 | transcribeAudio | audio_ref + pinned ASR → transcript revisions | Consume iterator; failure preserves text path | VOICE-OFFLINE |
| F018 | WS-019 | guardTtsBackground | activation/segments → accepted/uncertain | Background/TTS no execution grant; preview required | VOICE-TTS |
| F019 | WS-019 | reviewVoiceSlots | transcript/gold slots → preview/correction | Exact repo/chat/path/effect/amount; old revision fenced | VOICE-CORRECTION |
| F020 | WS-019 | dispatchIndependentStop | keyboard/Core stop → blocked admission | No ASR dependency; unknown remote effects retained | STOP-INDEPENDENT |
| F021 | WS-019 | measureCriticalSlotErrors | held-out gold/attempts → device metrics | Separate WER/slots/false admission/latency; missing null | VOICE-GOLD |
| F022 | WS-019 | provideKeyboardParity | desktop controls → same intent operations | Names/focus/status/errors; no drag requirement | UI-KEYBOARD,UI-A11Y |
| F023 | WS-021 | bindSelectedTarget | user selection+observation → TargetBinding | Observable stable identity; missing→rebind/manual | TARGET-DUPLICATE |
| F024 | WS-021 | revalidateTarget | binding+current observation → match/rebind | Before upload/Send; tab handles not identity | TARGET-DRIFT |
| F025 | WS-021 | resolveTargetAfterRestart | persisted binding → qualified handle | Duplicate title/account/reused ID block guessed match | TARGET-RESTART,ALL-RESTART |
| F026 | WS-021 | discoverAdapterCapabilities | route/environment → actual capabilities | Separate API/CLI/UIA/DOM qualification; no silent switch | TARGET-ROUTE,TARGET-LOGIN,COMPAT-UPSTREAM |
| F027 | WS-021 | runAdapterCanary | UI contract+environment → qualification receipt | Drift invalidates only affected adapter | TARGET-CANARY,TARGET-MULTILINE |
| F028 | WS-021 | acquireComposerOwnership | target resource key → lease/fence | One writer across contexts; user focus priority | OUTBOX-LEASE |
| F029 | WS-021 | yieldFocusToUser | manual takeover → paused operation | Block next keystroke/click; retain task/draft | TARGET-FOCUS |
| F030 | WS-021 | restoreOwnedClipboard | saved clipboard/current version → restore/noop | Never overwrite new user clipboard value | TARGET-CLIPBOARD |
| F031 | WS-022 | enqueueImmutableDelivery | packet/binding/intent → durable outbox | Same operation keys; atomic commit; local hashes verified | OUTBOX-TX,OUTBOX-ENVELOPE,COMPAT-UPSTREAM |
| F032 | WS-022 | inspectDraftConflict | current composer → empty/owned/conflict | Do not overwrite foreign draft | DRAFT-CONFLICT |
| F033 | WS-022 | prepareAndAttachDraft | supported parts/prompt → draft evidence | Separate local hashes and observable upload grades | DRAFT-VERIFY,DRAFT-NOUPLOAD |
| F034 | WS-022 | armSendAttempt | validated current state → SEND_ARMED | Persist before click; separate intent; STOP/revision check | SEND-SCOPE,SEND-PROVENANCE |
| F035 | WS-022 | dispatchSingleSend | armed attempt → one invocation+observation | No retries per attempt even after lease loss | SEND-ONCE |
| F036 | WS-022 | observeOutgoingMessage | qualified history → observed evidence | Match exact task/attempt/packet; no similar unrelated reply | SEND-OBSERVE |
| F037 | WS-022 | reconcileUnknownSend | attempt+history → observed/no-effect/unknown/conflict | Incomplete history remains unknown; no blind retry | SEND-RECONCILE,SEND-UNKNOWN |
| F038 | WS-022 | recordPartCoverage | part+observation/claim → typed ledger | Received/use claims not inferred from attach or generic reply | PART-COVERAGE |
| F039 | WS-022 | iteratePacketParts | manifest+cursor → bounded pages | No hidden total cap; backpressure/checkpoints preserve all IDs | PART-SCALE |
| F040 | WS-022 | importCorrelatedResult | final response+task/packet → result event | Schema/correlation/current-head checks; idempotent; data only | RESULT-CORRELATION,RESULT-IDEMPOTENT,RESULT-DATA,COMPAT-DOWNSTREAM |
| F041 | WS-022 | cancelDelivery | Core cancel/STOP → per-attempt outcomes | Remote unknown retained; next parts not dispatched | SEND-CANCEL |
| F042 | WS-020 | recordScopedDemonstration | allowed UI events → candidate recording | Sanitize before persistence; credential refs only | SKILL-SECRET |
| F043 | WS-020 | compilePortableSkill | recording+contracts → versioned skill | Same Core compiler; stable identity not recorded coordinates | SKILL-RECORD |
| F044 | WS-020 | qualifySkillReplay | normal/unseen/fault cases → scoped receipt | Bind exact code/environment/dependency hashes | SKILL-UNSEEN |
| F045 | WS-020 | optimizeSkillSteps | candidate step diff+verifier → optimized version | Mandatory checks/STOP/effect invariant preserved | SKILL-OPTIMIZE |
| F046 | WS-020 | appendFailureCapsule | failed attempt → immutable capsule | All negative attempts survive success/repair | SKILL-FAILURE |
| F047 | WS-020 | computePermissionDiff | old/new scopes → unchanged/reduced/grown | No implicit scope growth; compatible reuse allowed | SKILL-SCOPE |
| F048 | WS-020 | invalidateDependentSkills | changed dependency → STALE closure | Selective index; independence proven before retaining receipt | SKILL-DRIFT |
| F049 | WS-020 | repairSkillVersion | capsules+repair → new version | Old version/receipts/failures retained; requalify negative corpus | SKILL-NEGATIVE |
| F050 | WS-020 | invokeQualifiedRecipe | skill+scope+current refs → Core plan | Reuse jobs/leases/cancel/reconcile; no second executor | SKILL-RECIPE,ALL-RESTART,COMPAT-UPSTREAM,COMPAT-DOWNSTREAM |
