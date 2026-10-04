"""Real Core/SQLite/Git/archive/restart fixtures; no installed device claims."""
import copy
from datetime import date,datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import zipfile

import automation_core as ac
import campaign_runtime as cr
import durable_schedule as ds
import workflow_runtime as wr
import workflow_state as ws
import release_updater as up


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=self.root/'store';self.source=self.root/'source';self.source.mkdir()
        (self.source/'note.txt').write_text('evidence',encoding='utf-8')
        self.policy={'schema':'occ.automation-policy.v1','max_parallel':1,'money_budget':0,
                     'sources':{'notes':{'root':str(self.source),'namespace':'notes'}},'repos':{}}
        self.payload={'kind':'sync','source_profile':'notes'}
        db=ws.connect(self.store);db.close()

    def profile_file(self):
        policy=self.root/'policy.json';policy.write_text(ac.encoded(self.policy),encoding='utf-8')
        profile=self.root/'profile.json';profile.write_text(ac.encoded({'schema':'occ.native-durable-profile.v1','store':str(self.store),'policy_file':str(policy),'namespaces':['notes'],'templates':{'notes':self.payload},'campaigns':list(self.policy.get('campaigns',{}))}),encoding='utf-8')
        return profile

    def schedule(self,**changes):
        value={'schema':ds.SCHEMA,'schedule_id':'daily','revision':1,'enabled':True,'template':'notes','timezone':'Europe/Riga','local_time':'03:30','start_date':'2026-10-24','end_date':'2026-10-26','gap_policy':'SKIP','fold_policy':'BOTH','catch_up':'BOUNDED','catch_up_limit':10}
        return {**value,**changes}

    def utc(self,text):return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()

    def sql(self,query,params=()):
        with ws.transaction(self.store) as db:return [tuple(r) for r in db.execute(query,params)]

    def manifest(self,nodes=None,revision=1):
        inp=self.source/'note.txt'
        node=lambda name,needs=[]:{'id':name,'template':'notes','needs':needs,'inputs':['input'],'resources':[{'id':'writer','mode':'WRITE'}],'demand':{'cpu':1}}
        m={'schema':'occ.campaign.v1','campaign_id':'research','revision':revision,'goal_ids':['GOAL5-20'],'criteria':[{'id':'x','text':'Do not truncate'}],
           'nodes':nodes or [node('read'),node('join',['read'])],
           'limits':{'max_elapsed_seconds':86400,'max_iterations':3,'no_progress_limit':2,'max_transfers':10000}}
        path=self.root/f'manifest-{revision}.json';path.write_text(ac.encoded(m),encoding='utf-8')
        self.policy.setdefault('campaigns',{})['research']={'manifest_file':str(path),'manifest_sha256':ws.file_digest(path),'templates':{'notes':self.payload},'inputs':{'input':{'file':str(inp),'sha256':ws.file_digest(inp)}},'capacity':{'cpu':1},'lease_seconds':300}
        return m

    def brief_config(self,data=None):
        data=data or {'goal_ids':['GOAL5-24'],'criteria':[{'id':'x','text':'Retain old goal'}], 'claims':[], 'trials':[{'outcome':'NEGATIVE'}],
            'gaps':[{'id':'gap','task_id':'G3-010','kind':'MISSING_DEVICE_BINDING','owner':'device owner','dependencies':[], 'acceptance':['exact device receipt'],'recovery':['retain draft'],'source_refs':['original:x'],'priority':10,'revisit_condition':'new receipt'}], 'evidence_delta':'new failure'}
        path=self.root/'brief-input.json';path.write_text(ac.encoded(data),encoding='utf-8')
        return {'input_file':str(path),'input_sha256':ws.file_digest(path),'planner_version':'v1','max_iterations':3,'no_progress_limit':2}

    def operation(self,action,config,key='operation'):
        self.policy.setdefault('workflow_operations',{})[key]={'action':action,'config':config}
        payload={'kind':'workflow_operation','operation_profile':key}
        return ac.enqueue(self.store,self.policy,key,payload)['id']

    def release(self,mode='BOUNDED_QUALIFICATION',files=None,tests=None):
        files=files or {'feature.txt':b'works\n'}
        asset=self.root/'asset.zip'
        with zipfile.ZipFile(asset,'w') as z:
            for n,raw in files.items():z.writestr(n,raw)
        bind={'source_commit':'a'*40,'source_tree':'b'*40,'asset_sha256':ws.file_digest(asset),'data_schema_version':0,
              'files':{n:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for n,raw in files.items()},'capabilities':{'context':{'contract_version':'v1'}},'build_provenance':{'producer':'registered fixture','reproducibility':'NOT_MEASURED'}}
        binding=self.root/'binding.json';binding.write_text(ac.encoded(bind),encoding='utf-8')
        target=self.root/'test-installation';target.mkdir(exist_ok=True)
        (target/'QUALIFICATION_TARGET.json').write_text(ac.encoded({'schema':'occ.isolated-update-target.v1','installation_id':'installation','device_id':'test-device','mode':'TEST_ONLY'}),encoding='utf-8')
        config={'mode':mode,'root':str(target),'device_id':'test-device','installation_id':'installation','asset_file':str(asset),'asset_sha256':ws.file_digest(asset),'binding_file':str(binding),'binding_sha256':ws.file_digest(binding),'source_commit':'a'*40,'source_tree':'b'*40,
                'tests':tests or [[sys.executable,'-B','-c',"from pathlib import Path; assert Path('feature.txt').read_bytes()==b'works\\n'"]],'timeout_seconds':5}
        return config,bind,target

    def git(self,root,*args):
        return subprocess.check_output(['git','-c','user.name=Fixture','-c','user.email=fixture@invalid','-c','commit.gpgSign=false','-c','core.autocrlf=false',*args],cwd=root,stderr=subprocess.DEVNULL).decode('utf-8').strip()

    def merge_fixture(self,method='merge'):
        repo=self.root/'git';repo.mkdir();self.git(repo,'init','-q');self.git(repo,'checkout','-b','target')
        (repo/'value.txt').write_text('base\n',encoding='utf-8');self.git(repo,'add','.');self.git(repo,'commit','-qm','base');base=self.git(repo,'rev-parse','HEAD')
        self.git(repo,'remote','add','origin','https://github.com/example/registered.git')
        self.git(repo,'checkout','-b','proposal');(repo/'value.txt').write_text('candidate\n',encoding='utf-8');self.git(repo,'add','.');self.git(repo,'commit','-qm','proposal');proposal=self.git(repo,'rev-parse','HEAD');tree=self.git(repo,'rev-parse','HEAD^{tree}')
        self.git(repo,'checkout','target')
        if method=='squash':self.git(repo,'merge','--squash','proposal');self.git(repo,'commit','-qm','squash')
        elif method=='manual':
            (repo/'value.txt').write_text('candidate\n',encoding='utf-8');self.git(repo,'add','.');self.git(repo,'commit','-qm','manual')
        elif method=='rebase':
            (repo/'other.txt').write_text('other',encoding='utf-8');self.git(repo,'add','.');self.git(repo,'commit','-qm','advance target');self.git(repo,'cherry-pick',proposal)
        else:self.git(repo,'merge','--no-ff','proposal','-m','merge')
        c={'root':str(repo),'repository_id':'example/registered','remote_identity':'https://github.com/example/registered.git','target_ref':'refs/heads/target','base_commit':base,'proposal_commit':proposal,'expected_tree':tree,
           'tests':[[sys.executable,'-B','-c',"from pathlib import Path; assert Path('value.txt').read_text()=='candidate\\n'"]],'timeout_seconds':5}
        return c,repo


