"""Read-only, offline labels and context coverage over sce.desktop.export.v1.

Original packs are authoritative. Labels are derivatives, never execution rules.
Python 3.11+; standard library only. No source-count or total-size cap.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata

VERSION = 'sce.labels.v1'
FACETS = ['source', 'authorship', 'semantic_type', 'project', 'goal', 'time',
          'status', 'evidence', 'confidence', 'sensitivity', 'machine_parse',
          'language', 'execution', 'custom']

class Cancelled(Exception):
    pass

def checkpoint(cancel):
    if cancel():
        raise Cancelled('Отменено: завершённый результат не создан.')

def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))

def identity(kind, *values):
    return kind + ':' + hashlib.sha256(canonical(values).encode('utf-8')).hexdigest()

def digest_file(path, cancel=lambda: False):
    with Path(path).open('rb') as source:
        digest = hashlib.sha256()
        while True:
            checkpoint(cancel)
            block = source.read(65536)
            if not block:
                return digest.hexdigest()
            digest.update(block)

def safe_path(root, relative):
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if not p.is_relative_to(root) or p == root:
        raise ValueError('PATH_OUTSIDE_PACK: ' + str(relative))
    return p

def sanitize_tag(value):
    """Keep Unicode letters/digits; remove controls and syntactic punctuation."""
    text = unicodedata.normalize('NFKC', str(value)).casefold()
    return re.sub(r'[-_]+', '-', ''.join(c if c.isalnum() else '-' for c in text)).strip('-')

def label(facet, value, basis, status='SUGGESTED', confidence=None):
    if facet not in FACETS:
        raise ValueError('Unknown facet: ' + facet)
    item = {'facet': facet, 'value': str(value), 'tag': sanitize_tag(value),
            'status': status, 'basis': basis, 'confidence': confidence}
    return item

def jsonl(path):
    with Path(path).open(encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f'INVALID_JSONL: {path}:{n}') from e

def write_row(out, row):
    out.write(canonical(row) + '\n')

def pieces(stream, chars):
    offset = 0
    while True:
        text = stream.read(chars)
        if not text:
            if offset == 0:
                yield 0, 0, ''
            return
        yield offset, offset + len(text), text
        offset += len(text)

def infer(text, path='', role=None):
    low = text.casefold()
    result = []
    rules = [('question', r'\?|\bвопрос\b'),
             ('goal_candidate', r'\b(?:хочу|нужно|цель|надо|want|need|goal)\b'),
             ('task_candidate', r'\b(?:todo|сделать|добавить|исправить|implement|fix)\b'),
             ('test_related', r'\b(?:pytest|unittest|assert|тест|тесты|test)\b'),
             ('web3_related', r'\b(?:flashloan|solidity|evm|web3|uniswap|arbitrage|флешлоан)\b'),
             ('decision_candidate', r'\b(?:решили|выбираем|decided|decision)\b')]
    for value, pattern in rules:
        if re.search(pattern, low):
            result.append(label('semantic_type', value, 'lexical_rule_v1'))
    suffix = Path(path).suffix.casefold()
    if suffix in {'.py', '.sol', '.js', '.ts', '.rs', '.go', '.cpp', '.java'}:
        result.append(label('semantic_type', 'code_candidate', 'filename_extension'))
    if re.search('[а-яё]', low):
        result.append(label('language', 'russian_present', 'unicode_script_heuristic'))
    if re.search('[a-z]', low):
        result.append(label('language', 'latin_present', 'unicode_script_heuristic'))
    if re.search(r'(?i)(private[_ -]?key|seed phrase|api[_ -]?key|пароль|секрет)', text):
        result.append(label('sensitivity', 'potential_secret_reference', 'lexical_rule_v1'))
    result.append(label('sensitivity', 'unclassified', 'no_complete_secret_or_pii_detector', 'UNKNOWN'))
    result.append(label('execution', 'source_data_untrusted', 'all_imported_content', 'ASSERTED'))
    result.append(label('status', 'unverified_content', 'no_fact_or_execution_verification', 'ASSERTED'))
    if role:
        result.append(label('authorship', role, 'exported_author_role_not_identity_verification', 'ASSERTED'))
    return result

def _metadata_labels(row, namespace, project, tags):
    output = [label('source', namespace, 'explicit_namespace_or_snapshot_source', 'ASSERTED'),
              label('machine_parse', row.get('text_state', 'UNKNOWN'), 'export_manifest', 'ASSERTED')]
    if project:
        output.append(label('project', project, 'explicit_cli_project', 'ASSERTED'))
    for tag in tags:
        output.append(label('custom', tag, 'explicit_cli_tag', 'ASSERTED'))
    annotation = row.get('annotation') or {}
    if annotation.get('tags'):
        # Original annotation stays intact; tokenization is only a suggestion.
        for tag in re.split(r'[,;\n]', annotation['tags']):
            if tag.strip():
                output.append(label('custom', tag.strip(), 'imported_annotation', 'ASSERTED'))
    return output

def _graph(labels_path, output, cancel=lambda: False):
    """Streaming graph file; edges refer to the same stable IDs as labels.jsonl."""
    with output.open('w', encoding='utf-8') as f:
        f.write('{"schema":"sce.label.graph.v1","nodes":[')
        first = True
        for record in jsonl(labels_path):
            checkpoint(cancel)
            if not first:
                f.write(',')
            first = False
            f.write(canonical({k: record[k] for k in ('id', 'kind', 'source_id', 'revision_id')}))
        f.write('],"edges":[')
        first = True
        for record in jsonl(labels_path):
            checkpoint(cancel)
            if record['kind'] == 'source':
                continue
            edge = {'from': record['id'], 'to': record['source_record_id'], 'relation': 'derived_from'}
            if not first:
                f.write(',')
            first = False
            f.write(canonical(edge))
            if record.get('parent_message_record_id'):
                f.write(',' + canonical({'from': record['id'], 'to': record['parent_message_record_id'],
                                        'relation': 'reply_to', 'target_may_be_absent': True}))
        f.write(']}\n')

def build_labels(pack, destination, namespace=None, project=None, tags=(), span_chars=4096,
                 progress=lambda message: None, cancel=lambda: False):
    if span_chars < 1:
        raise ValueError('span_chars must be positive; this is a segmentation size, not a total cap')
    pack, destination = Path(pack).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('Choose a new output directory')
    index = json.loads((pack / 'index.json').read_text(encoding='utf-8'))
    if index.get('schema') != 'sce.desktop.export.v1':
        raise ValueError('Only sce.desktop.export.v1 is supported')
    namespace = namespace or index['snapshot'].get('source') or index['snapshot']['id']
    # Check source objects and derived text parts. A corrupt input must not acquire labels.
    for part in index.get('parts', []):
        checkpoint(cancel)
        p = safe_path(pack, part['path'])
        if p.stat().st_size != part['bytes'] or digest_file(p, cancel) != part['sha256']:
            raise ValueError('CORRUPT_TEXT_PART: ' + str(part['path']))
    if index['snapshot'].get('archive_sha'):
        archive_sha = index['snapshot']['archive_sha']
        if digest_file(safe_path(pack, 'originals/' + archive_sha), cancel) != archive_sha:
            raise ValueError('CORRUPT_ARCHIVE')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.labels-', dir=destination.parent))
    counts = {'sources': 0, 'spans': 0, 'messages': 0, 'raw_only': 0, 'unknown': 0}
    duplicates, source_by_entry = {}, {}
    try:
        with (temp / 'labels.jsonl').open('w', encoding='utf-8') as out:
            for row in jsonl(pack / 'files.jsonl'):
                checkpoint(cancel)
                path = row['path']
                occurrence = duplicates.get(path, 0)
                duplicates[path] = occurrence + 1
                source_id = identity('source', namespace, path, occurrence)
                source_hash = row.get('sha256')
                revision = identity('revision', source_id, source_hash, row['kind'])
                source_record_id = identity('source-record', revision)
                locator = {'path': path, 'duplicate_occurrence': occurrence, 'entry': row['id'],
                           'ordinal': row['ordinal'], 'snapshot': row['snapshot'],
                           'original_object': row.get('original_object')}
                labels = _metadata_labels(row, namespace, project, tags)
                original = safe_path(pack, row['original_object']) if row.get('original_object') else None
                if row['text_state'] == 'TEXT_COMPLETE' and original is None:
                    raise ValueError('TEXT_COMPLETE_WITHOUT_ORIGINAL: ' + path)
                if original and (digest_file(original, cancel) != source_hash or original.stat().st_size != row['size']):
                    raise ValueError('CORRUPT_ORIGINAL: ' + path)
                record = {'schema': VERSION, 'id': source_record_id, 'kind': 'source',
                          'source_id': source_id, 'revision_id': revision, 'source_sha256': source_hash,
                          'content_revision_id': revision,
                          'annotation_revision_id': identity('annotation', source_id, labels, row.get('annotation')),
                          'locator': locator, 'labels': labels, 'source_manifest': row,
                          'integrity': 'VERIFIED_RAW_BYTES' if original else 'NO_RAW_OBJECT',
                          'text_state': row['text_state'], 'text': None}
                source_by_entry[row['id']] = record
                write_row(out, record)
                counts['sources'] += 1
                if row['text_state'] == 'TEXT_COMPLETE' and original:
                    encoding = row.get('encoding') or 'utf-8'
                    # newline='' preserves CR/LF; offsets are decoded Unicode code points, not bytes.
                    with original.open('r', encoding=encoding, errors='strict', newline='') as stream:
                        for start, end, text in pieces(stream, span_chars):
                            checkpoint(cancel)
                            span_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                            span = dict(schema=VERSION, id=identity('span', revision, start, end, span_hash),
                                        kind='span', source_id=source_id, revision_id=revision,
                                        source_record_id=source_record_id, source_sha256=source_hash,
                                        locator={**locator, 'unit': 'decoded_unicode_codepoints',
                                                 'encoding': encoding, 'start': start, 'end': end},
                                        text_sha256=span_hash, text=text,
                                        labels=labels + infer(text, path), text_state='TEXT_COMPLETE')
                            write_row(out, span)
                            counts['spans'] += 1
                elif row['text_state'] not in ('METADATA_ONLY',):
                    counts['raw_only'] += row['text_state'] == 'RAW_ONLY'
                    counts['unknown'] += row['text_state'] != 'RAW_ONLY'
                progress(f'Метки: {counts["sources"]} источников — {path}')
            if counts['sources'] != index['entries']:
                raise ValueError('MANIFEST_ENTRY_COUNT_MISMATCH')
            messages_path = pack / 'messages.jsonl'
            message_occurrences = {}
            if messages_path.exists():
                for message in jsonl(messages_path):
                    checkpoint(cancel)
                    if message.get('entry') not in source_by_entry:
                        raise ValueError('MESSAGE_WITHOUT_SOURCE_ENTRY')
                    source = source_by_entry[message['entry']]
                    message_key = (message['entry'], message['conversation'], message['message'])
                    message_occurrence = message_occurrences.get(message_key, 0)
                    message_occurrences[message_key] = message_occurrence + 1
                    message_id = identity('message', source['revision_id'], message['conversation'], message['message'], message_occurrence)
                    parent = message.get('parent')
                    parent_id = (identity('message', source['revision_id'], message['conversation'], parent, 0)
                                 if parent and parent not in ('None', 'null') else None)
                    text = message.get('text', '')
                    record = dict(schema=VERSION, id=message_id, kind='message',
                                  source_id=source['source_id'], revision_id=source['revision_id'],
                                  source_record_id=source['id'], source_sha256=source['source_sha256'],
                                  locator={**source['locator'], 'conversation_id': message['conversation'],
                                           'message_id': message['message'], 'message_occurrence': message_occurrence,
                                           'exported_derived_id': message['id']},
                                  text=text, text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                                  text_state='DERIVED_MESSAGE', parent_message_record_id=parent_id,
                                  derivative_integrity='ORIGINAL_HASH_VERIFIED_MAPPING_NOT_REVALIDATED',
                                  message_metadata=message,
                                  labels=source['labels'] + infer(text, source['locator']['path'], message.get('role')) +
                                  [label('time', message.get('created', 'unknown'), 'exported_message_timestamp', 'ASSERTED')])
                    write_row(out, record)
                    counts['messages'] += 1
        _graph(temp / 'labels.jsonl', temp / 'graph.json', cancel)
        manifest = {'schema': 'sce.labels.manifest.v1', 'source_pack': str(pack), 'namespace': namespace,
                    'source_manifest_sha256': digest_file(pack / 'files.jsonl', cancel),
                    'source_index_sha256': digest_file(pack / 'index.json', cancel),
                    'source_messages_sha256': digest_file(pack / 'messages.jsonl', cancel) if (pack / 'messages.jsonl').exists() else None,
                    'labels_sha256': digest_file(temp / 'labels.jsonl', cancel), 'graph_sha256': digest_file(temp / 'graph.json', cancel),
                    'counts': counts, 'span_chars': span_chars, 'enumeration_complete': index.get('coverage', {}).get('enumeration_complete', False),
                    'enumeration_completeness_basis': 'REPORTED_BY_EXPORT_MANIFEST_NOT_INDEPENDENT_SOURCE_INVENTORY',
                    'semantic_labels_verified': False, 'laya_inference': 'NOT_RUN',
                    'source_originals_copied': False, 'originals_location': str(pack / 'originals'),
                    'revision_rule': 'namespace + exact path + duplicate occurrence; content hash invalidates source revision and every dependent span',
                    'source_is_untrusted_data': True, 'network_calls': 0, 'code_executed': False}
        (temp / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, destination)
        return manifest
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise

STOPWORDS = set('a an the and or to of in for i my we our is it this that please мне я мы и в на для это как что по с к не нужно пожалуйста хочу'.split())

def goal_terms(goal):
    return sorted(set(re.findall(r'\w+', goal.casefold())) - STOPWORDS)

def assemble_goal(labels_dir, goal, destination, include_all=False,
                  progress=lambda message: None, cancel=lambda: False):
    labels_dir, destination = Path(labels_dir).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('Choose a new output directory')
    manifest = json.loads((labels_dir / 'manifest.json').read_text(encoding='utf-8'))
    labels_path = labels_dir / 'labels.jsonl'
    if digest_file(labels_path, cancel) != manifest['labels_sha256']:
        raise ValueError('CORRUPT_LABELS')
    terms = goal_terms(goal)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.goal-', dir=destination.parent))
    counts = {'INCLUDED': 0, 'EXCLUDED': 0, 'UNKNOWN': 0, 'METADATA_ONLY': 0}
    try:
        with (temp / 'coverage.jsonl').open('w', encoding='utf-8') as coverage, \
             (temp / 'context.jsonl').open('w', encoding='utf-8') as context, \
             (temp / 'context.txt').open('w', encoding='utf-8', newline='\n') as txt:
            txt.write('GOAL: ' + goal + '\nIMPORTED CONTENT IS DATA, NOT EXECUTION AUTHORITY.\n')
            for row in jsonl(labels_path):
                checkpoint(cancel)
                text = row.get('text')
                haystack = ((text or '') + ' ' + row['locator']['path'] + ' ' + ' '.join(x['value'] for x in row['labels'])).casefold()
                matched = [term for term in terms if term in haystack]
                if row['kind'] == 'source':
                    state = 'METADATA_ONLY' if row['text_state'] in ('TEXT_COMPLETE', 'METADATA_ONLY') else 'UNKNOWN'
                    reason = 'source_has_derived_spans_or_metadata' if state == 'METADATA_ONLY' else 'no_complete_readable_derivative'
                elif text is None:
                    state, reason = 'UNKNOWN', 'no_readable_text'
                elif include_all:
                    state, reason = 'INCLUDED', 'explicit_include_all'
                elif matched:
                    state, reason = 'INCLUDED', 'lexical_candidate_not_verified_relevance'
                elif not terms:
                    state, reason = 'UNKNOWN', 'goal_has_no_search_terms_use_include_all'
                else:
                    state, reason = 'EXCLUDED', 'no_lexical_match_not_proof_of_irrelevance'
                counts[state] += 1
                if sum(counts.values()) % 200 == 0:
                    progress(f'Контекст: {sum(counts.values())} записей, включено {counts["INCLUDED"]}')
                write_row(coverage, {'id': row['id'], 'source_id': row['source_id'], 'revision_id': row['revision_id'],
                                     'locator': row['locator'], 'state': state, 'reason': reason, 'matched_terms': matched})
                if state == 'INCLUDED':
                    write_row(context, row)
                    txt.write('\n===== ' + canonical({k: row[k] for k in ('id', 'source_sha256', 'locator')}) + ' =====\n')
                    txt.write(text)
                    txt.write('\n===== END =====\n')
        report = {'schema': 'sce.goal.coverage.v1', 'goal_id': identity('goal', goal), 'goal': goal,
                  'input_labels_sha256': manifest['labels_sha256'], 'terms': terms, 'include_all': include_all,
                  'counts': counts, 'every_label_record_accounted': True,
                  'source_enumeration_complete': manifest['enumeration_complete'],
                  'source_enumeration_completeness_basis': manifest['enumeration_completeness_basis'],
                  'all_modalities_interpreted': False, 'semantic_relevance': 'NOT_VERIFIED',
                  'goal_achieved': 'NOT_RUN', 'laya_inference': 'NOT_RUN',
                  'no_top_k_cap': True, 'context_unit': 'characters_not_model_tokens',
                  'context_sha256': digest_file(temp / 'context.jsonl', cancel),
                  'coverage_sha256': digest_file(temp / 'coverage.jsonl', cancel)}
        (temp / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, destination)
        return report
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise

def compare_revisions(old_labels, new_labels, destination):
    """Conservative dependency invalidation; graph/coverage are never proof of goal success."""
    def revisions(folder):
        path = Path(folder)
        manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
        if digest_file(path / 'labels.jsonl') != manifest['labels_sha256']:
            raise ValueError('CORRUPT_LABELS')
        return manifest, {r['source_id']: r for r in jsonl(path / 'labels.jsonl') if r['kind'] == 'source'}
    old_manifest, old = revisions(old_labels)
    new_manifest, new = revisions(new_labels)
    changes = []
    for sid in sorted(set(old) | set(new)):
        a, b = old.get(sid), new.get(sid)
        state = 'ADDED' if not a else 'REMOVED' if not b else 'UNCHANGED' if a['revision_id'] == b['revision_id'] else 'CHANGED'
        annotations_changed = bool(a and b and a.get('annotation_revision_id') != b.get('annotation_revision_id'))
        changes.append({'source_id': sid, 'state': state,
                        'old_revision': a['revision_id'] if a else None,
                        'new_revision': b['revision_id'] if b else None,
                        'annotation_revision_changed': annotations_changed,
                        'old_annotation_revision': a.get('annotation_revision_id') if a else None,
                        'new_annotation_revision': b.get('annotation_revision_id') if b else None,
                        'invalidate_old_dependent_context': state in ('REMOVED', 'CHANGED') or annotations_changed})
    result = {'schema': 'sce.revision.diff.v1', 'changes': changes,
              'new_sources_require_context_reassembly': any(x['state'] == 'ADDED' for x in changes),
              'labels_artifact_changed': old_manifest['labels_sha256'] != new_manifest['labels_sha256'],
              'dependent_context_reassembly_required': old_manifest['labels_sha256'] != new_manifest['labels_sha256'],
              'reassembly_rule': 'Conservative: any labels artifact change includes tags, metadata, segmentation and derivative messages.',
              'duplicate_path_order_caveat': 'Reordering same-path duplicate entries changes occurrence identity.'}
    p = Path(destination)
    with p.open('x', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    b.add_argument('pack'); b.add_argument('destination')
    b.add_argument('--namespace'); b.add_argument('--project'); b.add_argument('--tag', action='append', default=[])
    b.add_argument('--span-chars', type=int, default=4096)
    g = sub.add_parser('goal')
    g.add_argument('labels'); g.add_argument('destination'); g.add_argument('--goal', required=True)
    g.add_argument('--include-all', action='store_true')
    d = sub.add_parser('diff')
    d.add_argument('old'); d.add_argument('new'); d.add_argument('destination')
    a = p.parse_args()
    if a.command == 'build':
        result = build_labels(a.pack, a.destination, a.namespace, a.project, a.tag, a.span_chars)
    elif a.command == 'goal':
        result = assemble_goal(a.labels, a.goal, a.destination, a.include_all)
    else:
        result = compare_revisions(a.old, a.new, a.destination)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
