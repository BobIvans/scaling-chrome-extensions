"""Publish immutable JS/TS syntax projections from the captured repository ledger."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))

from repo_archive_input import operator_scope
from repo_artifacts import atomic_json, file_proof, json_bytes, outside, process_lock, safe_path, sync_dir
import repo_js_input as inputs
from repo_js_runtime import Control, budget, interpretation, node_path, parse_file, stable_digest as digest

ARTIFACTS = ('JS_ANALYSIS.jsonl', 'RELATIONS.jsonl', 'INTERPRETATION.json', 'ANALYSIS_STATUS.json')
FORMS = {'ESM_IMPORT', 'ESM_SIDE_EFFECT', 'ESM_REEXPORT', 'TS_IMPORT_TYPE', 'TS_EXPORT_TYPE',
         'COMMONJS_REQUIRE', 'IMPORT_EQUALS', 'DYNAMIC_IMPORT', 'COMPUTED_IMPORT'}
KINDS = {'VALUE_OR_MIXED', 'TYPE_ONLY', 'DYNAMIC_OR_UNKNOWN'}


def boundary(event, **context):
    """Local fault-injection seam; never exposed through input/profile/Native data."""


def within(path, root):
    return root in {'', '.'} or path == root or path.startswith(root + '/')


def resolve(source_path, reference, lookup, roots):
    form, specifier = reference['syntax_form'], reference['specifier']
    if form in {'COMMONJS_REQUIRE', 'IMPORT_EQUALS'}:
        return None, 'COMMONJS_NOT_QUALIFIED'
    if form in {'DYNAMIC_IMPORT', 'COMPUTED_IMPORT'}:
        return None, 'DYNAMIC_IMPORT_UNRESOLVED'
    if specifier is None or any(c in specifier for c in ('\\', '\0', '?', '#', '%', ':')):
        return None, 'SPECIFIER_FORM_UNSUPPORTED'
    if not specifier.startswith(('./', '../')):
        return None, 'NON_RELATIVE_POLICY_NOT_QUALIFIED'
    scopes = [root for root in roots if within(source_path, root)]
    if not scopes:
        return None, 'SOURCE_SCOPE_ESCAPE'
    scope = max(scopes, key=lambda root: len(root) if root != '.' else 0)
    target = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), specifier))
    if target == '..' or target.startswith('../') or target.startswith('/') or not within(target, scope):
        return None, 'SOURCE_SCOPE_ESCAPE'
    suffix = PurePosixPath(specifier).suffix
    if not suffix or specifier.endswith('/'):
        return None, 'EXTENSION_RULE_NOT_QUALIFIED'
    if suffix not in inputs.EXTENSIONS:
        return None, 'TARGET_EXTENSION_UNSUPPORTED'
    if inputs.extension(source_path) in {'.ts', '.tsx', '.mts', '.cts'} and suffix in {'.js', '.jsx', '.mjs', '.cjs'}:
        return None, 'TYPE_RESOLUTION_POLICY_REQUIRED'
    found = lookup(target)
    if found is None:
        return None, 'TARGET_MISSING'
    if not found['eligible']:
        return None, 'TARGET_NOT_ELIGIBLE'
    return found, None


def checked_span(record, raw):
    a, b = record.get('byte_start'), record.get('byte_end')
    if (type(a) is not int or type(b) is not int or not 0 <= a < b <= len(raw)
            or a < len(raw) and raw[a] & 0xc0 == 0x80
            or b < len(raw) and raw[b] & 0xc0 == 0x80
            or record.get('range_sha256') != hashlib.sha256(raw[a:b]).hexdigest()):
        raise ValueError('PARSER_EVIDENCE_INVALID')


def symbol_identity(namespace, alias, path, symbol, occurrence):
    """For consumers of the schema's ordered symbols; no callable binding claim."""
    return digest(['repo-static-symbol.v1', namespace, alias, path, symbol['kind'], symbol['name'], occurrence])


