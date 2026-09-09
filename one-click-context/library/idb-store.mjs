const DB_NAME='one-click-context-library';
const DB_VERSION=1;
const RECORDS='records';
const META='meta';
const META_KEY='library';

function fail(code){throw Object.assign(new Error(code),{code});}
function req(request){return new Promise((resolve,reject)=>{request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error||new Error('IDB_REQUEST_FAILED'));});}
function done(tx){return new Promise((resolve,reject)=>{tx.oncomplete=()=>resolve();tx.onabort=()=>reject(tx.error||new Error('IDB_ABORT'));tx.onerror=()=>{};});}
function checkedRevision(value){if(!Number.isSafeInteger(value)||value<0)fail('INVALID_LIBRARY_REVISION');return value;}
function checkedRecords(records){if(!Array.isArray(records))fail('INVALID_LIBRARY_RECORDS');const ids=new Set();for(const r of records){if(!r||typeof r!=='object'||typeof r.id!=='string'||!r.id||ids.has(r.id))fail('INVALID_LIBRARY_RECORD');ids.add(r.id);}return records;}

export function openLibraryDB(indexedDB=globalThis.indexedDB){
  if(!indexedDB?.open) return Promise.reject(Object.assign(new Error('INDEXEDDB_UNAVAILABLE'),{code:'INDEXEDDB_UNAVAILABLE'}));
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open(DB_NAME,DB_VERSION);
    request.onupgradeneeded=()=>{
      const db=request.result;
      if(!db.objectStoreNames.contains(RECORDS))db.createObjectStore(RECORDS,{keyPath:'id'});
      if(!db.objectStoreNames.contains(META))db.createObjectStore(META,{keyPath:'key'});
    };
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error||new Error('IDB_OPEN_FAILED'));
    request.onblocked=()=>reject(Object.assign(new Error('IDB_UPGRADE_BLOCKED'),{code:'IDB_UPGRADE_BLOCKED'}));
  });
}

export async function readLibrary(db){
  const tx=db.transaction([RECORDS,META],'readonly'), recordsStore=tx.objectStore(RECORDS), metaStore=tx.objectStore(META);
  const [records,meta]=await Promise.all([req(recordsStore.getAll()),req(metaStore.get(META_KEY))]);
  await done(tx);
  const revision=meta?.revision??0;checkedRevision(revision);checkedRecords(records);
  return {revision,records,updatedAt:meta?.updatedAt||null,schema:1};
}

export async function replaceLibrary(db,expectedRevision,records,{updatedAt=new Date().toISOString()}={}){
  checkedRevision(expectedRevision);checkedRecords(records);
  const tx=db.transaction([RECORDS,META],'readwrite'), recordsStore=tx.objectStore(RECORDS), metaStore=tx.objectStore(META);
  let result;
  try{
    const meta=await req(metaStore.get(META_KEY)), current=meta?.revision??0;checkedRevision(current);
    if(current!==expectedRevision){tx.abort();fail('LIBRARY_REVISION_CONFLICT');}
    recordsStore.clear();for(const r of records)recordsStore.put(structuredClone(r));
    const revision=current+1;metaStore.put({key:META_KEY,revision,updatedAt});result={revision,updatedAt,count:records.length};
  }catch(error){try{tx.abort();}catch{}throw error;}
  await done(tx);return result;
}

export async function mergeRestore(db,expectedRevision,plan,{updatedAt=new Date().toISOString()}={}){
  checkedRevision(expectedRevision);
  if(!plan||!Array.isArray(plan.adds)||!Array.isArray(plan.conflicts)||plan.conflicts.length)fail('RESTORE_CONFLICT');
  checkedRecords(plan.adds);
  const tx=db.transaction([RECORDS,META],'readwrite'), recordsStore=tx.objectStore(RECORDS), metaStore=tx.objectStore(META);
  let result;
  try{
    const meta=await req(metaStore.get(META_KEY)),current=meta?.revision??0;checkedRevision(current);
    if(current!==expectedRevision){tx.abort();fail('LIBRARY_REVISION_CONFLICT');}
    for(const r of plan.adds){if(await req(recordsStore.get(r.id))){tx.abort();fail('RESTORE_STALE_PLAN');}recordsStore.add(structuredClone(r));}
    const revision=current+1;metaStore.put({key:META_KEY,revision,updatedAt});result={revision,updatedAt,added:plan.adds.length};
  }catch(error){try{tx.abort();}catch{}throw error;}
  await done(tx);return result;
}

export async function clearLibrary(db,expectedRevision,{updatedAt=new Date().toISOString()}={}){
  return replaceLibrary(db,expectedRevision,[],{updatedAt});
}

export async function importLegacyOnce(db,legacyRecords){
  checkedRecords(legacyRecords);
  const current=await readLibrary(db);
  if(current.records.length||current.revision!==0)return {...current,migrated:false};
  if(!legacyRecords.length)return {...current,migrated:false};
  const committed=await replaceLibrary(db,0,legacyRecords);
  return {revision:committed.revision,records:legacyRecords,updatedAt:committed.updatedAt,schema:1,migrated:true};
}

export const IDB_LIBRARY={DB_NAME,DB_VERSION,RECORDS,META,META_KEY};
