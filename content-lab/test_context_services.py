"""Independent local qualification: exact bytes, binding, recovery and fences."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import automation_core as core
import context_library as lib
import context_packets as packets
import context_recovery as recovery
import context_runtime as runtime
import native_adapter


class Services(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=self.root/'store';packets.db_for(self.store).close()
        self.profile={'destination_id':'manual','destination_revision':'1','policy_revision':'1','source_keys':['source','second'],'protected_literals':['TOP_SECRET_CANARY']}
        self.c={'namespace':'n','input_roots':[str(self.root)],'output_roots':[str(self.root)],'destinations':{'manual':self.profile},'actions':list(runtime.WRITES),'qualification_path':str(self.root/'qualification.json')}
        self.policy={'schema':'occ.automation-policy.v1','max_parallel':1,'money_budget':0,'context_services':{'local':self.c}}
        self.write_qualification()
    def tearDown(self):self.temp.cleanup()
    def write_qualification(self):
        raw=b'Operator-owned local qualification log';(self.root/'qualification.log').write_bytes(raw)
        (self.root/'qualification.json').write_bytes(lib.encoded({'schema':'occ.context-qualification.v1','build_digest':runtime.build_digest(),'grant_digest':lib.digest(self.c),'status':'PASS','test_count':1,'log_sha256':lib.sha(raw),'log_file':'qualification.log','platform':sys.platform,'device_qualification':'NOT_RUN'}))
    def capture(self,raw=b'first\r\nsecond\n',key='source',op='capture'):
        p=self.root/(key+'.bin');p.write_bytes(raw);r=lib.import_file(self.store,'n',key,p,op);return r,lib.source_ref(self.store,'n',r['revision'])
    def packet(self,raw=b'first\r\nsecond\n',part_bytes=4,goal='goal'):
        captured,ref=self.capture(raw)
        selection=packets.create_selection(self.store,'n',[{'source_ref':ref,'reason':'source supports criterion'}])
        result=packets.compile_task_document(self.store,'n',selection['selection_id'],goal,['criterion'], 'build',part_bytes=part_bytes)
        return captured,ref,result
    def test_raw_crlf_unicode_and_hashes(self):
        raw=('Привет\r\n🙂é\n'*900).encode();cap,ref=self.capture(raw)
        got=bytearray()
        for start in range(0,len(raw),8192):got.extend(base64.b64decode(lib.read_span(self.store,'n',{**ref,'start':start,'end':min(start+8192,len(raw))})['base64']))
        self.assertEqual(bytes(got),raw);self.assertEqual(cap['sha256'],hashlib.sha256(raw).hexdigest())
    def test_capture_idempotency_and_conflict(self):
        cap,ref=self.capture();self.assertEqual(cap,lib.import_file(self.store,'n','source',self.root/'source.bin','capture'))
        with self.assertRaisesRegex(ValueError,'IDEMPOTENCY_CONFLICT'):lib.import_file(self.store,'n','second',self.root/'source.bin','capture')
    def test_capture_drift_does_not_publish(self):
        cap,_=self.capture(b'original');p=self.root/'changed.bin';p.write_bytes(b'A'*20_000);called=[0]
        def drift():
            called[0]+=1
            if called[0]==2:p.write_bytes(b'B'*20_000)
        with self.assertRaisesRegex(ValueError,'SOURCE_DRIFT'):lib.import_file(self.store,'n','source',p,'drift',progress=drift)
        self.assertEqual(lib.search_sources(self.store,'n')['rows'][0]['source_ref']['revision'],cap['revision'])
    def test_capture_resume_and_tombstone_late_publication(self):
        p=self.root/'large';p.write_bytes(b'A'*20_000);calls=[0]
        def crash():
            calls[0]+=1
            if calls[0]==2:raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):lib.import_file(self.store,'n','source',p,'resume',progress=crash)
        self.assertEqual(lib.search_sources(self.store,'n')['state'],'NO_MATCH')
        r=lib.import_file(self.store,'n','source',p,'resume');self.assertEqual(r['bytes'],20_000)
        lib.tombstone(self.store,'n','source','delete')
        with self.assertRaisesRegex(ValueError,'SOURCE_TOMBSTONED'):lib.import_file(self.store,'n','source',p,'late')
    def test_namespace_and_invalid_ranges(self):
        _,ref=self.capture()
        with self.assertRaisesRegex(ValueError,'OUT_OF_SCOPE'):lib.read_span(self.store,'other',ref)
        with self.assertRaises(ValueError):lib.read_span(self.store,'n',{**ref,'start':True})
        with self.assertRaises(ValueError):lib.read_span(self.store,'n',{**ref,'end':999})
    def test_packet_more_than_1000_parts_and_immutable_parent(self):
        raw=b'12345678'*600;_,ref,packet=self.packet(raw,part_bytes=4)
        offset=0;got=bytearray();count=0
        while True:
            page=packets.metadata_page(self.store,'n',packet['packet_id'],offset=offset,limit=100)
            for r in page['rows']:got.extend(base64.b64decode(packets.read_document_part(self.store,'n',packet['packet_id'],r['ordinal'])['base64']));count+=1
            if page['next_offset'] is None:break
            offset=page['next_offset']
        self.assertEqual(bytes(got),raw);self.assertGreater(count,1000)
        meta=packets.metadata_page(self.store,'n',packet['packet_id'],kind='INFO')['metadata'];self.assertFalse(meta['dispatch_allowed']);self.assertFalse(meta['criterion_verified'])
    def test_selection_append_remove_preserves_previous(self):
        _,ref=self.capture();first=packets.create_selection(self.store,'n',[{'source_ref':ref,'reason':'first'}])
        second=packets.create_selection(self.store,'n',[{'source_ref':{**ref,'end':4},'reason':'second'}],parent=first['selection_id'])
        removed=packets.remove_selected_range(self.store,'n',second['selection_id'],0)
        self.assertEqual((first['count'],second['count'],removed['count']),(1,2,1))
    def test_share_secret_across_parts_and_metadata(self):
        raw=b'prefix TOP_SECRET_CANARY suffix';_,ref,packet=self.packet(raw,goal='Hide TOP_SECRET_CANARY')
        profile={**self.profile,'protected_literals':['TOP_SECRET_CANARY']}
        projection=packets.create_share_projection(self.store,'n',packet['packet_id'],profile,'project')
        out=self.root/'export';packets.export_projection(self.store,'n',projection['projection_id'],out,profile)
        for p in out.rglob('*'):
            if p.is_file():self.assertNotIn(b'TOP_SECRET_CANARY',p.read_bytes())
        self.assertEqual(base64.b64decode(packets.read_document_part(self.store,'n',packet['packet_id'],2)['base64']),raw[8:12])
        (out/'unexpected').write_text('untracked')
        with self.assertRaisesRegex(ValueError,'EXPORT_UNTRACKED_FILE'):packets.verify_export(out)
    def test_export_profile_change_or_delete_blocks_publish(self):
        _,ref,packet=self.packet();projection=packets.create_share_projection(self.store,'n',packet['packet_id'],self.profile,'project')
        with self.assertRaisesRegex(ValueError,'SHARE_PROFILE_CHANGED'):packets.export_projection(self.store,'n',projection['projection_id'],self.root/'out',{**self.profile,'policy_revision':'2'})
        lib.tombstone(self.store,'n','source','delete')
        with self.assertRaisesRegex(ValueError,'SOURCE_TOMBSTONED'):packets.export_projection(self.store,'n',projection['projection_id'],self.root/'out',self.profile)
        self.assertFalse((self.root/'out').exists())
    def result(self,ref,p):
        meta=packets.metadata_page(self.store,'n',p['packet_id'],kind='INFO')['metadata']
        return {'schema':'occ.context-result.v1','packet_id':p['packet_id'],'packet_digest':p['packet_digest'],'criteria_revision':meta['criteria_revision'],'claims':[{'criterion':'criterion','statement':'DONE','citations':[ref]}],'artifacts':[],'gaps':[]}
    def test_ai_result_never_authorizes_done_or_execution(self):
        _,ref,p=self.packet();value=self.result(ref,p);r=packets.import_result(self.store,'n','result',lib.encoded(value))
        self.assertEqual(r['state'],'PROPOSAL_ONLY');self.assertFalse(r['criterion_verified']);self.assertFalse(r['dispatch_allowed'])
        value['command']=['rm','-rf','/'];self.assertEqual(packets.import_result(self.store,'n','injection',lib.encoded(value))['state'],'UNBOUND')
        malformed=b'\xffpartial';self.assertEqual(packets.import_result(self.store,'n','malformed',malformed)['state'],'UNBOUND')
        with lib.view(self.store) as db:self.assertEqual(base64.b64decode(json.loads(db.execute("SELECT payload FROM context_claims WHERE result_id='malformed'").fetchone()[0])['raw_base64']),malformed)
    def test_stale_result_and_unknown_criterion(self):
        _,ref,p=self.packet();value=self.result(ref,p);self.capture(b'new revision',op='new')
        self.assertEqual(packets.import_result(self.store,'n','stale',lib.encoded(value))['state'],'STALE')
        value['claims'][0]['criterion']='foreign';self.assertEqual(packets.import_result(self.store,'n','foreign',lib.encoded(value))['state'],'UNBOUND')
    def test_need_context_binding_scope_and_retry(self):
        _,ref,p=self.packet();meta=packets.metadata_page(self.store,'n',p['packet_id'],kind='INFO')['metadata']
        req={'request_id':'need','packet_id':p['packet_id'],'packet_digest':p['packet_digest'],'criteria_revision':meta['criteria_revision'],'criterion_id':'criterion','source_ref':{**ref,'start':2,'end':7},'reason':'specific gap'}
        a=packets.need_context(self.store,'n',req);self.assertEqual(a,packets.need_context(self.store,'n',req));self.assertEqual(base64.b64decode(a['response']['base64']),b'rst\r\n')
        with self.assertRaisesRegex(ValueError,'NEED_CONTEXT_CRITERION'):packets.need_context(self.store,'n',{**req,'criterion_id':'unknown'})
    def test_temporal_scope_history_and_correction(self):
        _,ref=self.capture(b'old decision');ann={'project':'p','valid_from':10,'valid_until':20,'supersedes':None,'conflict_group':'g','note':'prior'};lib.annotate(self.store,'n',ref,ann,'ann1')
        _,new=self.capture(b'new decision',op='new');lib.annotate(self.store,'n',new,{**ann,'valid_from':20,'valid_until':None,'supersedes':ref['revision'],'note':'correction'},'ann2')
        old=lib.search_sources(self.store,'n','decision',as_of=15,project='p');now=lib.search_sources(self.store,'n','decision',as_of=21,project='p')
        self.assertEqual(old['rows'][0]['source_ref']['revision'],ref['revision']);self.assertTrue(old['rows'][0]['historical']);self.assertEqual(now['rows'][0]['source_ref']['revision'],new['revision'])
        self.assertEqual(lib.search_sources(self.store,'n',project='other')['state'],'NO_MATCH')
    def test_backup_concurrent_writer_and_restore_tombstone(self):
        _,ref,p=self.packet();ticks=[0]
        def writer():
            ticks[0]+=1
            with lib.view(self.store,write=True) as db:lib.record_event(db,'n','WRITER',{'tick':ticks[0]})
        backup=self.root/'backup';recovery.snapshot_backup(self.store,backup,progress=writer);self.assertGreater(ticks[0],0)
        self.assertEqual(recovery.verify_backup(backup)['state'],'VERIFIED_COMPLETE')
        lib.tombstone(self.store,'n','source','delete');copy=self.root/'restore';r=recovery.restore_to_copy(backup,copy,current_store=self.store)
        self.assertFalse(r['dispatch_allowed']);self.assertEqual(lib.search_sources(copy,'n')['state'],'NO_MATCH')
        self.assertTrue(core.Core(copy,self.policy).control_status()['stopped'])
    def test_corrupt_backup_and_packet_bytes_rejected(self):
        _,ref,p=self.packet();backup=self.root/'backup';recovery.snapshot_backup(self.store,backup)
        with (backup/'content.sqlite3').open('r+b') as f:f.seek(100);f.write(b'BAD')
        with self.assertRaisesRegex(ValueError,'BACKUP_HASH'):recovery.verify_backup(backup)
        with lib.view(self.store,write=True) as db:db.execute('UPDATE context_packet_parts SET raw=? WHERE ordinal=0',(b'evil',))
        with self.assertRaisesRegex(ValueError,'BACKUP_PACKET_CORRUPT'):recovery.snapshot_backup(self.store,self.root/'bad')
    def test_offline_sync_replay_conflicts_and_deletion(self):
        _,ref=self.capture();bundle=self.root/'sync';recovery.export_sync(self.store,'n',bundle);other=self.root/'other';packets.db_for(other).close()
        first=recovery.import_sync(other,'n',bundle);again=recovery.import_sync(other,'n',bundle);self.assertEqual(first['records'],again['records']);self.assertFalse(again['dispatch_allowed'])
        raw=b'local competing';path=self.root/'competing';path.write_bytes(raw);lib.import_file(other,'n','source',path,'local')
        self.assertGreater(recovery.import_sync(other,'n',bundle)['conflicts'],0)
        lib.tombstone(self.store,'n','source','delete');deleted=self.root/'deleted';recovery.export_sync(self.store,'n',deleted);recovery.import_sync(other,'n',deleted);self.assertEqual(lib.search_sources(other,'n')['state'],'NO_MATCH')
    def test_corrupt_sync_is_atomic(self):
        self.capture();bundle=self.root/'sync';recovery.export_sync(self.store,'n',bundle)
        path=bundle/'RECORDS.jsonl';rows=[json.loads(x) for x in path.read_bytes().splitlines()]
        for r in rows:
            if r['table']=='context_raw_parts':r['record']['raw']['base64']=base64.b64encode(b'bad').decode()
        raw=b''.join(lib.encoded(r)+b'\n' for r in rows);path.write_bytes(raw);m=json.loads((bundle/'MANIFEST.json').read_bytes());m['sha256']=lib.sha(raw);(bundle/'MANIFEST.json').write_bytes(lib.encoded(m))
        other=self.root/'other';packets.db_for(other).close()
        with self.assertRaisesRegex(ValueError,'SYNC_BLOB_CORRUPT'):recovery.import_sync(other,'n',bundle)
        with lib.view(other) as db:self.assertEqual(db.execute('SELECT count(*) FROM context_sources').fetchone()[0],0)
    def test_core_registered_job_and_logical_retry(self):
        p=self.root/'input';p.write_bytes(b'from Core');args={'path':str(p),'source_key':'source'}
        j=runtime.submit(self.store,self.policy,'local','CAPTURE',args,'core-capture');self.assertEqual(j['state'],'QUEUED')
        result=core.Core(self.store,self.policy).run_once();self.assertEqual(result['state'],'SUCCEEDED',result['result'])
        again=runtime.submit(self.store,self.policy,'local','CAPTURE',args,'core-capture');self.assertEqual(j['job_id'],again['job_id'])
        observed=runtime.query(self.store,self.policy,'local','OPERATION',{'operation_id':'core-capture'});self.assertEqual(observed['result']['bytes'],9)
    def test_qualification_grant_change_and_path_scope(self):
        self.assertEqual(runtime.capabilities(self.c)['qualification'],'LOCAL_TESTS_VERIFIED')
        self.c['actions'].remove('CAPTURE');self.assertEqual(runtime.capabilities(self.c)['qualification'],'STALE')
        with self.assertRaisesRegex(ValueError,'PATH_OUTSIDE_OPERATOR_SCOPE'):runtime.submit(self.store,self.policy,'local','RESULT',{'path':'/outside/data.json','result_id':'r'},'r')
        with self.assertRaisesRegex(ValueError,'CONTEXT_ACTION_NOT_GRANTED'):runtime.submit(self.store,self.policy,'local','CAPTURE',{'path':str(self.root/'x'),'source_key':'source'},'x')
    def test_stop_fences_queue_and_independent_running_job(self):
        p=self.root/'input';p.write_bytes(b'data');args={'path':str(p),'source_key':'source'};j=runtime.submit(self.store,self.policy,'local','CAPTURE',args,'running');runner=core.Core(self.store,self.policy);claimed=runner.claim()
        receipt=runner.stop('stop');self.assertEqual(receipt['control_ack'],'DURABLE_FENCED');self.assertEqual(receipt,runner.stop('stop'))
        self.assertEqual(runner.get(j['job_id'])['state'],'RUNNING')
        with self.assertRaises(core.Cancelled):runner.heartbeat(claimed)
        with self.assertRaisesRegex(ValueError,'CORE_STOPPED'):runtime.submit(self.store,self.policy,'local','CAPTURE',args,'new')
        with self.assertRaisesRegex(ValueError,'RECONCILIATION_REQUIRED'):runner.resume_control(receipt['epoch'])
    def test_desktop_profile_opt_in_and_scope(self):
        policy=self.root/'policy.json';policy.write_bytes(lib.encoded(self.policy));profile=self.root/'profile.json';obj={'schema':'occ.native-durable-profile.v1','store':str(self.store),'policy_file':str(policy),'namespaces':['n'],'templates':{},'context_service':'local'};profile.write_bytes(lib.encoded(obj))
        info=native_adapter.dispatch_desktop({'type':'durable.info'},profile);self.assertIn('durable.library',info['result']['info']['capabilities']);self.assertIsNotNone(info['adapter_context']['backend_bundle_sha256'])
        reply=native_adapter.dispatch_desktop({'type':'durable.library','namespace':'n','action':'SEARCH','arguments':{'query':''}},profile);self.assertTrue(reply['ok'],reply)
        reply=native_adapter.dispatch_desktop({'type':'durable.library','namespace':'wrong','action':'SEARCH','arguments':{'query':''}},profile);self.assertEqual(reply['error'],'DURABLE_NAMESPACE_OUTSIDE_SCOPE')
    def test_stop_epoch_prevents_old_partial_intent_after_resume(self):
        file=self.root/'big';file.write_bytes(b'A'*20_000);calls=[0]
        def crash():
            calls[0]+=1
            if calls[0]==2:raise RuntimeError('interrupted')
        with self.assertRaises(RuntimeError):lib.import_file(self.store,'n','source',file,'old',progress=crash)
        runner=core.Core(self.store,self.policy);receipt=runner.stop('stop');runner.resume_control(receipt['epoch'])
        with self.assertRaisesRegex(ValueError,'STOP_EPOCH_CHANGED'):lib.import_file(self.store,'n','source',file,'old')
        self.assertEqual(lib.search_sources(self.store,'n')['state'],'NO_MATCH')
    def test_stop_busy_store_is_unconfirmed_instead_of_false_success(self):
        owner=lib.db_for(self.store);owner.execute('BEGIN IMMEDIATE')
        started=time.monotonic()
        try:
            with self.assertRaises(sqlite3.OperationalError):core.Core(self.store,self.policy).stop('locked')
        finally:owner.rollback();owner.close()
        self.assertLess(time.monotonic()-started,2)
        self.assertFalse(core.Core(self.store,self.policy).control_status()['stopped'])
    def test_new_tombstone_after_restore_rehearsal_survives_activation(self):
        self.capture();backup=self.root/'backup';copy=self.root/'restore';recovery.snapshot_backup(self.store,backup);recovery.restore_to_copy(backup,copy,current_store=self.store)
        lib.tombstone(self.store,'n','source','after-rehearsal')
        r=recovery.activate_restored_copy(self.store,copy,process_stopped=True)
        self.assertEqual(r['state'],'ACTIVATED');self.assertEqual(lib.search_sources(self.store,'n')['state'],'NO_MATCH');self.assertTrue((self.store/'content.pre-restore.sqlite3').exists());self.assertTrue(core.Core(self.store,self.policy).control_status()['stopped'])
    def test_activation_rename_failure_marker_and_explicit_recovery(self):
        self.capture();backup=self.root/'backup';copy=self.root/'restore';recovery.snapshot_backup(self.store,backup);recovery.restore_to_copy(backup,copy,current_store=self.store)
        original=recovery.os.rename;calls=[0]
        def fail(source,target):
            calls[0]+=1
            if calls[0]==2:raise OSError('simulated rename failure')
            return original(source,target)
        with patch.object(recovery.os,'rename',side_effect=fail):
            with self.assertRaises(OSError):recovery.activate_restored_copy(self.store,copy,process_stopped=True)
        with self.assertRaisesRegex(ValueError,'STORE_MAINTENANCE_REQUIRED'):lib.search_sources(self.store,'n')
        self.assertEqual(recovery.recover_activation(self.store,process_stopped=True)['state'],'RECOVERED')
        self.assertTrue(core.Core(self.store,self.policy).control_status()['stopped'])
    def test_existing_browser_search_after_capture_and_sync(self):
        self.capture(b'canonical compatibility needle');self.assertEqual(len(core.search(self.store,'n','needle')),1)
        bundle=self.root/'sync';recovery.export_sync(self.store,'n',bundle);other=self.root/'other';packets.db_for(other).close();recovery.import_sync(other,'n',bundle)
        result=core.search(other,'n','needle');self.assertEqual(len(result),1);self.assertEqual(core.context_pack(other,'n',[result[0]['id']])['items'][0]['text'],'canonical compatibility needle')
    def test_duplicate_and_nonfinite_inputs_quarantined(self):
        for i,raw in enumerate((b'{"schema":"x","schema":"y"}',b'{"number":1e999}',b'{"number":NaN}')):
            self.assertEqual(packets.import_result(self.store,'n','invalid-'+str(i),raw)['state'],'UNBOUND')
    def test_purge_retains_tombstone_and_refuses_dependent_packet(self):
        self.capture();lib.tombstone(self.store,'n','source','deleted');r=recovery.purge_tombstoned_source(self.store,'n','source','purge');self.assertTrue(r['tombstone_retained'])
        with lib.view(self.store) as db:self.assertEqual(db.execute('SELECT count(*) FROM context_raw_parts').fetchone()[0],0);self.assertEqual(db.execute('SELECT count(*) FROM items').fetchone()[0],0)
        self.capture(b'new source','second','capture-second');ref=lib.search_sources(self.store,'n')['rows'][0]['source_ref'];sid=packets.create_selection(self.store,'n',[{'source_ref':ref,'reason':'retain'}])['selection_id'];packets.compile_task_document(self.store,'n',sid,'g',['criterion'],'retained');lib.tombstone(self.store,'n','second','deleted-second')
        self.assertEqual(lib.deletion_impact(self.store,'n','second')['dependent_packets'],1)
        with self.assertRaisesRegex(ValueError,'DEPENDENT_PACKET_RETENTION_REQUIRED'):recovery.purge_tombstoned_source(self.store,'n','second','blocked-purge')

    def test_read_only_query_does_not_migrate(self):
        self.capture();before=(self.store/'content.sqlite3').read_bytes();lib.search_sources(self.store,'n');self.assertEqual((self.store/'content.sqlite3').read_bytes(),before)
    def test_packet_interrupted_build_resumes_same_bytes(self):
        cap,ref=self.capture(b'0123456789'*200);sid=packets.create_selection(self.store,'n',[{'source_ref':ref,'reason':'all'}])['selection_id'];calls=[0]
        def crash():
            calls[0]+=1
            if calls[0]==4:raise RuntimeError('interrupted')
        with self.assertRaises(RuntimeError):packets.compile_task_document(self.store,'n',sid,'g',['criterion'],'resume-build',part_bytes=20,progress=crash)
        r=packets.compile_task_document(self.store,'n',sid,'g',['criterion'],'resume-build',part_bytes=20);self.assertEqual(r['bytes'],2000);self.assertEqual(r['part_count'],100)

if __name__=='__main__':unittest.main(verbosity=2)