class ResourceTests(Fixture):
    def acquire(self,owner='old',now=100):
        with ws.transaction(self.store) as db:return ws.acquire(db,owner,[{'id':'shared','mode':'WRITE'}],{'ram':10},{'ram':6},now=now,seconds=10)

    def test_atomic_failure_does_not_leave_partial_resource(self):
        with self.assertRaisesRegex(ValueError,'BUDGET_WAIT'),ws.transaction(self.store) as db:ws.acquire(db,'x',[{'id':'shared','mode':'WRITE'}],{'ram':2},{'ram':3},now=100)
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_leases')[0][0],0)
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_reservations')[0][0],0)

    def test_racing_writers_only_one_granted(self):
        def acquire(i):
            try:self.acquire(str(i));return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(acquire,range(2)))
        self.assertEqual(sum(results),1)

    def test_expiry_requires_stop_and_effect_reconciliation(self):
        self.acquire()
        with self.assertRaisesRegex(ValueError,'RECONCILE'):self.acquire('next',111)
        with self.assertRaisesRegex(ValueError,'OBSERVATION'),ws.transaction(self.store) as db:ws.reconcile_stopped(db,'old',process_stopped=True,effects_observed=False,now=111)
        with ws.transaction(self.store) as db:ws.reconcile_stopped(db,'old',process_stopped=True,effects_observed=True,now=111)
        self.assertEqual(self.acquire('next',111)['fences'][0]['epoch'],2)

    def test_old_fence_cannot_commit_after_replacement(self):
        old=self.acquire()
        with ws.transaction(self.store) as db:ws.reconcile_stopped(db,'old',process_stopped=True,effects_observed=True,now=111)
        self.acquire('next',111)
        with self.assertRaisesRegex(ValueError,'FENCE_LOST'),ws.transaction(self.store) as db:ws.check_fence(db,old,111)

    def test_unknown_cost_is_retained(self):
        lease=self.acquire()
        with ws.transaction(self.store) as db:ws.release(db,lease,now=101,unknown=True)
        self.assertEqual(self.sql('SELECT state FROM workflow_reservations')[0][0],'UNKNOWN')
        with self.assertRaises(ValueError):self.acquire('next',102)

    def test_unknown_capacity_is_not_zero(self):
        with self.assertRaisesRegex(ValueError,'CAPACITY_UNKNOWN'),ws.transaction(self.store) as db:ws.acquire(db,'x',[],{'ram':None},{'ram':1},now=100)

    def test_two_immutable_readers_share_resource(self):
        with ws.transaction(self.store) as db:
            for owner in ['a','b']:ws.acquire(db,owner,[{'id':'immutable','mode':'READ'}],{'ram':10},{'ram':1},now=100)
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_leases')[0][0],2)

    def test_canonical_hardlink_alias(self):
        first=self.source/'note.txt';second=self.root/'alias.txt';os.link(first,second)
        self.assertEqual(ws.canonical_resource(first)['id'],ws.canonical_resource(second)['id'])

    def test_unknown_physical_identity_is_conservative(self):
        self.assertEqual(ws.canonical_resource(self.root/'absent-a')['id'],ws.canonical_resource(self.root/'absent-b')['id'])
        self.assertFalse(ws.canonical_resource(self.root/'absent-a')['known'])

    def test_effect_duplicate_and_unknown_no_blind_retry(self):
        with ws.transaction(self.store) as db:
            old=ws.begin_effect(db,'effect','binding');again=ws.begin_effect(db,'effect','binding');self.assertEqual(old,again)
            r=ws.effect_transition(db,'effect','DISPATCHING',1,[]);ws.effect_transition(db,'effect','UNKNOWN_EFFECT',r,[])
        with self.assertRaises(ValueError),ws.transaction(self.store) as db:ws.effect_transition(db,'effect','DISPATCHING',3,[])
        with ws.transaction(self.store) as db:r=ws.effect_transition(db,'effect','NOT_APPLIED',3,['external status absent']);ws.effect_transition(db,'effect','DISPATCHING',r,[])


