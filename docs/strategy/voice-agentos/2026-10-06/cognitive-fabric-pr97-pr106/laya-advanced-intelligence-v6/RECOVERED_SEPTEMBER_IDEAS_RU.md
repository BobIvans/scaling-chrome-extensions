# Recovered September/older ideas — exact direction that should be preserved

## September 4–14: authenticated web3/browser research

Earlier architecture already aimed at:
- Playwright/CDP/MCP/browser-use style observation;
- authenticated UI scans;
- semantic DOM + accessibility + screenshot + network/console evidence;
- typed extraction of `pair_name`, liquidity, volatility, fees, quotes and route-relevant values;
- multi-site Jupiter/Meteora/Raydium research;
- read-only `web3` plugin;
- persistent `runs/<task>/` evidence folders;
- screenshots/network/sources/findings/actions per run;
- `recipes/web3-arbitrage-research.json`;
- workflow recorder → reusable recipes;
- 2 parallel read-only workers, with login/wallet/stateful writes serialized;
- cheap local LFM-class model for routine browser steps and stronger model only on low confidence / unknown page / recovery.

## September 8–13: local task-driven app, not model-owned browser

Earlier user preference:
- Chrome/local app as “eyes and hands”;
- separate AI chats/planner/researcher;
- relay data between chats and browser;
- DOM snapshots with element refs;
- minimal-context observations;
- two-chat verification;
- saved evidence URL/page-fragment/time;
- demonstrations → reusable workflows;
- invoke chat only on deviation.

This is the core principle of V6:
**the local app owns state and execution; AI sessions are cognitive copilots.**

## September 9–12: self-improving skill compiler

Earlier ideas:
- record workflows into reusable `SKILL.md`/recipes;
- Failure Capsules;
- Failure-to-Skill Compiler;
- skill lifecycle states;
- browser agents + OpenHands/code worker;
- one qualified workflow should run without repeated model calls until drift.

Modern mapping:
`AI discovery → SemanticRecipe → fixture/replay → canary → REGISTERED capability → deterministic reuse`.

## September 19: Universal Market Opportunity Compiler

Earlier market architecture:
`streams → immutable journal → market-state twins → anomaly workers → exact solver → chain compiler → simulation → execution → learning`

Important retained data:
timestamps, state versions, decoder versions, candidates, screenshots/DOM/network evidence, simulations, submissions and finalized outcomes.

Modern mapping:
AgentOS ContextGraph + market evidence graph + Qualification Campaign.

## September 21–30: Notion competitor / Context Hub

Earlier Context Hub ideas:
- local canonical context objects from voice/browser/files/chats/Telegram/Notion/GitHub;
- universal capture;
- project memory with decisions and failed attempts;
- fresh-context handoff;
- context shopping cart;
- evidence packs;
- terminal/browser session capture;
- source provenance;
- Notion-like structured control plane;
- Universal Ingestion → normalization → knowledge/provenance graph → research/goal engines → automation compiler → execution graph.

Modern mapping:
Project Capsule / Context Canvas + JIT ContextPack + durable Goal/Railway.

## Named experimental models/tools previously discussed

- Laya — short structured routing/choice.
- GLiNER2.5 Multi — entity/relation extraction experiment.
- Qwen3-ASR — Russian/voice transcription experiment.
- Qwen3-Embedding — context/code retrieval.
- Docling — document parsing.
- Qwen3.5-4B / local Qwen — generative local fallback.
- smolagents — lightweight agent experiments.
- DeepSite — site/visual-web experimentation.
- LFM 1.2B-class local model — cheap browser-step policy.
- stronger remote “Spark”/large model escalation on invalid JSON, low confidence, unknown page or recovery.

V6 treats these as replaceable capability providers, not hard-coded dependencies.