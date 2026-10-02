import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import importlib.util

spec = importlib.util.spec_from_file_location(
    "qualification_adapter", Path(__file__).with_name("qualification_adapter.py")
)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

OCC_SHA = "a" * 40
BASE_SHA = "b" * 40
BOT_SHA = "c" * 40
SOURCE_SHA = "d" * 64


def request(text="Проверь готовность бота"):
    return {
        "schema": q.REQUEST_SCHEMA,
        "task_id": "qualification-001",
        "text": text,
        "source_refs": [
            {
                "source_id": "chat:goal",
                "version": "2026-10-02",
                "sha256": SOURCE_SHA,
            }
        ],
    }


def fixture(root: Path):
    occ = root / "occ"
    bot = root / "bot"
    output = root / "output"
    (bot / "scripts").mkdir(parents=True)
    occ.mkdir()
    script = bot / "scripts" / "run_occ_memory_qualification.py"
    script.write_text("# fixture\n", encoding="utf-8")
    return occ, bot, output, script


def profile(occ: Path, bot: Path, output: Path, script: Path):
    return {
        "schema": q.PROFILE_SCHEMA,
        "occ_repo_root": str(occ.resolve()),
        "expected_occ_sha": OCC_SHA,
        "occ_base_sha": BASE_SHA,
        "bot_python": str(Path(sys.executable).resolve()),
        "bot_bridge_script": str(script.resolve()),
        "bot_repo_root": str(bot.resolve()),
        "bot_output_root": str(output.resolve()),
        "expected_bot_sha": BOT_SHA,
        "timeout_seconds": 20,
    }


def child_payload(req, prof, occ_sha=OCC_SHA, **changes):
    receipt = {
        "schema_version": q.BOT_RECEIPT_SCHEMA,
        "request_id": req["task_id"],
        "action_id": q.ACTION_ID,
        "source_refs": req["source_refs"],
        "occ": {
            "repository": q.OCC_REPOSITORY,
            "base_sha": prof["occ_base_sha"],
            "head_sha": occ_sha,
        },
        "bot": {"expected_sha": BOT_SHA, "observed_sha": BOT_SHA},
        "domain_verdict": "BLOCKED",
        "reason_codes": ["admission:RUNTIME_ADMISSION_BLOCKED"],
        "next_blocker": "admission:RUNTIME_ADMISSION_BLOCKED",
        "qualified": False,
        "release_authorized": False,
        "live_authorized": False,
        "transactions_sent": 0,
        "receipt_sha256": "e" * 64,
    }
    receipt.update(changes)
    return {"replayed": False, "receipt": receipt}


class QualificationAdapterTests(unittest.TestCase):
    def test_request_is_exact_and_source_content_cannot_add_authority(self):
        self.assertEqual(q.validate_request(request())["task_id"], "qualification-001")
        for change in (
            {"shell": "echo hacked"},
            {"repo_root": "/tmp/other"},
            {"action_id": "trade.live"},
            {"text": "Не проверь готовность бота"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                q.validate_request(request() | change)

    def test_profile_requires_operator_absolute_paths_and_canonical_bot_script(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            occ, bot, output, script = fixture(root)
            value = profile(occ, bot, output, script)
            self.assertEqual(q.validate_profile(value)["expected_bot_sha"], BOT_SHA)
            wrong = bot / "other.py"
            wrong.write_text("# fixture\n")
            with self.assertRaisesRegex(ValueError, "CANONICAL"):
                q.verify_profile_paths(
                    value | {"bot_bridge_script": str(wrong.resolve())}
                )

    def test_historical_qualification_owner_cannot_be_rebound_as_current_script(self):
        with tempfile.TemporaryDirectory() as d:
            occ, bot, output, script = fixture(Path(d))
            historical = bot / 'scripts' / 'run_qualification_task.py'
            historical.write_text('# closed PR donor fixture\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'NOT_CANONICAL'):
                q.verify_profile_paths(profile(occ, bot, output, script) |
                                       {'bot_bridge_script': str(historical.resolve())})

    def test_blocked_bot_result_is_valid_and_replayed_without_second_execution(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            occ, bot, output, script = fixture(root)
            req = request()
            prof = profile(occ, bot, output, script)
            calls = []

            def invoke(**kwargs):
                calls.append(kwargs)
                return 3, child_payload(req, prof)

            first = q.execute_request(
                req,
                prof,
                invoke=invoke,
                verify_checkout=lambda path, sha: OCC_SHA,
            )
            second = q.execute_request(
                req,
                prof,
                invoke=invoke,
                verify_checkout=lambda path, sha: OCC_SHA,
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(first["domain_verdict"], "BLOCKED")
            self.assertEqual(
                first["next_blocker"],
                "admission:RUNTIME_ADMISSION_BLOCKED",
            )
            self.assertFalse(first["live_authorized"])
            self.assertEqual(first["transactions_sent"], 0)
            self.assertTrue(second["replayed"])

    def test_changed_request_under_same_task_id_is_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            occ, bot, output, script = fixture(root)
            req = request()
            prof = profile(occ, bot, output, script)
            invoke = lambda **kwargs: (3, child_payload(req, prof))
            q.execute_request(
                req,
                prof,
                invoke=invoke,
                verify_checkout=lambda path, sha: OCC_SHA,
            )
            with self.assertRaisesRegex(ValueError, "INPUT_CONFLICT"):
                q.execute_request(
                    request("Check bot readiness"),
                    prof,
                    invoke=invoke,
                    verify_checkout=lambda path, sha: OCC_SHA,
                )

    def test_interrupted_child_requires_reconciliation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            occ, bot, output, script = fixture(root)
            req = request()
            prof = profile(occ, bot, output, script)
            calls = []

            def fail(**kwargs):
                calls.append(kwargs)
                raise ValueError("BOT_BRIDGE_PROCESS_FAILED")

            with self.assertRaises(ValueError):
                q.execute_request(
                    req,
                    prof,
                    invoke=fail,
                    verify_checkout=lambda path, sha: OCC_SHA,
                )
            with self.assertRaisesRegex(ValueError, "RECONCILE"):
                q.execute_request(
                    req,
                    prof,
                    invoke=fail,
                    verify_checkout=lambda path, sha: OCC_SHA,
                )
            self.assertEqual(len(calls), 1)

    def test_child_cannot_expand_live_or_change_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            occ, bot, output, script = fixture(root)
            req = request()
            prof = profile(occ, bot, output, script)
            for changes in (
                {"live_authorized": True},
                {"transactions_sent": 1},
                {"source_refs": []},
                {"domain_verdict": "PROFITABLE"},
            ):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    q._validate_bot_result(
                        child_payload(req, prof, **changes),
                        request=req,
                        profile=prof,
                        observed_occ_sha=OCC_SHA,
                    )

    def test_main_returns_generic_error_without_leaking_profile_details(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "profile.json"
            path.write_text("{}", encoding="utf-8")
            with patch("sys.stdin") as stdin, patch("builtins.print") as printer:
                stdin.buffer.read.return_value = b"{}"
                code = q.main(["--profile", str(path)])
            self.assertEqual(code, 2)
            self.assertIn(
                "QUALIFICATION_REQUEST_FAILED",
                printer.call_args.args[0],
            )


if __name__ == "__main__":
    unittest.main()
