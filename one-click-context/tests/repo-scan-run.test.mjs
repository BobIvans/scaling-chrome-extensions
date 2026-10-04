import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {RepoReviewSession,attachRepoReviewView} from '../library/repo-review-ui.mjs';
import {DurableSession} from '../library/durable-ui.mjs';
import {NativeClient} from '../library/agent.mjs';
import {JobHost} from '../../agent-bridge/host.mjs';

const id='a'.repeat(64),snapshot='b'.repeat(64);
const projection=(patch={})=>({schema:'occ.repo-scan-run.v1',repository:'sce',alias:'sce',namespace:'code',run_id:id,intent_key:'c'.repeat(32),snapshot_id:snapshot,repo_sha:'d'.repeat(40),tree_sha:'e'.repeat(40),state:'RUNNING',run_revision:0,cursor:0,total:45,ledger_entries:45,processed:0,pending:45,indexed:0,excluded:0,errors:0,counts:{PENDING:45},inventory_complete:false,exact_for_indexed:false,files:[],...patch});
const reply=run=>({schema:'occ.native-durable-result.v1',operation:'durable.repo.scanRun',scan_run:run});
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const until=async condition=>{for(let n=0;n<200;n++){if(condition())return;await new Promise(r=>setTimeout(r,5));}throw Error('Test condition did not arrive');};
function session(handler){const calls=[],durable={generation:0,can:c=>c==='durable.repo.scanRun',request:async(type,args)=>{calls.push(args);return handler(args);}};const s=new RepoReviewSession({durable});s.repositories=[{repository:'sce',namespace:'code'},{repository:'other',namespace:'code'}];s.choose('sce');return {s,durable,calls};}

test('one intent pumps all pages sequentially and yields between requests',async()=>{
 let cursor=0,inflight=0,peak=0,yielded=false;
 const {s,calls}=session(async args=>{
  if(args.action==='START')return reply(projection({intent_key:args.intentKey}));
  if(args.action==='STEP'){
   assert.equal(args.expectedCursor,cursor);inflight++;peak=Math.max(peak,inflight);
   await new Promise(r=>setTimeout(r,1));cursor=Math.min(45,cursor+20);inflight--;
   return reply(projection({cursor,processed:cursor,pending:45-cursor,state:cursor===45?'COMPLETE':'RUNNING',run_revision:cursor===45?1:0,inventory_complete:cursor===45,exact_for_indexed:cursor===45}));
  }return reply(projection({cursor,processed:cursor,pending:45-cursor}));
 });
 setTimeout(()=>{yielded=true;},0);await s.startWholeScan();
 assert.equal(yielded,true);assert.equal(peak,1);assert.equal(s.run.cursor,45);
 assert.deepEqual(calls.map(c=>c.action),['START','STEP','STEP','STEP']);assert.equal(s.scanPumping,false);
});

test('local pause stops scheduling before a late STEP; reopen only observes; Continue is explicit',async()=>{
 const held=deferred();let stored=projection();
 const {s,calls}=session(async args=>{
  if(args.action==='START')return reply(stored);
  if(args.action==='STEP'){if(stored.cursor===0){await held.promise;stored=projection({cursor:20,processed:20,pending:25});}else stored=projection({cursor:45,processed:45,pending:0,state:'COMPLETE',run_revision:3,inventory_complete:true,exact_for_indexed:true});}
  if(args.action==='PAUSE')stored={...stored,state:'PAUSED',run_revision:1};
  if(args.action==='CONTINUE')stored={...stored,state:'RUNNING',run_revision:2};
  return reply(stored);
 });
 const pump=s.startWholeScan();await until(()=>calls.some(c=>c.action==='STEP'));
 const pause=s.controlScan('PAUSE');assert.equal(s.scanPumping,false);held.resolve();await Promise.all([pump,pause]);
 assert.equal(calls.filter(c=>c.action==='STEP').length,1);assert.equal(s.run.state,'PAUSED');assert.equal(s.run.cursor,20);
 const fresh=new RepoReviewSession({durable:s.durable});fresh.repositories=s.repositories;fresh.choose('sce');await fresh.restoreScan();
 assert.equal(fresh.scanPumping,false);assert.equal(calls.filter(c=>c.action==='STEP').length,1);
 await fresh.controlScan('CONTINUE');assert.equal(fresh.run.state,'COMPLETE');assert.equal(fresh.run.cursor,45);
});

