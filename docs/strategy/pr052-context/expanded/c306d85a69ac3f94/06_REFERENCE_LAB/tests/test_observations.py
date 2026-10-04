from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from agentos_lab.observations import (Observation, ObservationJournal, Producer,
                                     collect_complementary, fuse_claims, readiness)
from agentos_lab.resources import TaskFootprint, can_overlap, independent_batches
from agentos_lab.ledger import Conflict


def obs(producer='dom', seq=0, payload=b'bytes', **kwargs):
    values=dict(session='s1',producer=producer,sequence=seq,source_uri='local://demo/item',
                source_revision='r1',lineage_root='source-item-1',kind='document',
                observed_ns=10+seq,payload=payload,partial=False)
    values.update(kwargs)
    return Observation(**values)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.j=ObservationJournal(Path(self.temp.name)/'capture.sqlite3')

    def test_exact_bytes(self):
        raw=b'\xef\xbb\xbfline\r\n\x00\xff'
        self.j.append(obs(payload=raw))
        self.assertEqual(self.j.read('s1')[0]['payload'],raw)

    def test_unicode_source(self):
        self.j.append(obs(source_uri='file:///C:/проект/🧪.txt',payload='цель'.encode()))
        self.assertIn('проект',self.j.read('s1')[0]['source_uri'])

    def test_same_bytes_keep_provenance(self):
        self.j.append(obs('dom'))
        self.j.append(obs('export'))
        self.assertEqual(len(self.j.read('s1')),2)
        self.assertEqual(self.j.object_count(),1)

    def test_same_event_replay(self):
        self.assertTrue(self.j.append(obs())['inserted'])
        self.assertFalse(self.j.append(obs())['inserted'])
        self.assertEqual(len(self.j.read('s1')),1)

    def test_same_key_different_payload_conflict(self):
        self.j.append(obs())
        with self.assertRaises(Conflict):self.j.append(obs(payload=b'changed'))

    def test_same_key_different_metadata_conflict(self):
        self.j.append(obs())
        with self.assertRaises(Conflict):self.j.append(obs(source_revision='r2'))

    def test_revisions_preserved(self):
        self.j.append(obs())
        self.j.append(obs(seq=1,source_revision='r2'))
        self.assertEqual({x['source_revision'] for x in self.j.read('s1')},{'r1','r2'})

    def test_negative_sequence(self):
        with self.assertRaises(ValueError):self.j.append(obs(seq=-1))

    def test_boolean_sequence_not_integer(self):
        with self.assertRaises(ValueError):self.j.append(obs(seq=True))

    def test_empty_source(self):
        with self.assertRaises(ValueError):self.j.append(obs(source_uri=''))

    def test_payload_requires_bytes(self):
        with self.assertRaises(TypeError):self.j.append(obs(payload='text'))

    def test_restart(self):
        self.j.append(obs())
        other=ObservationJournal(self.j.path)
        self.assertEqual(other.read('s1'),self.j.read('s1'))

    def test_more_than_twenty(self):
        for i in range(57):self.j.append(obs(f'p{i}',payload=str(i).encode()))
        self.assertEqual(len(self.j.read('s1')),57)

    def test_many_threads_shared_raw(self):
        items=[obs(f'p{i}',seq=j) for i in range(4) for j in range(8)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            result=list(pool.map(self.j.append,items))
        self.assertTrue(all(r['inserted'] for r in result))
        self.assertEqual(len(self.j.read('s1')),32)
        self.assertEqual(self.j.object_count(),1)

    def test_concurrent_duplicate_exactly_one_observation(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            result=list(pool.map(self.j.append,[obs()]*16))
        self.assertEqual(sum(r['inserted'] for r in result),1)

    def test_corrupt_raw_detected(self):
        self.j.append(obs())
        with self.j.connect() as con:con.execute('UPDATE raw_objects SET payload=?',(b'broken',))
        with self.assertRaises(ValueError):self.j.read('s1')

    def test_corrupt_header_detected(self):
        self.j.append(obs())
        with self.j.connect() as con:con.execute("UPDATE observations SET header='{}'")
        with self.assertRaises(ValueError):self.j.read('s1')

    def test_missing_producer_explicit(self):
        self.j.append(obs())
        c=self.j.source_coverage('s1',{'dom','export'})
        self.assertEqual(c['missing'],['export'])
        self.assertFalse(c['channel_presence_complete'])

    def test_partial_not_claimed_full(self):
        self.j.append(obs(partial=True))
        c=self.j.source_coverage('s1',{'dom'})
        self.assertEqual(c['partial'],['dom'])
        self.assertFalse(c['full_source_history_proven'])


class CollectorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.j=ObservationJournal(Path(self.temp.name)/'capture.sqlite3')

    async def test_slow_complementary_channel_not_cancelled(self):
        async def a():yield obs('a')
        async def b():
            await asyncio.sleep(.005)
            yield obs('b',payload=b'additional detail')
        result=await collect_complementary(self.j,'s1',[Producer('a',a),Producer('b',b)])
        self.assertEqual(result['new_events'],{'a':1,'b':1})
        self.assertTrue(result['coverage']['channel_presence_complete'])

    async def test_backpressure_does_not_drop(self):
        async def source():
            for i in range(35):yield obs('a',i)
        result=await collect_complementary(self.j,'s1',[Producer('a',source)],max_pending=1)
        self.assertEqual(result['new_events']['a'],35)

    async def test_failure_does_not_hide_other_channel(self):
        async def a():yield obs('a')
        async def b():
            raise RuntimeError('synthetic disconnect')
            yield obs('b')
        result=await collect_complementary(self.j,'s1',[Producer('a',a),Producer('b',b)])
        self.assertEqual(result['statuses']['b'],'ERROR')
        self.assertEqual(result['new_events']['a'],1)
        self.assertEqual(result['coverage']['missing'],['b'])

    async def test_identity_mismatch(self):
        async def a():yield obs('other')
        result=await collect_complementary(self.j,'s1',[Producer('a',a)])
        self.assertEqual(result['statuses']['a'],'ERROR')
        self.assertEqual(self.j.read('s1'),[])

    async def test_partial_stream_error_keeps_prior_events(self):
        async def a():
            yield obs('a')
            raise RuntimeError('later disconnect')
        result=await collect_complementary(self.j,'s1',[Producer('a',a)])
        self.assertEqual(result['statuses']['a'],'ERROR')
        self.assertEqual(len(self.j.read('s1')),1)

    async def test_deadline_reports_interruption(self):
        async def a():
            yield obs('a')
            await asyncio.sleep(10)
        result=await collect_complementary(self.j,'s1',[Producer('a',a)],timeout=.01)
        self.assertEqual(result['statuses']['a'],'INTERRUPTED')
        self.assertEqual(len(self.j.read('s1')),1)

    async def test_duplicate_producer_rejected(self):
        async def a():yield obs('a')
        with self.assertRaises(ValueError):
            await collect_complementary(self.j,'s1',[Producer('a',a),Producer('a',a)])

    async def test_invalid_budget(self):
        with self.assertRaises(ValueError):await collect_complementary(self.j,'s1',[],max_pending=0)

    async def test_consumer_conflict_propagated(self):
        async def a():
            yield obs('a')
            yield obs('a',payload=b'different')
        with self.assertRaises(Conflict):
            await collect_complementary(self.j,'s1',[Producer('a',a)],timeout=.05)


class FusionReadinessTests(unittest.TestCase):
    def claim(self,value='blocked',root='original',ref='r1',revision='sha1'):
        return dict(subject='qualification',predicate='state',value=value,
                    source_revision=revision,lineage_root=root,source_ref=ref)

    def test_copies_not_independent(self):
        out=fuse_claims([self.claim(ref=f'r{i}') for i in range(5)])
        self.assertEqual(out[0]['values'][0]['declared_lineage_count'],1)
        self.assertEqual(len(out[0]['values'][0]['source_refs']),5)

    def test_conflicts_survive_majority(self):
        rows=[self.claim(ref=f'r{i}') for i in range(5)]+[self.claim('ready','different','r6')]
        out=fuse_claims(rows)
        self.assertEqual(out[0]['status'],'CONFLICT')
        self.assertEqual(len(out[0]['values']),2)
        self.assertFalse(out[0]['verified_fact'])

    def test_different_snapshots_not_false_conflict(self):
        out=fuse_claims([self.claim(),self.claim('ready',revision='sha2')])
        self.assertEqual(len(out),2)
        self.assertTrue(all(x['status']=='UNCONTESTED_CLAIM' for x in out))

    def test_incomplete_claim_rejected(self):
        with self.assertRaises(ValueError):fuse_claims([{'value':'x'}])

    def test_ready_is_not_execute_permission(self):
        out=readiness({'code','test'},{'code','test'},snapshot_current=True)
        self.assertEqual(out['state'],'EVIDENCE_READY')
        self.assertFalse(out['execution_authorized'])
        self.assertFalse(out['full_archive_complete'])

    def test_missing_slot_blocks(self):
        self.assertEqual(readiness({'code','test'},{'code'},snapshot_current=True)['missing'],['test'])

    def test_stale_snapshot_blocks(self):
        self.assertEqual(readiness({'code'},{'code'},snapshot_current=False)['state'],'NEEDS_CONTEXT')

    def test_conflict_blocks(self):
        self.assertEqual(readiness({'code'},{'code'},snapshot_current=True,has_blocking_conflict=True)['state'],'NEEDS_CONTEXT')

    def test_empty_contract_rejected(self):
        with self.assertRaises(ValueError):readiness(set(),set(),snapshot_current=True)


class ResourceTests(unittest.TestCase):
    def test_readers_can_parallel(self):
        self.assertTrue(can_overlap(TaskFootprint('a',reads=frozenset({'repo'})),TaskFootprint('b',reads=frozenset({'repo'})))[0])

    def test_distinct_capture_keys_can_parallel(self):
        self.assertTrue(can_overlap(TaskFootprint('a',writes=frozenset({'capture:a:1'})),TaskFootprint('b',writes=frozenset({'capture:b:1'})))[0])

    def test_same_event_key_blocks(self):
        self.assertFalse(can_overlap(TaskFootprint('a',writes=frozenset({'capture:a:1'})),TaskFootprint('b',writes=frozenset({'capture:a:1'})))[0])

    def test_worktree_writers_can_parallel(self):
        self.assertTrue(can_overlap(TaskFootprint('a',writes=frozenset({'worktree:A'})),TaskFootprint('b',writes=frozenset({'worktree:B'})))[0])

    def test_shared_main_blocks(self):
        self.assertFalse(can_overlap(TaskFootprint('a',writes=frozenset({'branch:main'})),TaskFootprint('b',writes=frozenset({'branch:main'})))[0])

    def test_read_write_conflict(self):
        self.assertFalse(can_overlap(TaskFootprint('a',reads=frozenset({'repo'})),TaskFootprint('b',writes=frozenset({'repo'})))[0])

    def test_foreground_lease(self):
        self.assertFalse(can_overlap(TaskFootprint('a',foreground='desktop'),TaskFootprint('b',foreground='desktop'))[0])

    def test_distinct_effects_can_parallel(self):
        self.assertTrue(can_overlap(TaskFootprint('a',writes=frozenset({'report:new'})),TaskFootprint('b',writes=frozenset({'job:isolated'})))[0])

    def test_batch_capacity(self):
        out=independent_batches([TaskFootprint(str(i)) for i in range(7)],2)
        self.assertTrue(all(len(x)<=2 for x in out))
        self.assertEqual(sum(map(len,out)),7)

    def test_batch_conflicting_effects(self):
        out=independent_batches([TaskFootprint('a',writes=frozenset({'main'})),TaskFootprint('b',writes=frozenset({'main'}))],2)
        self.assertEqual(len(out),2)

    def test_duplicate_task_rejected(self):
        with self.assertRaises(ValueError):independent_batches([TaskFootprint('a'),TaskFootprint('a')],2)