class ScheduleTests(Fixture):
    def test_riga_fold_has_two_distinct_utc_occurrences(self):
        slots=ds.resolve_slot(self.schedule(),date(2026,10,25));self.assertEqual([s.isoformat() for s in slots],['2026-10-25T00:30:00+00:00','2026-10-25T01:30:00+00:00'])

    def test_fold_policies(self):
        self.assertEqual(len(ds.resolve_slot(self.schedule(fold_policy='FIRST'),date(2026,10,25))),1)
        self.assertEqual(ds.resolve_slot(self.schedule(fold_policy='SECOND'),date(2026,10,25))[0].hour,1)

    def test_gap_skip_and_shift_forward(self):
        self.assertEqual(ds.resolve_slot(self.schedule(),date(2026,3,29)),[])
        slot=ds.resolve_slot(self.schedule(gap_policy='SHIFT_FORWARD'),date(2026,3,29))[0]
        from zoneinfo import ZoneInfo
        self.assertEqual(slot.astimezone(ZoneInfo('Europe/Riga')).hour,4)

    def test_tick_race_canonical_jobs_exactly_once(self):
        profile=self.profile_file();now=self.utc('2026-10-25T02:00:00')
        with ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(lambda _:ds.tick(self.schedule(),profile,apply=True,now=now),range(2)))
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],3)
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_occurrences')[0][0],3)
        self.assertEqual(sum(len(x.get('job_ids',[])) for x in results),3)

    def test_latest_retains_skipped_ledger(self):
        ds.tick(self.schedule(catch_up='LATEST'),self.profile_file(),apply=True,now=self.utc('2026-10-25T02:00:00'))
        self.assertEqual(self.sql("SELECT count(*) FROM workflow_occurrences WHERE state='SKIPPED'")[0][0],2)
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],1)

    def test_bounded_sleep_catchup_is_finite(self):
        result=ds.tick(self.schedule(catch_up_limit=1),self.profile_file(),apply=True,now=self.utc('2026-10-25T02:00:00'));self.assertEqual(len(result['job_ids']),1)

    def test_stop_survives_restart_and_disable(self):
        p=self.profile_file();ds.tick(self.schedule(),p,stop=True,now=self.utc('2026-10-25T02:00:00'))
        ds.tick(self.schedule(enabled=False),p,apply=True,now=self.utc('2026-10-25T02:00:00'))
        self.assertEqual(ds.tick(self.schedule(),p,apply=True,now=self.utc('2026-10-25T02:00:00'))['state'],'STOPPED_FUTURE_ADMISSIONS')
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],0)

    def test_policy_drift_pauses(self):
        p=self.profile_file();ds.tick(self.schedule(),p,apply=True,now=self.utc('2026-10-24T02:00:00'));self.policy['grant_revision']=2;p=self.profile_file()
        self.assertEqual(ds.tick(self.schedule(),p,apply=True,now=self.utc('2026-10-25T02:00:00'))['state'],'PAUSED_BINDING_DRIFT')

    def test_edit_preserves_occurrence_history(self):
        p=self.profile_file();ds.tick(self.schedule(),p,apply=True,now=self.utc('2026-10-24T02:00:00'));ds.tick(self.schedule(revision=2,local_time='04:30'),p,apply=True,now=self.utc('2026-10-25T03:00:00'))
        self.assertEqual({r[0] for r in self.sql('SELECT revision FROM workflow_occurrences')},{1,2})
        self.assertEqual(self.sql("SELECT count(*) FROM jobs WHERE state='CANCELLED'")[0][0],1)

    def test_backward_clock_does_not_duplicate(self):
        p=self.profile_file();v=self.schedule();ds.tick(v,p,apply=True,now=self.utc('2026-10-25T02:00:00'))
        self.assertEqual(ds.tick(v,p,apply=True,now=self.utc('2026-10-24T02:00:00'))['state'],'CLOCK_MOVED_BACKWARD')
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],3)

    def test_capacity_wait_retains_occurrence(self):
        self.policy['max_queued']=1;p=self.profile_file();now=self.utc('2026-10-25T02:00:00')
        ds.tick(self.schedule(),p,apply=True,now=now)
        self.assertEqual(self.sql("SELECT count(*) FROM workflow_occurrences WHERE state='WAITING_CAPACITY'")[0][0],2)
        ac.Core(self.store,self.policy).run_once();ds.tick(self.schedule(),p,apply=True,now=now)
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],2)

    def test_v2_routes_through_existing_schedule_owner(self):
        import schedule_tick
        result=schedule_tick.tick(self.schedule(),self.profile_file(),apply=True,now=self.utc('2026-10-25T02:00:00'))
        self.assertEqual(result['state'],'ADMITTED');self.assertFalse(result['worker_started'])


