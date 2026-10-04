from __future__ import annotations
import asyncio
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from agentos_lab.context import Vault, partitions
from agentos_lab.ledger import CommitLedger, Conflict, StaleVersion
from agentos_lab.race import Candidate, Effect, Route, diverse_routes, race_to_verified

class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = Vault(self.root)
    def tearDown(self):
        self.temp.cleanup()
    def test_utf8_roundtrip(self):
        data = ('Привет🌍\r\n' * 40).encode()
        sid = self.vault.put(data, 'file://C:/проект/README.md', chunk_bytes=17)
        blocks = self.vault.records(sid)
        self.assertEqual(b''.join(b['text'].encode() for b in blocks), data)
        self.assertTrue(all(b['end']-b['start'] <= 17 for b in blocks))
    def test_bom_roundtrip(self):
        data=b'\xef\xbb\xbfhello\r\n'
        sid=self.vault.put(data,'fixture://bom',chunk_bytes=4)
        self.assertEqual(self.vault.read(sid),data)
    def test_binary_preserved(self):
        data=b'\xff\xfe\x00\x80abc'
        sid=self.vault.put(data,'fixture://binary',chunk_bytes=7)
        self.assertEqual(self.vault.read(sid),data)
        pack=self.vault.compile_pack([sid],'',budget_bytes=200)
        self.assertEqual(pack['omissions'][0]['reason'],'BINARY_NOT_TEXT')
    def test_empty_file_has_partition(self):
        sid=self.vault.put(b'','fixture://empty')
        self.assertEqual(len(self.vault.records(sid)),1)
    def test_dedup_bytes_keeps_two_source_uris(self):
        a=self.vault.put(b'same','fixture://a')
        b=self.vault.put(b'same','fixture://b')
        self.assertNotEqual(a,b)
        self.assertEqual(len(list(self.vault.objects.iterdir())),1)
    def test_same_source_is_idempotent(self):
        a=self.vault.put(b'a','fixture://same')
        self.assertEqual(a,self.vault.put(b'a','fixture://same'))
        self.assertEqual(len(self.vault.records(a)),1)
    def test_metadata_revision_preserved(self):
        a=self.vault.put(b'a','fixture://same',{'valid_from':'t0'})
        b=self.vault.put(b'a','fixture://same',{'valid_from':'t1'})
        self.assertNotEqual(a,b)
    def test_corrupt_original_blocked(self):
        sid=self.vault.put(b'original','fixture://x')
        next(self.vault.objects.iterdir()).write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.vault.read(sid)
    def test_corrupt_chunk_offsets_blocked(self):
        sid=self.vault.put(b'original','fixture://x')
        with self.vault.connect() as con: con.execute('UPDATE chunks SET start=1')
        with self.assertRaises(ValueError): self.vault.records(sid)
    def test_corrupt_normalized_text_blocked(self):
        sid=self.vault.put(b'original','fixture://x')
        with self.vault.connect() as con: con.execute("UPDATE chunks SET text='forged'")
        with self.assertRaises(ValueError): self.vault.records(sid)
    def test_missing_chunk_blocked(self):
        sid=self.vault.put(b'0123456789','fixture://x',chunk_bytes=4)
        with self.vault.connect() as con: con.execute('DELETE FROM chunks WHERE position=1')
        with self.assertRaises(ValueError): self.vault.records(sid)
    def test_budget_omissions_do_not_delete_raw(self):
        sid=self.vault.put(b'abcdefgh','fixture://x',chunk_bytes=4)
        pack=self.vault.compile_pack([sid],'abc',budget_bytes=4)
        self.assertEqual(len(pack['evidence']),1)
        self.assertEqual(len(pack['omissions']),1)
        self.assertEqual(self.vault.read(sid),b'abcdefgh')
    def test_required_evidence_blocks_incomplete_pack(self):
        sid=self.vault.put(b'hello','fixture://x')
        ref=self.vault.records(sid)[0]['ref']
        pack=self.vault.compile_pack([sid],'hello',budget_bytes=0,required_refs=(ref,))
        self.assertEqual(pack['status'],'NEEDS_CONTEXT')
    def test_private_content_does_not_enter_cloud_pack(self):
        sid=self.vault.put(b'private','fixture://x')
        pack=self.vault.compile_pack([sid],'',budget_bytes=200,allow_cloud=True)
        self.assertEqual(pack['evidence'],[])
        self.assertEqual(pack['omissions'][0]['reason'],'PRIVATE_SOURCE_NOT_CLOUD_APPROVED')
    def test_public_content_can_enter_cloud_pack(self):
        sid=self.vault.put(b'public','fixture://x',{'privacy':'public'})
        self.assertEqual(len(self.vault.compile_pack([sid],'',budget_bytes=200,allow_cloud=True)['evidence']),1)
    def test_more_than_twenty_documents(self):
        ids=[self.vault.put(str(i).encode(),f'fixture://{i}') for i in range(65)]
        pack=self.vault.compile_pack(ids,'',budget_bytes=1000)
        self.assertEqual(pack['sources_selected'],65)
        self.assertEqual(len(pack['evidence']),65)
    def test_missing_source_is_explicit(self):
        pack=self.vault.compile_pack(['missing'],'',budget_bytes=100)
        self.assertEqual(pack['omissions'][0]['reason'],'MISSING_SOURCE')
    def test_bad_budgets_rejected(self):
        with self.assertRaises(ValueError): partitions(b'x',3)
        with self.assertRaises(ValueError): self.vault.compile_pack([],'',budget_bytes=-1)
    def test_duplicate_source_selection_not_duplicated(self):
        sid=self.vault.put(b'hello','fixture://x')
        self.assertEqual(len(self.vault.compile_pack([sid,sid],'',budget_bytes=100)['evidence']),1)
    def test_restart_preserves_sources(self):
        sid=self.vault.put(b'persist','fixture://x')
        self.assertEqual(Vault(self.root).read(sid),b'persist')

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'ledger.sqlite3'
        self.ledger=CommitLedger(self.path)
        self.ledger.seed('target',{'x':0})
    def tearDown(self): self.temp.cleanup()
    def test_replay_single_effect(self):
        a=self.ledger.commit('op','target',0,{'x':1},verified=True)
        b=self.ledger.commit('op','target',0,{'x':1},verified=True)
        self.assertEqual(a,b)
        self.assertEqual(self.ledger.operation_count(),1)
    def test_conflicting_payload_rejected(self):
        self.ledger.commit('op','target',0,{'x':1},verified=True)
        with self.assertRaises(Conflict): self.ledger.commit('op','target',0,{'x':2},verified=True)
    def test_stale_second_writer_rejected(self):
        self.ledger.commit('one','target',0,{'x':1},verified=True)
        with self.assertRaises(StaleVersion): self.ledger.commit('two','target',0,{'x':2},verified=True)
    def test_unverified_rejected(self):
        with self.assertRaises(PermissionError): self.ledger.commit('op','target',0,{},verified=False)
        self.assertEqual(self.ledger.operation_count(),0)
    def test_restart_after_commit_replay(self):
        receipt=self.ledger.commit('op','target',0,{'x':1},verified=True)
        self.assertEqual(CommitLedger(self.path).commit('op','target',0,{'x':1},verified=True),receipt)
    def test_concurrent_writers_have_one_winner(self):
        def write(i):
            try:
                return CommitLedger(self.path).commit(str(i),'target',0,{'x':i},verified=True)['revision']
            except StaleVersion: return 'stale'
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(write,[1,2]))
        self.assertEqual(outcomes.count(1),1)
        self.assertEqual(self.ledger.operation_count(),1)
    def test_new_intent_after_new_revision(self):
        self.ledger.commit('op1','target',0,{'x':1},verified=True)
        self.ledger.commit('op2','target',1,{'x':2},verified=True)
        self.assertEqual(self.ledger.read('target'),(2,{'x':2}))
    def test_missing_target_no_receipt(self):
        with self.assertRaises(KeyError): self.ledger.commit('op','absent',0,{},verified=True)
        self.assertEqual(self.ledger.operation_count(),0)

