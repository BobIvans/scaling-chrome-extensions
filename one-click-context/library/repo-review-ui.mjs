// A view over the existing durable adapter and review ledger.
export const REVIEW_NATIVE_INPUT_BYTES=16000;
const HASH=/^[0-9a-f]{64}$/;
const bytes=value=>new TextEncoder().encode(value).length;

export function parseReviewInput(raw,namespace,sessionId=null){
 if(typeof raw!=='string'||bytes(raw)>REVIEW_NATIVE_INPUT_BYTES)throw Error('REVIEW_NATIVE_INPUT_LIMIT');
 const value=JSON.parse(raw);
 // JSON.parse otherwise drops duplicate keys before the native strict parser.
 const tokens=raw.match(/"(?:\\.|[^"\\])*"|[{}\[\]:,]|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null/g)||[];
 let pos=0;
 function walk(depth=0){
  if(depth>64)throw Error('REVIEW_JSON_DEPTH');
  const token=tokens[pos++];
  if(token==='{'){
   const keys=new Set();
   while(tokens[pos]!=='}'){
    const key=JSON.parse(tokens[pos++]);if(keys.has(key))throw Error('REVIEW_DUPLICATE_KEY');keys.add(key);pos++;walk(depth+1);
    if(tokens[pos]!==',')break;pos++;
   }pos++;
  }else if(token==='['){while(tokens[pos]!==']'){walk(depth+1);if(tokens[pos]!==',')break;pos++;}pos++;}
 }
 walk();
 const envelope=value.schema==='occ.review_bundle.v5'?{type:'durable.review.importBound',namespace,sessionId,review:value}:{type:'durable.review.import',namespace,review:value};
 if(bytes(JSON.stringify(envelope))>REVIEW_NATIVE_INPUT_BYTES)throw Error('REVIEW_NATIVE_INPUT_LIMIT');
 return value;
}