test('cancelled intent, repository switch and disconnect cannot be revived by late STEP replies',async()=>{
 for(const action of ['CANCEL','switch','disconnect']){
  const held=deferred();let stored=projection();
  const {s,calls,durable}=session(async args=>{
   if(args.action==='STEP'){await held.promise;stored=projection({cursor:20,processed:20,pending:25});}
   if(args.action==='CANCEL')stored={...stored,state:'CANCELLED',run_revision:1};
   return reply(stored);
  });
  const pump=s.startWholeScan();await until(()=>calls.some(c=>c.action==='STEP'));
  let control;
  if(action==='CANCEL')control=s.controlScan('CANCEL');
  else if(action==='switch')s.choose('other');
  else {durable.generation++;s.reset();}
  held.resolve();await pump;await control;
  assert.equal(calls.filter(c=>c.action==='STEP').length,1);
  assert.equal(s.scanPumping,false);
  if(action==='CANCEL'){assert.equal(s.run.state,'CANCELLED');await s.restoreScan();assert.equal(s.run.state,'CANCELLED');}
  else assert.equal(s.run,null);
 }
});

test('no progress and lost STEP/control replies stop the pump and reconcile exactly once',async()=>{
 for(const fault of ['no-progress','timeout']){
  let stored=projection();const {s,calls}=session(async args=>{
   if(args.action==='STEP'&&fault==='timeout'){stored=projection({cursor:20,processed:20,pending:25});throw Error('Native host timeout');}
   return reply(stored);
  });
  await assert.rejects(s.startWholeScan(),fault==='timeout'?/timeout/:/NO_PROGRESS/);
  assert.equal(calls.filter(c=>c.action==='STEP').length,1);
  assert.equal(calls.filter(c=>c.action==='STATUS').length,1);
  assert.equal(s.scanPumping,false);assert.equal(s.run.cursor,fault==='timeout'?20:0);
 }
 let stored=projection();const {s,calls}=session(async args=>{
  if(args.action==='CANCEL'){stored={...stored,state:'CANCELLED',run_revision:1};throw Error('Lost control reply');}
  return reply(stored);
 });
 s.acceptRun(stored);await assert.rejects(s.controlScan('CANCEL'),/Lost control/);
 assert.equal(s.run.state,'CANCELLED');assert.equal(s.scanPumping,false);assert.ok(s.scanError);
 assert.equal(calls.filter(c=>c.action==='STEP').length,0);
});

test('older host is explicitly unavailable and reconnect to RUNNING does not pump',async()=>{
 const {s,durable,calls}=session(()=>reply(projection()));durable.can=()=>false;
 await assert.rejects(s.startWholeScan(),/WHOLE_REPO_SCAN_UNAVAILABLE/);assert.equal(calls.length,0);
 durable.can=()=>true;await s.restoreScan();assert.equal(s.run.state,'RUNNING');assert.equal(s.scanPumping,false);assert.equal(calls.length,1);
});

class Element{constructor(){this.children=[];this.value='';this.disabled=false;this.checked=false;this.textContent='';}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=[...nodes];}}
function dom(){const ids=['repo-panel','repo-status','repo-list','repo-scan','repo-rescan','repo-pause','repo-continue','repo-stop','review-list','review-import','repo-export','repo-next','repo-prev','repo-copy','repo-download','repo-repository','repo-progress','repo-files','repo-goal','repo-scope','repo-acceptance','repo-output','review-sessions','review-details','review-next-request','review-namespace','review-input','review-file'];const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));return {elements,document:{getElementById:id=>elements[id],createElement:()=>new Element()}};}

