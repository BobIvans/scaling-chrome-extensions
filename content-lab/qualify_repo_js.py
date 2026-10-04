"""Reproducible AST qualification on the PR007 synthetic labelled corpus."""
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_js
from repo_js_runtime import Control, budget, parse_file, parser_pin


def qualify():
    corpus = json.loads((Path(__file__).parent / 'fixtures/repo_js_corpus.json').read_text('utf8'))
    control, families, failures = Control(budget()), Counter(), []
    true_positive = false_positive = false_negative = dynamic = dynamic_unresolved = references = 0
    started = time.monotonic()
    for case in corpus['cases']:
        raw = case['source_text'].encode('utf8')
        if len(raw) != case['raw_bytes'] or repo_js.hashlib.sha256(raw).hexdigest() != case['raw_sha256']:
            raise ValueError('CORPUS_INPUT_CHANGED')
        parsed = parse_file(raw, Path(case['source_path']).suffix, control)
        manifest = {entry['path']: {'path': entry['path'], 'file_sha256': entry['raw_sha256'],
                                    'eligible': entry['analysis_eligible']} for entry in case['manifest']}
        refs = repo_js.relations({'id': 'a' * 64, 'namespace': 'fixture', 'alias': 'sce'},
            {'path': case['source_path'], 'file_hash': case['raw_sha256']}, parsed, raw, 'b' * 64,
            manifest.get, [case['scope_root']]) if parsed['status'] == 'AST_SYNTAX_ONLY' else []
        expected = [{key: value for key, value in ref.items() if key != 'literal_or_expression'}
                    for ref in case['expected_refs']]
        columns = set(expected[0]) if expected else set()
        actual = [{key: value for key, value in ref.items() if key in columns} for ref in refs]
        if parsed['status'] != case['expected_analysis'] or actual != expected or parsed['symbols'] != case['expected_symbols']:
            failures.append(case['case_id'])
        key = lambda ref: (ref['syntax_form'], ref['specifier'], ref['byte_start'], ref['byte_end'], ref['target_path'])
        positives = {key(ref) for ref in expected if ref['resolution_status'] == 'LOCAL_STATIC_EXACT_PATH'}
        predicted = {key(ref) for ref in refs if ref['resolution_status'] == 'LOCAL_STATIC_EXACT_PATH'}
        true_positive += len(positives & predicted)
        false_positive += len(predicted - positives)
        false_negative += len(positives - predicted)
        for ref in expected:
            if ref['syntax_form'] in {'DYNAMIC_IMPORT', 'COMPUTED_IMPORT'}:
                dynamic += 1
                dynamic_unresolved += int(any(r['syntax_form'] == ref['syntax_form'] and
                    r['byte_start'] == ref['byte_start'] and r['resolution_status'] == 'UNRESOLVED' and
                    r['reason'] == 'DYNAMIC_IMPORT_UNRESOLVED' for r in refs))
        references += len(refs)
        families[case['family_id']] += 1
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else None
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else None
    return {'status': 'PASS' if not failures and precision is not None and precision >= .98 and recall
            and dynamic == dynamic_unresolved else 'FAIL',
            'corpus_sha256': repo_js.file_proof(Path(__file__).parent / 'fixtures/repo_js_corpus.json')['sha256'],
            'parser_pin': parser_pin(), 'cases': len(corpus['cases']), 'families': dict(families),
            'synthetic': True, 'real_world_holdout': 'NOT_PROVIDED', 'references': references,
            'true_positive': true_positive, 'false_positive': false_positive, 'false_negative': false_negative,
            'precision': precision, 'recall': recall, 'known_dynamic_total': dynamic,
            'known_dynamic_unresolved': dynamic_unresolved, 'failed_cases': failures,
            'seconds': round(time.monotonic() - started, 3), 'parent_child_peak_rss_bytes': control.peak_rss,
            'parser_peak_rss_bytes': control.child_peak, 'platform': sys.platform}


if __name__ == '__main__':
    result = qualify()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