export class RepoReviewSession{
 constructor({durable,onChange=()=>{}}){this.durable=durable;this.onChange=onChange;this.version=0;this.reset();}
 reset(){this.stopScanPump();this.run=null;this.scanIntent=null;this.scanError=null;this.scanControlPending=null;this.version++;this.repositories=[];this.repository=null;this.namespace=null;this.snapshot=null;this.selected=new Set();this.exported=null;this.handoff=null;this.reviews=[];this.review=null;this.reportJob=null;this.busy=false;this.onChange();}
 invalidate(){this.version++;this.exported=null;this.handoff=null;this.reportJob=null;this.review=null;this.onChange();}
 async call(type,args={}){return this.durable.request(type,args);}
 async loadRepositories(){
  const version=++this.version;const d=await this.call('durable.repo.list');
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(!Array.isArray(d.repositories)||d.repositories.length>20||d.repositories.some(r=>typeof r.repository!=='string'||typeof r.namespace!=='string'))throw Error('REPO_RESULT_SCHEMA');
  this.repositories=d.repositories;this.onChange();return d.repositories;
 }
 choose(alias){this.stopScanPump();this.run=null;this.scanIntent=null;this.scanError=null;this.scanControlPending=null;const repo=this.repositories.find(r=>r.repository===alias);if(!repo)throw Error('REPO_OUTSIDE_OPERATOR_SCOPE');this.version++;this.repository=alias;this.namespace=repo.namespace;this.snapshot=null;this.selected.clear();this.exported=null;this.handoff=null;this.reportJob=null;this.review=null;this.reviews=[];this.onChange();}
 select(path,checked){if(!this.snapshot?.files.some(f=>f.path===path&&f.state==='INDEXED'))throw Error('REPO_PATH_OUTSIDE_SNAPSHOT');if(checked&&this.selected.size>=10&&!this.selected.has(path))throw Error('REPO_SELECTION_LIMIT');checked?this.selected.add(path):this.selected.delete(path);this.invalidate();}
 acceptSnapshot(s){if(s?.schema!=='occ.repo-snapshot.v1'||s.alias!==this.repository||s.namespace!==this.namespace||!HASH.test(s.snapshot_id)||!Array.isArray(s.files)||!Number.isInteger(s.cursor)||!Number.isInteger(s.total)||s.cursor<0||s.cursor>s.total)throw Error('REPO_RESULT_SCHEMA');this.snapshot=s;this.exported=null;this.handoff=null;this.review=null;this.onChange();return s;}
 async scan({fresh=false}={}){
  if(!this.repository)throw Error('REPO_SELECTION_REQUIRED');
  const version=++this.version;
  const args={repository:this.repository,...(!fresh&&this.snapshot?{snapshotId:this.snapshot.snapshot_id}:{})};
  const d=await this.call('durable.repo.scan',args);if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(fresh)this.selected.clear();return this.acceptSnapshot(d.snapshot);
 }
 // The pump has a separate generation from review/source selection. A late
 // reply cannot resume a paused run, a different repository or a new client.
 stopScanPump(){this.scanGeneration=(this.scanGeneration||0)+1;this.scanPumping=false;}
 scanScope(){return {generation:this.scanGeneration,client:this.durable.generation,repository:this.repository};}
 currentScan(scope){return scope.generation===this.scanGeneration&&scope.client===this.durable.generation&&scope.repository===this.repository;}
 scanAvailable(){if(!this.durable.can('durable.repo.scanRun'))throw Error('WHOLE_REPO_SCAN_UNAVAILABLE');if(!this.repository)throw Error('REPO_SELECTION_REQUIRED');}
 acceptRun(run){
  if(run===null){this.run=null;this.onChange();return null;}
  const states=['RUNNING','PAUSED','CANCELLED','COMPLETE','BLOCKED','FAILED'];
  if(run?.schema!=='occ.repo-scan-run.v1'||run.repository!==this.repository||run.namespace!==this.namespace||!HASH.test(run.run_id)||!HASH.test(run.snapshot_id)||!states.includes(run.state)||['cursor','total','processed','pending','run_revision'].some(k=>!Number.isSafeInteger(run[k])||run[k]<0)||run.cursor>run.total||run.processed+run.pending!==run.total)throw Error('REPO_SCAN_RESULT_SCHEMA');
  if(this.run?.run_id===run.run_id&&(this.run.run_revision>run.run_revision||this.run.cursor>run.cursor))return this.run;
  this.run=run;this.scanIntent=run.intent_key;this.scanError=null;
  this.acceptSnapshot({...run,schema:'occ.repo-snapshot.v1',state:run.inventory_complete&&run.exact_for_indexed?'COMPLETE':'PENDING',accounted:run.ledger_entries,files:run.files||[]});
  return run;
 }
 async scanRequest(action,fields={}){return (await this.call('durable.repo.scanRun',{repository:this.repository,action,...fields})).scan_run;}
 async restoreScan(){
  this.scanAvailable();this.stopScanPump();const scope=this.scanScope();
  const run=await this.scanRequest('STATUS');if(!this.currentScan(scope))throw Error('STALE_SCAN_REPLY');
  return this.acceptRun(run); // Reconnect is observation, never a STEP.
 }
 async scanFailure(error,scope){
  if(!this.currentScan(scope))return;
  this.scanPumping=false;this.scanError=error.message;this.onChange();
  try{const run=await this.scanRequest('STATUS',this.run?{runId:this.run.run_id}:{});if(this.currentScan(scope)){this.acceptRun(run);this.scanError=error.message;this.onChange();}}catch{/* Remains visibly uncertain; explicit restore is required. */}
 }
 async startWholeScan(){
  this.scanAvailable();if(this.scanPumping||this.scanControlPending)throw Error('SCAN_ALREADY_RUNNING');
  this.stopScanPump();const scope=this.scanScope();
  if(this.stepInFlight)await this.stepInFlight.catch(()=>{});
  if(!this.currentScan(scope))return;
  const replayIntent=!this.run&&this.scanError?this.scanIntent:null;
  this.version++;this.run=null;this.selected.clear();this.exported=null;
  this.scanIntent=replayIntent||crypto.randomUUID().replaceAll('-','');
  try{
   const run=await this.scanRequest('START',{intentKey:this.scanIntent});
   if(!this.currentScan(scope))return;
   this.acceptRun(run);await this.pumpScan(scope);
  }catch(error){if(this.scanError!==error.message)await this.scanFailure(error,scope);throw error;}
 }
 async pumpScan(scope=this.scanScope()){
  if(!this.currentScan(scope)||this.run?.state!=='RUNNING')return;
  this.scanPumping=true;this.onChange();
  try{
   while(this.currentScan(scope)&&this.run?.state==='RUNNING'){
    await new Promise(resolve=>setTimeout(resolve,0));
    if(!this.currentScan(scope)||!this.scanPumping)return;
    if(this.stepInFlight)throw Error('SCAN_STEP_IN_FLIGHT');
    const previous=this.run;
    const pending=this.scanRequest('STEP',{runId:previous.run_id,expectedCursor:previous.cursor,expectedRevision:previous.run_revision});
    this.stepInFlight=pending;
    let run;
    try{run=await pending;}finally{if(this.stepInFlight===pending)this.stepInFlight=null;}
    if(!this.currentScan(scope))return;
    if(run?.run_id!==previous.run_id)throw Error('REPO_SCAN_RESULT_SCHEMA');
    this.acceptRun(run);
    if(run.state==='RUNNING'&&run.cursor<=previous.cursor)throw Error('SCAN_NO_PROGRESS');
   }
  }catch(error){if(this.scanError!==error.message)await this.scanFailure(error,scope);throw error;}
  finally{if(this.currentScan(scope)){this.scanPumping=false;this.onChange();}}
 }
 async controlScan(action){
  this.scanAvailable();if(!this.run)throw Error('REPO_SCAN_REQUIRED');
  if(!['PAUSE','CONTINUE','CANCEL'].includes(action))throw Error('DURABLE_SCHEMA');
  this.stopScanPump();const scope=this.scanScope(),runId=this.run.run_id;
  this.scanControlPending=action;this.onChange();
  try{
   // Stop scheduling immediately. Reconcile the already-started page before
   // using its control revision, including an unknown/lost page response.
   if(this.stepInFlight)await this.stepInFlight.catch(()=>{});
   if(!this.currentScan(scope))return;
   const observed=await this.scanRequest('STATUS',{runId});
   if(!this.currentScan(scope))return;this.acceptRun(observed);
   const run=await this.scanRequest(action,{runId,expectedRevision:observed.run_revision});
   if(!this.currentScan(scope))return;this.acceptRun(run);
   this.scanControlPending=null;this.onChange();
   if(action==='CONTINUE')await this.pumpScan(scope);
   return this.run;
  }catch(error){if(this.scanError!==error.message)await this.scanFailure(error,scope);throw error;}
  finally{if(this.currentScan(scope)){this.scanControlPending=null;this.onChange();}}
 }
 async page(offset){
  if(!this.snapshot)throw Error('REPO_SCAN_REQUIRED');const version=++this.version;
  const d=await this.call('durable.repo.get',{repository:this.repository,snapshotId:this.snapshot.snapshot_id,offset});
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');return this.acceptSnapshot(d.snapshot);
 }
 async export(goal,scope,acceptance,sourceOffset=0){
  if(this.snapshot?.state!=='COMPLETE'||!this.selected.size)throw Error('CONTEXT_INCOMPLETE');
  const version=++this.version;this.exported=null;this.onChange();
  if(!Number.isSafeInteger(sourceOffset)||sourceOffset<0)throw Error('REPO_SOURCE_OFFSET_REQUIRED');
  const args={repository:this.repository,snapshotId:this.snapshot.snapshot_id,paths:[...this.selected],goal,scope,acceptance,maxBytes:24000,...(sourceOffset?{sourceOffset}:{})};
  if(bytes(JSON.stringify({type:'durable.repo.export',...args}))>REVIEW_NATIVE_INPUT_BYTES)throw Error('REVIEW_NATIVE_INPUT_LIMIT');
  const d=await this.call('durable.repo.export',args);if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(d.export?.document?.schema!=='occ.repo-request.v1'||!HASH.test(d.export?.review?.session_id)||d.export.review.namespace!==this.namespace)throw Error('REPO_RESULT_SCHEMA');
  this.exported=d.export;this.review=d.export.review;this.onChange();return this.exported;
 }
 async list(namespace=this.namespace){
  const version=++this.version;const d=await this.call('durable.review.list',{namespace,limit:20});
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(!Array.isArray(d.reviews)||d.reviews.length>20||d.reviews.some(r=>!HASH.test(r.session_id)||r.namespace!==namespace))throw Error('REVIEW_RESULT_SCHEMA');
  this.reviews=d.reviews;this.onChange();return this.reviews;
 }
 async get(namespace,sessionId){
  const version=++this.version;const d=await this.call('durable.review.get',{namespace,sessionId,includeContent:true});
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(d.review?.session_id!==sessionId||d.review.namespace!==namespace)throw Error('REVIEW_RESULT_SCHEMA');
  this.review=d.review;this.handoff=null;this.onChange();return d.review;
 }
 async import(namespace,raw){
  const sessionId=this.review?.session_id,value=parseReviewInput(raw,namespace,sessionId);const version=++this.version;
  const bound=value.schema==='occ.review_bundle.v5';
  if(bound&&(!sessionId||this.review.namespace!==namespace))throw Error('HANDOFF_SELECTED_SESSION_REQUIRED');
  const d=await this.call(bound?'durable.review.importBound':'durable.review.import',{namespace,...(bound?{sessionId}:{}),review:value});
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(d.review?.session_id!==(bound?sessionId:value.session_id)||d.review.namespace!==namespace)throw Error('REVIEW_RESULT_SCHEMA');
  this.review=d.review;this.handoff=null;this.onChange();return d.review;
 }
 async exportHandoff(){
  if(!this.review)throw Error('HANDOFF_SELECTED_SESSION_REQUIRED');
  const version=this.version,id=this.review.session_id;
  const d=await this.call('durable.review.handoff',{namespace:this.review.namespace,sessionId:id});
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(d.handoff?.binding_v7?.session_id!==id||typeof d.handoff.rendered_txt!=='string')throw Error('HANDOFF_RESULT_SCHEMA');
  this.handoff=d.handoff;this.onChange();return d.handoff;
 }
 async enqueueReport(template,taskKey){
  const r=this.review;
  if(!r?.session_id||r.state!=='NEEDS_REVIEW')throw Error('REPORT_CURRENT_COMPLETE_REVIEW_REQUIRED');
  const version=this.version;
  const job=await this.durable.enqueueReport(r.namespace,r.session_id,template,taskKey);
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(!/^[0-9a-f]{32}$/.test(job?.id))throw Error('DURABLE_RESULT_SCHEMA');
  this.reportJob=job;this.onChange();return job;
 }
 async refreshReport(){
  if(!this.reportJob)throw Error('REPORT_JOB_REQUIRED');
  const version=this.version,id=this.reportJob.id;
  const d=await this.call('durable.get',{jobId:id});
  if(version!==this.version)throw Error('STALE_CONTEXT_REPLY');
  if(d.job?.id!==id)throw Error('DURABLE_RESULT_SCHEMA');
  this.reportJob=d.job;this.onChange();return d.job;
 }
}

