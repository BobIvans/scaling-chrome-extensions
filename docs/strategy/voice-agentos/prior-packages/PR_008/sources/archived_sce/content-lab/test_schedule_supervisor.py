"""F-15 bounded supervisor contracts and canonical queue integration."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import schedule_supervisor as supervisor
import schedule_tick

START = 1790812800


def config(**updates):
    value = {"schema": supervisor.SCHEMA, "supervisor_id": "notes-supervisor",
             "enabled": True, "poll_seconds": 10, "max_seconds": 60,
             "max_ticks": 2, "lease_seconds": 30}
    value.update(updates)
    return value


def schedule(**updates):
    value = {"schema": schedule_tick.SCHEMA, "schedule_id": "notes-day",
             "enabled": True, "template": "sync-notes",
             "start_at_utc": "2026-10-01T00:00:00Z",
             "interval_seconds": 3600, "occurrences": 24}
    value.update(updates)
    return value


class FakeRuntime:
    def __init__(self, *, interrupt=False, wall=START):
        self.elapsed, self.now, self.interrupt, self.waits = 0, wall, interrupt, []

    def monotonic(self):
        return self.elapsed

    def wall(self):
        return self.now

    def pause(self, seconds):
        self.waits.append(seconds)
        self.elapsed += seconds
        self.now += seconds
        return self.interrupt


class SupervisorContractTests(unittest.TestCase):
    def test_strict_schema_types_and_limits(self):
        self.assertEqual(config(), supervisor.validate_config(config()))
        values = [None, [], {}, {**config(), "argv": ["unsafe"]}]
        values += [{k: v for k, v in config().items() if k != field} for field in config()]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                supervisor.validate_config(value)
        for value in (0, 1, "false", None):
            with self.assertRaisesRegex(ValueError, "BOOLEAN"):
                supervisor.validate_config(config(enabled=value))
        for field, values in {"poll_seconds": [9, 3601, True, 10.0],
                              "max_seconds": [59, 86401, "60"],
                              "max_ticks": [0, 8641, 2.0],
                              "lease_seconds": [29, 7201, False]}.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    supervisor.validate_config(config(**{field: value}))
        with self.assertRaisesRegex(ValueError, "LEASE_TOO_SHORT"):
            supervisor.validate_config(config(poll_seconds=60, lease_seconds=60))

    def test_bounded_json_file_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "supervisor.json"
            path.write_text(json.dumps(config()), encoding="utf-8")
            self.assertEqual(supervisor.load_config(path), config())
            path.write_text('{"enabled":false,"enabled":true}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "DUPLICATE"):
                supervisor.load_config(path)
            path.write_text("x" * (supervisor.MAX_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "INPUT_LIMIT"):
                supervisor.load_config(path)


class SupervisorLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "store"
        self.profile_path = self.root / "profile.json"
        self.profile = {"store": str(self.store), "templates": {}}
        self.calls = []

        def connect(store):
            store.mkdir(parents=True, exist_ok=True)
            return sqlite3.connect(store / "lease.sqlite3")

        def tick(value, profile, **kwargs):
            self.calls.append(kwargs)
            return {"state": "ADMITTED", "enqueued": len(self.calls) == 1,
                    "job": {"id": "f" * 32}, "worker_started": False}

        self.connect, self.tick = connect, tick
        self.deps = patch.object(supervisor, "_dependencies",
                                 return_value=(lambda _: (self.profile, {}), connect, tick))
        self.deps.start()
        self.addCleanup(self.deps.stop)

    def call(self, cfg=None, *, runtime=None, **kwargs):
        return supervisor.supervise(cfg or config(), schedule(), self.profile_path,
                                    runtime=runtime or FakeRuntime(), **kwargs)

    def lease_count(self):
        if not self.store.exists():
            return 0
        db = self.connect(self.store)
        try:
            row = db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' "
                             "AND name='bounded_schedule_supervisors'").fetchone()[0]
            return db.execute("SELECT count(*) FROM bounded_schedule_supervisors").fetchone()[0] if row else 0
        finally:
            db.close()

    def test_preview_and_disabled_apply_do_not_create_lease(self):
        preview = self.call()
        self.assertEqual(preview["state"], "PREVIEW")
        self.assertFalse(preview["worker_started"])
        self.assertEqual(self.lease_count(), 0)
        disabled = self.call(config(enabled=False), apply=True)
        self.assertEqual(disabled["state"], "SUPERVISOR_DISABLED")
        self.assertEqual(self.lease_count(), 0)

    def test_max_ticks_is_bounded_and_cleanly_releases_lease(self):
        run = FakeRuntime()
        result = self.call(apply=True, runtime=run)
        self.assertEqual(result["state"], "MAX_TICKS_REACHED")
        self.assertEqual(result["ticks"], 2)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(run.waits, [10])
        self.assertEqual(self.lease_count(), 0)
        self.call(apply=True)  # A clean prior run does not strand authority.

    def test_interrupt_is_clean_but_does_not_persistently_stop_schedule(self):
        result = self.call(apply=True, runtime=FakeRuntime(interrupt=True))
        self.assertEqual(result["state"], "INTERRUPTED")
        self.assertFalse(result["future_admissions_stopped"])
        self.assertEqual(result["ticks"], 1)
        self.assertEqual(self.lease_count(), 0)

    def test_active_and_expired_lease_need_explicit_reconciliation(self):
        supervisor._acquire(self.store, self.connect, "notes-day", "first", "a" * 32,
                            START, 30)
        with self.assertRaisesRegex(ValueError, "ALREADY_ACTIVE"):
            self.call(apply=True, runtime=FakeRuntime(wall=START + 1))
        with self.assertRaisesRegex(ValueError, "NEEDS_RECONCILIATION"):
            self.call(apply=True, runtime=FakeRuntime(wall=START + 31))
        with self.assertRaisesRegex(ValueError, "STILL_ACTIVE"):
            self.call(reconcile=True, runtime=FakeRuntime(wall=START + 1))
        cleared = self.call(reconcile=True, runtime=FakeRuntime(wall=START + 31))
        self.assertEqual(cleared, {"state": "EXPIRED_LEASE_RECONCILED", "cleared": True})
        self.assertEqual(self.lease_count(), 0)

    def test_unknown_tick_failure_retains_lease_until_reconciliation(self):
        def failed(*_args, **_kwargs):
            raise ValueError("UNKNOWN_TICK_EFFECT")
        with patch.object(supervisor, "_dependencies",
                          return_value=(lambda _: (self.profile, {}), self.connect, failed)):
            with self.assertRaisesRegex(ValueError, "UNKNOWN_TICK_EFFECT"):
                self.call(apply=True)
        self.assertEqual(self.lease_count(), 1)
        with self.assertRaisesRegex(ValueError, "NEEDS_RECONCILIATION"):
            self.call(apply=True, runtime=FakeRuntime(wall=START + 31))
        self.call(reconcile=True, runtime=FakeRuntime(wall=START + 31))
        self.assertEqual(self.lease_count(), 0)

    def test_stop_from_existing_owner_terminates_and_releases(self):
        def stopped(*_args, **_kwargs):
            return {"state": "STOPPED_FUTURE_ADMISSIONS", "enqueued": False,
                    "inflight_admissions_may_complete": True,
                    "cancels_existing_jobs": False}
        with patch.object(supervisor, "_dependencies",
                          return_value=(lambda _: (self.profile, {}), self.connect, stopped)):
            result = self.call(apply=True)
        self.assertEqual(result["state"], "STOPPED_FUTURE_ADMISSIONS")
        self.assertFalse(result["last"]["cancels_existing_jobs"])
        self.assertEqual(self.lease_count(), 0)

    def test_lost_lease_blocks_without_releasing_someone_elses_lease(self):
        def steals(value, profile, **kwargs):
            db = self.connect(self.store)
            db.execute("UPDATE bounded_schedule_supervisors SET token=?", ("b" * 32,))
            db.commit(); db.close()
            return {"state": "ADMITTED", "worker_started": False}
        with patch.object(supervisor, "_dependencies",
                          return_value=(lambda _: (self.profile, {}), self.connect, steals)):
            with self.assertRaisesRegex(ValueError, "LEASE_LOST"):
                self.call(apply=True)
        self.assertEqual(self.lease_count(), 1)

    def test_cli_failure_does_not_disclose_absolute_paths(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = supervisor.main(["--supervisor", str(self.root / "missing"),
                                    "--schedule", str(self.root / "other"),
                                    "--profile", str(self.profile_path)])
        self.assertEqual(code, 2)
        self.assertNotIn(str(self.root), output.getvalue())


class CanonicalSupervisorIntegrationTests(unittest.TestCase):
    def test_two_ticks_replay_one_real_core_job_and_release_supervisor_lease(self):
        from automation_core import connection
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source"; source.mkdir()
            store = root / "store"
            policy = {"schema": "occ.automation-policy.v1", "max_parallel": 1,
                      "money_budget": 0,
                      "sources": {"notes": {"namespace": "notes", "root": str(source)}},
                      "repos": {}}
            policy_path = root / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            profile = {"schema": "occ.native-durable-profile.v1", "store": str(store),
                       "policy_file": str(policy_path), "namespaces": ["notes"],
                       "templates": {"sync-notes": {"kind": "sync",
                                                       "source_profile": "notes"}}}
            profile_path = root / "profile.json"
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            result = supervisor.supervise(config(), schedule(), profile_path,
                                          apply=True, runtime=FakeRuntime())
            self.assertEqual(result["state"], "MAX_TICKS_REACHED")
            self.assertFalse(result["worker_started"])
            db = connection(store)
            try:
                self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM job_events").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM bounded_schedule_supervisors").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT state FROM jobs").fetchone()[0], "QUEUED")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
