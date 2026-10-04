"""Schedule contracts plus real canonical-queue integration in the full checkout."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import schedule_tick as scheduler

START = 1790812800  # 2026-10-01 00:00:00 UTC


def plan(**updates):
    value = {"schema": scheduler.SCHEMA, "schedule_id": "sample-day",
             "enabled": True, "template": "sync-notes",
             "start_at_utc": "2026-10-01T00:00:00Z",
             "interval_seconds": 3600, "occurrences": 24}
    value.update(updates)
    return value


class ScheduleContractTests(unittest.TestCase):
    def test_copy_not_mutation(self):
        value = plan()
        self.assertEqual(value, scheduler.validate_schedule(value))
        self.assertIsNot(value, scheduler.validate_schedule(value))

    def test_missing_extra_and_nonobject(self):
        values = [None, [], "sync", {}, {**plan(), "argv": ["unsafe"]}]
        values += [{k: v for k, v in plan().items() if k != field} for field in plan()]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                scheduler.validate_schedule(value)

    def test_flags_are_not_coerced(self):
        for value in (0, 1, None, "false", [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "BOOLEAN"):
                scheduler.validate_schedule(plan(enabled=value))

    def test_intervals_and_window_limits(self):
        for value in (True, 3599, 0, -1, 86401, 3600.0, "3600"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scheduler.validate_schedule(plan(interval_seconds=value))
        for value in (True, 0, 25, 1.0, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scheduler.validate_schedule(plan(occurrences=value))
        with self.assertRaises(ValueError):
            scheduler.validate_schedule(plan(interval_seconds=7200, occurrences=24))
        self.assertEqual(scheduler.validate_schedule(plan(interval_seconds=86400, occurrences=1))["occurrences"], 1)

    def test_identifiers(self):
        for name in (None, 1, "", "../escape", "a/b", "x" * 41, "x\n", "a:b"):
            for field in ("schedule_id", "template"):
                with self.subTest(name=name, field=field), self.assertRaises(ValueError):
                    scheduler.validate_schedule(plan(**{field: name}))

    def test_exact_utc(self):
        for value in ("2026-10-01", "2026-10-01T00:00:00+03:00",
                      "2026-10-01T00:00:00", "2026-02-30T00:00:00Z", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scheduler.validate_schedule(plan(start_at_utc=value))

    def test_clock_rejects_nonfinite_and_coercions(self):
        for value in (True, float("nan"), float("inf"), "1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scheduler.due_slot(plan(), value)

    def test_disabled_and_window_boundaries(self):
        self.assertEqual(scheduler.due_slot(plan(enabled=False), START)["state"], "DISABLED")
        self.assertEqual(scheduler.due_slot(plan(), START - 1)["state"], "NOT_DUE")
        self.assertEqual(scheduler.due_slot(plan(), START)["slot"], 0)
        self.assertEqual(scheduler.due_slot(plan(), START + 3599)["slot"], 0)
        self.assertEqual(scheduler.due_slot(plan(), START + 3600)["slot"], 1)
        self.assertEqual(scheduler.due_slot(plan(), START + 86399)["slot"], 23)
        self.assertEqual(scheduler.due_slot(plan(), START + 86400)["state"], "EXPIRED")

    def test_missed_slots_not_expanded(self):
        result = scheduler.due_slot(plan(), START + 10 * 3600)
        self.assertEqual(result, {"state": "DUE", "slot": 10, "task_key": "schedule:sample-day:10"})

    def test_json_input_bounds_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schedule.json"
            path.write_text(json.dumps(plan()), encoding="utf-8")
            self.assertEqual(scheduler.load_schedule(path), plan())
            path.write_text('{"enabled":false,"enabled":true}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "DUPLICATE"):
                scheduler.load_schedule(path)
            path.write_text("x" * (scheduler.MAX_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "INPUT_LIMIT"):
                scheduler.load_schedule(path)
            with self.assertRaises(ValueError):
                scheduler.load_schedule(Path(directory))

    def test_disabled_does_not_load_runtime(self):
        with patch.object(scheduler, "_runtime", side_effect=AssertionError("runtime called")):
            result = scheduler.tick(plan(enabled=False), Path.cwd() / "missing.json", apply=True, now=START)
        self.assertEqual(result["state"], "DISABLED")

    def test_relative_profile_and_invalid_modes(self):
        with self.assertRaisesRegex(ValueError, "ABSOLUTE"):
            scheduler.tick(plan(), "relative.json", now=START)
        for flags in ({"apply": 1}, {"stop": "yes"}, {"apply": True, "stop": True}):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                scheduler.tick(plan(), Path.cwd() / "profile.json", now=START, **flags)


class ControlContractTests(unittest.TestCase):
    """Real SQLite for control; fake enqueue explicitly is NOT worker evidence."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = {"store": str(self.root / "store"),
                        "templates": {"sync-notes": {"kind": "sync", "source_profile": "notes"}}}
        self.policy = {"schema": "occ.automation-policy.v1", "max_parallel": 1, "money_budget": 0}
        self.calls = []

        def connect(store):
            store.mkdir(parents=True, exist_ok=True)
            return sqlite3.connect(store / "control.sqlite3")

        def enqueue(store, policy, key, payload):
            self.calls.append((key, payload))
            return {"id": "f" * 32, "state": "QUEUED", "reused": False}

        self.runtime = (lambda path: (self.profile, self.policy), connect, enqueue)
        self.mock = patch.object(scheduler, "_runtime", return_value=self.runtime)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def call(self, value=None, **kwargs):
        return scheduler.tick(value or plan(), self.root / "profile.json", now=START, **kwargs)

    def test_preview_has_no_control_or_queue_write(self):
        self.assertEqual(self.call()["state"], "PREVIEW")
        self.assertEqual(self.calls, [])
        self.assertFalse(Path(self.profile["store"]).exists())

    def test_apply_delegates_only_registered_payload(self):
        result = self.call(apply=True)
        self.assertEqual(self.calls, [("schedule:sample-day:0", {"kind": "sync", "source_profile": "notes"})])
        self.assertFalse(result["worker_started"])

    def test_unknown_and_nonsync_templates_blocked(self):
        with self.assertRaisesRegex(ValueError, "REGISTERED_SYNC_ONLY"):
            self.call(plan(template="missing"), apply=True)
        self.profile["templates"]["sync-notes"] = {"kind": "patch_test_ci"}
        with self.assertRaisesRegex(ValueError, "REGISTERED_SYNC_ONLY"):
            self.call(apply=True)
        self.assertEqual(self.calls, [])

    def test_stop_persists_and_does_not_admit(self):
        self.assertEqual(self.call(stop=True)["state"], "STOPPED_FUTURE_ADMISSIONS")
        for _ in range(2):
            self.assertFalse(self.call(apply=True)["enqueued"])
        self.assertEqual(self.calls, [])

    def test_changed_definition_rejected(self):
        self.call(apply=True)
        with self.assertRaisesRegex(ValueError, "BINDING_CHANGED"):
            self.call(plan(occurrences=12), apply=True)
        self.assertEqual(len(self.calls), 1)

    def test_changed_profile_or_policy_rejected(self):
        self.call(apply=True)
        self.policy["new_setting"] = "changed"
        with self.assertRaisesRegex(ValueError, "BINDING_CHANGED"):
            self.call(apply=True)
        self.assertEqual(len(self.calls), 1)

    def test_disable_does_not_reset_stop(self):
        self.call(stop=True)
        self.assertEqual(self.call(plan(enabled=False), apply=True)["state"], "DISABLED")
        self.assertEqual(self.call(apply=True)["state"], "STOPPED_FUTURE_ADMISSIONS")

    def test_cli_errors_do_not_print_paths(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = scheduler.main(["--schedule", str(self.root / "missing"), "--profile", str(self.root / "profile.json")])
        self.assertEqual(code, 2)
        self.assertNotIn(str(self.root), output.getvalue())


class CanonicalQueueIntegrationTests(unittest.TestCase):
    """Requires the full existing checkout; CI's test_*.py discovery runs this."""
    def setUp(self):
        from automation_core import connection
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "source"
        source.mkdir()
        self.store = self.root / "store"
        policy = {"schema": "occ.automation-policy.v1", "max_parallel": 1, "money_budget": 0,
                  "sources": {"notes": {"namespace": "notes", "root": str(source)}}, "repos": {}}
        self.policy_path = self.root / "policy.json"
        self.policy_path.write_text(json.dumps(policy), encoding="utf-8")
        profile = {"schema": "occ.native-durable-profile.v1", "store": str(self.store),
                   "policy_file": str(self.policy_path), "namespaces": ["notes"],
                   "templates": {"sync-notes": {"kind": "sync", "source_profile": "notes"}}}
        self.profile_path = self.root / "profile.json"
        self.profile_path.write_text(json.dumps(profile), encoding="utf-8")
        self.policy = policy
        db = connection(self.store)
        db.close()

    def call(self, *, now=START, stop=False):
        return scheduler.tick(plan(), self.profile_path, apply=not stop, stop=stop, now=now)

    def test_replay_reuses_canonical_job_and_event(self):
        from automation_core import connection
        first, second = self.call(), self.call()
        self.assertEqual(first["job"]["id"], second["job"]["id"])
        self.assertTrue(second["job"]["reused"])
        db = connection(self.store)
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM job_events").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT state FROM jobs").fetchone()[0], "QUEUED")
        finally:
            db.close()

    def test_concurrent_admission_still_one_job(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.call(), range(2)))
        self.assertEqual(results[0]["job"]["id"], results[1]["job"]["id"])
        self.assertEqual(sum(result["enqueued"] for result in results), 1)

    def test_cancelled_slot_not_resurrected(self):
        from automation_core import Core
        first = self.call()
        Core(self.store, self.policy).cancel(first["job"]["id"])
        self.assertEqual(self.call()["job"]["state"], "CANCELLED")

    def test_stop_keeps_existing_job_but_prevents_next(self):
        from automation_core import Core
        first = self.call()
        self.assertFalse(self.call(stop=True)["cancels_existing_jobs"])
        self.assertEqual(self.call(now=START + 3600)["state"], "STOPPED_FUTURE_ADMISSIONS")
        self.assertEqual(Core(self.store, self.policy).get(first["job"]["id"])["state"], "QUEUED")

    def test_next_slot_distinct_and_no_catchup(self):
        from automation_core import connection
        first, later = self.call(), self.call(now=START + 10 * 3600)
        self.assertNotEqual(first["job"]["id"], later["job"]["id"])
        db = connection(self.store)
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 2)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
