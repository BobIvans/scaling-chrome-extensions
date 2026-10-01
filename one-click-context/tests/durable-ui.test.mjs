import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {webcrypto} from 'node:crypto';
import {DurableSession,attachDurableView} from '../library/durable-ui.mjs';
import {NativeClient,attachAgent} from '../library/agent.mjs';
import {JobHost} from '../../agent-bridge/host.mjs';
globalThis.crypto??=webcrypto;
const commands=['durable.search','durable.context','durable.enqueue','durable.get','durable.cancel'];
const hello={version:1,durableCommands:commands};
const id='1'.repeat(32), item='2'.repeat(64);
const response=(op,fields)=>({durable:{schema:'occ.native-durable-result.v1',operation:op,...fields}});
const job=(state='QUEUED',extra={})=>({id,state,...extra});
function storage(){const data=new Map();return {data,getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};}
function setup(handler,cache=storage()){const calls=[],client={closed:false,request:async(type,args)=>{calls.push({type,args});return handler(type,args);}};const s=new DurableSession({storage:cache});s.connect(client,hello,'test:local');return {s,calls,client,cache};}
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}

test('legacy v1/malformed capabilities grant no durable authority',async()=>{
 for(const h of [{version:1},{version:1,durableCommands:'all'},{version:2,durableCommands:commands},{version:1,durableCommands:['shell.exec',{}]}]){
  let called=false;const s=new DurableSession({storage:storage()});s.connect({request(){called=true;}},h,'test');
  assert.equal(s.can('durable.enqueue'),false);await assert.rejects(s.enqueue('sync','key'),/DURABLE_UNAVAILABLE/);assert.equal(called,false);
 }
});
test('persist-before-dispatch prevents an effect when reference storage fails',async()=>{
 const {s,calls}=setup(()=>response('durable.enqueue',{job:job()}),{getItem:()=>null,setItem(){throw Error('QUOTA');}});
 await assert.rejects(s.enqueue('sync','same-key'),/QUOTA/);assert.equal(calls.length,0);
});
test('unknown committed enqueue survives reload and replays exactly the saved key',async()=>{
 let attempt=0;const cache=storage();
 const {s,calls}=setup((op)=>{if(attempt++===0)throw Error('Native host timeout');return response(op,{job:job('QUEUED',{reused:true})});},cache);
 await assert.rejects(s.enqueue('sync','goal-001'),/timeout/);
 const persisted=JSON.parse(cache.getItem('occ.durable.references.v1:test:local'));
 assert.deepEqual(persisted.refs,[{id:null,template:'sync',taskKey:'goal-001'}]);
 const restored=setup(op=>response(op,{job:job('QUEUED',{reused:true})}),cache);
 assert.equal(restored.s.refs[0].state,'UNKNOWN_COMMIT');await restored.s.enqueue('sync','goal-001');
 assert.deepEqual(restored.calls[0],calls[0]);assert.equal(restored.s.refs[0].id,id);
 assert.deepEqual(Object.keys(JSON.parse(cache.getItem('occ.durable.references.v1:test:local')).refs[0]).sort(),['id','taskKey','template']);
 await assert.rejects(restored.s.enqueue('different','goal-001'),/TASK_KEY_TEMPLATE_CONFLICT/);
});
test('disconnect/rebind ignores delayed enqueue and retains its old-scope intent',async()=>{
 const pending=deferred();const {s,client,cache}=setup(()=>pending.promise);
 const rejected=assert.rejects(s.enqueue('sync','key'),/STALE_DURABLE_REPLY/);
 s.connect(client,hello,'test:other');pending.resolve(response('durable.enqueue',{job:job()}));await rejected;
 assert.equal(s.refs.length,0);assert.equal(JSON.parse(cache.getItem('occ.durable.references.v1:test:local')).refs[0].id,null);
});
test('new search and input invalidation reject older replies and clear current context',async()=>{
 const first=deferred();let count=0;
 const {s}=setup(op=>++count===1?first.promise:response(op,{items:[{id:item,source_key:'new.md',snippet:'new'}]}));
 const stale=assert.rejects(s.search('docs','old'),/STALE_SEARCH_REPLY/);await s.search('docs','new');
 first.resolve(response('durable.search',{items:[{id:item,source_key:'old.md',snippet:'old'}]}));await stale;
 assert.equal(s.hits[0].source_key,'new.md');s.invalidateSearch();assert.deepEqual(s.hits,[]);
});
test('context has bounded selected IDs, namespace binding and unchanged error verdict',async()=>{
 const {s,calls}=setup(op=>op==='durable.search'?response(op,{items:[{id:item,source_key:'note.md',snippet:'needle'}]}):Promise.reject(Error('ITEM_OUTSIDE_SCOPE_OR_STALE')));
 await s.search('docs','needle');await assert.rejects(s.pack('private',[item]),/DURABLE_ITEM_IDS_REQUIRED/);
 await assert.rejects(s.pack('docs',[item,item]),/DURABLE_ITEM_IDS_REQUIRED/);
 await assert.rejects(s.pack('docs',[item]),/ITEM_OUTSIDE_SCOPE_OR_STALE/);assert.equal(s.context,null);
 assert.deepEqual(calls.at(-1).args,{namespace:'docs',ids:[item],maxBytes:48000});
});
test('malformed/wrong operation and foreign job receipt never become observed',async()=>{
 const {s}=setup(op=>response(op,{job:job()}));await s.enqueue('sync','key');
 s.client.request=async()=>response('durable.get',{job:job('RUNNING',{id:'f'.repeat(32)})});
 await assert.rejects(s.observe(s.refs[0]),/DURABLE_RESULT_SCHEMA/);assert.equal(s.refs[0].observed,false);
 s.client.request=async()=>response('durable.search',{job:job()});
 await assert.rejects(s.observe(s.refs[0]),/DURABLE_RESULT_SCHEMA/);
});
test('delayed get cannot overwrite a newer cancel receipt; running cancel stays running',async()=>{
 const {s}=setup(op=>response(op,{job:job()}));await s.enqueue('sync','key');const pending=deferred();
 s.client.request=(op)=>op==='durable.get'?pending.promise:Promise.resolve(response(op,{job:job('RUNNING',{task_key:'key',cancel_requested:true})}));
 const stale=assert.rejects(s.observe(s.refs[0]),/STALE_JOB_REPLY/);await s.observe(s.refs[0],'durable.cancel');
 assert.equal(s.refs[0].state,'RUNNING');assert.equal(s.refs[0].cancelRequested,true);
 pending.resolve(response('durable.get',{job:job('SUCCEEDED')}));await stale;assert.equal(s.refs[0].state,'RUNNING');
});
test('disconnect marks status unverified, preserves refs and never dispatches cancel/discard',async()=>{
 const {s,calls,cache}=setup(op=>response(op,{job:job('WAITING_CI')}));await s.enqueue('sync','key');const raw=cache.getItem('occ.durable.references.v1:test:local');
 s.disconnect();assert.equal(s.refs[0].observed,false);assert.equal(cache.getItem('occ.durable.references.v1:test:local'),raw);
 assert.deepEqual(calls.map(x=>x.type),['durable.enqueue']);
});
test('corrupt/oversized references fail closed and known-job cache is bounded',async()=>{
 const cache=storage();cache.setItem('occ.durable.references.v1:test:local','{');assert.throws(()=>setup(()=>{},cache),/CACHE_INVALID/);
 cache.setItem('occ.durable.references.v1:test:local','x'.repeat(16001));assert.throws(()=>setup(()=>{},cache),/CACHE_LIMIT/);
 const {s,calls}=setup(op=>response(op,{job:job()}));for(let i=0;i<20;i++)await s.enqueue('sync','key'+i);
 await assert.rejects(s.enqueue('sync','key20'),/REFERENCE_LIMIT/);assert.equal(calls.length,20);
});
test('NativeClient handles thrown postMessage and disconnect without leaking pending requests',async()=>{
 const listeners={};const port={onMessage:{addListener:f=>listeners.message=f},onDisconnect:{addListener:f=>listeners.disconnect=f},postMessage(){throw Error('Port closed');},disconnect(){}};
 let notices=0;const c=new NativeClient(port,{onDisconnect:()=>notices++});await assert.rejects(c.request('hello'),/Port closed/);assert.equal(c.pending.size,0);
 port.postMessage=()=>{};const rejected=assert.rejects(c.request('durable.enqueue'),/disconnected/);listeners.disconnect();await rejected;assert.equal(c.pending.size,0);assert.equal(notices,1);
});

