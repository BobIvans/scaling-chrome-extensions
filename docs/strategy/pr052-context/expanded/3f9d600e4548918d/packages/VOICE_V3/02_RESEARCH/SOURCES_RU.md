# Первичные источники — реестр V3



Дата чтения: 3 октября 2026. Документация прочитана; установку и заявленные benchmark-результаты на Dell мы не воспроизводили. Прямые посты X не удалось прочитать; ограничения описаны отдельно.



## S01 — The Tail at Scale

https://research.google/pubs/the-tail-at-scale/

Источник: Google Research; original research, 2013

Поддерживает: Tail latency and redundant/hedged requests motivate a delayed backup rather than unconditional fan-out.

Границы: Application to desktop context retrieval is our design inference, not a measured result for this app.



## S02 — Making retries safe with idempotent APIs

https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/

Источник: AWS Builders Library

Поддерживает: A caller request identifier and atomic recording of an operation reduce duplicate side effects on retries.

Границы: A local journal alone cannot provide exactly-once effects in an external service.



## S03 — Playwright isolation

https://playwright.dev/docs/browser-contexts

Источник: Playwright official documentation

Поддерживает: Browser contexts separate cookies and browser storage for independent sessions.

Границы: Browser contexts do not isolate writes to the same remote account; they are not full OS sandboxes.



## S04 — Git worktree

https://git-scm.com/docs/git-worktree

Источник: Git documentation

Поддерживает: Multiple working trees can be attached to one repository.

Границы: Worktrees share Git administration; this is not credential, process or filesystem security isolation.



## S05 — UFO

https://github.com/microsoft/UFO

Источник: Microsoft official repository

Поддерживает: UFO3 documents dynamic task DAGs and parallel orchestration; UFO2 is the device-agent layer.

Границы: Not installed or benchmarked on the user Dell. Use as an optional adapter, not a second authority.



## S06 — Laya model card

https://huggingface.co/convaiinnovations/laya

Источник: Convai Innovations author model card

Поддерживает: Typed decision models and multilingual/typed checkpoints are available; the card itself reports variable accuracy with domain and input length.

Границы: No 33ms or near-perfect routing promise on this Dell; decision confidence does not grant execution permission.



## S07 — Unsloth decision Laya

https://unsloth.ai/docs/models/decision-laya

Источник: Unsloth documentation

Поддерживает: Documents local decision-model serving, including CPU execution and optional GPU.

Границы: Model execution and deployment are untested in this pack; pin a reviewed version before installation.



## S08 — GLiNER

https://github.com/urchade/GLiNER

Источник: Author repository

Поддерживает: Entity extraction accepts user-supplied entity labels.

Границы: Candidate span extraction is not proof of a task being completed or a permission being granted. Russian/code-mixed evaluation is required.



## S09 — SCIP

https://github.com/scip-code/scip

Источник: Project repository; redirects from sourcegraph/scip

Поддерживает: A protocol for code intelligence with ecosystem language indexers.

Границы: Choose a supported indexer; syntax parsing alone does not produce a complete runtime call graph.



## S10 — Docling

https://github.com/docling-project/docling

Источник: Project repository

Поддерживает: Document conversion can provide structured inputs to context pipelines.

Границы: Optional parser only. Raw files, page offsets and parser errors still need separate retention. No OCR was used in this delivery.



## S11 — DSPy

https://github.com/stanfordnlp/dspy

Источник: Author repository

Поддерживает: Modular model pipelines and optimization of prompts/weights.

Границы: Use held-out evaluation; do not tune and report on the same voice/repo cases.



## S12 — GEPA

https://github.com/gepa-ai/gepa

Источник: Author repository

Поддерживает: Reflective optimization evaluates candidate textual parameters and uses execution feedback.

Границы: Our proposed use is offline context-policy/skill optimization, not uncontrolled self-modification.



## S13 — GEPA paper

https://arxiv.org/abs/2507.19457

Источник: Research paper abstract, 2025

Поддерживает: Research basis for reflective optimization.

Границы: Reported task results do not transfer automatically to PC control or flashloan qualification.



## S14 — OpenTelemetry traces

https://opentelemetry.io/docs/concepts/signals/traces/

