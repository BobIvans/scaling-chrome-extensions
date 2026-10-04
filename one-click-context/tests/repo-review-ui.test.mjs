import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {RepoReviewSession,attachRepoReviewView,parseReviewInput,REVIEW_NATIVE_INPUT_BYTES} from '../library/repo-review-ui.mjs';
import {DurableSession} from '../library/durable-ui.mjs';
import {NativeClient} from '../library/agent.mjs';
import {JobHost} from '../../agent-bridge/host.mjs';
import {DURABLE_COMMANDS,DURABLE_INPUT_BYTES} from '../../agent-bridge/durable.mjs';

const snapshotId='a'.repeat(64),sessionId='b'.repeat(64);
const snapshot={schema:'occ.repo-snapshot.v1',alias:'sce',namespace:'code',snapshot_id:snapshotId,repo_sha:'c'.repeat(40),cursor:1,total:1,state:'COMPLETE',files:[{path:'main.py',state:'INDEXED',parser:'PYTHON_AST',findings:[{criterion:'Review <script>candidate</script>'}]}],counts:{INDEXED:1},offset:0,next_offset:null};
const status={schema:'occ.review-status.v1',namespace:'code',session_id:sessionId,state:'NEEDS_REVIEW',sources:[],next_step:'VERIFY_CRITERION_EVIDENCE'};
const response=(operation,payload)=>({schema:'occ.native-durable-result.v1',operation,...payload});
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
function setup(handler){const calls=[],d={generation:0,can:()=>true,request:async(op,args)=>{calls.push({op,args});return handler(op,args);}};d.enqueueReport=async(namespace,sessionId,template,taskKey)=>(await d.request('durable.review.report',{namespace,sessionId,template,taskKey})).job;const s=new RepoReviewSession({durable:d});s.repositories=[{repository:'sce',namespace:'code'}];s.choose('sce');return {s,d,calls};}

test('review import preflights complete UTF-8 native envelope and duplicate keys',()=>{
 assert.equal(REVIEW_NATIVE_INPUT_BYTES,DURABLE_INPUT_BYTES);
 for(const raw of ['{"x":1,"x":2}','{"a":{"x":1,"\\u0078":2}}'])assert.throws(()=>parseReviewInput(raw,'code'),/DUPLICATE_KEY/);
 assert.throws(()=>parseReviewInput(JSON.stringify({text:'Я'.repeat(8000)}),'code'),/INPUT_LIMIT/);
 assert.throws(()=>parseReviewInput(JSON.stringify({text:'x'.repeat(15950)}),'code'),/INPUT_LIMIT/);
 assert.deepEqual(parseReviewInput('{"a":[{},[],1,"x"],"b":true}','code'),{a:[{},[],1,'x'],b:true});
});
test('one persisted snapshot resumes; stale scans/exports never overwrite a changed selection',async()=>{
 const pending=deferred();const {s,calls}=setup(()=>pending.promise);
 const stale=assert.rejects(s.scan(),/STALE_CONTEXT_REPLY/);s.choose('sce');pending.resolve(response('durable.repo.scan',{snapshot}));await stale;assert.equal(s.snapshot,null);
 s.durable.request=async(op,args)=>{calls.push({op,args});return response(op,{snapshot});};await s.scan();await s.scan();assert.equal(calls.at(-1).args.snapshotId,snapshotId);
 const late=deferred();s.durable.request=()=>late.promise;s.select('main.py',true);const exportStale=assert.rejects(s.export('goal','scope',['criterion']),/STALE_CONTEXT_REPLY/);s.select('main.py',false);
 late.resolve(response('durable.repo.export',{export:{document:{schema:'occ.repo-request.v1'},review:status}}));await exportStale;assert.equal(s.exported,null);
});
test('source selection and import cannot add paths, commands or execution authority',async()=>{
 const {s,calls}=setup(op=>response(op,{snapshot}));await s.scan();assert.throws(()=>s.select('unknown.py',true),/OUTSIDE/);s.select('main.py',true);
 s.durable.request=async(op,args)=>{calls.push({op,args});return response(op,{export:{document:{schema:'occ.repo-request.v1'},review:status}});};await s.export('goal','scope',['criterion']);
 assert.deepEqual(calls.at(-1).args,{repository:'sce',snapshotId,paths:['main.py'],goal:'goal',scope:'scope',acceptance:['criterion'],maxBytes:24000});
 await assert.rejects(s.import('code','{"x":1,"x":2}'),/DUPLICATE/);
});