// DOM contract harness; it does not claim an installed Windows/Chrome test.
class Element{
 constructor(){this.children=[];this.value='';this.disabled=false;this.checked=false;this._text='';}
 set textContent(v){this._text=String(v);}get textContent(){return this._text;}
 set innerHTML(v){throw Error('Unsafe HTML render: '+v);}
 append(...children){this.children.push(...children);}replaceChildren(...children){this.children=[...children];}
}
function dom(){const ids=['durable-search','durable-context','durable-enqueue','durable-refresh','durable-status','durable-profile','durable-namespace','durable-query','durable-template','durable-task-key','durable-hits','durable-output','durable-jobs'];const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));elements['durable-profile'].value='local';elements['durable-namespace'].value='docs';return {elements,document:{getElementById:id=>elements[id],createElement:()=>new Element()}};}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function agentDOM(){
 const d=dom();for(const id of ['agent-connect','agent-run','agent-disconnect','agent-status','agent-mode','agent-instruction','agent-constraints','agent-prohibitions','agent-budget','agent-parallel','agent-normalize','agent-goal-proposal','agent-jobs'])d.elements[id]=new Element();
 d.elements['agent-budget'].value='0';d.elements['agent-parallel'].value='1';
 const option=new Element();d.elements['agent-mode'].querySelector=()=>option;return d;
}

