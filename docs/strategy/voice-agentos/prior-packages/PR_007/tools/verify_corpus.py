"""Verify synthetic labels/ranges and resolver oracle; no real AST parser."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from relation_fixture_oracle import digest, logical_id, relation, resolve

ROOT=Path(__file__).resolve().parents[1]


def check(ok,reason):
    if not ok:
        raise ValueError(reason)


def verify(case,raw):
    check(len(raw)==case['raw_bytes'] and hashlib.sha256(raw).hexdigest()==case['raw_sha256'],'raw source hash')
    check(case['source_path'].startswith(case['scope_root']+'/'),'source scope')
    check(case['synthetic'] and not case['ast_adapter_executed'],'synthetic scope')
    refs=case['expected_refs']
    if case['expected_analysis']=='PARSER_FAILED':
        check(not refs and not case['expected_symbols'],'error AST must not leak exact edges')
    ids=[]
    for ref in refs:
        a,b=ref['byte_start'],ref['byte_end']
        check(type(a) is int and type(b) is int and 0<=a<b<=len(raw),'range bounds')
        piece=raw[a:b]
        check(hashlib.sha256(piece).hexdigest()==ref['range_sha256'],'range hash')
        check(piece.decode('utf-8')==ref['literal_or_expression'],'literal raw span')
        if ref['specifier'] is not None:
            check(json.loads(piece.decode('utf-8'))==ref['specifier'],'decoded literal specifier')
        target,reason=resolve(case,ref)
        check(reason==ref['reason'] and (target['path'] if target else None)==ref['target_path'],'resolution label')
        check((target['raw_sha256'] if target else None)==ref['target_sha256'],'target hash')
        check(ref['resolution_status']==('UNRESOLVED' if reason else 'LOCAL_STATIC_EXACT_PATH'),'status label')
        if ref['syntax_form'] in {'DYNAMIC_IMPORT','COMPUTED_IMPORT','COMMONJS_REQUIRE'}:
            check(ref['resolution_status']=='UNRESOLVED','unsafe exact inference')
        ids.append(logical_id('code','sce',case['source_path'],ref))
    check(len(ids)==len(set(ids)),'duplicate logical edge')
    for sym in case['expected_symbols']:
        a,b=sym['byte_start'],sym['byte_end']
        check(0<=a<b<=len(raw) and hashlib.sha256(raw[a:b]).hexdigest()==sym['range_sha256'],'symbol range hash')
        check(sym['name'].encode() in raw[a:b],'symbol name evidence')
    return len(refs)


def run():
    corpus=json.loads((ROOT/'fixtures/LABELLED_CORPUS.json').read_text())
    cases=corpus['cases']
    check(len(cases)==len({c['case_id'] for c in cases})==200,'case count')
    families=Counter(c['family_id'] for c in cases)
    check(len(families)==20 and set(families.values())=={10},'family/variation count')
    check(not corpus['independent_holdout'],'false holdout claim')
    refs_total=0
    records=[]
    interpretation=digest({'kind':'synthetic-label-oracle','version':'fixture-v1','ast_executed':False})
    for case in cases:
        raw=(ROOT/case['raw_file']).read_bytes()
        refs_total+=verify(case,raw)
        for ref in case['expected_refs']:
            records.append(relation(case,ref,interpretation))
    records.sort(key=lambda r:(r['source_path'],r['byte_start'],r['edge_id']))
    graph_digest=digest(records)
    reverse=[]
    for case in reversed(cases):
        reverse.extend(relation(case,r,interpretation) for r in reversed(case['expected_refs']))
    reverse.sort(key=lambda r:(r['source_path'],r['byte_start'],r['edge_id']))
    check(digest(reverse)==graph_digest,'order-dependent graph digest')
    first=next(c for c in cases if c['expected_refs'] and c['expected_refs'][0]['resolution_status']=='LOCAL_STATIC_EXACT_PATH')
    raw=(ROOT/first['raw_file']).read_bytes()
    changed=deepcopy(first)
    changed['manifest'].append({'path':first['scope_root']+'/unrelated.ts','raw_sha256':'b'*64,'analysis_eligible':True})
    ref=first['expected_refs'][0]
    check(logical_id('code','sce',first['source_path'],ref)==logical_id('code','sce',changed['source_path'],changed['expected_refs'][0]),'unrelated renumber')
    original=relation(first,ref,interpretation)
    new_version=relation(first,ref,digest({'kind':'synthetic-label-oracle','version':'fixture-v2'}))
    check(original['edge_id']==new_version['edge_id'] and original['revision']!=new_version['revision'],'interpretation invalidation')
    target_changed=deepcopy(first)
    target_changed['manifest'][1]['raw_sha256']='f'*64
    check(relation(target_changed,ref,interpretation)['revision']!=original['revision'],'target invalidation')
    check(relation(first,ref,interpretation,'e'*64)['edge_id']==original['edge_id'],'snapshot renumber')
    check(relation(first,ref,interpretation,'e'*64)['revision']!=original['revision'],'snapshot revision')
    mutations=[]
    c=deepcopy(first);c['expected_refs'][0]['byte_start']+=1;mutations.append((c,raw))
    c=deepcopy(first);c['expected_refs'][0]['range_sha256']='0'*64;mutations.append((c,raw))
    c=deepcopy(first);c['raw_sha256']='0'*64;mutations.append((c,raw))
    c=deepcopy(first);c['expected_refs'][0]['target_path']=first['source_path'];mutations.append((c,raw))
    c=deepcopy(first);c['expected_refs'][0]['target_sha256']='0'*64;mutations.append((c,raw))
    c=deepcopy(next(c for c in cases if c['family_id']=='DYNAMIC_LITERAL'));c['expected_refs'][0]['resolution_status']='LOCAL_STATIC_EXACT_PATH';mutations.append((c,(ROOT/c['raw_file']).read_bytes()))
    c=deepcopy(next(c for c in cases if c['family_id']=='SYNTAX_ERROR'));c['expected_refs']=[deepcopy(ref)];mutations.append((c,(ROOT/c['raw_file']).read_bytes()))
    c=deepcopy(first);c['expected_refs'][0]['literal_or_expression']='changed';mutations.append((c,raw))
    rejected=0
    for c,b in mutations:
        try:
            verify(c,b)
        except ValueError:
            rejected+=1
    check(rejected==len(mutations),'mutation accepted')
    check(len(records)==refs_total==171,'reference count')
    check(cases[-1]['case_id']=='JS007-200','tail omitted')
    check(not any(c['expected_refs'] for c in cases if c['family_id'] in {'COMMENT_FAKE','STRING_FAKE'}),'fake syntax reference')
    known_dynamic=[r for c in cases for r in c['expected_refs'] if r['syntax_form'] in {'DYNAMIC_IMPORT','COMPUTED_IMPORT'}]
    check(len(known_dynamic)==20 and all(r['resolution_status']=='UNRESOLVED' for r in known_dynamic),'dynamic label gap')
    golden=(ROOT/'fixtures/derived_golden/RELATIONS.jsonl').read_text().splitlines()
    check([json.loads(x) for x in golden]==records,'golden records drift')
    return {'status':'PASS','scope':'Synthetic source labels/ranges and resolver/identity oracle only; NOT AST/application qualification',
            'cases':200,'families':20,'variants_per_family':10,'references':refs_total,
            'local_static_labels':sum(r['resolution_status']=='LOCAL_STATIC_EXACT_PATH' for r in records),
            'unresolved_labels':sum(r['resolution_status']=='UNRESOLVED' for r in records),
            'known_dynamic_labels':20,'malformed_mutations_rejected':rejected,
            'ordered_fixture_graph_digest':graph_digest,'application_runtime_executed':False,
            'ast_adapter_executed':False,'independent_holdout':False,'qualified_precision':None,'qualified_recall':None}


if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
