import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizedRecord,filterRecords,facets,restorePlan,applyRestorePlan} from '../library/workspace.mjs';
const base={id:'1',name:'a',text:'hello',source:'local',status:'EXTRACTED',warnings:[],createdAt:'2026-09-09T01:00:00Z',sha256:'a'.repeat(64)};
test('migrates legacy createdAt and assigns project/session',()=>{const r=normalizedRecord(base,{defaultProject:'P',defaultSession:'S'});assert.equal(r.project,'P');assert.equal(r.session,'S');assert.equal(r.savedAt,'2026-09-09T01:00:00.000Z');});
test('filters by project session date and text',()=>{const a=normalizedRecord({...base,project:'A',session:'s'}),b=normalizedRecord({...base,id:'2',project:'B',session:'x',text:'other',createdAt:'2026-09-10T01:00:00Z'});assert.deepEqual(filterRecords([a,b],{project:'A',session:'s',from:'2026-09-09',to:'2026-09-09',query:'HELLO'}).map(x=>x.id),['1']);});
test('facets are deterministic',()=>{const a=normalizedRecord({...base,project:'B',session:'z'}),b=normalizedRecord({...base,id:'2',project:'A',session:'a'});assert.deepEqual(facets([a,b]),{projects:['A','B'],sessions:['a','z']});});
test('restore preserves IDs and separates duplicates/conflicts',()=>{const a=normalizedRecord(base),dup=normalizedRecord(base),conflict=normalizedRecord({...base,text:'changed',sha256:'b'.repeat(64)}),newer=normalizedRecord({...base,id:'2'});const p=restorePlan([a],[dup,newer]);assert.deepEqual(p.duplicates,['1']);assert.equal(applyRestorePlan([a],p).length,2);assert.equal(restorePlan([a],[conflict]).conflicts.length,1);});
