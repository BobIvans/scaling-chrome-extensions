"""Real Tk lifecycle smoke when a display is available (Windows CI / Xvfb)."""
import json
import os
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from desktop.app import App
from desktop.state import Fence, Ticket
import test_desktop as fixtures


class FixtureFenceTests(unittest.TestCase):
    def test_independent_design_events_reject_every_stale_binding(self):
        value = json.loads((fixtures.FIXTURES / 'UI_FENCE_CASES.json').read_bytes())
        current = value['current']
        keys = ('profile_digest', 'store_identity', 'adapter_sha256')
        def ticket(source):
            return Ticket(source['generation'], source['request_id'], source['expected_operation'],
                          source['namespace'], source['query_revision'],
                          tuple(sorted((key, source[key]) for key in keys)))
        fence = Fence()
        expected = ticket(current)
        fence.generation, fence.query_revision = expected.generation, expected.query_revision
        fence.namespace, fence.identity, fence.active = expected.namespace, expected.identity, expected
        for case in value['cases']:
            with self.subTest(case=case['id']):
                self.assertEqual(fence.accepts(ticket(case['event'])), case['expected'] == 'APPLY')


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Tk display unavailable locally; Windows/Xvfb CI runs UI')
class TkTests(unittest.TestCase):
    setUpOwner = fixtures.OwnerTests.setUp

    def setUp(self):
        self.setUpOwner()
        self.tk = tk.Tk()
        self.tk.withdraw()
        config = self.root / 'connection.json'
        config.write_text(json.dumps(self.connection.as_dict()), encoding='utf-8')
        self.app = App(self.tk, config)
        self.addCleanup(self.close_tk)

    def close_tk(self):
        try:
            exists = self.tk.winfo_exists()
        except tk.TclError:
            return
        if exists:
            self.app.close()
            deadline = time.monotonic() + 5
            while self.app.busy() and time.monotonic() < deadline:
                self.tk.update()
                time.sleep(0.01)
            try:
                self.tk.destroy()
            except tk.TclError:
                pass

    def pump(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.tk.update()
            if predicate():
                return
            time.sleep(0.01)
        self.fail('Tk state did not reach expected result: ' + self.app.status.get())

    def test_search_select_draft_keyboard_cancel_and_close_on_main_thread(self):
        self.pump(lambda: self.app.report is not None and not self.app.busy())
        self.assertEqual(self.app.namespace.get(), 'code')
        self.assertIn(str(self.store), self.app.location.get())
        self.app.query.set('needle')
        self.app.search()
        self.pump(lambda: bool(self.app.items) and not self.app.busy())
        self.app.results.selection_set(0)
        self.app.selection_changed()
        self.app.read_context()
        self.pump(lambda: self.app.context is not None and not self.app.busy())
        self.assertIn('Привет', self.app.preview.get('1.0', 'end'))
        self.app.goal.set('Review')
        self.app.scope.set('Selected text')
        self.app.acceptance.set('Exact bytes')
        output = self.root / 'ui draft'
        with mock.patch.object(self.app, 'output_folder', return_value=output):
            self.app.save()
        self.pump(lambda: (output / 'TASK_DRAFT.txt').exists() and not self.app.busy())
        ticket = self.app.fence.begin('durable.search')
        self.app.query.set('changed')
        changed = []
        self.app.events.put((ticket, 'result', {'stale': True}, changed.append))
        self.pump(lambda: self.app.events.empty())
        self.assertEqual(changed, [])
        self.app.cancel()
        self.assertIn('отменена', self.app.status.get())
        self.assertTrue(self.tk.bind('<Escape>'))
        self.assertEqual(self.app.owner_thread, threading.get_ident())
        self.app.close()
        self.pump(lambda: not self.app.busy(), timeout=3)

    selected = fixtures.OwnerTests.selected


if __name__ == '__main__':
    unittest.main()
