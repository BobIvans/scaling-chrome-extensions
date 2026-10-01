import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import automation_core as ac


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.store = self.root / "store"
        self.policy = {"schema": "occ.automation-policy.v1", "max_parallel": 1,
                       "money_budget": 0, "sources": {"exports": {
                           "root": str(self.source), "namespace": "occ"}}, "repos": {}}
        self.core = ac.Core(self.store, self.policy)

    def tearDown(self):
        self.temp.cleanup()

    def queue(self, key="one"):
        return ac.enqueue(self.store, self.policy, key,
                          {"kind": "sync", "source_profile": "exports"})["id"]

    def write(self, text="hello roadmap", name="chat.txt"):
        path = self.source / name
        path.write_text(text, encoding="utf-8")
        return path

    def sql(self, query, values=()):
        db = ac.connection(self.store)
        try:
            with db:
                rows = db.execute(query, values).fetchall()
                return rows
        finally:
            db.close()

    def git(self, repo, *args):
        return subprocess.check_output(["git", "-c", "user.name=Fixture", "-c",
                                        "core.autocrlf=false", "-c",
                                        "user.email=fixture@invalid", "-c", "commit.gpgSign=false",
                                        *args], cwd=repo, stderr=subprocess.DEVNULL).decode().strip()

    def patch_fixture(self, values=("good",), tests=None):
        repo = self.root / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q")
        (repo / "value.txt").write_text("bad\n", newline="\n")
        self.git(repo, "add", "value.txt")
        self.git(repo, "commit", "-qm", "base")
        patches = {}
        for number, value in enumerate(values):
            path = self.root / f"patch{number}.diff"
            path.write_text("diff --git a/value.txt b/value.txt\n--- a/value.txt\n+++ b/value.txt\n@@ -1 +1 @@\n-bad\n+" + value + "\n", newline="\n")
            patches[f"p{number}"] = {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        self.snapshot = self.root / "ci.json"
        self.policy["repos"]["fixture"] = {
            "root": str(repo), "base_sha": self.git(repo, "rev-parse", "HEAD"),
            "patches": patches, "allowed_paths": ["value.txt"],
            "tests": tests or [[sys.executable, "-B", "-c", "from pathlib import Path; assert Path('value.txt').read_text() == 'good\\n'"]],
            "timeout_seconds": 3, "retry_delay_seconds": 0,
            "ci": {"snapshot_file": str(self.snapshot), "required_checks": ["test", "lint"]}}
        self.core = ac.Core(self.store, self.policy)
        job = {"kind": "patch_test_ci", "repo_profile": "fixture",
               "patch_ids": list(patches), "max_attempts": len(values)}
        return repo, ac.enqueue(self.store, self.policy, "patch", job)["id"]

    def snapshot_for(self, job_id, conclusion="success", **extra):
        head = self.core.get(job_id)["checkpoint"]["head_sha"]
        snapshot = {"schema": "occ.ci-snapshot.v1", "origin": "operator_github_actions_export",
                    "head_sha": head, "checks": [{"name": name, "run_id": n,
                    "head_sha": head, "status": "completed", "conclusion": conclusion}
                    for n, name in enumerate(["test", "lint"], 10)]}
        snapshot.update(extra)
        self.snapshot.write_text(json.dumps(snapshot))
        return snapshot

    def test_sync_replay_edit_delete_retains_versions_and_filters_stale(self):
        path = self.write()
        first = ac.sync(self.store, "occ", self.source)
        self.assertEqual(first["new_versions"], 1)
        old_id = ac.search(self.store, "occ", "roadmap")[0]["id"]
        self.assertEqual(ac.sync(self.store, "occ", self.source)["unchanged"], 1)
        path.write_text("changed blocker")
        self.assertEqual(ac.sync(self.store, "occ", self.source)["new_versions"], 1)
        self.assertEqual(ac.search(self.store, "occ", "roadmap"), [])
        with self.assertRaisesRegex(ValueError, "STALE"):
            ac.context_pack(self.store, "occ", [old_id])
        path.unlink()
        self.assertEqual(ac.sync(self.store, "occ", self.source)["missing"], 1)
        self.assertEqual(ac.search(self.store, "occ", "blocker"), [])
        self.assertEqual(self.sql("SELECT count(*) FROM sync_versions")[0][0], 2)

    def test_same_text_preserves_source_identity_and_namespace(self):
        self.write(name="a.txt")
        self.write(name="b.txt")
        ac.sync(self.store, "occ", self.source)
        ac.sync(self.store, "other", self.source)
        occ = ac.search(self.store, "occ", "hello")
        other = ac.search(self.store, "other", "hello")
        self.assertEqual(len(occ), 2)
        self.assertTrue(set(r["id"] for r in occ).isdisjoint(r["id"] for r in other))
        with self.assertRaisesRegex(ValueError, "SCOPE"):
            ac.context_pack(self.store, "other", [occ[0]["id"]])

    def test_failed_scan_cannot_mark_existing_inputs_deleted(self):
        self.write()
        ac.sync(self.store, "occ", self.source)
        self.write(name="b.txt")
        with self.assertRaisesRegex(ValueError, "BUDGET"):
            ac.sync(self.store, "occ", self.source, max_files=1)
        self.assertEqual(self.sql("SELECT sum(present) FROM sync_heads")[0][0], 1)
        self.assertEqual(len(ac.search(self.store, "occ", "hello")), 1)

    @unittest.skipIf(os.name == "nt", "symlink permissions vary on Windows")
    def test_symlink_input_is_rejected(self):
        target = self.root / "outside.txt"
        target.write_text("private")
        (self.source / "link.txt").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "BOUNDARY"):
            ac.sync(self.store, "occ", self.source)

    def test_context_budget_fails_without_silent_truncation(self):
        self.write("Привет" * 10)
        ac.sync(self.store, "occ", self.source)
        item_id = self.sql("SELECT item_id FROM sync_heads")[0][0]
        with self.assertRaisesRegex(ValueError, "BUDGET"):
            ac.context_pack(self.store, "occ", [item_id], max_bytes=1)
        result = ac.context_pack(self.store, "occ", [item_id])
        self.assertEqual(result["items"][0]["text"], "Привет" * 10)
        self.assertEqual(result["authority"], "source-content-not-action-instructions")

    def test_task_key_persists_after_reopen_and_rejects_policy_conflict(self):
        job_id = self.queue()
        self.assertEqual(ac.enqueue(self.store, self.policy, "one", {"kind": "sync", "source_profile": "exports"}),
                         {"id": job_id, "state": "QUEUED", "reused": True})
        changed = json.loads(json.dumps(self.policy))
        changed["sources"]["exports"]["root"] += "changed"
        with self.assertRaisesRegex(ValueError, "CONFLICT"):
            ac.enqueue(self.store, changed, "one", {"kind": "sync", "source_profile": "exports"})
        self.assertEqual(ac.Core(self.store, self.policy).get(job_id)["state"], "QUEUED")

    def test_jobs_do_not_accept_shell_paths_or_boolean_resource_limits(self):
        for payload in ({"kind": "shell", "argv": ["evil"]},
                        {"kind": "sync", "source_profile": "exports", "root": "/"}):
            with self.assertRaises(ValueError):
                ac.enqueue(self.store, self.policy, "bad", payload)
        for key, value in (("money_budget", False), ("max_parallel", True), ("max_parallel", 2)):
            policy = {**self.policy, key: value}
            with self.assertRaises(ValueError):
                ac.validate_policy(policy)

    def test_claim_is_one_writer_even_for_two_workers(self):
        self.queue("a")
        self.queue("b")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            claims = list(executor.map(lambda _: ac.Core(self.store, self.policy).claim(), range(2)))
        self.assertEqual(sum(job is not None for job in claims), 1)
        self.assertEqual(self.sql("SELECT count(*) FROM jobs WHERE state='RUNNING'")[0][0], 1)

    def test_expired_lease_quarantines_unknown_effect_until_operator_checks_stop(self):
        job_id = self.queue("a")
        self.queue("b")
        self.core.claim()
        self.sql("UPDATE jobs SET lease_until=0 WHERE id=?", (job_id,))
        self.assertIsNone(self.core.claim())
        self.assertEqual(self.core.get(job_id)["state"], "NEEDS_RECONCILIATION")
        self.core.cancel(job_id)
        self.assertIsNone(self.core.claim())
        with self.assertRaisesRegex(ValueError, "CONFIRMATION"):
            self.core.abandon_orphan(job_id, False)
        self.core.abandon_orphan(job_id, True)
        self.assertIsNotNone(self.core.claim())

    def test_queued_cancel_never_imports_and_policy_change_blocks(self):
        self.write()
        job_id = self.queue()
        self.core.cancel(job_id)
        self.assertEqual(self.core.run_once()["state"], "IDLE")
        self.assertEqual(self.sql("SELECT count(*) FROM items")[0][0], 0)
        second = self.queue("second")
        changed = {**self.policy, "revision": "changed"}
        self.assertIsNone(ac.Core(self.store, changed).claim())
        self.assertEqual(self.core.get(second)["state"], "BLOCKED")

    def test_sync_job_survives_restart_and_replay_does_not_repeat_effect(self):
        self.write()
        job_id = self.queue()
        result = ac.Core(self.store, self.policy).run_once()
        self.assertEqual(result["state"], "SUCCEEDED")
        self.assertEqual(ac.Core(self.store, self.policy).run_once()["state"], "IDLE")
        self.assertEqual(self.sql("SELECT count(*) FROM sync_versions")[0][0], 1)
        self.assertEqual(self.core.get(job_id)["result"]["model_calls"], 0)

    def test_real_worktree_patch_tests_ci_snapshot_success_and_idempotent_replay(self):
        repo, job_id = self.patch_fixture()
        base = self.git(repo, "rev-parse", "HEAD")
        result = self.core.run_once()
        self.assertEqual(result["state"], "WAITING_CI", result)
        self.assertEqual((repo / "value.txt").read_text(), "bad\n")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), base)
        self.assertEqual(Path(result["checkpoint"]["worktree"]).joinpath("value.txt").read_text(), "good\n")
        self.snapshot_for(job_id)
        self.assertEqual(ac.Core(self.store, self.policy).poll_ci()[0]["state"], "SUCCEEDED")
        replay = ac.enqueue(self.store, self.policy, "patch", result["payload"])
        self.assertTrue(replay["reused"])
        self.assertEqual(replay["id"], job_id)
        self.assertEqual(self.core.get(job_id)["attempt"], 1)

    def test_failed_patch_then_prepared_retry_is_bounded_and_uses_fresh_worktree(self):
        _, job_id = self.patch_fixture(("stillbad", "good"))
        first = self.core.run_once()
        self.assertEqual(first["state"], "RETRY_READY", first)
        second = self.core.run_once()
        self.assertEqual(second["state"], "WAITING_CI", second)
        self.assertNotEqual(first["checkpoint"]["worktree"], second["checkpoint"]["worktree"])
        self.snapshot_for(job_id, "failure")
        self.assertEqual(self.core.poll_ci()[0]["state"], "FAILED")
        self.assertEqual(self.core.run_once()["state"], "IDLE")
        self.assertEqual(self.core.get(job_id)["attempt"], 2)

    def test_pinned_crlf_profile_applies_index_patch_and_runs_tests(self):
        _, old_id = self.patch_fixture()
        self.core.cancel(old_id)
        self.policy["repos"]["fixture"]["git_autocrlf"] = True
        self.core = ac.Core(self.store, self.policy)
        ac.enqueue(self.store, self.policy, "crlf", self.core.get(old_id)["payload"])
        result = self.core.run_once()
        self.assertEqual(result["state"], "WAITING_CI", result)
        self.assertEqual((Path(result["checkpoint"]["worktree"]) / "value.txt").read_text(), "good\n")

    def test_ci_wrong_sha_empty_missing_pending_and_untrusted_origin_never_pass(self):
        _, job_id = self.patch_fixture()
        self.assertEqual(self.core.run_once()["state"], "WAITING_CI")
        for extra in ({"head_sha": "a" * 40}, {"checks": []}, {"origin": "page_text"}):
            self.snapshot_for(job_id, **extra)
            self.assertEqual(self.core.poll_ci(), [])
        for change in ("missing", "pending"):
            snapshot = self.snapshot_for(job_id)
            if change == "missing":
                snapshot["checks"].pop()
            else:
                snapshot["checks"][0]["status"] = "in_progress"
            self.snapshot.write_text(json.dumps(snapshot))
            self.assertEqual(self.core.poll_ci(), [])
        self.assertEqual(self.core.get(job_id)["state"], "WAITING_CI")

    def test_latest_ci_failure_overrides_older_green_and_ambiguous_export_blocks(self):
        _, job_id = self.patch_fixture()
        self.core.run_once()
        snapshot = self.snapshot_for(job_id)
        duplicate = {**snapshot["checks"][0], "conclusion": "failure"}
        snapshot["checks"].append(duplicate)
        self.snapshot.write_text(json.dumps(snapshot))
        self.assertEqual(self.core.poll_ci(), [])
        duplicate["run_id"] += 100
        self.snapshot.write_text(json.dumps(snapshot))
        self.assertEqual(self.core.poll_ci()[0]["state"], "FAILED")

    def test_authenticated_ci_origin_is_bound_to_registered_repository_and_checks(self):
        _, old_id = self.patch_fixture()
        payload = self.core.get(old_id)["payload"]
        self.core.cancel(old_id)
        self.policy["repos"]["fixture"]["ci"]["transport"] = {
            "kind": "github_check_runs_v1", "repository": "owner/repo",
            "token_env": "OCC_GITHUB_TOKEN", "timeout_seconds": 10, "max_pages": 2}
        self.core = ac.Core(self.store, self.policy)
        job_id = ac.enqueue(self.store, self.policy, "authenticated", payload)["id"]
        self.assertEqual(self.core.run_once()["state"], "WAITING_CI")
        snapshot = self.snapshot_for(job_id, origin="authenticated_github_check_runs_v1")
        snapshot.update(repository="owner/repo", required_checks=["test", "lint"],
                        transport_status="OBSERVED")
        self.snapshot.write_text(json.dumps(snapshot))
        self.assertEqual(self.core.poll_ci()[0]["state"], "SUCCEEDED")
        self.assertEqual(self.core.get(job_id)["result"]["evidence_origin"],
                         "authenticated_github_check_runs_v1")

    def test_authenticated_ci_mismatch_or_blocked_transport_never_passes(self):
        _, old_id = self.patch_fixture()
        payload = self.core.get(old_id)["payload"]
        self.core.cancel(old_id)
        self.policy["repos"]["fixture"]["ci"]["transport"] = {
            "kind": "github_check_runs_v1", "repository": "owner/repo",
            "token_env": "OCC_GITHUB_TOKEN"}
        self.core = ac.Core(self.store, self.policy)
        job_id = ac.enqueue(self.store, self.policy, "authenticated-blocked", payload)["id"]
        self.core.run_once()
        base = self.snapshot_for(job_id, origin="authenticated_github_check_runs_v1")
        base.update(repository="owner/repo", required_checks=["test", "lint"],
                    transport_status="OBSERVED")
        for change in ({"repository": "other/repo"}, {"required_checks": ["test"]},
                       {"transport_status": "BLOCKED"}):
            snapshot = {**base, **change}
            self.snapshot.write_text(json.dumps(snapshot))
            self.assertEqual(self.core.poll_ci(), [])
        self.assertEqual(self.core.get(job_id)["state"], "WAITING_CI")

    def test_policy_rejects_unregistered_ci_transport_shape(self):
        _, old_id = self.patch_fixture()
        self.core.cancel(old_id)
        ci_policy = self.policy["repos"]["fixture"]["ci"]
        ci_policy["transport"] = {"kind": "github_check_runs_v1",
                                  "repository": "owner/repo", "token_env": "TOKEN"}
        with self.assertRaisesRegex(ValueError, "CI_TRANSPORT_SCHEMA"):
            ac.enqueue(self.store, self.policy, "bad-transport", self.core.get(old_id)["payload"])

    def test_changed_patch_is_blocked_before_test_execution(self):
        repo, job_id = self.patch_fixture()
        path = Path(self.policy["repos"]["fixture"]["patches"]["p0"]["file"])
        path.write_text(path.read_text() + "tampered")
        result = self.core.run_once()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["result"]["reason"], "PATCH_HASH_CHANGED")
        self.assertEqual((repo / "value.txt").read_text(), "bad\n")

    def test_dirty_base_is_blocked_before_patch(self):
        repo, _ = self.patch_fixture()
        (repo / "value.txt").write_text("operator edit\n")
        result = self.core.run_once()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["result"]["reason"], "CLEAN_OPERATOR_CHECKOUT_REQUIRED")
        self.assertEqual((repo / "value.txt").read_text(), "operator edit\n")

    def test_unregistered_changed_path_blocks_before_tests(self):
        _, job_id = self.patch_fixture()
        self.policy["repos"]["fixture"]["allowed_paths"] = ["different.txt"]
        # New policy requires a new task; an existing binding cannot silently change.
        self.core.cancel(job_id)
        self.core = ac.Core(self.store, self.policy)
        ac.enqueue(self.store, self.policy, "new", self.core.get(job_id)["payload"])
        result = self.core.run_once()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertIn("REGISTERED_PATHS", result["result"]["reason"])

    def test_new_nested_file_matches_an_explicit_registered_path(self):
        _, old_id = self.patch_fixture()
        self.core.cancel(old_id)
        profile = self.policy["repos"]["fixture"]
        patch_path = Path(profile["patches"]["p0"]["file"])
        patch_path.write_text(patch_path.read_text() +
                             "diff --git a/src/new.txt b/src/new.txt\nnew file mode 100644\n--- /dev/null\n+++ b/src/new.txt\n@@ -0,0 +1 @@\n+additional\n", newline="\n")
        profile["patches"]["p0"]["sha256"] = hashlib.sha256(patch_path.read_bytes()).hexdigest()
        profile["allowed_paths"].append("src/new.txt")
        self.core = ac.Core(self.store, self.policy)
        ac.enqueue(self.store, self.policy, "nested", self.core.get(old_id)["payload"])
        result = self.core.run_once()
        self.assertEqual(result["state"], "WAITING_CI", result)
        self.assertEqual((Path(result["checkpoint"]["worktree"]) / "src/new.txt").read_text(), "additional\n")

    def test_command_timeout_output_limit_and_dirty_test_fail(self):
        for code, reason in (("import time; time.sleep(5)", "COMMAND_TIMEOUT"),
                             ("print('x' * 200000)", "COMMAND_OUTPUT_LIMIT"),
                             ("from pathlib import Path; Path('value.txt').write_text('mutated')", "TEST_MUTATED_WORKTREE")):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                old_root, old_store, old_policy = self.root, self.store, self.policy
                self.root, self.store = Path(temp), Path(temp) / "store"
                self.policy = {"schema": "occ.automation-policy.v1", "max_parallel": 1, "money_budget": 0, "sources": {}, "repos": {}}
                self.patch_fixture(tests=[[sys.executable, "-B", "-c", code]])
                self.policy["repos"]["fixture"]["timeout_seconds"] = 1
                # Rebind only this freshly-created synthetic task to the final profile.
                self.sql("UPDATE jobs SET policy_hash=?", (ac.digest(self.policy),))
                result = self.core.run_once()
                self.assertIn(result["state"], {"FAILED", "BLOCKED"}, result)
                if reason == "TEST_MUTATED_WORKTREE":
                    self.assertEqual(result["result"]["reason"], reason)
                else:
                    self.assertEqual(result["result"]["tests"][0]["reason"], reason)
                self.root, self.store, self.policy = old_root, old_store, old_policy

    def test_running_cancel_stops_process_and_keeps_terminal_state(self):
        _, job_id = self.patch_fixture(tests=[[sys.executable, "-B", "-c", "import time; time.sleep(5)"]])
        results = []
        thread = threading.Thread(target=lambda: results.append(self.core.run_once()))
        thread.start()
        deadline = time.monotonic() + 3
        while not self.core.get(job_id)["checkpoint"] and time.monotonic() < deadline:
            time.sleep(0.02)
        self.core.cancel(job_id)
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.core.get(job_id)["state"], "CANCELLED")


if __name__ == "__main__":
    unittest.main()
