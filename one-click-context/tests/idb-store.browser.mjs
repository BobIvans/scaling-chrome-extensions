import {openLibraryDB,readLibrary,replaceLibrary,mergeRestore,clearLibrary,restorePlanHash,readOriginal,storageStats,IDB_LIBRARY} from '../library/idb-store.mjs';

const assert=(value,message='assertion failed')=>{if(!value)throw Error(message);};
const record=(id,text=id)=>({id,name:id,text,source:'fixture',status:'EXTRACTED',warnings:[],project:'p',session:'s',savedAt:'2026-09-09T00:00:00.000Z',createdAt:'2026-09-09T00:00:00.000Z',capturedAt:null,sha256:'a'.repeat(64)});
const original=(id)=>({...record(id),original:[1,2,3,4,5]});

export async function runIDBQualification(){
  await new Promise((resolve,reject)=>{const d=indexedDB.deleteDatabase(IDB_LIBRARY.DB_NAME);d.onsuccess=()=>resolve();d.onerror=()=>reject(d.error);d.onblocked=()=>reject(Error('DELETE_BLOCKED'));});
  const a=await openLibraryDB(),b=await openLibraryDB();assert(a!==b,'connections must be independent');
  let state=await readLibrary(a);assert(state.revision===0&&state.records.length===0,'empty baseline');
  const first=await replaceLibrary(a,0,[record('one')]);assert(first.revision===1,'first revision');
  const race=await Promise.allSettled([replaceLibrary(a,1,[record('one'),record('two')]),replaceLibrary(b,1,[record('one'),record('three')])]);
  assert(race.filter(x=>x.status==='fulfilled').length===1,'one writer must win');assert(race.filter(x=>x.status==='rejected').length===1,'one stale writer must fail');
  state=await readLibrary(b);assert(state.revision===2&&state.records.length===2,'winner persisted');
  const existingIds=new Set(state.records.map(r=>r.id)),addId=existingIds.has('two')?'three':'two';
  const plan={adds:[record('restore-'+addId)],duplicates:[],conflicts:[]},planHash=await restorePlanHash(2,plan);
  let badApproval=false;try{await mergeRestore(a,2,plan,'0'.repeat(64));}catch(e){badApproval=e.code==='RESTORE_NOT_APPROVED_OR_CHANGED';}assert(badApproval,'wrong plan hash rejected');
  const merged=await mergeRestore(a,2,plan,planHash);assert(merged.revision===3,'restore revision');
  const before=await readLibrary(b);let conflict=false;const conflictPlan={adds:[],duplicates:[],conflicts:[{id:'one'}]};try{await mergeRestore(b,3,conflictPlan,await restorePlanHash(3,conflictPlan));}catch(e){conflict=e.code==='RESTORE_CONFLICT';}assert(conflict,'restore conflicts must fail');
  const after=await readLibrary(a);assert(JSON.stringify(before)===JSON.stringify(after),'failed restore must not mutate');
  let stale=false;const stalePlan={adds:[record('stale')],duplicates:[],conflicts:[]};try{await mergeRestore(a,2,stalePlan,await restorePlanHash(2,stalePlan));}catch(e){stale=e.code==='LIBRARY_REVISION_CONFLICT';}assert(stale,'stale restore revision rejected');

  state=await readLibrary(a);const base=state.records;
  let saved=await replaceLibrary(a,3,[...base,original('blob-a'),original('blob-b')]);assert(saved.revision===4,'blob save revision');
  let stats=await storageStats(b);assert(stats.blobs===1&&stats.blobBytes===5,'identical originals deduplicated');
  state=await readLibrary(a);const blobA=state.records.find(r=>r.id==='blob-a');assert(blobA.originalRef&&blobA.original===undefined,'record stores ref not byte array');
  assert(Array.from(await readOriginal(b,blobA)).join(',')==='1,2,3,4,5','original bytes roundtrip');

  saved=await replaceLibrary(b,4,state.records.filter(r=>r.id!=='blob-a'));assert(saved.revision===5,'first blob ref removal');stats=await storageStats(a);assert(stats.blobs===1,'shared blob retained while referenced');
  state=await readLibrary(a);saved=await replaceLibrary(a,5,state.records.filter(r=>r.id!=='blob-b'));assert(saved.revision===6,'last blob ref removal');stats=await storageStats(b);assert(stats.blobs===0&&stats.tombstones>=2,'unreferenced blob collected and tombstones retained');
  const resurrect={adds:[original('blob-a')],duplicates:[],conflicts:[]};let tombstoned=false;try{await mergeRestore(a,6,resurrect,await restorePlanHash(6,resurrect));}catch(e){tombstoned=e.code==='RESTORE_TOMBSTONED_ID';}assert(tombstoned,'old backup cannot resurrect tombstoned id');

  const cleared=await clearLibrary(b,6);assert(cleared.revision===7,'clear revision');state=await readLibrary(a);assert(state.records.length===0,'clear persisted');
  a.close();b.close();const reopened=await openLibraryDB();state=await readLibrary(reopened);stats=await storageStats(reopened);assert(state.revision===7&&state.records.length===0&&stats.blobs===0,'restart durable state');reopened.close();
  return {pass:15,revision:state.revision,tombstones:stats.tombstones};
}