def relations(snap, entry, parsed, raw, interpretation_digest, lookup, roots, pulse=lambda: None):
    counts, result = Counter(), []
    for reference in parsed['refs']:
        pulse()
        if (not isinstance(reference, dict) or set(reference) != {'syntax_form', 'specifier', 'dependency_kind',
                'byte_start', 'byte_end', 'range_sha256'} or reference['syntax_form'] not in FORMS
                or reference['dependency_kind'] not in KINDS
                or reference['specifier'] is not None and not isinstance(reference['specifier'], str)):
            raise ValueError('PARSER_PROTOCOL_INVALID')
        dynamic = reference['syntax_form'] in {'COMMONJS_REQUIRE', 'IMPORT_EQUALS', 'DYNAMIC_IMPORT', 'COMPUTED_IMPORT'}
        if (dynamic != (reference['dependency_kind'] == 'DYNAMIC_OR_UNKNOWN')
                or reference['syntax_form'] in {'TS_IMPORT_TYPE', 'TS_EXPORT_TYPE'} and reference['dependency_kind'] != 'TYPE_ONLY'):
            raise ValueError('PARSER_PROTOCOL_INVALID')
        checked_span(reference, raw)
        if reference['specifier'] is not None:
            reference['specifier'].encode('utf8')
        key = (reference['syntax_form'], reference['specifier'])
        occurrence = counts[key]; counts[key] += 1
        target, reason = resolve(entry['path'], reference, lookup, roots)
        target_hash = None if target is None else target['file_sha256']
        edge_id = digest(['repo-static-edge.v1', snap['namespace'], snap['alias'], entry['path'],
                          reference['syntax_form'], reference['specifier'], occurrence])
        status = 'UNRESOLVED' if reason else 'LOCAL_STATIC_EXACT_PATH'
        revision = digest([edge_id, snap['id'], entry['file_hash'], target_hash, reference['byte_start'],
                           reference['byte_end'], reference['range_sha256'], interpretation_digest, status, reason])
        result.append({'schema': 'occ.repo-static-relation.v1', 'edge_id': edge_id, 'revision': revision,
                       'snapshot_id': snap['id'], 'namespace': snap['namespace'], 'repository': snap['alias'],
                       'source_path': entry['path'], 'source_sha256': entry['file_hash'], **reference,
                       'occurrence': occurrence, 'target_path': None if target is None else target['path'],
                       'target_sha256': target_hash, 'resolution_status': status, 'reason': reason,
                       'resolution_scope': 'MANIFEST_SOURCE_PATH_ONLY', 'symbol_binding': 'NOT_TYPECHECKED',
                       'evidence_class': 'JS_TS_STATIC_SYNTAX', 'interpretation_digest': interpretation_digest})
    previous = (-1, -1)
    for symbol in parsed['symbols']:
        pulse()
        if (not isinstance(symbol, dict) or set(symbol) != {'name', 'kind', 'byte_start', 'byte_end', 'range_sha256'}
                or not isinstance(symbol['name'], str) or not symbol['name']
                or symbol['kind'] not in {'FUNCTION_DECLARATION', 'CLASS_DECLARATION'}):
            raise ValueError('PARSER_PROTOCOL_INVALID')
        checked_span(symbol, raw)
        symbol['name'].encode('utf8')
        position = (symbol['byte_start'], symbol['byte_end'])
        if position < previous:
            raise ValueError('PARSER_EVIDENCE_INVALID')
        previous = position
    return result


