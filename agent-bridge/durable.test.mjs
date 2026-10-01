import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {EventEmitter} from 'node:events';
import {PassThrough} from 'node:stream';
import {JobHost} from './host.mjs';
import {DurableBridge,durableEnvironment,DURABLE_OUTPUT_BYTES,DURABLE_TIMEOUT_MS} from './durable.mjs';

const lab=fileURLToPath(new URL('../content-lab/',import.meta.url));
const discovered=spawnSync(process.platform==='win32'?'python':'python3',['-I','-c','import sys; print(sys.executable)'],{encoding:'utf8',shell:false});
if(discovered.status!==0)throw Error('Python 3.11+ required for real durable bridge tests');
const python=discovered.stdout.trim();
function runPython(code,args=[]){const result=spawnSync(python,['-I','-X','utf8','-c',code,lab,...args],{encoding:'utf8',shell:false,env:durableEnvironment()});assert.equal(result.status,0,result.stderr);return result.stdout.trim();}
async function fixture(t){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'occ-durable-test-'));
 const source=path.join(root,'source'),privateSource=path.join(root,'private'),store=path.join(root,'store');
 await fs.mkdir(source);await fs.mkdir(privateSource);
 await fs.writeFile(path.join(source,'note.md'),'Public needle context. Привет 👋\r\n');
 await fs.writeFile(path.join(privateSource,'hidden.md'),'Private needle context.');
 const policy={schema:'occ.automation-policy.v1',max_parallel:1,money_budget:0,sources:{docs:{namespace:'docs',root:source},hidden:{namespace:'private',root:privateSource}},repos:{}};
 const policyPath=path.join(root,'policy.json'),profilePath=path.join(root,'native-profile.json');
 const profile={schema:'occ.native-durable-profile.v1',store,policy_file:policyPath,namespaces:['docs'],templates:{syncDocs:{kind:'sync',source_profile:'docs'}}};
 await fs.writeFile(policyPath,JSON.stringify(policy));await fs.writeFile(profilePath,JSON.stringify(profile));
 const hidden=runPython('import sys,json; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from automation_core import sync,enqueue; store=Path(sys.argv[2]); policy=json.loads(Path(sys.argv[3]).read_text()); sync(store,"docs",Path(policy["sources"]["docs"]["root"])); sync(store,"private",Path(policy["sources"]["hidden"]["root"])); print(json.dumps(enqueue(store,policy,"hidden-task",{"kind":"sync","source_profile":"hidden"})))',[store,policyPath]);
 const config={dataRoot:path.join(root,'ephemeral'),codexPath:'not-invoked',durableCore:{enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath}};
 const hosts=[];const host=()=>{const value=new JobHost(config);hosts.push(value);return value;};
 t.after(async()=>{for(const value of hosts)await value.close();await fs.rm(root,{recursive:true,force:true});});
 return {root,source,store,policy,profile,policyPath,profilePath,config,host,hiddenId:JSON.parse(hidden).id};
}
function fakeSpawn(effect){return (exe,args,opts)=>{const child=new EventEmitter();child.stdin=new PassThrough();child.stdout=new PassThrough();child.stderr=new PassThrough();child.kill=()=>{child.killed=true;setImmediate(()=>child.emit('close',null));return true;};child.stdin.on('finish',()=>effect?.(child,exe,args,opts));return child;};}

