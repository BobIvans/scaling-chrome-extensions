import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from label_context import build_labels, assemble_goal, compare_revisions, jsonl, sanitize_tag, Cancelled


class LabelContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def pack(self, name, files, messages=()):
        folder = self.root / name
        (folder / 'originals').mkdir(parents=True)
        rows = []
        for n, item in enumerate(files, 1):
            path, raw, state = item[:3]
            encoding = item[3] if len(item) > 3 else 'utf-8'
            digest = hashlib.sha256(raw).hexdigest()
            (folder / 'originals' / digest).write_bytes(raw)
            rows.append(dict(id=n, ordinal=n-1, path=path, kind='file', snapshot=name,
                             sha256=digest, size=len(raw), text_state=state, encoding=encoding,
                             original_object='originals/' + digest, annotation=None))
        (folder / 'files.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in rows), encoding='utf-8')
        (folder / 'messages.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in messages), encoding='utf-8')
        (folder / 'index.json').write_text(json.dumps({'schema': 'sce.desktop.export.v1',
            'snapshot': {'id': name, 'source': 'repo.zip'}, 'entries': len(rows), 'parts': [],
            'coverage': {'enumeration_complete': True}}), encoding='utf-8')
        return folder

    def test_preserves_all_unicode_spans_and_full_paths_over_twenty_files(self):
        content = '\ufeffНужны тесты flashloan\r\n' * 30
        pack = self.pack('p', [(f'src/deep/{n}.txt', content.encode(), 'TEXT_COMPLETE') for n in range(57)])
        before = {p.name: p.read_bytes() for p in (pack / 'originals').iterdir()}
        result = build_labels(pack, self.root / 'labels', span_chars=17)
        records = list(jsonl(self.root / 'labels/labels.jsonl'))
        self.assertEqual(57, result['counts']['sources'])
        self.assertGreater(result['counts']['spans'], 57)
        for n in range(57):
            spans = [r for r in records if r['kind'] == 'span' and r['locator']['path'] == f'src/deep/{n}.txt']
            self.assertEqual(content, ''.join(r['text'] for r in spans))
            self.assertEqual(0, spans[0]['locator']['start'])
            self.assertEqual(len(content), spans[-1]['locator']['end'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in (pack / 'originals').iterdir()})

    def test_raw_objects_unknown_not_falsely_interpreted(self):
        pack = self.pack('p', [('code.py', b'flashloan = 1', 'TEXT_COMPLETE'), ('doc.pdf', b'\x00\xffPDF', 'RAW_ONLY')])
        build_labels(pack, self.root / 'labels')
        report = assemble_goal(self.root / 'labels', 'flashloan', self.root / 'goal')
        self.assertEqual(1, report['counts']['UNKNOWN'])
        self.assertEqual(1, report['counts']['INCLUDED'])
        self.assertFalse(report['all_modalities_interpreted'])
        self.assertEqual('NOT_RUN', report['goal_achieved'])

    def test_goal_has_no_topk_and_accounts_every_record(self):
        pack = self.pack('p', [(str(n), b'flashloan test', 'TEXT_COMPLETE') for n in range(101)] + [('other', b'apples', 'TEXT_COMPLETE')])
        build_labels(pack, self.root / 'labels')
        report = assemble_goal(self.root / 'labels', 'flashloan', self.root / 'goal')
        self.assertEqual(101, report['counts']['INCLUDED'])
        self.assertEqual(1, report['counts']['EXCLUDED'])
        self.assertEqual(204, sum(report['counts'].values()))
        self.assertEqual(204, len(list(jsonl(self.root / 'goal/coverage.jsonl'))))

    def test_source_revision_stable_and_change_invalidates_dependent_spans(self):
        a = self.pack('a', [('same.py', b'old', 'TEXT_COMPLETE')])
        b = self.pack('b', [('same.py', b'new', 'TEXT_COMPLETE')])
        build_labels(a, self.root / 'la', namespace='project')
        build_labels(a, self.root / 'la2', namespace='project')
        build_labels(b, self.root / 'lb', namespace='project')
        arows, a2rows, brows = [list(jsonl(self.root / folder / 'labels.jsonl')) for folder in ('la', 'la2', 'lb')]
        self.assertEqual([x['id'] for x in arows], [x['id'] for x in a2rows])
        self.assertEqual(arows[0]['source_id'], brows[0]['source_id'])
        self.assertNotEqual(arows[1]['id'], brows[1]['id'])
        report = compare_revisions(self.root / 'la', self.root / 'lb', self.root / 'diff.json')
        self.assertEqual('CHANGED', report['changes'][0]['state'])
        self.assertTrue(report['changes'][0]['invalidate_old_dependent_context'])

    def test_duplicate_paths_have_distinct_identity(self):
        p = self.pack('p', [('same', b'A', 'TEXT_COMPLETE'), ('same', b'B', 'TEXT_COMPLETE')])
        build_labels(p, self.root / 'labels')
        rows = [r for r in jsonl(self.root / 'labels/labels.jsonl') if r['kind'] == 'source']
        self.assertNotEqual(rows[0]['source_id'], rows[1]['source_id'])
        self.assertEqual([0, 1], [x['locator']['duplicate_occurrence'] for x in rows])

    def test_chat_branches_roles_duplicate_message_ids_preserved(self):
        messages = [dict(id=str(n), entry=1, conversation='chat1', message=mid,
                         parent=parent, text=f'goal {n}', role=role, created='100', parts_json='{}')
                    for n, (mid, parent, role) in enumerate([
                        ('a', 'None', 'user'), ('b', 'a', 'assistant'),
                        ('c', 'a', 'assistant'), ('c', 'a', 'tool'), ('d', 'a', 'system')])]
        p = self.pack('p', [('conversations.json', b'[]', 'TEXT_COMPLETE')], messages)
        build_labels(p, self.root / 'labels')
        rows = [r for r in jsonl(self.root / 'labels/labels.jsonl') if r['kind'] == 'message']
        self.assertEqual(5, len(rows))
        self.assertEqual(5, len({r['id'] for r in rows}))
        self.assertEqual({'user','assistant','tool','system'}, {r['message_metadata']['role'] for r in rows})
        graph = json.loads((self.root / 'labels/graph.json').read_text())
        self.assertEqual(4, len([x for x in graph['edges'] if x['relation'] == 'reply_to']))
        self.assertTrue(all(r['derivative_integrity'].endswith('NOT_REVALIDATED') for r in rows))

    def test_asserted_project_differs_from_suggested_goal(self):
        p = self.pack('p', [('x', 'Хочу flashloan тесты'.encode(), 'TEXT_COMPLETE')])
        build_labels(p, self.root / 'labels', project='Мой проект', tags=['Tag\n$(danger)'])
        span = list(jsonl(self.root / 'labels/labels.jsonl'))[1]
        self.assertEqual('ASSERTED', next(x for x in span['labels'] if x['facet'] == 'project')['status'])
        self.assertEqual('SUGGESTED', next(x for x in span['labels'] if x['value'] == 'goal_candidate')['status'])
        self.assertEqual('tag-danger', sanitize_tag('Tag\n$(danger)'))
        self.assertTrue(all(x['confidence'] is None for x in span['labels']))

    def test_utf16_character_locators_and_include_all(self):
        original = 'Привет\r\n二😀'
        p = self.pack('p', [('utf16', original.encode('utf-16'), 'TEXT_COMPLETE', 'utf-16')])
        build_labels(p, self.root / 'labels', span_chars=2)
        rows = [r for r in jsonl(self.root / 'labels/labels.jsonl') if r['kind'] == 'span']
        self.assertEqual(original, ''.join(r['text'] for r in rows))
        self.assertTrue(all(r['locator']['unit'] == 'decoded_unicode_codepoints' for r in rows))
        report = assemble_goal(self.root / 'labels', 'unmatched', self.root / 'goal', include_all=True)
        self.assertEqual(len(rows), report['counts']['INCLUDED'])
        self.assertEqual(0, report['counts']['EXCLUDED'])

    def test_corrupted_original_rejected_no_completed_output(self):
        p = self.pack('p', [('x', b'good', 'TEXT_COMPLETE')])
        next((p / 'originals').iterdir()).write_bytes(b'evil')
        with self.assertRaisesRegex(ValueError, 'CORRUPT_ORIGINAL'):
            build_labels(p, self.root / 'labels')
        self.assertFalse((self.root / 'labels').exists())

    def test_path_escape_rejected(self):
        p = self.pack('p', [('x', b'good', 'TEXT_COMPLETE')])
        row = next(jsonl(p / 'files.jsonl')); row['original_object'] = '../../outside'
        (p / 'files.jsonl').write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError, 'PATH_OUTSIDE_PACK'):
            build_labels(p, self.root / 'labels')

    def test_tampered_labels_not_used_as_goal_context(self):
        p = self.pack('p', [('x', b'good', 'TEXT_COMPLETE')])
        build_labels(p, self.root / 'labels')
        with (self.root / 'labels/labels.jsonl').open('a') as f:
            f.write('{}\n')
        with self.assertRaisesRegex(ValueError, 'CORRUPT_LABELS'):
            assemble_goal(self.root / 'labels', 'good', self.root / 'goal')

    def test_empty_goal_terms_unknown_instead_of_silently_empty(self):
        p = self.pack('p', [('x', b'good', 'TEXT_COMPLETE')])
        build_labels(p, self.root / 'labels')
        report = assemble_goal(self.root / 'labels', 'и на для', self.root / 'goal')
        self.assertEqual(1, report['counts']['UNKNOWN'])
        self.assertEqual(0, report['counts']['EXCLUDED'])

    def test_text_complete_without_original_rejected(self):
        p = self.pack('p', [('x', b'good', 'TEXT_COMPLETE')])
        row = next(jsonl(p / 'files.jsonl')); row['original_object'] = None
        (p / 'files.jsonl').write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError, 'TEXT_COMPLETE_WITHOUT_ORIGINAL'):
            build_labels(p, self.root / 'labels')

    def test_annotation_changes_invalidate_context_without_changing_content_revision(self):
        p = self.pack('p', [('x', b'neutral text', 'TEXT_COMPLETE')])
        build_labels(p, self.root / 'old', project='apples')
        build_labels(p, self.root / 'new', project='flashloan')
        report = compare_revisions(self.root / 'old', self.root / 'new', self.root / 'diff.json')
        self.assertEqual('UNCHANGED', report['changes'][0]['state'])
        self.assertTrue(report['changes'][0]['annotation_revision_changed'])
        self.assertTrue(report['changes'][0]['invalidate_old_dependent_context'])
        self.assertTrue(report['dependent_context_reassembly_required'])

    def test_cancel_build_atomic_cleanup(self):
        p = self.pack('p', [('x', b'good', 'TEXT_COMPLETE')])
        state = {'stop': False}
        def progress(message):
            state['stop'] = True
        with self.assertRaises(Cancelled):
            build_labels(p, self.root / 'labels', progress=progress, cancel=lambda: state['stop'])
        self.assertFalse((self.root / 'labels').exists())
        self.assertFalse(list(self.root.glob('.labels-*')))

    def test_cancel_goal_atomic_cleanup(self):
        p = self.pack('p', [('x', b'good', 'TEXT_COMPLETE')])
        build_labels(p, self.root / 'labels')
        with self.assertRaises(Cancelled):
            assemble_goal(self.root / 'labels', 'good', self.root / 'goal', cancel=lambda: True)
        self.assertFalse((self.root / 'goal').exists())


if __name__ == '__main__':
    unittest.main()
