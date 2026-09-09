import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const core=await import('../library/bundle-core.mjs');

test('split/rejoin preserves unicode exactly',async()=>{
  const text=('Привет🙂\nкод\\_+-\n').repeat(12000);
  const out=await core.splitBundle(text,{partBytes:20000});
  assert.ok(out.payloads.length>1);
  assert.equal(core.rejoin(out.payloads),text);
  assert.equal(out.totalBytes,core.byteLength(text));
  for(const p of out.payloads)assert.ok(p.bytes<=20000);
});

test('manifest hashes identify whole and parts',async()=>{
  const text='a'.repeat(40000)+'\n\n=== SOURCE B ===\n'+'б'.repeat(30000);
  const out=await core.splitBundle(text,{partBytes:16000,label:'test'});
  assert.equal(out.wholeSha256,await core.sha256(text));
  assert.deepEqual(out.parts.map(x=>x.index),out.payloads.map(x=>x.index));
  for(const p of out.payloads)assert.equal(p.sha256,await core.sha256(p.text));
});

test('invalid budgets and sequences fail closed',async()=>{
  await assert.rejects(()=>core.splitBundle('abc',{partBytes:100}),/Размер части/);
  assert.throws(()=>core.rejoin([{index:2,text:'x'}]),/последовательность/);
});

test('parts never split a UTF-16 surrogate pair and preserve exported UTF-8 bytes',async()=>{
  const text='a'.repeat(15999)+'🙂tail';
  const out=await core.splitBundle(text,{partBytes:16002});
  const joinedBytes=Buffer.concat(out.payloads.map(part=>Buffer.from(part.text,'utf8')));
  assert.deepEqual(joinedBytes,Buffer.from(text,'utf8'));
});
