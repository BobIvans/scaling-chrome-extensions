"""Core STOP and operator scope remain shared by context and campaign owners."""
import json
import unittest
import automation_core as core
import campaign_runtime as campaign
import native_adapter
from test_workflow_runtime import Fixture


class InteroperabilityTests(Fixture):
    def test_global_stop_fences_campaign_transaction_and_resume_uses_same_core(self):
        self.manifest()
        executor = core.Core(self.store, self.policy)
        acknowledgement = executor.stop('combined-stop')
        result = campaign.advance(self.store, self.policy, 'research')
        self.assertEqual(result['admitted'], [])
        self.assertEqual(result['blockers']['read'], 'CORE_STOPPED')
        self.assertEqual(self.sql('SELECT count(*) FROM jobs'), [(0,)])
        self.assertEqual(self.sql('SELECT count(*) FROM workflow_reservations'), [(0,)])
        executor.resume_control(acknowledgement['epoch'])
        result = campaign.advance(self.store, self.policy, 'research')
        self.assertEqual(len(result['admitted']), 1)
        job_id = result['admitted'][0]
        executor.run_once()
        self.assertEqual(executor.get(job_id)['state'], 'SUCCEEDED')
        # The dependency advances in the original committed queue, without retrying read.
        result = campaign.advance(self.store, self.policy, 'research')
        self.assertEqual(len(result['admitted']), 1)
        self.assertNotEqual(result['admitted'][0], job_id)

    def test_campaign_and_context_operator_profile_coexist(self):
        self.manifest()
        self.policy['context_services'] = {'local': {
            'namespace': 'notes', 'input_roots': [str(self.source)],
            'output_roots': [str(self.root)], 'actions': ['CAPTURE'],
            'destinations': {}, 'qualification_path': str(self.root / 'qualification.json')}}
        profile_path = self.profile_file()
        value = json.loads(profile_path.read_text())
        value['context_service'] = 'local'
        value['desktop_scan_enabled'] = True
        profile_path.write_text(json.dumps(value), encoding='utf-8')
        profile, policy = native_adapter.operator_profile(profile_path)
        self.assertEqual(profile['campaigns'], ['research'])
        self.assertEqual(profile['context_service'], 'local')
        reply = native_adapter.dispatch_desktop({'type': 'durable.info'}, profile_path)
        self.assertTrue(reply['ok'], reply)
        self.assertIn('durable.library', reply['result']['info']['capabilities'])
        # Campaign writes retain their established API and are not silently advertised to desktop.
        reply = native_adapter.dispatch({'type': 'durable.campaign.inspect', 'campaign': 'research'}, profile_path)
        self.assertEqual(reply['campaign']['state'], 'PROPOSED')


if __name__ == '__main__':
    unittest.main()
