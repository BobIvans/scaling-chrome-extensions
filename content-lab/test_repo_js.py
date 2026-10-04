"""Real AST, captured-ledger, immutable export and process-boundary qualification."""
from collections import Counter
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import repo_context as repo
import repo_archive_input
import repo_js as app
import repo_js_input as inputs
import repo_js_runtime as runtime
from qualify_repo_js import qualify
from repo_artifacts import file_proof

LAB = Path(app.__file__).parent


class SyntaxTests(unittest.TestCase):
    def parse(self, source, ext='.mjs', **options):
        control = runtime.Control(runtime.budget(options))
        return runtime.parse_file(source.encode('utf8'), ext, control)

    def test_labelled_corpus_200_cases_20_families_exact_labels_and_positive_metrics(self):
        result = qualify()
        self.assertEqual(result['status'], 'PASS', result['failed_cases'])
        self.assertEqual((result['cases'], len(result['families']), result['references']), (200, 20, 171))
        self.assertEqual(set(result['families'].values()), {10})
        self.assertEqual((result['true_positive'], result['false_positive'], result['false_negative']), (67, 0, 0))
        self.assertEqual((result['precision'], result['recall']), (1, 1))
        self.assertEqual(result['known_dynamic_total'], result['known_dynamic_unresolved'])

    def test_bom_crlf_astral_escaped_literal_nested_symbols_and_anonymous(self):
        raw = '\ufeff// 👋 Привет\r\nimport "./\\u0075til.js";\r\nexport class Класс {}\r\nexport default function() { function inner() {} }\r\n'.encode('utf8')
        parsed = runtime.parse_file(raw, '.mjs', runtime.Control(runtime.budget()))
        self.assertEqual(parsed['status'], 'AST_SYNTAX_ONLY')
        self.assertEqual(parsed['refs'][0]['specifier'], './util.js')
        self.assertEqual(raw[parsed['refs'][0]['byte_start']:parsed['refs'][0]['byte_end']], b'"./\\u0075til.js"')
        self.assertEqual([symbol['name'] for symbol in parsed['symbols']], ['Класс', '<anonymous>', 'inner'])
        for record in parsed['refs'] + parsed['symbols']:
            app.checked_span(record, raw)

    def test_types_import_equals_shadowed_require_templates_and_type_query(self):
        source = 'import type { T } from "./type.ts"; export type { T } from "./type.ts";\nimport x = require("./x.cts"); function f(require:any) { require("./x.cts"); }\ntype Q = import("./type.ts").T; const d = import(`./${x}.ts`);\n'
        parsed = self.parse(source, '.ts')
        self.assertEqual(parsed['status'], 'AST_SYNTAX_ONLY')
        self.assertEqual([r['syntax_form'] for r in parsed['refs']],
                         ['TS_IMPORT_TYPE', 'TS_EXPORT_TYPE', 'IMPORT_EQUALS', 'COMMONJS_REQUIRE', 'TS_IMPORT_TYPE', 'COMPUTED_IMPORT'])
        self.assertEqual(parsed['refs'][-1]['specifier'], None)
        self.assertTrue(all(r['dependency_kind'] == 'TYPE_ONLY' for r in (parsed['refs'][0], parsed['refs'][1], parsed['refs'][4])))
        for ext in ('.mts', '.cts'):
            self.assertEqual(self.parse('export function f():number { return 1; }', ext)['status'], 'AST_SYNTAX_ONLY')

    def test_malformed_syntax_has_no_provisional_refs_and_fake_syntax_is_ignored(self):
        parsed = self.parse('import "./a.js"; export function broken( {')
        self.assertEqual((parsed['status'], parsed['refs'], parsed['symbols']), ('PARSER_FAILED', [], []))
        parsed = self.parse('/* import "./a.js" */ const x = "require(\\\"./b.js\\\")"; const y=/import/g;')
        self.assertEqual(parsed['refs'], [])

    def test_output_and_input_budgets_return_explicit_fallback(self):
        parsed = self.parse('import "./a.js";\n' * 100, parser_output_frame_bytes=1024)
        self.assertEqual(parsed['reason'], 'PARSER_OUTPUT_BUDGET')
        parsed = self.parse('/*' + 'x' * 4000 + '*/', parser_input_frame_bytes=1024)
        self.assertEqual(parsed['reason'], 'PARSER_INPUT_BUDGET')

    def test_resolver_never_guesses_mode_case_alias_extension_scope_or_assets(self):
        found = {'path': 'src/util.js', 'file_sha256': 'a' * 64, 'eligible': True}
        lookup = lambda path: found if path == found['path'] else None
        ref = {'syntax_form': 'ESM_IMPORT', 'specifier': './util.js'}
        self.assertEqual(app.resolve('src/main.js', ref, lookup, ['src']), (found, None))
        for spec, reason in [('./Util.js', 'TARGET_MISSING'), ('./util', 'EXTENSION_RULE_NOT_QUALIFIED'),
                ('./dir/', 'EXTENSION_RULE_NOT_QUALIFIED'), ('@app/util', 'NON_RELATIVE_POLICY_NOT_QUALIFIED'),
                ('./asset.json', 'TARGET_EXTENSION_UNSUPPORTED'), ('./util.js?raw', 'SPECIFIER_FORM_UNSUPPORTED'),
                ('../../other.js', 'SOURCE_SCOPE_ESCAPE')]:
            with self.subTest(spec=spec):
                self.assertEqual(app.resolve('src/main.js', dict(ref, specifier=spec), lookup, ['src'])[1], reason)
        for ext in ('.ts', '.tsx', '.mts', '.cts'):
            self.assertEqual(app.resolve('src/main' + ext, ref, lookup, ['src'])[1], 'TYPE_RESOLUTION_POLICY_REQUIRED')
        self.assertEqual(app.resolve('src/main.js', ref, lambda path: dict(found, eligible=False), ['src'])[1], 'TARGET_NOT_ELIGIBLE')

    def test_logical_id_is_stable_revision_changes_and_invalid_bytes_rejected(self):
        raw = 'import "./util.js"; import "./util.js";'.encode()
        parsed = self.parse(raw.decode())
        snap = {'id': 'a' * 64, 'namespace': 'code', 'alias': 'sce'}
        entry = {'path': 'src/main.js', 'file_hash': repo.sha(raw)}
        target = {'path': 'src/util.js', 'file_sha256': 'c' * 64, 'eligible': True}
        first = app.relations(snap, entry, parsed, raw, 'b' * 64, lambda path: target, ['src'])
        second = app.relations(dict(snap, id='d' * 64), entry, parsed, raw, 'e' * 64,
                               lambda path: dict(target, file_sha256='f' * 64), ['src'])
        self.assertEqual([r['edge_id'] for r in first], [r['edge_id'] for r in second])
        self.assertNotEqual([r['revision'] for r in first], [r['revision'] for r in second])
        self.assertEqual([r['occurrence'] for r in first], [0, 1])
        expected = hashlib.sha256(json.dumps(['repo-static-edge.v1', 'code', 'sce', 'src/main.js',
            'ESM_SIDE_EFFECT', './util.js', 0], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(first[0]['edge_id'], expected)
        with self.assertRaisesRegex(ValueError, 'PARSER_EVIDENCE_INVALID'):
            app.checked_span(dict(parsed['refs'][0], byte_start=1), raw)

    def fault_parser(self, script, **limits):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'repo_js_parser.cjs').write_text(script)
            control = runtime.Control(runtime.budget(limits))
            started = time.monotonic()
            with mock.patch.object(runtime, 'LAB', root):
                result = runtime.parse_file(b'', '.js', control)
            self.assertLess(time.monotonic() - started, 4)
            return result

    def test_timeout_kills_child_and_stderr_output_and_protocol_are_bounded(self):
        self.assertEqual(self.fault_parser('setInterval(()=>{},100);', file_timeout_seconds=1)['reason'], 'PARSER_TIMEOUT')
        self.assertEqual(self.fault_parser('process.stderr.write("x".repeat(100000)); setInterval(()=>{},100);',
                                         stderr_total_bytes=1024, stderr_retained_bytes=1024)['reason'], 'PARSER_STDERR_BUDGET')
        self.assertEqual(self.fault_parser('process.stdout.write(Buffer.alloc(200000)); setInterval(()=>{},100);',
                                         parser_output_frame_bytes=1024)['reason'], 'PARSER_OUTPUT_BUDGET')
        self.assertEqual(self.fault_parser('process.stdout.write("bad");')['reason'], 'PARSER_PROCESS_FAILED')

    def test_environment_drops_preloads_and_parser_pin_tampering_is_rejected(self):
        with mock.patch.dict(os.environ, {'NODE_OPTIONS': '--require untrusted', 'NODE_PATH': '/untrusted', 'GIT_TOKEN': 'test'}):
            env = runtime.parser_environment()
            self.assertFalse({'NODE_OPTIONS', 'NODE_PATH', 'GIT_TOKEN'} & set(env))
            self.assertEqual(self.parse('const x = 1;')['status'], 'AST_SYNTAX_ONLY')
        with mock.patch.object(runtime, 'file_proof', return_value={'bytes': 1, 'sha256': 'x'}):
            with self.assertRaisesRegex(ValueError, 'PARSER_PIN_MISMATCH'):
                runtime.parser_pin()

    def test_cancel_and_global_deadline_clean_up_actual_child_process(self):
        for cancellation in (True, False):
            with self.subTest(cancellation=cancellation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); (root / 'repo_js_parser.cjs').write_text('setInterval(()=>{},100);')
                children, original = [], subprocess.Popen
                def popen(*args, **kwargs):
                    child = original(*args, **kwargs); children.append(child); return child
                def stop(value):
                    if cancellation: raise KeyboardInterrupt()
                control = runtime.Control(runtime.budget({'global_timeout_seconds': 1}), stop)
                if not cancellation: control.started -= 2
                with mock.patch.object(runtime, 'LAB', root), mock.patch.object(runtime.subprocess, 'Popen', side_effect=popen):
                    with self.assertRaises(KeyboardInterrupt if cancellation else ValueError):
                        runtime.parse_file(b'', '.js', control)
                self.assertEqual(len(children), 1)
                self.assertIsNotNone(children[0].poll())


class LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name); cls.checkout = cls.root / 'repo'; cls.checkout.mkdir()
        cls.source = {'root': str(cls.checkout), 'namespace': 'code', 'source_roots': ['src'], 'exclusions': []}
        sources = {f'src/{i:03}.mjs': 'import "./util.js"; export function caller() { return 1; }\n'.encode() for i in range(42)}
        sources.update({'src/util.js': b'export function util() { return 1; }\n', 'src/type.ts': b'export type T = number;\n',
                        'src/type-main.ts': b'import type { T } from "./type.ts";\n', 'src/python.py': b'import os\n',
                        'src/empty.mts': b'', 'src/broken.ts': b'import "./type.ts"; function broken( {',
                        'src/canary.js': b'globalThis.__PR007_EXECUTED=true; require("fs").writeFileSync("EXECUTED","bad");\n',
                        'src/binary.js': b'\xff\0', 'src/.env.js': b'protected'})
        for path, raw in sources.items():
            target = cls.checkout / path; target.parent.mkdir(exist_ok=True); target.write_bytes(raw)
        def git(*args):
            subprocess.run(['git', '-C', str(cls.checkout), *args], check=True, capture_output=True)
        git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
        git('config', 'core.autocrlf', 'false'); git('add', '-A'); git('commit', '-qm', 'fixture')
        cls.baseline = cls.root / 'baseline'
        cls.sid = repo.start_scan(cls.baseline, 'sce', cls.source)
        while repo.scan_page(cls.baseline, 'code', cls.sid, limit=100)['state'] != 'COMPLETE':
            pass

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.root)); self.addCleanup(shutil.rmtree, self.work)
        self.store = self.work / 'store'; shutil.copytree(self.baseline, self.store)
        self.profile = self.work / 'profile.json'; self.policy = self.work / 'policy.json'; self.output = self.work / 'derived'
        self.policy.write_text(json.dumps({'schema': 'occ.automation-policy.v1', 'money_budget': 0, 'max_parallel': 1}))
        self.profile_value = {'schema': 'occ.native-durable-profile.v1', 'store': str(self.store),
                              'policy_file': str(self.policy), 'namespaces': ['code'], 'templates': {},
                              'repositories': {'sce': self.source}}
        self.profile.write_text(json.dumps(self.profile_value))

    def add_facts(self):
        # Contract fixture only: PR005's actual runtime is qualified separately.
        db = repo.db_for(self.store)
        with db:
            for row in db.execute('SELECT * FROM repo_entries WHERE snapshot_id=?', (self.sid,)):
                analysis = json.loads(row['analysis'] or '{}')
                if inputs.FACT_OWNER is not None:
                    owner = inputs.FACT_OWNER
                    classified = owner.classify_chunks(c[0] for c in db.execute(
                        'SELECT raw FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (self.sid, row['path'])))
                    analysis['format_eligibility'] = (owner.make_facts(self.sid, row, classified, analysis.get('parser'))
                        if row['state'] == 'INDEXED' else owner.metadata_facts({'id': self.sid}, row))
                    db.execute('UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path=?',
                               (json.dumps(analysis), self.sid, row['path']))
                    continue
                eligible = row['state'] == 'INDEXED' and row['path'] != 'src/binary.js'
                analysis['format_eligibility'] = {'schema': 'occ.format-eligibility.v1', 'snapshot_id': self.sid,
                    'ordinal': str(row['ordinal']), 'path': row['path'], 'mode': row['mode'], 'kind': row['kind'],
                    'git_oid': row['oid'], 'git_size': None if row['size'] is None else str(row['size']),
                    'disposition': row['state'], 'legacy_reason': row['reason'], 'file_sha256': row['file_hash'],
                    'classifier_version': 'utf8-controls-strict-lfs3.v1',
                    'format_kind': 'EMPTY' if row['size'] == 0 else 'UTF8_TEXT_CANDIDATE' if eligible else 'NOT_CLASSIFIED',
                    'text_eligibility': 'ELIGIBLE' if eligible else 'INELIGIBLE',
                    'raw_capture': 'RECORDED' if row['state'] == 'INDEXED' else 'NOT_CAPTURED',
                    'raw_integrity': 'NOT_RUN', 'reasons': [], 'parser': analysis.get('parser'), 'lfs': None}
                db.execute('UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path=?',
                           (json.dumps(analysis), self.sid, row['path']))
        db.close()

    def change(self, path, action):
        db = repo.db_for(self.store)
        with db:
            row = db.execute('SELECT * FROM repo_entries WHERE snapshot_id=? AND path=?', (self.sid, path)).fetchone()
            analysis = json.loads(row['analysis']); action(analysis)
            db.execute('UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path=?', (json.dumps(analysis), self.sid, path))
        db.close()

    def build(self, **kwargs):
        return app.build(self.profile, 'sce', self.sid, self.output, **kwargs)

    def rows(self, name):
        return [json.loads(line) for line in (self.output / name).read_text('utf8').splitlines()]

    def command(self):
        return [sys.executable, '-I', '-X', 'utf8', str(LAB / 'repo_js.py'), '--profile', str(self.profile),
                '--repository', 'sce', '--snapshot-id', self.sid, '--output', str(self.output)]

    def test_default_missing_facts_no_silent_legacy_then_explicit_legacy(self):
        # Exercise an old capture even when the new PR005 scanner is installed.
        db = repo.db_for(self.store)
        with db:
            for entry in db.execute('SELECT path,analysis FROM repo_entries WHERE snapshot_id=?', (self.sid,)):
                analysis = json.loads(entry['analysis'] or '{}'); analysis.pop('format_eligibility', None)
                db.execute('UPDATE repo_entries SET analysis=? WHERE snapshot_id=? AND path=?',
                           (json.dumps(analysis), self.sid, entry['path']))
        db.close()
        result = self.build()
        self.assertEqual(result['state'], 'PARTIAL')
        self.assertEqual(result['candidate_files'], 50)
        self.assertEqual(result['relations'], 0)
        self.assertFalse(result['eligibility_policy_verified'])
        self.assertEqual({r['reason'] for r in self.rows('JS_ANALYSIS.jsonl')}, {'ELIGIBILITY_FACTS_UNAVAILABLE'})
        self.output = self.work / 'legacy'
        result = self.build(legacy=True)
        self.assertGreater(result['local_static_edges'], 39)
        self.assertFalse(result['eligibility_policy_verified'])
        self.assertEqual(json.loads((self.output / 'INTERPRETATION.json').read_text())['eligibility_policy_version'],
                         'LEGACY_CAPTURE_GUARD_UNVERIFIED_PR005')

    def test_actual_cli_50_candidates_exact_files_and_deterministic_reuse_no_source_execution(self):
        self.add_facts()
        before = file_proof(self.store / 'content.sqlite3')
        # Alter/remove working sources: only the captured ledger can be used.
        modified = self.checkout / 'src/000.mjs'
        original = modified.read_bytes(); modified.write_bytes(b'invalid changed working source')
        self.addCleanup(modified.write_bytes, original)
        with mock.patch.object(repo, 'git', side_effect=AssertionError('must not inspect Git')):
            result = subprocess.run(self.command(), check=True, capture_output=True, timeout=120)
        status = json.loads(result.stdout)
        self.assertEqual((status['processed_entries'], status['candidate_files'], status['other_language_entries']), (51, 50, 1))
        self.assertEqual(status['state'], 'PARTIAL')
        self.assertEqual(status['local_static_edges'], 43)
        self.assertEqual(status['type_only_exact_edges'], 1)
        self.assertTrue(status['projection_complete'])
        self.assertFalse(status['resolution_complete'])
        self.assertEqual(before, file_proof(self.store / 'content.sqlite3'))
        self.assertFalse((LAB / 'EXECUTED').exists()); self.assertFalse((self.checkout / 'EXECUTED').exists())
        baseline = {name: file_proof(self.output / name) for name in app.ARTIFACTS}
        self.assertTrue(self.build()['reused'])
        self.assertEqual(baseline, {name: file_proof(self.output / name) for name in app.ARTIFACTS})
        self.assertEqual([r['source_path'] for r in self.rows('JS_ANALYSIS.jsonl')], sorted(r['source_path'] for r in self.rows('JS_ANALYSIS.jsonl')))

    @unittest.skipIf(inputs.FACT_OWNER is None, 'Actual PR005 owner not installed on this base')
    def test_actual_pr005_capture_private_binding_uses_owned_projection_without_manual_facts(self):
        before = file_proof(self.store / 'content.sqlite3')
        result = self.build()
        self.assertEqual((result['candidate_files'], result['local_static_edges'], result['type_only_exact_edges']), (50, 43, 1))
        self.assertTrue(result['eligibility_complete'])
        self.assertTrue(result['eligibility_policy_verified'])
        self.assertEqual(before, file_proof(self.store / 'content.sqlite3'))
        interpreted = json.loads((self.output / 'INTERPRETATION.json').read_text())
        self.assertEqual(interpreted['eligibility_owner_sha256'], file_proof(LAB / 'source_eligibility.py')['sha256'])

    def test_facts_binding_schema_versions_fail_closed_and_targets_do_not_resolve(self):
        self.add_facts()
        self.change('src/000.mjs', lambda a: a['format_eligibility'].update(ordinal='000'))
        self.change('src/001.mjs', lambda a: a['format_eligibility'].update(classifier_version='future'))
        self.change('src/002.mjs', lambda a: a['format_eligibility'].update(snapshot_id='a' * 64))
        self.change('src/util.js', lambda a: a['format_eligibility'].update(text_eligibility='INELIGIBLE'))
        result = self.build()
        reasons = {r['source_path']: r['reason'] for r in self.rows('JS_ANALYSIS.jsonl')}
        self.assertEqual(reasons['src/000.mjs'], 'ELIGIBILITY_FACTS_INVALID')
        self.assertEqual(reasons['src/001.mjs'], 'ELIGIBILITY_VERSION_MISMATCH')
        self.assertEqual(reasons['src/002.mjs'], 'ELIGIBILITY_BINDING_MISMATCH')
        self.assertEqual(result['local_static_edges'], 1)
        self.assertEqual(result['unresolved_reasons']['TARGET_NOT_ELIGIBLE'], 39)

    def test_profile_incomplete_capture_and_corrupt_raw_block_without_publish(self):
        self.add_facts()
        db = repo.db_for(self.store)
        with db:
            db.execute('UPDATE repo_snapshots SET cursor=0 WHERE id=?', (self.sid,))
        db.close()
        with self.assertRaisesRegex(ValueError, 'CONTEXT_INCOMPLETE'):
            self.build()
        self.assertFalse(self.output.exists())
        db = repo.db_for(self.store)
        with db:
            db.execute('UPDATE repo_snapshots SET cursor=total WHERE id=?', (self.sid,))
            db.execute('UPDATE repo_chunks SET raw=? WHERE snapshot_id=? AND path=? AND ordinal=0', (b'corrupt', self.sid, 'src/000.mjs'))
        db.close()
        with self.assertRaisesRegex(ValueError, 'RAW_INTEGRITY_FAIL'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_per_file_budget_keeps_accounted_projection_global_budgets_abort(self):
        self.add_facts()
        result = self.build(limits={'file_bytes': 1})
        self.assertTrue(result['projection_complete']); self.assertEqual(result['state'], 'PARTIAL')
        self.assertGreater(result['analysis_outcomes']['NOT_SUPPORTED'], 39)
        self.output = self.work / 'limited'
        with self.assertRaisesRegex(ValueError, 'GLOBAL_STAGE_BUDGET'):
            self.build(limits={'stage_max_bytes': 1})
        self.assertFalse(self.output.exists())
        self.assertIsNone(runtime.DEFAULT_BUDGET['global_timeout_seconds'])
        self.assertIsNone(runtime.DEFAULT_BUDGET['stage_max_bytes'])

    def test_cancel_and_disk_failure_preserve_previous_bundle_and_raw_ledger(self):
        self.add_facts(); self.build(limits={'file_bytes': 1})
        before = {name: file_proof(self.output / name) for name in app.ARTIFACTS}
        raw_before = file_proof(self.store / 'content.sqlite3')
        def cancel(event, **kwargs):
            if event == 'AFTER_FILE': raise KeyboardInterrupt()
        with mock.patch.object(app, 'boundary', side_effect=cancel):
            with self.assertRaises(KeyboardInterrupt): self.build(limits={'file_bytes': 1})
        with mock.patch.object(app.Projection, 'append', side_effect=OSError(errno.ENOSPC, 'injected disk full')):
            with self.assertRaises(OSError): self.build()
        self.assertEqual(before, {name: file_proof(self.output / name) for name in app.ARTIFACTS})
        self.assertEqual(raw_before, file_proof(self.store / 'content.sqlite3'))
        self.assertTrue(any((p / 'BLOCKED.json').exists() for p in self.work.glob('.derived.stage-*')))

    def test_corrupted_reuse_extra_members_and_new_interpretation_refused(self):
        self.add_facts(); self.build(limits={'file_bytes': 1})
        with self.assertRaisesRegex(ValueError, 'DERIVED_BUNDLE_CONFLICT'):
            self.build(limits={'file_bytes': 2})
        (self.output / 'JS_ANALYSIS.jsonl').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'DERIVED_BUNDLE_CONFLICT'):
            self.build(limits={'file_bytes': 1})
        (self.output / 'EXTRA').write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'DERIVED_BUNDLE_CONFLICT'):
            app.checked_bundle(self.output)

    def test_output_paths_profile_revocation_and_snapshot_scope_enforced(self):
        self.add_facts()
        for path in (self.checkout / 'derived', self.store / 'derived', Path('relative')):
            with self.assertRaises(ValueError):
                app.build(self.profile, 'sce', self.sid, path)
        def revoke(event, **kwargs):
            if event == 'AFTER_FILE':
                self.profile_value['repositories'] = {}; self.profile.write_text(json.dumps(self.profile_value))
        with mock.patch.object(app, 'boundary', side_effect=revoke):
            with self.assertRaisesRegex(ValueError, 'REPO_OUTSIDE_OPERATOR_SCOPE'):
                self.build(limits={'file_bytes': 1})
        self.assertFalse(self.output.exists())

    def test_node_executable_from_source_is_rejected_before_version_or_execution(self):
        with mock.patch.object(app, 'node_path', return_value=str(self.checkout / 'node.exe')):
            with mock.patch.object(runtime.subprocess, 'run', side_effect=AssertionError('must not execute source')):
                with self.assertRaisesRegex(ValueError, 'NODE_EXECUTABLE_IN_SOURCE_OR_STORE'):
                    self.build()
        self.assertFalse(self.output.exists())

    def test_installed_offline_isolated_layout_loads_without_project_dependencies(self):
        self.add_facts()
        installed = self.work / 'installed'; installed.mkdir()
        for path in LAB.glob('*.py'):
            if not path.name.startswith(('test_', 'qualify_')): shutil.copy2(path, installed / path.name)
        shutil.copy2(LAB / 'repo_js_parser.cjs', installed / 'repo_js_parser.cjs')
        for name in ('occ_v4', 'occ_v5', 'js-parser', 'js-contracts'):
            shutil.copytree(LAB / name, installed / name)
        cmd = self.command(); cmd[4] = str(installed / 'repo_js.py')
        result = subprocess.run(cmd + ['--budget', str(self.write_budget({'file_bytes': 1}))],
            cwd=self.checkout, env=dict(os.environ, NODE_OPTIONS='--require ./untrusted.cjs', NODE_PATH=str(self.checkout)),
            capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout)['candidate_files'], 50)
        content = (LAB.parent / 'agent-bridge/Install.ps1').read_text()
        self.assertIn('repo_js_parser.cjs', content); self.assertIn("'js-parser'", content)

    def write_budget(self, value):
        path = self.work / 'budget.json'; path.write_text(json.dumps(value)); return path

    def test_manifest_and_zip_inputs_have_identical_proofs_after_analysis(self):
        self.add_facts()
        first, second = self.work / 'before', self.work / 'after'
        repo_archive_input.write_manifest(self.store, 'sce', self.source, self.sid, first)
        self.build(limits={'file_bytes': 1})
        repo_archive_input.write_manifest(self.store, 'sce', self.source, self.sid, second)
        self.assertEqual({name: file_proof(first / name) for name in repo_archive_input.METADATA},
                         {name: file_proof(second / name) for name in repo_archive_input.METADATA})
        import repo_archive
        before_zip = repo_archive.build(self.profile, 'sce', first, self.work / 'zip-before')
        after_zip = repo_archive.build(self.profile, 'sce', second, self.work / 'zip-after')
        self.assertEqual(before_zip['archive']['sha256'], after_zip['archive']['sha256'])

    def test_tampered_stage_before_publish_is_blocked(self):
        self.add_facts()
        def tamper(event, **kwargs):
            if event == 'BEFORE_PUBLISH': (kwargs['stage'] / 'RELATIONS.jsonl').write_bytes(b'corrupt')
        with mock.patch.object(app, 'boundary', side_effect=tamper):
            with self.assertRaisesRegex(ValueError, 'DERIVED_BUNDLE_CONFLICT'):
                self.build(limits={'file_bytes': 1})
        self.assertFalse(self.output.exists())

    def test_crash_before_directory_rename_then_rebuild_after_publish_reuses(self):
        self.add_facts(); self.write_budget({'file_bytes': 1})
        script = '''import os,sys
sys.path.insert(0,sys.argv[1]);import repo_js as a
def fault(event,**kwargs):
 if event==sys.argv[2]:os._exit(91)
a.boundary=fault
a.main(sys.argv[3:])
'''
        cmd = [sys.executable, '-I', '-X', 'utf8', '-c', script, str(LAB)]
        args = self.command()[5:] + ['--budget', str(self.work / 'budget.json')]
        before = subprocess.run(cmd + ['BEFORE_PUBLISH'] + args, capture_output=True, timeout=120)
        self.assertEqual(before.returncode, 91, before.stderr.decode()); self.assertFalse(self.output.exists())
        after = subprocess.run(cmd + ['AFTER_PUBLISH'] + args, capture_output=True, timeout=120)
        self.assertEqual(after.returncode, 91, after.stderr.decode()); self.assertTrue(self.output.exists())
        self.assertTrue(self.build(limits={'file_bytes': 1})['reused'])

    def test_kernel_lock_blocks_second_process_until_first_publishes(self):
        self.add_facts(); self.write_budget({'file_bytes': 1})
        marker = self.work / 'held'
        script = '''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import repo_js as a
def hold(event,**kwargs):
 if event=='BEFORE_PUBLISH':
  Path(sys.argv[2]).write_text('held');sys.stdin.read(1)
a.boundary=hold
sys.exit(a.main(sys.argv[3:]))
'''
        args = self.command()[5:] + ['--budget', str(self.work / 'budget.json')]
        child = subprocess.Popen([sys.executable, '-I', '-X', 'utf8', '-c', script, str(LAB), str(marker)] + args,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 30
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(marker.exists())
            second = subprocess.run(self.command() + ['--budget', str(self.work / 'budget.json')], capture_output=True, timeout=30)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(json.loads(second.stdout)['reason'], 'EXPORT_LOCKED')
            stdout, stderr = child.communicate(b'x', timeout=30)
            self.assertEqual(child.returncode, 0, stderr.decode())
            self.assertTrue(json.loads(stdout)['projection_complete'])
        finally:
            if child.poll() is None: child.kill()
            child.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main()