test('production controls remain available during a held page; initial pending ledger shows processed zero',async()=>{
 const {elements:e,document}=dom(),held=deferred(),calls=[];let stored=projection();
 const durable={generation:0,can:()=>true,request:async(op,args={})=>{
  calls.push(args.action||op);
  if(op==='durable.repo.list')return {schema:'occ.native-durable-result.v1',operation:op,repositories:[{repository:'sce',namespace:'code'}]};
  if(args.action==='STATUS'&&calls.filter(c=>c==='START').length===0)return reply(null);
  if(args.action==='STEP'){await held.promise;stored=projection({cursor:20,processed:20,pending:25});}
  if(args.action==='PAUSE')stored={...stored,state:'PAUSED',run_revision:1};
  return reply(stored);
 }};
 const view=attachRepoReviewView({document,session:durable});
 e['repo-list'].onclick({isTrusted:true});await until(()=>view.state.repository==='sce'&&!view.state.busy);
 e['repo-scan'].onclick({isTrusted:true});await until(()=>calls.includes('STEP'));
 assert.match(e['repo-progress'].textContent,/обработано 0\/45/);
 assert.equal(e['repo-pause'].disabled,false);assert.equal(e['repo-stop'].disabled,false);
 e['repo-pause'].onclick({isTrusted:true});assert.equal(view.state.scanPumping,false);held.resolve();
 await until(()=>view.state.run.state==='PAUSED'&&!view.state.scanControlPending);
 assert.equal(calls.filter(c=>c==='STEP').length,1);assert.equal(e['repo-continue'].disabled,false);
 view.disconnect();
 const html=await fs.readFile(new URL('../library.html',import.meta.url),'utf8');
 for(const control of ['repo-pause','repo-continue','repo-stop'])assert.match(html,new RegExp('<button id="'+control+'"'));
 assert.match(html,/id="repo-progress" role="status" aria-live="polite"/);
});

