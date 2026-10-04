# Теги V3: не единственная плоская классификация

Детерминированные поля: source URI, object hash, full original path, source revision, offsets/message IDs, capture producer, observed/ingested times, MIME, size, ingest status. Эти поля нельзя «предсказывать» Laya, если источник уже даёт их точно.

Предлагаемые моделью поля: project candidates, entity spans, intent/goal, role (idea/requirement/decision/code/evidence), topic, likely duplicate, contradictions, relevance to this task. Каждый такой label имеет model/version, input hash, confidence/calibration scope и source span. Ненадёжный label — CANDIDATE, не authoritative fact.

Authority: USER_INSTRUCTION / SOURCE_CODE / OBSERVED_RESULT / THIRD_PARTY_CLAIM / ASSISTANT_PROPOSAL. Proposed future behavior отделён от фактического состояния.

Execution state: PLANNED, IMPLEMENTED_UNVERIFIED, OFFLINE_VERIFIED, DEVICE_VERIFIED, BLOCKED, STALE, SUPERSEDED. Переход к verified требует receipt того же commit/env/task, а не голосования summaries.

Availability: AVAILABLE, PARTIAL, NOT_CAPTURED, UNSUPPORTED, DENIED, MISSING_DEPENDENCY, STALE, ERROR. «Нет информации» не равно «информация ложная».

Context quality — вектор, а не один магический score: source authority, freshness, task relevance, required-slot coverage, integrity, contradiction count, provenance, privacy eligibility. Hard constraints сначала; ranker выбирает внутри допустимого множества.

Relations: requires, implements, tested_by, observed_in, derived_from, copied_from, contradicts, supersedes, blocked_by, repairs. Copies одного сообщения не становятся независимыми confirmations.

Для web3-контекста добавить chain/protocol/version/state reference/timestamp и evidence type (fixture, offline replay, paper observation). Read-only market data и live execution authority никогда не смешиваются одним `financial` tag.

User deletes/retention requests должны удалять соответствующие originals и derived indexes согласно policy. «Immutable» здесь означает отсутствие скрытой перезаписи истории, а не запрет пользователю управлять своей информацией.
