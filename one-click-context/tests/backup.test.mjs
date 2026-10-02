import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
import {makeBackup,planRestore,serializePersistentLibrary,sha256} from '../library/backup-core.mjs';

function record(overrides={}){return {id:'r1',name:'chat.txt',text:'hello\nмир\n',source:'ChatGPT',status:'BEST_EFFORT',createdAt:'2026-09-09T00:00:00.000Z',warnings:['partial source'],...overrides};}

test('backup roundtrip preserves ids dates provenance and hash',async()=>{
 const input=[record({original:[1,2,3]})];
 const backup=await makeBackup(input,{includeOriginals:true});
 assert.equal(backup.kind,'occ-library-backup');
 assert.equal(backup.version,2);
 assert.equal(backup.records[0].id,'r1');
 assert.deepEqual(backup.records[0].original,[1,2,3]);
 assert.equal(backup.records[0].sha256,await sha256(input[0].text));
 const plan=await planRestore([],backup);
 assert.equal(plan.ok,true);assert.equal(plan.additions.length,1);assert.equal(plan.merged[0].id,'r1');
});

test('same id and same semantic record is skipped',async()=>{
 const current=[{...record(),sha256:await sha256(record().text)}];
 const backup=await makeBackup(current);
 const plan=await planRestore(current,backup);
 assert.equal(plan.ok,true);assert.equal(plan.additions.length,0);assert.equal(plan.skipped.length,1);
});

test('same id with changed text blocks the entire restore',async()=>{
 const current=[{...record(),sha256:await sha256(record().text)}];
 const incoming=[record({text:'changed'})];
 const backup=await makeBackup(incoming);
 const plan=await planRestore(current,backup);
 assert.equal(plan.ok,false);assert.equal(plan.conflicts.length,1);assert.equal(plan.merged,null);
});

test('tampered text hash is rejected',async()=>{
 const backup=await makeBackup([record()]);
 backup.records[0].text='tampered';
 await assert.rejects(()=>planRestore([],backup),/SHA-256/);
});

test('backup without originals omits raw bytes',async()=>{
 const backup=await makeBackup([record({original:[9,8,7]})],{includeOriginals:false});
 assert.equal('original' in backup.records[0],false);
});

test('persistent serializer writes the project/session-aware version 2 model',async()=>{
 const rec={...record(),sha256:await sha256(record().text)};
 const normalized=(await planRestore([],await makeBackup([rec]))).merged;
 const parsed=JSON.parse(serializePersistentLibrary(normalized));
 assert.equal(parsed.version,2);assert.equal(parsed.records[0].id,'r1');assert.equal(parsed.records[0].project,'Inbox');assert.equal(parsed.records[0].session,'');
});

test('tampered project/session metadata is rejected by the backup payload hash',async()=>{
 const backup=await makeBackup([record({project:'Research',session:'day-1'})]);
 backup.records[0].session='day-2';
 await assert.rejects(()=>planRestore([],backup),/резервной копии/);
});

test('backup preserves project/session and treats metadata drift as an ID conflict',async()=>{
 const current=[{...record({project:'Research',session:'day-1'}),sha256:await sha256(record().text)}];
 const backup=await makeBackup([{...current[0],session:'day-2'}]);
 const plan=await planRestore(current,backup);
 assert.equal(plan.ok,false);assert.equal(plan.conflicts.length,1);
});
