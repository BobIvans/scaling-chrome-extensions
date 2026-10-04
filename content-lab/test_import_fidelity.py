"""Runtime checks for original bytes and selected ChatGPT JSON lineage."""

from contextlib import closing, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import content_lab as lab


FIXTURES = Path(__file__).parent / "fixtures" / "import_fidelity_golden"
CASES = json.loads((FIXTURES / "CASES.json").read_text(encoding="utf-8"))["cases"]


class ImportFidelityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "store"

    def sql(self, query, args=()):
        with closing(sqlite3.connect(self.store / "content.sqlite3")) as db:
            return db.execute(query, args).fetchall()

    def selected(self, name="F01", *, namespace="selected", source_key="export-main"):
        return lab.import_chatgpt_export(
            self.store, FIXTURES / "raw" / f"{name}.json", namespace,
            source_key=source_key)

    def test_fixture_sequence_and_exact_original_roundtrip(self):
        """18 supplied scenarios run through the real owner, not a SQL prototype."""
        first_version = first_extraction = None
        for case in CASES:
            case_id = case["case_id"]
            source = FIXTURES / case["raw_path"]
            raw = source.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), case["raw_sha256"])
            raw_before = (self.sql("SELECT count(*) FROM import_raw_blobs")[0][0]
                          if (self.store / "content.sqlite3").exists() else 0)
            if case_id == "F13":
                with patch.object(lab, "MAX_CHATGPT_EXPORT_BYTES", len(raw) - 1):
                    with self.assertRaisesRegex(ValueError, "byte budget"):
                        self.selected(case_id)
                continue
            if case_id == "F16":
                context = patch.object(lab, "FIDELITY_EXTRACTOR_VERSION", "fixture.v2")
            else:
                from contextlib import nullcontext
                context = nullcontext()
            namespace = "independent" if case_id == "F15" else "selected"
            with context:
                result = self.selected(case_id, namespace=namespace)
            if case["expected_disposition"] == "ERROR":
                self.assertEqual(result["state"], "ORIGINAL_RETAINED_EXTRACTION_ERROR", case_id)
                self.assertFalse(result["derived_heads_changed"])
            else:
                self.assertEqual(result["fidelity_disposition"],
                                 case["expected_disposition"], case_id)
                self.assertEqual(result["observed_nodes"], case["counts"]["nodes"], case_id)
            self.assertTrue(result["original_retained"], case_id)
            self.assertEqual(result["export_sha256"], case["raw_sha256"], case_id)
            self.assertEqual(self.sql("SELECT count(*) FROM import_raw_blobs")[0][0] - raw_before,
                             case["expected_new_records"]["new_raw_blobs"], case_id)
            target = self.root / (case_id + "-recovered.json")
            recovered = lab.read_chatgpt_original(
                self.store, result["source_version_id"], target)
            self.assertEqual((target.read_bytes(), recovered["byte_count"]), (raw, len(raw)))
            inspected = lab.inspect_chatgpt_import(
                self.store, result["source_version_id"], result["extraction_id"], limit=3)
            self.assertEqual(inspected["disposition"], case["expected_disposition"])
            self.assertLessEqual(len(inspected["nodes"]), 3)
            if case_id == "F01":
                first_version, first_extraction = result["source_version_id"], result["extraction_id"]
                self.assertEqual(raw[:3], b"\xef\xbb\xbf")
                self.assertIn(b"\r\n", raw)
                self.assertEqual(len(self.sql("SELECT * FROM import_node_ledger")), 9)
                self.assertEqual(len(self.sql("SELECT * FROM import_raw_blobs")), 1)
            if case_id in ("F02", "F03"):
                self.assertEqual((result["source_version_id"], result["extraction_id"]),
                                 (first_version, first_extraction))
                self.assertEqual(len(self.sql("SELECT * FROM import_raw_blobs")), 1)
            if case_id == "F03":
                self.assertEqual(len(self.sql("SELECT * FROM import_origins")), 3)
            if case_id == "F04":
                self.assertNotEqual(result["source_version_id"], first_version)
                self.assertEqual(result["new_versions"], 0)
            if case_id == "F05":
                self.assertEqual(result["new_versions"], 1)
            if case_id == "F06":
                self.assertEqual(result["new_versions"], 0)
            if case_id == "F16":
                self.assertNotEqual(result["extraction_id"], first_extraction)
            if case_id == "F08":
                self.assertIn("PARENT_CYCLE", result["topology_gaps"])
                self.assertIn("CURRENT_NODE_MISSING", result["topology_gaps"])

    def test_selected_reconciliation_and_metadata_revision(self):
        first = self.selected()
        initial_items = self.sql("SELECT id,payload FROM items ORDER BY id")
        second = self.selected("F06")  # Message/author/title metadata only.
        self.assertNotEqual(first["source_version_id"], second["source_version_id"])
        self.assertEqual(first["new_versions"], 5)
        self.assertEqual(second["new_versions"], 0)
        self.assertEqual(self.sql("SELECT id,payload FROM items ORDER BY id"), initial_items)
        selected_b = self.selected("F07")
        self.assertEqual(selected_b["missing_conversations"], 0)
        self.assertEqual(self.sql("SELECT present FROM chatgpt_conversations "
                                  "WHERE namespace='chatgpt:selected' AND conversation_id='conv-a'"), [(1,)])
        self.assertEqual(self.sql("SELECT count(*) FROM sync_heads WHERE "
                                  "namespace='chatgpt:selected' AND "
                                  "source_key LIKE 'chatgpt/conv-a/%' AND present=1"), [(4,)])
        self.assertEqual(selected_b["missing"], 0)
        self.selected("F18")
        self.assertGreaterEqual(len(self.sql("SELECT * FROM import_absences")), 1)
        self.assertEqual(set(row[0] for row in self.sql(
            "SELECT reason FROM import_absences")), {"NOT_OBSERVED_IN_SELECTED_EXPORT"})

    def test_storage_rollback_and_receipt_repair(self):
        with patch.object(lab, "_insert_item", side_effect=sqlite3.OperationalError("disk full")):
            result = self.selected()
        self.assertEqual(result["state"], "IMPORT_STORAGE_ERROR")
        self.assertFalse(result["original_retained"])
        self.assertEqual(self.sql("SELECT count(*) FROM import_raw_blobs"), [(0,)])
        self.assertEqual(self.sql("SELECT count(*) FROM sync_heads"), [(0,)])
        with patch.object(lab, "_write_receipt", side_effect=OSError("receipt denied")):
            result = self.selected()
        self.assertEqual(result["state"], "COMMITTED_WITH_RECEIPT_WARNING")
        self.assertEqual(self.sql("SELECT count(*) FROM items"), [(5,)])
        replay = self.selected()
        self.assertEqual(replay["new_versions"], 0)
        self.assertEqual(len(list((self.store / "items").glob("*.json"))), 5)

    def test_process_death_before_commit_leaves_no_original_or_heads(self):
        script = """import os, pathlib, content_lab as lab
def die(*args): os._exit(91)
lab._insert_item = die
lab.import_chatgpt_export(pathlib.Path(__import__('sys').argv[1]),
                          pathlib.Path(__import__('sys').argv[2]), 'selected')
"""
        child = subprocess.run(
            [sys.executable, "-c", script, str(self.store),
             str(FIXTURES / "raw" / "F01.json")],
            env={**os.environ, "PYTHONPATH": str(Path(lab.__file__).parent)},
            capture_output=True, check=False,
        )
        self.assertEqual(child.returncode, 91, child.stderr.decode())
        self.assertEqual(self.sql("SELECT count(*) FROM import_raw_blobs"), [(0,)])
        self.assertEqual(self.sql("SELECT count(*) FROM sync_heads"), [(0,)])
        self.assertEqual(self.selected()["state"], "IMPORTED_CHATGPT_EXPORT")

    def test_migration_cli_bounds_and_integrity(self):
        self.store.mkdir()
        with closing(lab._database(self.store)) as db:
            db.execute("INSERT INTO items VALUES ('old','{}')")
            db.commit()
        first = self.selected()
        second = self.selected()
        self.assertEqual(first["source_version_id"], second["source_version_id"])
        self.assertEqual(self.sql("SELECT payload FROM items WHERE id='old'"), [("{}",)])
        self.assertEqual(self.sql("SELECT count(*) FROM import_source_versions"), [(1,)])
        with self.assertRaisesRegex(ValueError, "PAGE_BOUNDARY"):
            lab.inspect_chatgpt_import(self.store, first["source_version_id"],
                                       first["extraction_id"], limit=101)
        target = self.root / "original.json"
        target.write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError, "DESTINATION_EXISTS"):
            lab.read_chatgpt_original(self.store, first["source_version_id"], target)
        self.assertEqual(target.read_bytes(), b"existing")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(lab.main(["inspect-chatgpt", "--store", str(self.store),
                                       "--version-id", first["source_version_id"],
                                       "--extraction-id", first["extraction_id"],
                                       "--limit", "2"]), 0)
        self.assertEqual(len(json.loads(out.getvalue())["nodes"]), 2)
        self.assertNotIn("original alpha", out.getvalue())
        with closing(sqlite3.connect(self.store / "content.sqlite3")) as db:
            db.execute("UPDATE import_node_ledger SET payload=? WHERE ordinal=0",
                       (b'{"tampered":true}',))
            db.commit()
        with self.assertRaisesRegex(ValueError, "NODE_LEDGER_INTEGRITY"):
            lab.inspect_chatgpt_import(self.store, first["source_version_id"],
                                       first["extraction_id"])
        with closing(sqlite3.connect(self.store / "content.sqlite3")) as db:
            db.execute("UPDATE import_raw_blobs SET raw=? WHERE sha256=?",
                       (b"x" * first["input_bytes"], first["export_sha256"]))
            db.commit()
        with self.assertRaisesRegex(ValueError, "ORIGINAL_INTEGRITY"):
            lab.read_chatgpt_original(self.store, first["source_version_id"], target,
                                      overwrite=True)
        self.assertEqual(target.read_bytes(), b"existing")

    def test_capture_guard_and_total_node_budget(self):
        with patch.object(lab, "MAX_CHATGPT_NODES", 8):
            outcome = self.selected()
        self.assertEqual(outcome["reason_code"], "ERROR_NODE_BUDGET")
        self.assertEqual(self.sql("SELECT count(*) FROM sync_heads"), [(0,)])
        with patch.object(lab, "MAX_CHATGPT_LEDGER_BYTES", 20):
            outcome = self.selected("F04")
        self.assertEqual(outcome["reason_code"], "ERROR_LEDGER_BUDGET")
        with patch.object(lab, "_capture_chatgpt_export", side_effect=OSError("read failed")):
            with self.assertRaises(OSError):
                self.selected("F05")
        self.assertEqual(self.sql("SELECT count(*) FROM import_raw_blobs"), [(2,)])


if __name__ == "__main__":
    unittest.main()