test('agent view normalizes locally and rejects ambiguous negation before native access',async t=>{
 const saved={document:globalThis.document,localStorage:globalThis.localStorage,chrome:globalThis.chrome,window:globalThis.window};t.after(()=>Object.assign(globalThis,saved));
 const {elements:e,document}=agentDOM();Object.assign(globalThis,{document,localStorage:storage(),chrome:undefined,window:{addEventListener(){}}});
 const agent=attachAgent({getSelection:()=>'',getEpoch:()=>0,addResult:()=>{}});e['agent-instruction'].value='Сравнить документы';e['agent-constraints'].value='Сохранить SHA';e['agent-prohibitions'].value='Публикация данных';
 e['agent-normalize'].onclick({isTrusted:false});assert.equal(e['agent-goal-proposal'].value,'');e['agent-normalize'].onclick({isTrusted:true});assert.equal(JSON.parse(e['agent-goal-proposal'].value).action_authority,false);
 e['agent-instruction'].value='Не публиковать';e['agent-normalize'].onclick({isTrusted:true});assert.equal(e['agent-goal-proposal'].value,'');assert.match(e['agent-status'].textContent,/NEGATION_AMBIGUOUS/);agent.clear();
});

test('trusted run hands Native Host only the revalidated canonical goal proposal',async t=>{
 const saved={document:globalThis.document,localStorage:globalThis.localStorage,chrome:globalThis.chrome,window:globalThis.window,confirm:globalThis.confirm};t.after(()=>Object.assign(globalThis,saved));
 const {elements:e,document}=agentDOM(),calls=[];const port=wirePort(m=>{calls.push(m);if(m.type==='hello')return {version:1,supportedModes:['analyze']};if(m.type==='list')return {jobs:[]};if(m.type==='begin')return {job:{id:'typed-job'}};if(m.type==='append')return {received:m.offset+Buffer.from(m.base64,'base64').length};if(m.type==='run')return {job:{id:'typed-job',state:'QUEUED'}};throw Error('unexpected '+m.type);});
 Object.assign(globalThis,{document,localStorage:storage(),confirm:()=>true,chrome:{runtime:{id:'testextension',connectNative:()=>port},permissions:{request:async()=>true}},window:{addEventListener(){}}});
 const agent=attachAgent({getSelection:()=> 'selected context',getEpoch:()=>7,addResult:()=>{}});e['agent-instruction'].value='Сравнить документы';e['agent-constraints'].value='Сохранить SHA';e['agent-prohibitions'].value='Публикация данных';
 try{await e['agent-connect'].onclick({isTrusted:true});await e['agent-run'].onclick({isTrusted:true});const begin=calls.find(m=>m.type==='begin'),instruction=JSON.parse(begin.instruction);assert.equal(instruction.schema,'occ.goal-proposal.v1');assert.equal(instruction.money_budget,0);assert.equal(instruction.max_parallel,1);assert.equal(instruction.action_authority,false);assert.deepEqual(Object.keys(instruction),['schema','goal','constraints','prohibitions','money_budget','max_parallel','action_authority']);}
 finally{agent.clear();}
});
function wirePort(handler){
 const listeners={};return {listeners,onMessage:{addListener:f=>listeners.message=f},onDisconnect:{addListener:f=>listeners.disconnect=f},disconnect(){listeners.disconnect?.();},postMessage(m){void Promise.resolve().then(()=>handler(m)).then(r=>listeners.message({...r,ok:true,requestId:m.requestId}),e=>listeners.message({ok:false,requestId:m.requestId,error:e.message}));}};
}
test('production attachAgent negotiates optional capabilities and resets durable UI on host disconnect',async t=>{
 const saved={document:globalThis.document,localStorage:globalThis.localStorage,chrome:globalThis.chrome,window:globalThis.window};
 t.after(()=>Object.assign(globalThis,saved));
 for(const advertised of [false,true]){
  const {elements:e,document}=agentDOM(),calls=[];
  const port=wirePort(m=>{calls.push(m.type);return m.type==='hello'?{version:1,supportedModes:['analyze'],...(advertised?{durableCommands:commands}:{})}:{jobs:[]};});
  Object.assign(globalThis,{document,localStorage:storage(),chrome:{runtime:{id:'testextension',connectNative:()=>port},permissions:{request:async()=>true}},window:{addEventListener(){}}});
  const agent=attachAgent({getSelection:()=>'',getEpoch:()=>0,addResult:()=>{}});
  try{await e['agent-connect'].onclick({isTrusted:true});assert.deepEqual(calls,['hello','list']);assert.equal(e['durable-search'].disabled,!advertised);assert.equal(e['agent-mode'].value,'analyze');port.listeners.disconnect();assert.equal(e['durable-search'].disabled,true);assert.match(e['durable-status'].textContent,/queue сохранена/);}
  finally{agent.clear();}
 }
});
test('production attachAgent closes a bad hello and allows a fresh connection',async t=>{
 const saved={document:globalThis.document,localStorage:globalThis.localStorage,chrome:globalThis.chrome,window:globalThis.window};t.after(()=>Object.assign(globalThis,saved));
 const {elements:e,document}=agentDOM();let count=0,disconnects=0;
 Object.assign(globalThis,{document,localStorage:storage(),chrome:{runtime:{id:'testextension',connectNative:()=>{const p=wirePort(m=>m.type==='hello'?{version:++count===1?2:1,supportedModes:['analyze'],durableCommands:commands}:{jobs:[]});const close=p.disconnect;p.disconnect=()=>{disconnects++;close();};return p;}},permissions:{request:async()=>true}},window:{addEventListener(){}}});
 const agent=attachAgent({getSelection:()=>'',getEpoch:()=>0,addResult:()=>{}});
 try{await e['agent-connect'].onclick({isTrusted:true});assert.equal(disconnects,1);assert.equal(e['durable-search'].disabled,true);await e['agent-connect'].onclick({isTrusted:true});assert.equal(e['durable-search'].disabled,false);}
 finally{agent.clear();}
});
test('view wires search/context/enqueue/get/cancel; untrusted click grants no execution',async()=>{
 const {elements:e,document}=dom(),calls=[];
 const client={closed:false,request:async(op,args)=>{calls.push({op,args});if(op==='durable.search')return response(op,{items:[{id:item,source_key:'<img onerror=evil>',snippet:'<script>evil</script>'}]});if(op==='durable.context')return response(op,{context:{schema:'occ.context-pack.v1',namespace:'docs',items:[{id:item,text:'source only'}],sha256:'a'.repeat(64),bytes:11}});return response(op,{job:job(op==='durable.cancel'?'CANCELLED':'QUEUED',{cancel_requested:op==='durable.cancel'})});}};
 const view=attachDurableView({document,storage:storage(),scopePrefix:'test'});assert.equal(e['durable-search'].disabled,true);view.connect(client,hello);
 e['durable-query'].value='needle';e['durable-search'].onclick({isTrusted:false});await flush();assert.equal(calls.length,0);
 e['durable-search'].onclick({isTrusted:true});await flush();assert.equal(e['durable-hits'].children[0].children[1].textContent,'<img onerror=evil> · <script>evil</script>');
 const checkbox=e['durable-hits'].children[0].children[0];checkbox.checked=true;checkbox.onchange();e['durable-context'].onclick({isTrusted:true});await flush();assert.match(e['durable-output'].value,/source only/);
 e['durable-template'].value='sync';e['durable-task-key'].value='key';e['durable-enqueue'].onclick({isTrusted:true});await flush();
 e['durable-refresh'].onclick({isTrusted:true});await flush();const stop=e['durable-jobs'].children[0].children[1];stop.onclick({isTrusted:true});await flush();
 assert.equal(view.session.refs[0].state,'CANCELLED');assert.deepEqual(calls.map(x=>x.op),commands);
 assert.deepEqual(calls.find(x=>x.op==='durable.enqueue').args,{template:'sync',taskKey:'key'});view.disconnect();assert.equal(e['durable-search'].disabled,true);
});
test('selection change while pack is pending cannot display an obsolete context',async()=>{
 const {elements:e,document}=dom(),pending=deferred();
 const view=attachDurableView({document,storage:storage(),scopePrefix:'test'});
 view.connect({closed:false,request:op=>op==='durable.search'?Promise.resolve(response(op,{items:[{id:item,source_key:'note',snippet:'text'}]})):pending.promise},hello);
 await view.session.search('docs','needle');let check=e['durable-hits'].children[0].children[0];check.checked=true;check.onchange();e['durable-context'].onclick({isTrusted:true});
 check=e['durable-hits'].children[0].children[0];check.checked=false;check.onchange();pending.resolve(response('durable.context',{context:{schema:'occ.context-pack.v1',namespace:'docs',items:[{id:item}],sha256:item,bytes:0}}));await flush();assert.equal(e['durable-output'].value,'');
});