function manifestResult(action,offset=0,fileOrdinal=null,total=45){
 const count=action==='INFO'?0:Math.min(20,Math.max(0,total-offset));
 const rows=Array.from({length:count},(_,i)=>action==='ENTRIES'?{schema:'occ.repo-entry-manifest.v1',snapshot_id:snapshotId,ordinal:offset+i,path:`file ${offset+i} <script>.txt`,state:'INDEXED',chunk_count:45}:{schema:'occ.repo-part-index.v1',snapshot_id:snapshotId,file_ordinal:fileOrdinal??0,path:'main.py',chunk_ordinal:offset+i,part_id:'d'.repeat(64),sha256:'e'.repeat(64),source_start:(offset+i)*4096,source_end:(offset+i+1)*4096,text_eligible:true});
 return {schema:'occ.repo-manifest-view.v1',batch_id:'f'.repeat(64),binding:{snapshot_id:snapshotId,repository:'sce',namespace:'code'},scope:{action,file_ordinal:fileOrdinal},total:action==='INFO'?0:total,offset,rows,nextOffset:action==='INFO'||offset+rows.length>=total?null:offset+rows.length,global_validation:'NOT_RUN'};
}
test('manifest pages reach file and part tails and navigate back to the exact source',async()=>{
 const {s,calls}=setup((op,args)=>response(op,op==='durable.repo.manifest'?{manifest:manifestResult(args.action,args.offset,args.fileOrdinal??null)}:{snapshot}));s.acceptSnapshot(snapshot);
 await s.manifestPage('ENTRIES');await s.manifestNext();await s.manifestNext();assert.equal(s.manifest.rows.length,5);assert.equal(s.manifest.nextOffset,null);assert.deepEqual(s.manifestHistory,[0,20]);await s.manifestBack();assert.equal(s.manifest.offset,20);
 await s.manifestPage('PARTS',0,0);assert.deepEqual(s.manifestHistory,[]);await s.manifestNext();await s.manifestNext();assert.equal(s.manifest.rows[4].chunk_ordinal,44);
 await s.manifestSource(s.manifest.rows[4]);assert.equal(calls.at(-2).args.offset,0);assert.equal(s.manifest.scope.action,'ENTRIES');
});
test('late manifest replies cannot overwrite a changed repository or file filter',async()=>{
 const {s}=setup((op,args)=>response(op,{manifest:manifestResult(args.action,args.offset,args.fileOrdinal??null)}));s.acceptSnapshot(snapshot);
 const late=deferred();s.durable.request=()=>late.promise;const pending=assert.rejects(s.manifestPage('PARTS',0,0),/STALE_MANIFEST_REPLY/);
 s.durable.request=async op=>response(op,{manifest:manifestResult('PARTS',0,3)});await s.manifestPage('PARTS',0,3);
 late.resolve(response('durable.repo.manifest',{manifest:manifestResult('PARTS',0,0)}));await pending;assert.equal(s.manifest.scope.file_ordinal,3);
 const later=deferred();s.durable.request=()=>later.promise;const changed=assert.rejects(s.manifestPage('ENTRIES'),/STALE_MANIFEST_REPLY/);s.choose('sce');later.resolve(response('durable.repo.manifest',{manifest:manifestResult('ENTRIES')}));await changed;assert.equal(s.manifest,null);
});
test('manifest rejects a mismatched scope or falsely completed page',async()=>{
 const {s}=setup(op=>response(op,{manifest:{...manifestResult('ENTRIES'),nextOffset:null}}));s.acceptSnapshot(snapshot);await assert.rejects(s.manifestPage('ENTRIES'),/MANIFEST_RESULT_SCHEMA/);
 s.durable.request=async op=>response(op,{manifest:manifestResult('PARTS',0,3)});await assert.rejects(s.manifestPage('PARTS',0,0),/MANIFEST_RESULT_SCHEMA/);
});

