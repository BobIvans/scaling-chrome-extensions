"""Foreground Python SCC overlay over verified captured repository metadata.

Sources stay in content.sqlite3. This catalog contains references, never copied
source payload or a new execution authority. Unmapped whole-source eligibility
produces a complete diagnostic catalog without a qualified graph claim.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import closing
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from automation_core import digest, load_json
import repo_archive_input as base
from repo_artifacts import (atomic_json, copy_file, file_proof, json_bytes,
                           outside, process_lock, safe_path, sync_dir)
import repo_context as repo
import repo_source as source

PLANNER = 'PYTHON_RAW_REFERENCE_GROUPS_V1'
RESOLVER = 'REPO_SOURCE_IMPORT_GRAPH_V1'
SOURCE_SCHEMA = 'occ.repo-logical-source.v1'
GROUP_SCHEMA = 'occ.repo-logical-group.v1'
PART_SCHEMA = 'occ.repo-group-part.v1'
TABLES = {'GROUP_HEADS.jsonl': 'heads', 'GROUP_MEMBERS.jsonl': 'members',
          'GROUP_PARTS.jsonl': 'segments', 'RELATIONS.jsonl': 'relations',
          'UNRESOLVED.jsonl': 'unresolved'}
DEFAULT_POLICY = {
    'schema': 'occ.repo-group-policy.v1', 'planner_version': PLANNER,
    'source_id_version': SOURCE_SCHEMA, 'raw_reference_bytes_per_segment': 4096,
    'reference_frame_bytes': 8192, 'max_refs_per_segment': 16,
    'python_roots': ['.'], 'include_heuristic_candidates_as_topology': False,
    'emit_related_references': True, 'total_source_cap': None,
    'total_group_cap': None, 'total_segment_cap': None,
    'resource_budget_policy': 'EXPLICIT_BLOCK_NO_TRUNCATION',
}
PAGE_ROWS = 100  # Navigation page size, never a corpus ceiling.


def boundary(event, **context):
    """Fault/visibility boundary used by process and disk qualification tests."""


class Resources:
    def __init__(self, value=None):
        value = value if value is not None else {'schema': 'occ.repo-group-resources.v1',
                          'graph_input_bytes': None, 'timeout_seconds': None}
        if (not isinstance(value, dict) or set(value) != {'schema', 'graph_input_bytes', 'timeout_seconds'}
                or value['schema'] != 'occ.repo-group-resources.v1'):
            raise ValueError('GROUP_RESOURCE_POLICY_INVALID')
        for field in ('graph_input_bytes', 'timeout_seconds'):
            if value[field] is not None and (type(value[field]) is not int or value[field] <= 0):
                raise ValueError('GROUP_RESOURCE_POLICY_INVALID')
        self.value, self.bytes, self.started = value, 0, time.monotonic()

    def check(self):
        timeout = self.value['timeout_seconds']
        if timeout is not None and time.monotonic() - self.started >= timeout:
            raise ValueError('GRAPH_RESOURCE_BUDGET')

    def add(self, value):
        self.check()
        self.bytes += len(json_bytes(value))
        if self.value['graph_input_bytes'] is not None and self.bytes > self.value['graph_input_bytes']:
            raise ValueError('GRAPH_RESOURCE_BUDGET')


def policy_view(value, profile):
    value = DEFAULT_POLICY | {'python_roots': profile['source_roots']} if value is None else value
    if not isinstance(value, dict) or set(value) != set(DEFAULT_POLICY):
        raise ValueError('GROUP_POLICY_INVALID')
    constants = {'schema', 'planner_version', 'source_id_version', 'include_heuristic_candidates_as_topology',
                 'total_source_cap', 'total_group_cap', 'total_segment_cap', 'resource_budget_policy'}
    if any(value[k] != DEFAULT_POLICY[k] or type(value[k]) is not type(DEFAULT_POLICY[k]) for k in constants):
        raise ValueError('GROUP_POLICY_INVALID')
    for key in ('raw_reference_bytes_per_segment', 'reference_frame_bytes', 'max_refs_per_segment'):
        if type(value[key]) is not int or value[key] <= 0:
            raise ValueError('GROUP_POLICY_INVALID')
    if type(value['emit_related_references']) is not bool:
        raise ValueError('GROUP_POLICY_INVALID')
    roots = value['python_roots']
    if (not isinstance(roots, list) or not roots or any(type(r) is not str for r in roots)
            or len(set(roots)) != len(roots) or set(roots) - set(profile['source_roots'])):
        raise ValueError('GROUP_ROOTS_OUTSIDE_PROFILE')
    return dict(value, python_roots=sorted(roots))


def source_id(namespace, alias, path):
    return digest({'schema': SOURCE_SCHEMA, 'namespace': namespace, 'repository': alias, 'path': path})


def group_id(members):
    return digest({'schema': GROUP_SCHEMA, 'planner_version': PLANNER, 'members': sorted(members)})


def unmapped_eligibility(entries):
    return {e['path']: {'file_sha256': e['file_sha256'], 'captured_state': e['state'],
                       'text_exportable': False, 'code_analysis_eligible': False,
                       'format_kind': 'UNKNOWN', 'reason': 'ELIGIBILITY_UNMAPPED',
                       'revision': None} for e in entries}


def eligibility_view(db, snap, entries, profile):
    """Explicit PR005 adapter boundary; no classifier or chunk UTF8 fallback."""
    try:
        import source_eligibility as owner
    except ModuleNotFoundError as exc:
        if exc.name != 'source_eligibility':
            raise
        return unmapped_eligibility(entries), {'schema': None, 'version': None,
                                              'state': 'PR005_ADAPTER_UNMAPPED'}
    result, projection_hash, pending = {}, hashlib.sha256(), 0
    with closing(db.execute('SELECT * FROM repo_entries WHERE snapshot_id=? ORDER BY path', (snap['id'],))) as rows:
        for row in rows:
            status = owner.facts_status(snap['id'], row)
            if status == 'CORRUPT':
                raise ValueError('ELIGIBILITY_BINDING_MISMATCH')
            facts = owner.project_facts(snap['id'], row)
            analysis = owner.analysis_object(row['analysis'])
            if status == 'SUPPORTED' and facts['parser'] != analysis.get('parser'):
                raise ValueError('ANALYSIS_REVISION_STALE')
            pending += status == 'PENDING'
            text = status == 'SUPPORTED' and facts['text_eligibility'] == 'ELIGIBLE'
            result[row['path']] = {'file_sha256': row['file_hash'], 'captured_state': row['state'],
                'text_exportable': text,
                'code_analysis_eligible': text and row['path'].endswith(('.py', '.pyi')) and facts['parser'] == 'PYTHON_AST',
                'format_kind': facts['format_kind'], 'reason': facts['reasons'][0] if facts['reasons'] else None,
                'revision': digest(facts)}
            projection_hash.update(json_bytes(facts))
    return result, {'schema': owner.SCHEMA, 'version': owner.CLASSIFIER_VERSION,
                    'state': 'MAPPED' if pending == 0 else 'PR005_FACTS_PENDING', 'pending_sources': pending,
                    'owner': 'source_eligibility.facts_status/project_facts',
                    'owner_build': file_proof(Path(owner.__file__).resolve())['sha256'],
                    'projection_digest': projection_hash.hexdigest()}


def read_eligibility_input(directory, entries, batch, profile, resources):
    """Read an explicit operator-normalized whole-source projection.

    Upstream schema/version/digest are provenance, not an assertion that an
    unobserved PR005 DTO is installed. No extension or per-chunk inference.
    """
    directory = safe_path(directory, directory=True)
    header = load_json(directory / 'ELIGIBILITY.json')
    if (not isinstance(header, dict) or set(header) != {'schema', 'binding', 'upstream', 'source_projection'}
            or header['schema'] != 'occ.repo-group-eligibility-input.v1'):
        raise ValueError('PR005_ADAPTER_UNMAPPED')
    expected = {k: batch['binding'][k] for k in ('snapshot_id', 'namespace', 'repository', 'profile_revision')}
    expected['base_batch_id'] = batch['batch_id']
    if header['binding'] != expected:
        raise ValueError('ELIGIBILITY_BINDING_MISMATCH')
    upstream = header['upstream']
    if (not isinstance(upstream, dict) or set(upstream) != {'schema', 'version', 'owner', 'projection_digest', 'proof_scope'}
            or any(type(upstream[k]) is not str or not upstream[k] for k in upstream)
            or upstream['proof_scope'] != 'WHOLE_SOURCE_CLASSIFICATION'
            or re.fullmatch('[0-9a-f]{64}', upstream['projection_digest']) is None):
        raise ValueError('PR005_ADAPTER_UNMAPPED')
    projection = header['source_projection']
    if (not isinstance(projection, dict) or set(projection) != {'path', 'bytes', 'sha256'}
            or projection['path'] != 'SOURCE_ELIGIBILITY.jsonl' or type(projection['bytes']) is not int
            or projection['bytes'] < 0 or type(projection['sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', projection['sha256']) is None):
        raise ValueError('PR005_ADAPTER_UNMAPPED')
    result, count, hasher = {}, 0, hashlib.sha256()
    keys = {'schema', 'path', 'file_sha256', 'captured_state', 'text_exportable',
            'code_analysis_eligible', 'format_kind', 'reason', 'revision'}
    with safe_path(directory / projection['path']).open('rb') as incoming:
        for raw in incoming:
            resources.check()
            count += len(raw)
            hasher.update(raw)
            row = json.loads(raw)
            if (not isinstance(row, dict) or set(row) != keys or row['schema'] != 'occ.repo-source-eligibility-adapter.v1'
                    or type(row['path']) is not str or row['path'] in result
                    or type(row['format_kind']) is not str
                    or row['reason'] is not None and type(row['reason']) is not str
                    or row['revision'] is not None and (type(row['revision']) is not str or re.fullmatch('[0-9a-f]{64}', row['revision']) is None)):
                raise ValueError('PR005_ADAPTER_UNMAPPED')
            result[row['path']] = {k: row[k] for k in keys - {'schema', 'path'}}
    if {'bytes': count, 'sha256': hasher.hexdigest()} != {k: projection[k] for k in ('bytes', 'sha256')}:
        raise ValueError('ELIGIBILITY_BINDING_MISMATCH')
    verify_eligibility(entries, result)
    return result, {'schema': header['schema'], 'version': 'NORMALIZED_OPERATOR_ADAPTER_V1',
                    'state': 'MAPPED', 'upstream': upstream, 'input_digest': digest(header)}


def verify_eligibility(entries, eligibility):
    if set(eligibility) != {e['path'] for e in entries}:
        raise ValueError('PR005_ADAPTER_UNMAPPED')
    for entry in entries:
        q = eligibility[entry['path']]
        if (q.get('file_sha256') != entry['file_sha256'] or q.get('captured_state') != entry['state']
                or type(q.get('text_exportable')) is not bool or type(q.get('code_analysis_eligible')) is not bool
                or q['code_analysis_eligible'] and (not q['text_exportable'] or entry['state'] != 'INDEXED'
                    or not entry['path'].endswith(('.py', '.pyi')))
                or q['text_exportable'] and entry['state'] != 'INDEXED'
                or q['code_analysis_eligible'] and (type(q.get('revision')) is not str
                    or re.fullmatch('[0-9a-f]{64}', q['revision']) is None)
                or q['text_exportable'] and q.get('format_kind') in {'BINARY_OR_NON_UTF8', 'LFS_POINTER',
                    'BINARY_CONTROL_HEURISTIC', 'NON_UTF8', 'LFS_POINTER_V1', 'LFS_POINTER_MALFORMED', 'LFS_POINTER_UNSUPPORTED'}):
            raise ValueError('ELIGIBILITY_BINDING_MISMATCH')


def saved_analysis(db, snap, entry, qualified):
    value = json.loads(db.execute('SELECT analysis FROM repo_entries WHERE snapshot_id=? AND path=?',
                                 (snap['id'], entry['path'])).fetchone()[0] or '{}')
    if not isinstance(value, dict):
        raise ValueError('ANALYSIS_REVISION_STALE')
    if qualified:
        if value.get('parser') != 'PYTHON_AST' or entry['size'] > repo.AST_WINDOW_BYTES:
            return value, False
        # Only already-qualified whole sources are checked against saved AST.
        # The existing bounded AST window applies; this is never chunk parsing.
        raw = bytearray()
        for chunk in db.execute('SELECT raw FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal',
                                (snap['id'], entry['path'])):
            raw.extend(chunk[0])
        expected, _ = source.analyze(entry['path'], bytes(raw))
        # Classification and other registered overlays share analysis JSON;
        # verify every actual parser field without treating overlays as AST.
        if expected != {k: value.get(k) for k in expected}:
            raise ValueError('ANALYSIS_REVISION_STALE')
    return value, qualified and value.get('parser') == 'PYTHON_AST'


def is_test(path):
    name = Path(path).name
    return name.startswith('test_') or name.endswith('_test.py') or name.endswith('_test.pyi')


def declared_view(value):
    value = value if value is not None else {'schema': 'occ.repo-declared-relations.v1', 'links': []}
    if (not isinstance(value, dict) or set(value) != {'schema', 'links'}
            or value['schema'] != 'occ.repo-declared-relations.v1' or not isinstance(value['links'], list)):
        raise ValueError('DECLARED_MAP_INVALID')
    for link in value['links']:
        if (not isinstance(link, dict) or set(link) != {'from', 'to', 'from_sha256', 'to_sha256', 'kind'}
                or link['kind'] != 'OPERATOR_DECLARED_CONTRACT'
                or any(type(link[k]) is not str for k in link)
                or any(re.fullmatch('[0-9a-f]{64}', link[k]) is None for k in ('from_sha256', 'to_sha256'))):
            raise ValueError('DECLARED_MAP_INVALID')
    links = sorted(value['links'], key=json_bytes)
    if len({digest(v) for v in links}) != len(links):
        raise ValueError('DECLARED_MAP_INVALID')
    return dict(value, links=links)


def plan_sources(entries, analyses, eligibility, scope, policy, declared=None, resources=None):
    """Deterministic pure static plan. All entry dispositions remain members."""
    resources = resources or Resources()
    verify_eligibility(entries, eligibility)
    declared = declared_view(declared)
    entries = sorted(entries, key=lambda e: e['path'])
    by_path = {e['path']: e for e in entries}
    if len(by_path) != len(entries):
        raise ValueError('GROUP_MEMBERSHIP_CORRUPT')
    ids = {p: source_id(scope['namespace'], scope['repository'], p) for p in by_path}
    capable = {p for p in by_path if eligibility[p]['code_analysis_eligible']
               and analyses[p].get('parser') == 'PYTHON_AST'}
    graph_rows = [{'path': p, 'analysis': json.dumps(analyses[p] if p in capable else {})} for p in by_path]
    for row in graph_rows:
        resources.add(row)
    edges, pending = source.import_graph(graph_rows, policy['python_roots'], progress=resources.check)
    accepted, relations, unresolved = [], {}, {}

    def gap(path, status, line=None, module=None):
        row = {'schema': 'occ.repo-group-unresolved.v1', 'path': path, 'source_id': ids.get(path),
               'file_sha256': by_path[path]['file_sha256'] if path in by_path else None,
               'status': status, 'line': line, 'module': module,
               'qualification_reason': eligibility[path].get('reason') if path in eligibility else None,
               'next_action': 'Review source qualification or static resolver; no guessed edge'}
        row['unresolved_id'] = digest(row)
        unresolved[row['unresolved_id']] = row

    def relation(a, b, kind, topology, line=None):
        row = {'schema': 'occ.repo-group-relation.v1', 'from_path': a, 'to_path': b,
               'from_source_id': ids[a], 'to_source_id': ids[b],
               'from_sha256': by_path[a]['file_sha256'], 'to_sha256': by_path[b]['file_sha256'],
               'relation_kind': kind, 'topology': topology, 'line': line,
               'anchor_kind': 'IMPORT_START_LINE_ONLY' if topology else 'DECLARED_MAP_FILE' if kind == 'OPERATOR_DECLARED_CONTRACT' else 'FILENAME_ONLY',
               'rule_version': RESOLVER if topology else 'DECLARED_HASH_BINDING_V1' if kind == 'OPERATOR_DECLARED_CONTRACT' else 'TEST_FILENAME_V1',
               'evidence_class': 'STATIC_LOCAL' if topology else 'OPERATOR_DECLARED' if kind == 'OPERATOR_DECLARED_CONTRACT' else 'HEURISTIC',
               'observed_test_coverage': 'NOT_MEASURED', 'capability_status': 'NOT_QUALIFIED'}
        row['relation_id'] = digest(row)
        relations[row['relation_id']] = row

    for edge in sorted(edges, key=json_bytes):
        if edge['from'] in capable and edge['to'] in capable:
            accepted.append(edge)
            relation(edge['from'], edge['to'], 'STATIC_TEST_IMPORT' if is_test(edge['from']) else 'PYTHON_STATIC_IMPORT', True, edge['line'])
        else:
            gap(edge['from'], 'TARGET_INELIGIBLE', edge['line'], edge['to'])
    for item in pending:
        gap(item['from'], item['status'], item.get('line'), item.get('module'))
    for path, entry in by_path.items():
        if path not in capable:
            q = eligibility[path]
            status = q.get('reason') or analyses[path].get('parser') or 'SOURCE_CODE_INELIGIBLE'
            if path.endswith(('.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx')):
                status = 'JS_DEPENDENCIES_NOT_PARSED'
            elif path.endswith(('.py', '.pyi')) and q['code_analysis_eligible']:
                status = 'ANALYSIS_UNQUALIFIED'
            elif path.endswith(('.py', '.pyi')) and q.get('format_kind', '').startswith('LFS_POINTER'):
                status = 'LFS_POINTER_NOT_CODE'
            elif path.endswith(('.py', '.pyi')) and q.get('format_kind') in {'BINARY_OR_NON_UTF8', 'BINARY_CONTROL_HEURISTIC', 'NON_UTF8'}:
                status = 'SOURCE_CODE_INELIGIBLE'
            gap(path, status)
    if policy['emit_related_references']:
        tests = defaultdict(list)
        for path in by_path:
            if is_test(path):
                tests[Path(path).name].append(path)
        for path, entry in by_path.items():
            if is_test(path) or entry['state'] != 'INDEXED' or not path.endswith(('.py', '.pyi')):
                continue
            for test in tests.get('test_' + Path(path).name, []):
                if by_path[test]['state'] == 'INDEXED':
                    relation(path, test, 'HEURISTIC_TEST_CANDIDATE', False)
        for link in declared['links']:
            a, b = link['from'], link['to']
            if a not in by_path or b not in by_path or by_path[a]['state'] != 'INDEXED' or by_path[b]['state'] != 'INDEXED':
                gap(a, 'DECLARED_TARGET_UNAVAILABLE', module=b)
            elif by_path[a]['file_sha256'] != link['from_sha256'] or by_path[b]['file_sha256'] != link['to_sha256']:
                gap(a, 'DECLARED_MAPPING_STALE', module=b)
            else:
                relation(a, b, 'OPERATOR_DECLARED_CONTRACT', False)
    for row in relations.values():
        resources.add(row)
    for row in unresolved.values():
        resources.add(row)
    components = source.components(sorted(capable), accepted, progress=resources.check)
    components.extend([p] for p in by_path if p not in capable)
    groups, membership = {}, {}
    policy_hash = digest(policy)
    relation_rows = sorted(relations.values(), key=lambda v: v['relation_id'])
    unresolved_rows = sorted(unresolved.values(), key=lambda v: v['unresolved_id'])
    # Index neighbourhoods once; avoid a groups × edges scan on large trees.
    touching, missing = defaultdict(dict), defaultdict(list)
    for row in relation_rows:
        touching[row['from_path']][row['relation_id']] = row
        touching[row['to_path']][row['relation_id']] = row
    for row in unresolved_rows:
        missing[row['path']].append(row)
    for paths in components:
        resources.check()
        member_ids = sorted(ids[p] for p in paths)
        gid = group_id(member_ids)
        nearby = {}
        for path in paths:
            nearby.update(touching[path])
        revision = digest({'group_id': gid,
            'members': [{'source_id': ids[p], 'file_sha256': by_path[p]['file_sha256'],
                         'eligibility': eligibility[p]} for p in sorted(paths)],
            'relations': [nearby[k] for k in sorted(nearby)],
            'unresolved': sorted([v for p in paths for v in missing[p]], key=lambda v: v['unresolved_id']),
            'policy_digest': policy_hash, 'resolver_version': RESOLVER})
        groups[gid] = {'schema': 'occ.repo-group-head.v1', 'group_id': gid,
            'group_revision': revision, 'kind': 'PYTHON_STATIC_SCC' if len(paths) > 1 else 'PYTHON_SINGLETON' if paths[0] in capable else 'METADATA_SINGLETON',
            'reason': 'QUALIFIED_STATIC_PYTHON_SCOPE' if paths[0] in capable else eligibility[paths[0]].get('reason') or analyses[paths[0]].get('parser') or 'SOURCE_CODE_INELIGIBLE',
            'owner': {'status': 'UNSPECIFIED'}, 'member_count': len(paths),
            'raw_part_count': sum(by_path[p]['chunk_count'] for p in paths), 'segment_count': 0,
            'members_locator': {'group_id': gid}, 'relations_locator': {'group_id': gid}}
        for path in sorted(paths):
            entry, q = by_path[path], eligibility[path]
            membership[path] = {'schema': 'occ.repo-group-member.v1', 'snapshot_id': scope['snapshot_id'],
                'source_id': ids[path], 'group_id': gid, 'path': path,
                'entry_ordinal': entry['ordinal'], 'file_sha256': entry['file_sha256'],
                'state': entry['state'], 'raw_part_count': entry['chunk_count'],
                'text_exportable': q['text_exportable'], 'code_analysis_eligible': path in capable,
                'format_kind': q.get('format_kind'), 'reason': q.get('reason')}
    return {'groups': groups, 'members': membership, 'relations': relation_rows,
            'unresolved': unresolved_rows, 'capable': capable}


def raw_ref(part, member):
    return {'source_id': member['source_id'], 'part_id': part['part_id'],
            'chunk_ordinal': part['chunk_ordinal'],
            'logical_id': part['logical_id'], 'revision': part['revision'],
            'source_start': part['source_start'], 'source_end': part['source_end'],
            'bytes': part['bytes'], 'sha256': part['sha256'],
            'file_sha256': part['file_sha256'],
            'text_eligible': member['text_exportable'] and part['text_eligible']}


def segment(gid, refs, policy_hash, batch_id, ordinal, previous=None, following=None):
    logical = digest({'schema': PART_SCHEMA, 'group_id': gid,
                      'chunk_logical_ids': [r['logical_id'] for r in refs], 'policy_digest': policy_hash})
    row = {'schema': PART_SCHEMA, 'group_id': gid, 'group_part_id': logical,
           'ordinal': ordinal, 'previous': previous, 'next': following,
           'raw_reference_bytes': sum(r['bytes'] for r in refs), 'raw_refs': refs,
           'related_locator': {'group_id': gid}, 'payload_is_reference_only': True}
    row['revision'] = digest({'group_part_id': logical, 'base_batch_id': batch_id,
                              'raw_refs': refs, 'previous': previous, 'next': following})
    return row


def segments(gid, references, policy, batch_id, resources):
    policy_hash, refs, ordinal = digest(policy), [], 0
    previous, pending = None, None

    def reserve(values, n):
        return segment(gid, values, policy_hash, batch_id, n, '0' * 64, '0' * 64)

    def complete(values, n):
        return segment(gid, values, policy_hash, batch_id, n)

    try:
        for ref in references:
            resources.check()
            if ref['bytes'] > policy['raw_reference_bytes_per_segment']:
                raise ValueError('PART_BUDGET_TOO_SMALL')
            candidate = reserve([*refs, ref], ordinal)
            overflow = (len(candidate['raw_refs']) > policy['max_refs_per_segment']
                        or candidate['raw_reference_bytes'] > policy['raw_reference_bytes_per_segment']
                        or len(json_bytes(candidate)) > policy['reference_frame_bytes'])
            if refs and overflow:
                current = complete(refs, ordinal)
                if pending is not None:
                    yield segment(gid, pending['raw_refs'], policy_hash, batch_id, pending['ordinal'], previous, current['group_part_id'])
                    previous = pending['group_part_id']
                pending, refs, ordinal = current, [], ordinal + 1
            if len(json_bytes(reserve([ref], ordinal))) > policy['reference_frame_bytes']:
                raise ValueError('REFERENCE_ROW_TOO_LARGE')
            refs.append(ref)
        if refs:
            current = complete(refs, ordinal)
            if pending is not None:
                yield segment(gid, pending['raw_refs'], policy_hash, batch_id, pending['ordinal'], previous, current['group_part_id'])
                previous = pending['group_part_id']
            yield segment(gid, refs, policy_hash, batch_id, ordinal, previous, None)

    finally:
        getattr(references, "close", lambda: None)()


def plan_database(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript('''PRAGMA cache_size=-2048; PRAGMA temp_store=FILE;
        CREATE TABLE heads(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE members(id TEXT PRIMARY KEY,path TEXT UNIQUE,group_id TEXT,payload TEXT NOT NULL);
        CREATE INDEX member_group ON members(group_id,path);
        CREATE TABLE segments(id TEXT PRIMARY KEY,group_id TEXT,ordinal INTEGER,payload TEXT NOT NULL,UNIQUE(group_id,ordinal));
        CREATE TABLE refs(part_id TEXT PRIMARY KEY,source_id TEXT,segment_id TEXT,chunk_ordinal INTEGER,payload TEXT NOT NULL,UNIQUE(source_id,chunk_ordinal));
        CREATE INDEX ref_source ON refs(source_id,chunk_ordinal);
        CREATE TABLE relations(id TEXT PRIMARY KEY,from_id TEXT,to_id TEXT,payload TEXT NOT NULL);
        CREATE INDEX relation_from ON relations(from_id); CREATE INDEX relation_to ON relations(to_id);
        CREATE TABLE unresolved(id TEXT PRIMARY KEY,source_id TEXT,payload TEXT NOT NULL);
        CREATE INDEX unresolved_source ON unresolved(source_id);''')
    return db


def reference_rows(db, snap, entry, member):
    if entry['state'] != 'INDEXED':
        return
    with closing(db.execute('SELECT * FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal',
                            (snap['id'], entry['path']))) as chunks:
        for chunk in chunks:
            yield raw_ref(base.owner.part_record(db, snap,
                {'ordinal': entry['ordinal'], 'path': entry['path'], 'size': entry['size'], 'file_hash': entry['file_sha256']}, chunk), member)


def fill_plan(target, db, snap, entries, plan, policy, batch, resources):
    by_path = {e['path']: e for e in entries}
    grouped = defaultdict(list)
    for path, member in sorted(plan['members'].items()):
        target.execute('INSERT INTO members VALUES (?,?,?,?)',
                       (member['source_id'], path, member['group_id'], json_bytes(member).decode()))
        grouped[member['group_id']].append(path)
    for row in plan['relations']:
        target.execute('INSERT INTO relations VALUES (?,?,?,?)', (row['relation_id'], row['from_source_id'], row['to_source_id'], json_bytes(row).decode()))
    for row in plan['unresolved']:
        target.execute('INSERT INTO unresolved VALUES (?,?,?)', (row['unresolved_id'], row['source_id'], json_bytes(row).decode()))
    for gid, paths in sorted(grouped.items()):
        def references():
            for path in sorted(paths):
                yield from reference_rows(db, snap, by_path[path], plan['members'][path])
        count = 0
        for row in segments(gid, references(), policy, batch['batch_id'], resources):
            target.execute('INSERT INTO segments VALUES (?,?,?,?)', (row['group_part_id'], gid, row['ordinal'], json_bytes(row).decode()))
            for ref in row['raw_refs']:
                target.execute('INSERT INTO refs VALUES (?,?,?,?,?)', (ref['part_id'], ref['source_id'], row['group_part_id'], ref['chunk_ordinal'], json_bytes(ref).decode()))
            count += 1
        head = dict(plan['groups'][gid], segment_count=count)
        target.execute('INSERT INTO heads VALUES (?,?)', (gid, json_bytes(head).decode()))
    target.commit()


def verify_plan(target, db, snap, entries, plan, policy, batch, resources):
    """Independent readback against every authoritative entry and raw part."""
    if target.execute('SELECT count(*) FROM members').fetchone()[0] != len(entries):
        raise ValueError('GROUP_MEMBERSHIP_CORRUPT')
    if target.execute('SELECT count(*) FROM heads').fetchone()[0] != len(plan['groups']):
        raise ValueError('GROUP_MEMBERSHIP_CORRUPT')
    for table in ('relations', 'unresolved'):
        with closing(table_rows(target, table)) as rows:
            for expected in plan[table]:
                if next(rows, None) != expected:
                    raise ValueError('GROUP_RELATION_CORRUPT')
            if next(rows, None) is not None:
                raise ValueError('GROUP_RELATION_CORRUPT')
    parts = raw_bytes = text_parts = 0
    for entry in entries:
        resources.check()
        member = target.execute('SELECT payload FROM members WHERE path=?', (entry['path'],)).fetchone()
        if member is None or json.loads(member[0]) != plan['members'][entry['path']]:
            raise ValueError('GROUP_MEMBERSHIP_CORRUPT')
        for ref in reference_rows(db, snap, entry, json.loads(member[0])):
            saved = target.execute('SELECT payload,segment_id FROM refs WHERE part_id=?', (ref['part_id'],)).fetchone()
            if saved is None or json.loads(saved[0]) != ref:
                raise ValueError('RAW_REFERENCE_CORRUPT')
            row = json.loads(target.execute('SELECT payload FROM segments WHERE id=?', (saved[1],)).fetchone()[0])
            if ref not in row['raw_refs'] or row['group_id'] != plan['members'][entry['path']]['group_id']:
                raise ValueError('RAW_REFERENCE_CORRUPT')
            parts += 1
            raw_bytes += ref['bytes']
            text_parts += int(ref['text_eligible'])
    if target.execute('SELECT count(*) FROM refs').fetchone()[0] != parts or parts != batch['part_count']:
        raise ValueError('RAW_REFERENCE_CORRUPT')
    segment_count = 0
    for head in target.execute('SELECT id,payload FROM heads ORDER BY id'):
        gid, value = head[0], json.loads(head[1])
        members = [r[0] for r in target.execute('SELECT id FROM members WHERE group_id=? ORDER BY id', (gid,))]
        if (gid != group_id(members) or gid not in plan['groups'] or value['member_count'] != len(members)
                or value != dict(plan['groups'][gid], segment_count=value['segment_count'])):
            raise ValueError('GROUP_MEMBERSHIP_CORRUPT')
        previous, count, ref_count = None, 0, 0
        with closing(target.execute('SELECT id,payload FROM segments WHERE group_id=? ORDER BY ordinal', (gid,))) as cursor:
            current = next(cursor, None)
            while current is not None:
                resources.check()
                following = next(cursor, None)
                row = json.loads(current[1])
                expected = segment(gid, row['raw_refs'], digest(policy), batch['batch_id'], count, previous, following[0] if following else None)
                if (row != expected or len(json_bytes(row)) > policy['reference_frame_bytes']
                        or row['raw_reference_bytes'] > policy['raw_reference_bytes_per_segment']
                        or not row['raw_refs'] or len(row['raw_refs']) > policy['max_refs_per_segment']):
                    raise ValueError('RAW_REFERENCE_CORRUPT')
                for ref in row['raw_refs']:
                    stored = target.execute('SELECT payload,segment_id FROM refs WHERE part_id=?', (ref['part_id'],)).fetchone()
                    if stored is None or json.loads(stored[0]) != ref or stored[1] != current[0]:
                        raise ValueError('RAW_REFERENCE_CORRUPT')
                ref_count += len(row['raw_refs'])
                previous, current, count = current[0], following, count + 1
        if value['segment_count'] != count or value['raw_part_count'] != ref_count:
            raise ValueError('RAW_REFERENCE_CORRUPT')
        segment_count += count
    if target.execute('SELECT count(*) FROM segments').fetchone()[0] != segment_count:
        raise ValueError('RAW_REFERENCE_CORRUPT')
    return {'entry_count': len(entries), 'group_count': len(plan['groups']), 'segment_count': segment_count,
            'captured_part_count': parts, 'unique_raw_reference_bytes': raw_bytes,
            'text_eligible_reference_count': text_parts, 'all_entries_grouped': True,
            'all_captured_parts_referenced': True}


def table_rows(db, table):
    order = 'group_id,path' if table == 'members' else 'group_id,ordinal' if table == 'segments' else 'id'
    with closing(db.execute('SELECT payload FROM ' + table + ' ORDER BY ' + order)) as rows:
        for row in rows:
            yield json.loads(row[0])


def write_jsonl(path, rows, resources):
    with closing(rows), path.open('xb') as stream:
        for row in rows:
            resources.check()
            stream.write(json_bytes(row))
        stream.flush()
        os.fsync(stream.fileno())


def page_name(kind, identity, page):
    return f'{kind}_{identity}_{page:08d}.html'


def link(path, label):
    return '<a href="' + html.escape(path, quote=True) + '">' + html.escape(str(label)) + '</a>'


def write_navigation(stage, target, resources):
    directory = stage / 'navigation'
    directory.mkdir()
    with (stage / 'NAVIGATION.jsonl').open('xb') as proofs:
        def write(path, title, body):
            resources.check()
            value = ('<!doctype html><html lang="en"><meta charset="utf-8">'
                     '<meta name="viewport" content="width=device-width">'
                     '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
                     '<title>' + html.escape(title) + '</title><body><h1>' + html.escape(title) + '</h1>'
                     '<p>Captured references · static analysis · test coverage NOT_MEASURED · AI read UNKNOWN</p>'
                     + body + '</body></html>').encode()
            with path.open('xb') as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            proofs.write(json_bytes({'path': path.relative_to(stage).as_posix(), **file_proof(path)}))

        def pages(kind, identity, title, rows, render, parent='../INDEX.html'):
            try:
                iterator, pending, page = iter(rows), [], 0
                # One row lookahead retains bounded navigation pages to EOF.
                current = next(iterator, None)
                while current is not None or page == 0:
                    pending = []
                    while current is not None and len(pending) < PAGE_ROWS:
                        pending.append(render(current))
                        current = next(iterator, None)
                    links = [link(parent, 'Home')]
                    if page:
                        links.append(link(page_name(kind, identity, page - 1), 'Previous'))
                    if current is not None:
                        links.append(link(page_name(kind, identity, page + 1), 'Next'))
                    write(directory / page_name(kind, identity, page), title,
                          '<p>' + ' · '.join(links) + '</p><ul>' + ''.join('<li>' + r + '</li>' for r in pending) + '</ul>')
                    page += 1
                    if current is None:
                        break

            finally:
                getattr(rows, "close", lambda: None)()

        pages('catalog', 'groups', 'Python and metadata groups', table_rows(target, 'heads'),
              lambda r: link(page_name('group', r['group_id'], 0), r['group_id'] + ' · ' + r['kind']))
        write(stage / 'INDEX.html', 'Repository group catalog', '<p>' + link('navigation/' + page_name('catalog', 'groups', 0), 'Browse all groups') + '</p>')
        for head in table_rows(target, 'heads'):
            gid = head['group_id']
            def group_rows():
                queries = [
                    ('source', 'SELECT payload FROM members WHERE group_id=? ORDER BY path'),
                    ('segment', 'SELECT payload FROM segments WHERE group_id=? ORDER BY ordinal'),
                    ('relation', '''SELECT DISTINCT r.payload FROM relations r JOIN members m
                        ON r.from_id=m.id OR r.to_id=m.id WHERE m.group_id=? ORDER BY r.id'''),
                    ('gap', '''SELECT u.payload FROM unresolved u JOIN members m
                        ON u.source_id=m.id WHERE m.group_id=? ORDER BY u.id''')]
                for kind, query in queries:
                    with closing(target.execute(query, (gid,))) as cursor:
                        for r in cursor:
                            yield {'kind': kind, 'value': json.loads(r[0])}
            def display(row):
                r = row['value']
                if row['kind'] == 'source':
                    return link(page_name('source', r['source_id'], 0), r['path'])
                if row['kind'] == 'segment':
                    return link(page_name('segment', r['group_part_id'], 0), 'Segment ' + str(r['ordinal']))
                if row['kind'] == 'relation':
                    return html.escape(r['relation_kind']) + ': ' + link(page_name('source', r['from_source_id'], 0), r['from_path']) + ' → ' + link(page_name('source', r['to_source_id'], 0), r['to_path'])
                return html.escape(r['status'] + ': ' + str(r.get('module') or r['path']))
            pages('group', gid, head['kind'] + ' · ' + gid, group_rows(), display)
        for member in table_rows(target, 'members'):
            sid, gid = member['source_id'], member['group_id']
            def source_rows():
                with closing(target.execute('SELECT part_id,segment_id,chunk_ordinal FROM refs WHERE source_id=? ORDER BY chunk_ordinal', (sid,))) as cursor:
                    for r in cursor:
                        yield dict(r)
            pages('source', sid, member['path'] + ' · ' + member['state'], source_rows(),
                  lambda r: link(page_name('segment', r['segment_id'], 0), 'Part ' + str(r['chunk_ordinal']) + ' · ' + r['part_id']),
                  page_name('group', gid, 0))
        for row in table_rows(target, 'segments'):
            body = '<p>' + link(page_name('group', row['group_id'], 0), 'Group') + '</p><p>'
            if row['previous']:
                body += link(page_name('segment', row['previous'], 0), 'Previous') + ' · '
            if row['next']:
                body += link(page_name('segment', row['next'], 0), 'Next')
            body += '</p><ul>'
            for ref in row['raw_refs']:
                member = json.loads(target.execute('SELECT payload FROM members WHERE id=?', (ref['source_id'],)).fetchone()[0])
                body += '<li>' + link(page_name('source', ref['source_id'], 0), member['path']) + ' [' + str(ref['source_start']) + ',' + str(ref['source_end']) + ') · ' + html.escape(ref['part_id']) + ' · text eligible: ' + str(ref['text_eligible']) + '</li>'
            write(directory / page_name('segment', row['group_part_id'], 0), 'Reference segment ' + str(row['ordinal']), body + '</ul>')
        proofs.flush()
        os.fsync(proofs.fileno())


def verify_files(stage, target, resources):
    for name, table in TABLES.items():
        with (stage / name).open('rb') as incoming:
            for row in table_rows(target, table):
                resources.check()
                if incoming.readline() != json_bytes(row):
                    raise ValueError('GROUP_CATALOG_CORRUPT')
            if incoming.read(1):
                raise ValueError('GROUP_CATALOG_CORRUPT')
    verify_navigation(stage, resources)


def verify_navigation(stage, resources):
    with (stage / 'NAVIGATION.jsonl').open('rb') as incoming:
        for raw in incoming:
            resources.check()
            row = json.loads(raw)
            path = stage / row['path']
            if path.resolve().is_relative_to(stage.resolve()) is False or file_proof(path) != {'bytes': row['bytes'], 'sha256': row['sha256']}:
                raise ValueError('GROUP_NAVIGATION_CORRUPT')


def verify_output_proofs(stage, outputs, resources):
    for item in outputs:
        resources.check()
        if file_proof(stage / item['path']) != {'bytes': item['bytes'], 'sha256': item['sha256']}:
            raise ValueError('GROUP_CATALOG_CORRUPT')
    verify_navigation(stage, resources)


def publish(profile_path, alias, manifest, output, *, policy=None, declared=None, resources=None, eligibility_input=None):
    budget = Resources(resources)
    store, profile = base.operator_scope(profile_path, alias)
    manifest = safe_path(manifest, directory=True)
    if eligibility_input is not None:
        eligibility_input = safe_path(eligibility_input, directory=True)
    output = outside(output, store, profile['root'], manifest, *([eligibility_input] if eligibility_input is not None else []))
    chosen = policy_view(policy, profile)
    declared = declared_view(declared)
    batch_input = load_json(manifest / 'BATCH.json')
    sid = batch_input.get('binding', {}).get('snapshot_id')
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.parent / ('.occ-group-lock-' + digest(str(output)))
    stage = None
    with process_lock(lock):
        try:
            stage = Path(tempfile.mkdtemp(prefix='.occ-groups-', dir=output.parent))
            with base.snapshot_view(store, profile, alias, sid) as (db, snap):
                batch = base.verify_manifest(db, snap, profile, manifest)
                entries = list(base.entry_rows(db, snap))
                if eligibility_input is None:
                    qualifications, adapter = eligibility_view(db, snap, entries, profile)
                else:
                    qualifications, adapter = read_eligibility_input(eligibility_input, entries, batch, profile, budget)
                verify_eligibility(entries, qualifications)
                analyses, analysis_hash, eligibility_hash = {}, hashlib.sha256(), hashlib.sha256()
                for entry in sorted(entries, key=lambda v: v['path']):
                    budget.add(entry)
                    q = qualifications[entry['path']]
                    saved, qualified = saved_analysis(db, snap, entry, q['code_analysis_eligible'])
                    analyses[entry['path']] = saved
                    q = dict(q, code_analysis_eligible=qualified)
                    qualifications[entry['path']] = q
                    analysis_hash.update(json_bytes({'path': entry['path'], 'file_sha256': entry['file_sha256'], 'analysis': saved}))
                    eligibility_hash.update(json_bytes({'path': entry['path'], **q}))
                binding = {'schema': 'occ.repo-group-batch-binding.v1',
                    'base_batch_id': batch['batch_id'], 'snapshot_id': sid,
                    'namespace': profile['namespace'], 'repository': alias,
                    'profile_revision': batch['binding']['profile_revision'],
                    'eligibility_digest': eligibility_hash.hexdigest(), 'eligibility_adapter': adapter,
                    'analysis_digest': analysis_hash.hexdigest(), 'roots': chosen['python_roots'],
                    'planner_version': PLANNER, 'resolver_version': RESOLVER,
                    'planner_build': file_proof(Path(__file__).resolve())['sha256'],
                    'parser_version': {'source_sha256': file_proof(Path(source.__file__).resolve())['sha256'],
                                       'python': list(sys.version_info[:2]), 'ast_window_bytes': repo.AST_WINDOW_BYTES},
                    'declared_map_digest': digest(declared), 'policy_digest': digest(chosen),
                    'resource_policy': budget.value}
                scope = {'namespace': profile['namespace'], 'repository': alias, 'snapshot_id': sid}
                plan = plan_sources(entries, analyses, qualifications, scope, chosen, declared, budget)
                plan_path = stage / '.plan.sqlite3'
                with closing(plan_database(plan_path)) as target:
                    fill_plan(target, db, snap, entries, plan, chosen, batch, budget)
                    boundary('plan_written', stage=stage, plan=target)
                    proof = verify_plan(target, db, snap, entries, plan, chosen, batch, budget)
                    for name, table in TABLES.items():
                        write_jsonl(stage / name, table_rows(target, table), budget)
                    write_jsonl(stage / 'ELIGIBILITY_VIEW.jsonl',
                        ({'path': p, **qualifications[p]} for p in sorted(qualifications)), budget)
                    if file_proof(stage / 'ELIGIBILITY_VIEW.jsonl')['sha256'] != binding['eligibility_digest']:
                        raise ValueError('ELIGIBILITY_BINDING_MISMATCH')
                    write_navigation(stage, target, budget)
                    boundary('artifacts_written', stage=stage, plan=target)
                    verify_files(stage, target, budget)
                plan_path.unlink()
                coverage = {'schema': 'occ.repo-group-coverage.v1', 'status': 'PASS',
                    'proof_scope': 'ALL_CAPTURED_PART_REFERENCES_WITH_VERIFIED_BASE_BYTES', **proof,
                    'gap_count': batch['gap_count'], 'all_tracked_bytes_exportable': batch['all_tracked_bytes_exportable'],
                    'graph_scope': 'PYTHON_STATIC_ONLY_WITH_EXPLICIT_UNRESOLVED' if adapter['state'] == 'MAPPED' else 'BLOCKED_ELIGIBILITY_UNMAPPED',
                    'qualified_python_sources': len(plan['capable']),
                    'ai_delivery': 'NOT_PERFORMED', 'ai_read': 'UNKNOWN',
                    'observed_test_coverage': 'NOT_MEASURED', 'usefulness_trial': 'NOT_RUN', 'installed_device': 'NOT_RUN'}
                atomic_json(stage / 'COVERAGE.json', coverage)
                atomic_json(stage / 'POLICY.json', chosen)
                for name in base.METADATA:
                    copy_file(manifest / name, stage / name, progress=budget.check)
                    if file_proof(stage / name) != file_proof(manifest / name):
                        raise ValueError('MANIFEST_UNVERIFIED')
                # Detect input changes between initial proof and the final copy.
                base.verify_manifest(db, snap, profile, stage)
                outputs = [{ 'path': name, **file_proof(stage / name)} for name in
                           (*TABLES, 'ELIGIBILITY_VIEW.jsonl', 'COVERAGE.json', 'POLICY.json', 'NAVIGATION.jsonl', *base.METADATA)]
                counts = {'entries': proof['entry_count'], 'groups': proof['group_count'],
                          'segments': proof['segment_count'], 'parts': proof['captured_part_count'],
                          'relations': len(plan['relations']), 'unresolved': len(plan['unresolved'])}
                header = {'schema': 'occ.repo-groups.v1', 'grouping_batch_id': digest(binding),
                          'binding': binding, 'counts': counts, 'status': 'PASS',
                          'graph_scope': coverage['graph_scope'], 'outputs': outputs,
                          'proof_scope': coverage['proof_scope'], 'authority': 'DATA_ONLY', 'execution_authorized': False}
                budget.check()
                boundary('before_header', stage=stage)
                verify_output_proofs(stage, outputs, budget)
                atomic_json(stage / 'GROUPS.json', header)
                sync_dir(stage)
            reused = output.exists()
            if reused:
                if file_proof(output / 'GROUPS.json') != file_proof(stage / 'GROUPS.json'):
                    raise ValueError('GROUP_OUTPUT_CONFLICT')
                for item in outputs:
                    if file_proof(output / item['path']) != {'bytes': item['bytes'], 'sha256': item['sha256']}:
                        raise ValueError('GROUP_CATALOG_CORRUPT')
                with (stage / 'NAVIGATION.jsonl').open() as incoming:
                    for line in incoming:
                        item = json.loads(line)
                        if file_proof(output / item['path']) != {'bytes': item['bytes'], 'sha256': item['sha256']}:
                            raise ValueError('GROUP_NAVIGATION_CORRUPT')
            else:
                boundary('before_publish', stage=stage)
                verify_output_proofs(stage, outputs, budget)
                if (stage / 'GROUPS.json').read_bytes() != json_bytes(header):
                    raise ValueError('GROUP_CATALOG_CORRUPT')
                stage.rename(output)
                sync_dir(output.parent)
            return {'schema': 'occ.repo-group-receipt.v1', 'state': 'READY',
                    'grouping_batch_id': header['grouping_batch_id'], 'base_batch_id': batch['batch_id'],
                    'counts': counts, 'raw_reference_complete': True, 'graph_scope': coverage['graph_scope'],
                    'reused': reused, 'ai_delivery': 'NOT_PERFORMED'}
        except MemoryError as exc:
            raise ValueError('GRAPH_RESOURCE_BUDGET') from exc
        finally:
            if stage is not None and stage.exists():
                shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--policy', type=Path)
    parser.add_argument('--declared-map', type=Path)
    parser.add_argument('--resources', type=Path)
    parser.add_argument('--eligibility', type=Path, help='Explicit whole-source adapter directory; absent/unmapped means diagnostic catalog')
    args = parser.parse_args(argv)
    try:
        optional = {}
        for field in ('policy', 'declared_map', 'resources'):
            path = getattr(args, field)
            if path is not None:
                optional['declared' if field == 'declared_map' else field] = load_json(safe_path(path),
                    limit=sys.maxsize if field == 'declared_map' else 2_200_000)
        result = publish(args.profile, args.repository, args.manifest, args.output, eligibility_input=args.eligibility, **optional)
        print(json.dumps(result, separators=(',', ':')))
        return 0
    except KeyboardInterrupt:
        reason = 'CANCEL_REQUESTED'
    except OSError as exc:
        import errno
        reason = 'GROUP_DISK_FULL' if exc.errno in {errno.ENOSPC, errno.EDQUOT} else 'GROUP_IO_FAILED'
    except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        reason = str(exc) if re.fullmatch('[A-Z_]{1,100}', str(exc)) else 'GROUP_OPERATION_FAILED'
    print(json.dumps({'schema': 'occ.repo-group-receipt.v1', 'state': 'FAILED', 'reason': reason}, separators=(',', ':')))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
