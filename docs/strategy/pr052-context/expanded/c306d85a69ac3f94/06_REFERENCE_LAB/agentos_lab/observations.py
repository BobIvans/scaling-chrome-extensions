"""Offline multi-producer observation journal, not a desktop recording service.

Only synthetic, in-memory payloads are used by the shipped tests/demo. An append
transaction keeps immutable observations and deduplicated raw bytes together.
Collectors are trusted cooperative Python code: this is not an OS sandbox,
encryption layer, permission boundary, ASR, or an authenticity verifier.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import AsyncIterator, Callable, Iterator

from .ledger import canonical, digest, Conflict


@dataclass(frozen=True)
class Observation:
    session: str
    producer: str
    sequence: int
    source_uri: str
    source_revision: str
    lineage_root: str
    kind: str
    observed_ns: int
    payload: bytes
    partial: bool = False

    def header(self) -> dict:
        data = asdict(self)
        del data['payload']
        return data

    def validate(self) -> None:
        if any(not isinstance(v, str) or not v.strip() for v in
               (self.session, self.producer, self.source_uri, self.source_revision,
                self.lineage_root, self.kind)):
            raise ValueError('nonempty identities, source revision and lineage required')
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError('sequence must be a nonnegative integer')
        if type(self.observed_ns) is not int or self.observed_ns < 0:
            raise ValueError('timestamp must be a nonnegative integer')
        if not isinstance(self.payload, bytes) or type(self.partial) is not bool:
            raise TypeError('payload must be bytes and partial must be bool')


class ObservationJournal:
    """Many producers, short serialized DB transactions, no global recorder lock.

    Event identity = (session, producer, sequence). Replaying an identical event
    is idempotent; reusing its identity with different data is an explicit error.
    Two sources with the same bytes remain two observations, not two independent
    confirmations. Large media streaming and retention are NOT implemented here.
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript('''
                CREATE TABLE IF NOT EXISTS raw_objects (
                    sha TEXT PRIMARY KEY, payload BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS observations (
                    session TEXT NOT NULL, producer TEXT NOT NULL, seq INTEGER NOT NULL,
                    fingerprint TEXT NOT NULL, header TEXT NOT NULL, sha TEXT NOT NULL,
                    PRIMARY KEY (session,producer,seq),
                    FOREIGN KEY(sha) REFERENCES raw_objects(sha)
                );
            ''')

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=15)
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:
                yield con
        finally:
            con.close()

    def append(self, observation: Observation) -> dict:
        observation.validate()
        header = observation.header()
        sha = hashlib.sha256(observation.payload).hexdigest()
        fingerprint = digest({'header': header, 'sha': sha})
        key = (observation.session, observation.producer, observation.sequence)
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            previous = con.execute(
                'SELECT fingerprint FROM observations WHERE session=? AND producer=? AND seq=?', key
            ).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise Conflict('immutable observation identity reused with changed content')
                # A replay must not mask damage to the raw object.
                raw = con.execute('SELECT payload FROM raw_objects WHERE sha=?', (sha,)).fetchone()
                if not raw or hashlib.sha256(raw[0]).hexdigest() != sha:
                    raise ValueError('raw object missing or corrupt')
                return {'fingerprint': fingerprint, 'inserted': False, 'sha256': sha}
            raw = con.execute('SELECT payload FROM raw_objects WHERE sha=?', (sha,)).fetchone()
            if raw and raw[0] != observation.payload:
                raise ValueError('object integrity failure')
            con.execute('INSERT OR IGNORE INTO raw_objects VALUES (?,?)', (sha, observation.payload))
            con.execute('INSERT INTO observations VALUES (?,?,?,?,?,?)',
                        (*key, fingerprint, canonical(header), sha))
        return {'fingerprint': fingerprint, 'inserted': True, 'sha256': sha}

    def read(self, session: str) -> list[dict]:
        with self.connect() as con:
            records = con.execute(
                '''SELECT o.fingerprint,o.header,o.sha,r.payload FROM observations o
                   LEFT JOIN raw_objects r ON r.sha=o.sha WHERE o.session=?''', (session,)
            ).fetchall()
        out = []
        for fingerprint, raw_header, sha, payload in records:
            if payload is None or hashlib.sha256(payload).hexdigest() != sha:
                raise ValueError('raw object missing or corrupt')
            header = json.loads(raw_header)
            if digest({'header': header, 'sha': sha}) != fingerprint:
                raise ValueError('observation metadata integrity failure')
            out.append({**header, 'sha256': sha, 'fingerprint': fingerprint, 'payload': payload})
        # Ordering is a display convention, NOT proof of causal order across sources.
        return sorted(out, key=lambda e: (e['observed_ns'], e['producer'], e['sequence']))

    def object_count(self) -> int:
        with self.connect() as con:
            return con.execute('SELECT COUNT(*) FROM raw_objects').fetchone()[0]

    def source_coverage(self, session: str, expected_producers: set[str]) -> dict:
        rows = self.read(session)
        found = {row['producer'] for row in rows}
        missing = sorted(expected_producers - found)
        partial = sorted({row['producer'] for row in rows if row['partial']})
        return {'present': sorted(found), 'missing': missing, 'partial': partial,
                'channel_presence_complete': not missing,
                'full_source_history_proven': False,
                'note': 'Channel presence is not semantic completeness or authenticity.'}


