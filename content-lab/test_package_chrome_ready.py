import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


SCRIPT = (Path(__file__).resolve().parent.parent / "one-click-context" /
          "scripts" / "package_chrome_ready.py")
SPEC = importlib.util.spec_from_file_location("package_chrome_ready", SCRIPT)
package_chrome_ready = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package_chrome_ready)


class PackageChromeReadyTests(unittest.TestCase):
    def test_tree_digest_is_path_length_and_byte_sensitive(self):
        digest = package_chrome_ready._tree_digest
        self.assertEqual(digest({"a": b"x", "b": b"y"}),
                         "bd7ae9a9949344483a8b1c2bf794dbd7c2449b53af3908d954e6142a1ea89a0a")
        self.assertEqual(digest({"a": b"x", "b": b"y"}),
                         digest({"b": b"y", "a": b"x"}))
        self.assertNotEqual(digest({"a": b"x"}), digest({"a": b"y"}))
        self.assertNotEqual(digest({"a": b"x"}), digest({"b": b"x"}))

    def test_archive_identity_covers_every_installed_source_byte(self):
        extension = SCRIPT.parents[1]
        with tempfile.TemporaryDirectory() as directory:
            result = package_chrome_ready.build(directory, extension)
            with zipfile.ZipFile(result["archive"]) as archive:
                identity = json.loads(archive.read("PACKAGE_IDENTITY.json"))
                self.assertEqual(identity["package_tree_sha256"],
                                 result["package_tree_sha256"])
                entries = {}
                for item in identity["files"]:
                    data = archive.read(item["path"])
                    self.assertEqual(len(data), item["bytes"])
                    self.assertEqual(hashlib.sha256(data).hexdigest(),
                                     item["sha256"])
                    entries[item["path"]] = data
                self.assertEqual(package_chrome_ready._tree_digest(entries),
                                 result["package_tree_sha256"])
                self.assertNotIn("PACKAGE_IDENTITY.json", entries)


if __name__ == "__main__":
    unittest.main()
