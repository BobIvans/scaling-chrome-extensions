# Проверенные первичные источники

Дата проверки: 3 октября 2026 года. Ссылки [Sxx]/[Gxx] в документах раскрываются здесь. Это список источников, не копия сторонних репозиториев или моделей. Тексты документации могут изменяться.

## S01 — TypeSafe: Introducing System One Models & Jev
https://typesafe.ai/blog/introducing-system-one-models-and-jev

Creator announcement; published 2026-09-15. Decision model, not a PC executor.

## S02 — LangChain: Building a harness with Jev
https://www.langchain.com/blog/building-a-harness-with-jev

Primary integration example; published 2026-09-17. Harness is distinct from decision model.

## S03 — Laya model card
https://huggingface.co/convaiinnovations/laya

Creator-reported context, benchmark and calibration limitations. See the concise source note; no Dell benchmark performed.

## S04 — Laya source repository
https://github.com/NandhaKishorM/laya

Official implementation and integration reference. Pin a reviewed revision, not an unbounded latest dependency.

## S05 — Microsoft UFO
https://github.com/microsoft/UFO

Current README presents UFO³ Galaxy and retained UFO² Windows support. Architectural research reference.

## S06 — OpenAdapt
https://github.com/OpenAdaptAI/OpenAdapt

Demonstration-to-program automation; independent result verification is an important design pattern.

## S07 — Simular Agent-S
https://github.com/simular-ai/Agent-S

Computer-use agent framework. Candidate for controlled benchmark comparisons.

## S08 — ByteDance UI-TARS
https://github.com/bytedance/UI-TARS

GUI-agent research. Not assumed suitable for real-time inference on this Dell.

## S09 — Microsoft Fara-7B
https://huggingface.co/microsoft/Fara-7B

Computer-use research model; separate browser tasks from general Windows desktop claims.

## S10 — Microsoft Playwright MCP
https://github.com/microsoft/playwright-mcp

Browser automation integration; structured browser state before screenshot fallback.

## S11 — browser-use
https://github.com/browser-use/browser-use

Browser-agent implementation candidate; evaluate authority and state-verification boundaries.

## S12 — Windows UI Automation
https://learn.microsoft.com/en-us/windows/win32/winauto/entry-uiauto-win32

Official Windows accessibility/automation API reference.

## S13 — FlaUI
https://github.com/FlaUI/FlaUI

Windows .NET UI Automation library; candidate for native desktop adapter.

## S14 — pywinauto
https://github.com/pywinauto/pywinauto

Python Windows automation library; alternative adapter for a Python-first prototype.

## S15 — NVDA
https://github.com/nvaccess/nvda

Screen-reader project; target for keyboard and accessibility validation, not merely visual inspection.

## S16 — LangGraph persistence
https://docs.langchain.com/oss/python/langgraph/persistence

State persistence/checkpoint design reference; not required to replace the existing SCE owner.

## S17 — Hugging Face smolagents
https://huggingface.co/docs/smolagents/index

Code-agent framework; generated code still needs isolation, permissions and evaluation.

## S18 — faster-whisper
https://github.com/SYSTRAN/faster-whisper

CTranslate2 transcription implementation; CPU/int8 is a candidate baseline, not a measured speed claim.

## S19 — Qwen3-ASR-0.6B
https://huggingface.co/Qwen/Qwen3-ASR-0.6B

Small ASR research candidate. Verify the supported runtime, language and streaming mode actually used.

## S20 — FunctionGemma 270M
https://huggingface.co/google/functiongemma-270m-it

Small function-calling specialist; review Gemma terms and domain adaptation needs.

## S21 — LFM2.5-1.2B-Instruct
https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct

Compact local generation candidate; measure actual end-to-end latency and memory.

## S22 — SmolVLM-256M-Instruct
https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct

Small visual-description/triage candidate, not assumed to be a reliable full-PC operator.

## S23 — Qwen3-Embedding-0.6B
https://huggingface.co/Qwen/Qwen3-Embedding-0.6B

Semantic retrieval candidate; compare against lexical retrieval before adding runtime cost.

## S24 — Docling
https://github.com/docling-project/docling

Document conversion and structure extraction; keep originals separately.

## S25 — Microsoft MarkItDown
https://github.com/microsoft/markitdown

Document-to-Markdown extraction option; extracted text is a projection, not the original.

## S26 — Surya
https://github.com/datalab-to/surya

OCR/layout fallback research; review code and model licensing separately.

## S27 — AFFiNE
https://github.com/toeverything/AFFiNE

