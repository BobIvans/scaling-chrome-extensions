import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'content-lab'))
from desktop.client import Connection,DesktopClient,DesktopError
from desktop.install import install,uninstall,verify_install
from desktop.package import verify
import context_runtime as runtime
import context_library as lib
import context_packets as packets
import automation_core as core
from test_action_runtime import configuration, input_value


class InstalledContext(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.store=self.root/'data';packets.db_for(self.store).close()
        self.c={'namespace':'n','input_roots':[str(self.root)],'output_roots':[str(self.root)],'actions':list(runtime.WRITES),'destinations':{'local':{'destination_id':'local','destination_revision':'1','policy_revision':'1','source_keys':['source'],'protected_literals':[]}},'qualification_path':str(self.root/'qualification.json')}
        self.policy={'schema':'occ.automation-policy.v1','max_parallel':1,'money_budget':0,'context_services':{'local':self.c}}
        self.policy_path=self.root/'policy.json';self.policy_path.write_bytes(lib.encoded(self.policy))
        self.profile=self.root/'profile.json';self.profile.write_bytes(lib.encoded({'schema':'occ.native-durable-profile.v1','store':str(self.store),'policy_file':str(self.policy_path),'namespaces':['n'],'templates':{},'context_service':'local'}))
        self.installed=self.root/'version';install(ROOT,self.installed,sys.executable,self.profile)
        self.connection=Connection.load(self.installed/'desktop/connection.json');self.client=DesktopClient(self.connection);self.addCleanup(self.client.close);self.client.handshake()
    def command(self,action):
        r=subprocess.run([sys.executable,'-I','-X','utf8',str(self.installed/'backend/context_runtime.py'),'--profile',str(self.profile),action],capture_output=True,timeout=180)
        self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'));return json.loads(r.stdout)
    def request(self,action,args,op=None):
        req={'type':'durable.library','namespace':'n','action':action,'arguments':args}
        if op:req['operationId']=op
        return self.client.request(req)['result']['library']['data']
    def execute(self,action,args,op):
        first=self.request(action,args,op);self.command('work');r=self.request('OPERATION',{'operation_id':op});self.assertEqual(r['state'],'SUCCEEDED',r);return r['result']
    def test_installed_closed_browser_roundtrip_and_exact_ack_recovery(self):
        proof=self.command('qualify');self.assertEqual(proof['status'],'PASS');self.client.handshake();self.client.verify_backend_bundle()
        file=self.root/'source';file.write_bytes(b'Installed\r\nexact bytes')
        capture=self.execute('CAPTURE',{'path':str(file),'source_key':'source'},'capture')
        ref=self.request('SEARCH',{'query':'Installed'})['rows'][0]['source_ref'];ref['start']=0;ref['end']=capture['bytes']
        selection=self.execute('SELECT',{'rows':[{'source_ref':ref,'reason':'criterion source'}]},'selection')
        packet=self.execute('BUILD_PACKET',{'selection_id':selection['selection_id'],'goal':'goal','criteria':['criterion']},'build')
        projection=self.execute('PROJECT',{'packet_id':packet['packet_id'],'destination':'local'},'project')
        result=self.execute('EXPORT',{'projection_id':projection['projection_id'],'destination':'local','output':str(self.root/'export')},'export')
        self.assertFalse(result['criterion_verified']);self.assertEqual(result['model_read'],'UNKNOWN')
        # The retry is the same persistent operation, even from a new adapter process.
        again=self.request('CAPTURE',{'path':str(file),'source_key':'source'},'capture')
        self.assertEqual(again['state'],'SUCCEEDED')
    def test_stop_does_not_wait_for_ordinary_client_lock(self):
        other=DesktopClient(self.connection);self.addCleanup(other.close);other.handshake()
        self.client._gate.acquire()
        try:r=other.request({'type':'durable.stop','requestId':'independent-stop'})['result']['library']['data']
        finally:self.client._gate.release()
        self.assertEqual(r['control_ack'],'DURABLE_FENCED');self.assertFalse(r['new_dispatch_allowed'])
    def test_uninstall_unknown_file_blocks_before_deletion_and_preserves_data(self):
        extra=self.installed/'operator-note';extra.write_text('preserve')
        with self.assertRaisesRegex(DesktopError,'DESKTOP_INSTALL_UNOWNED_FILE'):uninstall(self.installed)
        self.assertTrue((self.installed/'backend/native_adapter.py').exists());extra.unlink();uninstall(self.installed)
        self.assertTrue((self.store/'content.sqlite3').exists());self.assertTrue(self.profile.exists());self.assertTrue(self.policy_path.exists())
    def test_installed_backend_mutation_invalidates_handshake_binding(self):
        self.client.verify_backend_bundle();module=self.installed/'backend/context_packets.py';module.write_text(module.read_text()+'\n# changed\n')
        with self.assertRaisesRegex(DesktopError,'DESKTOP_BACKEND_CHANGED'):self.client.verify_backend_bundle()
        with self.assertRaisesRegex(DesktopError,'DESKTOP_PROFILE_CHANGED'):self.request('CAPABILITIES',{})
        with self.assertRaisesRegex(DesktopError,'DESKTOP_BACKEND_CHANGED'):verify_install(self.installed)

    def test_installed_actions_and_library_share_core_stop_and_build_binding(self):
        actions=configuration();actions['namespaces']=['n']
        self.policy['actions']=actions
        self.policy_path.write_bytes(lib.encoded(self.policy))
        self.client.close();self.client=DesktopClient(self.connection)
        self.addCleanup(self.client.close);self.client.handshake()
        self.client.verify_backend_bundle()
        self.assertIn('durable.action',self.client.info['capabilities'])
        self.assertIn('durable.library',self.client.info['capabilities'])

        def action(name,payload):
            return self.client.request({'type':'durable.action','action':name,
                                        'payload':payload})['result']['action']

        intent=action('CREATE',input_value(namespace='n'))
        job=action('ENQUEUE',{'intent_id':intent['intent_id'],'revision':1})
        outcome=self.command('work');self.assertEqual(outcome['id'],job['id'])
        self.assertEqual(outcome['state'],'SUCCEEDED')
        self.client.request({'type':'durable.stop','requestId':'library-action-stop'})
        second=action('CREATE',input_value(namespace='n'))
        with self.assertRaisesRegex(DesktopError,'CORE_STOPPED'):
            action('ENQUEUE',{'intent_id':second['intent_id'],'revision':1})
        action('RESUME',{})
        self.assertFalse(core.Core(self.store,self.policy).control_status()['stopped'])
        module=self.installed/'backend/action_runtime.py'
        module.write_text(module.read_text()+'\n# changed\n')
        with self.assertRaisesRegex(DesktopError,'DESKTOP_BACKEND_CHANGED'):
            self.client.verify_backend_bundle()
    def test_context_window_keyboard_controls_on_available_display(self):
        import tkinter as tk
        from desktop.library import LibraryWindow
        try:root=tk.Tk()
        except tk.TclError:self.skipTest('No display; actual Windows device qualification remains NOT_RUN')
        self.addCleanup(root.destroy)
        with mock.patch.object(LibraryWindow,'call'):
            window=LibraryWindow(root,self.connection,'n');root.update()
            self.assertTrue(window.window.bind('<Control-Shift-X>'));self.assertEqual(window.listbox.cget('exportselection'),0)
            window.close()

if __name__=='__main__':unittest.main()