def analyze_entry(db, snap, entry, interpretation_digest, source, control, legacy=False):
    row = {'schema': 'occ.repo-js-file-analysis.v1', 'snapshot_id': snap['id'],
           'namespace': snap['namespace'], 'repository': snap['alias'], 'source_path': entry['path'],
           'source_sha256': entry['file_hash'], 'raw_bytes': entry['size'], 'analysis_status': 'ELIGIBILITY_GAP',
           'reason': None, 'symbol_binding': 'NOT_TYPECHECKED', 'symbols': [], 'reference_count': 0,
           'interpretation_digest': interpretation_digest}
    reason = inputs.eligibility(db, snap, entry, legacy)
    if reason:
        row['analysis_status'] = 'RAW_BYTES_UNAVAILABLE' if reason == 'RAW_BYTES_UNAVAILABLE' else 'ELIGIBILITY_GAP'
        row['reason'] = reason
        return row, []
    raw, reason = inputs.reconstruct(db, snap, entry, control.limits['file_bytes'], control)
    if reason:
        row.update(analysis_status='NOT_SUPPORTED', reason=reason)
        return row, []
    parsed = parse_file(raw, inputs.extension(entry['path']), control)
    if parsed['status'] == 'PARSER_FAILED':
        row.update(analysis_status='PARSER_FAILED', reason=parsed['reason'])
        return row, []
    def lookup(path):
        found = db.execute('SELECT * FROM repo_entries WHERE snapshot_id=? AND path=?', (snap['id'], path)).fetchone()
        if found is None:
            return None
        return {'path': path, 'file_sha256': found['file_hash'],
                'eligible': inputs.eligibility(db, snap, found, legacy) is None}
    try:
        refs = relations(snap, entry, parsed, raw, interpretation_digest, lookup, source['source_roots'], control.pulse)
    except (ValueError, UnicodeError, TypeError, KeyError):
        if control.reason:
            raise
        row.update(analysis_status='PARSER_FAILED', reason='PARSER_EVIDENCE_INVALID')
        return row, []
    row.update(analysis_status='AST_SYNTAX_ONLY', reason=None, symbols=parsed['symbols'], reference_count=len(refs))
    return row, refs


class Projection:
    def __init__(self, path, control, usage):
        self.path, self.control, self.usage = path, control, usage
        self.stream = path.open('xb')
        self.buffer, self.rows, self.written_rows = bytearray(), 0, 0
        self.hasher, self.bytes = hashlib.sha256(), 0

    def append(self, row):
        data = json_bytes(row)
        maximum = self.control.limits['stage_max_bytes']
        if maximum is not None and self.usage[0] + len(data) > maximum:
            raise ValueError('GLOBAL_STAGE_BUDGET')
        self.usage[0] += len(data)
        self.hasher.update(data); self.bytes += len(data)
        limit = self.control.limits['projection_batch_bytes']
        if len(data) > limit:
            self.flush(); self.stream.write(data)
        else:
            if len(self.buffer) + len(data) > limit:
                self.flush()
            self.buffer.extend(data)
        self.rows += 1; self.written_rows += 1
        if self.rows >= self.control.limits['projection_batch_rows']:
            self.flush()

    def flush(self):
        self.control.pulse()
        self.stream.write(self.buffer)
        self.buffer.clear(); self.rows = 0

    def close(self):
        if not self.stream.closed:
            try:
                self.flush(); self.stream.flush(); os.fsync(self.stream.fileno())
            finally:
                self.stream.close()

    def proof(self):
        return {'bytes': self.bytes, 'sha256': self.hasher.hexdigest()}


def checked_bundle(output, expected=None):
    safe_path(output, directory=True)
    if {p.name for p in output.iterdir()} != set(ARTIFACTS):
        raise ValueError('DERIVED_BUNDLE_CONFLICT')
    status = json.loads(safe_path(output / 'ANALYSIS_STATUS.json').read_text('utf8'))
    if status.get('state') not in {'READY', 'PARTIAL'} or not status.get('projection_complete'):
        raise ValueError('DERIVED_BUNDLE_CONFLICT')
    for name in ARTIFACTS[:-1]:
        if file_proof(output / name) != status.get('files', {}).get(name):
            raise ValueError('DERIVED_BUNDLE_CONFLICT')
    if expected is not None and status != expected:
        raise ValueError('DERIVED_BUNDLE_CONFLICT')
    return status


