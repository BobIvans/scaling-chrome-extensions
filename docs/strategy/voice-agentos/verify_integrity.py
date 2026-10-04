"""Verify every supplied strategy byte and complete requirement ownership."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent


def verify():
    manifest = json.loads((ROOT / "verification/SOURCE_INTEGRITY.json").read_text(encoding="utf-8"))
    failures = []
    seen = set()
    for entry in manifest["entries"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or entry["path"] in seen:
            failures.append({"path": entry["path"], "reason": "INVALID_OR_DUPLICATE_PATH"})
            continue
        seen.add(entry["path"])
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            failures.append({"path": entry["path"], "reason": "MISSING_OR_NONREGULAR"})
            continue
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while raw := source.read(1024 * 1024):
                size += len(raw)
                digest.update(raw)
        if size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
            failures.append({"path": entry["path"], "reason": "BYTE_MISMATCH"})
    if len(seen) != manifest["count"]:
        failures.append({"reason": "SOURCE_COUNT_MISMATCH"})
    catalogs = ROOT / "roadmap/source_master/strategy_v5"
    specs = [
        ("catalogs/ALL_TASKS_V5.json", "tasks", "task_id", 160, "source_task_ids"),
        ("catalogs/FEATURE_DEFINITION_AUDIT.json", "features", "feature_id", 164, "feature_ids"),
        ("goals/GOAL_REGISTER.json", "goals", "goal_id", 28, "goal_ids"),
        ("audit/DECISION_REGISTER.json", "decisions", "id", 24, "decision_ids"),
    ]
    owners = json.loads((ROOT / "handoff/REQUIREMENT_OWNERS.json").read_text(encoding="utf-8"))["packages"]
    counts = {}
    for file, key, id_key, expected, owner_key in specs:
        rows = json.loads((catalogs / file).read_text(encoding="utf-8"))[key]
        ids = {row[id_key] for row in rows}
        assigned = {identifier for package in owners for identifier in package[owner_key]}
        counts[key] = len(ids)
        if len(rows) != expected or len(ids) != expected or ids != assigned:
            failures.append({"reason": "REQUIREMENT_COVERAGE_MISMATCH", "catalog": file,
                             "missing": sorted(ids - assigned), "unknown": sorted(assigned - ids)})
    result = {"ok": not failures, "source_files_verified": len(seen),
              "source_bytes": manifest["source_bytes"], "catalog_counts": counts,
              "runtime_qualification": "NOT_INFERRED_FROM_ARCHIVE_INTEGRITY",
              "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(verify())