Источник: OpenTelemetry documentation

Поддерживает: Trace spans describe causally related operations and timing.

Границы: Tracing does not itself validate outcome correctness; keep source/effect receipts separately.



## S15 — Artifact attestations

https://docs.github.com/en/actions/concepts/security/artifact-attestations

Источник: GitHub documentation

Поддерживает: Attestations support verification of artifact build provenance.

Границы: Provenance is not proof of safe code. Permission diff, tests and local health check remain necessary.



## S16 — MCP specification

https://modelcontextprotocol.io/specification/2026-07-28

Источник: Official specification; current landing page redirected here during read

Поддерживает: Current specification links Tasks and Skills over MCP extensions.

Границы: Negotiate supported capabilities per client; not every AI web tab supports those extensions.



## S17 — Plugin submission

https://developers.openai.com/plugins/deploy/submission

Источник: OpenAI official documentation; apps-sdk submission redirected here

Поддерживает: Directory publication has package validation, review and publication steps.

Границы: A URL field or a personal connector is not automatic public listing. The earlier UI icon was not identified.



## S18 — Agent Skills

https://agentskills.io/home

Источник: Open format documentation

Поддерживает: A skill is a folder with SKILL.md and optional resources/scripts.

Границы: Instructions in a skill are not OS permission enforcement.



## S19 — LangGraph persistence

https://docs.langchain.com/oss/python/langgraph/persistence

Источник: LangChain official documentation

Поддерживает: Checkpointed graph state is a candidate for resumable agent workflows.

Границы: Do not add a parallel production queue over the existing SCE Core without a migration ADR.



## S20 — Introducing System One Models & Jev

https://typesafe.ai/blog/introducing-system-one-models-and-jev

Источник: TypeSafe author announcement, 15 September 2026

Поддерживает: State plus typed probabilistic decisions; host software owns surrounding workflow.

Границы: Type correctness is not semantic truth; performance figures are vendor claims, not Dell tests.



## S21 — Building a Harness with Jev

https://www.langchain.com/blog/building-a-harness-with-jev

Источник: LangChain integration authors, 17 September 2026

Поддерживает: Classifier middleware, model routing and structured decisions; links to browser and email demos on X.

Границы: Direct X posts failed to open here; the article is not independent verification of those demos.



## S22 — Node/TypeScript Laya runtime

https://github.com/receptron/laya

Источник: Project repository

Поддерживает: ONNX Runtime route for Node/TypeScript without Python at inference time.

Границы: Optional experiment; CPU/RAM, numeric parity and context truncation require local conformance tests.



## S23 — Laya Candle runtime

https://github.com/Trystan-SA/laya-candle

Источник: Project repository

Поддерживает: Rust/Candle local Laya port exists.

Границы: No Windows installation or performance comparison performed; not assumed equivalent to reference implementation.



## S24 — screenpipe

https://github.com/screenpipe/screenpipe

Источник: Project repository

Поддерживает: Accessibility-first/event-driven capture and local history can be an optional observation adapter.

Границы: Current source-available license and telemetry defaults need review; not described here as unrestricted open source or zero-network by default.



## S25 — UI Automation events

https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-eventsoverview

Источник: Microsoft Learn

Поддерживает: UI Automation clients can receive relevant UI events rather than constantly polling everything.

Границы: Accessibility providers may be incomplete; this source does not promise all app contents or complete history.



## S26 — xAI function calling

https://docs.x.ai/developers/tools/function-calling

Источник: xAI official documentation

Поддерживает: Model tool requests can be executed by client-side code and results returned to the model.

Границы: An API key or model response alone does not mount the PC or grant GitHub rights.



## S27 — ChatGPT/API billing

https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform

Источник: OpenAI Help

Поддерживает: ChatGPT subscription and API-platform billing are managed separately.

Границы: An API key is not an included Pro API credit allowance; separate supported sign-in products require their own eligibility check.



## S28 — Computer use

https://developers.openai.com/api/docs/guides/tools-computer-use

Источник: OpenAI API documentation

Поддерживает: Computer-use actions require an execution environment and an observe/act loop.

Границы: Optional fallback only; not a test of autonomous safety or device compatibility.

