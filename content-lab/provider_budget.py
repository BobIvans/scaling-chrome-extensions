"""Atomic provider-budget reservations in Content Lab's existing SQLite owner.

This module is a local accounting contract.  It does not dispatch provider
requests, read credentials, or grant action authority.  A future reviewed
backend must reserve before a request and settle, release, or explicitly
reconcile every reservation.
"""

from __future__ import annotations

import re
import time
import uuid

from automation_core import connection, digest, identifier, strict_int


SCHEMA = "occ.provider-budget.v1"
RECEIPT_SCHEMA = "occ.provider-budget-reservation.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_MICROUNITS = 1_000_000_000_000


def _plan(plan):
    expected = {"schema", "budget_id", "currency", "hard_cap_microunits",
                "max_attempts"}
    if not isinstance(plan, dict) or set(plan) != expected or plan.get("schema") != SCHEMA:
        raise ValueError("PROVIDER_BUDGET_SCHEMA")
    identifier(plan["budget_id"])
    if plan["currency"] != "USD_MICRO":
        raise ValueError("USD_MICRO_REQUIRED")
    strict_int(plan["hard_cap_microunits"], 0, MAX_MICROUNITS)
    strict_int(plan["max_attempts"], 1, 3)
    return plan


def _amount(value, *, allow_zero=False):
    return strict_int(value, 0 if allow_zero else 1, MAX_MICROUNITS)


def _sha256(value):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError("PROVIDER_RECEIPT_SHA256_REQUIRED")
    return value


