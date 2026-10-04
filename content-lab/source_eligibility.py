"""Versioned whole-source text facts; no Git, payload acquisition or source imports.

The CLI explicitly backfills the existing SQLite ledger from captured chunks.
Its source/byte budgets bound one invocation, never the repository corpus.
"""
from __future__ import annotations

import argparse
import codecs
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = 'occ.format-eligibility.v1'
CLASSIFIER_VERSION = 'utf8-controls-strict-lfs3.v1'
MAX_SQLITE_INT = 9223372036854775807
CONTROL = re.compile(rb'[\x00-\x08\x0b\x0e-\x1f]')
LFS_VERSION = b'version https://git-lfs.github.com/spec/v1\n'
LFS_CANONICAL = re.compile(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (0|[1-9][0-9]*)\n')
FORMAT_KINDS = {'UTF8_TEXT_CANDIDATE', 'EMPTY', 'BINARY_CONTROL_HEURISTIC', 'NON_UTF8',
                'LFS_POINTER_V1', 'LFS_POINTER_MALFORMED', 'LFS_POINTER_UNSUPPORTED',
                'SYMLINK_METADATA', 'SUBMODULE_METADATA', 'UNSUPPORTED_PATH_METADATA',
                'NOT_CLASSIFIED', 'LEGACY_UNKNOWN', 'CORRUPT_CAPTURE'}
WIRE_FIELDS = {'schema', 'snapshot_id', 'ordinal', 'path', 'mode', 'kind', 'git_oid', 'git_size',
               'disposition', 'legacy_reason', 'file_sha256', 'classifier_version', 'format_kind',
               'text_eligibility', 'raw_capture', 'raw_integrity', 'reasons', 'parser', 'lfs'}


def decimal(value):
    """Lossless wire integer within SQLite's signed integer domain."""
    if not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]{0,18}', value):
        raise ValueError('COVERAGE_INTEGER_REQUIRED')
    number = int(value)
    if number > MAX_SQLITE_INT:
        raise ValueError('COVERAGE_INTEGER_REQUIRED')
    return number


class SourceClassifier:
    """Fixed prefix and incremental decoder; memory independent of source size."""
    def __init__(self):
        self.decoder = codecs.getincrementaldecoder('utf-8')('strict')
        self.size, self.prefix, self.utf8, self.controls = 0, b'', True, False

    def feed(self, raw):
        self.size += len(raw)
        self.prefix += raw[:max(0, 1024 - len(self.prefix))]
        self.controls |= bool(CONTROL.search(raw))
        if self.utf8:
            try:
                self.decoder.decode(raw)
            except UnicodeDecodeError:
                self.utf8 = False

    def finish(self):
        if self.utf8:
            try:
                self.decoder.decode(b'', final=True)
            except UnicodeDecodeError:
                self.utf8 = False
        result = {'format_kind': 'UTF8_TEXT_CANDIDATE', 'text_eligibility': 'ELIGIBLE',
                  'reasons': [], 'lfs': None}
        if not self.utf8:
            result.update(format_kind='NON_UTF8', text_eligibility='INELIGIBLE', reasons=['INVALID_UTF8'])
        elif self.controls:
            result.update(format_kind='BINARY_CONTROL_HEURISTIC', text_eligibility='INELIGIBLE', reasons=['BINARY_CONTROL_BYTES'])
        elif not self.size:
            result['format_kind'] = 'EMPTY'
        elif self.prefix.startswith((b'version https://git-lfs.github.com/spec/',
                                     b'version https://hawser.github.com/spec/',
                                     b'version https://git-media.io/')):
            match = LFS_CANONICAL.fullmatch(self.prefix) if self.size < 1024 else None
            lfs = {'payload_sha256': None, 'payload_size': None, 'descriptor_evidence': 'UNPARSED',
                   'payload_availability': 'NOT_CHECKED', 'payload_verification': 'NOT_RUN'}
            kind, reason = 'LFS_POINTER_MALFORMED', 'LFS_POINTER_INVALID_SYNTAX'
            if match:
                kind, reason = 'LFS_POINTER_V1', 'LFS_PAYLOAD_NOT_CHECKED'
                lfs.update(payload_sha256=match[1].decode('ascii'), payload_size=match[2].decode('ascii'),
                           descriptor_evidence='DECLARED_IN_POINTER')
            elif not self.prefix.startswith(LFS_VERSION):
                kind, reason = 'LFS_POINTER_UNSUPPORTED', 'LFS_LEGACY_VERSION_NOT_IMPLEMENTED'
            elif b'\next-' in self.prefix:
                kind, reason = 'LFS_POINTER_UNSUPPORTED', 'LFS_EXTENSIONS_NOT_IMPLEMENTED'
            elif self.size >= 1024:
                kind, reason = 'LFS_POINTER_UNSUPPORTED', 'LFS_POINTER_FORM_NOT_IMPLEMENTED'
            elif not re.search(rb'\noid sha256:[0-9a-f]{64}\n', self.prefix):
                reason = 'LFS_POINTER_INVALID_OID'
            result.update(format_kind=kind, text_eligibility='METADATA_ONLY', reasons=[reason], lfs=lfs)
        return result


