import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "qualification_adapter", Path(__file__).with_name("qualification_adapter.py")
)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
SHA = "a" * 40


def request(**extra):
    return {"schema_version": q.REQUEST_SCHEMA, "request_id": "r1", **extra}


def checkout(root):
    path = Path(root) / "checkout"
    path.mkdir(exist_ok=True)
    return path


class AdapterTests(unittest.TestCase):
    def test_exact_action_and_exact_russian_phrase(self):
        self.assertEqual(
            q.select_action(request(action_id="qualify_and_report")),
            "qualify_and_report",
        )
        self.assertEqual(
            q.select_action(request(text="Проверь готовность бота")),
            "qualify_and_report",
        )

    def test_negation_and_injected_shell_are_not_substring_matches(self):
        for text in (
            "не проверь готовность бота",
            "проверь готовность бота; rm -rf /",
            "запусти profitable live trades",
            "напиши новую стратегию",
            "что лучше проверить?",
        ):
            with self.subTest(text=text):
                self.assertEqual(q.select_action(request(text=text)), "needs_context")

    def test_extra_parameters_cannot_become_argv(self):
        for extra in (
            {"argv": ["sh", "-c", "echo x"]},
            {"repo_root": "/"},
            {"action_id": "send_transaction"},
            {"action_id": []},
            {"request_id": "../escape"},
            {"text": "x" * 2001},
        ):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                q.validate_request(request(**extra))

    def test_missing_laya_has_no_paid_fallback(self):
        with patch.dict(sys.modules, {"laya": None}):
            result = q.laya_proposal("Проверь готовность бота")
        self.assertEqual(result["state"], "UNAVAILABLE")
        self.assertFalse(result["authorizes_execution"])
        self.assertFalse(result["model_inference_performed"])

    def test_laya_suggestion_cannot_authorize_ambiguous_request(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(
                q,
                "laya_proposal",
                return_value={
                    "state": "ADVISORY",
                    "action_id": "qualify_and_report",
                    "model_inference_performed": False,
                    "authorizes_execution": False,
                },
            ):
                receipt = q.execute_request(
                    request(text="maybe run something"),
                    repo_root=checkout(d),
                    output_root=Path(d) / "runs",
                    expected_sha=SHA,
                    laya_shadow=True,
                )
        self.assertEqual(receipt["execution_status"], "NOT_EXECUTED")
        self.assertEqual(receipt["action_id"], "needs_context")

    def test_child_scope_and_identity_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)
            details = {
                "schema_version": "fast-q1.qualification-receipt.v1",
                "request_id": "r1",
                "git_sha": SHA,
                "run_directory": str(output / "r1"),
                "execution_status": "COMPLETE",
                "domain_verdict": "BLOCKED",
                "qualified": False,
                "live_authorized": False,
                "market_run_performed": False,
                "transactions_sent": 0,
            }
            payload = {
                "schema_version": "pr189.command-result.v1",
                "command": "qualify-and-report",
                "command_mode": "inspect",
                "details": details,
            }
            result = q.validate_child(
                payload, request_id="r1", expected_sha=SHA, output_root=output
            )
            self.assertEqual(result["domain_verdict"], "BLOCKED")
            for key, value in (
                ("request_id", "other"),
                ("git_sha", "b" * 40),
                ("qualified", True),
                ("transactions_sent", False),
                ("transactions_sent", 1),
                ("execution_status", "RUNNING"),
                ("run_directory", str(output.parent)),
                ("domain_verdict", "PROFITABLE"),
            ):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    q.validate_child(
                        {**payload, "details": {**details, key: value}},
                        request_id="r1",
                        expected_sha=SHA,
                        output_root=output,
                    )

    def test_child_command_and_version_are_checked(self):
        with self.assertRaises(ValueError):
            q.validate_child(
                {"schema_version": "other"},
                request_id="r1",
                expected_sha=SHA,
                output_root=Path("."),
            )

    def test_completed_request_reuses_receipt_without_model_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(
                q,
                "laya_proposal",
                return_value={
                    "state": "UNAVAILABLE",
                    "model_inference_performed": False,
                    "authorizes_execution": False,
                },
            ) as model:
                kwargs = dict(
                    repo_root=checkout(root),
                    output_root=root / "runs",
                    expected_sha=SHA,
                    laya_shadow=True,
                )
                first = q.execute_request(request(text="ambiguous"), **kwargs)
                second = q.execute_request(request(text="ambiguous"), **kwargs)
                self.assertEqual(model.call_count, 1)
                self.assertFalse(first["reused"])
                self.assertTrue(second["reused"])
                self.assertEqual(second["request_sha256"], first["request_sha256"])

    def test_request_id_rejects_changed_text_or_operator_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            kwargs = dict(
                repo_root=checkout(root), output_root=root / "runs", expected_sha=SHA
            )
            q.execute_request(request(text="one"), **kwargs)
            with self.assertRaisesRegex(ValueError, "INPUT_CONFLICT"):
                q.execute_request(request(text="two"), **kwargs)
            with self.assertRaisesRegex(ValueError, "INPUT_CONFLICT"):
                q.execute_request(
                    request(text="one"), **{**kwargs, "expected_sha": "b" * 40}
                )

    def test_interrupted_request_is_not_automatically_reexecuted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run = root / "runs" / "adapter_requests" / "r1"
            run.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_RECONCILE"):
                q.execute_request(
                    request(text="ambiguous"),
                    repo_root=checkout(root),
                    output_root=root / "runs",
                    expected_sha=SHA,
                )

    def test_changed_stored_receipt_is_not_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            kwargs = dict(
                repo_root=checkout(root), output_root=root / "runs", expected_sha=SHA
            )
            q.execute_request(request(text="ambiguous"), **kwargs)
            path = root / "runs" / "adapter_requests" / "r1" / "adapter_receipt.json"
            path.write_text('{"execution_status":"COMPLETE"}')
            with self.assertRaisesRegex(ValueError, "INTEGRITY_FAILED"):
                q.execute_request(request(text="ambiguous"), **kwargs)

    def test_symlink_parent_cannot_hide_output_location(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "real").mkdir()
            (root / "alias").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "OUTPUT_SYMLINK"):
                q.execute_request(
                    request(text="ambiguous"),
                    repo_root=checkout(root),
                    output_root=root / "alias" / "runs",
                    expected_sha=SHA,
                )

    def test_main_returns_need_context_without_starting_bot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            input_path = root / "request.json"
            input_path.write_text(json.dumps(request(text="send live trades")))
            with patch("builtins.print"):
                code = q.main(
                    [
                        "--request",
                        str(input_path),
                        "--repo-root",
                        str(checkout(root)),
                        "--output-root",
                        str(root / "runs"),
                        "--expected-sha",
                        SHA,
                    ]
                )
            self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
