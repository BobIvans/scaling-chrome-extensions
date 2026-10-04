"""F-15 first slice: bounded admission into the EXISTING durable queue.

One invocation admits at most one registered sync template. No daemon, worker,
process, API call or trading action is started. Stop prevents future admissions;
an admission already accepted by the control transaction can still finish.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import time

SCHEMA = "occ.bounded-schedule.v1"
FIELDS = {"schema", "schedule_id", "enabled", "template", "start_at_utc",
          "interval_seconds", "occurrences"}
NAME = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")
UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MAX_BYTES = 16_000


def validate_schedule(value):
    """Return a validated copy; reject coercions and unrecognized permissions."""
    if isinstance(value, dict) and value.get('schema') == 'occ.durable-schedule.v2':
        from durable_schedule import validate
        return validate(value)
    if not isinstance(value, dict) or set(value) != FIELDS or value.get("schema") != SCHEMA:
        raise ValueError("SCHEDULE_SCHEMA")
    for key in ("schedule_id", "template"):
        if not isinstance(value[key], str) or not NAME.fullmatch(value[key]):
            raise ValueError("SCHEDULE_IDENTIFIER")
    if type(value["enabled"]) is not bool:
        raise ValueError("SCHEDULE_ENABLED_BOOLEAN")
    interval, count = value["interval_seconds"], value["occurrences"]
    if type(interval) is not int or not 3600 <= interval <= 86400:
        raise ValueError("SCHEDULE_INTERVAL")
    if type(count) is not int or not 1 <= count <= 24 or count * interval > 86400:
        raise ValueError("SCHEDULE_WINDOW_LIMIT")
    raw = value["start_at_utc"]
    if not isinstance(raw, str) or not UTC_TIMESTAMP.fullmatch(raw):
        raise ValueError("SCHEDULE_UTC_REQUIRED")
    try:
        datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError("SCHEDULE_UTC_REQUIRED") from exc
    return dict(value)


def due_slot(schedule, now):
    """UTC slots, no missed-slot catch-up; time does not authorize execution."""
    schedule = validate_schedule(schedule)
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError("SCHEDULE_CLOCK")
    if not schedule["enabled"]:
        return {"state": "DISABLED"}
    start = datetime.strptime(schedule["start_at_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    elapsed = now - start
    if elapsed < 0:
        return {"state": "NOT_DUE"}
    slot = int(elapsed // schedule["interval_seconds"])
    if slot >= schedule["occurrences"]:
        return {"state": "EXPIRED"}
    return {"state": "DUE", "slot": slot,
            "task_key": f"schedule:{schedule['schedule_id']}:{slot}"}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _control(store, schedule, profile, policy, connect, *, stop=False):
    """Only control metadata is new; jobs/events remain canonical core-owned."""
    definition = dict(schedule)
    definition.pop("enabled")  # temporary disable does not change job identity
    binding = _hash({"schedule": definition, "profile": profile, "policy": policy})
    db = connect(store)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS bounded_schedule_controls ("
                   "id TEXT PRIMARY KEY, binding TEXT NOT NULL, stopped INTEGER NOT NULL)")
        db.commit()
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT binding, stopped FROM bounded_schedule_controls WHERE id=?",
                         (schedule["schedule_id"],)).fetchone()
        if row is not None and row[0] != binding:
            raise ValueError("SCHEDULE_BINDING_CHANGED")
        if row is None:
            db.execute("INSERT INTO bounded_schedule_controls VALUES (?,?,?)",
                       (schedule["schedule_id"], binding, int(stop)))
            stopped = stop
        else:
            stopped = bool(row[1]) or stop
            if stop:
                db.execute("UPDATE bounded_schedule_controls SET stopped=1 WHERE id=?",
                           (schedule["schedule_id"],))
        db.commit()
        return bool(stopped)
    finally:
        db.close()


def _runtime():
    # Resolve only the installed sibling modules, including under python -I.
    root = str(Path(__file__).resolve().parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    from automation_core import connection, enqueue
    from native_adapter import operator_profile
    return operator_profile, connection, enqueue


def tick(schedule, profile_path, *, apply=False, stop=False, now=None):
    if isinstance(schedule, dict) and schedule.get('schema') == 'occ.durable-schedule.v2':
        from durable_schedule import tick as durable_tick
        return durable_tick(schedule, profile_path, apply=apply, stop=stop, now=now)
    schedule = validate_schedule(schedule)
    if type(apply) is not bool or type(stop) is not bool or (apply and stop):
        raise ValueError("SCHEDULE_MODE")
    profile_path = Path(profile_path)
    if not profile_path.is_absolute():
        raise ValueError("SCHEDULE_ABSOLUTE_PROFILE_REQUIRED")
    point = due_slot(schedule, time.time() if now is None else now)
    if not stop and point["state"] != "DUE":
        return {**point, "enqueued": False}
    load_profile, connect, enqueue_job = _runtime()
    profile, policy = load_profile(profile_path)
    payload = profile["templates"].get(schedule["template"])
    if not isinstance(payload, dict) or payload.get("kind") != "sync":
        raise ValueError("SCHEDULE_REGISTERED_SYNC_ONLY")
    store = Path(profile["store"])
    if not apply and not stop:
        return {**point, "state": "PREVIEW", "enqueued": False,
                "template": schedule["template"], "stop_state_checked": False}
    stopped = _control(store, schedule, profile, policy, connect, stop=stop)
    if stop or stopped:
        return {"state": "STOPPED_FUTURE_ADMISSIONS", "enqueued": False,
                "inflight_admissions_may_complete": True, "cancels_existing_jobs": False}
    # Enqueue remains the existing owner: transactional task-key/content binding,
    # queue limit, replay, job events, cancellation and worker lease are unchanged.
    job = enqueue_job(store, policy, point["task_key"], payload)
    return {**point, "state": "ADMITTED", "enqueued": not job["reused"],
            "job": job, "worker_started": False}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("SCHEDULE_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def load_schedule(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("SCHEDULE_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("SCHEDULE_INPUT_LIMIT")
    return validate_schedule(json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--stop", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = tick(load_schedule(args.schedule), args.profile,
                      apply=args.apply, stop=args.stop)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error) as exc:
        code = str(exc)
        if not re.fullmatch(r"[A-Z_]{1,100}", code):
            code = "SCHEDULE_FAILED"
        print(json.dumps({"ok": False, "error": code}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
