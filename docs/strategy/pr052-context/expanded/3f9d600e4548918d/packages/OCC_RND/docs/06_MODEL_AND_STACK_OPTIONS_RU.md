# Что исследовать из Hugging Face и GitHub

Ниже не «рейтинг SOTA на Dell», а shortlist для одинакового локального benchmark. Все источники — первичные; checked 2026-10-03. Не скачивались веса, не измерялись latency/RAM, не проверялась production-совместимость на твоём ПК.

| Слой | Кандидат | Эксперимент и ограничение |
|---|---|---|
| Speech baseline | faster-whisper [S18] | CPU/int8, собственный RU/EN корпус, final-intent accuracy |
| ASR challenger | Qwen3-ASR-0.6B [S19] | Сравнить потоковый/непотоковый путь выбранного runtime, не переносить чужой throughput на one-user latency |
| Typed router | Laya [S03,S04] | Routing/escalation на outcome-labelled cases; не authority grant |
| Remote decision baseline | Jev [S01,S02] | Тот же dataset/prompts/outcomes; отдельно учитывать сеть и стоимость |
| Small function caller | FunctionGemma 270M [S20] | Ограниченный tool vocabulary, held-out aliases, licence review |
| Local generator | LFM2.5-1.2B-Instruct [S21] | План короткой задачи vs deterministic template; не запускать большой набор моделей одновременно |
| Visual triage | SmolVLM-256M [S22] | Дать screen region category; сравнить с UIA/DOM без vision |
| Semantic retrieval | Qwen3-Embedding-0.6B [S23] | Recall@k по реальным старым запросам, рядом с lexical baseline |
| Heavier computer use | Fara-7B / UI-TARS / Agent-S [S09,S08,S07] | Изолированный benchmark/VPS/GPU при необходимости; не default always-on на Dell |
| Document structure | Docling / MarkItDown [S24,S25] | Сравнить extraction coverage и ссылки на оригинальные страницы/объекты |
| OCR fallback | Surya [S26] | Только для изображений без доступного исходного текста; оценивать отдельную ошибку OCR |

## Исследовать системы, не только модели

Microsoft UFO сейчас описывает UFO³ Galaxy и отдельно поддерживаемый Windows-путь UFO²: полезно изучить разделение агента приложения, глобального планирования и распределённого управления. [S05] Это не повод запускать распределённый флот для одной папки на Dell. Сначала single-device вертикальный срез.

Playwright MCP и browser-use дают разные пути к browser automation. [S10,S11] Изучить сохранение состояния, permission boundary, локаторы и верификацию. Не подключать основной Chrome-профиль с банковскими/кошельковыми сессиями к экспериментальному агенту.

LangGraph persistence и smolagents полезны как reference для checkpoints и code-agent loops. [S16,S17] У тебя уже есть durable queue в SCE; framework должен заменить конкретную недостающую функцию или адаптироваться к owner, а не добавить ещё одну независимую «истину» о статусе jobs.

## Выбор для первого Dell-профиля — проектное предложение

Без моделей: архив, Git, AST, FTS/поиск и receipts должны работать полностью. Затем один ASR worker, затем один router по потребности, затем API escalation только для сложного планирования. Тяжёлый visual planner не держать постоянно вместе со всеми остальными моделями. Перед выбором квантования замерить фактическую RAM, cold start, p95, батарею и частоту ошибок.

Не объявлять open-source автоматически бесплатным в эксплуатации: остаются память, электричество, сеть, обслуживание и лицензии. Для каждого кандидата pin revision/runtime/tokenizer, хэши, dependency lock и model licence; `trust_remote_code` не включать автоматически.

## Исторические имена, которые требуют отдельной новой проверки

Spark-X2.5-4B, Chronos-2, TimesFM3, TabPFN2.5, Web3-fine-tuned Laya и «model parliament» встречались в восстановленной истории как предложения. Этот пакет не выдаёт их за текущий независимо проверенный стек. Исследовать их после baseline по конкретной задаче, а не из-за названия волны.
