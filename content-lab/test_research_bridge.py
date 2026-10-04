"""Core/receipt/read-only contracts; fixture receipts are not market evidence."""

from collections import Counter
import hashlib
import json
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import automation_core as ac
import research_bridge as rb
import product_qualification as pq
import native_adapter as na


class ResearchBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "store"
        repo = self.root / "owner"
        (repo / "scripts").mkdir(parents=True)
        (repo / rb.SCRIPT).write_text("# operator-reviewed test fixture\n")
        data = self.root / "dataset"
        data.write_text("{}\n")
        cfg = self.root / "config"
        cfg.write_text("{}")
        self.profile = {
            "schema": "occ.research-profile.v1",
            "root": str(repo),
            "python": sys.executable,
            "source_commit": "a" * 40,
            "handler_sha256": rb.sha_file(repo / rb.SCRIPT),
            "dataset": str(data),
            "dataset_sha256": rb.sha_file(data),
            "config": str(cfg),
            "config_sha256": rb.sha_file(cfg),
            "output_root": str(self.root / "runs"),
            "timeout_seconds": 10,
        }
        self.payload = {"kind": "studious_research", "research_profile": "registered"}
        self.policy = {
            "schema": "occ.automation-policy.v1",
            "max_parallel": 1,
            "money_budget": 0,
            "research": {"registered": self.profile},
        }
        self.core = ac.Core(self.store, self.policy)

    def receipt(self, job_id, status="MODEL_REPLAY_COMPLETED", count=1):
        request = rb.request_for(self.profile, job_id)
        root = Path(self.profile["output_root"]) / job_id
        root.mkdir(parents=True)
        trial = {
            "ordinal": 1,
            "handler_invoked": True,
            "origin": "OFFLINE_FIXTURE",
            "result": {"status": "NO_CANDIDATE", "execution_right": False},
        }
        trials = rb.canonical(trial) + b"\n" if count else b""
        (root / "trials.jsonl").write_bytes(trials)
        sha = rb.sha_file(root / "trials.jsonl")
        report = {
            "schema": "studious.occ-research-campaign.v1",
            "mode": "REPLAY",
            "origin": "OFFLINE_FIXTURE",
            "status": status,
            "records": count,
            "handler_calls": count,
            "useful_calls": count,
            "outcome_counts": {"NO_CANDIDATE": count} if count else {},
            "decision_sha256": sha,
            "dataset_sha256": request["dataset_sha256"],
            "config_sha256": rb.digest({}),
            "pending": status == "PARTIAL",
            "campaign_executed": count > 0,
            "execution_right": False,
            "live_enabled": False,
            "transactions_sent": 0,
        }
        receipt = {
            "schema": "studious.occ-research-receipt.v1",
            "run_id": job_id,
            "request_sha256": rb.digest(request),
            "source_commit": request["source_commit"],
            "dataset_sha256": request["dataset_sha256"],
            "config_sha256": request["config_sha256"],
            "mode": "REPLAY",
            "origin": "OFFLINE_FIXTURE",
            "domain_status": status,
            "report": report,
            "trials_sha256": sha,
            "campaign_executed": count > 0,
            "live_enabled": False,
            "transactions_sent": 0,
            "release_authorized": False,
        }
        self.resign(root, receipt)
        return root, receipt

    def resign(self, root, receipt):
        receipt.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = rb.digest(receipt)
        (root / "receipt.json").write_bytes(rb.canonical(receipt))
        (root / "manifest.json").write_bytes(
            rb.canonical(
                {
                    "state": "COMPLETE",
                    "request_sha256": receipt["request_sha256"],
                    "receipt_sha256": receipt["receipt_sha256"],
                }
            )
        )

    def enqueue(self, key="task"):
        return ac.enqueue(self.store, self.policy, key, self.payload)["id"]

    def test_real_child_retains_windows_systemroot_and_excludes_credentials(self):
        self.enqueue()
        worker = ac.Core(self.store, self.policy)
        job = worker.claim()
        system_root = ac.os.environ.get('SYSTEMROOT', r'C:\Windows')
        with patch.dict(ac.os.environ, {'SYSTEMROOT': system_root,
                                       'OCC_FIXTURE_API_TOKEN': 'excluded-fixture-credential'}):
            result = worker.command(job, [sys.executable, '-I', '-c',
                'import asyncio,json,os; print(json.dumps({"system_root":os.environ.get("SYSTEMROOT"),'
                '"credential":os.environ.get("OCC_FIXTURE_API_TOKEN")}))'], self.root, 10)
        self.assertEqual(result['exit_code'], 0, result['output'])
        self.assertEqual(json.loads(result['output']), {'system_root': system_root, 'credential': None})

    def test_existing_campaign_admits_research_and_binds_only_selected_profile(self):
        import campaign_runtime as campaign
        import workflow_state
        manifest = {'schema':'occ.campaign.v1','campaign_id':'research-model','revision':1,
                    'goal_ids':['WS-029'],'criteria':[{'id':'local-replay','text':'Offline model only'}],
                    'nodes':[{'id':'model','template':'registered','needs':[], 'inputs':['dataset'],
                              'resources':[{'id':'fixture-dataset','mode':'READ'}],'demand':{'ram':1}}],
                    'limits':{'max_elapsed_seconds':600,'max_iterations':10,'no_progress_limit':10,'max_transfers':10}}
        path=self.root/'campaign.json';path.write_text(ac.encoded(manifest))
        selected={'manifest_file':str(path),'manifest_sha256':workflow_state.file_digest(path),
                  'templates':{'registered':self.payload},'inputs':{'dataset':{'file':self.profile['dataset'],'sha256':self.profile['dataset_sha256']}},
                  'capacity':{'ram':2},'lease_seconds':600}
        self.policy['campaigns']={'offline':selected}
        profile,loaded=campaign.load_manifest(self.policy,'offline')
        fingerprint=campaign.node_fingerprint(loaded['nodes'][0],profile,self.policy)
        from copy import deepcopy
        changed=deepcopy(self.policy);changed['research']['unrelated']=self.profile|{'timeout_seconds':11}
        self.assertEqual(campaign.node_fingerprint(loaded['nodes'][0],profile,changed),fingerprint)
        changed['research']['registered']['timeout_seconds']=12
        self.assertNotEqual(campaign.node_fingerprint(loaded['nodes'][0],profile,changed),fingerprint)
        campaign.advance(self.store,self.policy,'offline')
        worker=ac.Core(self.store,self.policy)
        def command(job,*_):
            self.receipt(job['id']);return {'reason':None,'exit_code':0}
        with patch.object(worker,'command',side_effect=command):
            result=worker.run_once()
        self.assertEqual(result['state'],'SUCCEEDED');self.assertFalse(result['result']['qualified'])
        campaign.advance(self.store,self.policy,'offline')

    def test_core_registered_dispatch_persists_process_and_domain_separately(self):
        job = self.enqueue()

        def command(_job, argv, cwd, timeout):
            self.assertEqual(argv[1:4], ["-I", "-X", "utf8"])
            self.assertEqual(argv[-2], "--request")
            request = rb.read_json(Path(argv[-1]))
            self.assertEqual(request, rb.request_for(self.profile, job))
            self.receipt(job)
            return {"reason": None, "exit_code": 0}

        with patch.object(self.core, "command", side_effect=command):
            result = self.core.run_once()
        self.assertEqual(result["state"], "SUCCEEDED")
        self.assertFalse(result["result"]["qualified"])
        self.assertEqual(result["result"]["domain_status"], "MODEL_REPLAY_COMPLETED")
        self.assertEqual(self.enqueue(), job)
        self.assertEqual(self.core.run_once()["state"], "IDLE")

    def test_profile_drift_arbitrary_job_and_nonzero_process_blocked(self):
        with self.assertRaises(ValueError):
            ac.enqueue(self.store, self.policy, "x", self.payload | {"argv": ["shell"]})
        job = self.enqueue()
        with patch.object(
            self.core,
            "command",
            return_value={"reason": "COMMAND_TIMEOUT", "exit_code": -9},
        ):
            result = self.core.run_once()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["result"]["reason"], "COMMAND_TIMEOUT")
        Path(self.profile["dataset"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "DRIFT"):
            self.enqueue("new")

    def test_zero_exit_partial_is_not_success(self):
        job = self.enqueue()

        def command(*_):
            self.receipt(job, status="PARTIAL")
            return {"reason": None, "exit_code": 0}

        with patch.object(self.core, "command", side_effect=command):
            result = self.core.run_once()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["result"]["process_exit_code"], 0)

    def test_independent_receipt_validation(self):
        root, receipt = self.receipt("b" * 32)
        self.assertEqual(rb.verify_receipt(self.profile, "b" * 32)["records"], 1)
        receipt["report"]["useful_calls"] = 2
        self.resign(root, receipt)
        with self.assertRaisesRegex(ValueError, "MISMATCH"):
            rb.verify_receipt(self.profile, "b" * 32)
        receipt["report"]["useful_calls"] = 1
        receipt["live_enabled"] = True
        self.resign(root, receipt)
        with self.assertRaisesRegex(ValueError, "EFFECTS"):
            rb.verify_receipt(self.profile, "b" * 32)

    def test_orphan_reconciliation_never_reexecutes_and_cancel_wins(self):
        job = self.enqueue()
        claimed = self.core.claim()
        self.core.transition(
            claimed,
            "RUNNING",
            checkpoint={"request_sha256": rb.digest(rb.request_for(self.profile, job))},
        )
        self.receipt(job)
        db = ac.connection(self.store)
        with db:
            db.execute("UPDATE jobs SET lease_until=0 WHERE id=?", (job,))
        db.close()
        self.assertIsNone(self.core.claim())
        self.assertEqual(self.core.get(job)["state"], "NEEDS_RECONCILIATION")
        with self.assertRaises(ValueError):
            self.core.reconcile_research(job, False)
        self.core.cancel(job)
        result = self.core.reconcile_research(job, True)
        self.assertEqual(result["state"], "CANCELLED")

    def test_read_only_page_includes_tail_scopes_and_fences_changes(self):
        for i in range(47):
            self.enqueue("task-" + str(i))
        templates = {"research": self.payload}
        before = (self.store / "content.sqlite3").read_bytes()
        pages = []
        offset = 0
        snapshot = None
        while True:
            page = rb.jobs_page(
                self.store, self.policy, templates, offset=offset, snapshot=snapshot
            )
            pages += page["items"]
            snapshot = page["snapshot"]
            if page["next_offset"] is None:
                break
            offset = page["next_offset"]
        self.assertEqual(len(pages), 47)
        self.assertEqual(len({r["id"] for r in pages}), 47)
        self.assertEqual(rb.jobs_page(self.store, self.policy, {})["total"], 0)
        profile = {
            "store": str(self.store),
            "templates": templates,
            "namespaces": ["test"],
        }
        with patch.object(
            ac, "connection", side_effect=AssertionError("reader called writer")
        ):
            result = na.dispatch_loaded(
                {"type": "durable.research.jobs"}, profile, self.policy, desktop=True
            )
        self.assertEqual(result["research"]["total"], 47)
        self.assertEqual(before, (self.store / "content.sqlite3").read_bytes())
        self.core.cancel(pages[0]["id"])
        with self.assertRaisesRegex(ValueError, "SNAPSHOT_CHANGED"):
            rb.jobs_page(
                self.store, self.policy, templates, offset=20, snapshot=snapshot
            )


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "store"
        self.catalog = (
            Path(__file__).resolve().parents[1]
            / "docs/automation/pr020-021/CRITERION_LEDGER.json"
        )
        self.catalog_id = rb.sha_file(self.catalog)
        self.scope = {
            "build": "b",
            "config": "c",
            "dataset": "d",
            "environment": "linux-model",
        }
        self.imported = pq.import_catalog(self.store, self.catalog, self.catalog_id)

    def test_all_1133_exact_criteria_retained_and_immutable_import(self):
        self.assertEqual(self.imported["criteria"], 1133)
        self.assertTrue(
            pq.import_catalog(self.store, self.catalog, self.catalog_id)["reused"]
        )
        result = pq.reconcile(self.store, self.catalog_id, self.scope)
        self.assertEqual(result["total"], 1133)
        self.assertEqual(result["counts"], {"OPEN": 1133})
        source = json.loads(self.catalog.read_text(encoding="utf-8"))
        self.assertEqual(
            {r["criterion_id"]: r["exact_text"] for r in result["criteria"]},
            {r["criterion_id"]: r["exact_text"] for r in source["criteria"]},
        )
        self.assertFalse(result["qualified"])

    def test_deferred_failure_conflict_and_stale_never_reduce_denominator(self):
        source = json.loads(self.catalog.read_text(encoding="utf-8"))
        ids = [r["criterion_id"] for r in source["criteria"][:3]]
        for status in ("DEFERRED", "FAIL"):
            pq.record_claim(
                self.store,
                self.catalog_id,
                ids[0],
                status=status,
                property_name="manual-note",
                scope=self.scope,
                evidence={},
            )
        pq.record_claim(
            self.store,
            self.catalog_id,
            ids[1],
            status="DEFERRED",
            property_name="manual-note",
            scope=self.scope,
            evidence={},
        )
        pq.record_claim(
            self.store,
            self.catalog_id,
            ids[2],
            status="FAIL",
            property_name="manual-note",
            scope=self.scope | {"build": "old"},
            evidence={},
        )
        result = pq.reconcile(self.store, self.catalog_id, self.scope)
        self.assertEqual(result["total"], 1133)
        self.assertEqual(result["counts"]["CONFLICT"], 1)
        self.assertEqual(result["counts"]["DEFERRED"], 1)
        with self.assertRaises(ValueError):
            pq.record_claim(
                self.store,
                self.catalog_id,
                ids[0],
                status="PASS",
                property_name="hash",
                scope=self.scope,
                evidence={},
            )
        with self.assertRaises(ValueError):
            pq.record_claim(
                self.store,
                self.catalog_id,
                "invented",
                status="OPEN",
                property_name="note",
                scope=self.scope,
                evidence={},
            )

    def test_all_started_costs_and_zero_denominator(self):
        cfg = {
            k: str(i) * 64
            for i, k in enumerate(
                (
                    "baseline_sha256",
                    "candidate_sha256",
                    "dataset_sha256",
                    "criteria_sha256",
                )
            )
        }

        def row(id, variant, status, cost, useful):
            return {
                "id": id,
                "variant": variant,
                "status": status,
                "cost_atoms": cost,
                "elapsed_ns": 10,
                "useful_outputs": useful,
                "dataset_sha256": cfg["dataset_sha256"],
                "criteria_sha256": cfg["criteria_sha256"],
                "build_sha256": cfg[variant + "_sha256"],
            }

        attempts = [
            row("a", "baseline", "SUCCEEDED", 10, 1),
            row("b", "candidate", "FAILED", 100, 0),
            row("c", "candidate", "SUCCEEDED", 1, 1),
        ]
        result = pq.benchmark(cfg, attempts)
        self.assertEqual(
            result["totals"]["candidate"]["cost_per_useful_output"],
            {"numerator": 101, "denominator": 1},
        )
        self.assertFalse(result["qualified"])
        self.assertEqual(
            pq.benchmark(cfg, attempts[:2])["status"], "NO_USEFUL_COMPARISON"
        )
        with self.assertRaises(ValueError):
            pq.benchmark(cfg, attempts + [attempts[0]])


if __name__ == "__main__":
    unittest.main()