class RaceTests(unittest.IsolatedAsyncioTestCase):
    def route(self,name,domain,delay=0,revision=0,effect=Effect.READ):
        async def run():
            await asyncio.sleep(delay)
            return Candidate(name,revision,{'ok':True},('fixture',))
        return Route(name,domain,effect,run)
    async def verify(self,c): return c.snapshot_revision==0,'snapshot check'
    async def test_fast_invalid_does_not_win(self):
        result=await race_to_verified([self.route('bad','cache',0,1),self.route('good','source',.001)],self.verify,hedge_delay=0)
        self.assertEqual(result.winner.route_id,'good')
    async def test_loser_cancelled(self):
        result=await race_to_verified([self.route('good','one'),self.route('slow','two',1)],self.verify,hedge_delay=0)
        self.assertTrue(any(e['state']=='CANCELLED' for e in result.events))
    async def test_external_write_rejected_before_execution(self):
        with self.assertRaises(PermissionError):
            await race_to_verified([self.route('bad','one',effect=Effect.EXTERNAL_WRITE)],self.verify)
    async def test_delayed_hedge_not_started_after_fast_success(self):
        result=await race_to_verified([self.route('fast','one'),self.route('backup','two')],self.verify,hedge_delay=.1)
        self.assertFalse(any(e['route_id']=='backup' and e['state']=='STARTED' for e in result.events))
    async def test_same_failure_domain_deduplicated(self):
        routes=[self.route('a','python_pytest'),self.route('b','python_pytest')]
        self.assertEqual(len(diverse_routes(routes)),1)
    async def test_all_rejected_returns_no_winner(self):
        result=await race_to_verified([self.route('bad','one',revision=1)],self.verify)
        self.assertIsNone(result.winner)
    async def test_deadline_cancels(self):
        result=await race_to_verified([self.route('slow','one',1)],self.verify,deadline=.005)
        self.assertIsNone(result.winner)
    async def test_max_parallel_budget(self):
        live=0; high=0
        def make(i):
            async def run():
                nonlocal live,high
                live+=1; high=max(high,live)
                try: await asyncio.sleep(.002)
                finally: live-=1
                return Candidate(str(i),1,{},())
            return Route(str(i),str(i),Effect.READ,run)
        await race_to_verified([make(i) for i in range(5)],self.verify,max_parallel=2,hedge_delay=0)
        self.assertLessEqual(high,2)
    async def test_route_exception_not_claimed_success(self):
        async def boom(): raise RuntimeError('fixture fault')
        result=await race_to_verified([Route('broken','a',Effect.READ,boom),self.route('good','b')],self.verify,hedge_delay=0)
        self.assertEqual(result.winner.route_id,'good')
        self.assertTrue(any(e['state']=='ERROR' for e in result.events))
    async def test_route_identity_mismatch_rejected(self):
        async def fake(): return Candidate('wrong',0,{},())
        result=await race_to_verified([Route('expected','one',Effect.READ,fake)],self.verify)
        self.assertIsNone(result.winner)
    async def test_empty_race(self):
        self.assertIsNone((await race_to_verified([],self.verify)).winner)
    async def test_duplicate_route_id_rejected(self):
        with self.assertRaises(ValueError):
            await race_to_verified([self.route('same','a'),self.route('same','b')],self.verify)
    async def test_invalid_timing_rejected(self):
        with self.assertRaises(ValueError): await race_to_verified([],self.verify,deadline=0)

if __name__=='__main__': unittest.main(verbosity=2)
