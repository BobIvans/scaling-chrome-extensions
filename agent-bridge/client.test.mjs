import {test} from 'node:test';
import assert from 'node:assert/strict';
import {NativeClient} from '../one-click-context/library/agent.mjs';
import {JobHost} from './host.mjs';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
function port(reply){let listener;return {onMessage:{addListener:f=>listener=f},onDisconnect:{addListener(){}},postMessage(m){queueMicrotask(async()=>{try{listener({requestId:m.requestId,ok:true,...await reply(m)});}catch(e){listener({requestId:m.requestId,ok:false,error:e.message});}});},disconnect(){}};}
test('client close rejects pending calls without waiting for Chrome disconnect event',async()=>{const p=port(()=>new Promise(()=>{}));const c=new NativeClient(p);const request=c.request('hello');c.close();await assert.rejects(request,/закрыто/);await assert.rejects(c.request('list'),/закрыто/);});
test('client submits exact multichunk Cyrillic UTF-8 through production host',async()=>{const directory=await mkdtemp(path.join(os.tmpdir(),'occ-client-test-'));const host=new JobHost({dataRoot:directory});host.pump=async()=>{};const c=new NativeClient(port(m=>host.handle(m)));try{const text='Привет 👋\r\n  x_y\\z +/-\n'.repeat(4000);const id=await c.submit('Summarize',text,'analyze');const j=host.jobs.get(id);assert.equal(j.state,'QUEUED');const {readFile}=await import('node:fs/promises');assert.equal(await readFile(path.join(j.directory,'input.txt'),'utf8'),text);await assert.rejects(c.request('run',{jobId:id}),/ALREADY/);}finally{c.close();await host.close();await rm(directory,{recursive:true});}});
test('client rejects result bytes with incorrect SHA-256',async()=>{const c=new NativeClient(port(()=>({bytes:3,offset:0,sha256:'0'.repeat(64),base64:'YWJj'})));await assert.rejects(c.result('id'),/hash mismatch/);c.close();});
test('client rejects malformed result offset and oversize payload declaration',async()=>{for(const response of [{bytes:3,offset:1},{bytes:2200001,offset:0}]){const c=new NativeClient(port(()=>response));await assert.rejects(c.result('id'),/framing/);c.close();}});
