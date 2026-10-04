# R&D ZIP Directions

Each R&D package should contain:
- README.md
- manifest.json
- hypotheses.md
- architecture.md
- experiments.md
- acceptance_criteria.md
- functions.md
- test_vectors.jsonl
- results/
- traces/

## RND-01 — Voice Fast Path
Goal: speech -> typed action with minimal latency.
Build: streaming ASR, VAD, partial intent, vocabulary bias, confidence escalation.
Acceptance: known read-only commands launch without large-LLM planning.

## RND-02 — Lossless Context Fabric
Goal: ingest arbitrarily large local data without lossy replacement.
Build: immutable object store, provenance, dedupe, versioning, parsers, event stream.
Acceptance: every derived chunk/summary points back to exact source bytes/message/event.

## RND-03 — Context Compiler
Goal: produce the smallest sufficient AI handoff context.
Build: lexical/vector/graph/code/time retrieval, conflict detection, context deltas.
Acceptance: reproduce answers/actions while reducing irrelevant context versus naive dumping.

## RND-04 — Repository Semantic Compiler
Goal: understand large repos structurally, not as random chunks.
Build: Tree-sitter AST, symbol graph, imports, callers/callees, tests, commits, PR mapping.
Acceptance: given a function/bug, retrieve affected symbols/tests/history with provenance.

## RND-05 — Capability Graph + Executor Mesh
Goal: one user goal, multiple independent execution methods.
Build: executor registry, capability manifests, success/latency/risk scores, fallback chain.
Acceptance: injected failure in primary executor triggers a different viable path.

## RND-06 — Windows Native Automation
Goal: reliable Windows 11 operations without coordinate clicking.
Build: PowerShell, Win32, COM, UIA, process/window/file/clipboard adapters, UFO² experiment.
Acceptance: common actions survive window movement/resolution changes.

## RND-07 — Browser Native Automation
Goal: robust Chrome/web actions.
Build: API-first adapters, CDP, Playwright, BrowserCode scripts, DOM state verifier.
Acceptance: repetitive browser workflow becomes deterministic reusable script.

## RND-08 — Universal GUI Fallback
Goal: recover when no structured interface exists.
Build: screenshots, accessibility tree fusion, visual grounding, Agent-S experiment.
Acceptance: fallback can complete selected opaque-app tasks and produce replay trace.

## RND-09 — Coding Skill Factory
Goal: unknown request -> tested reusable capability.
Build: AutomationSpec, coding agent, isolated branch/worktree, tests, plugin packaging, rollback.
Acceptance: second execution avoids coding model and invokes compiled skill.

## RND-10 — Temporal Personal Memory
Goal: know what was true, when, and what superseded it.
Build: event sourcing + Graphiti adapter + provenance + contradiction/supersession links.
Acceptance: historical query distinguishes old decision from current decision.

## RND-11 — Ambient Work Capture
Goal: make current PC activity queryable context.
Build: screenpipe-style event adapter, app/window/accessibility/audio metadata, privacy filters.
Acceptance: reconstruct the context preceding a bug/task without manual notes.

## RND-12 — Durable Workflows
Goal: multi-hour tasks survive crashes and reboots.
Build: Temporal workflow/activity split, retries, checkpoints, cancellation, resume.
Acceptance: kill process mid-run; restart continues from verified state.

## RND-13 — Multi-AI Handoff
Goal: same local context can be sent to any AI.
Build: provider-neutral HandoffBundle, output schemas, context-delta requests, model adapters.
Acceptance: OpenAI/Grok/Claude/local adapters consume same canonical bundle.

## RND-14 — Self-Evaluating Router
Goal: improve executor choice from real outcomes.
Build: per-task benchmarks, contextual-bandit experiment, success/latency/cost telemetry.
Acceptance: router shifts toward executor with better observed reliability.

## RND-15 — Behaviour-to-Skill Mining
Goal: discover automations from repeated manual behavior.
Build: trace segmentation, sequence clustering, candidate SOP extraction, skill synthesis.
Acceptance: repeated multi-step workflow is recognized and replayed as a skill.

## RND-16 — Studious-Pancake Vertical
Goal: 'continue qualification' compiles to a reliable repo workflow.
Build: repo graph, qualification runner, failure triage, PR/history retrieval, patch/test/receipt pipeline.
Acceptance: one command generates evidence-backed handoff or validated patch without losing source provenance.

## RND-17 — Accessibility-First UX
Goal: voice-only control for users who cannot use mouse/keyboard reliably.
Build: global hotkey/wake mode, command correction, spoken confirmations for risky actions, status summaries.
Acceptance: core workflows can be executed without visual pointer input.

## RND-18 — Speculative Context Prefetch
Goal: hide latency while the user is still speaking.
Build: partial-ASR intent prediction, repo/app preloading, read-only retrieval prefetch.
Acceptance: prefetch reduces post-utterance latency without speculative writes/actions.