test('durable bridge is disabled by default and exposes only explicit opt-in capabilities',async()=>{
 const host=new JobHost({dataRoot:os.tmpdir(),codexPath:'not-used'});
 assert.equal((await host.handle({type:'hello'})).durableCommands,undefined);
 await assert.rejects(host.handle({type:'durable.search',namespace:'docs',query:'needle'}),/DURABLE_UNAVAILABLE/);
 await host.close();
 for(const pythonPath of ['python',123,null])assert.throws(()=>new DurableBridge({enabled:true,pythonPath,profilePath:'/profile',adapterPath:'/adapter'}),/DURABLE_OPERATOR_CONFIG_REQUIRED/);
});
test('actual JobHost uses scoped SQLite search/context with UTF-8 provenance',async t=>{
 const f=await fixture(t),host=f.host();assert.equal((await host.handle({type:'hello'})).durableCommands.length,5);
 const {durable}=await host.handle({type:'durable.search',namespace:'docs',query:'needle',limit:1,requestId:1});
 assert.equal(durable.items.length,1);assert.equal(durable.items[0].source_key,'note.md');
 const result=await host.handle({type:'durable.context',namespace:'docs',ids:[durable.items[0].id],maxBytes:1000});
 assert.equal(result.durable.context.namespace,'docs');assert.match(result.durable.context.items[0].text,/Привет 👋/);
 assert.equal(result.durable.context.authority,'source-content-not-action-instructions');
 assert.match(result.durable.context.sha256,/^[a-f0-9]{64}$/);
});
test('durable enqueue survives host disconnect/restart, replays once and persists cancel',async t=>{
 const f=await fixture(t),first=f.host();
 const created=(await first.handle({type:'durable.enqueue',template:'syncDocs',taskKey:'voice-001'})).durable.job;
 assert.equal(created.reused,false);await first.close();
 const second=f.host(),replayed=(await second.handle({type:'durable.enqueue',template:'syncDocs',taskKey:'voice-001'})).durable.job;
 assert.equal(replayed.id,created.id);assert.equal(replayed.reused,true);
 const job=(await second.handle({type:'durable.get',jobId:created.id})).durable.job;
 assert.equal(job.state,'QUEUED');assert.equal(job.attempt,0);
 for(const key of ['payload','checkpoint','result','policy_hash','lease_token'])assert.equal(job[key],undefined);
 const cancelled=(await second.handle({type:'durable.cancel',jobId:created.id})).durable.job;
 assert.equal(cancelled.state,'CANCELLED');assert.equal(cancelled.cancel_requested,true);
 assert.equal((await f.host().handle({type:'durable.get',jobId:created.id})).durable.job.state,'CANCELLED');
 assert.equal((await second.handle({type:'durable.enqueue',template:'syncDocs',taskKey:'voice-001'})).durable.job.state,'CANCELLED');
});
test('native template scope blocks same-policy CLI jobs and conflicting task keys',async t=>{
 const f=await fixture(t),host=f.host();
 for(const type of ['durable.get','durable.cancel'])await assert.rejects(host.handle({type,jobId:f.hiddenId}),/DURABLE_JOB_OUTSIDE_SCOPE/);
 await assert.rejects(host.handle({type:'durable.enqueue',template:'syncDocs',taskKey:'hidden-task'}),/TASK_KEY_CONTENT_CONFLICT/);
 await assert.rejects(host.handle({type:'durable.enqueue',template:'hidden',taskKey:'other'}),/DURABLE_TEMPLATE_OUTSIDE_SCOPE/);
});
test('namespace and current-head scope are enforced by actual core',async t=>{
 const f=await fixture(t),host=f.host();
 await assert.rejects(host.handle({type:'durable.search',namespace:'private',query:'needle'}),/DURABLE_NAMESPACE_OUTSIDE_SCOPE/);
 const id=(await host.handle({type:'durable.search',namespace:'docs',query:'needle'})).durable.items[0].id;
 await fs.writeFile(path.join(f.source,'note.md'),'Replacement content.');
 runPython('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from automation_core import sync; sync(Path(sys.argv[2]),"docs",Path(sys.argv[3]))',[f.store,f.source]);
 await assert.rejects(host.handle({type:'durable.context',namespace:'docs',ids:[id]}),/ITEM_OUTSIDE_SCOPE_OR_STALE/);
});
test('native requests cannot inject operator paths, commands, worker authority or integer coercions',async t=>{
 const f=await fixture(t),host=f.host();
 for(const override of [{policy:'/tmp/other'},{root:'/tmp'},{argv:['anything']},{profilePath:f.profilePath},{maxBytes:1},{payload:{kind:'sync'}}])await assert.rejects(host.handle({type:'durable.enqueue',template:'syncDocs',taskKey:'x',...override}),/DURABLE_SCHEMA/);
 await assert.rejects(host.handle({type:'durable.work'}),/DURABLE_SCHEMA/);
 await assert.rejects(host.handle({type:'durable.search',namespace:'docs',query:'needle',limit:true}),/INTEGER_LIMIT_REQUIRED/);
 await assert.rejects(host.handle({type:'durable.context',namespace:'docs',ids:['x']}),/DURABLE_ITEM_IDS_REQUIRED/);
 await assert.rejects(host.handle({type:'durable.get',jobId:'../../policy.json'}),/DURABLE_JOB_ID_REQUIRED/);
 await assert.rejects(host.handle({type:'durable.search',namespace:'docs',query:'👋'.repeat(5000)}),/DURABLE_INPUT_LIMIT/);
});
test('changed operator policy and removed native template cannot authorize an older job',async t=>{
 const f=await fixture(t),host=f.host();
 const id=(await host.handle({type:'durable.enqueue',template:'syncDocs',taskKey:'pinned-policy'})).durable.job.id;
 await fs.writeFile(f.profilePath,JSON.stringify({...f.profile,templates:{}}));
 await assert.rejects(host.handle({type:'durable.cancel',jobId:id}),/DURABLE_JOB_OUTSIDE_SCOPE/);
 await fs.writeFile(f.profilePath,JSON.stringify(f.profile));
 await fs.writeFile(f.policyPath,JSON.stringify({...f.policy,operator_revision:2}));
 await assert.rejects(host.handle({type:'durable.get',jobId:id}),/DURABLE_JOB_OUTSIDE_SCOPE/);
});
test('corrupt job payload binding is blocked and complete context JSON has a byte limit',async t=>{
 const f=await fixture(t),host=f.host();
 const id=(await host.handle({type:'durable.enqueue',template:'syncDocs',taskKey:'corrupt-binding'})).durable.job.id;
 runPython('import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from automation_core import connection; db=connection(Path(sys.argv[2])); db.execute("UPDATE jobs SET payload_hash=? WHERE id=?",("0"*64,sys.argv[3])); db.commit(); db.close()',[f.store,id]);
 await assert.rejects(host.handle({type:'durable.get',jobId:id}),/DURABLE_JOB_OUTSIDE_SCOPE/);
 const itemId=(await host.handle({type:'durable.search',namespace:'docs',query:'needle'})).durable.items[0].id;
 runPython('import sys,json; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from automation_core import connection; db=connection(Path(sys.argv[2])); item=json.loads(db.execute("SELECT payload FROM items WHERE id=?",(sys.argv[3],)).fetchone()[0]); item["segments"]=[{"text":"metadata"*1000}]*30; db.execute("UPDATE items SET payload=? WHERE id=?",(json.dumps(item),sys.argv[3])); db.commit(); db.close()',[f.store,itemId]);
 await assert.rejects(host.handle({type:'durable.context',namespace:'docs',ids:[itemId]}),/DURABLE_OUTPUT_LIMIT/);
});
test('subprocess transport strips secrets, pins isolated Python argv and never uses a shell',async()=>{
 assert.deepEqual(durableEnvironment({PATH:'tools',SystemRoot:'system',OPENAI_API_KEY:'secret',HF_TOKEN:'secret',PYTHONPATH:'untrusted',CODEX_THREAD_ID:'parent'}),{PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PATH:'tools',SystemRoot:'system'});
 const config={enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath:path.join(os.tmpdir(),'profile.json')};
 const bridge=new DurableBridge(config,{spawnProcess:fakeSpawn((child,exe,args,opts)=>{
  assert.equal(exe,python);assert.deepEqual(args,['-I','-X','utf8',config.adapterPath,'--profile',config.profilePath]);assert.equal(opts.shell,false);assert.equal(opts.windowsHide,true);
  child.stdout.end(JSON.stringify({ok:true,result:{schema:'occ.native-durable-result.v1',operation:'durable.get',job:{state:'QUEUED'}}}));child.emit('close',0);
 })});
 assert.equal((await bridge.handle({type:'durable.get',jobId:'0'.repeat(32)})).durable.job.state,'QUEUED');bridge.close();
});
test('output and stderr limits kill child without forwarding untrusted logs',async()=>{
 const config={enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath:path.join(os.tmpdir(),'profile.json')};
 for(const stream of ['stdout','stderr']){let child;const bridge=new DurableBridge(config,{spawnProcess:fakeSpawn(c=>{child=c;c[stream].write(Buffer.alloc(DURABLE_OUTPUT_BYTES+1));})});await assert.rejects(bridge.handle({type:'durable.get',jobId:'0'.repeat(32)}),/^Error: DURABLE_OUTPUT_LIMIT$/);assert.equal(child.killed,true);bridge.close();}
});
test('invalid UTF-8/JSON/schema and process failure never produce a durable success',async()=>{
 const config={enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath:path.join(os.tmpdir(),'profile.json')};
 for(const [bytes,code] of [[Buffer.from([255]),0],[Buffer.from('{'),0],[Buffer.from('{"ok":true,"result":{}}'),0],[Buffer.from('private exception details'),1]]){
  const bridge=new DurableBridge(config,{spawnProcess:fakeSpawn(child=>{child.stdout.end(bytes);child.emit('close',code);})});await assert.rejects(bridge.handle({type:'durable.get',jobId:'0'.repeat(32)}),/DURABLE_/);bridge.close();
 }
});
test('timeout settles even if child refuses to acknowledge termination',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});let killed=false;
 const bridge=new DurableBridge({enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath:path.join(os.tmpdir(),'profile.json')},{spawnProcess:()=>{const child=new EventEmitter();child.stdin=new PassThrough();child.stdout=new PassThrough();child.stderr=new PassThrough();child.kill=()=>{killed=true;return true;};return child;}});
 const pending=assert.rejects(bridge.handle({type:'durable.get',jobId:'0'.repeat(32)}),/DURABLE_TIMEOUT/);t.mock.timers.tick(DURABLE_TIMEOUT_MS);await pending;assert.equal(killed,true);bridge.close();
});
test('disconnect kills a pending adapter and settles without waiting for process close',async()=>{
 let killed=false;
 const bridge=new DurableBridge({enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath:path.join(os.tmpdir(),'profile.json')},{spawnProcess:()=>{const child=new EventEmitter();child.stdin=new PassThrough();child.stdout=new PassThrough();child.stderr=new PassThrough();child.kill=()=>{killed=true;return true;};return child;}});
 const pending=assert.rejects(bridge.handle({type:'durable.get',jobId:'0'.repeat(32)}),/^Error: CLOSED$/);bridge.close();await pending;assert.equal(killed,true);assert.equal(bridge.children.size,0);
});
