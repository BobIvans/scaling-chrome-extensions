"""Consistent SQLite snapshots, isolated restore and portable offline sync.

Current raw import/repo/context bytes are SQLite BLOBs, not an external CAS.
Receipt JSON files, FTS and indexes are rebuildable. Source paths, worktrees,
credential storage and operator policies are intentionally not copied.
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
import context_packets as packets

BACKUP_SCHEMA='occ.context-backup.v1'
SYNC_TABLES={
    'context_sources':('namespace','source_key','revision','raw_hash','bytes','kind','observed','complete'),
    'context_raw_parts':('revision','ordinal','start','end','sha256','raw','item_id'),
    'context_source_heads':('namespace','source_key','revision'),
    'context_events':('namespace','event_id','kind','payload','payload_hash','observed'),
    'context_tombstones':('namespace','source_key','epoch','event_id'),
    'context_annotations':('namespace','revision','event_id','payload'),
}


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for raw in iter(lambda:stream.read(1024*1024),b''):h.update(raw)
    return h.hexdigest()


def regular_tree(path):
    path=Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('RECOVERY_LINK_PATH')
    return path


def ro_database(path):
    path=regular_tree(path)
    if not path.is_file():raise ValueError('BACKUP_DATABASE_MISSING')
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=1);db.row_factory=sqlite3.Row
    return db


def verify_database(path,*,progress=None,_connection=None):
    db=ro_database(path) if _connection is None else _connection
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('BACKUP_DB_CORRUPT')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'items','content_fts','sync_heads'}<=tables:raise ValueError('BACKUP_OWNER_SCHEMA')
        if 'context_schema' in tables and [r[0] for r in db.execute('SELECT version FROM context_schema')]!=[1]:raise ValueError('UNSUPPORTED_CONTEXT_SCHEMA')
        objects=0
        if 'import_raw_blobs' in tables:
            for r in db.execute('SELECT sha256,raw,byte_count FROM import_raw_blobs'):
                if progress:progress()
                if lib.sha(r['raw'])!=r['sha256'] or len(r['raw'])!=r['byte_count']:raise ValueError('BACKUP_BLOB_CORRUPT')
                objects+=1
        if 'context_sources' in tables:
            for source in db.execute('SELECT * FROM context_sources WHERE complete=1'):
                h=hashlib.sha256();cursor=0
                for part in db.execute('SELECT * FROM context_raw_parts WHERE revision=? ORDER BY ordinal',(source['revision'],)):
                    if progress:progress()
                    if part['start']!=cursor or part['end']-cursor!=len(part['raw']) or lib.sha(part['raw'])!=part['sha256']:raise ValueError('BACKUP_BLOB_CORRUPT')
                    h.update(part['raw']);cursor=part['end'];objects+=1
                if cursor!=source['bytes'] or h.hexdigest()!=source['raw_hash']:raise ValueError('BACKUP_SOURCE_CORRUPT')
        if 'context_packet_parts' in tables:
            for r in db.execute('SELECT raw,sha256 FROM context_packet_parts'):
                if progress:progress()
                if lib.sha(r['raw'])!=r['sha256']:raise ValueError('BACKUP_PACKET_CORRUPT')
                objects+=1
        if 'context_packets' in tables:
            for r in db.execute('SELECT payload,payload_hash FROM context_packets'):
                if lib.sha(r['payload'].encode())!=r['payload_hash']:raise ValueError('BACKUP_PACKET_METADATA_CORRUPT')
        if 'repo_chunks' in tables:
            import repo_context as repo
            for r in db.execute('SELECT c.*,e.file_hash,e.size FROM repo_chunks c JOIN repo_entries e ON c.snapshot_id=e.snapshot_id AND c.path=e.path'):
                if progress:progress()
                if (r['byte_end']-r['byte_start']!=len(r['raw']) or r['revision']!=repo.digest([r['logical_id'],r['file_hash'],repo.sha(r['raw']),r['byte_start'],r['byte_end']])):raise ValueError('BACKUP_REPO_BLOB_CORRUPT')
                objects+=1
        logical={}
        for table in ('items','sync_heads','sync_versions','review_sessions','review_results','repo_snapshots','repo_entries','repo_chunks','import_source_versions','import_origins','context_sources','context_raw_parts','context_events','context_annotations','context_tombstones','context_packets','context_claims','jobs','job_events'):
            if table in tables:
                logical[table]=db.execute('SELECT count(*) FROM '+table).fetchone()[0]
        head_digest=packets.row_digest(db.execute('SELECT namespace,source_key,item_id,raw_hash,present FROM sync_heads ORDER BY namespace,source_key'),('namespace','source_key','item_id','raw_hash','present'))
        watermark=db.execute('SELECT coalesce(max(seq),0) FROM job_events').fetchone()[0] if 'job_events' in tables else 0
        return {'integrity':'ok','logical_counts':logical,'head_digest':head_digest,
                'blob_objects_verified':objects,'event_watermark':watermark,
                'source_original_scope':'CAPTURED_DB_BYTES_ONLY','external_originals':'NOT_INCLUDED'}
    finally:
        if _connection is None:db.close()


def snapshot_backup(store,output,*,progress=None):
    store=regular_tree(store);output=regular_tree(output)
    if output.resolve().is_relative_to(store.resolve()) or store.resolve().is_relative_to(output.resolve()):raise ValueError('BACKUP_DESTINATION_OVERLAP')
    if output.exists():return verify_backup(output,progress=progress)
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.context-backup-',dir=output.parent))
    source=lib.read_connection(store)
    target=sqlite3.connect(stage/'content.sqlite3')
    try:
        # Online backup produces a single committed generation. All referenced
        # raw objects and events are in that same database snapshot.
        def tick(_status,_remaining,_total):
            if progress:progress()
        source.execute('BEGIN')
        source.execute('SELECT count(*) FROM sqlite_master').fetchone()
        source.backup(target,pages=64,progress=tick,sleep=0.01)
        target.commit();target.close();target=None
        report=verify_database(stage/'content.sqlite3',progress=progress)
        manifest={'schema':BACKUP_SCHEMA,'database_file':'content.sqlite3',
                  'database_sha256':file_sha(stage/'content.sqlite3'),
                  'database_bytes':(stage/'content.sqlite3').stat().st_size,
                  'verification':report,'encryption':'NONE_EXPLICIT_LOCAL_ARTIFACT',
                  'credential_storage_included':False,'policies_included':False,
                  'external_store_paths_included':False,'dispatch_after_restore':False,
                  'state':'VERIFIED_COMPLETE'}
        (stage/'MANIFEST.json').write_bytes(lib.encoded(manifest))
        verify_backup(stage,progress=progress)
        if progress:progress()
        if output.exists():raise ValueError('BACKUP_OUTPUT_EXISTS')
        os.rename(stage,output)
        return {'state':'VERIFIED_COMPLETE','sha256':manifest['database_sha256'],
                'bytes':manifest['database_bytes'],'verification':report,
                'restore_status':'NOT_RUN','dispatch_allowed':False}
    finally:
        source.close()
        if target is not None:target.close()
        if stage.exists():shutil.rmtree(stage)


def verify_backup(backup,*,progress=None):
    backup=regular_tree(backup)
    manifest=json.loads((backup/'MANIFEST.json').read_text(encoding='utf-8'))
    lib.exact(manifest,{'schema','database_file','database_sha256','database_bytes','verification','encryption','credential_storage_included','policies_included','external_store_paths_included','dispatch_after_restore','state'})
    if (manifest['schema']!=BACKUP_SCHEMA or manifest['database_file']!='content.sqlite3'
            or manifest['state']!='VERIFIED_COMPLETE' or manifest['dispatch_after_restore'] is not False
            or manifest['credential_storage_included'] is not False or manifest['policies_included'] is not False):raise ValueError('BACKUP_SCHEMA')
    path=regular_tree(backup/'content.sqlite3')
    if path.stat().st_size!=manifest['database_bytes'] or file_sha(path)!=manifest['database_sha256']:raise ValueError('BACKUP_HASH_MISMATCH')
    report=verify_database(path,progress=progress)
    if report!=manifest['verification']:raise ValueError('BACKUP_LOGICAL_MISMATCH')
    return {'state':'VERIFIED_COMPLETE','sha256':manifest['database_sha256'],
            'bytes':manifest['database_bytes'],'verification':report,'dispatch_allowed':False}


def restored_state(db):
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'core_control' in tables:db.execute('UPDATE core_control SET stopped=1,epoch=epoch+1 WHERE singleton=1')
    if 'jobs' in tables:
        # History and uncertainty are retained. A backup never restarts a send.
        db.execute("UPDATE jobs SET state=CASE WHEN state='RUNNING' THEN 'NEEDS_RECONCILIATION' WHEN state IN ('QUEUED','RETRY_READY','WAITING_CI') THEN 'BLOCKED' ELSE state END,lease_token=NULL,lease_until=0,cancel_requested=1 WHERE state NOT IN ('SUCCEEDED','FAILED','CANCELLED','BLOCKED')")
    if 'context_qualifications' in tables:db.execute("UPDATE context_qualifications SET state='STALE'")


def restore_to_copy(backup,output,*,current_store=None,recovery_namespace=False,progress=None):
    backup=regular_tree(backup);output=regular_tree(output)
    verified=verify_backup(backup,progress=progress)
    if output.exists():raise ValueError('RESTORE_OUTPUT_EXISTS')
    if current_store is None and recovery_namespace is not True:raise ValueError('CURRENT_DELETION_LEDGER_REQUIRED')
    if current_store:
        current_store=regular_tree(current_store)
        if output.resolve().is_relative_to(current_store.resolve()) or current_store.resolve().is_relative_to(output.resolve()):raise ValueError('RESTORE_DESTINATION_OVERLAP')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.context-restore-',dir=output.parent))
    try:
        shutil.copyfile(backup/'content.sqlite3',stage/'content.sqlite3')
        before=verify_database(stage/'content.sqlite3',progress=progress)
        # Additive owner migration on a copy, then compare invariant counts.
        db=packets.db_for(stage)
        try:
            with db:
                restored_state(db)
                if current_store:
                    current=lib.read_connection(current_store)
                    try:
                        tables={r[0] for r in current.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                        if 'context_tombstones' in tables:
                            for r in current.execute('SELECT * FROM context_tombstones'):
                                db.execute('INSERT INTO context_tombstones VALUES (?,?,?,?) ON CONFLICT(namespace,source_key) DO UPDATE SET epoch=max(epoch,excluded.epoch),event_id=CASE WHEN excluded.epoch>epoch THEN excluded.event_id ELSE event_id END',tuple(r))
                                pattern='context:'+r['source_key'].replace('!','!!').replace('_','!_').replace('%','!%')+':%'
                                db.execute("UPDATE sync_heads SET present=0 WHERE namespace=? AND (source_key=? OR source_key LIKE ? ESCAPE '!')",(r['namespace'],r['source_key'],pattern))
                        if 'library_record_heads' in tables:
                            for r in current.execute('SELECT namespace,source_key FROM library_record_heads WHERE tombstone=1'):
                                db.execute('UPDATE sync_heads SET present=0 WHERE namespace=? AND source_key=?',tuple(r))
                                eid=lib.record_event(db,r['namespace'],'RESTORED_CURRENT_TOMBSTONE',{'source_key':r['source_key']})
                                db.execute('INSERT OR IGNORE INTO context_tombstones VALUES (?,?,?,?)',(r['namespace'],r['source_key'],1,eid))
                    finally:current.close()
        finally:db.close()
        after=verify_database(stage/'content.sqlite3',progress=progress)
        for table,count in before['logical_counts'].items():
            if table not in {'context_events','context_tombstones'} and after['logical_counts'].get(table)!=count:raise ValueError('MIGRATION_INVARIANT_FAILED')
        report={'schema':'occ.context-restore.v1','state':'VERIFIED_ISOLATED_COPY',
                'backup_sha256':verified['sha256'],'before':before,'after':after,
                'current_tombstones_applied':current_store is not None,
                'recovery_namespace_required':current_store is None,'dispatch_allowed':False,
                'activation':'NOT_PERFORMED','credential_reconnect':'REQUIRED'}
        (stage/'RESTORE.json').write_bytes(lib.encoded(report))
        if progress:progress()
        os.rename(stage,output);return report
    finally:
        if stage.exists():shutil.rmtree(stage)


def activate_restored_copy(store,restored,*,process_stopped):
    """Explicit maintenance operation after an operator process-stop check.

    The app never automatically activates a restored archive. A durable marker
    blocks all new owner opens. The old DB is retained for crash recovery.
    """
    if process_stopped is not True:raise ValueError('OPERATOR_PROCESS_STOP_CONFIRMATION_REQUIRED')
    store=regular_tree(store);restored=regular_tree(restored)
    report=json.loads((restored/'RESTORE.json').read_text(encoding='utf-8'))
    if report.get('state')!='VERIFIED_ISOLATED_COPY' or report.get('current_tombstones_applied') is not True:raise ValueError('RESTORE_ACTIVATION_NOT_READY')
    verify_database(restored/'content.sqlite3')
    marker=store/'STORE_MAINTENANCE.json'
    old=store/'content.sqlite3';previous=store/'content.pre-restore.sqlite3';replacement=store/'content.restore-stage.sqlite3'
    if previous.exists() or replacement.exists():raise ValueError('ACTIVATION_RECOVERY_REQUIRED')
    with marker.open('xb') as stream:
        stream.write(lib.encoded({'phase':'PREPARED','old':'content.sqlite3','previous':previous.name,'replacement':replacement.name}));stream.flush();os.fsync(stream.fileno())
    try:
        db=sqlite3.connect(old,timeout=1)
        try:
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            db.execute('BEGIN EXCLUSIVE')
            if db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','NEEDS_RECONCILIATION') LIMIT 1").fetchone():raise ValueError('RECONCILIATION_REQUIRED')
            db.commit()
        finally:db.close()
        shutil.copyfile(restored/'content.sqlite3',replacement)
        current=ro_database(old);target=sqlite3.connect(replacement);target.row_factory=sqlite3.Row
        try:
            for tomb in current.execute('SELECT * FROM context_tombstones'):
                target.execute('INSERT INTO context_tombstones VALUES (?,?,?,?) ON CONFLICT(namespace,source_key) DO UPDATE SET epoch=max(epoch,excluded.epoch)',tuple(tomb))
                pattern='context:'+tomb['source_key'].replace('!','!!').replace('_','!_').replace('%','!%')+':%'
                target.execute("UPDATE sync_heads SET present=0 WHERE namespace=? AND (source_key=? OR source_key LIKE ? ESCAPE '!')",(tomb['namespace'],tomb['source_key'],pattern))
            if current.execute("SELECT 1 FROM sqlite_master WHERE name='library_record_heads'").fetchone():
                for tomb in current.execute('SELECT namespace,source_key FROM library_record_heads WHERE tombstone=1'):
                    target.execute('INSERT OR IGNORE INTO context_tombstones VALUES (?,?,1,?)',(tomb['namespace'],tomb['source_key'],'activation-ledger'))
                    target.execute('UPDATE sync_heads SET present=0 WHERE namespace=? AND source_key=?',tuple(tomb))
            restored_state(target);target.commit()
        finally:current.close();target.close()
        verify_database(replacement)
        for suffix in ('-wal','-shm'):
            sidecar=Path(str(old)+suffix)
            if sidecar.exists():sidecar.unlink()
        os.rename(old,previous)
        try:os.rename(replacement,old)
        except BaseException:
            os.rename(previous,old);raise
        marker.unlink()
        return {'state':'ACTIVATED','previous_database_retained':True,'dispatch_allowed':False}
    except BaseException:
        # A marker intentionally remains if an activation may have crossed its
        # boundary; a later fresh owner must not guess which database is current.
        raise


def recover_activation(store,*,process_stopped):
    if process_stopped is not True:raise ValueError('OPERATOR_PROCESS_STOP_CONFIRMATION_REQUIRED')
    store=regular_tree(store);marker=store/'STORE_MAINTENANCE.json'
    if not marker.is_file():raise ValueError('ACTIVATION_JOURNAL_REQUIRED')
    old=store/'content.sqlite3';previous=store/'content.pre-restore.sqlite3';replacement=store/'content.restore-stage.sqlite3'
    if not old.exists() and previous.exists():os.rename(previous,old)
    if not old.exists():raise ValueError('ACTIVATION_DATABASE_MISSING')
    verify_database(old)
    db=sqlite3.connect(old)
    try:
        restored_state(db);db.commit()
    finally:db.close()
    if replacement.exists():replacement.unlink()
    marker.unlink();return {'state':'RECOVERED','active_hash':file_sha(old),'dispatch_allowed':False}


def purge_tombstoned_source(store,namespace,source_key,operation_id):
    db=packets.db_for(store)
    try:
        db.execute('BEGIN IMMEDIATE')
        old=lib.begin_intent(db,namespace,operation_id,'purge',{'source_key':source_key})
        if old is not None:return old
        if not db.execute('SELECT 1 FROM context_tombstones WHERE namespace=? AND source_key=?',(namespace,source_key)).fetchone():raise ValueError('TOMBSTONE_REQUIRED')
        # Auditable packets may hold independent projected bytes; physical
        # removal never claims to erase those or already external backup copies.
        for row in db.execute('SELECT ref FROM context_packet_sources WHERE namespace=?',(namespace,)):
            if json.loads(row[0])['source_key']==source_key:raise ValueError('DEPENDENT_PACKET_RETENTION_REQUIRED')
        removed=0
        for source in db.execute('SELECT revision FROM context_sources WHERE namespace=? AND source_key=?',(namespace,source_key)):
            rev=source[0]
            for row in db.execute('SELECT item_id FROM context_raw_parts WHERE revision=?',(rev,)):
                if row[0] and not db.execute('SELECT 1 FROM sync_heads WHERE item_id=? AND present=1',(row[0],)).fetchone():
                    db.execute('DELETE FROM sync_versions WHERE item_id=?',(row[0],))
                    db.execute('DELETE FROM sync_heads WHERE item_id=? AND present=0',(row[0],))
                    db.execute('DELETE FROM content_fts WHERE id=?',(row[0],));db.execute('DELETE FROM items WHERE id=?',(row[0],))
            removed+=db.execute('DELETE FROM context_raw_parts WHERE revision=?',(rev,)).rowcount
            db.execute('DELETE FROM context_sources WHERE revision=?',(rev,))
        db.execute('DELETE FROM context_source_heads WHERE namespace=? AND source_key=?',(namespace,source_key))
        result={'state':'PURGED_OWNED_RAW_AND_DERIVED','parts_removed':removed,'external_backup_copies':'NOT_DELETED','tombstone_retained':True}
        lib.finish_intent(db,namespace,operation_id,result);db.commit();return result
    finally:db.close()


def export_sync(store,namespace,output):
    output=regular_tree(output)
    if output.exists():raise ValueError('SYNC_OUTPUT_EXISTS')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.context-sync-',dir=output.parent))
    db=lib.read_connection(Path(store))
    try:
        db.execute('BEGIN');h=hashlib.sha256();count=0
        with (stage/'RECORDS.jsonl').open('xb') as stream:
            for table,fields in SYNC_TABLES.items():
                if table=='context_raw_parts':
                    cursor=db.execute('SELECT p.* FROM context_raw_parts p JOIN context_sources s ON p.revision=s.revision WHERE s.namespace=? AND s.complete=1 ORDER BY p.revision,p.ordinal',(namespace,))
                else:
                    cursor=db.execute('SELECT * FROM '+table+' WHERE namespace=? ORDER BY rowid',(namespace,))
                for row in cursor:
                    record={k:({'base64':base64.b64encode(row[k]).decode()} if isinstance(row[k],bytes) else row[k]) for k in fields}
                    raw=lib.encoded({'table':table,'record':record})+b'\n';stream.write(raw);h.update(raw);count+=1
            stream.flush();os.fsync(stream.fileno())
        (stage/'MANIFEST.json').write_bytes(lib.encoded({'schema':'occ.context-sync.v1','namespace':namespace,'records':count,'sha256':h.hexdigest(),'grants_included':False,'execution_included':False}))
        os.rename(stage,output);return {'state':'EXPORTED_OFFLINE_SYNC','records':count,'sha256':h.hexdigest()}
    finally:
        db.rollback();db.close()
        if stage.exists():shutil.rmtree(stage)


def import_sync(store,namespace,bundle):
    bundle=regular_tree(bundle);manifest=json.loads((bundle/'MANIFEST.json').read_text(encoding='utf-8'))
    lib.exact(manifest,{'schema','namespace','records','sha256','grants_included','execution_included'})
    if manifest['schema']!='occ.context-sync.v1' or manifest['namespace']!=namespace or manifest['grants_included'] is not False or manifest['execution_included'] is not False:raise ValueError('SYNC_SCOPE')
    path=regular_tree(bundle/'RECORDS.jsonl')
    if file_sha(path)!=manifest['sha256']:raise ValueError('SYNC_HASH')
    db=packets.db_for(store)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS context_sync_conflicts(namespace TEXT,source_key TEXT,local_revision TEXT,remote_revision TEXT,PRIMARY KEY(namespace,source_key,remote_revision))')
        db.execute('BEGIN IMMEDIATE');count=0;conflicts=0
        with path.open('rb') as stream:
            while True:
                raw=stream.readline(lib.PAGE_BYTES+1)
                if not raw:break
                value=lib.strict_json(raw);lib.exact(value,{'table','record'});table=value['table']
                if table not in SYNC_TABLES:raise ValueError('SYNC_TABLE_DENIED')
                fields=SYNC_TABLES[table];rec=value['record'];lib.exact(rec,fields)
                if 'namespace' in rec and rec['namespace']!=namespace:raise ValueError('SYNC_SCOPE')
                if table=='context_raw_parts':
                    lib.exact(rec['raw'],{'base64'});rec['raw']=base64.b64decode(rec['raw']['base64'],validate=True)
                    if len(rec['raw'])>lib.PART_BYTES or lib.sha(rec['raw'])!=rec['sha256'] or rec['end']-rec['start']!=len(rec['raw']):raise ValueError('SYNC_BLOB_CORRUPT')
                    source=db.execute('SELECT namespace FROM context_sources WHERE revision=?',(rec['revision'],)).fetchone()
                    if not source or source[0]!=namespace:raise ValueError('SYNC_SCOPE')
                    # Imported text indexes are rebuilt, not copied as authority.
                    rec['item_id']=None
                if table=='context_events' and lib.sha(rec['payload'].encode())!=rec['payload_hash']:raise ValueError('SYNC_EVENT_CORRUPT')
                if table=='context_source_heads':
                    source=db.execute('SELECT namespace,source_key FROM context_sources WHERE revision=?',(rec['revision'],)).fetchone()
                    if not source or tuple(source)!=(namespace,rec['source_key']):raise ValueError('SYNC_SCOPE')
                    old=db.execute('SELECT revision FROM context_source_heads WHERE namespace=? AND source_key=?',(namespace,rec['source_key'])).fetchone()
                    if old and old[0]!=rec['revision']:
                        db.execute('INSERT OR IGNORE INTO context_sync_conflicts VALUES (?,?,?,?)',(namespace,rec['source_key'],old[0],rec['revision']));conflicts+=1;count+=1;continue
                # Exact primary-key replay must not overwrite another payload.
                keys=[r[1] for r in db.execute('PRAGMA table_info('+table+')') if r[5]]
                where=' AND '.join(k+'=?' for k in keys)
                old=db.execute('SELECT '+','.join(fields)+' FROM '+table+' WHERE '+where,tuple(rec[k] for k in keys)).fetchone()
                if old:
                    if table=='context_raw_parts':
                        if any(old[k]!=rec[k] for k in fields if k!='item_id'):raise ValueError('SYNC_RECORD_CONFLICT')
                    elif table=='context_tombstones':
                        if rec['epoch']>old['epoch']:db.execute('UPDATE context_tombstones SET epoch=?,event_id=? WHERE namespace=? AND source_key=?',(rec['epoch'],rec['event_id'],namespace,rec['source_key']))
                    elif any(old[k]!=rec[k] for k in fields):raise ValueError('SYNC_RECORD_CONFLICT')
                else:db.execute('INSERT INTO '+table+' ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',tuple(rec[k] for k in fields))
                count+=1
        if count!=manifest['records']:raise ValueError('SYNC_RECORD_COUNT')
        for tomb in db.execute('SELECT namespace,source_key FROM context_tombstones WHERE namespace=?',(namespace,)):
            key=tomb['source_key'];pattern='context:'+key.replace('!','!!').replace('_','!_').replace('%','!%')+':%'
            db.execute("UPDATE sync_heads SET present=0 WHERE namespace=? AND (source_key=? OR source_key LIKE ? ESCAPE '!')",(namespace,key,pattern))
        # Materialize imported current text through the existing items/FTS/head
        # owner. Raw parts remain authoritative even across UTF8 boundaries.
        for head in db.execute('SELECT * FROM context_source_heads WHERE namespace=?',(namespace,)):
            if db.execute('SELECT 1 FROM context_tombstones WHERE namespace=? AND source_key=?',(namespace,head['source_key'])).fetchone():continue
            for part in db.execute('SELECT * FROM context_raw_parts WHERE revision=? ORDER BY ordinal',(head['revision'],)):
                if part['item_id']:continue
                try:
                    decoded=part['raw'].decode('utf-8')
                    if '\0' in decoded:continue
                except UnicodeError:continue
                iid=lib.digest([head['revision'],part['ordinal'],part['sha256']]);key=f"context:{head['source_key']}:{part['ordinal']}"
                lib._insert_item(db,{'schema':'occ.content-lab.item.v1','id':iid,'namespace':namespace,'source_key':key,'text':decoded,'input_sha256':part['sha256'],'authority':'source-content-not-action-instructions','asr_inference_performed':False})
                db.execute('UPDATE context_raw_parts SET item_id=? WHERE revision=? AND ordinal=?',(iid,head['revision'],part['ordinal']))
                db.execute('INSERT OR IGNORE INTO sync_versions VALUES (?,?,?,?)',(namespace,key,iid,time.time()))
                db.execute('INSERT INTO sync_heads VALUES (?,?,?,?,?,1) ON CONFLICT(namespace,source_key) DO UPDATE SET item_id=excluded.item_id,raw_hash=excluded.raw_hash,generation=excluded.generation,present=1',(namespace,key,iid,part['sha256'],head['revision']))
        verify_database(None,_connection=db)
        db.commit()
        return {'state':'SYNC_IMPORTED','records':count,'conflicts':conflicts,'dispatch_allowed':False}
    finally:db.close()
