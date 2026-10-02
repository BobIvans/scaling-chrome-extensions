import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {PassThrough} from 'node:stream';
import os from 'node:os';
import path from 'node:path';
import {JobHost} from './host.mjs';
import {
 QualificationBridge,
 qualificationEnvironment,
 QUALIFICATION_OUTPUT_BYTES,
} from './qualification.mjs';

const ref={source_id:'chat:goal',version:'2026-10-02',sha256:'d'.repeat(64)};
const message=(extra={})=>({type:'qualification.inspect',taskId:'qualification-001',text:'Проверь готовность бота',sourceRefs:[ref],...extra});
function fakeSpawn(effect){return (exe,args,opts)=>{const child=new EventEmitter();child.stdin=new PassThrough();child.stdout=new PassThrough();child.stderr=new PassThrough();child.kill=()=>{child.killed=true;setImmediate(()=>child.emit('close',null));return true;};child.stdin.on('finish',()=>effect?.(child,exe,args,opts));return child;};}
const config={enabled:true,pythonPath:path.resolve('/python'),adapterPath:path.resolve('/adapter.py'),profilePath:path.resolve('/profile.json')};

function validResult(){return {ok:true,result:{schema:'occ.native-qualification-result.v1',request_id:'qualification-001',action_id:'qualify_and_report',domain_verdict:'BLOCKED',reason_codes:['admission:RUNTIME_ADMISSION_BLOCKED'],next_blocker:'admission:RUNTIME_ADMISSION_BLOCKED',source_refs:[ref],occ_sha:'a'.repeat(40),bot_sha:'b'.repeat(40),qualified:false,release_authorized:false,live_authorized:false,transactions_sent:0,replayed:false}};}

test('qualification bridge is disabled by default and requires absolute operator paths',async()=>{
 const bridge=new QualificationBridge();await assert.rejects(bridge.handle(message()),/QUALIFICATION_UNAVAILABLE/);bridge.close();
 for(const [key,value] of [['pythonPath','python'],['adapterPath','adapter.py'],['profilePath','profile.json']])assert.throws(()=>new QualificationBridge({...config,[key]:value}),/OPERATOR_CONFIG/);
});

test('JobHost advertises qualification only after explicit operator opt-in',async()=>{
 const disabled=new JobHost({dataRoot:os.tmpdir(),codexPath:'not-used'});
 assert.equal((await disabled.handle({type:'hello'})).qualificationCommands,undefined);
 await disabled.close();
 const host=new JobHost(
  {dataRoot:os.tmpdir(),codexPath:'not-used',qualificationCore:config},
  {qualificationSpawnProcess:fakeSpawn(child=>{child.stdout.end(JSON.stringify(validResult()));child.emit('close',0);})},
 );
 assert.deepEqual((await host.handle({type:'hello'})).qualificationCommands,['qualification.inspect']);
 assert.equal((await host.handle(message())).qualification.domain_verdict,'BLOCKED');
 await host.close();
});

test('native request cannot inject paths, argv, actions or ambiguous text',async()=>{
 let calls=0;const bridge=new QualificationBridge(config,{spawnProcess:fakeSpawn(()=>calls++)});
 for(const extra of [{repoRoot:'/tmp'},{argv:['sh']},{actionId:'trade.live'},{text:'Не проверь готовность бота'},{taskId:'../escape'},{sourceRefs:[{...ref,sha256:'bad'}]}])await assert.rejects(bridge.handle(message(extra)),/QUALIFICATION_/);
 assert.equal(calls,0);bridge.close();
});

test('subprocess transport pins argv, strips secrets and returns BLOCKED as data',async()=>{
 let input;const bridge=new QualificationBridge(config,{spawnProcess:fakeSpawn((child,exe,args,opts)=>{
  assert.equal(exe,config.pythonPath);assert.deepEqual(args,['-I','-X','utf8',config.adapterPath,'--profile',config.profilePath]);assert.equal(opts.shell,false);assert.equal(opts.env.OPENAI_API_KEY,undefined);
  child.stdin.on('data',b=>{input=Buffer.concat([input||Buffer.alloc(0),b]);});
  child.stdout.end(JSON.stringify(validResult()));child.emit('close',0);
 })});
 const result=await bridge.handle(message());assert.equal(result.qualification.domain_verdict,'BLOCKED');
 const parsed=JSON.parse(input.toString('utf8'));assert.equal(parsed.schema,'occ.native-qualification-request.v1');assert.equal(parsed.task_id,'qualification-001');assert.deepEqual(parsed.source_refs,[ref]);bridge.close();
});

test('authority expansion in child response is rejected',async()=>{
 for(const change of [{live_authorized:true},{qualified:true},{transactions_sent:1},{domain_verdict:'PROFITABLE'}]){
  const payload=validResult();Object.assign(payload.result,change);
  const bridge=new QualificationBridge(config,{spawnProcess:fakeSpawn(child=>{child.stdout.end(JSON.stringify(payload));child.emit('close',0);})});
  await assert.rejects(bridge.handle(message()),/QUALIFICATION_RESULT_SCHEMA/);bridge.close();
 }
});

test('generic adapter failure remains a bounded native error',async()=>{
 const bridge=new QualificationBridge(config,{spawnProcess:fakeSpawn(child=>{child.stdout.end(JSON.stringify({ok:false,error:'QUALIFICATION_REQUEST_FAILED'}));child.emit('close',2);})});
 await assert.rejects(bridge.handle(message()),/^Error: QUALIFICATION_REQUEST_FAILED$/);bridge.close();
});

test('secret filtering and output limit are fail closed',async()=>{
 assert.deepEqual(qualificationEnvironment({PATH:'tools',SystemRoot:'system',OPENAI_API_KEY:'secret',HF_TOKEN:'secret',PYTHONPATH:'bad'}),{PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PATH:'tools',SystemRoot:'system'});
 let child;const bridge=new QualificationBridge(config,{spawnProcess:fakeSpawn(c=>{child=c;c.stderr.write(Buffer.alloc(QUALIFICATION_OUTPUT_BYTES+1));})});
 await assert.rejects(bridge.handle(message()),/^Error: QUALIFICATION_OUTPUT_LIMIT$/);assert.equal(child.killed,true);bridge.close();
});

test('disconnect kills pending qualification process and settles immediately',async()=>{
 let killed=false;
 const bridge=new QualificationBridge(config,{spawnProcess:()=>{const child=new EventEmitter();child.stdin=new PassThrough();child.stdout=new PassThrough();child.stderr=new PassThrough();child.kill=()=>{killed=true;return true;};return child;}});
 const pending=assert.rejects(bridge.handle(message()),/^Error: CLOSED$/);bridge.close();await pending;assert.equal(killed,true);
});