def _schema(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS provider_budgets(
          id TEXT PRIMARY KEY, plan_hash TEXT NOT NULL, currency TEXT NOT NULL,
          hard_cap_microunits INTEGER NOT NULL,
          reserved_microunits INTEGER NOT NULL,
          used_microunits INTEGER NOT NULL,
          created REAL NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS provider_budget_ops(
          op_key TEXT PRIMARY KEY, budget_id TEXT NOT NULL,
          request_hash TEXT NOT NULL, reserve_microunits INTEGER NOT NULL,
          state TEXT NOT NULL, attempt INTEGER NOT NULL,
          max_attempts INTEGER NOT NULL, reservation_id TEXT UNIQUE NOT NULL,
          actual_microunits INTEGER, provider_receipt_sha256 TEXT,
          created REAL NOT NULL, updated REAL NOT NULL,
          FOREIGN KEY(budget_id) REFERENCES provider_budgets(id));
        CREATE TABLE IF NOT EXISTS provider_budget_events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT, op_key TEXT NOT NULL,
          attempt INTEGER NOT NULL, reservation_id TEXT NOT NULL,
          state TEXT NOT NULL, reserve_microunits INTEGER NOT NULL,
          actual_microunits INTEGER, provider_receipt_sha256 TEXT,
          observed REAL NOT NULL);
    """)


def initialize_budget_store(store):
    """Create budget tables before starting concurrent backend workers."""
    db = connection(store)
    try:
        _schema(db)
    finally:
        db.close()


def _transaction(db, callback):
    db.execute("BEGIN IMMEDIATE")
    try:
        result = callback()
    except Exception:
        db.rollback()
        raise
    db.commit()
    return result


def _budget(db, plan, now):
    plan_hash = digest(plan)
    row = db.execute("SELECT * FROM provider_budgets WHERE id=?",
                     (plan["budget_id"],)).fetchone()
    if row is None:
        db.execute("INSERT INTO provider_budgets VALUES (?,?,?,?,?,?,?,?)",
                   (plan["budget_id"], plan_hash, plan["currency"],
                    plan["hard_cap_microunits"], 0, 0, now, now))
        row = db.execute("SELECT * FROM provider_budgets WHERE id=?",
                         (plan["budget_id"],)).fetchone()
    elif row["plan_hash"] != plan_hash:
        raise ValueError("BUDGET_PLAN_CONFLICT")
    return row


def _operation_receipt(row):
    return {
        "schema": RECEIPT_SCHEMA,
        "budget_id": row["budget_id"],
        "op_key": row["op_key"],
        "reservation_id": row["reservation_id"],
        "state": row["state"],
        "attempt": row["attempt"],
        "max_attempts": row["max_attempts"],
        "reserve_microunits": row["reserve_microunits"],
        "actual_microunits": row["actual_microunits"],
        "provider_receipt_sha256": row["provider_receipt_sha256"],
        "call_allowed": row["state"] == "RESERVED",
        "action_authority": False,
    }


def _event(db, row, now):
    db.execute("INSERT INTO provider_budget_events(op_key,attempt,reservation_id,state,reserve_microunits,actual_microunits,provider_receipt_sha256,observed) VALUES (?,?,?,?,?,?,?,?)",
               (row["op_key"], row["attempt"], row["reservation_id"],
                row["state"], row["reserve_microunits"],
                row["actual_microunits"], row["provider_receipt_sha256"], now))


def reserve_budget(store, plan, op_key, reserve_microunits, *, retry_reservation_id=None):
    """Atomically reserve a hard-cap amount; replay never reserves twice."""
    plan = _plan(plan)
    identifier(op_key)
    amount = _amount(reserve_microunits)
    if retry_reservation_id is not None:
        identifier(retry_reservation_id)
    request_hash = digest({"budget_id": plan["budget_id"], "op_key": op_key,
                           "reserve_microunits": amount})
    db = connection(store)
    try:
        _schema(db)

        def mutate():
            now = time.time()
            budget = _budget(db, plan, now)
            existing = db.execute("SELECT * FROM provider_budget_ops WHERE op_key=?",
                                  (op_key,)).fetchone()
            if existing is not None and (existing["budget_id"] != plan["budget_id"]
                                         or existing["request_hash"] != request_hash):
                raise ValueError("BUDGET_OPERATION_CONFLICT")
            if retry_reservation_id is None and existing is not None:
                return {**_operation_receipt(existing), "reused": True}
            if plan["hard_cap_microunits"] == 0:
                raise ValueError("ZERO_BUDGET_REJECTS_CALL")
            if existing is None:
                attempt = 1
            else:
                if existing["state"] == "NEEDS_RECONCILIATION":
                    raise ValueError("RECONCILIATION_REQUIRED_BEFORE_RETRY")
                if existing["state"] != "RELEASED":
                    raise ValueError("RETRY_REQUIRES_RELEASED_RESERVATION")
                if existing["reservation_id"] != retry_reservation_id:
                    raise ValueError("RETRY_RESERVATION_MISMATCH")
                if existing["attempt"] >= existing["max_attempts"]:
                    raise ValueError("BUDGET_RETRY_LIMIT")
                attempt = existing["attempt"] + 1
            if budget["used_microunits"] + budget["reserved_microunits"] + amount > budget["hard_cap_microunits"]:
                raise ValueError("BUDGET_HARD_CAP_EXCEEDED")
            reservation_id = "rsv-" + uuid.uuid4().hex
            if existing is None:
                db.execute("INSERT INTO provider_budget_ops VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (op_key, plan["budget_id"], request_hash, amount,
                            "RESERVED", attempt, plan["max_attempts"], reservation_id,
                            None, None, now, now))
            else:
                db.execute("UPDATE provider_budget_ops SET state='RESERVED',attempt=?,reservation_id=?,actual_microunits=NULL,provider_receipt_sha256=NULL,updated=? WHERE op_key=?",
                           (attempt, reservation_id, now, op_key))
            db.execute("UPDATE provider_budgets SET reserved_microunits=reserved_microunits+?,updated=? WHERE id=?",
                       (amount, now, plan["budget_id"]))
            row = db.execute("SELECT * FROM provider_budget_ops WHERE op_key=?",
                             (op_key,)).fetchone()
            _event(db, row, now)
            return {**_operation_receipt(row), "reused": False}

        return _transaction(db, mutate)
    finally:
        db.close()


def _by_reservation(db, reservation_id):
    identifier(reservation_id)
    row = db.execute("SELECT * FROM provider_budget_ops WHERE reservation_id=?",
                     (reservation_id,)).fetchone()
    if row is None:
        raise ValueError("UNKNOWN_RESERVATION")
    return row


def settle_budget(store, reservation_id, actual_microunits, provider_receipt_sha256):
    """Settle a known provider result; an unknown effect must use reconciliation."""
    actual = _amount(actual_microunits, allow_zero=True)
    receipt_hash = _sha256(provider_receipt_sha256)
    db = connection(store)
    try:
        _schema(db)

        def mutate():
            now = time.time()
            row = _by_reservation(db, reservation_id)
            if row["state"] == "SETTLED":
                if row["actual_microunits"] != actual or row["provider_receipt_sha256"] != receipt_hash:
                    raise ValueError("SETTLEMENT_CONFLICT")
                return _operation_receipt(row)
            if row["state"] != "RESERVED":
                raise ValueError("RESERVED_STATE_REQUIRED")
            if actual > row["reserve_microunits"]:
                raise ValueError("ACTUAL_EXCEEDS_RESERVATION")
            db.execute("UPDATE provider_budgets SET reserved_microunits=reserved_microunits-?,used_microunits=used_microunits+?,updated=? WHERE id=?",
                       (row["reserve_microunits"], actual, now, row["budget_id"]))
            db.execute("UPDATE provider_budget_ops SET state='SETTLED',actual_microunits=?,provider_receipt_sha256=?,updated=? WHERE op_key=?",
                       (actual, receipt_hash, now, row["op_key"]))
            updated = db.execute("SELECT * FROM provider_budget_ops WHERE op_key=?",
                                 (row["op_key"],)).fetchone()
            _event(db, updated, now)
            return _operation_receipt(updated)

        return _transaction(db, mutate)
    finally:
        db.close()


def release_budget(store, reservation_id, *, request_not_sent):
    """Release only when the caller proves the provider request was not sent."""
    if request_not_sent is not True:
        raise ValueError("REQUEST_NOT_SENT_CONFIRMATION_REQUIRED")
    db = connection(store)
    try:
        _schema(db)

        def mutate():
            now = time.time()
            row = _by_reservation(db, reservation_id)
            if row["state"] == "RELEASED":
                return _operation_receipt(row)
            if row["state"] != "RESERVED":
                raise ValueError("RESERVED_STATE_REQUIRED")
            db.execute("UPDATE provider_budgets SET reserved_microunits=reserved_microunits-?,updated=? WHERE id=?",
                       (row["reserve_microunits"], now, row["budget_id"]))
            db.execute("UPDATE provider_budget_ops SET state='RELEASED',updated=? WHERE op_key=?",
                       (now, row["op_key"]))
            updated = db.execute("SELECT * FROM provider_budget_ops WHERE op_key=?",
                                 (row["op_key"],)).fetchone()
            _event(db, updated, now)
            return _operation_receipt(updated)

        return _transaction(db, mutate)
    finally:
        db.close()


def mark_budget_unknown(store, reservation_id):
    """Quarantine an uncertain request while keeping its full amount reserved."""
    db = connection(store)
    try:
        _schema(db)

        def mutate():
            now = time.time()
            row = _by_reservation(db, reservation_id)
            if row["state"] == "NEEDS_RECONCILIATION":
                return _operation_receipt(row)
            if row["state"] != "RESERVED":
                raise ValueError("RESERVED_STATE_REQUIRED")
            db.execute("UPDATE provider_budget_ops SET state='NEEDS_RECONCILIATION',updated=? WHERE op_key=?",
                       (now, row["op_key"]))
            updated = db.execute("SELECT * FROM provider_budget_ops WHERE op_key=?",
                                 (row["op_key"],)).fetchone()
            _event(db, updated, now)
            return _operation_receipt(updated)

        return _transaction(db, mutate)
    finally:
        db.close()


def reconcile_budget(store, reservation_id, actual_microunits, provider_receipt_sha256):
    """Explicitly settle an uncertain request after independent observation."""
    actual = _amount(actual_microunits, allow_zero=True)
    receipt_hash = _sha256(provider_receipt_sha256)
    db = connection(store)
    try:
        _schema(db)

        def mutate():
            now = time.time()
            row = _by_reservation(db, reservation_id)
            if row["state"] == "SETTLED":
                if row["actual_microunits"] != actual or row["provider_receipt_sha256"] != receipt_hash:
                    raise ValueError("RECONCILIATION_CONFLICT")
                return _operation_receipt(row)
            if row["state"] != "NEEDS_RECONCILIATION":
                raise ValueError("NEEDS_RECONCILIATION_STATE_REQUIRED")
            if actual > row["reserve_microunits"]:
                raise ValueError("ACTUAL_EXCEEDS_RESERVATION")
            db.execute("UPDATE provider_budgets SET reserved_microunits=reserved_microunits-?,used_microunits=used_microunits+?,updated=? WHERE id=?",
                       (row["reserve_microunits"], actual, now, row["budget_id"]))
            db.execute("UPDATE provider_budget_ops SET state='SETTLED',actual_microunits=?,provider_receipt_sha256=?,updated=? WHERE op_key=?",
                       (actual, receipt_hash, now, row["op_key"]))
            updated = db.execute("SELECT * FROM provider_budget_ops WHERE op_key=?",
                                 (row["op_key"],)).fetchone()
            _event(db, updated, now)
            return _operation_receipt(updated)

        return _transaction(db, mutate)
    finally:
        db.close()


def budget_status(store, budget_id):
    """Return accounting totals and the append-only transition history."""
    identifier(budget_id)
    db = connection(store)
    try:
        _schema(db)
        budget = db.execute("SELECT * FROM provider_budgets WHERE id=?", (budget_id,)).fetchone()
        if budget is None:
            raise ValueError("UNKNOWN_BUDGET")
        operations = db.execute("SELECT * FROM provider_budget_ops WHERE budget_id=? ORDER BY created,op_key",
                                (budget_id,)).fetchall()
        events = db.execute("SELECT e.* FROM provider_budget_events e JOIN provider_budget_ops o ON o.op_key=e.op_key WHERE o.budget_id=? ORDER BY e.seq",
                            (budget_id,)).fetchall()
        return {
            "schema": "occ.provider-budget-status.v1",
            "budget_id": budget_id,
            "currency": budget["currency"],
            "hard_cap_microunits": budget["hard_cap_microunits"],
            "reserved_microunits": budget["reserved_microunits"],
            "used_microunits": budget["used_microunits"],
            "remaining_microunits": budget["hard_cap_microunits"] - budget["reserved_microunits"] - budget["used_microunits"],
            "operations": [_operation_receipt(row) for row in operations],
            "events": [{key: row[key] for key in row.keys() if key not in {"seq", "observed"}}
                       for row in events],
            "provider_calls_performed_by_budget_module": 0,
            "action_authority": False,
        }
    finally:
        db.close()