Workspace/editor reference; compare adoption cost and licences rather than rewrite every editor component.

## S28 — AppFlowy
https://github.com/AppFlowy-IO/AppFlowy

Workspace/editor reference; do not conflate a good editor with an automation evidence engine.

## S29 — VS Code command-line interface
https://code.visualstudio.com/docs/configure/command-line

External editor integration using CLI; a smaller initial surface than embedding an IDE.

## S30 — OpenAI function calling
https://developers.openai.com/api/docs/guides/function-calling

Official API tool-call reference. The application executes and verifies tools.

## S31 — OpenAI computer use
https://developers.openai.com/api/docs/guides/tools-computer-use

Official computer-use reference; isolate execution and review high-impact actions.

## S32 — ChatGPT Plus and API billing
https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus

Official plan help: API usage is separate from ChatGPT subscription billing; do not infer quota from a chat plan.

## S33 — Solana transactions
https://solana.com/docs/core/transactions

Atomic transaction and account model reference for strategy/execution separation.

## S34 — Jito low-latency transaction send
https://docs.jito.wtf/lowlatencytxnsend/

Bundle and submission reference. Verify current provider limits/fees before any live design.

## G01 — scaling-chrome-extensions/da6abf4c006e4e7d26fe45ef30fa9d07a356f396
https://github.com/BobIvans/scaling-chrome-extensions/commit/da6abf4c006e4e7d26fe45ef30fa9d07a356f396

Pinned branch metadata: PR37 merged, 2026-10-03T15:58:25Z.

## G02 — studious-pancake/67d3852cbc4cb1b24582df45adbf6a42d4da2af0
https://github.com/BobIvans/studious-pancake/commit/67d3852cbc4cb1b24582df45adbf6a42d4da2af0

Pinned branch metadata: PR562 merged, 2026-10-02T23:07:26Z.

## G03 — scaling-chrome-extensions/content-lab/automation_core.py
https://github.com/BobIvans/scaling-chrome-extensions/blob/da6abf4c006e4e7d26fe45ef30fa9d07a356f396/content-lab/automation_core.py

Read lines 1–260; actual sync/context/one-writer policy limits.

## G04 — scaling-chrome-extensions/content-lab/context_review.py
https://github.com/BobIvans/scaling-chrome-extensions/blob/da6abf4c006e4e7d26fe45ef30fa9d07a356f396/content-lab/context_review.py

Read lines 1–150; review context pack uses 48,000 bytes.

## G05 — scaling-chrome-extensions/content-lab/repo_context.py
https://github.com/BobIvans/scaling-chrome-extensions/blob/da6abf4c006e4e7d26fe45ef30fa9d07a356f396/content-lab/repo_context.py

Read lines 1–240; resumable pages, 8 MiB file cap, 20 is page size.

## G06 — scaling-chrome-extensions/content-lab/occ-config/paper_campaign.plan.json
https://github.com/BobIvans/scaling-chrome-extensions/blob/da6abf4c006e4e7d26fe45ef30fa9d07a356f396/content-lab/occ-config/paper_campaign.plan.json

Full proposal read; explicitly BLOCKED_NOT_STARTED and not native-adapter compatible.

## G07 — scaling-chrome-extensions/agent-bridge/QUALIFICATION_ADAPTER_RU.md
https://github.com/BobIvans/scaling-chrome-extensions/blob/da6abf4c006e4e7d26fe45ef30fa9d07a356f396/agent-bridge/QUALIFICATION_ADAPTER_RU.md

Full document read; direct CLI works without Chrome; no live permissions.

## G08 — studious-pancake/scripts/run_occ_memory_qualification.py
https://github.com/BobIvans/studious-pancake/blob/67d3852cbc4cb1b24582df45adbf6a42d4da2af0/scripts/run_occ_memory_qualification.py

Full script read; exact wrapper arguments and domain exit codes.

## G09 — studious-pancake/src/occ_memory_qualification_bridge.py
https://github.com/BobIvans/studious-pancake/blob/67d3852cbc4cb1b24582df45adbf6a42d4da2af0/src/occ_memory_qualification_bridge.py

Read lines 1–210; exact schemas/operator profile and FAST-Q1 ownership.

## G10 — studious-pancake/src/qualification_report.py
https://github.com/BobIvans/studious-pancake/blob/67d3852cbc4cb1b24582df45adbf6a42d4da2af0/src/qualification_report.py

Read lines 1–240; exact preflight argv and paper-only environment.
