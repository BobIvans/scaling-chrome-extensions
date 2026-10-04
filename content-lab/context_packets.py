"""Immutable, provider-neutral task/result packets and redacted projections.

Sources/parts are SQLite rows and JSONL export streams, so frame/page budgets
never silently truncate the selected corpus. An imported result is data only.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time

import context_library as lib
from automation_core import identifier, strict_int


def db_for(store):
    db=lib.db_for(store)
    db.executescript('''
      CREATE TABLE IF NOT EXISTS context_selections(
        namespace TEXT, id TEXT, parent TEXT, PRIMARY KEY(namespace,id));
      CREATE TABLE IF NOT EXISTS context_selection_rows(
        namespace TEXT, selection_id TEXT, ordinal INTEGER, ref TEXT, reason TEXT,
        PRIMARY KEY(namespace,selection_id,ordinal));
      CREATE TABLE IF NOT EXISTS context_packet_sources(
        namespace TEXT, packet_id TEXT, ordinal INTEGER, ref TEXT, reason TEXT,
        PRIMARY KEY(namespace,packet_id,ordinal));
    ''')
    return db


def row_digest(cursor, fields):
    h=hashlib.sha256()
    for row in cursor:
        raw=lib.encoded([row[k] for k in fields]);h.update(len(raw).to_bytes(8,'big'));h.update(raw)
    return h.hexdigest()


def put_document(db,namespace,kind,payload,*,parent=None,document_id=None):
    raw=lib.encoded(payload).decode();h=lib.sha(raw.encode())
    docid=document_id or lib.digest([namespace,kind,parent,h])
    old=db.execute('SELECT payload_hash FROM context_packets WHERE namespace=? AND id=?',(namespace,docid)).fetchone()
    if old and old[0]!=h:raise ValueError('IMMUTABLE_DOCUMENT_CONFLICT')
    db.execute('INSERT OR IGNORE INTO context_packets VALUES (?,?,?,?,?,?,?)',(namespace,docid,kind,parent,raw,h,time.time()))
    return docid


def load_document(db,namespace,docid,kind=None):
    lib.hash_id(docid)
    row=db.execute('SELECT * FROM context_packets WHERE namespace=? AND id=?',(namespace,docid)).fetchone()
    if not row:raise ValueError('DOCUMENT_OUTSIDE_SCOPE')
    if kind is not None and row['kind']!=kind:raise ValueError('DOCUMENT_KIND')
    if lib.sha(row['payload'].encode())!=row['payload_hash']:raise ValueError('DOCUMENT_CORRUPT')
    return row,json.loads(row['payload'])


def create_selection(store,namespace,rows,*,parent=None):
    identifier(namespace)
    if not isinstance(rows,list):raise ValueError('SELECTION_ROWS_REQUIRED')
    db=db_for(store)
    try:
        db.execute('BEGIN IMMEDIATE')
        for r in rows:
            lib.exact(r,{'source_ref','reason'})
            lib.validate_ref(db,namespace,r['source_ref']);lib.text(r['reason'],2000)
        selection_id=lib.digest(['selection-v1',namespace,parent,rows])
        if db.execute('SELECT 1 FROM context_selections WHERE namespace=? AND id=?',(namespace,selection_id)).fetchone():
            return selection_status(db,namespace,selection_id)
        if parent:
            lib.hash_id(parent)
            if not db.execute('SELECT 1 FROM context_selections WHERE namespace=? AND id=?',(namespace,parent)).fetchone():
                raise ValueError('SELECTION_OUTSIDE_SCOPE')
        db.execute('INSERT INTO context_selections VALUES (?,?,?)',(namespace,selection_id,parent))
        if parent:
            db.execute('INSERT INTO context_selection_rows SELECT namespace,?,ordinal,ref,reason FROM context_selection_rows WHERE namespace=? AND selection_id=?',(selection_id,namespace,parent))
        ordinal=db.execute('SELECT count(*) FROM context_selection_rows WHERE namespace=? AND selection_id=?',(namespace,selection_id)).fetchone()[0]
        for r in rows:
            raw=lib.encoded(r['source_ref']).decode()
            if not db.execute('SELECT 1 FROM context_selection_rows WHERE namespace=? AND selection_id=? AND ref=?',(namespace,selection_id,raw)).fetchone():
                db.execute('INSERT INTO context_selection_rows VALUES (?,?,?,?,?)',(namespace,selection_id,ordinal,raw,r['reason']));ordinal+=1
        db.commit()
        return selection_status(db,namespace,selection_id)
    finally:db.close()


def selection_status(db,namespace,sid):
    return {'selection_id':sid,'count':db.execute('SELECT count(*) FROM context_selection_rows WHERE namespace=? AND selection_id=?',(namespace,sid)).fetchone()[0],'immutable':True}


def remove_selected_range(store,namespace,parent,ordinal):
    strict_int(ordinal,0,lib.MAX_INT)
    db=db_for(store)
    try:
        db.execute('BEGIN IMMEDIATE');status=selection_status(db,namespace,parent)
        if ordinal>=status['count']:raise ValueError('SELECTION_ORDINAL')
        sid=lib.digest(['selection-remove-v1',namespace,parent,ordinal])
        if not db.execute('SELECT 1 FROM context_selections WHERE namespace=? AND id=?',(namespace,sid)).fetchone():
            db.execute('INSERT INTO context_selections VALUES (?,?,?)',(namespace,sid,parent))
            db.execute('''INSERT INTO context_selection_rows SELECT namespace,?,
              CASE WHEN ordinal>? THEN ordinal-1 ELSE ordinal END,ref,reason
              FROM context_selection_rows WHERE namespace=? AND selection_id=? AND ordinal<>?''',(sid,ordinal,namespace,parent,ordinal))
        db.commit();return selection_status(db,namespace,sid)
    finally:db.close()


def adopt_item_ref(store,namespace,item_id):
    """Existing imports are exposed as explicitly derived UTF-8, never raw bytes."""
    lib.hash_id(item_id)
    with lib.view(store) as db:
        row=db.execute('SELECT payload FROM items WHERE id=?',(item_id,)).fetchone()
        if row is None:raise ValueError('MISSING_SOURCE')
        item=json.loads(row[0])
        if item.get('namespace')!=namespace:raise ValueError('OUT_OF_SCOPE')
        raw=item['text'].encode()
        return {'namespace':namespace,'source_key':item['source_key'],'revision':item_id,
                'sha256':lib.sha(raw),'start':0,'end':len(raw),'offset_space':'ITEM_TEXT_UTF8'}


def compile_task_document(store,namespace,selection_id,goal,criteria,operation_id,*,part_bytes=4096,progress=None):
    identifier(namespace);lib.text(goal)
    if not isinstance(criteria,list) or not criteria or any(not isinstance(c,str) or not c for c in criteria):
        raise ValueError('CRITERIA_REQUIRED')
    if len(lib.encoded(criteria))>lib.PAGE_BYTES:raise ValueError('CRITERIA_FRAME_LIMIT')
    strict_int(part_bytes,1,lib.PART_BYTES)
    inputs={'selection_id':selection_id,'goal':goal,'criteria':criteria,'part_bytes':part_bytes}
    db=db_for(store)
    try:
        db.execute('BEGIN IMMEDIATE')
        existing=db.execute('SELECT * FROM context_intents WHERE namespace=? AND operation_id=?',(namespace,operation_id)).fetchone()
        if existing and (existing['input_digest']!=lib.digest(['packet',inputs]) or existing['kind']!='packet'):
            raise ValueError('IDEMPOTENCY_CONFLICT')
        if existing and existing['state']=='COMPLETED':return json.loads(existing['result'])
        if not existing:lib.begin_intent(db,namespace,operation_id,'packet',inputs)
        lib.ensure_running(db,operation_id,namespace)
        if not db.execute('SELECT 1 FROM context_selections WHERE namespace=? AND id=?',(namespace,selection_id)).fetchone():
            raise ValueError('SELECTION_OUTSIDE_SCOPE')
        count=selection_status(db,namespace,selection_id)['count']
        if not count:raise ValueError('EMPTY_SELECTION')
        packet_id=lib.digest(['packet-v1',namespace,operation_id,inputs])
        source_hash=row_digest(db.execute('SELECT ref,reason FROM context_selection_rows WHERE namespace=? AND selection_id=? ORDER BY ordinal',(namespace,selection_id)),('ref','reason'))
        db.execute('INSERT OR IGNORE INTO context_packet_sources SELECT namespace,?,ordinal,ref,reason FROM context_selection_rows WHERE namespace=? AND selection_id=?',(packet_id,namespace,selection_id))
        db.commit()
        # Construction transactions are bounded. Immutable rows are staged until
        # the final packet document exists; STOP can acquire the same DB owner.
        part_ordinal=0;total=0
        for source in db.execute('SELECT * FROM context_packet_sources WHERE namespace=? AND packet_id=? ORDER BY ordinal',(namespace,packet_id)):
            ref=json.loads(source['ref'])
            for offset,raw in lib.iter_span(db,namespace,ref,chunk_bytes=part_bytes):
                if progress:progress()
                db.execute('BEGIN IMMEDIATE');lib.ensure_running(db,operation_id,namespace)
                part_ref={**ref,'start':offset,'end':offset+len(raw)}
                prior=db.execute('SELECT source_ref,sha256 FROM context_packet_parts WHERE namespace=? AND packet_id=? AND ordinal=?',(namespace,packet_id,part_ordinal)).fetchone()
                if prior and (prior['sha256']!=lib.sha(raw) or prior['source_ref']!=lib.encoded(part_ref).decode()):raise ValueError('SOURCE_DRIFT')
                db.execute('INSERT OR IGNORE INTO context_packet_parts VALUES (?,?,?,?,?,?)',(namespace,packet_id,part_ordinal,lib.encoded(part_ref).decode(),sqlite3.Binary(raw),lib.sha(raw)))
                db.commit();part_ordinal+=1;total+=len(raw)
        db.execute('BEGIN IMMEDIATE');lib.ensure_running(db,operation_id,namespace)
        for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=?',(namespace,packet_id)):
            lib.validate_ref(db,namespace,json.loads(r[0]))
        parts_hash=row_digest(db.execute('SELECT ordinal,source_ref,sha256 FROM context_packet_parts WHERE namespace=? AND packet_id=? ORDER BY ordinal',(namespace,packet_id)),('ordinal','source_ref','sha256'))
        payload={'schema':'occ.context-packet.v1','serialization':'OCC_PYTHON_JSON_V1',
                 'namespace':namespace,'goal':goal,'goal_revision':lib.digest(goal),
                 'criteria':criteria,'criteria_revision':lib.digest(criteria),'selection_id':selection_id,
                 'source_manifest_digest':source_hash,'part_manifest_digest':parts_hash,
                 'source_count':count,'part_count':part_ordinal,'bytes':total,
                 'coverage':'ALL_SELECTED_RANGES','archive_coverage':'SELECTED_SCOPE_ONLY',
                 'supplied':'LOCAL_PREPARED','delivered':'NOT_PERFORMED','model_read':'UNKNOWN',
                 'criterion_verified':False,'dispatch_allowed':False}
        put_document(db,namespace,'PACKET',payload,document_id=packet_id)
        result={'packet_id':packet_id,'packet_digest':lib.digest(payload),'source_count':count,'part_count':part_ordinal,'bytes':total,'state':'PREPARED'}
        lib.finish_intent(db,namespace,operation_id,result);db.commit();return result
    except BaseException:
        db.rollback()
        # Reconciliation can see persisted intent; no complete document exists.
        raise
    finally:db.close()


def metadata_page(store,namespace,docid,*,kind='PARTS',offset=0,limit=20):
    strict_int(offset,0,lib.MAX_INT);strict_int(limit,1,100)
    with lib.view(store) as db:
        row,meta=load_document(db,namespace,docid)
        if kind=='INFO':return {'document_id':docid,'kind':row['kind'],'digest':row['payload_hash'],'metadata':meta}
        if kind=='SOURCES':
            # Projections inherit only sources admitted when built.
            sid=meta.get('packet_id',docid)
            cursor=db.execute('SELECT ordinal,ref,reason FROM context_packet_sources WHERE namespace=? AND packet_id=? ORDER BY ordinal LIMIT ? OFFSET ?',(namespace,sid,limit+1,offset))
            records=[{'ordinal':r['ordinal'],'source_ref':json.loads(r['ref']),'why':r['reason']} for r in cursor]
        elif kind=='PARTS':
            cursor=db.execute('SELECT ordinal,source_ref,sha256,length(raw) AS bytes FROM context_packet_parts WHERE namespace=? AND packet_id=? ORDER BY ordinal LIMIT ? OFFSET ?',(namespace,docid,limit+1,offset))
            records=[{'ordinal':r['ordinal'],'source_ref':json.loads(r['source_ref']),'sha256':r['sha256'],'bytes':r['bytes']} for r in cursor]
        else:raise ValueError('CONTEXT_PAGE_KIND')
        rows=[]
        for r in records[:limit]:
            if len(lib.encoded(rows+[r]))>lib.PAGE_BYTES:
                if not rows:raise ValueError('ROW_PAGE_LIMIT')
                break
            rows.append(r)
        return {'document_id':docid,'digest':row['payload_hash'],'rows':rows,'offset':offset,
                'next_offset':offset+len(rows) if len(records)>len(rows) else None}


def read_document_part(store,namespace,docid,ordinal):
    strict_int(ordinal,0,lib.MAX_INT)
    with lib.view(store) as db:
        load_document(db,namespace,docid)
        r=db.execute('SELECT * FROM context_packet_parts WHERE namespace=? AND packet_id=? AND ordinal=?',(namespace,docid,ordinal)).fetchone()
        if r is None:raise ValueError('PART_NOT_FOUND')
        if lib.sha(r['raw'])!=r['sha256']:raise ValueError('PART_CORRUPT')
        return {'ordinal':ordinal,'source_ref':json.loads(r['source_ref']),'sha256':r['sha256'],
                'base64':base64.b64encode(r['raw']).decode(),'bytes':len(r['raw']),
                'text':r['raw'].decode('utf-8',errors='replace')}


def create_share_projection(store,namespace,packet_id,profile,operation_id,*,redactions=None,progress=None):
    lib.exact(profile,{'destination_id','destination_revision','policy_revision','source_keys','protected_literals'})
    for k in ('destination_id','destination_revision','policy_revision'):lib.text(profile[k],200)
    if not isinstance(profile['source_keys'],list) or not all(isinstance(k,str) for k in profile['source_keys']):raise ValueError('SHARE_SCOPE_REQUIRED')
    if not isinstance(profile['protected_literals'],list):raise ValueError('SHARE_POLICY_REQUIRED')
    for literal in profile['protected_literals']:lib.text(literal,1024)
    redactions=redactions or []
    for r in redactions:
        lib.exact(r,{'revision','start','end'});lib.hash_id(r['revision'])
        strict_int(r['start'],0,lib.MAX_INT);strict_int(r['end'],r['start']+1,lib.MAX_INT)
    db=db_for(store)
    try:
        db.execute('BEGIN IMMEDIATE')
        projection_input=[packet_id,profile,redactions]
        existing=db.execute('SELECT * FROM context_intents WHERE namespace=? AND operation_id=?',(namespace,operation_id)).fetchone()
        if existing and (existing['input_digest']!=lib.digest(['projection',projection_input]) or existing['kind']!='projection'):raise ValueError('IDEMPOTENCY_CONFLICT')
        if existing and existing['state']=='COMPLETED':return json.loads(existing['result'])
        if not existing:lib.begin_intent(db,namespace,operation_id,'projection',projection_input)
        _row,packet=load_document(db,namespace,packet_id,'PACKET');lib.ensure_running(db,operation_id,namespace)
        pid=lib.digest(['projection-v1',namespace,operation_id,packet_id,profile,redactions])
        # An export profile cannot invent permission: caller is the trusted host
        # and profile/destination comes from operator configuration, not AI data.
        for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=?',(namespace,packet_id)):
            ref=json.loads(r[0]);lib.validate_ref(db,namespace,ref)
            if ref['source_key'] not in profile['source_keys']:raise ValueError('SHARE_SOURCE_OUTSIDE_SCOPE')
        db.commit()
        intervals=list(redactions)
        for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=? ORDER BY ordinal',(namespace,packet_id)):
            ref=json.loads(r[0]);carry=b'';carry_start=ref['start']
            maxlit=max((len(s.encode()) for s in profile['protected_literals']),default=1)
            for start,raw in lib.iter_span(db,namespace,ref):
                data=carry+raw
                for secret in profile['protected_literals']:
                    literal=secret.encode();at=0
                    while (at:=data.find(literal,at))>=0:
                        intervals.append({'revision':ref['revision'],'start':carry_start+at,'end':carry_start+at+len(literal)});at+=len(literal)
                keep=min(len(data),maxlit-1);carry=data[-keep:] if keep else b'';carry_start=start+len(raw)-keep
        total=0;count=0
        for r in db.execute('SELECT * FROM context_packet_parts WHERE namespace=? AND packet_id=? ORDER BY ordinal',(namespace,packet_id)):
            if progress:progress()
            ref=json.loads(r['source_ref']);raw=bytearray(r['raw'])
            if lib.sha(bytes(raw))!=r['sha256']:raise ValueError('PART_CORRUPT')
            for red in intervals:
                if red['revision']!=ref['revision']:continue
                lo=max(red['start'],ref['start']);hi=min(red['end'],ref['end'])
                if hi>lo:raw[lo-ref['start']:hi-ref['start']]=b'*'*(hi-lo)
            raw=bytes(raw)
            db.execute('BEGIN IMMEDIATE');lib.ensure_running(db,operation_id,namespace)
            prior=db.execute('SELECT sha256 FROM context_packet_parts WHERE namespace=? AND packet_id=? AND ordinal=?',(namespace,pid,r['ordinal'])).fetchone()
            if prior and prior[0]!=lib.sha(raw):raise ValueError('PROJECTION_DRIFT')
            db.execute('INSERT OR IGNORE INTO context_packet_parts VALUES (?,?,?,?,?,?)',(namespace,pid,r['ordinal'],r['source_ref'],sqlite3.Binary(raw),lib.sha(raw)))
            db.commit();count+=1;total+=len(raw)
        db.execute('BEGIN IMMEDIATE');lib.ensure_running(db,operation_id,namespace)
        parts_hash=row_digest(db.execute('SELECT ordinal,source_ref,sha256 FROM context_packet_parts WHERE namespace=? AND packet_id=? ORDER BY ordinal',(namespace,pid)),('ordinal','source_ref','sha256'))
        # Secret literals and the local redaction mapping are absent from metadata.
        payload={'schema':'occ.share-projection.v1','namespace':namespace,'packet_id':packet_id,
                 'packet_digest':lib.digest(packet),'destination_id':profile['destination_id'],
                 'destination_revision':profile['destination_revision'],'policy_revision':profile['policy_revision'],
                 'profile_digest':lib.digest(profile),'part_manifest_digest':parts_hash,'part_count':count,'bytes':total,
                 'redaction_count':len(intervals),'transformation':'BYTE_MASKING_PRESERVES_RANGE_LENGTH',
                 'provider_limits':'UNKNOWN','secret_scan_guarantee':False,'delivery':'NOT_PERFORMED'}
        put_document(db,namespace,'PROJECTION',payload,parent=packet_id,document_id=pid)
        result={'projection_id':pid,'projection_digest':lib.digest(payload),'parts':count,'bytes':total,'state':'READY_LOCAL_EXPORT'}
        lib.finish_intent(db,namespace,operation_id,result);db.commit();return result
    finally:db.close()


def export_projection(store,namespace,projection_id,output,profile,*,progress=None):
    output=Path(output).absolute()
    if any(p.is_symlink() for p in (output,*output.parents)):raise ValueError('EXPORT_LINK_PATH')
    output.parent.mkdir(parents=True,exist_ok=True)
    db=db_for(store)
    try:
        _row,meta=load_document(db,namespace,projection_id,'PROJECTION')
        if lib.digest(profile)!=meta['profile_digest']:raise ValueError('SHARE_PROFILE_CHANGED')
        packetid=meta['packet_id'];_pr,packet=load_document(db,namespace,packetid,'PACKET')
        for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=?',(namespace,packetid)):
            lib.validate_ref(db,namespace,json.loads(r[0]))
        if output.exists():
            receipt=verify_export(output,expected_digest=lib.digest(meta))
            return {**receipt,'reused':True}
        stage=Path(tempfile.mkdtemp(prefix='.context-export-',dir=output.parent))
        try:
            (stage/'parts').mkdir()
            manifest=[]
            def write(name,raw):
                p=stage/name
                with p.open('xb') as stream:
                    stream.write(raw);stream.flush();os.fsync(stream.fileno())
                manifest.append({'path':name,'sha256':lib.sha(raw),'bytes':len(raw)})
            def safe(value):
                if isinstance(value,str):
                    for secret in profile['protected_literals']:value=value.replace(secret,'[REDACTED]')
                    return value
                if isinstance(value,list):return [safe(x) for x in value]
                if isinstance(value,dict):return {k:safe(v) for k,v in value.items()}
                return value
            write('TASK.json',lib.encoded(safe(packet)))
            write('PROJECTION.json',lib.encoded(safe(meta)))
            # Streaming index avoids a complete corpus-sized array allocation.
            for filename,query,fields in [
                ('SOURCES.jsonl','SELECT ordinal,ref,reason FROM context_packet_sources WHERE namespace=? AND packet_id=? ORDER BY ordinal',('ordinal','ref','reason')),
                ('PARTS_INDEX.jsonl','SELECT ordinal,source_ref,sha256 FROM context_packet_parts WHERE namespace=? AND packet_id=? ORDER BY ordinal',('ordinal','source_ref','sha256'))]:
                h=hashlib.sha256();size=0
                with (stage/filename).open('xb') as stream:
                    for row in db.execute(query,(namespace,packetid if filename=='SOURCES.jsonl' else projection_id)):
                        if progress:progress()
                        raw=lib.encoded(safe({k:row[k] for k in fields}))+b'\n';stream.write(raw);h.update(raw);size+=len(raw)
                    stream.flush();os.fsync(stream.fileno())
                manifest.append({'path':filename,'sha256':h.hexdigest(),'bytes':size})
            for row in db.execute('SELECT ordinal,raw,sha256 FROM context_packet_parts WHERE namespace=? AND packet_id=? ORDER BY ordinal',(namespace,projection_id)):
                if progress:progress()
                if lib.sha(row['raw'])!=row['sha256']:raise ValueError('PART_CORRUPT')
                write(f"parts/{row['ordinal']:08}.bin",row['raw'])
            write('INDEX.html',b'<!doctype html><meta charset="utf-8"><title>Context packet</title><h1>Offline context packet</h1><p>Exact part/source mappings: <a href="SOURCES.jsonl">sources</a> and <a href="PARTS_INDEX.jsonl">parts</a>. Delivery/read/criterion verification are independent.</p>')
            with (stage/'MANIFEST.json').open('xb') as stream:
                stream.write(lib.encoded({'schema':'occ.context-export.v1','projection_digest':lib.digest(meta),'files':manifest}));stream.flush();os.fsync(stream.fileno())
            verify_export(stage,expected_digest=lib.digest(meta))
            # Guard publication against late stop/delete/profile changes.
            if progress:progress()
            for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=?',(namespace,packetid)):
                lib.validate_ref(db,namespace,json.loads(r[0]))
            if output.exists():raise ValueError('OUTPUT_EXISTS')
            os.rename(stage,output)
            return {**verify_export(output,expected_digest=lib.digest(meta)),'reused':False}
        finally:
            if stage.exists():shutil.rmtree(stage)
    finally:db.close()


def verify_export(output,*,expected_digest=None):
    output=Path(output)
    if any(p.is_symlink() for p in (output,*output.parents)) or (output/'MANIFEST.json').is_symlink():raise ValueError('EXPORT_PATH')
    manifest=lib.strict_json((output/'MANIFEST.json').read_bytes(),16_000_000)
    lib.exact(manifest,{'schema','projection_digest','files'})
    if manifest['schema']!='occ.context-export.v1':raise ValueError('EXPORT_SCHEMA')
    if expected_digest and manifest['projection_digest']!=expected_digest:raise ValueError('EXPORT_DIGEST')
    seen=set()
    for r in manifest['files']:
        lib.exact(r,{'path','sha256','bytes'});relative=Path(r['path'])
        if (relative.is_absolute() or '..' in relative.parts or '\\' in r['path']
                or r['path'] in seen):raise ValueError('EXPORT_PATH')
        seen.add(r['path']);p=output/relative
        if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('EXPORT_PATH')
        h=hashlib.sha256();size=0
        with p.open('rb') as stream:
            for raw in iter(lambda:stream.read(64*1024),b''):h.update(raw);size+=len(raw)
        if h.hexdigest()!=r['sha256'] or size!=r['bytes']:raise ValueError('EXPORT_CORRUPT')
    if {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} != seen|{'MANIFEST.json'}:raise ValueError('EXPORT_UNTRACKED_FILE')
    return {'state':'EXPORTED_LOCAL','projection_digest':manifest['projection_digest'],
            'files':len(seen),'delivery':'NOT_PERFORMED','model_read':'UNKNOWN','criterion_verified':False}


def need_context(store,namespace,request):
    lib.exact(request,{'request_id','packet_id','packet_digest','criteria_revision','criterion_id','source_ref','reason'})
    identifier(request['request_id']);lib.text(request['reason']);lib.text(request['criterion_id'],200)
    db=db_for(store)
    try:
        _row,packet=load_document(db,namespace,request['packet_id'],'PACKET')
        if request['packet_digest']!=lib.digest(packet) or request['criteria_revision']!=packet['criteria_revision']:
            raise ValueError('STALE_BINDING')
        if request['criterion_id'] not in packet['criteria']:raise ValueError('NEED_CONTEXT_CRITERION')
        ref=request['source_ref'];lib.validate_ref(db,namespace,ref)
        # Only an identity present in the manifest grants a bounded range read;
        # the capture itself remains immutable even outside the initial part.
        allowed=False
        for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=?',(namespace,request['packet_id'])):
            known=json.loads(r[0])
            if all(known[k]==ref[k] for k in ('namespace','source_key','revision','sha256','offset_space')):
                allowed=True;break
        if not allowed:raise ValueError('NEED_CONTEXT_OUTSIDE_MANIFEST')
        if ref['end']-ref['start']>lib.PART_BYTES:raise ValueError('RANGE_PAGE_REQUIRED')
        response=lib.read_span(store,namespace,ref)
        # Read resolution has no send or dispatch effect. Key binds request bytes.
        delta={'schema':'occ.context-delta.v1','request_digest':lib.digest(request),
               'packet_id':request['packet_id'],'response':response,'delivery':'NOT_PERFORMED'}
        db.execute('BEGIN IMMEDIATE')
        old=lib.begin_intent(db,namespace,request['request_id'],'need-context',request)
        if old is not None:return old
        deltaid=put_document(db,namespace,'DELTA',delta,parent=request['packet_id'])
        result={'delta_id':deltaid,**delta};lib.finish_intent(db,namespace,request['request_id'],result);db.commit();return result
    finally:db.close()


def import_result(store,namespace,result_id,raw):
    identifier(result_id)
    if not isinstance(raw,bytes) or len(raw)>128_000:raise ValueError('CONTEXT_FRAME_LIMIT')
    try:value=lib.strict_json(raw,128_000)
    except (ValueError,UnicodeError):value=None
    db=db_for(store)
    try:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT * FROM context_claims WHERE namespace=? AND result_id=?',(namespace,result_id)).fetchone()
        if old:
            if old['payload_hash']!=lib.sha(raw):raise ValueError('RESULT_ID_CONFLICT')
            return {'result_id':result_id,'state':old['state'],'reused':True,'criterion_verified':False}
        state='UNBOUND';packet_id=None
        try:
            lib.exact(value,{'schema','packet_id','packet_digest','criteria_revision','claims','artifacts','gaps'})
            if value['schema']!='occ.context-result.v1':raise ValueError('RESULT_SCHEMA')
            packet_id=value['packet_id'];_row,packet=load_document(db,namespace,packet_id,'PACKET')
            if value['packet_digest']!=lib.digest(packet) or value['criteria_revision']!=packet['criteria_revision']:
                state='STALE'
            else:
                if not isinstance(value['claims'],list) or not isinstance(value['artifacts'],list) or not isinstance(value['gaps'],list):raise ValueError('RESULT_SCHEMA')
                for claim in value['claims']:
                    lib.exact(claim,{'criterion','statement','citations'})
                    if claim['criterion'] not in packet['criteria']:raise ValueError('RESULT_CRITERION')
                    lib.text(claim['statement'])
                    if not isinstance(claim['citations'],list):raise ValueError('RESULT_CITATIONS')
                    for ref in claim['citations']:
                        lib.validate_ref(db,namespace,ref)
                        if not any(all(json.loads(r[0])[k]==ref[k] for k in ('namespace','revision','source_key','sha256','offset_space')) and json.loads(r[0])['start']<=ref['start']<=ref['end']<=json.loads(r[0])['end'] for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=?',(namespace,packet_id))):
                            raise ValueError('RESULT_CITATION_OUTSIDE_MANIFEST')
                for artifact in value['artifacts']:
                    lib.exact(artifact,{'name','sha256'});lib.text(artifact['name'],1000);lib.hash_id(artifact['sha256'])
                state='PROPOSAL_ONLY'
                for r in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=? AND packet_id=?',(namespace,packet_id)):
                    ref=json.loads(r[0])
                    if ref['offset_space']=='RAW_BYTES':
                        head=db.execute('SELECT revision FROM context_source_heads WHERE namespace=? AND source_key=?',(namespace,ref['source_key'])).fetchone()
                        if not head or head[0]!=ref['revision']:state='STALE'
        except (ValueError,KeyError,TypeError):
            state='UNBOUND'
        # Raw input remains attributable AI data; no grants, executable or DONE.
        db.execute('INSERT INTO context_claims VALUES (?,?,?,?,?,?)',(namespace,result_id,packet_id,lib.encoded({'raw_base64':base64.b64encode(raw).decode(),'authority':'AI_CLAIM'}).decode(),lib.sha(raw),state))
        lib.record_event(db,namespace,'AI_CLAIM_IMPORTED',{'result_id':result_id,'raw_sha256':lib.sha(raw),'state':state})
        db.commit()
        return {'result_id':result_id,'state':state,'reused':False,'evidence_kind':'AI_CLAIM','criterion_verified':False,'dispatch_allowed':False}
    finally:db.close()
