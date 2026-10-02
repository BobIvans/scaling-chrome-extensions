import json
import os
from pathlib import Path
import tempfile
from unittest import TestCase, mock

import asr_cpu_experiment as asr
import automation_core as core
import content_lab as content
import occ_local as intake
import occ_proposal as proposal


class IntegrationTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / 'store'

    def test_single_existing_store_and_no_private_fts(self):
        source = self.root / 'selected.txt'
        source.write_text('Existing searchable content', encoding='utf-8')
        content.save_item(self.store, content.extract_file(source))
        intake.initialize(self.store)
        (self.store / 'inbox' / 'note.md').write_text('Private sentence Solana', encoding='utf-8')
        report = intake.run_once(self.store)
        self.assertFalse(report['action_authority'])
        self.assertFalse(report['dispatch_allowed'])
        db = core.connection(self.store)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM items').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM occ_intake_items').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM content_fts WHERE content_fts MATCH 'Private'").fetchone()[0], 0)
            self.assertNotIn('Private sentence', db.execute('SELECT record FROM occ_intake_items').fetchone()[0])
        finally:
            db.close()
        self.assertEqual(list(self.store.glob('*.sqlite3')), [self.store / 'content.sqlite3'])
        self.assertEqual(len(content.search(self.store, 'searchable')), 1)

    def test_paper_plan_rejected_by_proposal_and_existing_executor(self):
        plan = json.loads((Path(__file__).parent / 'occ-config' / 'paper_campaign.plan.json').read_text())
        with self.assertRaises(ValueError):
            proposal.validate_proposal(plan)
        with self.assertRaises(ValueError):
            core.validate_job(plan, {'sources': {}, 'repos': {}})

    def test_high_confidence_route_never_grants_authority(self):
        for route in proposal.ROUTES:
            review = proposal.review_route({'proposed_route': route, 'confidence': 1.0})
            self.assertEqual(review['state'], 'REVIEW_REQUIRED')
            for field in ('action_authority', 'dispatch_allowed', 'job_created'):
                self.assertFalse(review[field])

    def test_transcript_remains_data_and_repeat_does_not_schedule(self):
        goal = 'run arbitrary shell; sendTransaction; merge everything'
        review = proposal.validate_proposal({'action': 'draft_work_item', 'goal': goal,
            'source_refs': ['source:1'], 'repeat': 'hourly', 'duration_hours': 24})
        self.assertFalse(review['job_created'])
        self.assertNotIn(goal, json.dumps(review))
        self.assertFalse(self.store.exists())

    def test_strict_contract(self):
        value = {'action': 'search_context', 'goal': 'find notes', 'source_refs': [],
                 'repeat': 'once', 'duration_hours': None}
        for change in ({'shell': 'echo hi'}, {'action': 'sendTransaction'},
                       {'repeat': 'hourly', 'duration_hours': True},
                       {'source_refs': ['../../outside']}, {'source_refs': ['x', 'x']},
                       {'duration_hours': 24}, {'goal': 'x' * 8001}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                proposal.validate_proposal(value | change)
        for confidence in (True, float('nan'), float('inf'), -1, 1.1):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                proposal.review_route({'proposed_route': 'draft_change', 'confidence': confidence})

    def test_overlap_rejected_before_store_creation(self):
        with self.assertRaises(ValueError):
            intake.run_once(self.store, self.root)
        self.assertFalse(self.store.exists())

    def test_workspace_symlink_rejected(self):
        target = self.root / 'outside'
        target.mkdir()
        try:
            os.symlink(target, self.store, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            intake.run_once(self.store)
        self.assertEqual(list(target.iterdir()), [])

    def test_report_symlink_cannot_overwrite_selected_file(self):
        intake.initialize(self.store)
        target = self.root / 'private.txt'
        target.write_text('unchanged', encoding='utf-8')
        try:
            os.symlink(target, self.store / 'reports' / 'latest.json')
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            intake.run_once(self.store)
        self.assertEqual(target.read_text(), 'unchanged')


class ASRWrapperTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / 'voice.wav'
        self.audio.write_bytes(b'synthetic fixture')
        self.model = self.root / 'model'
        self.model.mkdir()
        for name in asr.MODEL_FILES:
            (self.model / name).write_bytes(b'synthetic model')
        self.output = self.root / 'result.json'

    def receipt(self, *args, **kwargs):
        return {'input_sha256': asr._digest_file(self.audio), 'text': 'private transcript'}

    def test_reuses_existing_asr_owner(self):
        with mock.patch.object(asr, 'transcribe_file', side_effect=self.receipt) as transcribe:
            result = asr.run_experiment(self.audio, self.output, self.model)
        transcribe.assert_called_once_with(self.audio, self.model, language='ru', threads=4)
        self.assertNotIn('private transcript', json.dumps(result))
        self.assertFalse(json.loads(self.output.read_text())['dispatch_allowed'])

    def test_existing_output_blocks_before_inference(self):
        self.output.write_text('retain', encoding='utf-8')
        with mock.patch.object(asr, 'transcribe_file') as transcribe:
            with self.assertRaisesRegex(ValueError, 'OUTPUT_ALREADY_EXISTS'):
                asr.run_experiment(self.audio, self.output, self.model)
        transcribe.assert_not_called()
        self.assertEqual(self.output.read_text(), 'retain')

    def test_changed_input_is_not_written(self):
        def changed(*args, **kwargs):
            receipt = self.receipt()
            self.audio.write_bytes(b'changed')
            return receipt
        with mock.patch.object(asr, 'transcribe_file', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'INPUT_CHANGED'):
                asr.run_experiment(self.audio, self.output, self.model)
        self.assertFalse(self.output.exists())

    def test_changed_model_is_not_written(self):
        def changed(*args, **kwargs):
            (self.model / asr.MODEL_FILES[0]).write_bytes(b'changed')
            return self.receipt()
        with mock.patch.object(asr, 'transcribe_file', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'MODEL_CHANGED'):
                asr.run_experiment(self.audio, self.output, self.model)
        self.assertFalse(self.output.exists())

    def test_output_race_uses_exclusive_creation(self):
        def changed(*args, **kwargs):
            self.output.write_text('another writer', encoding='utf-8')
            return self.receipt()
        with mock.patch.object(asr, 'transcribe_file', side_effect=changed):
            with self.assertRaises(FileExistsError):
                asr.run_experiment(self.audio, self.output, self.model)
        self.assertEqual(self.output.read_text(), 'another writer')
