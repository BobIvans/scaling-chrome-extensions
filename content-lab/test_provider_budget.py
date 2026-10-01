import concurrent.futures
from pathlib import Path
import tempfile
import unittest

import automation_core as ac
import provider_budget as pb


HASH_A = "a" * 64


class ProviderBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        self.plan = {"schema": "occ.provider-budget.v1", "budget_id": "run-1",
                     "currency": "USD_MICRO", "hard_cap_microunits": 100,
                     "max_attempts": 2}

    def tearDown(self):
        self.temp.cleanup()

    def test_zero_budget_rejects_before_operation_exists(self):
        plan = {**self.plan, "hard_cap_microunits": 0}
        with self.assertRaisesRegex(ValueError, "ZERO_BUDGET"):
            pb.reserve_budget(self.store, plan, "call-1", 1)
        db = ac.connection(self.store)
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM provider_budgets").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM provider_budget_ops").fetchone()[0], 0)
        finally:
            db.close()

    def test_hard_cap_is_atomic_for_concurrent_callers(self):
        pb.initialize_budget_store(self.store)

        def reserve(key):
            try:
                return pb.reserve_budget(self.store, self.plan, key, 60)["state"]
            except ValueError as exc:
                return str(exc)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(reserve, ("call-a", "call-b")))
        self.assertEqual(outcomes.count("RESERVED"), 1)
        self.assertEqual(outcomes.count("BUDGET_HARD_CAP_EXCEEDED"), 1)
        status = pb.budget_status(self.store, "run-1")
        self.assertEqual((status["reserved_microunits"], status["used_microunits"],
                          status["remaining_microunits"]), (60, 0, 40))

    def test_reservation_replay_and_conflicts_do_not_double_count(self):
        first = pb.reserve_budget(self.store, self.plan, "call-1", 30)
        self.assertEqual(pb.reserve_budget(self.store, self.plan, "call-1", 30), first)
        self.assertEqual(pb.budget_status(self.store, "run-1")["reserved_microunits"], 30)
        with self.assertRaisesRegex(ValueError, "OPERATION_CONFLICT"):
            pb.reserve_budget(self.store, self.plan, "call-1", 31)
        with self.assertRaisesRegex(ValueError, "PLAN_CONFLICT"):
            pb.reserve_budget(self.store, {**self.plan, "hard_cap_microunits": 101}, "call-2", 1)

    def test_settlement_moves_reserved_to_used_and_is_idempotent(self):
        reservation = pb.reserve_budget(self.store, self.plan, "call-1", 40)
        with self.assertRaisesRegex(ValueError, "ACTUAL_EXCEEDS"):
            pb.settle_budget(self.store, reservation["reservation_id"], 41, HASH_A)
        settled = pb.settle_budget(self.store, reservation["reservation_id"], 27, HASH_A)
        self.assertEqual(settled["state"], "SETTLED")
        self.assertFalse(settled["call_allowed"])
        self.assertEqual(pb.settle_budget(self.store, reservation["reservation_id"], 27, HASH_A), settled)
        status = pb.budget_status(self.store, "run-1")
        self.assertEqual((status["reserved_microunits"], status["used_microunits"],
                          status["remaining_microunits"]), (0, 27, 73))
        with self.assertRaisesRegex(ValueError, "SETTLEMENT_CONFLICT"):
            pb.settle_budget(self.store, reservation["reservation_id"], 28, HASH_A)

    def test_release_requires_proof_and_retry_is_explicit_and_bounded(self):
        first = pb.reserve_budget(self.store, self.plan, "call-1", 40)
        with self.assertRaisesRegex(ValueError, "CONFIRMATION"):
            pb.release_budget(self.store, first["reservation_id"], request_not_sent=False)
        released = pb.release_budget(self.store, first["reservation_id"], request_not_sent=True)
        self.assertEqual(pb.reserve_budget(self.store, self.plan, "call-1", 40), released)
        with self.assertRaisesRegex(ValueError, "MISMATCH"):
            pb.reserve_budget(self.store, self.plan, "call-1", 40,
                              retry_reservation_id="rsv-not-the-owner")
        second = pb.reserve_budget(self.store, self.plan, "call-1", 40,
                                   retry_reservation_id=first["reservation_id"])
        self.assertEqual(second["attempt"], 2)
        pb.release_budget(self.store, second["reservation_id"], request_not_sent=True)
        with self.assertRaisesRegex(ValueError, "RETRY_LIMIT"):
            pb.reserve_budget(self.store, self.plan, "call-1", 40,
                              retry_reservation_id=second["reservation_id"])
        self.assertEqual(pb.budget_status(self.store, "run-1")["reserved_microunits"], 0)

    def test_unknown_effect_stays_reserved_until_explicit_reconciliation(self):
        reservation = pb.reserve_budget(self.store, self.plan, "call-1", 50)
        unknown = pb.mark_budget_unknown(self.store, reservation["reservation_id"])
        self.assertEqual(unknown["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(pb.mark_budget_unknown(self.store, reservation["reservation_id"]), unknown)
        with self.assertRaisesRegex(ValueError, "RECONCILIATION_REQUIRED"):
            pb.reserve_budget(self.store, self.plan, "call-1", 50,
                              retry_reservation_id=reservation["reservation_id"])
        with self.assertRaisesRegex(ValueError, "RESERVED_STATE"):
            pb.settle_budget(self.store, reservation["reservation_id"], 20, HASH_A)
        settled = pb.reconcile_budget(self.store, reservation["reservation_id"], 20, HASH_A)
        self.assertEqual(pb.reconcile_budget(self.store, reservation["reservation_id"], 20, HASH_A), settled)
        status = pb.budget_status(self.store, "run-1")
        self.assertEqual((status["reserved_microunits"], status["used_microunits"]), (0, 20))
        self.assertEqual([event["state"] for event in status["events"]],
                         ["RESERVED", "NEEDS_RECONCILIATION", "SETTLED"])

    def test_schema_is_strict_and_existing_jobs_share_store_unchanged(self):
        for changed in (
                {**self.plan, "hard_cap_microunits": True},
                {**self.plan, "max_attempts": "2"},
                {**self.plan, "currency": "EUR_MICRO"},
                {**self.plan, "extra": 1}):
            with self.assertRaises(ValueError):
                pb.reserve_budget(self.store, changed, "call-1", 1)
        with self.assertRaises(ValueError):
            pb.reserve_budget(self.store, self.plan, "call-1", False)
        db = ac.connection(self.store)
        try:
            with db:
                db.execute("INSERT INTO jobs(id,task_key,payload,payload_hash,policy_hash,state,attempt,max_attempts,available,lease_until,lease_token,cancel_requested,checkpoint,result,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("job-1", "keep", "{}", "p", "q", "QUEUED", 0, 1,
                            0, None, None, 0, None, None, 0, 0))
        finally:
            db.close()
        pb.reserve_budget(self.store, self.plan, "call-1", 1)
        db = ac.connection(self.store)
        try:
            self.assertEqual(db.execute("SELECT state FROM jobs WHERE id='job-1'").fetchone()[0], "QUEUED")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
