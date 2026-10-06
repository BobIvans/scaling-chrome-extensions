# Experimental Models / Intelligence Lab

These are optional experiments, not mandatory production dependencies.

## Cheap text/structure

- Laya: primary typed System-1 router.
- GLiNER2.5 Multi-class experiment: entity/relation extraction for documents/web3 observations.
- Qwen3-Embedding-class models: local semantic retrieval/code/context indexing.
- Docling: structured document extraction.

## Local visual

### SmolVLM 256M / 500M
Very small multimodal models suitable for cheap captioning, document QA/basic visual reasoning. 500M is a reasonable experiment for constrained hardware.

### ScreenVLM / ScreenParser
Current Docling/IBM ScreenVLM is a compact screen parser that emits structured UI elements, bounding boxes, semantic classes and visible text. Good fallback experiment when DOM/UIA state is unavailable.

### Qwen3-VL-2B-Instruct
Stronger small VLM; model card explicitly describes visual-agent / GUI interaction capabilities. Heavier than SmolVLM; use as optional local/alternate-machine tier, benchmark before adopting on a CPU laptop.

## Rule

Do not use vision just because it is impressive.
Structured WebMCP/CDP/DOM/UIA evidence is cheaper and more exact.
Vision handles gaps.