"""Offline resource-interference model; NOT an OS permission or path resolver."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class TaskFootprint:
    task_id: str
    reads: frozenset[str] = frozenset()
    writes: frozenset[str] = frozenset()
    foreground: str | None = None

    def validate(self) -> None:
        if not self.task_id or any(not r for r in self.reads | self.writes):
            raise ValueError('task and resource identities required')


def can_overlap(a: TaskFootprint, b: TaskFootprint) -> tuple[bool, str]:
    """Resources MUST already be canonical and expanded for parent/child aliases.

    Immutable event keys and separate worktrees use distinct resources. A shared
    external account/object or foreground input requires the same resource key.
    A real app must bind/check these scopes outside model output and fence writes.
    """
    a.validate(); b.validate()
    if a.task_id == b.task_id:
        return False, 'SAME_OPERATION_REPLAY'
    if a.foreground and a.foreground == b.foreground:
        return False, 'SHARED_FOREGROUND'
    conflicts = (a.writes & (b.reads | b.writes)) | (b.writes & a.reads)
    if conflicts:
        return False, 'RESOURCE_CONFLICT:' + ','.join(sorted(conflicts))
    return True, 'DISJOINT_OR_READ_ONLY'


def independent_batches(tasks: list[TaskFootprint], max_parallel: int) -> list[list[str]]:
    """Greedy order-preserving schedule proposal. Does not execute anything."""
    if max_parallel < 1 or len({t.task_id for t in tasks}) != len(tasks):
        raise ValueError('positive capacity and unique tasks required')
    batches: list[list[TaskFootprint]] = []
    for task in tasks:
        task.validate()
        for batch in batches:
            if len(batch) < max_parallel and all(can_overlap(task, other)[0] for other in batch):
                batch.append(task)
                break
        else:
            batches.append([task])
    return [[t.task_id for t in batch] for batch in batches]
