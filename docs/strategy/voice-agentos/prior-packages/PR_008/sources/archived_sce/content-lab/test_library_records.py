import copy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from content_lab import apply_library_record


class LibraryRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        self.base = {
            "schema": "occ.library-record.v1", "namespace": "docs",
            "sourceKey": "record-1", "revision": 1, "parentRevision": None,
            "tombstone": False,
            "provenance": {
                "source": "selected Chrome library", "savedAt": "2026-10-01T10:00:00.000Z",
                "capturedAt": "2026-09-30T09:00:00.000Z", "status": "EXTRACTED",
                "warnings": ["fixture provenance"], "project": "OCC", "session": "wave-18",
            },
            "content": {"name": "Roadmap", "text": "first searchable revision", "sha256": ""},
        }
        self.hash_content(self.base)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def hash_content(mutation):
        if mutation["content"] is not None:
            mutation["content"]["sha256"] = hashlib.sha256(
                mutation["content"]["text"].encode("utf-8")
            ).hexdigest()
        return mutation

    def rows(self, query, values=()):
        with closing(sqlite3.connect(self.store / "content.sqlite3")) as connection:
            return connection.execute(query, values).fetchall()

    def test_versions_use_existing_items_owner_and_preserve_provenance(self):
        created = apply_library_record(self.store, self.base)
        self.assertEqual((created["state"], created["revision"], created["tombstone"]),
                         ("APPLIED", 1, False))
        edit = copy.deepcopy(self.base)
        edit.update(revision=2, parentRevision=1)
        edit["content"]["text"] = "second searchable revision"
        edit["provenance"]["savedAt"] = "2026-10-01T10:01:00.000Z"
        self.hash_content(edit)
        updated = apply_library_record(self.store, edit)
        self.assertNotEqual(updated["itemId"], created["itemId"])
        head = self.rows("SELECT revision,tombstone,item_id FROM library_record_heads")[0]
        self.assertEqual(head, (2, 0, updated["itemId"]))
        payload = json.loads(self.rows("SELECT payload FROM items WHERE id=?",
                                       (updated["itemId"],))[0][0])
        self.assertEqual(payload["provenance"], edit["provenance"])
        self.assertEqual(self.rows("SELECT count(*) FROM items")[0][0], 2)
        self.assertEqual(self.rows("SELECT present FROM sync_heads")[0][0], 1)

    def test_stale_edit_and_same_revision_conflict_are_atomic(self):
        apply_library_record(self.store, self.base)
        stale = copy.deepcopy(self.base)
        stale.update(revision=3, parentRevision=1)
        stale["content"]["text"] = "skipped revision"
        self.hash_content(stale)
        with self.assertRaisesRegex(ValueError, "STALE_RECORD"):
            apply_library_record(self.store, stale)
        conflicting = copy.deepcopy(self.base)
        conflicting["content"]["text"] = "same revision, different bytes"
        self.hash_content(conflicting)
        with self.assertRaisesRegex(ValueError, "REVISION_CONTENT"):
            apply_library_record(self.store, conflicting)
        self.assertEqual(self.rows("SELECT count(*) FROM library_record_versions")[0][0], 1)
        self.assertEqual(apply_library_record(self.store, self.base)["state"], "UNCHANGED")

    def test_tombstone_hides_head_and_blocks_stale_resurrection(self):
        first = apply_library_record(self.store, self.base)
        deleted = copy.deepcopy(self.base)
        deleted.update(revision=2, parentRevision=1, tombstone=True, content=None)
        result = apply_library_record(self.store, deleted)
        self.assertEqual((result["tombstone"], result["itemId"]), (True, first["itemId"]))
        self.assertEqual(apply_library_record(self.store, deleted),
                         {**result, "state": "UNCHANGED"})
        self.assertEqual(self.rows("SELECT present FROM sync_heads")[0][0], 0)
        provenance = json.loads(self.rows(
            "SELECT provenance FROM library_record_versions WHERE revision=2"
        )[0][0])
        self.assertEqual(provenance, deleted["provenance"])
        stale = copy.deepcopy(self.base)
        stale.update(revision=2, parentRevision=1)
        stale["content"]["text"] = "stale resurrection"
        self.hash_content(stale)
        with self.assertRaisesRegex(ValueError, "REVISION_CONTENT"):
            apply_library_record(self.store, stale)
        self.assertEqual(self.rows("SELECT present FROM sync_heads")[0][0], 0)

    def test_invalid_hash_and_unbounded_text_do_not_create_store(self):
        invalid = copy.deepcopy(self.base)
        invalid["content"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "CONTENT_HASH"):
            apply_library_record(self.store, invalid)
        large = copy.deepcopy(self.base)
        large["content"]["text"] = "x" * 8001
        self.hash_content(large)
        with self.assertRaisesRegex(ValueError, "CONTENT_SCHEMA"):
            apply_library_record(self.store, large)
        self.assertFalse((self.store / "content.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