export function attachRepoReviewView({document=globalThis.document,session:durable}={}){
 const $=id=>document.getElementById(id);
 if(!$('repo-panel'))return {connect(){},disconnect(){}};
 const notice=t=>{$('repo-status').textContent=t;};
 let state;
 function render(){
  if(!state)return;
  for(const [id,command] of [['repo-list','durable.repo.list'],['repo-scan','durable.repo.scanRun'],['repo-rescan','durable.repo.scanRun'],['review-list','durable.review.list'],['review-import','durable.review.import']])$(id).disabled=state.busy||!durable.can(command);
  for(const [id,action] of [['repo-pause','PAUSE'],['repo-continue','CONTINUE'],['repo-stop','CANCEL']])if($(id))$(id).disabled=!durable.can('durable.repo.scanRun')||!!state.scanControlPending||!state.run||!['RUNNING','PAUSED'].includes(state.run.state)||(action==='PAUSE'&&(!state.scanPumping||state.run.state!=='RUNNING'))||(action==='CONTINUE'&&state.scanPumping);
  $('repo-scan').disabled ||= !!state.run&&['RUNNING','PAUSED'].includes(state.run.state);
  $('repo-rescan').disabled ||= !!state.run&&['RUNNING','PAUSED'].includes(state.run.state);
  $('repo-export').disabled=state.busy||!durable.can('durable.repo.export')||state.snapshot?.state!=='COMPLETE'||!state.selected.size;
  if($('repo-export-next'))$('repo-export-next').disabled=state.busy||!durable.can('durable.repo.export')||state.exported?.document?.selection?.next_source_offset==null;
  $('repo-next').disabled=state.busy||!durable.can('durable.repo.get')||state.snapshot?.next_offset==null;
  $('repo-prev').disabled=state.busy||!durable.can('durable.repo.get')||!state.snapshot?.offset;
  $('repo-copy').disabled=!state.exported;
  $('repo-download').disabled=!state.exported;
  $('repo-repository').replaceChildren();
  for(const r of state.repositories){const option=document.createElement('option');option.value=r.repository;option.textContent=r.repository+' · '+r.namespace;$('repo-repository').append(option);}
  if(state.repository)$('repo-repository').value=state.repository;
  const s=state.snapshot;
  $('repo-progress').textContent=s?`${state.scanControlPending||state.run?.state||s.state}: обработано ${state.run?.processed??(s.total-(s.counts?.PENDING||0))}/${s.total} · cursor ${s.cursor}/${s.total} · ${s.repo_sha} · ${JSON.stringify(s.counts)}${state.scanError?' · '+state.scanError:''}`:'Выберите настроенный репозиторий.';
  if($('repo-inventory-details'))$('repo-inventory-details').textContent=s?JSON.stringify({ledger_entries:s.accounted,processed:s.total-(s.counts?.PENDING||0),pending:s.counts?.PENDING||0,total:s.total,roundtrip:s.roundtrip,changes:s.changes,ai_delivery:'NOT_PERFORMED'},null,2):'';
  $('repo-files').replaceChildren();
  for(const f of s?.files||[]){
   const row=document.createElement('label');row.className='item';const check=document.createElement('input');check.type='checkbox';check.disabled=f.state!=='INDEXED';check.checked=state.selected.has(f.path);
   check.onchange=()=>{try{state.select(f.path,check.checked);}catch(e){check.checked=false;notice(e.message);}};
   const text=document.createElement('span');text.textContent=`${f.path} · ${f.state}${f.reason?' · '+f.reason:''}${f.working_state?' · '+f.working_state:''} · ${f.parser||'metadata'}`;
   row.append(check,text);
   for(const finding of f.findings||[]){const button=document.createElement('button');button.textContent='Разобрать: '+finding.criterion;button.onclick=e=>{if(!e.isTrusted)return;try{state.select(f.path,true);$('repo-goal').value=finding.criterion;notice('Файл выбран. Укажите область и критерии, затем экспортируйте запрос.');}catch(error){notice(error.message);}};row.append(button);}
   $('repo-files').append(row);
  }
  $('repo-output').value=state.exported?JSON.stringify(state.exported.document,null,2):'';
  if($('repo-coverage'))$('repo-coverage').textContent=state.exported?JSON.stringify({coverage:state.exported.document.selection?.coverage,source_offset:state.exported.document.selection?.source_offset,next_source_offset:state.exported.document.selection?.next_source_offset,source_total:state.exported.document.selection?.source_total,omitted:state.exported.document.selection?.omitted_count}):'';
  $('review-sessions').replaceChildren();
  for(const r of state.reviews){const button=document.createElement('button');button.textContent=r.session_id.slice(0,12)+' · '+r.state;button.onclick=e=>{if(e.isTrusted)void act(()=>state.get(r.namespace,r.session_id),'Review сверён с источниками.');};$('review-sessions').append(button);}
  const r=state.review;
  $('review-details').textContent=r?JSON.stringify({state:r.state,repo_binding:r.repo_binding,coverage:r.coverage,unaccounted_sources:r.unaccounted_sources,findings:r.finding_details||r.findings,missing:r.missing_dependencies,changed:r.changed_dependencies,next_step:r.next_step,request:r.request_meta},null,2):'Сессия review ещё не выбрана.';
  if($('review-report-enqueue'))$('review-report-enqueue').disabled=state.busy||!durable.can('durable.review.report')||r?.state!=='NEEDS_REVIEW';
  if($('review-report-refresh'))$('review-report-refresh').disabled=state.busy||!state.reportJob||!durable.can('durable.get');
  if($('review-report-status'))$('review-report-status').textContent=state.reportJob?JSON.stringify(state.reportJob,null,2):'Отчёт ещё не поставлен в очередь. Выберите настроенный оператором template.';
  if($('review-handoff'))$('review-handoff').disabled=state.busy||!state.review||!durable.can('durable.review.handoff');
  if($('review-handoff-download'))$('review-handoff-download').disabled=!state.handoff;
  if($('review-handoff-txt'))$('review-handoff-txt').value=state.handoff?.rendered_txt||'';
  $('review-next-request').value=r?JSON.stringify({session_id:r.session_id,goal:r.request_meta?.goal,next_step:r.next_step,missing:r.missing_dependencies,changed:r.changed_dependencies,criteria:(r.finding_details||[]).map(f=>({finding_id:f.finding_id,criterion:f.criterion})),authority:'DATA_ONLY'},null,2):'';
 }
 state=new RepoReviewSession({durable,onChange:render});
 async function act(fn,message){
  if(state.busy)return;const generation=durable.generation;state.busy=true;render();
  try{await fn();if(generation===durable.generation)notice(message);}
  catch(e){if(generation===durable.generation&&!e.message.startsWith('STALE_'))notice(e.message==='REVIEW_NATIVE_INPUT_LIMIT'?'Review превышает 16 000 байт native transport. Сократите JSON или импортируйте файл через локальный review CLI (до 128 000 байт).':e.message);}
  finally{if(generation===durable.generation){state.busy=false;render();}}
 }
 $('repo-list').onclick=e=>{if(e.isTrusted)void act(async()=>{await state.loadRepositories();if(state.repositories.length){state.choose(state.repositories[0].repository);$('review-namespace').value=state.namespace;if(durable.can('durable.repo.scanRun'))await state.restoreScan();}},'Настроенные репозитории получены.');};
 $('repo-repository').onchange=()=>{try{state.choose($('repo-repository').value);$('review-namespace').value=state.namespace;if(durable.can('durable.repo.scanRun'))void state.restoreScan().catch(e=>notice(e.message));}catch(e){notice(e.message);}};
 $('repo-scan').onclick=e=>{if(e.isTrusted)void act(()=>state.startWholeScan(),'Проход repo сохранён. Исключения и ошибки видны в счётчиках.');};
 $('repo-rescan').onclick=e=>{if(e.isTrusted)void act(()=>state.startWholeScan(),'Текущий HEAD выбран; полный проход сохранён.');};
 for(const [id,action] of [['repo-pause','PAUSE'],['repo-continue','CONTINUE'],['repo-stop','CANCEL']])if($(id))$(id).onclick=e=>{
  if(!e.isTrusted)return;notice(action==='CANCEL'?'Остановка ожидается: текущая порция может завершиться.':'Запрошено '+action);
  void state.controlScan(action).then(()=>notice('Состояние сохранено: '+state.run.state),error=>notice(error.message));
 };
 $('repo-next').onclick=e=>{if(e.isTrusted)void act(()=>state.page(state.snapshot.next_offset),'Следующая страница файлов.');};
 $('repo-prev').onclick=e=>{if(e.isTrusted)void act(()=>state.page(Math.max(0,state.snapshot.offset-20)),'Предыдущая страница файлов.');};
 for(const id of ['repo-goal','repo-scope','repo-acceptance'])$(id).oninput=()=>state.invalidate();
 $('repo-export').onclick=e=>{if(e.isTrusted)void act(()=>state.export($('repo-goal').value,$('repo-scope').value,$('repo-acceptance').value.split('\n').map(x=>x.trim()).filter(Boolean)),'Запрос и review session сохранены. Проверьте coverage и пропуски перед передачей в AI.');};
 if($('repo-export-next'))$('repo-export-next').onclick=e=>{if(e.isTrusted&&state.exported?.document?.selection?.next_source_offset!=null){const offset=state.exported.document.selection.next_source_offset;void act(()=>state.export($('repo-goal').value,$('repo-scope').value,$('repo-acceptance').value.split('\n').map(x=>x.trim()).filter(Boolean),offset),'Следующая часть context экспортирована. Сохраните каждую часть отдельно.');}};
 $('repo-copy').onclick=e=>{if(e.isTrusted&&state.exported)void act(()=>globalThis.navigator.clipboard.writeText($('repo-output').value),'Запрос скопирован.');};
 $('repo-download').onclick=e=>{if(!e.isTrusted||!state.exported)return;const url=URL.createObjectURL(new Blob([$('repo-output').value],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='OCC_REVIEW_REQUEST_'+state.exported.review.session_id.slice(0,12)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 $('review-list').onclick=e=>{if(e.isTrusted)void act(()=>state.list($('review-namespace').value.trim()),'Сохранённые review sessions получены.');};
 $('review-import').onclick=e=>{if(e.isTrusted)void act(async()=>{const r=await state.import($('review-namespace').value.trim(),$('review-input').value);await state.get(r.namespace,r.session_id);},'Review импортирован. DONE остаётся заявлением до проверки evidence.');};
 $('review-file').onchange=async e=>{const file=e.target.files?.[0];if(!file)return;if(file.size>REVIEW_NATIVE_INPUT_BYTES){notice('Файл превышает лимит native import: 16 000 байт включая request.');return;}$('review-input').value=await file.text();};
 if($('review-report-enqueue'))$('review-report-enqueue').onclick=e=>{if(e.isTrusted)void act(()=>state.enqueueReport($('review-report-template').value.trim(),$('review-report-key').value.trim()),'Отчёт поставлен в существующую очередь. Для создания файла запустите настроенный локальный worker; затем обновите статус.');};
 if($('review-report-refresh'))$('review-report-refresh').onclick=e=>{if(e.isTrusted)void act(()=>state.refreshReport(),'Получен статус worker и проверка результата.');};
 if($('review-handoff'))$('review-handoff').onclick=e=>{if(e.isTrusted)void act(()=>state.exportHandoff(),'V4 request + V5 overlay собраны из текущих host-bound источников.');};
 if($('review-handoff-download'))$('review-handoff-download').onclick=e=>{if(!e.isTrusted||!state.handoff)return;const url=URL.createObjectURL(new Blob([state.handoff.rendered_txt],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='REQUEST_TO_AI_RU_'+state.handoff.binding_v7.session_id.slice(0,12)+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 render();
 return {state,connect(){state.reset();notice(durable.can('durable.repo.list')?'Подключён repo/review host. Получите список репозиториев.':'Установленный host ещё не поддерживает repo/review.');render();},disconnect(){state.reset();notice('Канал закрыт. Scan и review сохранены в локальном store.');render();}};
}
