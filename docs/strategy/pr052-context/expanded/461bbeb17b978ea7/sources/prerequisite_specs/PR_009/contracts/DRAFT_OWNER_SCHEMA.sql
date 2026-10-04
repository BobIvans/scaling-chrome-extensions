-- PROPOSED ADDITIVE FALLBACK, NOT INSTALLED APPLICATION MIGRATION.
-- Use existing original/source/extraction owner on actual HEAD if available.
-- Execute schema migration before BEGIN IMMEDIATE import transaction.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS import_raw_blobs(
  sha256 TEXT PRIMARY KEY NOT NULL CHECK(length(sha256)=64),
  byte_count INTEGER NOT NULL CHECK(byte_count>=0),
  raw BLOB NOT NULL CHECK(typeof(raw)='blob' AND length(raw)=byte_count)
);
CREATE TABLE IF NOT EXISTS import_source_versions(
  namespace TEXT NOT NULL, source_key TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
  source_version_id TEXT NOT NULL UNIQUE, first_observed_at REAL NOT NULL,
  PRIMARY KEY(namespace,source_key,raw_sha256),
  FOREIGN KEY(raw_sha256) REFERENCES import_raw_blobs(sha256)
);
CREATE TABLE IF NOT EXISTS import_origins(
  origin_id TEXT PRIMARY KEY NOT NULL,
  namespace TEXT NOT NULL, source_key TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
  origin_locator TEXT NOT NULL, scope_policy TEXT NOT NULL, first_observed_at REAL NOT NULL,
  FOREIGN KEY(namespace,source_key,raw_sha256)
    REFERENCES import_source_versions(namespace,source_key,raw_sha256)
);
CREATE TABLE IF NOT EXISTS import_extractions(
  namespace TEXT NOT NULL, source_key TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
  extractor_key TEXT NOT NULL, extraction_id TEXT NOT NULL UNIQUE,
  payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
  payload BLOB NOT NULL CHECK(typeof(payload)='blob'),
  disposition TEXT NOT NULL CHECK(disposition IN ('LOCAL_NODES_ACCOUNTED','PARTIAL_TOPOLOGY','ERROR')),
  first_observed_at REAL NOT NULL,
  PRIMARY KEY(namespace,source_key,raw_sha256,extractor_key),
  FOREIGN KEY(namespace,source_key,raw_sha256)
    REFERENCES import_source_versions(namespace,source_key,raw_sha256)
);
CREATE TABLE IF NOT EXISTS import_source_heads(
  namespace TEXT NOT NULL, source_key TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
  extractor_key TEXT NOT NULL, last_observed_at REAL NOT NULL,
  PRIMARY KEY(namespace,source_key),
  FOREIGN KEY(namespace,source_key,raw_sha256,extractor_key)
    REFERENCES import_extractions(namespace,source_key,raw_sha256,extractor_key)
);
-- Application verifies SHA256(raw/payload), versions, validated policy before commit
-- and on read; SQLite length checks alone do not prove SHA256 or immutability.
-- Updates to immutable version rows are forbidden by owner API; additive DDL
-- does not enforce every semantic rule via triggers. No automatic data deletion.