class CampaignTests(Fixture):
    def test_end_to_end_dag_uses_core_and_restart(self):
        self.manifest();one=cr.advance(self.store,self.policy,'research');self.assertEqual(len(one['admitted']),1)
        self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'SUCCEEDED')
        self.assertEqual(len(cr.advance(self.store,self.policy,'research')['admitted']),1)
        self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'SUCCEEDED')
        self.assertEqual(cr.advance(self.store,self.policy,'research')['state'],'SUCCEEDED')
        self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'IDLE')
        self.assertEqual(self.sql('SELECT count(*) FROM sync_versions')[0][0],1)

    def test_parallel_admission_of_same_manifest_replays(self):
        self.manifest()
        with ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(lambda _:cr.advance(self.store,self.policy,'research'),range(2)))
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],1)

    def test_stop_does_not_resurrect(self):
        self.manifest();cr.advance(self.store,self.policy,'research');cr.cancel(self.store,self.policy,'research')
        self.assertEqual(cr.advance(self.store,self.policy,'research')['state'],'CANCELLED')
        self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'IDLE')

    def test_worker_input_drift_fails_without_import(self):
        self.manifest();cr.advance(self.store,self.policy,'research');(self.source/'note.txt').write_text('changed',encoding='utf-8')
        result=ac.Core(self.store,self.policy).run_once();self.assertEqual(result['state'],'BLOCKED')
        self.assertEqual(self.sql('SELECT count(*) FROM items')[0][0],0)

    def test_unknown_running_blocks_new_node(self):
        self.manifest();cr.advance(self.store,self.policy,'research');ac.Core(self.store,self.policy).claim()
        result=cr.advance(self.store,self.policy,'research');self.assertEqual(result['admitted'],[])
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],1)

    def test_cycle_rejected_before_queue(self):
        m=self.manifest();m['nodes'][0]['needs']=['join'];p=Path(self.policy['campaigns']['research']['manifest_file']);p.write_text(ac.encoded(m),encoding='utf-8');self.policy['campaigns']['research']['manifest_sha256']=ws.file_digest(p)
        with self.assertRaisesRegex(ValueError,'CYCLE'):cr.advance(self.store,self.policy,'research')
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],0)

    def test_source_drift_retained_as_blocker(self):
        self.manifest();(self.source/'note.txt').write_text('changed',encoding='utf-8');result=cr.advance(self.store,self.policy,'research')
        self.assertEqual(result['blockers']['read'],'WORKFLOW_SOURCE_DRIFT');self.assertEqual(result['admitted'],[])

    def test_large_dag_uses_pagination_not_twenty_node_cap(self):
        nodes=[{'id':f'n{i}','template':'notes','needs':[],'inputs':[],'resources':[],'demand':{}} for i in range(2100)]
        self.manifest(nodes);result=cr.inspect(self.store,self.policy,'research',offset=2090,limit=20)
        self.assertEqual(result['total'],2100);self.assertEqual(len(result['nodes']),10);self.assertIsNone(result['next_offset'])

    def test_same_store_no_competing_database(self):
        self.manifest();cr.advance(self.store,self.policy,'research');self.assertEqual([p.name for p in self.store.glob('*.sqlite3')],['content.sqlite3'])

    def test_native_scope_and_registered_manifest(self):
        self.manifest();profile=self.profile_file();import native_adapter
        result=native_adapter.dispatch({'type':'durable.campaign.advance','campaign':'research'},profile)
        self.assertEqual(len(result['campaign']['admitted']),1)
        with self.assertRaisesRegex(ValueError,'OUTSIDE'):native_adapter.dispatch({'type':'durable.campaign.inspect','campaign':'foreign'},profile)

    def test_dag_deadline_records_deferred(self):
        self.manifest();cr.advance(self.store,self.policy,'research',now=100)
        self.assertEqual(cr.advance(self.store,self.policy,'research',now=90000)['state'],'DEFERRED')

    def test_refresh_reuses_independent_receipt_and_invalidates_descendants(self):
        self.manifest();cr.advance(self.store,self.policy,'research');ac.Core(self.store,self.policy).run_once();cr.advance(self.store,self.policy,'research');ac.Core(self.store,self.policy).run_once();cr.advance(self.store,self.policy,'research')
        old=copy.deepcopy(self.policy);m=self.manifest(revision=2);m['nodes'][1]['resources']=[{'id':'new-writer','mode':'WRITE'}]
        path=Path(self.policy['campaigns']['research']['manifest_file']);path.write_text(ac.encoded(m),encoding='utf-8');self.policy['campaigns']['research']['manifest_sha256']=ws.file_digest(path)
        result=cr.refresh(self.store,old,self.policy,'research')
        self.assertEqual(result['reused_nodes'],['read']);self.assertEqual(result['invalidated_nodes'],['join'])
        self.assertEqual(cr.inspect(self.store,self.policy,'research')['nodes'][0]['state'],'SUCCEEDED')
        self.assertEqual(len(cr.advance(self.store,self.policy,'research')['admitted']),1)


