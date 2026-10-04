"""Real SQLite/CLI and independently labelled SCC/continuation qualification."""
import errno
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from automation_core import digest
import repo_archive_input as base
from repo_artifacts import file_proof, json_bytes
import repo_context as repo
import repo_groups as groups

LAB = Path(groups.__file__).parent
FIXTURE = LAB / 'fixtures' / 'pr006'


def jsonl(path):
    with Path(path).open() as incoming:
        return [json.loads(line) for line in incoming]


def reachability_components(paths, edges):
    """Independent mutual reachability; never calls the application's SCC."""
    adjacent = {p: set() for p in paths}
    for edge in edges:
        adjacent[edge['from_path']].add(edge['to_path'])
    def reachable(start):
        seen, pending = {start}, [start]
        while pending:
            for child in adjacent[pending.pop()] - seen:
                seen.add(child)
                pending.append(child)
        return seen
    reach = {p: reachable(p) for p in paths}
    todo, result = set(paths), []
    while todo:
        path = min(todo)
        component = {p for p in todo if path in reach[p] and p in reach[path]}
        result.append(sorted(component))
        todo -= component
    return sorted(result)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.active, self.text = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'href' in attrs:
            self.links.append(attrs['href'])
        if tag in {'script', 'iframe', 'img', 'tag'} or any(k.startswith('on') for k in attrs):
            self.active.append(tag)

    def handle_data(self, data):
        self.text.append(data)


class GroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.root = cls.work / 'source'
        cls.root.mkdir()
        cls.profile = {'root': str(cls.root), 'namespace': 'code',
                       'source_roots': ['.', 'libA', 'libB'],
                       'exclusions': ['operator-excluded.txt', 'oversize.dat']}
        cls.fixture_entries = jsonl(FIXTURE / 'REPO_MANIFEST.jsonl')
        cls.oracle = json.loads((FIXTURE / 'EXPECTED_ORACLE.json').read_text())
        cls.fixture_eligibility = {r['path']: r for r in jsonl(FIXTURE / 'SOURCE_ELIGIBILITY.jsonl')}
        env = repo.git_environment() | {'GIT_AUTHOR_NAME': 'Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@invalid',
                    'GIT_COMMITTER_NAME': 'Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@invalid'}
        def git(*args, data=None):
            return subprocess.run(['git', '-C', str(cls.root), *args], input=data, env=env,
                                  capture_output=True, check=True).stdout.strip()
        cls.git = staticmethod(git)
        git('init', '-q')
        tree = {}
        cls.raw_sources = {}
        for entry in cls.fixture_entries:
            path = FIXTURE / 'raw' / ('source_%03d.bin' % entry['ordinal'])
            raw = path.read_bytes() if path.is_file() else b'metadata'
            if entry['git_type'] == 'commit':
                kind, oid = 'commit', b'1' * 40
            else:
                kind, oid = 'blob', git('hash-object', '-w', '--stdin', data=raw)
            if entry['state'] == 'INDEXED':
                cls.raw_sources[entry['path']] = raw
            components = entry['path'].split('/')
            parent = tree
            for component in components[:-1]:
                parent = parent.setdefault(component, {})
            parent[components[-1]] = (entry['mode'], kind, oid)
        def write_tree(node):
            raw = bytearray()
            for name, value in sorted(node.items()):
                mode, kind, oid = ('040000', 'tree', write_tree(value)) if isinstance(value, dict) else value
                raw.extend(mode.encode() + b' ' + kind.encode() + b' ' + oid + b'\t' + name.encode() + b'\0')
            return git('mktree', '-z', '--missing', data=bytes(raw))
        tree_oid = write_tree(tree)
        head = git('commit-tree', tree_oid.decode(), data=b'Group fixture\n')
        git('update-ref', 'HEAD', head.decode())
        cls.baseline = cls.work / 'baseline'
        cls.sid = repo.start_scan(cls.baseline, 'sce', cls.profile)
        while repo.scan_page(cls.baseline, 'code', cls.sid)['state'] != 'COMPLETE':
            pass
        db = repo.db_for(cls.baseline)
        try:
            db.execute("UPDATE repo_entries SET state='ERROR',reason='FIXTURE_READ_FAULT' WHERE snapshot_id=? AND path='oversize.dat'", (cls.sid,))
            import source_eligibility
            snap=repo.load_snapshot(db,'code',cls.sid)
            row=db.execute("SELECT * FROM repo_entries WHERE snapshot_id=? AND path='oversize.dat'",(cls.sid,)).fetchone()
            source_eligibility.write_facts(db,snap,row,source_eligibility.metadata_facts(snap,row))
            db.commit()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp_run = tempfile.TemporaryDirectory(dir=self.work)
        self.addCleanup(self.temp_run.cleanup)
        self.run = Path(self.temp_run.name)
        self.store, self.manifest, self.output = self.run / 'store', self.run / 'manifest', self.run / 'groups'
        shutil.copytree(self.baseline, self.store)
        self.policy_path = self.run / 'automation.json'
        self.policy_path.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'money_budget': 0, 'max_parallel': 1}))
        self.operator = self.run / 'operator.json'
        self.operator.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(self.policy_path), 'namespaces': ['code'], 'templates': {}, 'repositories': {'sce': self.profile}}))
        self.batch = base.write_manifest(self.store, 'sce', self.profile, self.sid, self.manifest)
        self.policy = groups.policy_view(None, self.profile)
        self.adapter = mock.patch.object(groups, 'eligibility_view', side_effect=self.mapped)

    def mapped(self, db, snap, entries, profile):
        result = {}
        for entry in entries:
            original = self.fixture_eligibility[entry['path']]
            result[entry['path']] = {'file_sha256': entry['file_sha256'], 'captured_state': entry['state'],
                'text_exportable': original['text_exportable'], 'code_analysis_eligible': original['code_analysis_eligible'],
                'format_kind': original['format_kind'], 'reason': original['reason'],
                'revision': digest([entry['file_sha256'], original['format_kind']])}
        return result, {'schema': 'roadmap.pr006-proposed-source-eligibility-view.v1',
                        'version': 'SYNTHETIC_ADAPTER_TEST_ONLY', 'state': 'MAPPED'}

    def build(self, **kwargs):
        with self.adapter:
            return groups.publish(self.operator, 'sce', self.manifest, self.output, **kwargs)

    def frozen(self):
        with base.snapshot_view(self.store, self.profile, 'sce', self.sid) as (db, snap):
            entries = list(base.entry_rows(db, snap))
            q, _ = self.mapped(db, snap, entries, self.profile)
            analyses = {e['path']: json.loads(db.execute('SELECT analysis FROM repo_entries WHERE snapshot_id=? AND path=?',
                        (self.sid, e['path'])).fetchone()[0] or '{}') for e in entries}
        return entries, analyses, q

    def pure(self, entries, analyses, q, policy=None, declared=None):
        return groups.plan_sources(entries, analyses, q, {'namespace': 'code', 'repository': 'sce', 'snapshot_id': self.sid},
                                   policy or self.policy, declared)

    def eligibility_directory(self):
        directory=self.run/'eligibility';directory.mkdir()
        entries, _, _=self.frozen()
        mapping,_=self.mapped(None,None,entries,self.profile)
        rows=[{'schema':'occ.repo-source-eligibility-adapter.v1','path':p,**v} for p,v in sorted(mapping.items())]
        (directory/'SOURCE_ELIGIBILITY.jsonl').write_bytes(b''.join(json_bytes(r) for r in rows))
        binding={k:self.batch['binding'][k] for k in ('snapshot_id','namespace','repository','profile_revision')}
        binding['base_batch_id']=self.batch['batch_id']
        header={'schema':'occ.repo-group-eligibility-input.v1','binding':binding,
                'upstream':{'schema':'roadmap.pr006-proposed-source-eligibility-view.v1',
                    'version':'SYNTHETIC_ADAPTER_TEST_ONLY','owner':'supplied fixture, not PR005',
                    'projection_digest':file_proof(directory/'SOURCE_ELIGIBILITY.jsonl')['sha256'],
                    'proof_scope':'WHOLE_SOURCE_CLASSIFICATION'},
                'source_projection':{'path':'SOURCE_ELIGIBILITY.jsonl',**file_proof(directory/'SOURCE_ELIGIBILITY.jsonl')}}
        (directory/'ELIGIBILITY.json').write_bytes(json_bytes(header))
        return directory,header

    def test_full_real_ledger_raw_refs_and_immutable_base(self):
        before = {n: file_proof(self.manifest / n) for n in base.METADATA}
        receipt = self.build()
        self.assertEqual(receipt['counts']['entries'], 70)
        self.assertEqual(receipt['counts']['groups'], 68)
        members = jsonl(self.output / 'GROUP_MEMBERS.jsonl')
        refs = [r for s in jsonl(self.output / 'GROUP_PARTS.jsonl') for r in s['raw_refs']]
        original = jsonl(self.manifest / 'PARTS_INDEX.jsonl')
        self.assertEqual(len(members), len({m['source_id'] for m in members}))
        for member in members:
            self.assertEqual(member['source_id'],self.oracle['common_ids_after_addition']['sources'][member['path']])
        self.assertEqual({r['part_id'] for r in refs}, {r['part_id'] for r in original})
        self.assertEqual(len(refs), len(original))
        self.assertEqual(sum(r['bytes'] for r in refs), sum(map(len, self.raw_sources.values())))
        for ref in refs:
            part = next(p for p in original if p['part_id'] == ref['part_id'])
            for field in ('logical_id', 'revision', 'source_start', 'source_end', 'bytes', 'sha256'):
                self.assertEqual(ref[field], part[field])
        self.assertEqual({n: file_proof(self.output / n) for n in base.METADATA}, before)
        self.assertTrue(receipt['raw_reference_complete'])
        header=json.loads((self.output/'GROUPS.json').read_text())
        self.assertEqual(file_proof(self.output/'ELIGIBILITY_VIEW.jsonl')['sha256'],header['binding']['eligibility_digest'])

    def test_scc_independent_oracle_shuffling_and_labelled_cycle(self):
        entries, analyses, q = self.frozen()
        first = self.pure(entries, analyses, q)
        actual = sorted(sorted(p for p, m in first['members'].items() if m['group_id'] == gid) for gid in first['groups'])
        self.assertEqual(actual, sorted(self.oracle['components']))
        self.assertEqual(actual, reachability_components([e['path'] for e in entries], [r for r in first['relations'] if r['topology']]))
        for seed in range(5):
            random.Random(seed).shuffle(entries)
            # Mapping order and saved import order must not affect canonical plan.
            analyses = dict(reversed(list(analyses.items())))
            for value in analyses.values():
                random.Random(seed).shuffle(value.get('imports', []))
            self.assertEqual(self.pure(entries, analyses, q), first)

    def test_oversized_cycle_all_segments_tail_and_budgets(self):
        self.build()
        member = next(m for m in jsonl(self.output / 'GROUP_MEMBERS.jsonl') if m['path'] == 'pkg/a.py')
        rows = [s for s in jsonl(self.output / 'GROUP_PARTS.jsonl') if s['group_id'] == member['group_id']]
        self.assertGreater(len(rows), 20)
        for n, row in enumerate(rows):
            self.assertEqual(row['ordinal'], n)
            self.assertEqual(row['previous'], rows[n-1]['group_part_id'] if n else None)
            self.assertEqual(row['next'], rows[n+1]['group_part_id'] if n+1 < len(rows) else None)
            self.assertLessEqual(row['raw_reference_bytes'], self.policy['raw_reference_bytes_per_segment'])
            self.assertLessEqual(len(json_bytes(row)), self.policy['reference_frame_bytes'])
        refs = [r for s in rows for r in s['raw_refs'] if r['source_id'] == member['source_id']]
        self.assertEqual(refs[-1]['source_end'], len(self.raw_sources['pkg/a.py']))

    def test_logical_ids_survive_unrelated_addition_byte_change_and_membership_change(self):
        entries, analyses, q = self.frozen()
        first = self.pure(entries, analyses, q)
        new = dict(entries[0], path='aaa_unrelated.txt', ordinal=0, file_sha256='a'*64, chunk_count=1)
        entries = [new, *[dict(e, ordinal=e['ordinal']+1) for e in entries]]
        q[new['path']] = {'file_sha256': new['file_sha256'], 'captured_state': 'INDEXED', 'text_exportable': True,
                         'code_analysis_eligible': False, 'format_kind': 'UTF8_TEXT', 'reason': None, 'revision': 'a'*64}
        analyses[new['path']] = {'parser': 'TEXT_ONLY'}
        added = self.pure(entries, analyses, q)
        for path, old in first['members'].items():
            self.assertEqual(added['members'][path]['source_id'], old['source_id'])
            self.assertEqual(added['members'][path]['group_id'], old['group_id'])
            self.assertEqual(added['groups'][old['group_id']]['group_revision'], first['groups'][old['group_id']]['group_revision'])
        changed = [dict(e, file_sha256='b'*64) if e['path'] == 'pkg/a.py' else e for e in entries]
        q['pkg/a.py'] = dict(q['pkg/a.py'], file_sha256='b'*64)
        edited = self.pure(changed, analyses, q)
        gid = first['members']['pkg/a.py']['group_id']
        self.assertEqual(edited['members']['pkg/a.py']['group_id'], gid)
        self.assertNotEqual(edited['groups'][gid]['group_revision'], first['groups'][gid]['group_revision'])
        analyses['pkg/c.py'] = dict(analyses['pkg/c.py'], imports=[])
        separated = self.pure(changed, analyses, q)
        self.assertNotEqual(separated['members']['pkg/a.py']['group_id'], gid)

    def test_static_declared_and_filename_evidence_do_not_mix(self):
        rows, _, _ = self.frozen()
        by_path = {r['path']: r for r in rows}
        declared = {'schema': 'occ.repo-declared-relations.v1', 'links': [{
            'from': 'pkg/a.py', 'to': 'contracts/task.schema.json', 'kind': 'OPERATOR_DECLARED_CONTRACT',
            'from_sha256': by_path['pkg/a.py']['file_sha256'], 'to_sha256': by_path['contracts/task.schema.json']['file_sha256']}]}
        self.build(declared=declared)
        relations = jsonl(self.output / 'RELATIONS.jsonl')
        self.assertTrue({'PYTHON_STATIC_IMPORT', 'STATIC_TEST_IMPORT', 'OPERATOR_DECLARED_CONTRACT', 'HEURISTIC_TEST_CANDIDATE'} <= {r['relation_kind'] for r in relations})
        for relation in relations:
            self.assertEqual(relation['topology'], relation['relation_kind'] in {'PYTHON_STATIC_IMPORT', 'STATIC_TEST_IMPORT'})
            self.assertEqual(relation['observed_test_coverage'], 'NOT_MEASURED')

    def test_whole_source_binary_lfs_and_gaps_never_become_code(self):
        self.build()
        members = {m['path']: m for m in jsonl(self.output / 'GROUP_MEMBERS.jsonl')}
        for path in ['binary_source.py', 'lfs_code.py', 'parse_failed.py']:
            self.assertFalse(members[path]['code_analysis_eligible'])
        for path in ['binary_source.py', 'lfs_code.py']:
            self.assertFalse(members[path]['text_exportable'])
            refs = [r for s in jsonl(self.output / 'GROUP_PARTS.jsonl') for r in s['raw_refs'] if r['source_id'] == members[path]['source_id']]
            self.assertTrue(refs)
            self.assertTrue(all(not r['text_eligible'] for r in refs))
        empty = members['empty.txt']
        refs = [r for s in jsonl(self.output / 'GROUP_PARTS.jsonl') for r in s['raw_refs'] if r['source_id'] == empty['source_id']]
        self.assertEqual([(r['source_start'],r['source_end']) for r in refs], [(0,0)])
        coverage = json.loads((self.output / 'COVERAGE.json').read_text())
        self.assertFalse(coverage['all_tracked_bytes_exportable'])
        self.assertEqual(coverage['ai_read'], 'UNKNOWN')

    def test_unresolved_static_cases_and_ineligible_targets(self):
        self.build()
        rows = jsonl(self.output / 'UNRESOLVED.jsonl')
        required = {(r['path'],r['status']) for r in self.oracle['expected_unresolved'] if not r['status'].startswith('DECLARED_')}
        # The qualifier's explicit parse/binary reasons may be more specific.
        self.assertTrue(required <= {(r['path'],r['status']) for r in rows})
        self.assertFalse(any(r['topology'] and r['to_path'] == 'binary_source.py' for r in jsonl(self.output / 'RELATIONS.jsonl')))

    def test_unmapped_adapter_diagnostic_cli_and_stale_hash_rejected(self):
        def unknown(db,snap,entries,profile):
            return groups.unmapped_eligibility(entries),{'schema':None,'version':None,'state':'PR005_ADAPTER_UNMAPPED'}
        with mock.patch.object(groups,'eligibility_view',side_effect=unknown):
            receipt = groups.publish(self.operator, 'sce', self.manifest, self.output)
        self.assertEqual(receipt['graph_scope'], 'BLOCKED_ELIGIBILITY_UNMAPPED')
        self.assertEqual(receipt['counts']['groups'], 70)
        self.assertFalse(any(r['topology'] for r in jsonl(self.output / 'RELATIONS.jsonl')))
        q, _ = self.mapped(None, None, self.frozen()[0], self.profile)
        q['pkg/a.py']['file_sha256'] = '0'*64
        with mock.patch.object(groups, 'eligibility_view', return_value=(q, {'state':'MAPPED'})):
            with self.assertRaisesRegex(ValueError, 'ELIGIBILITY_BINDING_MISMATCH'):
                groups.publish(self.operator, 'sce', self.manifest, self.run / 'bad')
        result = subprocess.run([sys.executable, '-I', '-B', str(LAB / 'repo_groups.py'), '--profile', str(self.operator),
            '--repository', 'sce', '--manifest', str(self.manifest), '--output', str(self.run / 'cli')], capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)['counts']['entries'], 70)

    def test_saved_analysis_tamper_is_not_published(self):
        db = repo.db_for(self.store)
        try:
            row = db.execute('SELECT analysis FROM repo_entries WHERE snapshot_id=? AND path=?', (self.sid,'pkg/a.py')).fetchone()
            value = json.loads(row[0]); value['imports'] = []
            db.execute('UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path=?', (json.dumps(value),self.sid,'pkg/a.py'))
            db.commit()
        finally:
            db.close()
        with self.assertRaisesRegex(ValueError,'ANALYSIS_REVISION_STALE'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_manifest_and_derived_range_membership_tamper(self):
        before = self.build()
        proof = file_proof(self.output / 'GROUPS.json')
        for table, field, error in [('refs','source_end','RAW_REFERENCE_CORRUPT'), ('members','source_id','GROUP_MEMBERSHIP_CORRUPT')]:
            def corrupt(event, **context):
                if event == 'plan_written':
                    db = context['plan']
                    row = db.execute('SELECT '+ ('part_id' if table=='refs' else 'id') + ',payload FROM ' + table + ' LIMIT 1').fetchone()
                    value = json.loads(row[1]); value[field] = '0'*64 if field=='source_id' else value[field]+1
                    db.execute('UPDATE '+table+' SET payload=? WHERE '+('part_id' if table=='refs' else 'id')+'=?',(json.dumps(value),row[0]))
                    db.commit()
            with self.subTest(table=table), mock.patch.object(groups,'boundary',side_effect=corrupt):
                with self.assertRaisesRegex(ValueError,error):
                    self.build()
            self.assertEqual(file_proof(self.output/'GROUPS.json'),proof)
        raw = (self.manifest/'PARTS_INDEX.jsonl').read_bytes()
        (self.manifest/'PARTS_INDEX.jsonl').write_bytes(raw.replace(b'"source_end":',b'"tampered_end":',1))
        with self.assertRaisesRegex(ValueError,'MANIFEST_UNVERIFIED'):
            self.build()
        self.assertEqual(before['grouping_batch_id'],json.loads((self.output/'GROUPS.json').read_text())['grouping_batch_id'])

    def test_explicit_part_frame_resource_budgets_without_total_caps(self):
        for changes, error in [({'raw_reference_bytes_per_segment':1},'PART_BUDGET_TOO_SMALL'),
                               ({'reference_frame_bytes':100},'REFERENCE_ROW_TOO_LARGE')]:
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError,error):
                self.build(policy=self.policy|changes)
            self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError,'GRAPH_RESOURCE_BUDGET'):
            self.build(resources={'schema':'occ.repo-group-resources.v1','graph_input_bytes':1,'timeout_seconds':None})
        self.assertIsNone(groups.Resources().value['graph_input_bytes'])
        self.assertIsNone(groups.Resources().value['timeout_seconds'])
        for key in ['total_source_cap','total_group_cap','total_segment_cap']:
            self.assertIsNone(self.policy[key])

    def test_declared_outside_excluded_and_hash_drift(self):
        entries, analyses, q = self.frozen()
        a = next(e for e in entries if e['path']=='pkg/a.py')
        links = [{'from':'pkg/a.py','to':p,'from_sha256':a['file_sha256'],'to_sha256':'0'*64,'kind':'OPERATOR_DECLARED_CONTRACT'}
                 for p in ['missing.schema.json','operator-excluded.txt','contracts/task.schema.json']]
        plan = self.pure(entries,analyses,q,declared={'schema':'occ.repo-declared-relations.v1','links':links})
        self.assertEqual({r['status'] for r in plan['unresolved'] if r['status'].startswith('DECLARED_')},
                         {'DECLARED_TARGET_UNAVAILABLE','DECLARED_MAPPING_STALE'})
        self.assertFalse(any(r['relation_kind']=='OPERATOR_DECLARED_CONTRACT' for r in plan['relations']))

    def test_foreground_fault_rollback_reuse_and_immutable_output_conflict(self):
        first = self.build()
        self.assertTrue(self.build()['reused'])
        proof = file_proof(self.output/'GROUPS.json')
        def fail(event,**context):
            if event=='artifacts_written':
                raise OSError(errno.ENOSPC,'injected disk full')
        with mock.patch.object(groups,'boundary',side_effect=fail), self.assertRaises(OSError):
            self.build()
        self.assertEqual(file_proof(self.output/'GROUPS.json'),proof)
        self.assertEqual(list(self.run.glob('.occ-groups-*')),[])
        with self.assertRaisesRegex(ValueError,'GROUP_OUTPUT_CONFLICT'):
            self.build(policy=self.policy|{'max_refs_per_segment':1})
        self.assertEqual(first['grouping_batch_id'],json.loads((self.output/'GROUPS.json').read_text())['grouping_batch_id'])

    def test_post_validation_tamper_never_publishes_success_header(self):
        for event in ['artifacts_written','before_header','before_publish']:
            def tamper(found,**context):
                if found==event:
                    path=context['stage']/'GROUP_PARTS.jsonl'
                    raw=path.read_bytes();path.write_bytes(raw.replace(b'"source_end":',b'"bad_end":',1))
            with self.subTest(event=event),self.adapter,mock.patch.object(groups,'boundary',side_effect=tamper):
                with self.assertRaisesRegex(ValueError,'GROUP_CATALOG_CORRUPT'):
                    groups.publish(self.operator,'sce',self.manifest,self.output)
            self.assertFalse(self.output.exists())
            self.assertEqual(list(self.run.glob('.occ-groups-*')),[])

    def test_missing_head_relation_and_windows_style_stage_handle_cleanup(self):
        for table,error in [('heads','GROUP_MEMBERSHIP_CORRUPT'),('relations','GROUP_RELATION_CORRUPT')]:
            def corrupt(event,**context):
                if event=='plan_written':
                    context['plan'].execute('DELETE FROM '+table+' WHERE id=(SELECT id FROM '+table+' LIMIT 1)')
                    context['plan'].commit()
            remove=shutil.rmtree
            def windows_style_remove(directory,*args,**kwargs):
                if Path('/proc/self/fd').is_dir():
                    handles=[]
                    for fd in Path('/proc/self/fd').iterdir():
                        try: value=os.readlink(fd)
                        except OSError: continue
                        if value.startswith(str(directory)):handles.append(value)
                    self.assertEqual(handles,[], 'An active SQLite reader would lock stage deletion on Windows')
                return remove(directory,*args,**kwargs)
            with self.subTest(table=table),self.adapter,mock.patch.object(groups,'boundary',side_effect=corrupt),mock.patch.object(groups.shutil,'rmtree',side_effect=windows_style_remove):
                with self.assertRaisesRegex(ValueError,error):
                    groups.publish(self.operator,'sce',self.manifest,self.output)
            self.assertFalse(self.output.exists())

    def test_subprocess_crash_before_publish_never_exposes_verified_catalog(self):
        code = "import sys,os;sys.path.insert(0,sys.argv[1]);import repo_groups as g;g.boundary=lambda e,**k:os._exit(19) if e=='before_publish' else None;g.publish(*sys.argv[2:])"
        result = subprocess.run([sys.executable,'-I','-B','-c',code,str(LAB),str(self.operator),'sce',str(self.manifest),str(self.output)],capture_output=True)
        self.assertEqual(result.returncode,19,result.stderr)
        self.assertFalse(self.output.exists())
        # Kernel lock is released by death; retry never adopts the partial stage.
        receipt = groups.publish(self.operator,'sce',self.manifest,self.output)
        self.assertEqual(receipt['state'],'READY')

    def test_offline_navigation_movable_escaped_and_all_links_resolve(self):
        self.build()
        moved = self.run/'moved'
        self.output.rename(moved)
        labels, count = [], 0
        for path in moved.rglob('*.html'):
            parser=Links();parser.feed(path.read_text())
            self.assertEqual(parser.active,[])
            labels.extend(parser.text)
            for href in parser.links:
                self.assertFalse(re.match(r'^[A-Za-z]+:',href))
                resolved=(path.parent/href).resolve()
                self.assertTrue(resolved.is_relative_to(moved.resolve()))
                self.assertTrue(resolved.is_file(),href)
                count+=1
        self.assertGreater(count,400)
        self.assertTrue(any('русский_<tag>.txt' in label for label in labels))

    def test_trusted_cli_boundaries_and_policy_types(self):
        with self.assertRaisesRegex(ValueError,'REPO_OUTSIDE_OPERATOR_SCOPE'):
            groups.publish(self.operator,'other',self.manifest,self.output)
        with self.assertRaisesRegex(ValueError,'OUTPUT_MUST_BE_OUTSIDE'):
            groups.publish(self.operator,'sce',self.manifest,self.store/'groups')
        for change in [{'max_refs_per_segment':True},{'total_source_cap':20},{'include_heuristic_candidates_as_topology':True},
                       {'python_roots':['outside']},{'unknown':1}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                groups.policy_view(self.policy|change,self.profile)
        with self.assertRaisesRegex(ValueError,'GROUP_RESOURCE_POLICY_INVALID'):
            groups.Resources({})

    def test_explicit_normalized_adapter_cli_scope_schema_hash_and_no_chunk_fallback(self):
        directory,header=self.eligibility_directory()
        command=[sys.executable,'-I','-B',str(LAB/'repo_groups.py'),'--profile',str(self.operator),
                 '--repository','sce','--manifest',str(self.manifest),'--output',str(self.output),
                 '--eligibility',str(directory)]
        result=subprocess.run(command,capture_output=True,check=True)
        receipt=json.loads(result.stdout)
        self.assertEqual(receipt['counts']['groups'],68)
        members={m['path']:m for m in jsonl(self.output/'GROUP_MEMBERS.jsonl')}
        self.assertFalse(members['binary_source.py']['text_exportable'])
        self.assertFalse(members['lfs_code.py']['code_analysis_eligible'])
        for mutation,reason in [('schema','PR005_ADAPTER_UNMAPPED'),('binding','ELIGIBILITY_BINDING_MISMATCH'),
                                ('proof_scope','PR005_ADAPTER_UNMAPPED'),('sha256','ELIGIBILITY_BINDING_MISMATCH')]:
            bad=json.loads(json.dumps(header))
            if mutation=='schema':bad['schema']='unknown'
            if mutation=='binding':bad['binding']['namespace']='other'
            if mutation=='proof_scope':bad['upstream']['proof_scope']='PART_UTF8_ONLY'
            if mutation=='sha256':bad['source_projection']['sha256']='0'*64
            (directory/'ELIGIBILITY.json').write_bytes(json_bytes(bad))
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,reason):
                groups.publish(self.operator,'sce',self.manifest,self.run/'bad',eligibility_input=directory)

    def test_actual_pr005_default_cli_whole_source_binding_and_legacy_diagnostics(self):
        import source_eligibility as owner
        receipt=groups.publish(self.operator,'sce',self.manifest,self.output)
        self.assertEqual(receipt['counts']['groups'],68)
        header=json.loads((self.output/'GROUPS.json').read_text())
        adapter=header['binding']['eligibility_adapter']
        self.assertEqual(adapter['schema'],owner.SCHEMA)
        self.assertEqual(adapter['version'],owner.CLASSIFIER_VERSION)
        self.assertEqual(adapter['pending_sources'],0)
        q={r['path']:r for r in jsonl(self.output/'ELIGIBILITY_VIEW.jsonl')}
        self.assertFalse(q['binary_source.py']['text_exportable'])
        self.assertFalse(q['binary_source.py']['code_analysis_eligible'])
        self.assertFalse(q['lfs_code.py']['text_exportable'])
        self.assertEqual(q['lfs_code.py']['format_kind'],'LFS_POINTER_V1')
        self.assertFalse(q['parse_failed.py']['code_analysis_eligible'])
        self.assertTrue(q['parse_failed.py']['text_exportable'])
        db=repo.db_for(self.store)
        try:
            for row in db.execute('SELECT path,analysis FROM repo_entries WHERE snapshot_id=?',(self.sid,)):
                value=json.loads(row['analysis'] or '{}');value.pop('format_eligibility',None)
                db.execute('UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path=?',(json.dumps(value),self.sid,row['path']))
            db.commit()
        finally:db.close()
        legacy=groups.publish(self.operator,'sce',self.manifest,self.run/'legacy')
        self.assertEqual(legacy['graph_scope'],'BLOCKED_ELIGIBILITY_UNMAPPED')
        self.assertEqual(legacy['counts']['groups'],70)
        self.assertFalse(any(r['topology'] for r in jsonl(self.run/'legacy'/'RELATIONS.jsonl')))

    def test_actual_pr005_fact_corruption_preserves_valid_catalog(self):
        groups.publish(self.operator,'sce',self.manifest,self.output)
        proof=file_proof(self.output/'GROUPS.json')
        db=repo.db_for(self.store)
        try:
            row=db.execute("SELECT analysis FROM repo_entries WHERE snapshot_id=? AND path='pkg/a.py'",(self.sid,)).fetchone()
            value=json.loads(row[0]);value['format_eligibility']['file_sha256']='0'*64
            db.execute("UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path='pkg/a.py'",(json.dumps(value),self.sid));db.commit()
        finally:db.close()
        with self.assertRaisesRegex(ValueError,'ELIGIBILITY_BINDING_MISMATCH'):
            groups.publish(self.operator,'sce',self.manifest,self.output)
        self.assertEqual(file_proof(self.output/'GROUPS.json'),proof)

    def test_missing_owner_module_preserves_diagnostic_full_ledger(self):
        with mock.patch.dict(sys.modules,{'source_eligibility':None}):
            receipt=groups.publish(self.operator,'sce',self.manifest,self.output)
        self.assertEqual(receipt['graph_scope'],'BLOCKED_ELIGIBILITY_UNMAPPED')
        self.assertEqual(receipt['counts']['entries'],70)
        self.assertEqual(receipt['counts']['groups'],70)
        self.assertTrue(receipt['raw_reference_complete'])

    def test_large_iterative_graph_no_files_groups_or_segments_cap(self):
        count = 5000
        entries, analyses, eligibility = [], {}, {}
        for n in range(count):
            path = f'ring/m{n:05}.py'
            entries.append({'path':path,'ordinal':n,'state':'INDEXED','file_sha256':'a'*64,'chunk_count':1})
            analyses[path] = {'parser':'PYTHON_AST','imports':[{'module':f'ring.m{(n+1)%count:05}',
                                'level':0,'names':[],'line':1}]}
            eligibility[path] = {'file_sha256':'a'*64,'captured_state':'INDEXED','text_exportable':True,
                                  'code_analysis_eligible':True,'format_kind':'PYTHON','reason':None,'revision':'a'*64}
        plan=self.pure(entries,analyses,eligibility)
        self.assertEqual(len(plan['members']),count)
        self.assertEqual(len(plan['groups']),1)
        gid=next(iter(plan['groups']))
        refs=({'source_id':plan['members'][f'ring/m{n:05}.py']['source_id'],'part_id':digest(['part',n]),
               'logical_id':digest(['logical',n]),'revision':digest(['part',n]),'source_start':0,'source_end':1,
               'chunk_ordinal':0,'bytes':1,'sha256':'a'*64,'file_sha256':'a'*64,'text_eligible':True} for n in range(count))
        segments=list(groups.segments(gid,refs,self.policy|{'max_refs_per_segment':3},'a'*64,groups.Resources()))
        self.assertGreater(len(segments),1000)
        self.assertEqual(sum(len(r['raw_refs']) for r in segments),count)
        self.assertIsNone(segments[-1]['next'])

    def test_source_is_data_no_import_hooks_or_execution(self):
        with mock.patch.object(groups.source,'analyze',wraps=groups.source.analyze) as parse:
            self.build()
        self.assertTrue(parse.called)
        self.assertFalse((self.root/'DANGEROUS_IMPORT_EXECUTED').exists())
        self.assertFalse(any(name in sys.modules for name in ['dangerous','pkg.a','pkg.b','pkg.c']))


if __name__ == '__main__':
    unittest.main()
