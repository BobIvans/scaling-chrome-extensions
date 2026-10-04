import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from repo_smells import scan_repo, write_report, strongly_connected


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def source(self, relative, value):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode())
        return path

    def test_candidates_hashes_spans_and_never_executes_source(self):
        marker = self.base / "executed.txt"
        code = (f"open({str(marker)!r}, 'w').write('executed')\n"
                "def unsafe(value):\n"
                "    try:\n"
                "        eval(value)\n"
                "        exec(value)\n"
                "        runner(value, shell=True)\n"
                "    except:\n"
                "        pass\n")
        path = self.source("jobs/runner.py", code)
        original = path.read_bytes()
        report = scan_repo(self.repo, long_function_lines=3)
        rules = {item["rule"] for item in report["findings"]}
        self.assertTrue({"EVAL_OR_EXEC", "LITERAL_SHELL_TRUE", "BARE_EXCEPT", "EXCEPT_PASS", "LONG_FUNCTION"} <= rules)
        self.assertEqual(report["security_audit_pass"], "NOT_RUN")
        self.assertFalse(marker.exists())
        self.assertEqual(path.read_bytes(), original)
        for finding in report["findings"]:
            self.assertEqual(finding["status"], "STATIC_CANDIDATE")
            ev = finding["evidence"][0]
            self.assertEqual(ev["path"], "jobs/runner.py")
            self.assertEqual(ev["source_sha256"], hashlib.sha256(original).hexdigest())
            self.assertGreaterEqual(ev["start_line"], 2)
            self.assertGreaterEqual(ev["end_line"], ev["start_line"])

    def test_repeated_filenames_and_normalized_duplicates(self):
        self.source("one/common.py", 'def a(x):\n    "first doc"\n    return x + 1\n')
        self.source("two/common.py", 'async def b(x):\n    "different doc"\n    return x + 1\n')
        report = scan_repo(self.repo)
        duplicate = [item for item in report["findings"] if item["rule"] == "DUPLICATE_FUNCTION_BODY"]
        self.assertEqual(len(duplicate), 1)
        self.assertEqual({item["path"] for item in duplicate[0]["evidence"]},
                         {"one/common.py", "two/common.py"})
        self.assertEqual(len(report["files"]), 2)

    def test_binary_syntax_encoding_and_unreadable_are_explicit(self):
        self.source("binary.py", b"\x00\xff")
        self.source("syntax.py", "def nope(\n")
        self.source("encoding.py", b"\xff = 1\n")
        blocked = self.source("unreadable.py", "x = 1\n")
        self.source("latin.py", b"# coding: latin-1\ns = '\xe9'\n")
        real_open = os.open
        def fake_open(path, flags, *args, **kwargs):
            if Path(path) == blocked:
                raise PermissionError("fixture denies read")
            return real_open(path, flags, *args, **kwargs)
        with patch("repo_smells.os.open", side_effect=fake_open):
            report = scan_repo(self.repo)
        outcomes = {item["path"]: item["status"] for item in report["files"]}
        self.assertEqual(outcomes, {"binary.py": "BINARY", "syntax.py": "SYNTAX_ERROR",
                                   "encoding.py": "DECODE_ERROR", "unreadable.py": "READ_ERROR",
                                   "latin.py": "PARSED"})
        self.assertEqual(report["scan_status"], "COMPLETE_WITH_GAPS")
        self.assertEqual(report["live_bot_readiness"], "NOT_RUN")

    def test_directory_and_file_symlinks_not_followed(self):
        self.source("real/a.py", "x = 1\n")
        try:
            (self.repo / "loop").symlink_to(self.repo, target_is_directory=True)
            (self.repo / "alias.py").symlink_to(self.repo / "real/a.py")
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable: {exc}")
        report = scan_repo(self.repo)
        self.assertEqual(len(report["files"]), 3)
        self.assertEqual(sum(item["status"] == "PARSED" for item in report["files"]), 1)
        self.assertEqual(sum(item["status"] == "SKIPPED_SYMLINK_OR_JUNCTION" for item in report["files"]), 2)

    def test_resolvable_cycle_external_and_dynamic_imports(self):
        self.source("a.py", "import b\nimport third_party_unknown\nimport importlib as il\nil.import_module('hidden')\n")
        self.source("b.py", "import a\nfrom importlib import import_module as imp\nimp(name)\n")
        report = scan_repo(self.repo)
        cycles = [item for item in report["findings"] if item["rule"] == "LOCAL_IMPORT_CYCLE"]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["component"], ["a.py", "b.py"])
        self.assertTrue(all(edge["target"] in {"a.py", "b.py"} for edge in report["imports"]["edges"]))
        self.assertEqual(len(report["imports"]["dynamic"]), 2)
        self.assertTrue(any(item["module"] == "third_party_unknown" for item in report["imports"]["unresolved"]))

    def test_relative_src_imports_and_ambiguous_module(self):
        self.source("src/pkg/__init__.py", "")
        self.source("src/pkg/a.py", "from . import b\n")
        self.source("src/pkg/b.py", "from .a import missing_attribute\n")
        report = scan_repo(self.repo, import_roots=["src"])
        cycles = [item for item in report["findings"] if item["rule"] == "LOCAL_IMPORT_CYCLE"]
        self.assertEqual(cycles[0]["component"], ["src/pkg/a.py", "src/pkg/b.py"])
        self.assertTrue(any(item["status"] == "ATTRIBUTE_OR_SUBMODULE_UNKNOWN"
                            for item in report["imports"]["unresolved"]))
        self.source("both.py", "")
        self.source("both/__init__.py", "")
        self.source("consumer.py", "import both\n")
        ambiguous = scan_repo(self.repo)
        self.assertTrue(any(item["status"] == "AMBIGUOUS_LOCAL_MODULE"
                            for item in ambiguous["imports"]["unresolved"]))

    def test_file_count_is_not_capped_and_revision_tracks_bytes(self):
        for index in range(321):
            self.source(f"group/{index:04}.py", f"value = {index}\n")
        report = scan_repo(self.repo)
        self.assertEqual(len(report["files"]), 321)
        self.assertIsNone(report["configuration"]["file_count_cap"])
        again = scan_repo(self.repo)
        self.assertEqual(report["inventory_revision_sha256"], again["inventory_revision_sha256"])
        self.source("group/0000.py", "value = 42\n")
        self.assertNotEqual(report["inventory_revision_sha256"], scan_repo(self.repo)["inventory_revision_sha256"])

    def test_cli_atomic_report_and_refusal_to_write_inside_repo(self):
        source = self.source("a.py", "x = 1\n")
        output = self.base / "report.json"
        cli = Path(__file__).with_name("repo_smells.py")
        process = subprocess.run([sys.executable, str(cli), str(self.repo), "--output", str(output)],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(output.read_text())
        self.assertEqual(report["assessment"], "STATIC_CANDIDATES_ONLY")
        with self.assertRaisesRegex(ValueError, "outside"):
            write_report(report, source)
        self.assertEqual(source.read_text(), "x = 1\n")
        bad = subprocess.run([sys.executable, str(cli), str(self.repo), "--output", str(output),
                              "--long-function-lines", "0"], capture_output=True)
        self.assertEqual(bad.returncode, 2)

    def test_large_graph_uses_iterative_cycle_algorithm(self):
        nodes = [str(index) for index in range(2500)]
        edges = [{"source": nodes[index], "target": nodes[(index + 1) % len(nodes)]}
                 for index in range(len(nodes))]
        components = list(strongly_connected(nodes, edges))
        self.assertEqual(len(components), 1)
        self.assertEqual(len(components[0]), 2500)


if __name__ == "__main__":
    unittest.main()