class BriefTests(Fixture):
    def test_core_generates_early_brief_no_install_or_send(self):
        config=self.brief_config();job=self.operation('brief',config);result=ac.Core(self.store,self.policy).run_once()
        self.assertEqual(result['state'],'SUCCEEDED');brief=result['result'];self.assertFalse(brief['usable']);self.assertEqual(brief['state'],'DRAFT_NOT_SENT');self.assertEqual(brief['external_effects'],0)

    def test_repeat_draft_reuses_same_id(self):
        c=self.brief_config();a=wr.build_brief(self.store,c);b=wr.build_brief(self.store,c)
        self.assertEqual(a['brief_id'],b['brief_id']);self.assertTrue(b['reused']);self.assertEqual(self.sql("SELECT count(*) FROM workflow_records WHERE kind='brief'")[0][0],1)

    def test_negative_trial_and_old_goal_are_retained(self):
        result=wr.build_brief(self.store,self.brief_config());self.assertEqual(result['goal_ids'],['GOAL5-24']);self.assertEqual(result['negative_and_other_trials'][0]['outcome'],'NEGATIVE')

    def test_unknown_and_correlated_claims_are_not_verified(self):
        c=self.brief_config();data=json.loads(Path(c['input_file']).read_text());claim={'id':'a','text':'claim','source_ref':'source','source_sha256':'a'*64,'lineage':[],'primary_source_ref':'primary'}
        data['claims']=[claim,{**claim,'id':'b'},{**claim,'id':'c','source_ref':None}];c=self.brief_config(data)
        b=wr.build_brief(self.store,c);self.assertEqual(b['claims'][2]['provenance_state'],'UNKNOWN');self.assertEqual(b['claims'][0]['correlation_group'],b['claims'][1]['correlation_group']);self.assertNotIn('VERIFIED',[x['provenance_state'] for x in b['claims']])

    def test_no_progress_stops_persistently(self):
        cfg={'max_iterations':10,'max_elapsed_seconds':100,'max_transfers':2,'no_progress_limit':1}
        wr.bounded_loop(self.store,'loop',cfg,'same',now=10)
        self.assertEqual(wr.bounded_loop(self.store,'loop',cfg,'same',now=11)['reason'],'NO_PROGRESS')
        self.assertEqual(wr.bounded_loop(self.store,'loop',cfg,'new',now=12)['state'],'DEFERRED')

    def test_unknown_effect_stops_before_iteration(self):
        cfg={'max_iterations':3,'max_elapsed_seconds':100,'max_transfers':2,'no_progress_limit':2}
        result=wr.bounded_loop(self.store,'loop',cfg,'same',unknown_effect=True,now=10);self.assertEqual(result['reason'],'UNKNOWN_EFFECT');self.assertEqual(result['iterations'],0)

    def test_registered_experiment_retains_negative_result(self):
        inp=self.source/'note.txt';c={'root':str(self.source),'argv':[sys.executable,'-B','-c','raise SystemExit(1)'],'timeout_seconds':3,'input_file':str(inp),'input_sha256':ws.file_digest(inp),'criteria_ids':['criterion'],'hypothesis_id':'hypothesis'}
        self.operation('experiment',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'SUCCEEDED');self.assertEqual(r['result']['outcome'],'NEGATIVE_OR_FAILED');self.assertFalse(r['result']['criterion_closure'])


class CanonicalResearchTests(Fixture):
    def test_campaign_brief_uses_actual_receipts_and_preserves_open_criteria(self):
        self.manifest()
        cfg={'campaign':'research','planner_version':'v1','loop_id':'research-loop','limits':{'max_iterations':3,'max_elapsed_seconds':1000,'max_transfers':2,'no_progress_limit':1}}
        self.policy['workflow_operations']={'followup':{'action':'campaign_brief','config':cfg}}
        cr.advance(self.store,self.policy,'research');ac.Core(self.store,self.policy).run_once();cr.advance(self.store,self.policy,'research');ac.Core(self.store,self.policy).run_once();cr.advance(self.store,self.policy,'research')
        payload={'kind':'workflow_operation','operation_profile':'followup'}
        ac.enqueue(self.store,self.policy,'followup-one',payload);r=ac.Core(self.store,self.policy).run_once()
        self.assertEqual(r['state'],'SUCCEEDED',r['result']);self.assertEqual(len(r['result']['negative_and_other_trials']),2)
        self.assertEqual(r['result']['gaps'][0]['acceptance'],['Do not truncate']);self.assertFalse(r['result']['usable'])
        ac.enqueue(self.store,self.policy,'followup-two',payload);r2=ac.Core(self.store,self.policy).run_once()
        self.assertTrue(r2['result']['reused']);self.assertEqual(r2['result']['loop_state'],'DEFERRED');self.assertEqual(r2['result']['loop_stop_reason'],'NO_PROGRESS')


