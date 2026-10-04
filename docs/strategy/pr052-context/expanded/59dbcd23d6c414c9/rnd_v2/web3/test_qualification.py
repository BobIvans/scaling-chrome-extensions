import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from qualification import evaluate, canonical_hash, file_hash, EvidenceError, validate_plan, read_json, write_report

NOW = dt.datetime(2026, 10, 3, 17, 0, tzinfo=dt.timezone.utc)
BINDING = {
    "repo_revision": "a" * 40, "config_sha256": "b" * 64,
    "input_manifest_sha256": "c" * 64, "environment_sha256": "d" * 64,
    "network": {"family": "offline_fixture", "network_id": "fixture:1", "genesis_hash": "fixture-genesis"},
    "anchor": {"height": "100", "hash": "fixture-block-100", "finality": "fixture"},
    "provider": {"id": "fixture-provider", "version": "1"},
    "model": {"id": "none", "revision": "none"}, "toolchain": {"python": "3.11.fixture"}
}
PRODUCER = {"id": "qualification-test-fixture", "version": "1", "binary_sha256": "e" * 64}
CRITERIA = {
    "junit_xml.v1": {"min_cases": 1, "required_name_fragments": ["repayment"]},
    "inventory_diff.v1": {"min_entries": 1},
    "economics_samples.v1": {"min_samples": 1, "min_accepted": 1, "max_quote_age_ms": 100, "min_net_minor": 1, "accounting_unit": "USDC:atomic:fixture"},
    "observation_window.v1": {"min_samples": 2, "min_duration_seconds": 60, "max_gap_seconds": 60, "min_providers": 2, "max_source_age_ms": 1000, "mode": "REAL_MARKET_PAPER_OBSERVATION"},
    "stop_latency.v1": {"min_probes": 1, "max_stop_latency_ms": 50, "required_faults": ["rpc_timeout"]}
}

def plan(adapter="junit_xml.v1"):
    return {"schema": "web3-qualification/v1", "campaign_id": "TEST_FIXTURE_NOT_BOT",
            "live_authorized": False, "binding": copy.deepcopy(BINDING), "stages": [
                {"id": "stage1", "adapter": adapter, "producer": dict(PRODUCER), "depends_on": [],
                 "max_age_seconds": 3600, "criteria": copy.deepcopy(CRITERIA[adapter])}]}

