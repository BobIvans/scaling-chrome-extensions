"""Read-only format coverage over the existing pinned repository ledger."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from automation_core import digest, strict_int
import repo_context as repo
from source_eligibility import (CLASSIFIER_VERSION, SQL_FACT_ARGS, decimal,
                                project_facts, register_facts)

FRAME_BYTES = 32768
GAPS_SQL = "coalesce(json_extract(e.analysis,'$.format_eligibility.text_eligibility'),'UNKNOWN')!='ELIGIBLE' OR coalesce(json_extract(e.analysis,'$.format_eligibility.raw_capture'),'UNKNOWN')!='RECORDED' OR json_extract(e.analysis,'$.format_eligibility.lfs') IS NOT NULL"


def validate_request(action, *, query=None, limit=None, cursor=None, page_fields=False):
    if not isinstance(action, str):
        raise ValueError('DURABLE_SCHEMA')
    if action == 'SUMMARY':
        if page_fields:
            raise ValueError('DURABLE_SCHEMA')
        return -1
    if action != 'PAGE' or not isinstance(query, str) or query not in {'ALL', 'GAPS'}:
        raise ValueError('DURABLE_SCHEMA')
    strict_int(limit, 1, 20)
    if cursor is None:
        return -1
    if not isinstance(cursor, dict) or set(cursor) != {'snapshotId', 'classifierVersion', 'query', 'afterOrdinal'}:
        raise ValueError('DURABLE_SCHEMA')
    return decimal(cursor['afterOrdinal'])


@contextmanager
def read_view(store, namespace, sid, alias, profile):
    # Do not initialize schema, change journal mode, classify, prove or scan.
    path = Path(store) / 'content.sqlite3'
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.set_progress_handler(repo.pulse, 10000)
        register_facts(db)
        db.execute('BEGIN')
        snap = repo.load_snapshot(db, namespace, sid)
        if snap['alias'] != alias or json.loads(snap['profile']) != profile:
            raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
        if sid != digest({'alias': alias, 'profile': profile, 'head': snap['head'], 'tree': snap['tree']}):
            raise ValueError('CORRUPT_FACTS')
        yield db, snap
    finally:
        db.close()


def summary_db(db, snap):
    if type(snap['total']) is not int or type(snap['cursor']) is not int or not 0 <= snap['cursor'] <= snap['total']:
        raise ValueError('CORRUPT_FACTS')
    aggregate = db.execute('''SELECT count(*) AS ledger_rows, min(e.ordinal) AS first, max(e.ordinal) AS last,
        coalesce(sum(e.state!='PENDING'),0) AS terminal_entries,
        coalesce(sum(e.state='PENDING'),0) AS pending_entries,
        coalesce(sum(e.state='INDEXED'),0) AS indexed,
        coalesce(sum(e.state='EXCLUDED'),0) AS excluded,
        coalesce(sum(e.state='ERROR'),0) AS error,
        coalesce(sum(e.state NOT IN ('PENDING','INDEXED','EXCLUDED','ERROR')),0) AS invalid_states,
        coalesce(sum(occ_facts_status(''' + SQL_FACT_ARGS + ''')='SUPPORTED'),0) AS facts_entries,
        coalesce(sum(occ_facts_status(''' + SQL_FACT_ARGS + ''')='CORRUPT'),0) AS corrupt_facts,
        coalesce(sum(occ_source_text(''' + SQL_FACT_ARGS + ''')=1),0) AS text_eligible,
        coalesce(sum(CASE WHEN json_valid(e.analysis) AND occ_facts_status(''' + SQL_FACT_ARGS + ''')='SUPPORTED'
          THEN json_extract(e.analysis,'$.format_eligibility.raw_capture')='RECORDED' ELSE 0 END),0) AS raw_recorded,
        coalesce(sum(CASE WHEN json_valid(e.analysis) THEN json_extract(e.analysis,'$.format_eligibility.lfs') IS NOT NULL ELSE 0 END),0) AS lfs
        FROM repo_entries e WHERE e.snapshot_id=?''', (snap['id'],)).fetchone()
    counts = {k: aggregate[k] for k in ('ledger_rows', 'terminal_entries', 'pending_entries', 'facts_entries',
                                      'indexed', 'excluded', 'error', 'text_eligible', 'raw_recorded')}
    counts['total'], counts['gaps'] = snap['total'], aggregate['ledger_rows'] - aggregate['text_eligible']
    ledger_valid = (aggregate['ledger_rows'] == snap['total'] and not aggregate['invalid_states']
        and (snap['total'] == 0 or aggregate['first'] == 0 and aggregate['last'] == snap['total'] - 1))
    inventory_complete = ledger_valid and snap['cursor'] == snap['total'] and not aggregate['pending_entries']
    facts_complete = inventory_complete and aggregate['facts_entries'] == snap['total']
    state = ('CORRUPT_FACTS' if not ledger_valid or aggregate['corrupt_facts'] else
             'SCAN_PENDING' if not inventory_complete else 'READY' if facts_complete else 'FORMAT_FACTS_PENDING')
    # Counts are observations. A read-only metadata query never supplies byte proof.
    return {'state': state, **{k: str(v) for k, v in counts.items()},
            'inventory_complete': bool(inventory_complete), 'facts_complete': bool(facts_complete),
            'all_tracked_bytes_exportable': False if facts_complete and aggregate['raw_recorded'] < snap['total'] else None,
            'external_payloads_complete': None if aggregate['lfs'] or not facts_complete else True,
            'raw_integrity': 'NOT_RUN', 'ai_delivery': 'NOT_PERFORMED', 'ai_read': 'UNKNOWN'}


def next_cursor(sid, query, ordinal):
    return {'snapshotId': sid, 'classifierVersion': CLASSIFIER_VERSION, 'query': query, 'afterOrdinal': str(ordinal)}


def frame_size(coverage):
    result = {'schema': 'occ.native-durable-result.v1', 'operation': 'durable.repo.coverage', 'coverage': coverage}
    frames = ({'ok': True, 'result': result}, {'ok': True, 'requestId': 'x' * 128, 'durable': result})
    return max(len(json.dumps(f, ensure_ascii=False, allow_nan=False).encode('utf-8')) for f in frames)


def query(store, namespace, sid, alias, profile, action, *, query=None, limit=None, cursor=None):
    after = validate_request(action, query=query, limit=limit, cursor=cursor,
                             page_fields=action == 'SUMMARY' and any(x is not None for x in (query, limit, cursor)))
    if cursor is not None and (cursor['snapshotId'] != sid or cursor['classifierVersion'] != CLASSIFIER_VERSION or cursor['query'] != query):
        raise ValueError('COVERAGE_CURSOR_SCOPE_MISMATCH')
    with read_view(store, namespace, sid, alias, profile) as (db, snap):
        summary = summary_db(db, snap)
        result = {'schema': 'occ.repo-coverage.v1', 'snapshot_id': sid, 'classifier_version': CLASSIFIER_VERSION,
                  'action': action, 'query': query, 'summary': summary, 'rows': [], 'next_cursor': None}
        if action == 'SUMMARY':
            if frame_size(result) > FRAME_BYTES:
                raise ValueError('ROW_ENVELOPE_LIMIT')
            return result
        if summary['state'] != 'READY':
            raise ValueError('CORRUPT_FACTS' if summary['state'] == 'CORRUPT_FACTS' else 'FORMAT_FACTS_PENDING')
        where = ' AND (' + GAPS_SQL + ')' if query == 'GAPS' else ''
        rows = db.execute('SELECT e.* FROM repo_entries e WHERE e.snapshot_id=? AND e.ordinal>?' + where +
                          ' ORDER BY e.ordinal LIMIT ?', (sid, after, limit + 1)).fetchall()
        for i, row in enumerate(rows[:limit]):
            fact = project_facts(sid, row)
            candidate = dict(result, rows=result['rows'] + [fact],
                             next_cursor=next_cursor(sid, query, row['ordinal']) if i + 1 < len(rows) else None)
            if frame_size(candidate) > FRAME_BYTES:
                if not result['rows']:
                    raise ValueError('ROW_ENVELOPE_LIMIT')
                result['next_cursor'] = next_cursor(sid, query, int(result['rows'][-1]['ordinal']))
                break
            result = candidate
        if frame_size(result) > FRAME_BYTES:
            raise ValueError('ROW_ENVELOPE_LIMIT')
        return result


def write_gaps(store, namespace, sid, alias, profile, output):
    """Explicit deterministic GAPS.jsonl projection; raw manifest formats unchanged."""
    from repo_artifacts import atomic_file, file_proof, json_bytes, safe_path
    target = safe_path(output)
    for root in (Path(store).resolve(), Path(profile['root']).resolve()):
        if target.is_relative_to(root) or root.is_relative_to(target):
            raise ValueError('OUTPUT_MUST_BE_OUTSIDE_SOURCE_STORE_INPUT')
    count = 0
    with read_view(store, namespace, sid, alias, profile) as (db, snap):
        if summary_db(db, snap)['state'] != 'READY':
            raise ValueError('FORMAT_FACTS_PENDING')
        with atomic_file(target) as stream:
            for row in db.execute('SELECT e.* FROM repo_entries e WHERE e.snapshot_id=? AND (' + GAPS_SQL + ') ORDER BY e.ordinal', (sid,)):
                stream.write(json_bytes(project_facts(sid, row)))
                count += 1
    return {'schema': 'occ.format-gaps-projection.v1', 'snapshot_id': sid,
            'classifier_version': CLASSIFIER_VERSION, 'entries': str(count), **file_proof(target)}