class UpdateTests(Fixture):
    def test_exact_stage_only_does_not_activate(self):
        c,b,target=self.release(mode='STAGE_ONLY');self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once()
        self.assertEqual(r['state'],'SUCCEEDED',r['result']);self.assertEqual(r['result']['state'],'STAGED_VERIFIED');self.assertFalse((target/'active.json').exists());self.assertFalse(r['result']['usable'])

    def test_real_core_install_canary_is_only_test_root(self):
        c,b,target=self.release();self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once()
        self.assertEqual(r['state'],'SUCCEEDED',r['result']);self.assertEqual(r['result']['state'],'INSTALLED_OBSERVED');self.assertEqual(r['result']['scope'],'ISOLATED_TEST_TARGET');self.assertFalse(r['result']['device_qualified']);self.assertFalse(r['result']['usable'])
        self.assertEqual(json.loads((target/'active.json').read_text())['asset_sha256'],c['asset_sha256'])

    def test_tampered_asset_keeps_active_pointer(self):
        c,b,target=self.release();(target/'active.json').write_text(ac.encoded({'asset_sha256':'old'}));Path(c['asset_file']).write_bytes(b'corrupt');self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once()
        self.assertEqual(r['state'],'BLOCKED');self.assertEqual(json.loads((target/'active.json').read_text())['asset_sha256'],'old')

    def test_mismatched_source_binding_rejected(self):
        c,b,target=self.release();b['source_commit']='c'*40;path=Path(c['binding_file']);path.write_text(ac.encoded(b));c['binding_sha256']=ws.file_digest(path)
        self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertIn('MISMATCH',r['result']['reason'])

    def test_archive_traversal_rejected(self):
        c,b,target=self.release(files={'../escape':b'bad'})
        self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertFalse((target.parent/'escape').exists())

    def test_archive_undeclared_file_rejected(self):
        c,b,target=self.release()
        with zipfile.ZipFile(c['asset_file'],'a') as z:z.writestr('extra',b'bad')
        c['asset_sha256']=ws.file_digest(Path(c['asset_file']));b['asset_sha256']=c['asset_sha256'];p=Path(c['binding_file']);p.write_text(ac.encoded(b));c['binding_sha256']=ws.file_digest(p)
        self.operation('release_update',c);self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'BLOCKED')

    def test_failed_rehearsal_retains_production_data(self):
        c,b,target=self.release(tests=[[sys.executable,'-B','-c','raise SystemExit(2)']]);self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertFalse((target/'active.json').exists());self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],1)

    def test_canary_failure_restores_previous_pointer_without_data_loss(self):
        script="from pathlib import Path; import sys; raise SystemExit(1 if Path(sys.argv[1]).name=='content.sqlite3' else 0)"
        c,b,target=self.release(tests=[[sys.executable,'-B','-c',script,'{DATA}']]);old={'asset_sha256':'previous','source_commit':'previous'};(target/'active.json').write_text(ac.encoded(old),encoding='utf-8')
        self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertEqual(json.loads((target/'active.json').read_text()),old);self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],1)

    def test_migration_schema_mismatch_does_not_activate(self):
        c,b,target=self.release();b['data_schema_version']=99;p=Path(c['binding_file']);p.write_text(ac.encoded(b));c['binding_sha256']=ws.file_digest(p)
        self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertFalse((target/'active.json').exists())

    def test_unmarked_target_cannot_activate(self):
        c,b,target=self.release();(target/'QUALIFICATION_TARGET.json').unlink();self.operation('release_update',c);self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'BLOCKED')

    def test_case_alias_archive_rejected(self):
        c,b,target=self.release(files={'a':b'a','A':b'b'});self.operation('release_update',c);self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'BLOCKED')

    def test_capability_usability_requires_all_bindings(self):
        keys={'device_id':'device','installation_id':'installation','artifact_digest':'hash','source_commit':'sha','capability_id':'cap','contract_version':'v1','scope_digest':'scope','target_profile':'profile'}
        i={**keys,'state':'INSTALLED_OBSERVED'};q={**keys,'state':'DEVICE_QUALIFIED'};g={**keys,'state':'ACTIVE'}
        self.assertTrue(up.usability(i,q,g));self.assertFalse(up.usability(i,q,g,revoked=True));self.assertFalse(up.usability(i,{**q,'artifact_digest':'other'},g));self.assertFalse(up.usability(i,{**q,'state':'AI_CLAIM'},g))

    def test_power_loss_after_pointer_switch_reconciles_without_second_install(self):
        c,b,target=self.release();cfg=self.root/'update-config.json';cfg.write_text(ac.encoded(c),encoding='utf-8')
        job=self.operation('release_update',c);policyfile=self.root/'worker-policy.json';policyfile.write_text(ac.encoded(self.policy),encoding='utf-8')
        # A separate process exits at the durable boundary; no Python finally runs.
        code="""import sys,json,os
from pathlib import Path
import automation_core as ac,release_updater as up
policy=json.loads(Path(sys.argv[2]).read_text())
original=up.atomic_json
def crash(path,value):
 original(path,value)
 if path.name=='active.json':os._exit(77)
up.atomic_json=crash
ac.Core(Path(sys.argv[1]),policy).run_once()
"""
        env={**os.environ,'PYTHONPATH':str(Path(__file__).parent.resolve()),'PYTHONUTF8':'1'}
        r=subprocess.run([sys.executable,'-B','-c',code,str(self.store),str(policyfile)],env=env,capture_output=True,timeout=15)
        self.assertEqual(r.returncode,77,r.stderr.decode('utf-8',errors='replace'));self.assertTrue((target/'active.json').exists())
        receipt=up.reconcile_test_installation(self.store,c,process_stopped=True);self.assertEqual(receipt['state'],'INSTALLED_OBSERVED_UNQUALIFIED');self.assertFalse(receipt['usable'])
        self.assertEqual(self.sql("SELECT count(*) FROM workflow_records WHERE kind='update'")[0][0],1)


class GitTests(Fixture):
    def check(self,method):
        c,repo=self.merge_fixture(method);self.operation('merge_observe',c);r=ac.Core(self.store,self.policy).run_once()
        self.assertEqual(r['state'],'SUCCEEDED',r['result']);self.assertEqual(r['result']['state'],'LOCAL_TARGET_VERIFIED');self.assertEqual(r['result']['result_commit'],self.git(repo,'rev-parse','target'));self.assertFalse(r['result']['usable'])
        self.assertNotEqual(r['result']['result_commit'],r['result']['proposal_commit'])

    def test_merge_actual_final_revision(self):self.check('merge')
    def test_squash_does_not_require_head_equality(self):self.check('squash')
    def test_manual_commit_without_pr(self):self.check('manual')
    def test_rebased_change_has_distinct_sha_and_extra_base_files(self):self.check('rebase')

    def test_wrong_repository_remote_is_rejected(self):
        c,repo=self.merge_fixture();self.git(repo,'remote','set-url','origin','https://github.com/other/repository.git');self.operation('merge_observe',c)
        self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'BLOCKED')

    def test_revert_does_not_claim_current_coverage(self):
        c,repo=self.merge_fixture();(repo/'value.txt').write_text('base\n',encoding='utf-8');self.git(repo,'add','.');self.git(repo,'commit','-qm','revert');self.operation('merge_observe',c)
        r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertIn('REVERT',r['result']['reason'])

    def test_failed_final_tree_tests_cannot_pass(self):
        c,repo=self.merge_fixture();c['tests']=[[sys.executable,'-B','-c','raise SystemExit(1)']];self.operation('merge_observe',c)
        self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'BLOCKED')


