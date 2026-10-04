"""Race trusted read/draft coroutines, then use an independent verifier.

Effect labels are assertions by trusted demo code, NOT a security sandbox.
Production needs separate OS workers, scoped credentials, network policy,
resource leases and verified termination. Cancellation here is cooperative.
"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable

class Effect(str, Enum):
    READ = "read"
    PREPARE = "isolated_prepare"
    EXTERNAL_WRITE = "external_write"

@dataclass(frozen=True)
class Candidate:
    route_id: str
    snapshot_revision: int
    payload: dict
    source_refs: tuple[str, ...] = ()

@dataclass(frozen=True)
class Route:
    route_id: str
    failure_domain: str
    effect: Effect
    run: Callable[[], Awaitable[Candidate]]

@dataclass
class RaceResult:
    winner: Candidate | None
    events: list[dict] = field(default_factory=list)
    elapsed_ms: float = 0

Verifier = Callable[[Candidate], Awaitable[tuple[bool, str]]]

def diverse_routes(routes: list[Route]) -> list[Route]:
    """Keep first route per declared domain. Domains need empirical validation."""
    seen, result = set(), []
    for route in routes:
        if not route.route_id or not route.failure_domain:
            raise ValueError("route identity and failure domain are required")
        if route.failure_domain not in seen:
            seen.add(route.failure_domain)
            result.append(route)
    return result

async def race_to_verified(routes: list[Route], verifier: Verifier, *,
                           max_parallel: int = 2, hedge_delay: float = 0.02,
                           deadline: float = 2.0,
                           cancellation_grace: float = 0.1) -> RaceResult:
    if max_parallel < 1 or deadline <= 0 or hedge_delay < 0 or cancellation_grace < 0:
        raise ValueError("invalid concurrency or timing budget")
    # Validate ALL supplied routes, including duplicates, before invoking any.
    if any(r.effect not in (Effect.READ, Effect.PREPARE) for r in routes):
        raise PermissionError("external writes may not enter the speculative race")
    if len({r.route_id for r in routes}) != len(routes):
        raise ValueError("duplicate route_id")
    selected = diverse_routes(routes)
    result = RaceResult(None)
    started_at = time.monotonic()
    semaphore = asyncio.Semaphore(max_parallel)

    def event(route: Route, state: str, detail: str = "") -> None:
        result.events.append({"route_id": route.route_id, "failure_domain": route.failure_domain,
                              "state": state, "detail": detail,
                              "elapsed_ms": round((time.monotonic()-started_at)*1000, 3)})

    async def worker(route: Route, position: int) -> Candidate | None:
        try:
            # Delayed hedging: later candidates are not necessarily started.
            await asyncio.sleep(position * hedge_delay)
            async with semaphore:
                event(route, "STARTED")
                candidate = await route.run()
                if candidate.route_id != route.route_id:
                    event(route, "REJECTED", "route identity mismatch")
                    return None
                ok, reason = await verifier(candidate)
                event(route, "VERIFIED" if ok else "REJECTED", reason)
                return candidate if ok else None
        except asyncio.CancelledError:
            event(route, "CANCELLED")
            raise
        except Exception as exc:
            event(route, "ERROR", type(exc).__name__ + ": " + str(exc))
            return None

    tasks = [asyncio.create_task(worker(r, i)) for i, r in enumerate(selected)]
    pending = set(tasks)
    try:
        while pending and result.winner is None:
            remaining = deadline - (time.monotonic()-started_at)
            if remaining <= 0:
                break
            done, pending = await asyncio.wait(pending, timeout=remaining,
                                                return_when=asyncio.FIRST_COMPLETED)
            if not done:
                break
            # Deterministic tie-break only for completions in the same wait batch.
            for task in tasks:
                if task in done:
                    value = task.result()
                    if value is not None:
                        result.winner = value
                        break
    finally:
        leftovers = {t for t in tasks if not t.done()}
        for task in leftovers:
            task.cancel()
        if leftovers:
            _, unsettled = await asyncio.wait(leftovers, timeout=cancellation_grace)
            if unsettled:
                result.winner = None
                raise RuntimeError("cancellation unconfirmed; do not commit; production must terminate workers")
        # Retrieve exceptions/cancellations to avoid orphaned task warnings.
        await asyncio.gather(*tasks, return_exceptions=True)
        result.elapsed_ms = round((time.monotonic()-started_at)*1000, 3)
    return result
