const DB_NAME='one-click-context-library';
const DB_VERSION=2;
const RECORDS='records';
const META='meta';
const BLOBS='blobs';
const TOMBSTONES='tombstones';
const META_KEY='library';

function fail(code){throw Object.assign(new Error(code),{code});}
function req(request){return new Promise((resolve,reject)=>{request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error||new Error('IDB_REQUEST_FAILED'));});}
function done(tx){return new Promise((resolve,reject)=>{tx.oncomplete=()=>resolve();tx.onabort=()=>reject(tx.error||new Error('IDB_ABORT'));tx.onerror=()=>{};});}
function checkedRevision(value){if(!Number.isSafeInteger(value)||value<0)fail('INVALID_LIBRARY_REVISION');return value;}
function checkedRecords(records){if(!Array.isArray(records))fail('INVALID_LIBRARY_RECORDS');const ids=new Set();for(const r of records){if(!r||typeof r!=='object'||typeof r.id!=='string'||!r.id||ids.has(r.id))fail('INVALID_LIBRARY_RECORD');ids.add(r.id);}return records;}
function canonical(value){if(value===null||typeof value==='boolean'||typeof value==='string')return JSON.stringify(value);if(typeof value==='number'){if(!Number.isSafeInteger(value))fail('INVALID_CANONICAL_NUMBER');return JSON.stringify(value);}if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';fail('INVALID_CANONICAL_VALUE');}
async function sha256Bytes(bytes){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');}
async function sha256(text){return sha256Bytes(new TextEncoder().encode(text));}
function validHash(value){return typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);}

export async function restorePlanHash(expectedRevision,plan){checkedRevision(expectedRevision);if(!plan||!Array.isArray(plan.adds)||!Array.isArray(plan.duplicates)||!Array.isArray(plan.conflicts))fail('INVALID_RESTORE_PLAN');return sha256(canonical({expectedRevision,adds:plan.adds,duplicates:plan.duplicates,conflicts:plan.conflicts}));}

async function prepareRecords(records){
  checkedRecords(records);const prepared=[],candidates=new Map();
  for(const source of records){const r=structuredClone(source);
    if(r.original!=null){if(!Array.isArray(r.original)||r.original.some(x=>!Number.isInteger(x)||x<0||x>255))fail('INVALID_ORIGINAL_BYTES');const bytes=Uint8Array.from(r.original),hash=await sha256Bytes(bytes);if(r.inputSha256&&r.inputSha256!==hash)fail('ORIGINAL_HASH_MISMATCH');r.originalRef={sha256:hash,bytes:bytes.length};delete r.original;candidates.set(hash,bytes);}
    if(r.originalRef!=null){if(!r.originalRef||!validHash(r.originalRef.sha256)||!Number.isSafeInteger(r.originalRef.bytes)||r.originalRef.bytes<0)fail('INVALID_ORIGINAL_REF');}
    prepared.push(r);
  }
  return {records:prepared,candidates};
}

function desiredBlobRefs(records){const refs=new Map();for(const r of records)if(r.originalRef){refs.set(r.originalRef.sha256,(refs.get(r.originalRef.sha256)||0)+1);}return refs;}
function writeBlobReconciliation(store,currentBlobs,desired,candidates){const existing=new Map(currentBlobs.map(b=>[b.sha256,b]));for(const [sha256,refCount] of desired){const candidate=candidates.get(sha256),prior=existing.get(sha256);if(!candidate&&!prior)fail('MISSING_ORIGINAL_BLOB');const bytes=candidate||prior.bytes;if(!(bytes instanceof Uint8Array))fail('CORRUPT_ORIGINAL_BLOB');store.put({sha256,bytes,size:bytes.length,refCount});}for(const blob of currentBlobs)if(!desired.has(blob.sha256))store.delete(blob.sha256);}

export function openLibraryDB(indexedDB=globalThis.indexedDB){
  if(!indexedDB?.open)return Promise.reject(Object.assign(new Error('INDEXEDDB_UNAVAILABLE'),{code:'INDEXEDDB_UNAVAILABLE'}));
  return new Promise((resolve,reject)=>{const request=indexedDB.open(DB_NAME,DB_VERSION);request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains(RECORDS))db.createObjectStore(RECORDS,{keyPath:'id'});if(!db.objectStoreNames.contains(META))db.createObjectStore(META,{keyPath:'key'});if(!db.objectStoreNames.contains(BLOBS))db.createObjectStore(BLOBS,{keyPath:'sha256'});if(!db.objectStoreNames.contains(TOMBSTONES))db.createObjectStore(TOMBSTONES,{keyPath:'id'});};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error||new Error('IDB_OPEN_FAILED'));request.onblocked=()=>reject(Object.assign(new Error('IDB_UPGRADE_BLOCKED'),{code:'IDB_UPGRADE_BLOCKED'}));});
}

