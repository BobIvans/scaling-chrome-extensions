"""Bounded F-15 supervisor for the existing schedule admission and queue.

The supervisor has a finite duration/tick count and one SQLite lease. It never
starts a worker, model, browser or arbitrary command. An expired lease requires
explicit reconciliation after the operator verifies the old process stopped.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import secrets
import signal
import sqlite3
import sys
import threading
import time

import schedule_tick

SCHEMA = "occ.bounded-supervisor.v1"
FIELDS = {"schema", "supervisor_id", "enabled", "poll_seconds",
          "max_seconds", "max_ticks", "lease_seconds"}
NAME = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")
MAX_BYTES = 16_000
TERMINAL = {"DISABLED", "EXPIRED", "STOPPED_FUTURE_ADMISSIONS"}


def validate_config(value):
    if not isinstance(value, dict) or set(value) != FIELDS or value.get("schema") != SCHEMA:
        raise ValueError("SUPERVISOR_SCHEMA")
    if not isinstance(value["supervisor_id"], str) or not NAME.fullmatch(value["supervisor_id"]):
        raise ValueError("SUPERVISOR_IDENTIFIER")
    if type(value["enabled"]) is not bool:
        raise ValueError("SUPERVISOR_ENABLED_BOOLEAN")
    limits = (("poll_seconds", 10, 3600), ("max_seconds", 60, 86400),
              ("max_ticks", 1, 8640), ("lease_seconds", 30, 7200))
    for field, low, high in limits:
        if type(value[field]) is not int or not low <= value[field] <= high:
            raise ValueError("SUPERVISOR_LIMIT")
    if value["lease_seconds"] < min(7200, value["poll_seconds"] * 2):
        raise ValueError("SUPERVISOR_LEASE_TOO_SHORT")
    return dict(value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("SUPERVISOR_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load_config(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("SUPERVISOR_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("SUPERVISOR_INPUT_LIMIT")
    return validate_config(json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object))


def _dependencies():
    load_profile, connect, _ = schedule_tick._runtime()
    return load_profile, connect, schedule_tick.tick


def _table(db):
    db.execute("CREATE TABLE IF NOT EXISTS bounded_schedule_supervisors ("
               "schedule_id TEXT PRIMARY KEY, supervisor_id TEXT NOT NULL, "
               "token TEXT NOT NULL, lease_until REAL NOT NULL, updated REAL NOT NULL)")
    db.commit()


def _acquire(store, connect, schedule_id, supervisor_id, token, now, lease_seconds):
    db = connect(store)
    try:
        _table(db)
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT supervisor_id, lease_until FROM bounded_schedule_supervisors "
                         "WHERE schedule_id=?", (schedule_id,)).fetchone()
        if row is not None:
            db.rollback()
            if row[1] >= now:
                raise ValueError("SUPERVISOR_ALREADY_ACTIVE")
            raise ValueError("SUPERVISOR_NEEDS_RECONCILIATION")
        db.execute("INSERT INTO bounded_schedule_supervisors VALUES (?,?,?,?,?)",
                   (schedule_id, supervisor_id, token, now + lease_seconds, now))
        db.commit()
    finally:
        db.close()


def _heartbeat(store, connect, schedule_id, token, now, lease_seconds):
    db = connect(store)
    try:
        db.execute("BEGIN IMMEDIATE")
        changed = db.execute("UPDATE bounded_schedule_supervisors SET lease_until=?,updated=? "
                             "WHERE schedule_id=? AND token=? AND lease_until>=?",
                             (now + lease_seconds, now, schedule_id, token, now)).rowcount
        if changed != 1:
            db.rollback()
            raise ValueError("SUPERVISOR_LEASE_LOST")
        db.commit()
    finally:
        db.close()


def _release(store, connect, schedule_id, token):
    db = connect(store)
    try:
        db.execute("BEGIN IMMEDIATE")
        changed = db.execute("DELETE FROM bounded_schedule_supervisors "
                             "WHERE schedule_id=? AND token=?", (schedule_id, token)).rowcount
        if changed != 1:
            db.rollback()
            raise ValueError("SUPERVISOR_LEASE_LOST")
        db.commit()
    finally:
        db.close()


def reconcile_stopped(store, connect, schedule_id, now):
    """Clear only an expired lease after external process-stop verification."""
    db = connect(store)
    try:
        _table(db)
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT lease_until FROM bounded_schedule_supervisors "
                         "WHERE schedule_id=?", (schedule_id,)).fetchone()
        if row is None:
            db.rollback()
            return {"state": "NO_SUPERVISOR_LEASE", "cleared": False}
        if row[0] >= now:
            db.rollback()
            raise ValueError("SUPERVISOR_STILL_ACTIVE")
        db.execute("DELETE FROM bounded_schedule_supervisors WHERE schedule_id=?", (schedule_id,))
        db.commit()
        return {"state": "EXPIRED_LEASE_RECONCILED", "cleared": True}
    finally:
        db.close()


@dataclass
class Runtime:
    monotonic: object = time.monotonic
    wall: object = time.time
    wait: object = None

    def pause(self, seconds):
        if self.wait is not None:
            return self.wait(seconds)
        time.sleep(seconds)
        return False


def supervise(config, schedule, profile_path, *, apply=False,
              reconcile=False, runtime=None):
    config, schedule = validate_config(config), schedule_tick.validate_schedule(schedule)
    if type(apply) is not bool or type(reconcile) is not bool or (apply and reconcile):
        raise ValueError("SUPERVISOR_MODE")
    profile_path = Path(profile_path)
    if not profile_path.is_absolute():
        raise ValueError("SUPERVISOR_ABSOLUTE_PROFILE_REQUIRED")
    load_profile, connect, tick = _dependencies()
    profile, _ = load_profile(profile_path)
    store = Path(profile["store"])
    run = runtime or Runtime()
    now = run.wall()
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError("SUPERVISOR_CLOCK")
    if reconcile:
        return reconcile_stopped(store, connect, schedule["schedule_id"], now)
    if not apply:
        preview = tick(schedule, profile_path, now=now)
        return {"state": "PREVIEW", "enabled": config["enabled"], "ticks": 0,
                "schedule": preview, "worker_started": False}
    if not config["enabled"]:
        return {"state": "SUPERVISOR_DISABLED", "ticks": 0,
                "worker_started": False}
    token = secrets.token_hex(16)
    started, deadline = run.monotonic(), None
    if type(started) not in (int, float) or not math.isfinite(started):
        raise ValueError("SUPERVISOR_CLOCK")
    deadline = started + config["max_seconds"]
    _acquire(store, connect, schedule["schedule_id"], config["supervisor_id"],
             token, now, config["lease_seconds"])
    ticks, last, clean, last_wall = 0, None, False, now
    try:
        while ticks < config["max_ticks"]:
            current = run.monotonic()
            if type(current) not in (int, float) or not math.isfinite(current) or current < started:
                raise ValueError("SUPERVISOR_CLOCK")
            if current >= deadline:
                clean = True
                return {"state": "MAX_DURATION_REACHED", "ticks": ticks,
                        "last": last, "worker_started": False}
            now = run.wall()
            if type(now) not in (int, float) or not math.isfinite(now) or now < last_wall:
                raise ValueError("SUPERVISOR_CLOCK")
            last_wall = now
            _heartbeat(store, connect, schedule["schedule_id"], token, now,
                       config["lease_seconds"])
            last = tick(schedule, profile_path, apply=True, now=now)
            ticks += 1
            if last["state"] in TERMINAL:
                clean = True
                return {"state": last["state"], "ticks": ticks, "last": last,
                        "worker_started": False}
            if ticks >= config["max_ticks"]:
                clean = True
                return {"state": "MAX_TICKS_REACHED", "ticks": ticks,
                        "last": last, "worker_started": False}
            after = run.monotonic()
            if type(after) not in (int, float) or not math.isfinite(after) or after < current:
                raise ValueError("SUPERVISOR_CLOCK")
            remaining = deadline - after
            if remaining <= 0:
                clean = True
                return {"state": "MAX_DURATION_REACHED", "ticks": ticks,
                        "last": last, "worker_started": False}
            if run.pause(min(config["poll_seconds"], remaining)):
                clean = True
                return {"state": "INTERRUPTED", "ticks": ticks, "last": last,
                        "worker_started": False,
                        "future_admissions_stopped": False}
        raise AssertionError("bounded loop invariant")
    finally:
        # An exception or lease loss is an unknown outcome. Retain the lease so
        # a future run cannot start until explicit --reconcile-stopped.
        if clean:
            _release(store, connect, schedule["schedule_id"], token)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervisor", required=True, type=Path)
    parser.add_argument("--schedule", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--reconcile-stopped", action="store_true")
    args = parser.parse_args(argv)
    interrupted = threading.Event()
    if args.apply:
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, lambda *_: interrupted.set())
    try:
        result = supervise(load_config(args.supervisor),
                           schedule_tick.load_schedule(args.schedule), args.profile,
                           apply=args.apply, reconcile=args.reconcile_stopped,
                           runtime=Runtime(wait=interrupted.wait))
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False,
                         allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error) as exc:
        code = str(exc)
        if not re.fullmatch(r"[A-Z_]{1,100}", code):
            code = "SUPERVISOR_FAILED"
        print(json.dumps({"ok": False, "error": code}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
