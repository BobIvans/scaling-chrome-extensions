#!/usr/bin/env python3
"""Independent synthetic data-contract QA, NOT an SCE planner implementation.

Metadata for this small fixture is kept in memory. Payload hashes are checked
against independent raw source fixtures. SCC expectations are tested by mutual
reachability, with no import/call of repo_source/import_graph/components.
"""
import hashlib
import json
import sys
from pathlib import Path
from collections import defaultdict
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote


def need(condition, code):
    if not condition:
        raise ValueError(code)


def unique(pairs):
    value = {}
    for k, v in pairs:
        need(k not in value, 'DUPLICATE_JSON_KEY')
        value[k] = v
    return value


def bad_constant(value):
    raise ValueError('NONFINITE_JSON')


def decode(text):
    return json.loads(text, object_pairs_hook=unique, parse_constant=bad_constant)


def read(path):
    return decode(path.read_text(encoding='utf-8'))


def rows(path):
    result = []
    with path.open('r', encoding='utf-8', newline='') as f:
        for line in f:
            need(line.endswith('\n') and bool(line.strip()), 'JSONL_LINE')
            result.append(decode(line))
    return result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def digest(obj):
    return sha(json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False).encode())


def source_id(path):
    return digest({'schema':'occ.repo-logical-source.v1','namespace':'code','repository':'sce','path':path})


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        need(tag not in {'script','iframe','embed','object','base'}, 'ACTIVE_HTML')
        for key, value in attrs:
            need(not key.lower().startswith('on'), 'ACTIVE_HTML')
            if key=='id':
                need(value not in self.ids, 'DUPLICATE_HTML_ID')
                self.ids.add(value)
            if key in {'href','src'}:
                need(value is not None, 'EMPTY_LINK')
                self.links.append(value)


def links(root):
    parsers = {}
    for file in root.rglob('*.html'):
        parser = HTMLLinks()
        parser.feed(file.read_text(encoding='utf-8'))
        parser.close()
        parsers[file.resolve()] = parser
    count = 0
    for path, parser in parsers.items():
        for link in parser.links:
            url = urlsplit(link)
            need(not url.scheme and not url.netloc and not url.query, 'NONRELATIVE_LINK')
            name = unquote(url.path)
            need(not name.startswith(('/','\\')) and '\\' not in name, 'UNSAFE_LINK')
            target=(path.parent/name).resolve() if name else path
            need(target.is_relative_to(root.resolve()) and target.is_file(), 'BROKEN_LINK')
            if url.fragment:
                need(target in parsers and unquote(url.fragment) in parsers[target].ids, 'BROKEN_FRAGMENT')
            count += 1
    return count


def reachability_components(nodes, edges):
    # A deliberately different oracle from iterative Kosaraju used by the app.
    adjacency={n:set() for n in nodes}
    for edge in edges:
        need(edge['from'] in adjacency and edge['to'] in adjacency, 'ORACLE_EDGE_OUTSIDE_SCOPE')
        adjacency[edge['from']].add(edge['to'])
    reach={}
    for start in nodes:
        seen, todo={start},[start]
        while todo:
            current=todo.pop()
            for next_node in adjacency[current]:
                if next_node not in seen:
                    seen.add(next_node)
                    todo.append(next_node)
        reach[start]=seen
    return {frozenset(n for n in nodes if n in reach[start] and start in reach[n]) for start in nodes}


