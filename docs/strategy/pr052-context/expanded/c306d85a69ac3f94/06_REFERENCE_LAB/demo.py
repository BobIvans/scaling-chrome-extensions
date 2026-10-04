"""Run synthetic, network-free race + context + single SQLite commit example."""
from __future__ import annotations
import argparse
import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from agentos_lab.context import Vault
from agentos_lab.ledger import CommitLedger
from agentos_lab.race import Candidate, Effect, Route, race_to_verified

async def example(root: Path) -> dict:
    vault = Vault(root / "vault")
    sid = vault.put(
        "Синтетический пример: qualification блокируется без подтверждённых зависимостей.\n".encode(),
        "fixture://studious/demo-note", {"privacy": "private", "evidence_state": "SYNTHETIC"},
        chunk_bytes=256)
    ref = vault.records(sid)[0]["ref"]
    pack = vault.compile_pack([sid], "qualification", budget_bytes=2048, required_refs=(ref,))
    ledger = CommitLedger(root / "commit.sqlite3")
    ledger.seed("handoff/demo", {"state": "empty"})
    revision, _ = ledger.read("handoff/demo")

    async def stale():
        await asyncio.sleep(0.002)
        return Candidate("cached_stale", revision + 1, {"answer": "stale"}, (ref,))

    async def exact():
        await asyncio.sleep(0.006)
        return Candidate("source_bound", revision,
                         {"kind": "handoff", "pack": pack}, (ref,))

    async def expensive():
        await asyncio.sleep(0.2)
        return Candidate("slow_alternative", revision, {"answer": "unused"}, (ref,))

    async def verifier(candidate):
        if candidate.snapshot_revision != revision:
            return False, "STALE_SNAPSHOT"
        if candidate.payload.get("kind") != "handoff":
            return False, "WRONG_ARTIFACT_TYPE"
        if ref not in candidate.source_refs:
            return False, "MISSING_SOURCE"
        if candidate.payload["pack"]["status"] != "READY_FOR_REVIEW":
            return False, "INCOMPLETE_CONTEXT"
        vault.read(sid)  # Re-read original bytes instead of accepting model claim.
        return True, "BOUND_SOURCE_AND_CONTRACT"

    race = await race_to_verified([
        Route("cached_stale", "cache", Effect.READ, stale),
        Route("source_bound", "source_reader", Effect.READ, exact),
        Route("slow_alternative", "alternative_reader", Effect.READ, expensive),
    ], verifier, hedge_delay=0.005, max_parallel=2)
    if race.winner is None:
        raise RuntimeError("no candidate passed")
    receipt = ledger.commit("demo-intent-1", "handoff/demo", revision,
                            race.winner.payload, verified=True)
    replay = ledger.commit("demo-intent-1", "handoff/demo", revision,
                           race.winner.payload, verified=True)
    return {"evidence_state": "SYNTHETIC_OFFLINE_DEMO", "winner": race.winner.route_id,
            "events": race.events, "elapsed_ms_not_hardware_benchmark": race.elapsed_ms,
            "receipt": receipt, "replay_is_identical": replay == receipt,
            "commit_count": ledger.operation_count(), "external_actions": 0,
            "real_repository_tests_run": False, "desktop_tested": False,
            "voice_or_laya_or_api_tested": False, "context_pack": pack}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("demo-output"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agentos-lab-") as tmp:
        result = asyncio.run(example(Path(tmp)))
        shutil.copy2(Path(tmp) / "commit.sqlite3", args.output / "demo-ledger.sqlite3")
    (args.output / "demo-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("events", "context_pack")}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
