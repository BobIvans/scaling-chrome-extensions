# Cheapest Reliable Intelligence Policy

## Rule

Never ask a model to do what exact code can already do.

## Zero-LLM examples

- hash/version/dedupe;
- MIME/type labels;
- exact metadata labels;
- known DOM/AX/WebMCP action;
- known download/export;
- known command/test;
- exact numeric comparison;
- deterministic route/pair filters;
- replay a qualified recipe;
- source freshness checks;
- simple threshold alarms.

## Local-lightweight examples

- Laya: bounded route/choice/score;
- embeddings: retrieval/ranking;
- GLiNER-class extraction: entities/relations;
- ASR: voice transcription;
- tiny OCR/VLM: screenshot triage/basic document/screen parsing.

## Strong-model examples

- unfamiliar UI semantics;
- novel web3 protocol research;
- code architecture/change;
- contradictory multi-source synthesis;
- visual ambiguity;
- strategy redesign;
- procedure repair after drift.

## Cost memory

For each semantic task class store:
- provider;
- model;
- success;
- latency;
- tokens/plan quota;
- monetary cost;
- context size;
- whether output became reusable procedure.

Router learns the cheapest provider meeting the target success threshold.