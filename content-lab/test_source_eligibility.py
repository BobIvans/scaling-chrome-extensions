import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import zipfile
from unittest import TestCase, mock

import automation_core as core
from content_lab import _insert_item
import native_adapter
import repo_context as repo
import repo_coverage as coverage
import repo_manifest as manifest
import repo_source
import source_eligibility as eligibility
import test_repo_context

FIXTURES = Path(__file__).parent / 'fixtures/pr005'


class SourceEligibilityTests(TestCase):
    setUp = test_repo_context.RepoContextTests.setUp
    git = test_repo_context.RepoContextTests.git
    put = test_repo_context.RepoContextTests.put
    commit = test_repo_context.RepoContextTests.commit
    scan = test_repo_context.RepoContextTests.scan

    def capture(self, sources):
        for path, raw in sources.items():
            self.put(path, raw)
        self.commit()
        self.status = self.scan()
        self.sid = self.status['snapshot_id']
        return self.status

    def mutate(self, sql, args=()):
        db = repo.db_for(self.store)
        try:
            with db:
                db.execute(sql, args)
        finally:
            db.close()

    def page(self, action='SUMMARY', **kwargs):
        return coverage.query(self.store, 'code', self.sid, 'sce', self.profile, action, **kwargs)

    def all_rows(self, query='ALL', limit=20, native=False):
        cursor, rows, pages = None, [], 0
        while True:
            args = dict(query=query, limit=limit, cursor=cursor)
            value = (native_adapter.dispatch(dict(type='durable.repo.coverage', repository='sce',
                snapshotId=self.sid, action='PAGE', **args), self.profile_file())['coverage'] if native else self.page('PAGE', **args))
            self.assertLessEqual(coverage.frame_size(value), 32768)
            rows.extend(value['rows'])
            pages += 1
            if value['next_cursor'] is None:
                return rows, pages
            self.assertEqual(value['next_cursor']['afterOrdinal'], rows[-1]['ordinal'])
            cursor = value['next_cursor']

    def profile_file(self):
        policy = self.root / 'policy.json'
        policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'max_parallel': 1, 'money_budget': 0}), encoding='utf-8')
        path = self.root / 'native-profile.json'
        path.write_text(json.dumps({'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
            'policy_file': str(policy), 'namespaces': ['code'], 'templates': {}, 'repositories': {'sce': self.profile}}), encoding='utf-8')
        return path

    def legacy(self):
        self.mutate("UPDATE repo_entries SET analysis=json_remove(analysis,'$.format_eligibility') WHERE snapshot_id=?", (self.sid,))

    def backfill(self, **kwargs):
        return eligibility.backfill(self.store, 'code', self.sid, 'sce', self.profile, **kwargs)

    def seed_golden(self):
        # The input package explicitly defines four metadata/fault recipes.
        # Only ledger identities/dispositions come from the recipe; facts are
        # independently classified and compared with the golden expected DTO.
        expected = [json.loads(s) for s in (FIXTURES / 'EXPECTED_LEDGER.jsonl').read_text().splitlines()]
        inputs = json.loads((FIXTURES / 'INPUTS.json').read_text())['sources']
        self.profile['exclusions'] = ['ignored']
        snap = {'alias': 'sce', 'profile': self.profile, 'head': 'a' * 40, 'tree': 'b' * 40}
        self.sid = core.digest(snap)
        stored_snap = dict(id=self.sid, namespace='code', alias='sce', profile=json.dumps(self.profile),
                           head=snap['head'], tree=snap['tree'], cursor=64, total=64)
        db = repo.db_for(self.store)
        try:
            with db:
                db.execute('INSERT INTO repo_snapshots VALUES (?,?,?,?,?,?,?,?,?)',
                    (self.sid, 'code', 'sce', json.dumps(self.profile), snap['head'], snap['tree'], 64, 64, time.time()))
                for recipe, wanted in zip(inputs, expected):
                    raw = (FIXTURES / recipe['input_path'].removeprefix('fixtures/')).read_bytes() if recipe['input_path'] else None
                    row = dict(snapshot_id=self.sid, ordinal=int(recipe['ordinal']), path=recipe['path'], mode=recipe['mode'],
                        kind=recipe['kind'], oid=wanted['git_oid'], size=int(recipe['git_size']) if recipe['git_size'] is not None else None,
                        state=wanted['disposition'], reason=wanted['legacy_reason'], file_hash=wanted['file_sha256'], analysis='{}', working_state=None)
                    if row['state'] == 'INDEXED':
                        self.assertEqual(repo.sha(raw), recipe['input_sha256'])
                        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                        self.assertEqual(blob, row['oid'])
                        classified = eligibility.classify_chunks([raw])
                        analysis, boundaries = repo_source.analyze(row['path'], raw) if classified['text_eligibility'] == 'ELIGIBLE' else ({'parser': None}, [])
                        facts = eligibility.make_facts(self.sid, row, classified, analysis.get('parser'))
                        for ordinal, chunk in enumerate(repo_source.partition('sce', row['path'], raw, row['file_hash'], boundaries)):
                            db.execute('INSERT INTO repo_chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                                (self.sid, row['path'], ordinal, chunk['logical_id'], chunk['revision'], chunk['byte_start'], chunk['byte_end'],
                                 chunk['start_line'], chunk['end_line'], chunk['fragment'], chunk['raw'], None))
                    else:
                        analysis = {}
                        facts = eligibility.metadata_facts(stored_snap, row)
                    analysis['format_eligibility'] = facts
                    row['analysis'] = json.dumps(analysis)
                    db.execute('INSERT INTO repo_entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', tuple(row.values()))
        finally:
            db.close()
        return [dict(r, snapshot_id=self.sid) for r in expected]

    def test_A01_A06_A07_A08_A09_A10_A11_golden_64_entries_native_EOF_and_gaps(self):
        expected = self.seed_golden()
        actual, pages = self.all_rows(native=True)
        self.assertEqual(actual, expected)
        self.assertGreaterEqual(pages, 4)
        expected_summary = json.loads((FIXTURES / 'EXPECTED_SUMMARY.json').read_text())['coverage']['summary']
        self.assertEqual(self.page()['summary'], expected_summary)
        gaps, _ = self.all_rows('GAPS', native=True)
        self.assertEqual(gaps, [r for r in expected if r['text_eligibility'] != 'ELIGIBLE'])
        output = self.root / 'GAPS.jsonl'
        receipt = coverage.write_gaps(self.store, 'code', self.sid, 'sce', self.profile, output)
        self.assertEqual(receipt['entries'], '15')
        self.assertEqual([json.loads(r) for r in output.read_text().splitlines()], gaps)
        self.assertNotIn((FIXTURES / 'input_bytes/source_055.bin').read_bytes(), output.read_bytes())
        self.assertNotIn((FIXTURES / 'input_bytes/source_056.bin').read_bytes(), output.read_bytes())

    def test_A02_A03_whole_binary_source_prevents_every_printable_fragment(self):
        self.capture({'controls.txt': b'matchprint\n' * 1500 + b'\0', 'nonutf.bin': b'matchprint\n' * 1500 + b'\xff',
                      'normal.txt': b'matchprint ordinary\n'})
        db = repo.db_for(self.store)
        try:
            for path in ('controls.txt', 'nonutf.bin'):
                chunks = list(db.execute('SELECT item_id,raw FROM repo_chunks WHERE snapshot_id=? AND path=?', (self.sid, path)))
                self.assertGreater(len(chunks), 1)
                self.assertTrue(all(c['item_id'] is None for c in chunks))
            ids = [x['id'] for x in core.search(self.store, 'code', 'matchprint', 1)]
            self.assertEqual(len(ids), 1)
            self.assertEqual(core.context_pack(self.store, 'code', ids)['items'][0]['path'], 'normal.txt')
        finally:
            db.close()
        for byte in range(32):
            wanted = 'ELIGIBLE' if byte in (9, 10, 12, 13) else 'INELIGIBLE'
            self.assertEqual(eligibility.classify_chunks([b'a', bytes([byte])])['text_eligibility'], wanted)

    def test_A04_A05_exact_empty_BOM_CRLF_long_lines_and_python_fallback(self):
        sources = {'empty.txt': b'', 'bom.txt': b'\xef\xbb\xbfhello\r\n',
                   'long.txt': ('Я👋' * 18000).encode(), 'broken.py': b'def broken(:\n    pass\n'}
        self.capture(sources)
        db = repo.db_for(self.store)
        try:
            for row in db.execute('SELECT * FROM repo_entries WHERE snapshot_id=?', (self.sid,)):
                facts = eligibility.project_facts(self.sid, row)
                self.assertEqual(facts['text_eligibility'], 'ELIGIBLE')
                raw = b''.join(c[0] for c in db.execute('SELECT raw FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (self.sid, row['path'])))
                self.assertEqual(raw, sources[row['path']])
                self.assertEqual(row['file_hash'], repo.sha(raw))
                if row['path'] == 'broken.py':
                    self.assertEqual(facts['parser'], 'PYTHON_PARSE_FAILED')
        finally:
            db.close()

    def test_A06_A07_A08_lfs_strict_boundaries_never_fetch_payload(self):
        canonical = eligibility.LFS_VERSION + b'oid sha256:' + b'a' * 64 + b'\nsize 0\n'
        self.assertEqual(eligibility.classify_chunks([canonical])['format_kind'], 'LFS_POINTER_V1')
        for malformed in (canonical[:-1], canonical.replace(b'size 0', b'size 00'), canonical.replace(b'a' * 64, b'A' * 64)):
            self.assertEqual(eligibility.classify_chunks([malformed])['format_kind'], 'LFS_POINTER_MALFORMED')
        self.assertEqual(eligibility.classify_chunks([b'Example:\n' + canonical])['text_eligibility'], 'ELIGIBLE')
        self.capture({'pointer.dat': canonical, 'normal.txt': b'normal'})
        rows, _ = self.all_rows()
        pointer = next(r for r in rows if r['path'] == 'pointer.dat')
        self.assertEqual(pointer['lfs']['payload_availability'], 'NOT_CHECKED')
        self.assertEqual(pointer['lfs']['payload_size'], '0')
        self.assertIsNone(self.page()['summary']['external_payloads_complete'])
        chosen = repo.selection(self.store, 'code', self.sid, ['pointer.dat', 'normal.txt'])
        self.assertEqual(chosen['omitted_sources'][0]['reason'], 'LFS_PAYLOAD_NOT_CHECKED')

    def test_A09_A10_real_metadata_modes_exclusions_and_wallet(self):
        self.profile['exclusions'] = ['ignored']
        for path, raw in {'wallet_logic.py': b'def wallet_logic():\n    return 1\n', '.env': b'protected dummy',
                          'ignored/generated.txt': b'operator dummy', 'secret.md': b'-----BEGIN ' + b'PRIVATE KEY-----\ndummy'}.items():
            self.put(path, raw)
        self.commit()
        head = self.git('rev-parse', 'HEAD').decode().strip()
        blob = subprocess.run(['git', '-C', str(self.checkout), 'hash-object', '-w', '--stdin'], input=b'outside', capture_output=True, check=True).stdout.decode().strip()
        self.git('update-index', '--add', '--cacheinfo', f'120000,{blob},link')
        self.git('update-index', '--add', '--cacheinfo', f'160000,{head},vendor/module')
        self.git('commit', '-qm', 'metadata')
        self.status = self.scan(); self.sid = self.status['snapshot_id']
        rows, _ = self.all_rows(); by = {r['path']: r for r in rows}
        self.assertEqual(by['wallet_logic.py']['text_eligibility'], 'ELIGIBLE')
        self.assertEqual(by['link']['format_kind'], 'SYMLINK_METADATA')
        self.assertEqual(by['vendor/module']['format_kind'], 'SUBMODULE_METADATA')
        self.assertEqual(by['.env']['reasons'], ['PROTECTED_NAME'])
        self.assertEqual(by['ignored/generated.txt']['reasons'], ['OPERATOR_EXCLUSION'])
        self.assertEqual(by['secret.md']['reasons'], ['PROTECTED_TEXT_HEURISTIC'])
        self.assertIsNone(by['.env']['file_sha256'])
        self.assertIsNotNone(by['secret.md']['file_sha256'])

    def test_A12_backfill_restart_replay_byte_budget_and_atomic_source_commit(self):
        self.capture({'a.txt': b'one', 'b.txt': b'two'})
        self.legacy()
        self.assertEqual(self.page()['summary']['state'], 'FORMAT_FACTS_PENDING')
        with self.assertRaisesRegex(ValueError, 'FORMAT_FACTS_PENDING'):
            self.page('PAGE', query='ALL', limit=20, cursor=None)
        db = repo.db_for(self.store)
        before = [tuple(c) for c in db.execute('SELECT * FROM repo_chunks ORDER BY path,ordinal')]; db.close()
        real = eligibility.capture_classification
        calls = [0]
        def crash(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 2:
                raise KeyboardInterrupt()
            return real(*args, **kwargs)
        with mock.patch.object(eligibility, 'capture_classification', side_effect=crash):
            with self.assertRaises(KeyboardInterrupt): self.backfill()
        self.assertEqual(self.page()['summary']['facts_entries'], '1')
        self.assertEqual(self.backfill(max_bytes=2)['blocker'], 'BACKFILL_BYTE_BUDGET')
        with mock.patch.object(repo, 'git', side_effect=AssertionError('no Git')):
            self.assertEqual(self.backfill()['updated_entries'], '1')
            self.assertEqual(self.backfill()['updated_entries'], '0')
        self.assertEqual(self.page()['summary']['state'], 'READY')
        db = repo.db_for(self.store)
        self.assertEqual([tuple(c) for c in db.execute('SELECT * FROM repo_chunks ORDER BY path,ordinal')], before); db.close()

    def test_A13_incremental_utf8_and_sha256_git_object_format(self):
        self.capture({'unicode.txt': 'а'.encode()})
        self.legacy()
        db = repo.db_for(self.store)
        try:
            with db:
                row = db.execute('SELECT * FROM repo_entries').fetchone()
                original = db.execute('SELECT * FROM repo_chunks').fetchone()
                db.execute('DELETE FROM repo_chunks')
                for n, raw in enumerate([b'\xd0', b'\xb0']):
                    logical = core.digest(['split', n])
                    revision = core.digest([logical, row['file_hash'], repo.sha(raw), n, n+1])
                    db.execute('INSERT INTO repo_chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                        (self.sid, row['path'], n, logical, revision, n, n+1, 1, 1, n, raw, None))
                oid = hashlib.sha256(b'blob 2\0' + 'а'.encode()).hexdigest()
                db.execute('UPDATE repo_entries SET oid=?', (oid,))
        finally: db.close()
        self.assertEqual(self.backfill()['updated_entries'], '1')
        self.assertEqual(self.all_rows()[0][0]['text_eligibility'], 'ELIGIBLE')
        self.assertEqual(eligibility.classify_chunks([b'\xd0'])['text_eligibility'], 'INELIGIBLE')

    def test_A14_corrupt_raw_range_revision_filehash_and_oid_block_readiness(self):
        self.capture({'bad.txt': b'a' * 9000, 'good.txt': b'good'})
        originals = []
        db = repo.db_for(self.store)
        for table in ('repo_entries','repo_chunks'):
            originals.append([tuple(r) for r in db.execute('SELECT * FROM ' + table)])
        db.close()
        faults = [("UPDATE repo_chunks SET raw=? WHERE path='bad.txt' AND ordinal=0", (b'b' * 4096,)),
                  ("UPDATE repo_chunks SET byte_start=byte_start+1 WHERE path='bad.txt' AND ordinal=1", ()),
                  ("UPDATE repo_chunks SET revision=? WHERE path='bad.txt' AND ordinal=0", ('f' * 64,)),
                  ("UPDATE repo_entries SET file_hash=? WHERE path='bad.txt'", ('f' * 64,)),
                  ("UPDATE repo_entries SET oid=? WHERE path='bad.txt'", ('f' * 40,))]
        for sql, args in faults:
            with self.subTest(sql=sql):
                db = repo.db_for(self.store)
                with db:
                    db.execute('DELETE FROM repo_chunks');db.execute('DELETE FROM repo_entries')
                    db.executemany('INSERT INTO repo_entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', originals[0])
                    db.executemany('INSERT INTO repo_chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', originals[1])
                db.close()
                self.legacy();self.mutate(sql,args)
                self.assertEqual(self.backfill()['corrupt_entries'], '1')
                self.assertEqual(self.page()['summary']['state'], 'CORRUPT_FACTS')
                with self.assertRaisesRegex(ValueError,'CORRUPT_FACTS'): self.page('PAGE',query='ALL',limit=20,cursor=None)
                db=repo.db_for(self.store)
                rows={r['path']:eligibility.project_facts(self.sid,r) for r in db.execute('SELECT * FROM repo_entries')};db.close()
                self.assertEqual(rows['good.txt']['text_eligibility'],'ELIGIBLE')
                self.assertEqual(rows['bad.txt']['format_kind'],'CORRUPT_CAPTURE')

    def test_A15_native_is_read_only_and_scope_fields_are_strict(self):
        self.capture({'a.txt': b'data'})
        profile = self.profile_file()
        req = dict(type='durable.repo.coverage',repository='sce',snapshotId=self.sid,action='SUMMARY')
        before = (self.store / 'content.sqlite3').read_bytes()
        with mock.patch.object(repo,'git',side_effect=AssertionError('no Git')), mock.patch.object(repo,'db_for',side_effect=AssertionError('no schema writes')), mock.patch.object(core,'Core',side_effect=AssertionError('no Core')), mock.patch.object(repo,'verify_roundtrip_db',side_effect=AssertionError('no proof')), mock.patch.object(eligibility,'backfill',side_effect=AssertionError('no backfill')):
            self.assertEqual(native_adapter.dispatch(req,profile)['coverage']['summary']['state'],'READY')
        self.assertEqual((self.store / 'content.sqlite3').read_bytes(),before)
        for extra in ({'root':'/tmp'},{'namespace':'other'},{'limit':20},{'cursor':None},{'query':'ALL'}):
            with self.assertRaises(ValueError): native_adapter.dispatch(dict(req,**extra),profile)
        for altered in ({'repository':'unknown'},{'snapshotId':'a'*64},{'action':'PAGE'}):
            with self.assertRaises(ValueError): native_adapter.dispatch(dict(req,**altered),profile)
        p=json.loads(profile.read_text());p['repositories']={};profile.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError,'REPO_OUTSIDE_OPERATOR_SCOPE'): native_adapter.dispatch(req,profile)

    def test_A16_lossless_keyset_scope_and_both_byte_envelopes(self):
        self.capture({f'{n:02}.txt':b'data' for n in range(45)})
        first=self.page('PAGE',query='ALL',limit=20,cursor=None)
        cursor=first['next_cursor']
        for changed in ({'query':'GAPS'},{'snapshotId':'a'*64},{'classifierVersion':'old'}):
            with self.assertRaisesRegex(ValueError,'COVERAGE_CURSOR_SCOPE_MISMATCH'):
                self.page('PAGE',query='ALL',limit=20,cursor=dict(cursor,**changed))
        for bad in ('01','-1','1e6',9007199254740993,'9223372036854775808'):
            with self.assertRaises(ValueError): self.page('PAGE',query='ALL',limit=20,cursor=dict(cursor,afterOrdinal=bad))
        for large in ('1000001','9007199254740993','9223372036854775807'):
            self.assertEqual(self.page('PAGE',query='ALL',limit=20,cursor=dict(cursor,afterOrdinal=large))['rows'],[])
        # Inflate supported metadata labels, retaining their exact binding.
        db=repo.db_for(self.store)
        try:
            with db:
                for row in list(db.execute('SELECT * FROM repo_entries')):
                    changed=dict(row,reason='Я'*1000)
                    facts=eligibility.make_facts(self.sid,changed,eligibility.classify_chunks([b'data']),'TEXT_ONLY')
                    db.execute('UPDATE repo_entries SET reason=? WHERE snapshot_id=? AND path=?',(changed['reason'],self.sid,row['path']))
                    eligibility.write_facts(db,{'id':self.sid},changed,facts)
        finally:db.close()
        rows,pages=self.all_rows();self.assertEqual(len(rows),45);self.assertGreater(pages,3)
        db=repo.db_for(self.store)
        try:
            with db:
                row=dict(db.execute('SELECT * FROM repo_entries ORDER BY ordinal LIMIT 1').fetchone(),reason='Я'*20000)
                db.execute('UPDATE repo_entries SET reason=? WHERE ordinal=0',(row['reason'],))
                eligibility.write_facts(db,{'id':self.sid},row,eligibility.make_facts(self.sid,row,eligibility.classify_chunks([b'data']),'TEXT_ONLY'))
        finally:db.close()
        with self.assertRaisesRegex(ValueError,'ROW_ENVELOPE_LIMIT'):self.page('PAGE',query='ALL',limit=20,cursor=None)

    def test_A18_raw_manifest_bytes_and_revisions_are_unchanged_by_backfill(self):
        self.capture({'binary.bin':b'printable\n'*900+b'\xff','empty.txt':b''})
        self.legacy()
        a,b=self.root/'manifest-a',self.root/'manifest-b'
        manifest.publish(self.store,'code',self.sid,'sce',self.profile,a)
        self.backfill()
        manifest.publish(self.store,'code',self.sid,'sce',self.profile,b)
        for name in manifest.ARTIFACTS:self.assertEqual((a/name).read_bytes(),(b/name).read_bytes())
        self.assertEqual(self.page()['summary']['raw_integrity'],'NOT_RUN')
        self.assertIsNone(self.page()['summary']['all_tracked_bytes_exportable'])
        import repo_archive
        output = self.root / 'archives'
        receipt = repo_archive.build(self.profile_file(), 'sce', b, output)
        self.assertTrue(receipt['captured_export_complete'])
        archive = next(output.glob('REPO_*.zip'))
        parts = [json.loads(r) for r in (b/'PARTS_INDEX.jsonl').read_text().splitlines()]
        with zipfile.ZipFile(archive) as z:
            binary = b''.join(z.read('parts/'+p['part_id']+'.bin') for p in parts if p['path']=='binary.bin')
        self.assertEqual(binary, b'printable\n'*900+b'\xff')

    def test_legacy_printable_items_remain_historical_but_all_current_text_paths_gate(self):
        self.capture({'a.bin':b'matchlegacy\n'*500+b'\0','z.txt':b'matchlegacy eligible'})
        self.legacy()
        db=repo.db_for(self.store)
        try:
            with db:
                snap=repo.load_snapshot(db,'code',self.sid)
                c=db.execute("SELECT * FROM repo_chunks WHERE path='a.bin' AND ordinal=0").fetchone()
                item_id=core.digest([self.sid,c['revision']])
                item=dict(id=item_id,schema_version='occ.git-source.v1',namespace='code',source_key='git:sce:'+c['logical_id'],
                    text=c['raw'].decode(),input_sha256=repo.sha(c['raw']),file_sha256=db.execute("SELECT file_hash FROM repo_entries WHERE path='a.bin'").fetchone()[0],
                    path='a.bin',repo_sha=snap['head'],logical_id=c['logical_id'],revision=c['revision'],byte_start=c['byte_start'],byte_end=c['byte_end'],
                    start_line=c['start_line'],end_line=c['end_line'],oversized_fragment=True,authority='DATA_ONLY')
                _insert_item(db,item)
                db.execute("UPDATE repo_chunks SET item_id=? WHERE path='a.bin' AND ordinal=0",(item_id,))
                repo._publish_snapshot_db(db,snap)
        finally:db.close()
        with self.assertRaisesRegex(ValueError,'FORMAT_BACKFILL_REQUIRED'):core.context_pack(self.store,'code',[item_id])
        self.backfill()
        hits=core.search(self.store,'code','matchlegacy',1);self.assertEqual(len(hits),1)
        self.assertEqual(core.context_pack(self.store,'code',[hits[0]['id']])['items'][0]['path'],'z.txt')
        with self.assertRaisesRegex(ValueError,'BINARY_CONTROL_BYTES'):core.context_pack(self.store,'code',[item_id])
        chosen=repo.selection(self.store,'code',self.sid,['a.bin','z.txt'])
        self.assertEqual(chosen['omitted_sources'][0]['reason'],'BINARY_CONTROL_BYTES')
        db=repo.db_for(self.store);self.assertIsNotNone(db.execute('SELECT 1 FROM items WHERE id=?',(item_id,)).fetchone());db.close()

    def test_installed_isolated_backfill_cli_and_native_pages(self):
        self.capture({'old.txt':b'old exact text'})
        self.legacy()
        lab=Path(repo.__file__).parent;installer=(lab.parent/'agent-bridge/Install.ps1').read_text()
        names=re.findall(r"'([^']+)'",re.search(r'foreach\(\$occFile in @\((.*?)\)\)',installer).group(1))
        installed=self.root/'installed';installed.mkdir()
        for name in names:shutil.copyfile(lab/name,installed/name)
        profile=self.profile_file()
        command=[sys.executable,'-I','-X','utf8',str(installed/'source_eligibility.py'),'--profile',str(profile),'--repository','sce','--snapshot',self.sid,'--backfill','--max-entries','1']
        result=subprocess.run(command,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout)['summary']['state'],'READY')
        request=dict(type='durable.repo.coverage',repository='sce',snapshotId=self.sid,action='PAGE',query='ALL',limit=20,cursor=None)
        result=subprocess.run([sys.executable,'-I','-X','utf8',str(installed/'native_adapter.py'),'--profile',str(profile)],input=json.dumps(request).encode(),capture_output=True,check=True)
        value=json.loads(result.stdout);self.assertTrue(value['ok'],value);self.assertEqual(value['result']['coverage']['rows'][0]['path'],'old.txt')

    def test_pending_scan_missing_rows_wrong_binding_and_policy_generation(self):
        self.put('a.txt',b'a');self.commit();self.sid=repo.start_scan(self.store,'sce',self.profile)
        self.assertEqual(self.page()['summary']['state'],'SCAN_PENDING')
        repo.scan_page(self.store,'code',self.sid)
        self.mutate("UPDATE repo_entries SET analysis=json_set(analysis,'$.format_eligibility.classifier_version','future')")
        self.assertEqual(self.page()['summary']['state'],'FORMAT_FACTS_PENDING')
        self.backfill();self.assertEqual(self.page()['summary']['state'],'READY')
        self.mutate("UPDATE repo_entries SET analysis=json_set(analysis,'$.format_eligibility._binding','wrong')")
        self.assertEqual(self.page()['summary']['state'],'CORRUPT_FACTS')
        self.backfill();self.mutate('DELETE FROM repo_entries')
        self.assertEqual(self.page()['summary']['state'],'CORRUPT_FACTS')

    def test_single_sqlite_read_view_survives_concurrent_fact_update(self):
        self.capture({'a.txt':b'one'})
        db=repo.db_for(self.store);db.execute('PRAGMA journal_mode=WAL');db.close()
        original=coverage.summary_db
        def update_after_summary(db,snap):
            result=original(db,snap)
            writer=repo.db_for(self.store)
            try:
                with writer:
                    row=dict(writer.execute('SELECT * FROM repo_entries').fetchone(),reason='new metadata')
                    writer.execute('UPDATE repo_entries SET reason=?',(row['reason'],))
                    eligibility.write_facts(writer,snap,row,eligibility.make_facts(self.sid,row,eligibility.classify_chunks([b'one']),'TEXT_ONLY'))
            finally:writer.close()
            return result
        with mock.patch.object(coverage,'summary_db',side_effect=update_after_summary):
            page=self.page('PAGE',query='ALL',limit=20,cursor=None)
        self.assertIsNone(page['rows'][0]['legacy_reason'])
        self.assertEqual(self.all_rows()[0][0]['legacy_reason'],'new metadata')

    def test_new_large_source_is_classified_before_any_text_items_and_keeps_progress(self):
        raw=b'printable\n'*(repo.AST_WINDOW_BYTES//10+50)+b'\0'
        with mock.patch.object(repo,'pulse',wraps=repo.pulse) as pulse:
            self.capture({'large.bin':raw})
            self.assertGreater(pulse.call_count,100)
        db=repo.db_for(self.store)
        try:
            chunks=list(db.execute('SELECT item_id,raw FROM repo_chunks ORDER BY ordinal'))
            self.assertTrue(all(c['item_id'] is None for c in chunks))
            self.assertEqual(b''.join(c['raw'] for c in chunks),raw)
        finally:db.close()
        self.assertEqual(self.all_rows()[0][0]['format_kind'],'BINARY_CONTROL_HEURISTIC')