def classify_chunks(chunks, *, progress=lambda: None):
    classifier = SourceClassifier()
    for raw in chunks:
        classifier.feed(raw)
        progress()
    return classifier.finish()


def analysis_object(value):
    result = json.loads(value or '{}')
    if not isinstance(result, dict):
        raise ValueError('CORRUPT_FACTS')
    return result


def source_identity(snapshot_id, row):
    return {'snapshot_id': snapshot_id, 'ordinal': str(row['ordinal']), 'path': row['path'],
            'mode': row['mode'], 'kind': row['kind'], 'git_oid': row['oid'],
            'git_size': str(row['size']) if row['size'] is not None else None,
            'disposition': row['state'], 'legacy_reason': row['reason'], 'file_sha256': row['file_hash']}


def binding(identity):
    return hashlib.sha256(json.dumps(dict(identity, classifier_version=CLASSIFIER_VERSION),
        ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')).hexdigest()


def make_facts(snapshot_id, row, classified, parser=None):
    identity = source_identity(snapshot_id, row)
    return dict(identity, schema=SCHEMA, classifier_version=CLASSIFIER_VERSION, parser=parser,
                raw_capture='RECORDED' if row['state'] == 'INDEXED' else 'NOT_CAPTURED',
                raw_integrity='NOT_RUN', **classified, _binding=binding(identity))


def metadata_facts(snap, row):
    """Facts for terminal metadata, without reading excluded or unavailable bytes."""
    kind, reason = 'NOT_CLASSIFIED', row['reason'] or row['state']
    if row['mode'] == '120000':
        kind, reason = 'SYMLINK_METADATA', 'SYMLINK_METADATA_ONLY'
    elif row['mode'] == '160000' or row['kind'] == 'commit':
        kind, reason = 'SUBMODULE_METADATA', 'SUBMODULE_METADATA_ONLY'
    elif row['reason'] == 'UNSUPPORTED_PATH':
        kind = 'UNSUPPORTED_PATH_METADATA'
    elif row['reason'] == 'SECRET_TEXT_HEURISTIC':
        reason = 'PROTECTED_TEXT_HEURISTIC'
    elif row['reason'] == 'PROTECTED_NAME_OR_OPERATOR_EXCLUSION':
        # Preserve legacy reason while distinguishing its policy evidence.
        import repo_context as repo
        reason = 'PROTECTED_NAME' if repo.SECRET_NAME.search(row['path']) else 'OPERATOR_EXCLUSION'
    elif row['reason'] in {'REPO_GIT_READ_FAILED', 'BLOB_SIZE_UNAVAILABLE'}:
        reason = 'BLOB_UNAVAILABLE'
    return make_facts(snap['id'], row, {'format_kind': kind, 'text_eligibility': 'INELIGIBLE',
        'reasons': [reason], 'lfs': None}, analysis_object(row['analysis']).get('parser'))


def facts_status(snapshot_id, row):
    """Validate the supported fact generation and its exact source binding."""
    try:
        facts = analysis_object(row['analysis']).get('format_eligibility')
        if not isinstance(facts, dict) or facts.get('classifier_version') != CLASSIFIER_VERSION:
            return 'PENDING'
        identity = source_identity(snapshot_id, row)
        if (set(facts) != WIRE_FIELDS | {'_binding'} or facts.get('schema') != SCHEMA or facts.get('_binding') != binding(identity)
                or any(facts.get(k) != v for k, v in identity.items())
                or facts.get('format_kind') not in FORMAT_KINDS
                or facts.get('text_eligibility') not in {'ELIGIBLE', 'INELIGIBLE', 'METADATA_ONLY', 'UNKNOWN'}
                or facts.get('raw_capture') not in {'RECORDED', 'NOT_CAPTURED', 'CORRUPT', 'UNKNOWN'}
                or facts.get('raw_integrity') not in {'NOT_RUN', 'PASS', 'FAIL'}
                or not isinstance(facts.get('reasons'), list)
                or not all(isinstance(x, str) for x in facts['reasons'])
                or 'parser' not in facts or facts.get('parser') is not None and not isinstance(facts['parser'], str)
                or 'lfs' not in facts or len(set(facts['reasons'])) != len(facts['reasons'])):
            return 'CORRUPT'
        eligible = facts['text_eligibility'] == 'ELIGIBLE'
        if (eligible != (facts['format_kind'] in {'UTF8_TEXT_CANDIDATE', 'EMPTY'})
                or eligible and (row['state'] != 'INDEXED' or facts['raw_capture'] != 'RECORDED')
                or facts['format_kind'] in {'LEGACY_UNKNOWN', 'NOT_CLASSIFIED'} and facts['text_eligibility'] == 'UNKNOWN'
                or facts['raw_capture'] == 'RECORDED' and row['state'] != 'INDEXED'
                or facts['raw_integrity'] != 'NOT_RUN'
                or facts['format_kind'] == 'EMPTY' and row['size'] != 0
                or facts['format_kind'] == 'UTF8_TEXT_CANDIDATE' and not row['size']
                or facts['format_kind'] == 'LEGACY_UNKNOWN'
                or facts['format_kind'] == 'NOT_CLASSIFIED' and row['state'] == 'INDEXED'
                or facts['format_kind'] == 'CORRUPT_CAPTURE'):
            return 'CORRUPT'
        lfs = facts['lfs']
        pointer = facts['format_kind'].startswith('LFS_POINTER_')
        if pointer:
            if (not isinstance(lfs, dict) or set(lfs) != {'payload_sha256', 'payload_size', 'descriptor_evidence',
                'payload_availability', 'payload_verification'} or facts['text_eligibility'] != 'METADATA_ONLY'
                or lfs['payload_availability'] != 'NOT_CHECKED' or lfs['payload_verification'] != 'NOT_RUN'):
                return 'CORRUPT'
            if facts['format_kind'] == 'LFS_POINTER_V1':
                if (lfs['descriptor_evidence'] != 'DECLARED_IN_POINTER'
                    or not isinstance(lfs['payload_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', lfs['payload_sha256'])
                    or not isinstance(lfs['payload_size'], str) or not re.fullmatch(r'0|[1-9][0-9]*', lfs['payload_size'])):
                    return 'CORRUPT'
            elif lfs['descriptor_evidence'] != 'UNPARSED' or lfs['payload_sha256'] is not None or lfs['payload_size'] is not None:
                return 'CORRUPT'
        elif lfs is not None or facts['text_eligibility'] == 'METADATA_ONLY':
            return 'CORRUPT'
        return 'SUPPORTED'
    except (ValueError, TypeError, KeyError):
        return 'CORRUPT'


def project_facts(snapshot_id, row):
    status = facts_status(snapshot_id, row)
    if status == 'SUPPORTED':
        facts = analysis_object(row['analysis'])['format_eligibility']
    else:
        facts = make_facts(snapshot_id, row, {'format_kind': 'LEGACY_UNKNOWN' if status == 'PENDING' else 'CORRUPT_CAPTURE',
            'text_eligibility': 'UNKNOWN' if status == 'PENDING' else 'INELIGIBLE',
            'reasons': ['FORMAT_BACKFILL_REQUIRED' if status == 'PENDING' else 'CORRUPT_FACTS'], 'lfs': None})
        facts['raw_capture'] = 'UNKNOWN' if status == 'PENDING' else 'CORRUPT'
        if status == 'CORRUPT':
            facts['raw_integrity'] = 'FAIL'
        # A bound backfill fault keeps its specific, non-content error detail.
        try:
            stored = analysis_object(row['analysis']).get('format_eligibility', {})
            if stored.get('format_kind') == 'CORRUPT_CAPTURE' and stored.get('_binding') == facts['_binding']:
                facts['reasons'] = stored['reasons']
        except (ValueError, TypeError, KeyError):
            pass
    return {k: facts[k] for k in sorted(WIRE_FIELDS)}


def text_blocker(snapshot_id, row):
    facts = project_facts(snapshot_id, row)
    if facts['text_eligibility'] == 'ELIGIBLE':
        return None
    if facts['text_eligibility'] == 'UNKNOWN':
        return 'FORMAT_BACKFILL_REQUIRED'
    return facts['reasons'][0] if facts['reasons'] else 'SOURCE_TEXT_INELIGIBLE'


SQL_FACT_ARGS = 'e.analysis,e.snapshot_id,e.ordinal,e.path,e.mode,e.kind,e.oid,e.size,e.state,e.reason,e.file_hash'


def register_facts(db):
    def status(analysis, sid, ordinal, path, mode, kind, oid, size, state, reason, file_hash):
        row = dict(analysis=analysis, ordinal=ordinal, path=path, mode=mode, kind=kind,
                   oid=oid, size=size, state=state, reason=reason, file_hash=file_hash)
        return facts_status(sid, row)
    def eligible(*args):
        if status(*args) != 'SUPPORTED':
            return 0
        return int(analysis_object(args[0])['format_eligibility']['text_eligibility'] == 'ELIGIBLE')
    def checkpoint(*args):
        if status(*args) == 'SUPPORTED':
            return 1
        try:
            facts = analysis_object(args[0]).get('format_eligibility', {})
            identity = source_identity(args[1], dict(ordinal=args[2], path=args[3], mode=args[4], kind=args[5],
                oid=args[6], size=args[7], state=args[8], reason=args[9], file_hash=args[10]))
            return int(facts.get('schema') == SCHEMA and facts.get('classifier_version') == CLASSIFIER_VERSION
                and facts.get('format_kind') == 'CORRUPT_CAPTURE' and facts.get('_binding') == binding(identity)
                and all(facts.get(k) == v for k, v in identity.items()))
        except (ValueError, TypeError):
            return 0
    db.create_function('occ_facts_status', 11, status, deterministic=True)
    db.create_function('occ_source_text', 11, eligible, deterministic=True)
    db.create_function('occ_facts_checkpoint', 11, checkpoint, deterministic=True)


def current_text_sql(db):
    """Shared current-source predicate, evaluated before search LIMIT/inclusion."""
    generic = "substr(sync_heads.source_key,1,4)!='git:'"
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='repo_heads'").fetchone():
        return generic
    register_facts(db)
    return '(' + generic + ''' OR EXISTS (
        SELECT 1 FROM repo_chunks c JOIN repo_entries e
          ON e.snapshot_id=c.snapshot_id AND e.path=c.path
        JOIN repo_heads h ON h.snapshot_id=e.snapshot_id
        JOIN repo_snapshots s ON s.id=e.snapshot_id
        WHERE c.item_id=sync_heads.item_id AND h.namespace=sync_heads.namespace
          AND sync_heads.generation=s.id AND sync_heads.source_key='git:'||h.alias||':'||c.logical_id
          AND s.namespace=h.namespace AND s.alias=h.alias AND s.cursor=s.total
          AND e.state='INDEXED' AND occ_source_text(''' + SQL_FACT_ARGS + ')=1))'


def blocked_item_reason(db, namespace, item_id):
    head = db.execute('SELECT source_key FROM sync_heads WHERE namespace=? AND item_id=? AND present=1',
                      (namespace, item_id)).fetchone()
    if head is None or not head['source_key'].startswith('git:'):
        return 'ITEM_OUTSIDE_SCOPE_OR_STALE'
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='repo_heads'").fetchone():
        row = db.execute('''SELECT e.* FROM repo_chunks c JOIN repo_entries e
          ON c.snapshot_id=e.snapshot_id AND c.path=e.path JOIN repo_heads h ON h.snapshot_id=e.snapshot_id
          WHERE h.namespace=? AND c.item_id=? LIMIT 1''', (namespace, item_id)).fetchone()
        if row:
            return text_blocker(row['snapshot_id'], row) or 'ITEM_OUTSIDE_SCOPE_OR_STALE'
    return 'FORMAT_BACKFILL_REQUIRED'


def capture_classification(db, snap, row, *, byte_budget=None):
    """Stored bytes only; prove every range/revision/hash/Git OID before facts."""
    from automation_core import digest
    from repo_artifacts import oid_hasher
    import repo_context as repo
    if row['kind'] != 'blob' or row['mode'] not in {'100644', '100755'} or row['size'] is None:
        raise ValueError('CAPTURE_METADATA_INVALID')
    classifier, file_hash, blob_hash = SourceClassifier(), hashlib.sha256(), oid_hasher(row['oid'], row['size'])
    end = count = 0
    cursor = db.execute('''SELECT ordinal,logical_id,revision,byte_start,byte_end,length(raw) AS raw_size
        FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal''', (snap['id'], row['path']))
    try:
        for chunk in cursor:
            if (chunk['raw_size'] > repo.CHUNK_BYTES or chunk['byte_end'] - chunk['byte_start'] != chunk['raw_size']
                    or chunk['byte_end'] > row['size']):
                raise ValueError('CAPTURE_CHUNK_SIZE_INVALID')
            # Check stored length before materializing a potentially damaged BLOB.
            raw = db.execute('SELECT raw FROM repo_chunks WHERE snapshot_id=? AND path=? AND ordinal=?',
                             (snap['id'], row['path'], chunk['ordinal'])).fetchone()[0]
            if byte_budget is not None and end + len(raw) > byte_budget:
                raise ValueError('BACKFILL_BYTE_BUDGET')
            if (chunk['ordinal'] != count or chunk['byte_start'] != end or chunk['byte_end'] != end + len(raw)
                    or not raw and (row['size'] != 0 or count != 0)
                    or chunk['revision'] != digest([chunk['logical_id'], row['file_hash'], repo.sha(raw), end, end + len(raw)])):
                raise ValueError('CAPTURE_RANGE_OR_REVISION_INVALID')
            classifier.feed(raw)
            file_hash.update(raw)
            blob_hash.update(raw)
            end, count = end + len(raw), count + 1
            repo.pulse()
    finally:
        cursor.close()
    if not count or end != row['size'] or file_hash.hexdigest() != row['file_hash'] or blob_hash.hexdigest() != row['oid']:
        raise ValueError('CAPTURE_HASH_OR_GIT_OID_INVALID')
    return classifier.finish()


def write_facts(db, snap, row, facts):
    analysis = analysis_object(row['analysis'])
    analysis['format_eligibility'] = facts
    db.execute('UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path=?',
               (json.dumps(analysis, ensure_ascii=False, allow_nan=False), snap['id'], row['path']))


def backfill(store, namespace, snapshot_id, alias, profile, *, max_entries=100, max_bytes=67108864):
    """One source per transaction; committed same-bound facts are restart checkpoints."""
    from automation_core import strict_int
    import repo_context as repo
    strict_int(max_entries, 1, MAX_SQLITE_INT)
    strict_int(max_bytes, 1, MAX_SQLITE_INT)
    db = repo.db_for(Path(store))
    updated = corrupt = byte_count = 0
    after = -1
    blocker = None
    try:
        register_facts(db)
        for _ in range(max_entries):
            with db:
                db.execute('BEGIN IMMEDIATE')
                snap = repo.load_snapshot(db, namespace, snapshot_id)
                if snap['alias'] != alias or json.loads(snap['profile']) != profile:
                    raise ValueError('REPO_OUTSIDE_OPERATOR_SCOPE')
                from automation_core import digest
                if snap['id'] != digest({'alias': alias, 'profile': profile, 'head': snap['head'], 'tree': snap['tree']}):
                    raise ValueError('CORRUPT_FACTS')
                if snap['cursor'] != snap['total'] or not repo.inventory_valid_db(db, snap) or repo.entry_counts_db(db, snapshot_id).get('PENDING'):
                    raise ValueError('CONTEXT_INCOMPLETE')
                # Bound corrupt facts are terminal blockers, not retry loops.
                row = db.execute('''SELECT e.* FROM repo_entries e WHERE e.snapshot_id=? AND e.ordinal>?
                    AND occ_facts_checkpoint(''' + SQL_FACT_ARGS + ''')=0
                    ORDER BY e.ordinal LIMIT 1''', (snapshot_id, after)).fetchone()
                if row is None:
                    break
                if row['state'] == 'INDEXED' and (row['size'] or 0) > max_bytes - byte_count:
                    blocker = 'BACKFILL_BYTE_BUDGET'
                    break
                if row['state'] != 'INDEXED':
                    facts = metadata_facts(snap, row)
                else:
                    try:
                        classified = capture_classification(db, snap, row, byte_budget=max_bytes - byte_count)
                        facts = make_facts(snapshot_id, row, classified, analysis_object(row['analysis']).get('parser'))
                        byte_count += row['size']
                    except ValueError as exc:
                        if str(exc) == 'BACKFILL_BYTE_BUDGET':
                            blocker = str(exc)
                            break
                        facts = make_facts(snapshot_id, row, {'format_kind': 'CORRUPT_CAPTURE', 'text_eligibility': 'INELIGIBLE',
                            'reasons': [str(exc)], 'lfs': None}, analysis_object(row['analysis']).get('parser'))
                        facts.update(raw_capture='CORRUPT', raw_integrity='FAIL')
                        corrupt += 1
                write_facts(db, snap, row, facts)
                updated += 1
                after = row['ordinal']
        from repo_coverage import query
        summary = query(store, namespace, snapshot_id, alias, profile, 'SUMMARY')['summary']
        return {'schema': 'occ.format-backfill-result.v1', 'snapshot_id': snapshot_id,
                'classifier_version': CLASSIFIER_VERSION, 'updated_entries': str(updated),
                'corrupt_entries': str(corrupt), 'verified_bytes': str(byte_count),
                'invocation_budget': {'entries': str(max_entries), 'bytes': str(max_bytes)},
                'blocker': blocker, 'summary': summary}
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--backfill', action='store_true')
    parser.add_argument('--max-entries', type=int, default=100)
    parser.add_argument('--max-bytes', type=int, default=67108864)
    parser.add_argument('--gaps-output', type=Path)
    args = parser.parse_args(argv)
    from repo_archive_input import operator_scope
    store, source = operator_scope(args.profile, args.repository)
    if not args.backfill and args.gaps_output is None:
        parser.error('--backfill or --gaps-output required')
    result = backfill(store, source['namespace'], args.snapshot, args.repository, source,
                      max_entries=args.max_entries, max_bytes=args.max_bytes) if args.backfill else {}
    if args.gaps_output is not None:
        from repo_coverage import write_gaps
        result['gaps'] = write_gaps(store, source['namespace'], args.snapshot, args.repository, source, args.gaps_output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
