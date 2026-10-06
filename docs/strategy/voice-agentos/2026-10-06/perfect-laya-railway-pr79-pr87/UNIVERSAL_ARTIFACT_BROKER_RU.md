# Universal Artifact & Download Broker
Chrome already has downloads permission, but current code lacks a generic artifact owner.

Inputs: Chrome downloads events; WebMCP/CDP/DOM download actions; Drive API/export; Drive UI download/export; watched folders; explicit import; future connectors.

ArtifactRecord: artifact_id, source kind, filename, MIME, bytes, SHA-256, URL, exact tab/document/account/workspace/file identity when known, goal/lane/effect IDs, timestamps, provenance, quarantine, extractor status, derived records, labels/relations, coverage/warnings.

Any MIME: always preserve allowed raw bytes. Extractor registry is additive: text/code/JSON/XML/CSV/PDF/DOCX/XLSX/PPTX/images/audio/video/archives/unknown binary metadata. Never auto-execute downloaded executables/scripts.

Drive UI fallback: bind exact Google account and selected file → prefer structured capability → otherwise exact DOM/AX/CDP → invoke download/export once → observe Chrome download receipt → ingest exact bytes → attach Drive/file/account provenance. Visible text alone never proves complete document capture.
