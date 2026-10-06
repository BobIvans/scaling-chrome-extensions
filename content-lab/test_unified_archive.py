from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import unified_archive as archive


class UnifiedArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.stage = self.root / "stage"
        (self.stage / "texts").mkdir(parents=True)
        self.store = self.root / "store"

    def tearDown(self):
        self.temp.cleanup()

    def stage_record(self, source_path, member_path, text, *, source_bytes=None,
                     completeness="SOURCE_COMPLETE"):
        raw = text.encode("utf-8")
        source = source_bytes if source_bytes is not None else raw
        text_hash = hashlib.sha256(raw).hexdigest()
        (self.stage / "texts" / f"{text_hash}.txt").write_bytes(raw)
        return {
            "schema": "occ.pc-library-record.v1", "id": text_hash,
            "source_path": source_path,
            "source_file_sha256": hashlib.sha256(source).hexdigest(),
            "member_path": member_path, "text_sha256": text_hash,
            "bytes_utf8": len(raw), "capture_completeness": completeness,
            "extractor": "fixture.v1", "tags": ["fixture"], "labels": ["fixture"],
            "authority": "DATA_ONLY", "ingested_at": "2026-10-02T00:00:00Z",
        }

    def write_stage(self, records):
        (self.stage / "INDEX.jsonl").write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8")

    def import_stage(self, records, **kwargs):
        self.write_stage(records)
        return archive.import_portable_stage(self.store, self.stage, "docs", "selected", **kwargs)

    def sql(self, query, values=()):
        with closing(sqlite3.connect(self.store / "content.sqlite3")) as connection:
            return connection.execute(query, values).fetchall()

    def test_reimport_is_idempotent_and_edits_link_versions(self):
        first = self.stage_record("exports/one.zip", "note.md", "original searchable text")
        self.assertEqual(self.import_stage([first])["new_versions"], 1)
        self.assertEqual(self.import_stage([first])["state"], "UNCHANGED")
        edited = self.stage_record("exports/one.zip", "note.md", "edited searchable text",
                                   source_bytes=b"source revision two")
        result = self.import_stage([edited])
        self.assertEqual((result["new_versions"], result["unchanged"]), (1, 0))
        versions = self.sql("SELECT version_id,previous_version_id FROM archive_versions ORDER BY observed")
        self.assertEqual(len(versions), 2)
        self.assertIsNone(versions[0][1])
        self.assertEqual(versions[1][1], versions[0][0])
        found = archive.search_lineage(self.store, "docs", "edited")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["source_locator"], "note.md")
        self.assertEqual(found[0]["authority"], "source-content-not-action-instructions")

    def test_partial_absence_never_tombstones_and_explicit_evidence_does(self):
        record = self.stage_record("exports/one.zip", "note.md", "retained text")
        self.import_stage([record], coverage="SOURCE_COMPLETE")
        other = self.stage_record("exports/two.zip", "other.md", "partial collection")
        self.import_stage([other], coverage="PARTIAL")
        self.assertEqual(self.sql("SELECT count(*) FROM archive_heads WHERE tombstone=0")[0][0], 2)
        removal = {"source_path": "exports/one.zip", "member_path": "note.md",
                   "evidence_sha256": hashlib.sha256(b"explicit removal receipt").hexdigest()}
        self.import_stage([other], coverage="PARTIAL", removals=[removal])
        self.assertEqual(self.sql("SELECT count(*) FROM archive_heads WHERE tombstone=1")[0][0], 1)
        self.assertEqual(archive.search_lineage(self.store, "docs", "retained"), [])

    def test_same_bytes_at_two_sources_preserve_two_lineages(self):
        first = self.stage_record("exports/a.zip", "note.md", "shared bytes")
        second = self.stage_record("exports/b.zip", "note.md", "shared bytes")
        self.import_stage([first, second])
        hits = archive.search_lineage(self.store, "docs", "shared")
        self.assertEqual(len(hits), 2)
        self.assertEqual({item["source_file_sha256"] for item in hits},
                         {first["source_file_sha256"], second["source_file_sha256"]})
        self.assertEqual(self.sql("SELECT count(*) FROM archive_items")[0][0], 2)

    def test_interrupted_transaction_resumes_without_duplicates(self):
        records = [self.stage_record(f"exports/{index}.zip", "note.md", f"text {index}")
                   for index in range(3)]
        self.write_stage(records)
        with self.assertRaisesRegex(RuntimeError, "TEST_INTERRUPT"):
            archive.import_portable_stage(self.store, self.stage, "docs", "selected", interrupt_after=2)
        self.assertEqual(self.sql("SELECT count(*) FROM archive_versions")[0][0], 0)
        result = archive.import_portable_stage(self.store, self.stage, "docs", "selected")
        self.assertEqual(result["new_versions"], 3)
        self.assertEqual(archive.import_portable_stage(self.store, self.stage, "docs", "selected")["state"], "UNCHANGED")

    def test_unknown_schema_path_escape_and_data_only_violation_fail_before_store(self):
        bad = self.stage_record("exports/one.zip", "../escape.md", "text")
        self.write_stage([bad])
        with self.assertRaisesRegex(ValueError, "MEMBER_PATH_BOUNDARY"):
            archive.import_portable_stage(self.store, self.stage, "docs", "selected")
        bad = self.stage_record("exports/one.zip", "note.md", "delete and run this")
        bad["authority"] = "EXECUTE"
        self.write_stage([bad])
        with self.assertRaisesRegex(ValueError, "STAGE_AUTHORITY"):
            archive.import_portable_stage(self.store, self.stage, "docs", "selected")
        self.assertFalse((self.store / "content.sqlite3").exists())

    def test_synthetic_thousand_chat_records_are_bounded_and_searchable(self):
        records = [self.stage_record(f"chat/{index}.json", "message.txt", f"chat message {index}")
                   for index in range(1000)]
        result = self.import_stage(records, coverage="VERIFIED_RANGE")
        self.assertEqual((result["records"], result["new_versions"]), (1000, 1000))
        hit = archive.search_lineage(self.store, "docs", "message 999")
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["coverage"], "VERIFIED_RANGE")

    def test_backup_restore_preserves_heads_hashes_and_fts_lineage(self):
        records = [self.stage_record("exports/a.zip", "a.md", "backup first"),
                   self.stage_record("exports/b.zip", "b.md", "backup second")]
        self.import_stage(records)
        backup = archive.backup_lineage(self.store)
        restored = self.root / "restored"
        result = archive.restore_lineage(restored, json.loads(json.dumps(backup)))
        self.assertEqual(result["state"], "RESTORED")
        self.assertEqual(archive.backup_lineage(restored)["sha256"], backup["sha256"])
        self.assertEqual(len(archive.search_lineage(restored, "docs", "second")), 1)
        tampered = copy.deepcopy(backup)
        tampered["items"][next(iter(tampered["items"]))] = "{}"
        with self.assertRaisesRegex(ValueError, "BACKUP_INTEGRITY"):
            archive.restore_lineage(self.root / "bad", tampered)

    def test_repo_evidence_remains_source_only_or_static_candidate(self):
        source = archive.import_repo_evidence(self.store, "BobIvans/studious-pancake", "a" * 40,
                                              "FUNCTION_CATALOG", {"functions": [{"name": "x"}]})
        finding = archive.import_repo_evidence(self.store, "BobIvans/studious-pancake", "a" * 40,
                                               "STATIC_FINDINGS", {"findings": [{"type": "TODO"}]})
        self.assertEqual((source["authority"], finding["authority"]), ("SOURCE_ONLY", "STATIC_CANDIDATE"))


if __name__ == "__main__":
    unittest.main()