test('UI → NativeClient → JobHost → installed adapter → Git/SQLite resumes across real host restart',async t=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'occ-whole-scan-')),checkout=path.join(root,'repo'),store=path.join(root,'store');await fs.mkdir(checkout);
 const git=(...args)=>{const r=spawnSync('git',['-C',checkout,...args],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);return r.stdout.trim();};
 git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');git('config','core.autocrlf','false');
 const lab=fileURLToPath(new URL('../../content-lab/',import.meta.url));await fs.cp(path.join(lab,'fixtures/full-repo-scan'),checkout,{recursive:true});git('add','-A');git('commit','-qm','45 source files');
 const installed=path.join(root,'installed/content-lab');await fs.mkdir(installed,{recursive:true});
 const installer=await fs.readFile(new URL('../../agent-bridge/Install.ps1',import.meta.url),'utf8'),files=installer.match(/foreach\(\$occFile in @\((.*?)\)\)/)[1];
 for(const name of [...files.matchAll(/'([^']+)'/g)].map(m=>m[1]))await fs.copyFile(path.join(lab,name),path.join(installed,name));
 for(const name of ['occ_v4','occ_v5'])await fs.cp(path.join(lab,name),path.join(installed,name),{recursive:true});
 const python=spawnSync(process.platform==='win32'?'python':'python3',['-I','-c','import sys;print(sys.executable)'],{encoding:'utf8'}).stdout.trim();
 const policyPath=path.join(root,'policy.json'),profilePath=path.join(root,'profile.json');await fs.writeFile(policyPath,JSON.stringify({schema:'occ.automation-policy.v1',max_parallel:1,money_budget:0}));
 await fs.writeFile(profilePath,JSON.stringify({schema:'occ.native-durable-profile.v1',store,policy_file:policyPath,namespaces:['code'],templates:{},repositories:{sce:{root:checkout,namespace:'code',source_roots:['.'],exclusions:[]}}}));
 const hosts=[],clients=[],trace=[];t.after(async()=>{for(const c of clients)c.close();for(const h of hosts)await h.close();await fs.rm(root,{recursive:true,force:true});});
 async function connect(loseStep=false){
  let lost=false;
  const host=new JobHost({dataRoot:path.join(root,'jobs'),codexPath:'never-executed',durableCore:{enabled:true,pythonPath:python,adapterPath:path.join(installed,'native_adapter.py'),profilePath}});hosts.push(host);
  const listeners={};const port={onMessage:{addListener:f=>listeners.message=f},onDisconnect:{addListener:f=>listeners.disconnect=f},disconnect(){},postMessage(m){trace.push({type:m.type,action:m.action});void host.handle(m,()=>listeners.message({requestId:m.requestId,progress:true})).then(r=>{if(loseStep&&!lost&&m.action==='STEP'){lost=true;listeners.message({requestId:m.requestId,ok:false,error:'Native host timeout'});}else listeners.message({...r,requestId:m.requestId,ok:true});},e=>listeners.message({requestId:m.requestId,ok:false,error:e.message}));}};
  const client=new NativeClient(port);clients.push(client);const durable=new DurableSession();durable.connect(client,await client.request('hello'),'fixture');assert.equal(durable.can('durable.repo.scanRun'),true);
  const view=new RepoReviewSession({durable});await view.loadRepositories();view.choose('sce');return {host,client,view};
 }
 const a=await connect();await a.view.restoreScan();assert.equal(a.view.run,null);
 let pause,requested=false;const cursors=[];a.view.onChange=()=>{if(a.view.run){const cursor=a.view.run.cursor;if(cursors.at(-1)!==cursor)cursors.push(cursor);if(cursor===20&&!requested){requested=true;pause=a.view.controlScan('PAUSE');}}};
 await a.view.startWholeScan();await pause;
 assert.equal(a.view.run.state,'PAUSED');assert.equal(a.view.run.cursor,20);assert.equal(trace.filter(x=>x.action==='STEP').length,1);
 a.client.close();await a.host.close();
 const b=await connect(true);await b.view.restoreScan();assert.equal(b.view.run.run_id,a.view.run.run_id);assert.equal(b.view.run.cursor,20);assert.equal(b.view.scanPumping,false);
 await assert.rejects(b.view.controlScan('CONTINUE'),/Native host timeout/);assert.equal(b.view.run.cursor,40);assert.equal(b.view.scanPumping,false);
 await b.view.controlScan('CONTINUE');assert.equal(b.view.run.state,'COMPLETE');assert.equal(b.view.run.cursor,45);assert.equal(b.view.run.exact_for_indexed,true);
 assert.equal(trace.filter(x=>x.action==='STEP').length,3);
 // New explicit intent reuses the completed pinned snapshot without another page.
 await b.view.startWholeScan();assert.equal(b.view.run.state,'COMPLETE');assert.equal(trace.filter(x=>x.action==='STEP').length,3);
});

test('NativeClient progress frames keep queued scan controls alive without resolving a pending request',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});const listeners={},sent=[];
 const port={onMessage:{addListener:f=>listeners.message=f},onDisconnect:{addListener:f=>listeners.disconnect=f},disconnect(){},postMessage:m=>sent.push(m)};
 const client=new NativeClient(port);const step=client.request('durable.repo.scanRun',{action:'STEP'}),stop=client.request('durable.repo.scanRun',{action:'CANCEL'});
 for(let n=0;n<4;n++){t.mock.timers.tick(14000);listeners.message({requestId:sent[0].requestId,progress:true});}
 assert.equal(client.pending.size,2);
 listeners.message({requestId:sent[0].requestId,ok:true,durable:{state:'RUNNING'}});
 listeners.message({requestId:sent[1].requestId,ok:true,durable:{state:'CANCELLED'}});
 assert.equal((await step).durable.state,'RUNNING');assert.equal((await stop).durable.state,'CANCELLED');client.close();
});