def build(profile_path, alias, snapshot_id, output, *, limits=None, legacy=False, progress=lambda value: None):
    limits = budget(limits)
    control = Control(limits, progress)
    store, source = operator_scope(profile_path, alias)
    control.node_executable = node_path()
    executable = Path(control.node_executable)
    if executable.is_relative_to(Path(source['root']).resolve()) or executable.is_relative_to(store):
        raise ValueError('NODE_EXECUTABLE_IN_SOURCE_OR_STORE')
    output = outside(output, source['root'], store, Path(__file__).resolve().parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.with_name('.' + output.name + '.stage-' + uuid.uuid4().hex)
    lock = output.with_name('.' + output.name + '.lock')
    with process_lock(lock):
        safe_path(stage, directory=True)
        stage.mkdir(mode=0o700)
        writers = []
        try:
            interpreted = interpretation(limits, legacy, control.node_executable)
            with inputs.read_snapshot(store, source, alias, snapshot_id, control) as (db, snap):
                interpreted['input_binding'] = {'snapshot_id': snap['id'], 'namespace': snap['namespace'],
                    'repository': snap['alias'], 'profile_digest': digest(source),
                    'manifest_eligibility_digest': inputs.snapshot_digest(db, snap, control)}
                interpretation_digest = digest(interpreted)
                atomic_json(stage / 'INTERPRETATION.json', interpreted)
                usage = [(stage / 'INTERPRETATION.json').stat().st_size]
                if limits['stage_max_bytes'] is not None and usage[0] > limits['stage_max_bytes']:
                    raise ValueError('GLOBAL_STAGE_BUDGET')
                files = Projection(stage / 'JS_ANALYSIS.jsonl', control, usage)
                edges = Projection(stage / 'RELATIONS.jsonl', control, usage)
                writers = [files, edges]
                outcomes, unresolved, exact, type_only, scc = Counter(), Counter(), 0, 0, 0
                eligibility_missing = 0
                for entry in db.execute('SELECT * FROM repo_entries WHERE snapshot_id=? ORDER BY path COLLATE BINARY', (snap['id'],)):
                    control.pulse()
                    control.counts['processed_entries'] += 1
                    if inputs.extension(entry['path']) not in inputs.EXTENSIONS:
                        continue
                    row, refs = analyze_entry(db, snap, entry, interpretation_digest, source, control, legacy)
                    files.append(row); outcomes[row['analysis_status']] += 1
                    control.counts['candidate_files'] += 1
                    # A valid known ineligible source is fully accounted by
                    # PR005. Unknown/invalid policy facts are a separate gap.
                    eligibility_missing += int(row['analysis_status'] == 'ELIGIBILITY_GAP'
                        and row['reason'] not in {'TEXT_NOT_ELIGIBLE', 'LEGACY_TEXT_NOT_ELIGIBLE'})
                    for ref in refs:
                        edges.append(ref)
                        control.counts['relations'] += 1
                        if ref['resolution_status'] == 'UNRESOLVED':
                            unresolved[ref['reason']] += 1
                        else:
                            exact += 1
                            type_only += int(ref['dependency_kind'] == 'TYPE_ONLY')
                            scc += int(ref['dependency_kind'] == 'VALUE_OR_MIXED')
                    boundary('AFTER_FILE', stage=stage, row=row)
                for writer in writers:
                    writer.close()
                counts = control.counts
                if counts['processed_entries'] != snap['total'] or files.written_rows != counts['candidate_files']:
                    raise ValueError('DERIVED_PROJECTION_INCOMPLETE')
                failed = sum(n for state, n in outcomes.items() if state != 'AST_SYNTAX_ONLY')
                proofs = {name: file_proof(stage / name) for name in ARTIFACTS[:-1]}
                expected_interpretation = json_bytes(interpreted)
                if (proofs['JS_ANALYSIS.jsonl'] != files.proof() or proofs['RELATIONS.jsonl'] != edges.proof()
                        or proofs['INTERPRETATION.json'] != {'bytes': len(expected_interpretation),
                            'sha256': hashlib.sha256(expected_interpretation).hexdigest()}):
                    raise ValueError('DERIVED_PROJECTION_CORRUPT')
                status = {'schema': 'occ.repo-js-analysis-status.v1', 'state': 'PARTIAL' if failed else 'READY',
                    'snapshot_id': snap['id'], 'namespace': snap['namespace'], 'repository': snap['alias'],
                    'interpretation_digest': interpretation_digest, 'files': proofs, **counts,
                    'other_language_entries': snap['total'] - counts['candidate_files'],
                    'analysis_outcomes': dict(outcomes), 'unresolved_reasons': dict(unresolved),
                    'local_static_edges': exact, 'type_only_exact_edges': type_only, 'scc_eligible_edges': scc,
                    'inventory_complete': True, 'raw_exact_for_indexed': True, 'projection_complete': True,
                    'syntax_complete': failed == 0, 'resolution_complete': failed == 0 and not unresolved,
                    'eligibility_complete': eligibility_missing == 0,
                    'eligibility_policy_verified': not legacy and eligibility_missing == 0,
                    'all_tracked_bytes_exportable': snap['raw_proof']['all_tracked_bytes_exportable'],
                    'raw_scope': 'INDEXED_CAPTURED_BLOBS', 'group_consumer': 'NOT_INTEGRATED_PR006_PYTHON_ONLY',
                    'authority': 'DATA_ONLY', 'execution_authorized': False, 'ai_delivery': 'NOT_PERFORMED'}
                if limits['stage_max_bytes'] is not None and usage[0] + len(json_bytes(status)) > limits['stage_max_bytes']:
                    raise ValueError('GLOBAL_STAGE_BUDGET')
                atomic_json(stage / 'ANALYSIS_STATUS.json', status)
                checked_bundle(stage, status)
                control.pulse()
                boundary('BEFORE_PUBLISH', stage=stage, output=output)
                if operator_scope(profile_path, alias) != (store, source):
                    raise ValueError('PROFILE_CHANGED')
                checked_bundle(stage, status)
                if output.exists():
                    checked_bundle(output, status)
                    shutil.rmtree(stage)
                    reused = True
                else:
                    sync_dir(stage)
                    os.rename(stage, output)
                    sync_dir(output.parent)
                    reused = False
                boundary('AFTER_PUBLISH', output=output)
                return dict(status, reused=reused, runtime={'seconds': round(time.monotonic() - control.started, 3),
                    'parent_child_peak_rss_bytes': control.peak_rss if control.rss_observed else None,
                    'parser_peak_rss_bytes': control.child_peak or None, 'rss_is_observation': True})
        except BaseException as exc:
            if stage.exists():
                for writer in writers:
                    if not writer.stream.closed:
                        writer.stream.close()
                reason = 'CANCELLED' if isinstance(exc, KeyboardInterrupt) else control.reason or (
                    str(exc) if isinstance(exc, ValueError) else 'LOCAL_IO_OR_PROCESS_FAILURE')
                try:
                    atomic_json(stage / 'BLOCKED.json', {'state': 'BLOCKED', 'reason': reason, **control.counts,
                                                       'projection_complete': False})
                except OSError:
                    pass
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator-profile', '--profile', type=Path, required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--snapshot-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--budget', type=Path)
    parser.add_argument('--legacy-capture-guard', action='store_true',
                        help='Explicitly accept unverified PR005 policy on old captures; recorded in interpretation.')
    args = parser.parse_args(argv)
    try:
        limits = None if args.budget is None else json.loads(safe_path(args.budget).read_text('utf8'))
        result = build(args.operator_profile, args.repository, args.snapshot_id, args.output, limits=limits,
                       legacy=args.legacy_capture_guard,
                       progress=lambda value: print(json.dumps(value), file=sys.stderr, flush=True))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print(json.dumps({'state': 'BLOCKED', 'reason': 'CANCELLED', 'projection_complete': False}))
        return 130
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) and re.fullmatch('[A-Z0-9_]+', str(exc)) else 'LOCAL_IO_OR_PROCESS_FAILURE'
        print(json.dumps({'state': 'BLOCKED', 'reason': reason, 'projection_complete': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