export async function readLibrary(db){const tx=db.transaction([RECORDS,META,TOMBSTONES],'readonly'),recordsStore=tx.objectStore(RECORDS),metaStore=tx.objectStore(META),tombStore=tx.objectStore(TOMBSTONES);const [records,meta,tombstones]=await Promise.all([req(recordsStore.getAll()),req(metaStore.get(META_KEY)),req(tombStore.getAll())]);await done(tx);const revision=meta?.revision??0;checkedRevision(revision);checkedRecords(records);return {revision,records,updatedAt:meta?.updatedAt||null,schema:2,tombstoneCount:tombstones.length};}

export async function readOriginal(db,record){if(record?.original!=null){if(!Array.isArray(record.original))fail('INVALID_ORIGINAL_BYTES');return Uint8Array.from(record.original);}const ref=record?.originalRef;if(!ref)return null;if(!validHash(ref.sha256))fail('INVALID_ORIGINAL_REF');const tx=db.transaction(BLOBS,'readonly'),blob=await req(tx.objectStore(BLOBS).get(ref.sha256));await done(tx);if(!blob)fail('MISSING_ORIGINAL_BLOB');if(!(blob.bytes instanceof Uint8Array)||blob.bytes.length!==ref.bytes||await sha256Bytes(blob.bytes)!==ref.sha256)fail('CORRUPT_ORIGINAL_BLOB');return blob.bytes.slice();}

export async function replaceLibrary(db,expectedRevision,records,{updatedAt=new Date().toISOString()}={}){
  checkedRevision(expectedRevision);const prepared=await prepareRecords(records),desired=desiredBlobRefs(prepared.records);
  const tx=db.transaction([RECORDS,META,BLOBS,TOMBSTONES],'readwrite'),recordsStore=tx.objectStore(RECORDS),metaStore=tx.objectStore(META),blobStore=tx.objectStore(BLOBS),tombStore=tx.objectStore(TOMBSTONES);let result;
  try{const [meta,currentRecords,currentBlobs,tombstones]=await Promise.all([req(metaStore.get(META_KEY)),req(recordsStore.getAll()),req(blobStore.getAll()),req(tombStore.getAll())]);const current=meta?.revision??0;checkedRevision(current);if(current!==expectedRevision){tx.abort();fail('LIBRARY_REVISION_CONFLICT');}const oldIds=new Set(currentRecords.map(r=>r.id)),newIds=new Set(prepared.records.map(r=>r.id)),tombById=new Set(tombstones.map(t=>t.id));for(const id of newIds)if(tombById.has(id)&&!oldIds.has(id)){tx.abort();fail('TOMBSTONED_RECORD_ID');}const revision=current+1;for(const id of oldIds)if(!newIds.has(id))tombStore.put({id,deletedAt:updatedAt,revision});recordsStore.clear();for(const r of prepared.records)recordsStore.put(r);writeBlobReconciliation(blobStore,currentBlobs,desired,prepared.candidates);metaStore.put({key:META_KEY,revision,updatedAt});result={revision,updatedAt,count:prepared.records.length,blobCount:desired.size};}catch(error){try{tx.abort();}catch{}throw error;}await done(tx);return result;
}

