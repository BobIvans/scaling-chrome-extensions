"""Check authored synthetic contracts, not an implementation of the SCE importer."""
from pathlib import Path
import hashlib, json, re, sqlite3, sys
from html.parser import HTMLParser


def check(ok, message):
    if not ok:
        raise ValueError(message)


def compact(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ident(v):
    return sha(compact(v))


def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('DUPLICATE_JSON_KEY')
        value[key]=item
    return value


def finite(value):
    raise ValueError('NONFINITE_JSON')


def source_json(raw):
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError as e:raise ValueError('INVALID_UTF8') from e
    try:return json.loads(text,object_pairs_hook=unique,parse_constant=finite)
    except json.JSONDecodeError as e:raise ValueError('INVALID_JSON') from e


def ptr(value,path):
    for token in path.lstrip('/').split('/'):
        token=token.replace('~1','/').replace('~0','~')
        value=value[int(token)] if isinstance(value,list) else value[token]
    return value


def valid_legacy_shape(data):
    if not isinstance(data,list) or not data:return 'UNSUPPORTED_JSON_SHAPE'
    ids=set()
    for conv in data:
        if not isinstance(conv,dict) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}',str(conv.get('id',''))):return 'LEGACY_SCHEMA_ERROR'
        if conv['id'] in ids:return 'LEGACY_SCHEMA_ERROR'
        ids.add(conv['id'])
        if not isinstance(conv.get('mapping'),dict):return 'LEGACY_SCHEMA_ERROR'
        for node_id,node in conv['mapping'].items():
            if not isinstance(node,dict):return 'LEGACY_SCHEMA_ERROR'
            msg=node.get('message')
            if msg is None:continue
            if not isinstance(msg,dict):return 'LEGACY_SCHEMA_ERROR'
            role=msg.get('author',{}).get('role')
            if not isinstance(role,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}',role):return 'LEGACY_SCHEMA_ERROR'
    for conv in data:
        for node in conv['mapping'].values():
            children=node.get('children',[])
            if not isinstance(children,list) or any(not isinstance(c,str) for c in children):return 'LEDGER_SCHEMA_ERROR'
    return None


def expected_text(content):
    if not isinstance(content,dict):return None
    if isinstance(content.get('parts'),list):
        chunks=[part for part in content['parts'] if isinstance(part,str) and part.strip()]
    else:
        chunks=[content['text']] if isinstance(content.get('text'),str) and content['text'].strip() else []
    return '\n'.join(chunks) or None


def expected_gaps(conversations):
    gaps=[]
    for conv in conversations:
        cid=conv['id'];mapping=conv['mapping']
        for node_id,node in mapping.items():
            parent=node.get('parent')
            if parent is not None and parent not in mapping:
                gaps.append({'conversation_id':cid,'code':'MISSING_PARENT','node_id':node_id,'target':parent})
            elif parent is not None and node_id not in mapping[parent].get('children',[]):
                gaps.append({'conversation_id':cid,'code':'PARENT_CHILD_MISMATCH','node_id':parent,'target':node_id})
            for child in node.get('children',[]):
                if child not in mapping:gaps.append({'conversation_id':cid,'code':'MISSING_CHILD','node_id':node_id,'target':child})
                elif mapping[child].get('parent')!=node_id:gaps.append({'conversation_id':cid,'code':'PARENT_CHILD_MISMATCH','node_id':node_id,'target':child})
        current=conv.get('current_node')
        if current is not None and current not in mapping:
            gaps.append({'conversation_id':cid,'code':'CURRENT_NODE_MISSING','node_id':None,'target':current})
        # Independent parent-walk oracle; each node has at most one parent.
        cycles=set()
        for start in mapping:
            chain=[];where={};at=start
            while at in mapping and at not in where:
                where[at]=len(chain);chain.append(at);at=mapping[at].get('parent')
            if at in where:cycles.add(tuple(sorted(chain[where[at]:])))
        for members in cycles:gaps.append({'conversation_id':cid,'code':'PARENT_CYCLE','node_id':None,'members':list(members)})
    return sorted({compact(g):g for g in gaps}.values(),key=compact)


class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.hrefs.extend(value for name,value in attrs if name=='href')


