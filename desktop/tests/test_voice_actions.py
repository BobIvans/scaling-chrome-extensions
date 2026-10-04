"""Synthetic audio lifecycle and real Native IPC; no microphone qualification."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import wave

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'content-lab'));sys.path.insert(0,str(Path(__file__).parent))
from desktop.voice import Capture,critical_metrics
from desktop.client import DesktopClient
import test_desktop as fixtures
from test_action_runtime import configuration,input_value
from automation_core import Core,connection


class AudioStream:
    def __init__(self,**values):
        self.callback=values['callback'];self.active=False;self.closed=False
    def start(self):self.active=True
    def stop(self):
        # PortAudio stop can join a callback: this must never hold Capture.lock.
        worker=threading.Thread(target=lambda:self.callback(b'\0\0'*10,10,None,False))
        worker.start();worker.join(1)
        if worker.is_alive():raise RuntimeError('CALLBACK_DEADLOCK')
        self.active=False
    def close(self):self.closed=True


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.capture=Capture(self.root,stream_factory=AudioStream)
        self.addCleanup(self.capture.stop)

    def test_one_stream_hold_release_and_exact_wave_bytes(self):
        first=self.capture.press();stream=self.capture.stream
        self.assertEqual(first['id'],self.capture.press()['id'])
        self.assertIs(self.capture.stream,stream)
        stream.callback(b'\1\0'*25,25,None,False)
        stopped=self.capture.stop()
        self.assertTrue(stream.closed);self.assertEqual(stopped['state'],'STOPPED');self.assertEqual(stopped['frames'],35)
        with wave.open(str(self.root/stopped['audio_filename']),'rb') as wav:
            self.assertEqual(wav.readframes(25),b'\1\0'*25);self.assertEqual(wav.getframerate(),16000)
        self.assertEqual(json.loads((self.root/(first['id']+'.json')).read_bytes())['state'],'STOPPED')

    def test_tts_gap_and_second_owner_cannot_capture(self):
        with self.assertRaisesRegex(ValueError,'PHYSICAL'):self.capture.press(physical=False)
        self.capture.tts_active=True
        with self.assertRaisesRegex(ValueError,'PHYSICAL'):self.capture.press()
        self.capture.tts_active=False;self.capture.press()
        other=Capture(self.root,stream_factory=AudioStream)
        with self.assertRaisesRegex(ValueError,'BUSY'):other.press()
        self.capture.tts_active=True;self.capture.stream.callback(b'\0\0'*10,10,None,False)
        self.assertEqual(self.capture.session['frames'],0);self.assertTrue(self.capture.session['gap'])
        self.capture.stop();other.press();other.stop()

    def test_device_loss_duration_and_restart_are_visible(self):
        self.capture.press();self.capture.stream.active=False
        stopped=self.capture.poll();self.assertEqual(stopped['state'],'ABORTED');self.assertEqual(stopped['reason'],'DEVICE_LOST')
        self.capture.press();self.capture.started-=61
        self.assertEqual(self.capture.poll()['reason'],'SESSION_DURATION')
        stale=self.root/'voice-stale.json'
        stale.write_text(json.dumps({'schema':'occ.capture-session.v1','state':'CAPTURING'}))
        self.capture.press();self.capture.stop()
        self.assertEqual(json.loads(stale.read_bytes())['reason'],'PROCESS_RESTART')

    def test_start_failure_releases_lease_for_retry(self):
        class Broken(AudioStream):
            def start(self):raise OSError('device unavailable')
        self.capture.factory=Broken
        with self.assertRaises(OSError):self.capture.press()
        self.assertIsNone(self.capture.lease);self.assertIsNone(self.capture.stream)
        self.capture.factory=AudioStream;self.capture.press();self.capture.stop()

    def test_metrics_include_failed_trials_and_human_gold(self):
        values=[{'gold_slots':{'repo':'a','mode':'dry-run'},'observed_slots':{'repo':'a','mode':'SEND'},'wrong_effect_admitted':True,'latency_ms':20},
                {'gold_slots':{'repo':'b'},'observed_slots':{},'latency_ms':None}]
        result=critical_metrics(values)
        self.assertEqual(result['critical_slot_errors'],2);self.assertEqual(result['critical_slots'],3)
        self.assertEqual(result['attempts'],2);self.assertEqual(result['false_effect_admissions'],1)


class ActionIPCTests(unittest.TestCase):
    def setUp(self):
        fixtures.OwnerTests.setUp(self)
        policy=json.loads(self.policy.read_bytes());policy['actions']=configuration()
        self.policy.write_text(json.dumps(policy));self.client.close()
        self.client=DesktopClient(self.connection);self.addCleanup(self.client.close);self.client.handshake()
        self.operator_policy=policy

    def action(self,op,payload):
        return self.client.request({'type':'durable.action','action':op,'payload':payload})['result']['action']

    def test_text_revision_enqueue_worker_stop_share_existing_owner(self):
        self.assertIn('durable.action',self.client.info['capabilities'])
        self.assertEqual(self.action('INFO',{})['queue_owner'],'CORE_JOBS')
        value=input_value();intent=self.action('CREATE',value)
        first=self.action('ENQUEUE',{'intent_id':intent['intent_id'],'revision':1})
        corrected=self.action('CORRECT',{'intent_id':intent['intent_id'],'revision':1,'input':dict(value,text='needle')})
        core=Core(self.store,self.operator_policy)
        self.assertEqual(core.get(first['id'])['state'],'CANCELLED')
        job=self.action('ENQUEUE',{'intent_id':intent['intent_id'],'revision':corrected['revision']})
        self.assertEqual(core.run_once()['id'],job['id']);self.assertEqual(core.get(job['id'])['state'],'SUCCEEDED')
        self.assertEqual(self.action('STOP',{})['state'],'STOPPED')
        db=connection(self.store)
        try:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],2)
        finally:db.close()


if __name__=='__main__':unittest.main()