class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def artifact(self, role, content, name=None):
        path = self.root / (name or role)
        path.write_text(content, encoding="utf-8")
        return {"role": role, "path": path.name, "bytes": path.stat().st_size, "sha256": file_hash(path)}
    def jsonl(self, role, values):
        return self.artifact(role, "".join(json.dumps(i) + "\n" for i in values))
    def receipt(self, p, artifacts=None):
        if artifacts is None:
            artifacts = [self.artifact("test_results", '<testsuite><testcase name="repayment" classname="flashloan"/></testsuite>')]
        return {"schema": "web3-qualification/v1/receipt", "campaign_id": p["campaign_id"],
                "plan_sha256": canonical_hash(p), "stage_id": "stage1", "adapter": p["stages"][0]["adapter"],
                "binding": copy.deepcopy(p["binding"]), "producer": dict(PRODUCER, kind="machine_runner"),
                "started_at": "2026-10-03T16:50:00Z", "completed_at": "2026-10-03T16:59:00Z",
                "process": {"state": "EXITED", "exit_code": 0}, "artifacts": artifacts}
    def run_receipt(self, p, r): return evaluate(p, [r], self.root, NOW)
    def status(self, p, r): return self.run_receipt(p, r)["stages"][0]["own_status"]
    def test_valid_machine_case_never_authorizes_live(self):
        p = plan(); r = self.receipt(p)
        report = self.run_receipt(p, r)
        self.assertEqual(report["configured_predicates"], "TRUE")
        self.assertFalse(report["live_authorized"])
        self.assertFalse(report["ready_for_live"])
        self.assertEqual(report["producer_authenticity"], "UNKNOWN")
    def test_absent_receipt_not_run(self):
        report = evaluate(plan(), [], self.root, NOW)
        self.assertEqual(report["configured_predicates"], "NOT_RUN")
    def test_each_binding_change_invalidates(self):
        for key in ("repo_revision", "config_sha256", "input_manifest_sha256", "environment_sha256", "network", "anchor", "provider", "model", "toolchain"):
            with self.subTest(key=key):
                p = plan(); r = self.receipt(p); r["binding"][key] = "changed"
                self.assertEqual(self.status(p, r), "UNKNOWN")
    def test_stale_and_future_invalidated(self):
        p = plan(); r = self.receipt(p)
        r["completed_at"] = "2026-10-02T16:59:00Z"; r["started_at"] = "2026-10-02T16:50:00Z"
        self.assertEqual(self.status(p, r), "UNKNOWN")
        r["completed_at"] = "2026-10-04T16:59:00Z"
        self.assertEqual(self.status(p, r), "UNKNOWN")
    def test_hash_corruption_false(self):
        p = plan(); r = self.receipt(p)
        (self.root / "test_results").write_text("tampered")
        self.assertEqual(self.status(p, r), "FALSE")
    def test_missing_artifact_unknown(self):
        p = plan(); r = self.receipt(p); (self.root / "test_results").unlink()
        self.assertEqual(self.status(p, r), "UNKNOWN")
    def test_model_text_success_boolean_not_evidence(self):
        p = plan(); r = self.receipt(p, [])
        r["success"] = True; r["model_text"] = "Everything is safe and live ready."
        self.assertEqual(self.status(p, r), "UNKNOWN")
        r["producer"]["kind"] = "llm"
        self.assertEqual(self.status(p, r), "UNKNOWN")
    def test_process_failure_false_and_bool_exit_refused(self):
        p = plan(); r = self.receipt(p); r["process"]["exit_code"] = 1
        self.assertEqual(self.status(p, r), "FALSE")
        r["process"]["exit_code"] = False
        self.assertEqual(self.status(p, r), "UNKNOWN")
    def test_failing_case_not_overridden_by_summary(self):
        p = plan(); a = self.artifact("test_results", '<testsuite tests="1" failures="0"><testcase name="repayment" classname="f"><failure>insufficient repayment</failure></testcase></testsuite>')
        self.assertEqual(self.status(p, self.receipt(p, [a])), "FALSE")
    def test_skip_and_empty_suite_not_qualifying(self):
        for data in ['<testsuite><testcase name="repayment" classname="f"><skipped/></testcase></testsuite>', '<testsuite tests="0" failures="0"/>']:
            p = plan(); a = self.artifact("test_results", data)
            self.assertEqual(self.status(p, self.receipt(p, [a])), "FALSE")
    def test_plan_change_and_duplicate_receipts_invalidated(self):
        p = plan(); r = self.receipt(p); p["stages"][0]["criteria"]["min_cases"] = 2
        self.assertEqual(self.status(p, r), "UNKNOWN")
        report = evaluate(p, [r, r], self.root, NOW)
        self.assertEqual(report["configured_predicates"], "UNKNOWN")
    def test_dependency_does_not_fake_progress(self):
        p = plan(); s2 = copy.deepcopy(p["stages"][0]); s2.update(id="stage2", depends_on=["stage1"]); p["stages"].append(s2)
        r = self.receipt(p); r["stage_id"] = "stage2"
        report = self.run_receipt(p, r)
        self.assertEqual(report["stages"][1]["own_status"], "TRUE")
        self.assertEqual(report["stages"][1]["status"], "NOT_RUN")
        self.assertFalse(report["stages"][1]["eligible_for_next_stage"])
    def test_paths_refused(self):
        for bad in ["../escape", "/tmp/escape", "C:/Windows/file", "x\\y", "file:stream", "//server/file"]:
            with self.subTest(bad=bad):
                p = plan(); r = self.receipt(p); r["artifacts"][0]["path"] = bad
                self.assertEqual(self.status(p, r), "UNKNOWN")
    def test_symlink_refused(self):
        p = plan(); r = self.receipt(p)
        (self.root / "link").symlink_to(self.root / "test_results")
        r["artifacts"][0]["path"] = "link"
        self.assertEqual(self.status(p, r), "UNKNOWN")
    def test_inventory_omission_false_and_order_independent(self):
        p = plan("inventory_diff.v1")
        a = {"path": "dir/a.py", "ordinal": 0, "bytes": 5, "sha256": "f"*64}
        b = dict(a, path="b.py", ordinal=1)
        artifacts = [self.jsonl("expected_manifest", [a,b]), self.jsonl("observed_manifest", [b,a])]
        self.assertEqual(self.status(p, self.receipt(p, artifacts)), "TRUE")
        artifacts[1] = self.jsonl("observed_manifest", [a])
        self.assertEqual(self.status(p, self.receipt(p, artifacts)), "FALSE")
    def test_cost_recomputation_detects_negative_profit(self):
        p = plan("economics_samples.v1")
        sample = {"sample_id":"s1", "accounting_unit":"USDC:atomic:fixture", "proceeds_minor":110, "principal_minor":100, "flash_fee_minor":2, "swap_fee_minor":3, "network_fee_minor":2, "slippage_reserve_minor":1, "other_cost_minor":1, "quote_age_ms":10, "decision":"ACCEPT", "profit_is_positive":True}
        r = self.receipt(p, [self.jsonl("economics", [sample])]); self.assertEqual(self.status(p,r), "TRUE")
        sample["network_fee_minor"] = 50
        r = self.receipt(p, [self.jsonl("economics", [sample])]); self.assertEqual(self.status(p,r), "FALSE")
    def test_quote_freshness_and_atomic_units(self):
        p = plan("economics_samples.v1")
        sample = {"sample_id":"s1", "accounting_unit":"USDC:atomic:fixture", "proceeds_minor":100, "principal_minor":0, "flash_fee_minor":0, "swap_fee_minor":0, "network_fee_minor":0, "slippage_reserve_minor":0, "other_cost_minor":0, "quote_age_ms":101, "decision":"ACCEPT"}
        self.assertEqual(self.status(p, self.receipt(p,[self.jsonl("economics",[sample])])), "FALSE")
        sample["quote_age_ms"] = 0; sample["network_fee_minor"] = 0.5
        self.assertEqual(self.status(p, self.receipt(p,[self.jsonl("economics",[sample])])), "UNKNOWN")
    def test_paper_observation_is_not_replay(self):
        p = plan("observation_window.v1")
        base = {"sample_id":"s1", "mode":"REAL_MARKET_PAPER_OBSERVATION", "network_id":"fixture:1", "anchor_hash":"hash", "height":"100", "finality":"fixture", "observed_at":"2026-10-03T16:50:00Z", "source_at":"2026-10-03T16:50:00Z", "provider_id":"provider1", "signed_transactions":0, "sent_transactions":0}
        nxt = dict(base, sample_id="s2", observed_at="2026-10-03T16:51:00Z", source_at="2026-10-03T16:51:00Z", provider_id="provider2")
        self.assertEqual(self.status(p,self.receipt(p,[self.jsonl("observations",[base,nxt])])), "TRUE")
        nxt["mode"] = "OFFLINE_REPLAY"
        self.assertEqual(self.status(p,self.receipt(p,[self.jsonl("observations",[base,nxt])])), "UNKNOWN")
    def test_stop_latency_and_forbidden_dispatch(self):
        p = plan("stop_latency.v1")
        probe = {"probe_id":"p1", "fault":"rpc_timeout", "trigger_monotonic_ns":1000000000, "blocked_monotonic_ns":1040000000, "forbidden_dispatches_after_trigger":0}
        self.assertEqual(self.status(p,self.receipt(p,[self.jsonl("stop_probes",[probe])])), "TRUE")
        probe["forbidden_dispatches_after_trigger"] = 1
        self.assertEqual(self.status(p,self.receipt(p,[self.jsonl("stop_probes",[probe])])), "FALSE")
    def test_malformed_json_and_nonfinite_rejected(self):
        path = self.root / "bad.json"
        for value in ['{"a":1,"a":2}', '{"a":NaN}']:
            path.write_text(value)
            with self.assertRaises(EvidenceError): read_json(path)
    def test_junit_declared_missing_case_or_failure_invalidates(self):
        for attrs in ['tests="2" failures="1"', 'tests="99" failures="0"', 'tests="1" errors="1"', 'tests="1" skipped="1"']:
            p = plan()
            a = self.artifact("test_results", '<testsuite ' + attrs + '><testcase name="repayment" classname="f"/></testsuite>')
            self.assertEqual(self.status(p, self.receipt(p,[a])), "UNKNOWN")
    def test_junit_suite_level_error_false(self):
        p = plan()
        a = self.artifact("test_results", '<testsuite><error>setup failed</error><testcase name="repayment" classname="f"/></testsuite>')
        self.assertEqual(self.status(p, self.receipt(p,[a])), "FALSE")
    def test_observation_outside_receipt_window_unknown(self):
        p = plan("observation_window.v1")
        base = {"sample_id":"s1", "mode":"REAL_MARKET_PAPER_OBSERVATION", "network_id":"fixture:1", "anchor_hash":"hash", "height":"100", "finality":"fixture", "observed_at":"2026-10-03T16:20:00Z", "source_at":"2026-10-03T16:20:00Z", "provider_id":"provider1", "signed_transactions":0, "sent_transactions":0}
        nxt = dict(base, sample_id="s2", observed_at="2026-10-03T16:21:00Z", source_at="2026-10-03T16:21:00Z", provider_id="provider2")
        self.assertEqual(self.status(p,self.receipt(p,[self.jsonl("observations",[base,nxt])])), "UNKNOWN")
    def test_report_cannot_overwrite_inputs_or_evidence(self):
        evidence = self.root / "evidence"; evidence.mkdir()
        plan_path = self.root / "plan.json"; plan_path.write_text("original")
        with self.assertRaises(EvidenceError): write_report(plan_path, "replacement", evidence, [plan_path])
        with self.assertRaises(EvidenceError): write_report(evidence / "report.json", "replacement", evidence)
        self.assertEqual(plan_path.read_text(), "original")
        self.assertFalse((evidence / "report.json").exists())
    def test_report_published_exclusively_and_complete(self):
        evidence = self.root / "evidence"; evidence.mkdir()
        output = self.root / "report.json"
        write_report(output, '{"complete":true}', evidence)
        self.assertEqual(output.read_text(), '{"complete":true}')
        with self.assertRaises(EvidenceError): write_report(output, "replacement", evidence)
        self.assertEqual(output.read_text(), '{"complete":true}')
        self.assertFalse(list(self.root.glob(".qualification-report-*")))
    def test_notrun_attribute_does_not_count_as_execution(self):
        p = plan()
        a = self.artifact("test_results", '<testsuite><testcase name="repayment" classname="f" status="notrun"/></testsuite>')
        self.assertEqual(self.status(p,self.receipt(p,[a])), "FALSE")
    def test_utf16_dtd_is_refused(self):
        p = plan()
        path = self.root / "test_results"
        path.write_bytes('<?xml version="1.0" encoding="utf-16"?><!DOCTYPE testsuite [<!ENTITY x "pass">]><testsuite><testcase name="repayment" classname="f">&x;</testcase></testsuite>'.encode("utf-16"))
        a = {"role":"test_results", "path":path.name, "bytes":path.stat().st_size, "sha256":file_hash(path)}
        self.assertEqual(self.status(p,self.receipt(p,[a])), "UNKNOWN")
    def test_invalid_plan_refused(self):
        p = plan(); p["live_authorized"] = True
        with self.assertRaises(EvidenceError): validate_plan(p)
        p = plan(); p["stages"][0]["depends_on"] = ["stage1"]
        with self.assertRaises(EvidenceError): validate_plan(p)
        p = plan(); p["stages"][0]["criteria"]["any_boolean_success"] = True
        with self.assertRaises(EvidenceError): validate_plan(p)

if __name__ == "__main__": unittest.main(verbosity=2)