class RecoveryAndObserverTests(Fixture):
    def test_pause_resume_no_extra_effect_and_stop_after_source_disappears(self):
        self.manifest();cr.advance(self.store,self.policy,'research')
        self.assertEqual(cr.set_admission(self.store,self.policy,'research',True)['state'],'PAUSED')
        self.assertEqual(cr.advance(self.store,self.policy,'research')['state'],'PAUSED')
        cr.set_admission(self.store,self.policy,'research',False)
        Path(self.policy['campaigns']['research']['manifest_file']).unlink()
        self.assertEqual(cr.cancel(self.store,self.policy,'research')['state'],'CANCELLED')
        self.assertEqual(ac.Core(self.store,self.policy).run_once()['state'],'IDLE')

    def test_local_keyboard_stop_cli_without_execution_policy(self):
        self.manifest();cr.advance(self.store,self.policy,'research')
        r=subprocess.run([sys.executable,'-B',str(Path(cr.__file__).resolve()),'--store',str(self.store),'cancel','--campaign','research'],capture_output=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['state'],'CANCELLED')

    def test_deadline_does_not_allow_queued_job_to_execute(self):
        self.manifest();cr.advance(self.store,self.policy,'research');cr.advance(self.store,self.policy,'research',now=time.time()+100000)
        r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertEqual(self.sql('SELECT count(*) FROM items')[0][0],0)

    def test_updater_second_owner_cannot_touch_candidate(self):
        c,b,target=self.release();(target/'.update-owner.json').write_text('held',encoding='utf-8')
        self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED');self.assertFalse((target/'active.json').exists())
        self.assertEqual((target/'.update-owner.json').read_text(encoding='utf-8'),'held')

    def test_archive_windows_device_name_rejected_on_all_hosts(self):
        c,b,target=self.release(files={'CON.txt':b'bad'});self.operation('release_update',c);r=ac.Core(self.store,self.policy).run_once();self.assertEqual(r['state'],'BLOCKED')

    def github(self):
        return {'root':str(self.root),'repository':'example/registered','remote_identity':'https://github.com/example/registered.git','base_ref':'main','base_commit':'a'*40,'head_commit':'b'*40,'proposal_tree':'c'*40,'pr_number':1,'token_env':'OCC_GITHUB_TOKEN','required_checks':['test'],'tests':[[sys.executable,'-B','-c','pass']],'timeout_seconds':10,'max_pages':2}

    def request(self,c,merged=True,head=None,checks=None):
        def read(url,token,timeout):
            if '/pulls/' in url:return {'merged':merged,'merged_at':'2026-10-04T00:00:00Z','head':{'sha':head or c['head_commit']},'base':{'ref':'main','repo':{'full_name':c['repository']}},'merge_commit_sha':'d'*40}
            if '/git/ref/' in url:return {'object':{'sha':'d'*40}}
            runs=checks if checks is not None else [{'name':'test','id':2,'check_suite':{'head_sha':'d'*40},'app':{'slug':'github-actions'},'status':'completed','conclusion':'success'}]
            return {'total_count':len(runs),'check_runs':runs}
        return read

    def test_authenticated_observer_requires_actual_merge_and_head(self):
        import workflow_github as gh
        c=self.github()
        self.assertEqual(gh.collect_metadata(c,'fixture',self.request(c))['result_commit'],'d'*40)
        with self.assertRaisesRegex(ValueError,'NOT_CONFIRMED'):gh.collect_metadata(c,'fixture',self.request(c,merged=False))
        with self.assertRaisesRegex(ValueError,'DRIFT'):gh.collect_metadata(c,'fixture',self.request(c,head='e'*40))

    def test_ci_for_wrong_revision_does_not_verify_final_tree(self):
        import workflow_github as gh
        c=self.github();checks=[{'name':'test','id':2,'check_suite':{'head_sha':'b'*40},'app':{'slug':'github-actions'},'status':'completed','conclusion':'success'}]
        with self.assertRaisesRegex(ValueError,'CI_REQUIRED'):gh.collect_metadata(c,'fixture',self.request(c,checks=checks))

    def test_latest_check_rerun_wins_without_discarding_history(self):
        import workflow_github as gh
        c=self.github();success={'name':'test','id':2,'check_suite':{'head_sha':'d'*40},'app':{'slug':'github-actions'},'status':'completed','conclusion':'success'}
        failed={**success,'id':1,'conclusion':'failure'}
        result=gh.collect_metadata(c,'fixture',self.request(c,checks=[failed,success]));self.assertEqual(len(result['ci_snapshot']['checks']),2)

    def test_missing_token_has_no_network_call(self):
        import workflow_github as gh
        with self.assertRaisesRegex(ValueError,'TOKEN_MISSING'):gh.collect_metadata(self.github(),'',lambda *_:self.fail('network called'))

    def test_power_loss_before_switch_leaves_not_applied_receipt(self):
        c,b,target=self.release();job=self.operation('release_update',c)
        op=ac.digest([c['installation_id'],c['device_id'],c['asset_sha256'],c['source_commit']])
        with ws.transaction(self.store) as db:ws.put(db,'update',op,{'state':'ACTIVATING','previous':None},0)
        receipt=up.reconcile_test_installation(self.store,c,process_stopped=True)
        self.assertEqual(receipt['state'],'ACTIVATION_NOT_APPLIED');self.assertFalse((target/'active.json').exists())