test('next context part sends the disclosed source cursor without changing repo/snapshot selection',async()=>{
 const {s,calls}=setup(op=>response(op,{snapshot}));await s.scan();s.select('main.py',true);
 s.durable.request=async(op,args)=>{calls.push({op,args});return response(op,{export:{document:{schema:'occ.repo-request.v1',selection:{next_source_offset:4}},review:status}});};
 await s.export('goal','scope',['criterion']);await s.export('goal','scope',['criterion'],s.exported.document.selection.next_source_offset);
 assert.equal(calls.at(-1).args.sourceOffset,4);assert.equal(calls.at(-1).args.snapshotId,snapshotId);assert.deepEqual(calls.at(-1).args.paths,['main.py']);
 await assert.rejects(s.export('goal','scope',['criterion'],-1),/OFFSET_REQUIRED/);
});

test('report queue exposes verified output and blocker; stale replies do not replace a new goal',async()=>{
 const jobId='d'.repeat(32),{s,calls}=setup(op=>response(op,{job:{id:jobId,state:'QUEUED',next_step:'RUN_REGISTERED_LOCAL_WORKER'}}));
 s.review=status;await s.enqueueReport('configured-report','report-one');
 assert.equal(calls[0].op,'durable.review.report');assert.equal(calls[0].args.sessionId,sessionId);
 assert.equal(s.reportJob.next_step,'RUN_REGISTERED_LOCAL_WORKER');
 s.durable.request=async op=>response(op,{job:{id:jobId,state:'BLOCKED',outcome:{reason:'REPORT_POSTCONDITION_FAILED'},next_step:'INSPECT_BLOCKER'}});
 await s.refreshReport();assert.equal(s.reportJob.outcome.reason,'REPORT_POSTCONDITION_FAILED');
 const late=deferred();s.durable.request=()=>late.promise;const pending=assert.rejects(s.refreshReport(),/STALE_CONTEXT_REPLY/);s.invalidate();late.resolve(response('durable.get',{job:{id:jobId,state:'SUCCEEDED'}}));await pending;
 assert.equal(s.review,null);
});

test('V4/V5 TXT and bound reply use the selected immutable session and reject goal changes',async()=>{
 const {s,calls}=setup(op=>response(op,{handoff:{binding_v7:{session_id:sessionId},rendered_txt:'V4 request + V5 overlay'}}));
 s.review=status;await s.exportHandoff();assert.equal(s.handoff.rendered_txt,'V4 request + V5 overlay');
 s.durable.request=async(op,args)=>{calls.push({op,args});return response(op,{review:status});};
 await s.import('code',JSON.stringify({schema:'occ.review_bundle.v5'}));
 assert.equal(calls.at(-1).op,'durable.review.importBound');assert.equal(calls.at(-1).args.sessionId,sessionId);
 s.invalidate();assert.equal(s.handoff,null);
 await assert.rejects(s.import('code',JSON.stringify({schema:'occ.review_bundle.v5'})),/SELECTED_SESSION/);
});

