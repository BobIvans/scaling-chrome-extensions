// Explicit smoke test against a prepared native executable. --live spends a small Codex request.
import {spawn} from 'node:child_process';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {decoder,encodeFrame} from './host.mjs';
const directory=path.resolve(process.argv[2]);const live=process.argv.includes('--live');
const extensionId=process.env.OCC_TEST_EXTENSION_ID||'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';if(!/^[a-p]{32}$/.test(extensionId))throw Error('Invalid extension ID');
const child=spawn(path.join(directory,'occ-native-host.exe'),[`chrome-extension://${extensionId}/`],{windowsHide:true,shell:false,stdio:['pipe','pipe','pipe']});
const pending=new Map();let ended=false;
child.stdout.on('data',decoder(m=>{const p=pending.get(m.requestId);if(p){clearTimeout(p.timer);pending.delete(m.requestId);m.ok?p.resolve(m):p.reject(Error(m.error));}},e=>{throw e;}));
child.on('close',code=>{ended=true;for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Host exited '+code));}});
const request=(type,args={})=>new Promise((resolve,reject)=>{if(ended)return reject(Error('Host ended'));const requestId=randomUUID(),timer=setTimeout(()=>reject(Error('Native response timeout')),20000);pending.set(requestId,{resolve,reject,timer});child.stdin.write(encodeFrame({requestId,type,...args}));});
try{
 const hello=await request('hello');if(hello.version!==1)throw Error('version');console.log('PASS native executable framing and exact-origin handshake');
 if(live){const text=Buffer.from('Synthetic integration fixture. No private browser data.');const {job}=await request('begin',{instruction:'Return exactly OCC_AGENT_SMOKE_OK. Do not use any tools.',mode:'analyze',bytes:text.length,sha256:createHash('sha256').update(text).digest('hex')});await request('append',{jobId:job.id,offset:0,base64:text.toString('base64')});await request('run',{jobId:job.id});let complete=false;
  for(let i=0;i<90;i++){const {jobs}=await request('list');const j=jobs.find(x=>x.id===job.id);if(j.state==='FAILED')throw Error(j.error);if(j.state==='COMPLETE'){const r=await request('result',{jobId:job.id,offset:0});const answer=Buffer.from(r.base64,'base64').toString('utf8');if(answer.trim()!=='OCC_AGENT_SMOKE_OK')throw Error('Unexpected response');complete=true;console.log('PASS real Codex ChatGPT-auth synthetic job and returned TXT');break;}await new Promise(r=>setTimeout(r,2000));}
  await request('discard',{jobId:job.id});if(!complete)throw Error('Live test timeout');console.log('PASS explicit job discard');
 }
}finally{child.stdin.end();setTimeout(()=>child.kill(),5000).unref();}
