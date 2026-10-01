import {test} from 'node:test';
import assert from 'node:assert/strict';
import {libraryMutation,LIBRARY_RECORD_SCHEMA,MAX_NATIVE_RECORD_TEXT_BYTES} from '../library-store.mjs';

const record={id:'record-1',name:'Roadmap',text:'selected source',source:'Chrome library',
 status:'EXTRACTED',warnings:['fixture provenance'],savedAt:'2026-10-01T10:00:00.000Z',
 capturedAt:'2026-09-30T09:00:00.000Z',project:'OCC',session:'wave-18'};

test('Chrome record schema preserves provenance and explicit revision parent',async()=>{
 const mutation=await libraryMutation(record,{namespace:'docs',revision:1,parentRevision:null});
 assert.equal(mutation.schema,LIBRARY_RECORD_SCHEMA);assert.equal(mutation.sourceKey,record.id);
 assert.equal(mutation.content.text,record.text);assert.match(mutation.content.sha256,/^[0-9a-f]{64}$/);
 assert.deepEqual(mutation.provenance,{source:record.source,savedAt:record.savedAt,
  capturedAt:record.capturedAt,status:record.status,warnings:record.warnings,
  project:record.project,session:record.session});
});

test('tombstone carries provenance but never source content',async()=>{
 const mutation=await libraryMutation(record,{namespace:'docs',revision:2,parentRevision:1,tombstone:true});
 assert.equal(mutation.tombstone,true);assert.equal(mutation.content,null);
 assert.equal(mutation.provenance.source,'Chrome library');
});

test('schema rejects implicit lineage, tampering and oversized native records',async()=>{
 await assert.rejects(libraryMutation(record,{namespace:'docs',revision:2,parentRevision:null}),/REVISION/);
 await assert.rejects(libraryMutation({...record,sha256:'0'.repeat(64)},{namespace:'docs',revision:1,parentRevision:null}),/CONTENT_HASH/);
 await assert.rejects(libraryMutation({...record,text:'x'.repeat(MAX_NATIVE_RECORD_TEXT_BYTES+1)},{namespace:'docs',revision:1,parentRevision:null}),/TEXT_LIMIT/);
});
