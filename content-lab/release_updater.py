"""Exact-asset staged updater driven only by an existing registered Core job.

Activation is implemented for explicitly marked isolated qualification targets.
Production/unattended activation remains blocked until predecessor/STOP/device
qualification exists. Data migrations never run against the canonical store.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
import time
import zipfile

import automation_core as core
import workflow_state as state

FIELDS={'mode','root','device_id','installation_id','asset_file','asset_sha256',
        'binding_file','binding_sha256','source_commit','source_tree','tests','timeout_seconds'}


def safe_root(path):
    p=Path(path)
    if not p.is_absolute() or not p.is_dir() or any(x.is_symlink() or getattr(x,'is_junction',lambda:False)() for x in (p,*p.parents)):
        raise ValueError('UPDATE_ISOLATED_ROOT_REQUIRED')
    return p.resolve()


def validate_profile(config):
    if not isinstance(config,dict) or set(config)!=FIELDS or config['mode'] not in {'STAGE_ONLY','BOUNDED_QUALIFICATION','QUALIFY_EXISTING'}:
        raise ValueError('UPDATE_REGISTERED_PROFILE_REQUIRED')
    for k in ('root','asset_file','binding_file'):
        if not isinstance(config[k],str) or not Path(config[k]).is_absolute():raise ValueError('UPDATE_ABSOLUTE_POLICY_PATH_REQUIRED')
    for k in ('asset_sha256','binding_sha256'):state.checked_hash(config[k])
    for k in ('source_commit','source_tree'):
        if not isinstance(config[k],str) or not core.SHA.fullmatch(config[k]):raise ValueError('UPDATE_PINNED_SOURCE_REQUIRED')
    for k in ('device_id','installation_id'):core.identifier(config[k])
    if not isinstance(config['tests'],list) or not config['tests'] or not all(isinstance(a,list) and a and all(isinstance(x,str) and x and '\0' not in x for x in a) for a in config['tests']):
        raise ValueError('UPDATE_REGISTERED_TESTS_REQUIRED')
    core.strict_int(config['timeout_seconds'],1,300)
    return config


def atomic_json(path,value):
    if path.is_symlink() or not path.parent.is_dir():raise ValueError('UPDATE_POINTER_PATH_UNSAFE')
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'.')
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:
            f.write(core.encoded(value)+'\n');f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


def capability_diff(old,new):
    return {k:('ADDED' if k not in old else 'REMOVED' if k not in new else 'UNCHANGED' if old[k]==new[k] else 'REQUALIFICATION_REQUIRED') for k in sorted(set(old)|set(new))}


def usability(installed,qualification,grant,*,revoked=False):
    if revoked or not all(isinstance(x,dict) for x in (installed,qualification,grant)):return False
    if installed.get('state')!='INSTALLED_OBSERVED' or qualification.get('state')!='DEVICE_QUALIFIED' or grant.get('state')!='ACTIVE':return False
    bindings=('device_id','installation_id','artifact_digest','source_commit','capability_id','contract_version','scope_digest','target_profile')
    return all(installed.get(k) is not None and installed.get(k)==qualification.get(k)==grant.get(k) for k in bindings)


def load_binding(config,progress):
    path=state.registered_file(config['binding_file'],config['binding_sha256'],progress)
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=config['binding_sha256']:raise ValueError('UPDATE_BINDING_DRIFT')
    b=json.loads(raw.decode('utf-8'))
    if not isinstance(b,dict) or set(b)!={'source_commit','source_tree','asset_sha256','data_schema_version','files','capabilities','build_provenance'}:
        raise ValueError('UPDATE_BINDING_SCHEMA')
    if any(b[k]!=config[k] for k in ('source_commit','source_tree','asset_sha256')):raise ValueError('UPDATE_SOURCE_ASSET_MISMATCH')
    state.integer(b['data_schema_version'])
    if not isinstance(b['files'],dict) or not b['files'] or not isinstance(b['capabilities'],dict) or not isinstance(b['build_provenance'],dict):
        raise ValueError('UPDATE_PROVENANCE_REQUIRED')
    # Provenance is operator-bound input, not independently authenticated signature.
    for name,spec in b['files'].items():
        p=PurePosixPath(name)
        if not name or '\\' in name or '\0' in name or ':' in name or p.is_absolute() or '..' in p.parts or p.as_posix()!=name or not p.parts:
            raise ValueError('UPDATE_ARCHIVE_PATH_UNSAFE')
        if not isinstance(spec,dict) or set(spec)!={'sha256','bytes'}:raise ValueError('UPDATE_FILE_MANIFEST_SCHEMA')
        reserved={'con','prn','aux','nul'}|{f'com{i}' for i in range(1,10)}|{f'lpt{i}' for i in range(1,10)}
        if any(x.endswith((' ','.')) or x.split('.')[0].casefold() in reserved for x in p.parts):
            raise ValueError('UPDATE_ARCHIVE_WINDOWS_ALIAS')
        state.checked_hash(spec['sha256']);state.integer(spec['bytes'])
    # Windows case aliases, and file-vs-directory prefix conflicts.
    folded=[n.casefold() for n in b['files']]
    if len(set(folded))!=len(folded):raise ValueError('UPDATE_ARCHIVE_ALIAS_CONFLICT')
    for name in folded:
        if any('/'.join(PurePosixPath(name).parts[:i]) in set(folded) for i in range(1,len(PurePosixPath(name).parts))):
            raise ValueError('UPDATE_ARCHIVE_ALIAS_CONFLICT')
    return b


def extract_exact(asset,root,binding,progress):
    with zipfile.ZipFile(asset) as z:
        entries=z.infolist()
        if len({i.filename for i in entries})!=len(entries):raise ValueError('UPDATE_ARCHIVE_DUPLICATE')
        # Directory records are accepted only if they are ancestors of known files.
        expected=set(binding['files']);found=set()
        for i in entries:
            mode=(i.external_attr>>16)&0xffff
            if stat.S_ISLNK(mode) or (mode and stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)):
                raise ValueError('UPDATE_ARCHIVE_LINK_OR_SPECIAL')
            if i.is_dir():
                if i.filename.startswith('/') or '..' in PurePosixPath(i.filename).parts or not any(n.startswith(i.filename) for n in expected):
                    raise ValueError('UPDATE_ARCHIVE_PATH_UNSAFE')
                continue
            if i.filename not in expected:raise ValueError('UPDATE_ARCHIVE_UNDECLARED_PATH')
            spec=binding['files'][i.filename]
            if i.file_size!=spec['bytes']:raise ValueError('UPDATE_ARCHIVE_SIZE_MISMATCH')
            target=root/PurePosixPath(i.filename)
            target.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();total=0
            with z.open(i) as source,target.open('xb') as dest:
                for raw in iter(lambda:source.read(1024*1024),b''):
                    progress();total+=len(raw)
                    if total>spec['bytes']:raise ValueError('UPDATE_ARCHIVE_SIZE_MISMATCH')
                    h.update(raw);dest.write(raw)
                dest.flush();os.fsync(dest.fileno())
            if h.hexdigest()!=spec['sha256'] or total!=spec['bytes']:raise ValueError('UPDATE_FILE_HASH_MISMATCH')
            found.add(i.filename)
        if found!=expected:raise ValueError('UPDATE_ARCHIVE_INCOMPLETE')


def verify_tree(root,binding,progress):
    actual=set()
    for path in root.rglob('*'):
        if path.is_symlink() or getattr(path,'is_junction',lambda:False)():raise ValueError('UPDATE_CANDIDATE_CHANGED')
        if path.is_file():actual.add(path.relative_to(root).as_posix())
    if actual!=set(binding['files']):raise ValueError('UPDATE_CANDIDATE_CHANGED')
    for name,spec in binding['files'].items():
        path=root/name
        if path.stat().st_size!=spec['bytes'] or state.file_digest(path,progress)!=spec['sha256']:
            raise ValueError('UPDATE_CANDIDATE_CHANGED')


def rehearse_data(owner,job,root,schema_version):
    source=core.read_connection(owner.store);target=sqlite3.connect(root/'rehearsal.sqlite3')
    try:
        source.backup(target,pages=128,progress=lambda *_:owner.heartbeat(job))
        if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('UPDATE_BACKUP_INTEGRITY')
        version=target.execute('PRAGMA user_version').fetchone()[0]
        if version!=schema_version:raise ValueError('UPDATE_MIGRATION_PLAN_NOT_QUALIFIED')
        tables=[r[0] for r in target.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        counts={t:target.execute('SELECT count(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
        return {'state':'COPIED_STORE_REHEARSAL','schema_version':version,'table_counts':counts,'production_modified':False}
    finally:
        source.close();target.close()


def observe_pointer(root,binding,config,progress):
    pointer=root/'active.json'
    if any(x.is_symlink() or getattr(x,'is_junction',lambda:False)() for x in (pointer,pointer.parent)) or not pointer.is_file():raise ValueError('UPDATE_ACTIVE_POINTER_MISSING')
    value=json.loads(pointer.read_text(encoding='utf-8'))
    if value.get('asset_sha256')!=config['asset_sha256'] or value.get('source_commit')!=config['source_commit']:
        raise ValueError('UPDATE_ACTIVE_BINDING_MISMATCH')
    candidate=root/'versions'/config['asset_sha256'];verify_tree(candidate,binding,progress)
    return {'schema':'occ.installed-receipt.v1','state':'INSTALLED_OBSERVED','device_id':config['device_id'],
            'installation_id':config['installation_id'],'artifact_digest':config['asset_sha256'],
            'source_commit':config['source_commit'],'pointer_digest':state.file_digest(pointer),
            'observation_origin':'FILESYSTEM_TEST_TARGET','device_qualified':False,'usable':False}


@contextmanager
def installation_owner(owner,job,config):
    root=safe_root(config['root']);path=root/'.update-owner.json'
    binding={'store_digest':core.digest(str(owner.store.resolve())),'job_id':job['id'],
             'installation_id':config['installation_id'],'device_id':config['device_id'],
             'asset_sha256':config['asset_sha256']}
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        raise ValueError('UPDATE_OWNER_RECONCILIATION_REQUIRED') from None
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(core.encoded(binding));f.flush();os.fsync(f.fileno())
        yield
    finally:
        # On a lost canonical owner keep the marker; only explicit reconciliation
        # after observing the stopped process can retire it.
        current=owner.get(job['id'])
        if current['lease_token']==job['lease_token'] and current['state']=='RUNNING' and current['lease_until']>=time.time():
            if path.is_file() and not path.is_symlink() and json.loads(path.read_text(encoding='utf-8'))==binding:
                path.unlink()


def update(owner,job,config):
    config=validate_profile(config)
    with installation_owner(owner,job,config):
        return _update_owned(owner,job,config)


def _update_owned(owner,job,config):
    config=validate_profile(config);root=safe_root(config['root'])
    # Only explicit marked isolated test targets activate. Nothing fabricates the
    # missing device/keyboard/predecessor receipts for an unattended live install.
    marker=root/'QUALIFICATION_TARGET.json'
    if config['mode'] in {'BOUNDED_QUALIFICATION','QUALIFY_EXISTING'}:
        marker=state.registered_file(marker)
        v=json.loads(marker.read_text(encoding='utf-8'))
        if v!={'schema':'occ.isolated-update-target.v1','installation_id':config['installation_id'],'device_id':config['device_id'],'mode':'TEST_ONLY'}:
            raise ValueError('UPDATE_QUALIFICATION_SCOPE_REQUIRED')
    if root.is_relative_to(owner.store.resolve()) or owner.store.resolve().is_relative_to(root):
        raise ValueError('UPDATE_DATA_ROOT_OVERLAP')
    progress=lambda:owner.heartbeat(job)
    binding=load_binding(config,progress);asset=state.registered_file(config['asset_file'],config['asset_sha256'],progress)
    versions=root/'versions'
    if versions.is_symlink() or getattr(versions,'is_junction',lambda:False)():raise ValueError('UPDATE_VERSION_ROOT_UNSAFE')
    versions.mkdir(exist_ok=True)
    candidate=versions/config['asset_sha256'];operation=core.digest([config['installation_id'],config['device_id'],config['asset_sha256'],config['source_commit']])
    with state.transaction(owner.store) as db:
        state.assert_job(db,job)
        # The serial Core is the sole writer. Crash/orphan holds the global owner.
        prior=state.get(db,'update',operation)
        if prior and prior['value']['state'] in {'ACTIVATING','UNKNOWN_EFFECT'}:
            raise ValueError('UPDATE_RECONCILIATION_REQUIRED')
        if prior and prior['value']['state']=='INSTALLED_OBSERVED_UNQUALIFIED' and config['mode']!='QUALIFY_EXISTING':
            raise ValueError('UPDATE_POSTINSTALL_QUALIFICATION_REQUIRED')
        reuse=bool(prior and prior['value']['state']=='INSTALLED_OBSERVED' and prior['value'].get('config_digest')==core.digest(config))
        if not reuse:
            state.put(db,'update',operation,{'state':'STAGING','config_digest':core.digest(config),'candidate':config['asset_sha256']},prior['revision'] if prior else 0)
    if config['mode']=='QUALIFY_EXISTING':
        observed=observe_pointer(root,binding,config,progress)
        canary=[]
        for argv in config['tests']:
            args=[x.replace('{CANDIDATE}',str(candidate)).replace('{DATA}',str(owner.store/'content.sqlite3')) for x in argv]
            r=owner.command(job,args,candidate,config['timeout_seconds']);canary.append(r)
            if r['exit_code'] or r['reason']:raise ValueError('UPDATE_CANARY_FAILED')
        verify_tree(candidate,binding,progress)
        receipt={**observed,'canary':canary,'scope':'ISOLATED_TEST_TARGET','config_digest':core.digest(config)}
        with state.transaction(owner.store) as db:
            state.assert_job(db,job)
            old=state.get(db,'update',operation);state.put(db,'update',operation,receipt,old['revision'])
        return receipt
    if reuse:
        receipt=observe_pointer(root,binding,config,progress)
        return {**receipt,'reused':True}
    if candidate.exists():verify_tree(candidate,binding,progress)
    else:
        total=sum(x['bytes'] for x in binding['files'].values())
        if shutil.disk_usage(root).free<total:raise ValueError('UPDATE_DISK_CAPACITY_WAIT')
        stage=Path(tempfile.mkdtemp(dir=versions,prefix='.stage-'))
        try:
            extract_exact(asset,stage,binding,progress);verify_tree(stage,binding,progress)
            # Recheck actual downloaded bytes after extraction.
            if state.file_digest(asset,progress)!=config['asset_sha256']:raise ValueError('UPDATE_ASSET_DRIFT')
            os.replace(stage,candidate)
        finally:
            if stage.exists():shutil.rmtree(stage)
    with tempfile.TemporaryDirectory(dir=root,prefix='.rehearsal-') as rehearsal:
        data_receipt=rehearse_data(owner,job,Path(rehearsal),binding['data_schema_version'])
        results=[]
        for argv in config['tests']:
            args=[x.replace('{CANDIDATE}',str(candidate)).replace('{DATA}',str(Path(rehearsal)/'rehearsal.sqlite3')) for x in argv]
            r=owner.command(job,args,candidate,config['timeout_seconds']);results.append(r)
            if r['exit_code'] or r['reason']:raise ValueError('UPDATE_REHEARSAL_TEST_FAILED')
        verify_tree(candidate,binding,progress)
    receipt={'config_digest':core.digest(config),'state':'STAGED_VERIFIED','source_commit':config['source_commit'],'source_tree':config['source_tree'],
             'artifact_digest':config['asset_sha256'],'data_rehearsal':data_receipt,'tests':results,
             'provenance':'OPERATOR_BOUND_MANIFEST_NOT_SIGNATURE_AUTHENTICATION','reproducibility':'NOT_MEASURED','source_chain_state':'OPERATOR_BOUND_UNVERIFIED',
             'verified_properties':['exact_asset_bytes','file_manifest','copied_store_integrity','registered_candidate_tests'],
             'device_qualified':False,'usable':False,'capability_diff':capability_diff({},binding['capabilities'])}
    if config['mode']=='STAGE_ONLY':
        with state.transaction(owner.store) as db:
            state.assert_job(db,job)
            old=state.get(db,'update',operation);state.put(db,'update',operation,receipt,old['revision'])
        return receipt
    pointer=root/'active.json';old_pointer=json.loads(pointer.read_text(encoding='utf-8')) if pointer.exists() else None
    if pointer.is_symlink():raise ValueError('UPDATE_POINTER_PATH_UNSAFE')
    with state.transaction(owner.store) as db:
        state.assert_job(db,job)
        old=state.get(db,'update',operation)
        state.put(db,'update',operation,{**receipt,'state':'ACTIVATING','previous':old_pointer},old['revision'])
    # Core's global serial lease gives quiescence for its canonical jobs.
    progress()
    atomic_json(pointer,{'source_commit':config['source_commit'],'asset_sha256':config['asset_sha256'],'data_schema_version':binding['data_schema_version']})
    try:
        observed=observe_pointer(root,binding,config,progress)
        canary=[]
        for argv in config['tests']:
            # Canary reads live canonical data only through the registered argv;
            # no copied DB is promoted/replaced, so rollback retains new records.
            args=[x.replace('{CANDIDATE}',str(candidate)).replace('{DATA}',str(owner.store/'content.sqlite3')) for x in argv]
            r=owner.command(job,args,candidate,config['timeout_seconds']);canary.append(r)
            if r['exit_code'] or r['reason']:raise ValueError('UPDATE_CANARY_FAILED')
        verify_tree(candidate,binding,progress)
        observed={**receipt,**observed,'canary':canary,'scope':'ISOLATED_TEST_TARGET','previous':old_pointer}
        with state.transaction(owner.store) as db:
            state.assert_job(db,job)
            old=state.get(db,'update',operation);state.put(db,'update',operation,observed,old['revision'])
        return observed
    except BaseException:
        # Roll back only this pointer if still owned; never touch canonical data.
        current=json.loads(pointer.read_text(encoding='utf-8')) if pointer.is_file() else None
        if current and current.get('asset_sha256')==config['asset_sha256']:
            if old_pointer is not None:atomic_json(pointer,old_pointer)
            else:pointer.unlink()
        with state.transaction(owner.store) as db:
            state.assert_job(db,job)
            old=state.get(db,'update',operation);state.put(db,'update',operation,{**receipt,'state':'ROLLBACK_POINTER_RESTORED_UNQUALIFIED','previous':old_pointer},old['revision'])
        raise


def reconcile_test_installation(store,config,*,process_stopped):
    if process_stopped is not True:raise ValueError('UPDATE_STOP_OBSERVATION_REQUIRED')
    config=validate_profile(config);root=safe_root(config['root']);binding=load_binding(config,lambda:None)
    operation=core.digest([config['installation_id'],config['device_id'],config['asset_sha256'],config['source_commit']])
    with state.transaction(store) as db:
        old=state.get(db,'update',operation)
        if not old or old['value']['state'] not in {'ACTIVATING','UNKNOWN_EFFECT'}:raise ValueError('UPDATE_RECOVERY_STATE_REQUIRED')
        lock=root/'.update-owner.json'
        if lock.exists():
            if lock.is_symlink():raise ValueError('UPDATE_OWNER_RECONCILIATION_REQUIRED')
            held=json.loads(lock.read_text(encoding='utf-8'))
            if held.get('store_digest')!=core.digest(str(Path(store).resolve())) or any(held.get(k)!=config[k] for k in ('installation_id','device_id','asset_sha256')):
                raise ValueError('UPDATE_OWNER_SCOPE_MISMATCH')
        pointer=root/'active.json'
        if pointer.is_symlink():raise ValueError('UPDATE_POINTER_PATH_UNSAFE')
        current=json.loads(pointer.read_text(encoding='utf-8')) if pointer.exists() else None
        if current==old['value'].get('previous'):
            receipt={**old['value'],'state':'ACTIVATION_NOT_APPLIED','usable':False}
        elif current and current.get('asset_sha256')==config['asset_sha256']:
            receipt=observe_pointer(root,binding,config,lambda:None)
            receipt['state']='INSTALLED_OBSERVED_UNQUALIFIED'
        else:
            raise ValueError('UPDATE_RECOVERY_TARGET_UNKNOWN')
        state.put(db,'update',operation,receipt,old['revision'])
    if lock.exists():lock.unlink()
    return receipt