def verify(root):
    root=Path(root).resolve()
    need(root.is_dir(), 'FIXTURE_DIRECTORY_REQUIRED')
    policy=read(root/'POLICY.json')
    batch=read(root/'BATCH.json')
    summary=read(root/'GROUPS.json')
    coverage=read(root/'COVERAGE.json')
    oracle=read(root/'EXPECTED_ORACLE.json')
    for p in root.rglob('*'):
        need(not p.is_symlink(), 'FIXTURE_SYMLINK')
    need(digest(batch['binding'])==batch['batch_id'], 'BATCH_DIGEST')
    for item in batch['outputs']+summary['outputs']:
        p=root/item['path']
        need(p.is_file() and p.stat().st_size==item['bytes'] and file_hash(p)==item['sha256'], 'OUTPUT_HASH')
    bind=summary['binding']
    need(digest(bind)==summary['grouping_batch_id'] and bind['base_batch_id']==batch['batch_id'], 'GROUP_BATCH_DIGEST')
    need(bind['eligibility_digest']==file_hash(root/'SOURCE_ELIGIBILITY.jsonl'), 'ELIGIBILITY_DIGEST')
    need(bind['analysis_digest']==file_hash(root/'ANALYSIS.jsonl'), 'ANALYSIS_DIGEST')
    need(bind['declared_map_digest']==file_hash(root/'DECLARED_MAP.json'), 'DECLARED_MAP_DIGEST')
    need(bind['policy_digest']==digest(policy) and bind['roots']==policy['python_roots'], 'POLICY_DIGEST')
    entries=rows(root/'REPO_MANIFEST.jsonl')
    parts=rows(root/'PARTS_INDEX.jsonl')
    eligible=rows(root/'SOURCE_ELIGIBILITY.jsonl')
    heads=rows(root/'GROUP_HEADS.jsonl')
    members=rows(root/'GROUP_MEMBERS.jsonl')
    segments=rows(root/'GROUP_PARTS.jsonl')
    relations=rows(root/'RELATIONS.jsonl')
    unresolved=rows(root/'UNRESOLVED.jsonl')
    need([e['ordinal'] for e in entries]==list(range(len(entries))), 'ENTRY_ORDER')
    by_path={e['path']:e for e in entries}
    need(len(by_path)==len(entries), 'ENTRY_DUPLICATE')
    by_source={source_id(p):p for p in by_path}
    by_eligibility={e['source_id']:e for e in eligible}
    need(set(by_eligibility)==set(by_source) and len(eligible)==len(entries), 'ELIGIBILITY_SET')
    for e in eligible:
        need(e['source_id']==source_id(e['path']) and e['file_sha256']==by_path[e['path']]['file_sha256'], 'ELIGIBILITY_IDENTITY')
        need(type(e['text_exportable']) is bool and type(e['code_analysis_eligible']) is bool, 'ELIGIBILITY_BOOLEAN')
        need(not e['code_analysis_eligible'] or e['text_exportable'], 'CODE_REQUIRES_TEXT')
    for p in oracle['must_not_code_parse']:
        e=by_eligibility[source_id(p)]
        need(e['text_exportable'] is False and e['code_analysis_eligible'] is False, 'WHOLE_SOURCE_ELIGIBILITY')
    need([h['group_id'] for h in heads]==sorted(h['group_id'] for h in heads), 'GROUP_ORDER')
    by_group={h['group_id']:h for h in heads}
    need(len(by_group)==len(heads), 'GROUP_DUPLICATE')
    membership={}
    group_members=defaultdict(list)
    for m in members:
        need(m['source_id'] in by_source and m['source_id'] not in membership, 'MEMBERSHIP_DUPLICATE_OR_ORPHAN')
        need(m['group_id'] in by_group and m['source_id']==source_id(m['path']), 'MEMBER_IDENTITY')
        entry=by_path[m['path']]
        e=by_eligibility[m['source_id']]
        need(m['entry_ordinal']==entry['ordinal'] and m['file_sha256']==entry['file_sha256']
             and m['state']==entry['state'] and m['raw_part_count']==entry['chunk_count'], 'MEMBER_BINDING')
        need(m['text_exportable']==e['text_exportable'] and m['code_analysis_eligible']==e['code_analysis_eligible'], 'MEMBER_ELIGIBILITY')
        membership[m['source_id']]=m['group_id']
        group_members[m['group_id']].append(m)
    need(set(membership)==set(by_source), 'MEMBERSHIP_SET')
    topology=[]
    static_pairs=set()
    seen_relations=set()
    for relation in relations:
        rid=relation['relation_id']
        need(rid not in seen_relations, 'RELATION_DUPLICATE')
        seen_relations.add(rid)
        need(digest({k:v for k,v in relation.items() if k!='relation_id'})==rid, 'RELATION_DIGEST')
        for prefix in ['from','to']:
            src=relation[prefix+'_source_id']
            need(src in by_source and by_source[src]==relation[prefix+'_path'], 'RELATION_ENDPOINT')
            need(by_path[by_source[src]]['file_sha256']==relation[prefix+'_sha256'], 'RELATION_ENDPOINT_HASH')
        kind=relation['relation_kind']
        accepted=kind in {'PYTHON_STATIC_IMPORT','STATIC_TEST_IMPORT'}
        need(type(relation['topology']) is bool and relation['topology'] is accepted, 'RELATION_TOPOLOGY_CLASS')
        need(relation['observed_test_coverage']=='NOT_MEASURED' and relation['capability_status']=='NOT_QUALIFIED', 'FALSE_QUALIFICATION')
        if accepted:
            need(all(by_eligibility[relation[p+'_source_id']]['code_analysis_eligible'] for p in ['from','to']), 'TOPOLOGY_INELIGIBLE')
            need(relation['evidence_class']=='STATIC_LOCAL' and relation['anchor_kind']=='IMPORT_START_LINE_ONLY', 'STATIC_PROVENANCE')
            topology.append({'from':relation['from_path'],'to':relation['to_path']})
            static_pairs.add((relation['from_path'],relation['to_path']))
        elif kind=='OPERATOR_DECLARED_CONTRACT':
            need(relation['evidence_class']=='OPERATOR_DECLARATION', 'DECLARED_PROVENANCE')
        elif kind=='HEURISTIC_TEST_CANDIDATE':
            need(relation['evidence_class']=='NAME_HEURISTIC', 'HEURISTIC_PROVENANCE')
        else:
            raise ValueError('UNKNOWN_RELATION_KIND')
    need(static_pairs=={(x['from'],x['to']) for x in oracle['topology_edges']}, 'STATIC_EDGE_EXPECTATIONS')
    expected_components={frozenset(c) for c in oracle['components']}
    need(reachability_components(sorted(by_path),topology)==expected_components, 'SCC_ORACLE')
    actual_components={frozenset(m['path'] for m in group_members[g]) for g in by_group}
    need(actual_components==expected_components, 'SCC_MEMBERSHIP')
    need({(r['path'],r['status']) for r in unresolved}=={(r['path'],r['status']) for r in oracle['expected_unresolved']}, 'UNRESOLVED_SET')
    for r in unresolved:
        need(r['source_id']==source_id(r['path']) and r['file_sha256']==by_path[r['path']]['file_sha256'], 'UNRESOLVED_BINDING')
        need(digest({k:v for k,v in r.items() if k!='unresolved_id'})==r['unresolved_id'], 'UNRESOLVED_DIGEST')
    base_parts={p['part_id']:p for p in parts}
    need(len(base_parts)==len(parts), 'BASE_PART_DUPLICATE')
    refs_seen=set()
    by_segment={s['group_part_id']:s for s in segments}
    need(len(by_segment)==len(segments), 'SEGMENT_DUPLICATE')
    group_segments=defaultdict(list)
    for s in segments:
        need(s['group_id'] in by_group, 'SEGMENT_GROUP')
        need(s['payload_is_reference_only'] is True and bool(s['raw_refs']), 'SEGMENT_ROLE')
        need(len(s['raw_refs'])<=policy['max_refs_per_segment'], 'SEGMENT_REF_BUDGET')
        raw_total=0
        for r in s['raw_refs']:
            p=base_parts.get(r['part_id'])
            need(p is not None and r['part_id'] not in refs_seen, 'RAW_REFERENCE_DUPLICATE_OR_ORPHAN')
            refs_seen.add(r['part_id'])
            need(r['source_id']==source_id(p['path']) and membership[r['source_id']]==s['group_id'], 'RAW_REFERENCE_OWNER')
            need(all(r[k]==p[k] for k in ['part_id','logical_id','revision','source_start','source_end','bytes','sha256']), 'RAW_REFERENCE_BINDING')
            need(r['text_eligible']==by_eligibility[r['source_id']]['text_exportable'], 'RAW_REFERENCE_ELIGIBILITY')
            raw_total+=r['bytes']
        need(raw_total==s['raw_reference_bytes'] and raw_total<=policy['raw_reference_bytes_per_segment'], 'RAW_SEGMENT_BUDGET')
        frame=len(json.dumps(s,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())+1
        need(frame<=policy['reference_frame_bytes'], 'FRAME_SEGMENT_BUDGET')
        part_identity={'schema':'occ.repo-group-part.v1','group_id':s['group_id'],
                       'chunk_logical_ids':[r['logical_id'] for r in s['raw_refs']],'policy_digest':digest(policy)}
        need(digest(part_identity)==s['group_part_id'], 'GROUP_PART_ID')
        need(digest({'group_part_id':s['group_part_id'],'base_batch_id':batch['batch_id'],'raw_refs':s['raw_refs'],
                     'previous':s['previous'],'next':s['next']})==s['revision'], 'GROUP_PART_REVISION')
        group_segments[s['group_id']].append(s)
    need(refs_seen==set(base_parts), 'RAW_REFERENCE_SET')
    for gid, head in by_group.items():
        gm=sorted(group_members[gid],key=lambda x:x['path'])
        need(digest({'schema':'occ.repo-logical-group.v1','planner_version':policy['planner_version'],
                     'members':sorted(m['source_id'] for m in gm)})==gid, 'GROUP_ID')
        related=sorted(r['relation_id'] for r in relations if r['from_source_id'] in {m['source_id'] for m in gm}
                       or r['to_source_id'] in {m['source_id'] for m in gm})
        unresolved_ids=sorted(r['unresolved_id'] for r in unresolved if r['source_id'] in {m['source_id'] for m in gm})
        rev={'group_id':gid,'members':[{'source_id':m['source_id'],'file_sha256':m['file_sha256']} for m in gm],
             'related_relation_ids':related,'unresolved_ids':unresolved_ids,'policy_digest':digest(policy)}
        need(digest(rev)==head['group_revision'], 'GROUP_REVISION')
        gs=sorted(group_segments[gid],key=lambda x:x['ordinal'])
        need(head['member_count']==len(gm) and head['segment_count']==len(gs)
             and head['raw_part_count']==sum(m['raw_part_count'] for m in gm), 'GROUP_COUNTS')
        for n, s in enumerate(gs):
            need(s['ordinal']==n and s['previous']==(gs[n-1]['group_part_id'] if n else None)
                 and s['next']==(gs[n+1]['group_part_id'] if n+1<len(gs) else None), 'SEGMENT_CHAIN')
    cycle=by_group[oracle['cycle_group_id']]
    need(cycle['member_count']==3 and cycle['segment_count']>=oracle['minimum_cycle_segments'], 'CYCLE_CONTINUATION')
    for src in oracle['raw_sources']:
        raw=root/'raw'/Path(src['raw_path']).name
        need(raw.stat().st_size==src['bytes'] and file_hash(raw)==src['sha256'], 'RAW_SOURCE_HASH')
        raw_bytes=raw.read_bytes() # bounded synthetic corpus only, not a production streaming reader.
        entry=by_path[src['path']]
        original_parts=sorted((p for p in parts if p['path']==src['path']),key=lambda x:x['chunk_ordinal'])
        cursor=0
        for n,p in enumerate(original_parts):
            need(p['chunk_ordinal']==n and p['source_start']==cursor, 'SOURCE_RANGE')
            piece=raw_bytes[p['source_start']:p['source_end']]
            need(len(piece)==p['bytes'] and sha(piece)==p['sha256'], 'SOURCE_PART_BYTES')
            need(digest([p['logical_id'],entry['file_sha256'],p['sha256'],p['source_start'],p['source_end']])==p['revision']==p['part_id'], 'SOURCE_PART_REVISION')
            cursor=p['source_end']
        need(cursor==len(raw_bytes) and bool(original_parts), 'SOURCE_RECONSTRUCTION')
        need(hashlib.sha1(b'blob '+str(len(raw_bytes)).encode()+b'\0'+raw_bytes).hexdigest()==entry['git_oid'], 'SOURCE_GIT_OID')
    for p, ident in oracle['common_ids_after_addition']['sources'].items():
        need(source_id(p)==ident, 'STABLE_SOURCE_ID')
    added_path=oracle['unrelated_addition']
    added_components=reachability_components(sorted([*by_path,added_path]),topology)
    need(added_components==expected_components|{frozenset({added_path})}, 'ADDITION_SCC_ORACLE')
    for component in expected_components:
        gid=digest({'schema':'occ.repo-logical-group.v1','planner_version':policy['planner_version'],
                    'members':sorted(source_id(p) for p in component)})
        need(all(oracle['common_ids_after_addition']['groups'][p]==gid for p in component), 'STABLE_GROUP_ID')
    need(reachability_components(list(reversed(sorted(by_path))),list(reversed(topology)))==expected_components, 'SHUFFLED_ORACLE')
    counts=summary['counts']
    need(counts=={'entries':len(entries),'groups':len(heads),'segments':len(segments),'parts':len(parts),
                  'relations':len(relations),'unresolved':len(unresolved)}, 'SUMMARY_COUNTS')
    need(coverage['entry_count']==len(entries) and coverage['captured_part_count']==len(parts)
         and coverage['group_count']==len(heads) and coverage['segment_count']==len(segments), 'COVERAGE_COUNTS')
    need(coverage['all_entries_grouped'] is True and coverage['all_captured_parts_referenced'] is True
         and coverage['all_tracked_bytes_exportable'] is False and coverage['ai_read']=='UNKNOWN', 'FALSE_COVERAGE_CLAIM')
    need(coverage['text_eligible_reference_count']==sum(r['text_eligible'] for s in segments for r in s['raw_refs']), 'TEXT_COVERAGE_COUNT')
    need(coverage['unique_raw_reference_bytes']==sum(p['bytes'] for p in parts), 'RAW_COVERAGE_COUNT')
    return {'status':'PASS','scope':'SYNTHETIC_DATA_CONTRACT_ONLY_NOT_APPLICATION_RUNTIME',
            'entry_count':len(entries),'group_count':len(heads),'segment_count':len(segments),'raw_part_count':len(parts),
            'cycle_member_count':3,'cycle_segments':cycle['segment_count'],'relations':len(relations),'unresolved':len(unresolved),
            'raw_source_bytes':sum(x['bytes'] for x in oracle['raw_sources']),'relative_links':links(root),
            'scc_oracle':'INDEPENDENT_MUTUAL_REACHABILITY_PASS','stable_id_oracle':'PASS',
            'shuffled_oracle':'PASS','application_planner_tests':'NOT_RUN','pr005_interop':'NOT_RUN','device':'NOT_RUN','usefulness_trial':'NOT_RUN'}


if __name__=='__main__':
    try:
        need(len(sys.argv)==2,'USAGE_VERIFY_GROUPING_DIRECTORY')
        print(json.dumps(verify(Path(sys.argv[1])),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'FAIL','reason':str(exc)},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)