def verify_fixture(root):
    root=Path(root)
    fixture=root/'fixtures/import_fidelity_golden'
    data=json.loads((fixture/'CASES.json').read_text())
    cases=data['cases'];check(len(cases)==data['case_count']==18,'case count')
    captures=[json.loads(line) for line in (fixture/'CAPTURES.jsonl').read_text().splitlines()]
    check(len(captures)==len(cases),'capture count')
    by_capture={row['case_id']:row for row in captures};check(len(by_capture)==len(cases),'duplicate capture')
    blobs={};versions={};extractions={};origins={};payloads={};ledgers={};states={};node_rows=[];attachment_rows=[]
    db=sqlite3.connect(':memory:')
    sql=(root/'contracts/DRAFT_OWNER_SCHEMA.sql').read_text()
    db.executescript(sql);db.executescript(sql)
    for case in cases:
        cid=case['case_id'];cap=by_capture[cid];raw=(fixture/case['raw_path']).read_bytes()
        check(sha(raw)==case['raw_sha256']==cap['raw_sha256'],'original hash '+cid)
        check(len(raw)==case['input_bytes']==cap['input_bytes'],'original size '+cid)
        captured=len(raw)<=case['policy']['max_input_bytes']
        check(captured==case['expected_original_retained']==cap['original_retained'],'capture budget truth '+cid)
        if not captured:
            check(case['expected_disposition']==cap['disposition']=='NOT_CAPTURED','budget disposition')
            check(cap['source_version_id'] is None and cap['extraction_id'] is None and cap['ledger_path'] is None,'fabricated capture identity')
            continue
        sid=ident({'schema':'occ.import-source-version.v1','namespace':case['namespace'],'source_key':case['source_key'],'raw_sha256':sha(raw)})
        key=ident({'schema':'occ.import-extractor-key.v1','adapter_version':case['adapter_version'],'text_adapter':'chatgpt-export.v1',
                   'attachment_adapter':'occ.attachment-inventory.v1','policy':case['policy']})
        eid=ident({'schema':'occ.import-extraction.v1','source_version_id':sid,'extractor_key':key})
        oid=ident({'schema':'occ.import-origin.v1','source_version_id':sid,'origin_locator':case['origin_locator'],
                   'scope_policy':case['policy']['scope_policy']})
        check((sid,key,eid,oid)==(cap['source_version_id'],cap['extractor_key'],cap['extraction_id'],cap['origin_id']),'identity '+cid)
        payload=json.loads((fixture/case['ledger_path']).read_text());encoded=compact(payload)
        check(sha(encoded)==cap['payload_sha256'],'ledger hash '+cid)
        check(len(encoded)<=case['policy']['max_ledger_utf8_bytes'],'ledger byte budget')
        check(payload['source_version_id']==sid and payload['raw_sha256']==sha(raw) and payload['extractor_key']==key and payload['extraction_id']==eid,'ledger binding')
        check(payload['remote_completeness']=='UNKNOWN' and payload['network_fetches']==0,'false remote completeness')
        check(payload['disposition']==case['expected_disposition']==cap['disposition'],'disposition '+cid)
        try:
            parsed=source_json(raw);error=valid_legacy_shape(parsed)
        except ValueError as e:parsed=None;error=str(e)
        check(error==case['expected_error_reason']==payload['error_reason'],'expected parse/schema error '+cid)
        if error:
            check(payload['disposition']=='ERROR' and not payload['nodes'] and not payload['attachments'],'error partial writes')
        else:
            mapping={(conv['id'],node_id):(ci,node) for ci,conv in enumerate(parsed) for node_id,node in conv['mapping'].items()}
            keys=[(r['conversation_id'],r['node_id']) for r in payload['nodes']]
            check(len(keys)==len(set(keys))==len(mapping) and set(keys)==set(mapping),'node coverage '+cid)
            check(len(keys)<=case['policy']['max_total_mapping_nodes'],'mapping node budget')
            selected=sorted(conv['id'] for conv in parsed)
            check(payload['selected_conversation_ids']==selected==case['selected_conversations'],'selected scope '+cid)
            check(payload['conversation_metadata']==[{k:conv.get(k) for k in ['id','title','create_time','update_time','current_node']} for conv in parsed],'conversation metadata revision')
            for row in payload['nodes']:
                ci,node=mapping[(row['conversation_id'],row['node_id'])]
                check(ptr(parsed,row['json_pointer'])==node,'JSON Pointer '+cid)
                check(row['exact_raw_byte_range'] is None,'invented raw byte range')
                check(row['parent_node_id']==node.get('parent') and row['declared_children']==node.get('children',[]),'parent/children preservation')
                msg=node.get('message');content=msg.get('content') if isinstance(msg,dict) else None;text=expected_text(content)
                nontext=isinstance(content,dict) and isinstance(content.get('parts'),list) and any(not isinstance(p,str) for p in content['parts'])
                expected='STRUCTURAL_NODE' if msg is None else 'TEXT_EXTRACTED' if text is not None else 'NON_TEXT_ONLY' if nontext else 'EMPTY_CONTENT'
                check(row['state']==expected,'node state '+cid)
                check(row['author_role']==(None if msg is None else msg['author']['role']),'role preservation')
                check(row['author_confidence']==('UNKNOWN' if msg is None else 'DECLARED_FIELD_UNVERIFIED'),'authorship truth')
                check(row['message_create_time']==(None if msg is None else msg.get('create_time')),'source message time')
                check(row['message_update_time']==(None if msg is None else msg.get('update_time')),'source update time')
                check(row['content_type']==(None if not isinstance(content,dict) else content.get('content_type')),'content type')
                if text is None:check(row['legacy_text_ref'] is None,'fake text ref')
                else:
                    revision=ident({'conversation_id':row['conversation_id'],'message_id':msg['id'],'node_id':row['node_id'],
                                    'parent_node_id':node.get('parent'),'role':msg['author']['role'],
                                    'content_type':content.get('content_type'),'text':text})
                    item_id=ident({'namespace':case['namespace'],'source_key':f'chatgpt/{row["conversation_id"]}/{msg["id"]}',
                                   'revision_sha256':revision,'extractor':'chatgpt-export.v1'})
                    check(row['legacy_text_ref']=={'item_id':item_id,'revision_sha256':revision,'text':text,'text_sha256':sha(text.encode())},'legacy text identity')
                node_rows.append(dict(row,case_id=cid))
            expected_attach=[]
            for conv in parsed:
                for ni,node in sorted(conv['mapping'].items()):
                    msg=node.get('message');content=msg.get('content') if isinstance(msg,dict) else None
                    parts=content.get('parts',[]) if isinstance(content,dict) else []
                    if not isinstance(parts,list):continue
                    for pi,part in enumerate(parts):
                        if isinstance(part,str):continue
                        val=part if isinstance(part,dict) else {};kind=val.get('content_type','unknown');pointer=val.get('asset_pointer')
                        state='UNSUPPORTED'
                        if kind in ['image_asset_pointer','audio_asset_pointer','file_asset_pointer']:state='PRESENT' if isinstance(pointer,str) and pointer else 'MISSING'
                        if state!='PRESENT':pointer=None
                        expected_attach.append({'conversation_id':conv['id'],'message_id':msg['id'],'part_index':pi,'content_type':kind,
                            'state':state,'asset_pointer':pointer,'bytes_present':False,'network_fetch_performed':False,'retrieval_allowed':False,
                            'json_pointer':f'/{parsed.index(conv)}/mapping/{ni}/message/content/parts/{pi}'})
            check(payload['attachments']==expected_attach,'attachment coverage/truth '+cid)
            attachment_rows.extend(dict(row,case_id=cid) for row in payload['attachments'])
            gaps=expected_gaps(parsed)
            check(sorted(payload['topology_gaps'],key=compact)==gaps,'topology gaps '+cid)
            check(payload['disposition']==('PARTIAL_TOPOLOGY' if gaps else 'LOCAL_NODES_ACCOUNTED'),'topology completeness '+cid)
            for untouched in case['out_of_scope_unchanged']:check(untouched not in selected,'false selection label')
        counts={'nodes':len(payload['nodes']),'text_nodes':sum(r['state']=='TEXT_EXTRACTED' for r in payload['nodes']),
                'attachments':len(payload['attachments']),'topology_gaps':len(payload['topology_gaps'])}
        check(counts==case['counts'],'counts '+cid)
        wanted={'new_raw_blobs':int(sha(raw) not in blobs),'new_source_versions':int(sid not in versions),
                'new_extractions':int(eid not in extractions),'new_origins':int(oid not in origins)}
        check(wanted==case['expected_new_records'],'dedup counters '+cid)
        if eid in payloads:check(payloads[eid]==encoded,'same extraction identity different payload '+cid)
        blobs[sha(raw)]=raw;versions[sid]=case;extractions[eid]=cap;origins[oid]=case;payloads[eid]=encoded;ledgers[cid]=payload
        with db:
            db.execute('INSERT OR IGNORE INTO import_raw_blobs VALUES(?,?,?)',(sha(raw),len(raw),raw))
            db.execute('INSERT OR IGNORE INTO import_source_versions VALUES(?,?,?,?,?)',(case['namespace'],case['source_key'],sha(raw),sid,cap['captured_at']))
            db.execute('INSERT OR IGNORE INTO import_origins VALUES(?,?,?,?,?,?,?)',(oid,case['namespace'],case['source_key'],sha(raw),case['origin_locator'],case['policy']['scope_policy'],cap['captured_at']))
            db.execute('INSERT OR IGNORE INTO import_extractions VALUES(?,?,?,?,?,?,?,?,?)',(case['namespace'],case['source_key'],sha(raw),key,eid,sha(encoded),encoded,payload['disposition'],cap['captured_at']))
            db.execute('INSERT INTO import_source_heads VALUES(?,?,?,?,?) ON CONFLICT(namespace,source_key) DO UPDATE SET raw_sha256=excluded.raw_sha256,extractor_key=excluded.extractor_key,last_observed_at=excluded.last_observed_at',
                       (case['namespace'],case['source_key'],sha(raw),key,cap['captured_at']))
        stored=db.execute('SELECT raw FROM import_raw_blobs WHERE sha256=?',(sha(raw),)).fetchone()[0]
        check(stored==raw and sha(stored)==cap['raw_sha256'],'SQLite original roundtrip')
    for filename,expected in [('NODES.jsonl',node_rows),('ATTACHMENTS.jsonl',attachment_rows)]:
        rows=[json.loads(line) for line in (fixture/filename).read_text().splitlines()]
        check(rows==expected,'flat ledger '+filename)
    oracle=data['manual_oracle']
    for cid in ['F01','F07','F08','F18']:
        p=ledgers[cid];label=oracle[cid]
        check(len(p['nodes'])==label['nodes'],'manual node oracle')
        check(sum(r['state']=='TEXT_EXTRACTED' for r in p['nodes'])==label['text_nodes'],'manual text oracle')
    check(sorted(ledgers['F08']['topology_gaps'],key=compact)==sorted(oracle['F08']['topology_gaps'],key=compact),'manual gaps oracle')
    def items(cid):return {(r['conversation_id'],r['node_id']):r['legacy_text_ref']['item_id'] for r in ledgers[cid]['nodes'] if r['legacy_text_ref']}
    for a,b in oracle['same_legacy_item_ids']:check(items(a)==items(b),'text identity preserved '+a+b)
    a,b,conv,node=oracle['changed_legacy_item'];check(items(a)[(conv,node)]!=items(b)[(conv,node)],'changed text old item')
    a,b=oracle['same_raw_new_extractor'];check(by_capture[a]['raw_sha256']==by_capture[b]['raw_sha256'] and by_capture[a]['extractor_key']!=by_capture[b]['extractor_key'],'adapter key separation')
    check(db.execute('PRAGMA foreign_key_check').fetchall()==[],'SQLite foreign keys')
    for table,n in [('import_raw_blobs',len(blobs)),('import_source_versions',len(versions)),('import_extractions',len(extractions)),('import_origins',len(origins))]:
        check(db.execute('SELECT count(*) FROM '+table).fetchone()[0]==n,'schema dedup '+table)
    before=db.execute('SELECT count(*) FROM import_raw_blobs').fetchone()[0]
    injected=b'fault-probe';ih=sha(injected)
    try:
        with db:
            db.execute('INSERT INTO import_raw_blobs VALUES(?,?,?)',(ih,len(injected),injected))
            raise RuntimeError('INJECTED_BEFORE_COMMIT')
    except RuntimeError:pass
    check(db.execute('SELECT count(*) FROM import_raw_blobs').fetchone()[0]==before,'prototype rollback')
    failures=[]
    for label,sql,args in [
        ('wrong_blob_length','INSERT INTO import_raw_blobs VALUES(?,?,?)',(ih,999,injected)),
        ('missing_raw_fk','INSERT INTO import_source_versions VALUES(?,?,?,?,?)',('invalid','x','f'*64,'d'*64,1)),
        ('missing_extraction_fk','INSERT INTO import_source_heads VALUES(?,?,?,?,?)',('invalid','x','f'*64,'e'*64,1))]:
        try:
            with db:db.execute(sql,args)
        except sqlite3.IntegrityError:failures.append(label)
        else:raise ValueError('schema accepted '+label)
    links=0
    for path in [root/'INDEX.html',fixture/'INDEX.html']:
        parser=Links();parser.feed(path.read_text())
        for href in parser.hrefs:
            check(not href.startswith(('http:','https:','javascript:','file:','/')),'external/active link')
            resolved=(path.parent/href).resolve();check(resolved.is_relative_to(root.resolve()) and resolved.is_file(),'broken link '+href)
            links+=1
    summary=json.loads((root/'fixtures/GOLDEN_SUMMARY.json').read_text())
    check(summary['unique_captured_blobs']==len(blobs) and summary['source_versions']==len(versions) and summary['extraction_versions']==len(extractions),'summary counts')
    db.close()
    return {'cases':len(cases),'captured_originals':sum(c['original_retained'] for c in captures),'unique_captured_blobs':len(blobs),
            'source_versions':len(versions),'extraction_versions':len(extractions),'origins':len(origins),
            'node_rows':len(node_rows),'attachment_rows':len(attachment_rows),'relative_links':links,
            'manual_oracle':'PASS','schema_experiment':'PASS_PROTOTYPE_ONLY','schema_rejections':failures,
            'prototype_rollback':'PASS','application_runtime':'NOT_RUN'}


if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
    print(json.dumps(verify_fixture(root),ensure_ascii=False,indent=2))