export async function mergeRestore(db,expectedRevision,plan,approvedPlanHash,{updatedAt=new Date().toISOString()}={}){
  checkedRevision(expectedRevision);if(!plan||!Array.isArray(plan.adds)||!Array.isArray(plan.duplicates)||!Array.isArray(plan.conflicts)||plan.conflicts.length)fail('RESTORE_CONFLICT');const prepared=await prepareRecords(plan.adds);if(approvedPlanHash!==await restorePlanHash(expectedRevision,plan))fail('RESTORE_NOT_APPROVED_OR_CHANGED');const tx=db.transaction([RECORDS,META,BLOBS,TOMBSTONES],'readwrite'),recordsStore=tx.objectStore(RECORDS),metaStore=tx.objectStore(META),blobStore=tx.objectStore(BLOBS),tombStore=tx.objectStore(TOMBSTONES);let result;
  try{const [meta,currentRecords,currentBlobs]=await Promise.all([req(metaStore.get(META_KEY)),req(recordsStore.getAll()),req(blobStore.getAll())]);const current=meta?.revision??0;checkedRevision(current);if(current!==expectedRevision){tx.abort();fail('LIBRARY_REVISION_CONFLICT');}for(const r of prepared.records){if(await req(recordsStore.get(r.id))){tx.abort();fail('RESTORE_STALE_PLAN');}if(await req(tombStore.get(r.id))){tx.abort();fail('RESTORE_TOMBSTONED_ID');}}
    const combined=[...currentRecords,...prepared.records],desired=desiredBlobRefs(combined),revision=current+1;for(const r of prepared.records)recordsStore.add(r);writeBlobReconciliation(blobStore,currentBlobs,desired,prepared.candidates);metaStore.put({key:META_KEY,revision,updatedAt});result={revision,updatedAt,added:prepared.records.length,blobCount:desired.size};}catch(error){try{tx.abort();}catch{}throw error;}await done(tx);return result;
}

export async function clearLibrary(db,expectedRevision,{updatedAt=new Date().toISOString()}={}){checkedRevision(expectedRevision);const tx=db.transaction([RECORDS,META,BLOBS,TOMBSTONES],'readwrite'),recordsStore=tx.objectStore(RECORDS),metaStore=tx.objectStore(META),blobStore=tx.objectStore(BLOBS),tombStore=tx.objectStore(TOMBSTONES);let result;try{const [meta,currentRecords]=await Promise.all([req(metaStore.get(META_KEY)),req(recordsStore.getAll())]);const current=meta?.revision??0;if(current!==expectedRevision){tx.abort();fail('LIBRARY_REVISION_CONFLICT');}const revision=current+1;for(const r of currentRecords)tombStore.put({id:r.id,deletedAt:updatedAt,revision});recordsStore.clear();blobStore.clear();metaStore.put({key:META_KEY,revision,updatedAt});result={revision,updatedAt,count:0,blobCount:0};}catch(error){try{tx.abort();}catch{}throw error;}await done(tx);return result;}

export async function importLegacyOnce(db,legacyRecords){checkedRecords(legacyRecords);const current=await readLibrary(db);if(current.records.length||current.revision!==0)return {...current,migrated:false};if(!legacyRecords.length)return {...current,migrated:false};const committed=await replaceLibrary(db,0,legacyRecords);const state=await readLibrary(db);return {...state,migrated:true,blobCount:committed.blobCount};}

export async function storageStats(db){const tx=db.transaction([RECORDS,BLOBS,TOMBSTONES,META],'readonly');const [records,blobs,tombstones,meta]=await Promise.all([req(tx.objectStore(RECORDS).count()),req(tx.objectStore(BLOBS).getAll()),req(tx.objectStore(TOMBSTONES).count()),req(tx.objectStore(META).get(META_KEY))]);await done(tx);return {records,blobs:blobs.length,blobBytes:blobs.reduce((n,b)=>n+(Number.isSafeInteger(b.size)?b.size:0),0),tombstones,revision:meta?.revision??0};}

export const IDB_LIBRARY={DB_NAME,DB_VERSION,RECORDS,META,BLOBS,TOMBSTONES,META_KEY};