class Element{
 constructor(){this.children=[];this.value='';this.disabled=false;this.checked=false;this._text='';}
 set textContent(v){this._text=String(v);}get textContent(){return this._text;}
 set innerHTML(_value){throw Error('Unsafe source rendering');}
 append(...children){this.children.push(...children);}replaceChildren(...children){this.children=[...children];}
}
function dom(){const ids=['repo-pause','repo-continue','repo-stop','repo-panel','repo-status','repo-list','repo-scan','repo-rescan','review-list','review-import','repo-export','repo-export-next','repo-coverage','repo-next','repo-prev','repo-copy','repo-download','repo-repository','repo-progress','repo-files','repo-goal','repo-scope','repo-acceptance','repo-output','review-sessions','review-details','review-next-request','review-namespace','review-input','review-file','repo-manifest-info','repo-manifest-entries','repo-manifest-parts','repo-manifest-next','repo-manifest-prev','repo-manifest-summary','repo-manifest-rows'];const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));return {elements,document:{getElementById:id=>elements[id],createElement:()=>new Element()}};}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('production view wires repo selection → scan → finding → request → review with text-only rendering',async()=>{
 const {elements:e,document}=dom(),calls=[];
 const durable={generation:0,can:()=>true,request:async(op,args)=>{calls.push({op,args});if(op==='durable.repo.list')return response(op,{repositories:[{repository:'sce',namespace:'code'}]});if(op==='durable.repo.scanRun')return response(op,{scan_run:args.action==='STATUS'?null:{...snapshot,schema:'occ.repo-scan-run.v1',repository:'sce',run_id:'d'.repeat(64),intent_key:'e'.repeat(32),run_revision:1,processed:1,pending:0,ledger_entries:1,inventory_complete:true,exact_for_indexed:true}});if(op==='durable.repo.scan')return response(op,{snapshot});if(op==='durable.repo.export')return response(op,{export:{document:{schema:'occ.repo-request.v1',goal:'fixture',selection:{source_offset:args.sourceOffset||0,next_source_offset:4,source_total:8,omitted_count:4,coverage:'PARTIAL'}},review:status}});if(op==='durable.review.list')return response(op,{reviews:[status]});return response(op,{review:{...status,coverage:{reviewed:['main.py']},finding_details:[{finding_id:'F1',criterion:'<img src=evil>',disposition:'DONE'}]}});}};
 const view=attachRepoReviewView({document,session:durable});view.connect();e['repo-list'].onclick({isTrusted:false});await flush();assert.equal(calls.length,0);
 e['repo-list'].onclick({isTrusted:true});await flush();e['repo-scan'].onclick({isTrusted:true});await flush();assert.match(e['repo-progress'].textContent,/1\/1/);
 e['repo-files'].children[0].children[2].onclick({isTrusted:true});e['repo-scope'].value='current owner';e['repo-acceptance'].value='test criterion';e['repo-export'].onclick({isTrusted:true});await flush();assert.match(e['repo-output'].value,/fixture/);
 assert.equal(e['repo-export-next'].disabled,false);e['repo-export-next'].onclick({isTrusted:true});await flush();assert.equal(calls.at(-1).args.sourceOffset,4);
 e['review-input'].value=JSON.stringify({session_id:sessionId});e['review-import'].onclick({isTrusted:true});await flush();assert.match(e['review-details'].textContent,/<img src=evil>/);assert.match(e['review-next-request'].value,/VERIFY_CRITERION_EVIDENCE/);
 view.disconnect();assert.equal(e['repo-output'].value,'');assert.equal(view.state.review,null);
});

test('manifest view renders text and wires entry to parts to source without selection limits',async()=>{
 const {elements:e,document}=dom();const calls=[];
 const durable={generation:0,can:()=>true,request:async(op,args)=>{calls.push({op,args});return response(op,op==='durable.repo.manifest'?{manifest:manifestResult(args.action,args.offset??0,args.fileOrdinal??null)}:{snapshot});}};
 const view=attachRepoReviewView({document,session:durable});view.state.repositories=[{repository:'sce',namespace:'code'}];view.state.choose('sce');view.state.acceptSnapshot(snapshot);
 e['repo-manifest-entries'].onclick({isTrusted:false});await flush();assert.equal(calls.length,0);
 e['repo-manifest-entries'].onclick({isTrusted:true});await flush();assert.match(e['repo-manifest-rows'].children[0].children[0].textContent,/<script>/);
 e['repo-manifest-rows'].children[0].children[1].onclick({isTrusted:true});await flush();assert.equal(calls.at(-1).args.fileOrdinal,0);
 e['repo-manifest-next'].onclick({isTrusted:true});await flush();assert.equal(calls.at(-1).args.offset,20);
 e['repo-manifest-rows'].children[0].children[1].onclick({isTrusted:true});await flush();assert.equal(calls.at(-2).op,'durable.repo.get');assert.equal(calls.at(-1).args.action,'ENTRIES');
 view.disconnect();assert.equal(view.state.manifest,null);
});

