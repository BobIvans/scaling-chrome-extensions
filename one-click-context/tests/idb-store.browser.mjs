import {openLibraryDB,readLibrary,replaceLibrary,mergeRestore,clearLibrary,restorePlanHash,IDB_LIBRARY} from '../library/idb-store.mjs';

const assert=(value,message='assertion failed')=>{if(!value)throw Error(message);};
const record=(id,text=id)=>({id,name:id,text,source:'fixture',status:'EXTRACTED',warnings:[],project:'p',session:'s',savedAt:'2026-09-09T00:00:00.000Z',createdAt:'2026-09-09T00:00:00.000Z',capturedAt:null,sha256:'a'.repeat(64)});

export async function runIDBQualification(){
  await new Promise((resolve,reject)=>{const d=indexedDB.deleteDatabase(IDB_LIBRARY.DB_NAME);d.onsuccess=()=>resolve();d.onerror=()=>reject(d.error);d.onblocked=()=>reject(Error('DELETE_BLOCKED'));});
  const a=await openLibraryDB(),b=await openLibraryDB();assert(a!==b,'connections must be independent');
  let state=await readLibrary(a);assert(state.revision===0&&state.records.length===0,'empty baseline');
  const first=await replaceLibrary(a,0,[record('one')]);assert(first.revision===1,'first revision');
  const race=await Promise.allSettled([replaceLibrary(a,1,[record('one'),record('two')]),replaceLibrary(b,1,[record('one'),record('three')])]);
  assert(race.filter(x=>x.status==='fulfilled').length===1,'one writer must win');
  assert(race.filter(x=>x.status==='rejected').length===1,'one stale writer must fail');
  state=await readLibrary(b);assert(state.revision===2&&state.records.length===2,'winner persisted');
  const existingIds=new Set(state.records.map(r=>r.id));const addId=existingIds.has('two')?'three':'two';
  const plan={adds:[record('restore-'+addId)],duplicates:[],conflicts:[]},planHash=await restorePlanHash(2,plan);
  let badApproval=false;try{await mergeRestore(a,2,plan,'0'.repeat(64));}catch(e){badApproval=e.code==='RESTORE_NOT_APPROVED_OR_CHANGED';}assert(badApproval,'wrong plan hash rejected');
  const merged=await mergeRestore(a,2,plan,planHash);assert(merged.revision===3,'restore revision');
  const before=await readLibrary(b);let conflict=false;const conflictPlan={adds:[],duplicates:[],conflicts:[{id:'one'}]};try{await mergeRestore(b,3,conflictPlan,await restorePlanHash(3,conflictPlan));}catch(e){conflict=e.code==='RESTORE_CONFLICT';}assert(conflict,'restore conflicts must fail');
  const after=await readLibrary(a);assert(JSON.stringify(before)===JSON.stringify(after),'failed restore must not mutate');
  let stale=false;const stalePlan={adds:[record('stale')],duplicates:[],conflicts:[]};try{await mergeRestore(a,2,stalePlan,await restorePlanHash(2,stalePlan));}catch(e){stale=e.code==='LIBRARY_REVISION_CONFLICT';}assert(stale,'stale restore revision rejected');
  const cleared=await clearLibrary(b,3);assert(cleared.revision===4,'clear revision');state=await readLibrary(a);assert(state.records.length===0,'clear persisted');
  a.close();b.close();const reopened=await openLibraryDB();state=await readLibrary(reopened);assert(state.revision===4&&state.records.length===0,'restart durable state');reopened.close();
  return {pass:9,revision:state.revision};
}