class CoreGuardTests(Fixture):
    def test_cancelled_unstarted_node_releases_admission_capacity(self):
        self.manifest();cr.advance(self.store,self.policy,'research');cr.cancel(self.store,self.policy,'research')
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_reservations')[0][0],0)
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_leases')[0][0],0)

    def test_cancel_running_node_keeps_reservation_until_worker_stops(self):
        self.manifest();cr.advance(self.store,self.policy,'research');owner=ac.Core(self.store,self.policy);job=owner.claim()
        cr.cancel(self.store,self.policy,'research')
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_reservations')[0][0],1)
        owner.transition(job,'CANCELLED');cr.cancel(self.store,self.policy,'research')
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_reservations')[0][0],0)

    def test_revision_refresh_releases_completed_predecessor_leases(self):
        m=self.manifest();m['nodes']=m['nodes'][:1];p=Path(self.policy['campaigns']['research']['manifest_file']);p.write_text(ac.encoded(m));self.policy['campaigns']['research']['manifest_sha256']=ws.file_digest(p)
        cr.advance(self.store,self.policy,'research');ac.Core(self.store,self.policy).run_once()
        old=copy.deepcopy(self.policy);self.manifest(revision=2)
        cr.refresh(self.store,old,self.policy,'research')
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_reservations')[0][0],0)
        self.assertEqual(len(cr.advance(self.store,self.policy,'research')['admitted']),1)

    def test_running_campaign_cannot_refresh_away_its_owner(self):
        self.manifest();cr.advance(self.store,self.policy,'research');ac.Core(self.store,self.policy).claim()
        old=copy.deepcopy(self.policy);self.manifest(revision=2)
        with self.assertRaisesRegex(ValueError,'ACTIVE_OR_UNKNOWN'):cr.refresh(self.store,old,self.policy,'research')

    def test_stale_campaign_worker_cannot_renew_resource(self):
        self.manifest();cr.advance(self.store,self.policy,'research');owner=ac.Core(self.store,self.policy);job=owner.claim()
        before=self.sql('SELECT expires FROM workflow_leases')
        self.sql('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
        with self.assertRaisesRegex(ValueError,'JOB_FENCE_LOST'):owner.heartbeat(job)
        self.assertEqual(before,self.sql('SELECT expires FROM workflow_leases'))

    def test_stale_brief_job_cannot_publish_receipt(self):
        config=self.brief_config();self.operation('brief',config);job=ac.Core(self.store,self.policy).claim()
        self.sql('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
        with self.assertRaisesRegex(ValueError,'JOB_FENCE_LOST'):wr.build_brief(self.store,config,job=job)
        self.assertEqual(self.sql("SELECT count(*) FROM workflow_records WHERE kind='brief'")[0][0],0)

    def test_future_workflow_schema_is_not_silently_rewritten(self):
        self.sql('UPDATE workflow_schema_version SET version=99')
        with self.assertRaisesRegex(ValueError,'SCHEMA_VERSION_UNSUPPORTED'):ws.connect(self.store)

    def test_skipped_dst_gap_is_retained_in_ledger(self):
        value=self.schedule(start_date='2026-03-29',end_date='2026-03-29',fold_policy='FIRST')
        ds.tick(value,self.profile_file(),apply=True,now=self.utc('2026-03-29T12:00:00'))
        self.assertEqual(self.sql("SELECT count(*) FROM workflow_records WHERE kind='schedule_gap'")[0][0],1)
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],0)

    def test_null_github_metadata_fails_closed(self):
        import workflow_github as gh
        config={'root':str(self.root),'repository':'example/registered','remote_identity':'https://github.com/example/registered.git','base_ref':'main','base_commit':'a'*40,'head_commit':'b'*40,'proposal_tree':'c'*40,'pr_number':1,'token_env':'OCC_GITHUB_TOKEN','required_checks':['test'],'tests':[[sys.executable,'-B','-c','pass']],'timeout_seconds':10,'max_pages':2}
        with self.assertRaisesRegex(ValueError,'NOT_CONFIRMED'):gh.collect_metadata(config,'fixture',lambda *_:{'head':None,'base':None})

    def test_optional_queue_capacity_without_default_total_limit(self):
        with ws.transaction(self.store) as db:
            for i in range(1001):ac.enqueue_in_transaction(db,self.policy,'key:'+str(i),self.payload)
        self.assertEqual(self.sql('SELECT count(*) FROM jobs')[0][0],1001)

    def test_expired_worker_cannot_heartbeat_or_commit(self):
        job=ac.enqueue(self.store,self.policy,'one',self.payload)['id'];owner=ac.Core(self.store,self.policy);claimed=owner.claim();self.sql('UPDATE jobs SET lease_until=0 WHERE id=?',(job,))
        with self.assertRaises(ac.Cancelled):owner.heartbeat(claimed)
        with self.assertRaisesRegex(ValueError,'LEASE_LOST'):owner.transition(claimed,'SUCCEEDED')

    def test_job_cannot_supply_argv_or_update_path(self):
        for payload in [{'kind':'workflow_operation','operation_profile':'missing'}, {'kind':'workflow_operation','operation_profile':'x','argv':['evil']},{'kind':'workflow_operation','operation_profile':'x','root':'/'}]:
            with self.assertRaises(ValueError):ac.enqueue(self.store,self.policy,'bad',payload)

if __name__=='__main__':unittest.main()