test('NativeClient/real host roundtrip persists repo/review across restart and verifies dependency bytes',async t=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'occ-repo-e2e-')),checkout=path.join(root,'repo'),store=path.join(root,'store');await fs.mkdir(checkout);
 const git=(...args)=>{const r=spawnSync('git',['-C',checkout,...args],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);return r.stdout.trim();};
 git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');git('config','core.autocrlf','false');
 await fs.writeFile(path.join(checkout,'main.py'),'import helper\ndef f():\n    return helper.value\n');await fs.writeFile(path.join(checkout,'helper.py'),'value = 1\n');await fs.writeFile(path.join(checkout,'long.txt'),'Я👋'.repeat(23000));for(let i=0;i<22;i++)await fs.writeFile(path.join(checkout,`fixture-${i}.txt`),`source ${i}`);git('add','-A');git('commit','-qm','fixture');
 const lab=fileURLToPath(new URL('../../content-lab/',import.meta.url));const python=spawnSync(process.platform==='win32'?'python':'python3',['-I','-c','import sys;print(sys.executable)'],{encoding:'utf8'}).stdout.trim();
 const policyPath=path.join(root,'policy.json'),profilePath=path.join(root,'profile.json');await fs.writeFile(policyPath,JSON.stringify({schema:'occ.automation-policy.v1',max_parallel:1,money_budget:0}));
 await fs.writeFile(profilePath,JSON.stringify({schema:'occ.native-durable-profile.v1',store,policy_file:policyPath,namespaces:['code'],templates:{},repositories:{sce:{root:checkout,namespace:'code',source_roots:['.'],exclusions:[]}}}));
 const hosts=[],clients=[];t.after(async()=>{for(const c of clients)c.close();for(const h of hosts)await h.close();await fs.rm(root,{recursive:true,force:true});});
 async function connect(){const host=new JobHost({dataRoot:path.join(root,'ephemeral'),codexPath:'never-invoked',durableCore:{enabled:true,pythonPath:python,adapterPath:path.join(lab,'native_adapter.py'),profilePath}});hosts.push(host);const listeners={};const port={onMessage:{addListener:f=>listeners.message=f},onDisconnect:{addListener:f=>listeners.disconnect=f},disconnect(){},postMessage(m){void host.handle(m).then(r=>listeners.message({...r,requestId:m.requestId,ok:true}),e=>listeners.message({requestId:m.requestId,ok:false,error:e.message}));}};const client=new NativeClient(port);clients.push(client);const durable=new DurableSession();durable.connect(client,await client.request('hello'),'fixture');return {host,client,view:new RepoReviewSession({durable})};}
 const a=await connect();await a.view.loadRepositories();a.view.choose('sce');await a.view.startWholeScan();assert.equal(a.view.run.state,'COMPLETE');
 assert.equal(a.view.durable.can('durable.repo.manifest'),true);let allEntries=[];await a.view.manifestPage('ENTRIES');while(true){allEntries.push(...a.view.manifest.rows);if(a.view.manifest.nextOffset===null)break;await a.view.manifestNext();}assert.equal(allEntries.length,25);
 const long=allEntries.find(r=>r.path==='long.txt');await a.view.manifestPage('PARTS',0,long.ordinal);let allParts=[];while(true){allParts.push(...a.view.manifest.rows);if(a.view.manifest.nextOffset===null)break;await a.view.manifestNext();}assert.equal(allParts.length,long.chunk_count);assert.ok(allParts.length>20);assert.equal(allParts.at(-1).source_end,Buffer.byteLength('Я👋'.repeat(23000)));await a.view.manifestSource(a.view.manifest.rows[0]);assert.equal(a.view.snapshot.files[0].path,'long.txt');
 await a.view.page(20);a.view.select('main.py',true);const exported=await a.view.export('Review data','Source owner',['Prove criterion']);
 assert.deepEqual(exported.document.selection.dependencies,['helper.py']);const result=exported.document.review_result_template;result.findings=[{finding_id:'F001',classification:'CODE_DEFECT',disposition:'DONE',source_key:result.sources[0].source_key,source_sha256:result.sources[0].sha256,criterion:'Model claim',evidence_refs:[],duplicate_of:null,supersedes:null}];
 const imported=await a.view.import('code',JSON.stringify(result));assert.equal(imported.findings[0].closed,false);a.client.close();await a.host.close();
 const b=await connect();const list=await b.view.list('code');assert.equal(list[0].session_id,exported.review.session_id);const replay=await b.view.import('code',JSON.stringify(result));assert.equal(replay.import_state,'UNCHANGED');
 await fs.writeFile(path.join(checkout,'helper.py'),'value = 2\n');const changed=await b.view.get('code',exported.review.session_id);assert.equal(changed.state,'STALE');assert.ok(changed.changed_dependencies.includes('helper.py'));
 assert.equal(changed.execution_authorized,false);assert.equal(changed.repo_binding.source_bytes_verified,false);
});