test('UI session/NativeClient roundtrips real SQLite, restart/replay and persisted cancellation',async t=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'occ-f14-'));
 const lab=fileURLToPath(new URL('../../content-lab/',import.meta.url));
 const discovery=spawnSync(process.platform==='win32'?'python':'python3',['-I','-c','import sys;print(sys.executable)'],{encoding:'utf8'});assert.equal(discovery.status,0,discovery.stderr);const python=discovery.stdout.trim();
 const source=path.join(root,'source'),store=path.join(root,'store');await fs.mkdir(source);await fs.writeFile(path.join(source,'note.md'),'Needle current context 👋');
 const policy={schema:'occ.automation-policy.v1',max_parallel:1,money_budget:0,sources:{docs:{namespace:'docs',root:source}},repos:{}};
 const policyPath=path.join(root,'policy.json'),profilePath=path.join(root,'profile.json');await fs.writeFile(policyPath,JSON.stringify(policy));
 await fs.writeFile(profilePath,JSON.stringify({schema:'occ.native-durable-profile.v1',store,policy_file:policyPath,namespaces:['docs'],templates:{sync:{kind:'sync',source_profile:'docs'}}}));
 const initial=spawnSync(python,['-I','-X','utf8','-c','import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from automation_core import sync;sync(Path(sys.argv[2]),"docs",Path(sys.argv[3]))',lab,store,source],{encoding:'utf8'});assert.equal(initial.status,0,initial.stderr);
 const hosts=[],clients=[];
 const create=()=>{
  const host=new JobHost({dataRoot:path.join(root,'ephemeral'),codexPath:'never-invoked',durableCore:{enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath}});hosts.push(host);
  const listeners={};const port={onMessage:{addListener:f=>listeners.message=f},onDisconnect:{addListener:f=>listeners.disconnect=f},disconnect(){},postMessage(m){void host.handle(m).then(r=>listeners.message({...r,requestId:m.requestId,ok:true}),e=>listeners.message({requestId:m.requestId,ok:false,error:e.message}));}};
  const client=new NativeClient(port);clients.push(client);return {host,client};
 };
 t.after(async()=>{for(const c of clients)c.close();for(const h of hosts)await h.close();await fs.rm(root,{recursive:true,force:true});});
 const cache=storage(),a=create(),s=new DurableSession({storage:cache});s.connect(a.client,await a.client.request('hello'),'real:local');
 const hits=await s.search('docs','needle'),c=await s.pack('docs',[hits[0].id]);assert.match(c.items[0].text,/👋/);assert.equal(c.authority,'source-content-not-action-instructions');
 const first=await s.enqueue('sync','stable-goal');s.disconnect();a.client.close();await a.host.close();
 const b=create(),restored=new DurableSession({storage:cache});restored.connect(b.client,await b.client.request('hello'),'real:local');assert.equal(restored.refs[0].observed,false);
 await restored.refresh();assert.equal(restored.refs[0].state,'QUEUED');const replay=await restored.enqueue('sync','stable-goal');assert.equal(replay.id,first.id);assert.equal(replay.reused,true);
 await restored.observe(restored.refs[0],'durable.cancel');assert.equal(restored.refs[0].state,'CANCELLED');
 await assert.rejects(restored.search('private','needle'),/DURABLE_NAMESPACE_OUTSIDE_SCOPE/);
 await fs.writeFile(path.join(source,'note.md'),'replacement');const scan=spawnSync(python,['-I','-c','import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from automation_core import sync;sync(Path(sys.argv[2]),"docs",Path(sys.argv[3]))',lab,store,source],{encoding:'utf8'});assert.equal(scan.status,0,scan.stderr);
 // Old IDs were selected by a valid earlier search, but the owner now rejects them.
 restored.hits=hits;restored.namespace='docs';await assert.rejects(restored.pack('docs',[hits[0].id]),/ITEM_OUTSIDE_SCOPE_OR_STALE/);
 assert.equal((await b.client.request('durable.get',{jobId:first.id})).durable.job.state,'CANCELLED');
});