@dataclass(frozen=True)
class Producer:
    name: str
    stream: Callable[[], AsyncIterator[Observation]]


async def collect_complementary(journal: ObservationJournal, session: str,
                                producers: list[Producer], *, timeout: float = 5.0,
                                max_pending: int = 16, cancellation_grace: float = .2) -> dict:
    """Collect ALL channels until completion/deadline; never cancel after first data.

    Bounded queue applies backpressure without intentionally dropping items.
    A timeout reports an interrupted producer; it does not claim complete history.
    Cooperative tasks only. The caller is responsible for genuine capture consent.
    """
    if timeout <= 0 or max_pending < 1 or cancellation_grace < 0:
        raise ValueError('invalid collection budget')
    if len({p.name for p in producers}) != len(producers) or any(not p.name for p in producers):
        raise ValueError('producer names must be nonempty and unique')
    queue: asyncio.Queue[Observation | None] = asyncio.Queue(maxsize=max_pending)
    status = {p.name: 'PENDING' for p in producers}
    counts = {p.name: 0 for p in producers}
    errors: dict[str, str] = {}

    async def feed(producer: Producer) -> None:
        status[producer.name] = 'RUNNING'
        try:
            async for item in producer.stream():
                item.validate()
                if item.session != session or item.producer != producer.name:
                    raise ValueError('producer/session binding mismatch')
                await queue.put(item)
            status[producer.name] = 'STREAM_EXHAUSTED'
        except asyncio.CancelledError:
            status[producer.name] = 'INTERRUPTED'
            raise
        except Exception as exc:
            status[producer.name] = 'ERROR'
            errors[producer.name] = f'{type(exc).__name__}: {exc}'

    async def consume() -> None:
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                # A toy local transaction; production should offload disk IO from
                # the speech event loop to a registered writer worker.
                receipt = journal.append(item)
                counts[item.producer] += int(receipt['inserted'])
            finally:
                queue.task_done()

    consumer = asyncio.create_task(consume())
    tasks = [asyncio.create_task(feed(p)) for p in producers]
    try:
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=timeout)
            for task in pending:
                task.cancel()
            if pending:
                _, unsettled = await asyncio.wait(pending, timeout=cancellation_grace)
                if unsettled:
                    raise RuntimeError('producer stop unconfirmed; terminate real worker before reuse')
            await asyncio.gather(*tasks, return_exceptions=True)
        if consumer.done():
            consumer.result()
        # Drain with explicit consumer-error propagation, not an unbounded join.
        join = asyncio.create_task(queue.join())
        try:
            done, _ = await asyncio.wait({join, consumer}, return_when=asyncio.FIRST_COMPLETED)
            if consumer in done:
                consumer.result()
            await join
        finally:
            if not join.done():
                join.cancel()
                await asyncio.gather(join, return_exceptions=True)
        await queue.put(None)
        await consumer
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if not consumer.done():
            consumer.cancel()
        # Trusted cooperative tasks only; external process cancellation needs fencing.
        await asyncio.gather(consumer, return_exceptions=True)
    return {'strategy': 'complementary_union', 'statuses': status, 'new_events': counts,
            'errors': errors, 'coverage': journal.source_coverage(session, set(status)),
            'external_actions': 0}


def fuse_claims(claims: list[dict]) -> list[dict]:
    """Group claims but preserve contradictions and lineage. No majority truth rule.

    The key includes source_revision so different snapshots are never reconciled
    into one timeless fact. Declared lineage is not authenticated by this function.
    """
    grouped: dict[tuple[str, str, str], dict[str, list[dict]]] = {}
    required = {'subject', 'predicate', 'value', 'source_revision', 'lineage_root', 'source_ref'}
    for claim in claims:
        if not required <= claim.keys():
            raise ValueError('claim requires value, revision, lineage and source reference')
        if not all(isinstance(claim[k], str) and claim[k] for k in required - {'value'}):
            raise ValueError('claim identity fields must be nonempty strings')
        key = (claim['subject'], claim['predicate'], claim['source_revision'])
        grouped.setdefault(key, {}).setdefault(canonical(claim['value']), []).append(claim)
    results = []
    for (subject, predicate, revision), variants in sorted(grouped.items()):
        values = []
        for value_json, group in sorted(variants.items()):
            values.append({'value': json.loads(value_json),
                           'source_refs': sorted({g['source_ref'] for g in group}),
                           'declared_lineage_count': len({g['lineage_root'] for g in group}),
                           'independence_proven': False})
        results.append({'subject': subject, 'predicate': predicate, 'source_revision': revision,
                        'values': values, 'status': 'CONFLICT' if len(values) > 1 else 'UNCONTESTED_CLAIM',
                        'verified_fact': False})
    return results


def readiness(required: set[str], validated: set[str], *, snapshot_current: bool,
              has_blocking_conflict: bool = False) -> dict:
    """Coordinator-supplied evidence readiness, never automatic execution consent."""
    if not required:
        raise ValueError('required evidence slots may not be empty')
    missing = sorted(required - validated)
    ready = snapshot_current and not missing and not has_blocking_conflict
    return {'state': 'EVIDENCE_READY' if ready else 'NEEDS_CONTEXT',
            'missing': missing, 'snapshot_current': snapshot_current,
            'has_blocking_conflict': has_blocking_conflict,
            'execution_authorized': False, 'full_archive_complete': False}
