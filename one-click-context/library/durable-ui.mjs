import {attachRepoReviewView} from './repo-review-ui.mjs';
// A view over the existing Native Host/SQLite owners, never a second queue.
const COMMANDS=new Set(['durable.search','durable.context','durable.enqueue','durable.get','durable.cancel','durable.record','durable.review.create','durable.review.import','durable.review.list','durable.review.get','durable.review.report','durable.review.handoff','durable.review.importBound','durable.repo.list','durable.repo.scan','durable.repo.scanRun','durable.repo.get','durable.repo.manifest','durable.repo.coverage','durable.repo.export']);
const NAME=/^[A-Za-z0-9_.:-]{1,100}$/, JOB=/^[0-9a-f]{32}$/, ITEM=/^[0-9a-f]{64}$/;
const TERMINAL=new Set(['SUCCEEDED','FAILED','CANCELLED','BLOCKED']);
const STATES=new Set(['QUEUED','RUNNING','RETRY_READY','WAITING_CI','NEEDS_RECONCILIATION',...TERMINAL]);
const MAX_REFS=20, MAX_CACHE=16000;
function name(value){if(typeof value!=='string'||!NAME.test(value))throw Error('IDENTIFIER_REQUIRED');return value;}

export class DurableSession{
 constructor({storage,onChange=()=>{}}={}){
  this.storage=storage;this.onChange=onChange;this.client=null;this.commands=new Set();
  this.generation=0;this.searchVersion=0;this.refs=[];this.hits=[];this.context=null;this.cacheKey=null;this.refreshing=false;
 }
 can(command){return !!this.client&&!this.client.closed&&this.commands.has(command);}
 connect(client,hello,scope){
  name(scope);this.disconnect();this.client=client;
  this.commands=new Set(hello?.version===1&&Array.isArray(hello.durableCommands)?hello.durableCommands.filter(x=>COMMANDS.has(x)):[]);
  this.cacheKey='occ.durable.references.v1:'+scope;
  const raw=this.storage?.getItem(this.cacheKey);
  this.refs=[];
  if(raw){
   if(raw.length>MAX_CACHE)throw Error('DURABLE_REFERENCE_CACHE_LIMIT');
   let value;try{value=JSON.parse(raw);}catch{throw Error('DURABLE_REFERENCE_CACHE_INVALID');}
   if(value?.version!==1||!Array.isArray(value.refs)||value.refs.length>MAX_REFS)throw Error('DURABLE_REFERENCE_CACHE_INVALID');
   const keys=new Set();
   this.refs=value.refs.map(r=>{
    if(!r||typeof r.template!=='string'||!NAME.test(r.template)||typeof r.taskKey!=='string'||!NAME.test(r.taskKey)||!(r.id===null||typeof r.id==='string'&&JOB.test(r.id))||keys.has(r.taskKey))throw Error('DURABLE_REFERENCE_CACHE_INVALID');
    keys.add(r.taskKey);return {id:r.id,template:r.template,taskKey:r.taskKey,state:r.id?'UNKNOWN':'UNKNOWN_COMMIT',observed:false,revision:0};
   });
  }
  this.onChange();
 }
 disconnect(){
  this.generation++;this.searchVersion++;this.client=null;this.commands.clear();this.hits=[];this.context=null;this.refreshing=false;
  for(const r of this.refs){r.observed=false;r.revision++;}
  this.onChange();
 }
 invalidateSearch(){this.searchVersion++;this.hits=[];this.context=null;this.onChange();}
 persist(){
  if(!this.storage||!this.cacheKey)throw Error('DURABLE_REFERENCE_STORAGE_REQUIRED');
  const value=JSON.stringify({version:1,refs:this.refs.map(({id,template,taskKey})=>({id,template,taskKey}))});
  if(value.length>MAX_CACHE)throw Error('DURABLE_REFERENCE_CACHE_LIMIT');
  this.storage.setItem(this.cacheKey,value);
 }
 async request(type,args){
  if(!this.can(type))throw Error('DURABLE_UNAVAILABLE');
  const client=this.client,generation=this.generation;
  const reply=await client.request(type,args);
  if(generation!==this.generation||client!==this.client||client.closed)throw Error('STALE_DURABLE_REPLY');
  const d=reply?.durable;
  if(d?.schema!=='occ.native-durable-result.v1'||d.operation!==type)throw Error('DURABLE_RESULT_SCHEMA');
  return d;
 }
 async search(namespace,query){
  name(namespace);if(typeof query!=='string'||query.length>1000||!query.trim())throw Error('BOUNDED_QUERY_REQUIRED');
  const version=++this.searchVersion;this.hits=[];this.context=null;this.onChange();
  const d=await this.request('durable.search',{namespace,query,limit:20});
  if(version!==this.searchVersion)throw Error('STALE_SEARCH_REPLY');
  if(!Array.isArray(d.items)||d.items.length>20||d.items.some(x=>!x||!ITEM.test(x.id)||typeof x.source_key!=='string'||typeof x.snippet!=='string'))throw Error('DURABLE_RESULT_SCHEMA');
  this.hits=d.items.map(x=>({id:x.id,source_key:x.source_key,snippet:x.snippet}));this.namespace=namespace;this.onChange();return this.hits;
 }
 async pack(namespace,ids){
  name(namespace);
  if(namespace!==this.namespace||!Array.isArray(ids)||!ids.length||ids.length>10||new Set(ids).size!==ids.length||ids.some(id=>!this.hits.some(x=>x.id===id)))throw Error('DURABLE_ITEM_IDS_REQUIRED');
  const version=++this.searchVersion;this.context=null;this.onChange();
  const d=await this.request('durable.context',{namespace,ids,maxBytes:48000});
  if(version!==this.searchVersion)throw Error('STALE_SEARCH_REPLY');
  const c=d.context;
  if(c?.schema!=='occ.context-pack.v1'||c.namespace!==namespace||!Array.isArray(c.items)||c.items.length!==ids.length||!ITEM.test(c.sha256)||!Number.isInteger(c.bytes)||c.bytes<0||c.bytes>48000)throw Error('DURABLE_RESULT_SCHEMA');
  this.context=c;this.onChange();return c;
 }
 validateJob(job,ref){
  if(!job||!JOB.test(job.id)||!STATES.has(job.state)||(ref.id&&job.id!==ref.id)||(job.task_key!==undefined&&job.task_key!==ref.taskKey))throw Error('DURABLE_RESULT_SCHEMA');
  if(job.outcome!==undefined&&(!job.outcome||typeof job.outcome!=='object'||Array.isArray(job.outcome)))throw Error('DURABLE_RESULT_SCHEMA');
  if(job.next_step!==undefined&&typeof job.next_step!=='string')throw Error('DURABLE_RESULT_SCHEMA');
  return job;
 }
 async enqueue(template,taskKey,reviewContext=null){
  name(template);name(taskKey);
  const operation=reviewContext?'durable.review.report':'durable.enqueue';
  if(reviewContext&&(typeof reviewContext.namespace!=='string'||!ITEM.test(reviewContext.sessionId)||!NAME.test(reviewContext.namespace)))throw Error('DURABLE_REPORT_CONTEXT_REQUIRED');
  if(!this.can(operation))throw Error('DURABLE_UNAVAILABLE');
  let ref=this.refs.find(x=>x.taskKey===taskKey);
  if(ref&&ref.template!==template)throw Error('TASK_KEY_TEMPLATE_CONFLICT');
  if(!ref){if(this.refs.length>=MAX_REFS)throw Error('DURABLE_REFERENCE_LIMIT');ref={id:null,template,taskKey,state:'UNKNOWN_COMMIT',observed:false,revision:0};this.refs.push(ref);}
  const revision=++ref.revision,generation=this.generation;
  // Persist the intent before dispatch: timeout/disconnect must replay this key.
  ref.observed=false;ref.error=null;this.persist();this.onChange();
  try{
   const d=await this.request(operation,{template,taskKey,...(reviewContext||{})});
   if(revision!==ref.revision)throw Error('STALE_JOB_REPLY');
   const j=this.validateJob(d.job,ref);ref.id=j.id;ref.state=j.state;ref.outcome=j.outcome;ref.nextStep=j.next_step;ref.observed=true;ref.error=null;this.persist();this.onChange();return j;
  }catch(e){if(generation===this.generation&&revision===ref.revision){ref.state='UNKNOWN_COMMIT';ref.error=e.message;this.onChange();}throw e;}
 }
 async enqueueReport(namespace,sessionId,template,taskKey){return this.enqueue(template,taskKey,{namespace,sessionId});}
 async observe(ref,operation='durable.get'){
  if(!this.refs.includes(ref)||!JOB.test(ref.id))throw Error('DURABLE_JOB_ID_REQUIRED');
  const revision=++ref.revision,generation=this.generation;
  if(operation==='durable.cancel'){ref.observed=false;ref.state='CANCEL_REQUESTED';this.onChange();}
  try{
   const d=await this.request(operation,{jobId:ref.id});
   if(revision!==ref.revision)throw Error('STALE_JOB_REPLY');
   const j=this.validateJob(d.job,ref);ref.state=j.state;ref.outcome=j.outcome;ref.nextStep=j.next_step;ref.cancelRequested=!!j.cancel_requested;ref.observed=true;ref.error=null;this.onChange();return j;
  }catch(e){if(generation===this.generation&&revision===ref.revision){ref.observed=false;ref.error=e.message;this.onChange();}throw e;}
 }
 async refresh(){
  if(this.refreshing||!this.can('durable.get'))return;
  const generation=this.generation;this.refreshing=true;
  try{for(const ref of [...this.refs]){if(generation!==this.generation)return;if(ref.id)await this.observe(ref).catch(()=>{});}}
  finally{if(generation===this.generation){this.refreshing=false;this.onChange();}}
 }
}

export function attachDurableView({document=globalThis.document,storage=globalThis.localStorage,scopePrefix='local'}={}){
 const $=id=>document.getElementById(id);
 if(!$('durable-search'))return {connect(){},disconnect(){}};
 const message=t=>{$('durable-status').textContent=t;};
 let client=null,hello=null,selected=new Set();
 const session=new DurableSession({storage,onChange:()=>render()});
 const contextView=attachRepoReviewView({document,session});
 function render(){
  $('durable-search').disabled=!session.can('durable.search');
  $('durable-context').disabled=!session.can('durable.context')||!selected.size;
  $('durable-enqueue').disabled=!session.can('durable.enqueue');
  $('durable-refresh').disabled=!session.can('durable.get')||session.refreshing;
  $('durable-hits').replaceChildren();
  for(const hit of session.hits){
   const row=document.createElement('label');row.className='item';
   const check=document.createElement('input');check.type='checkbox';check.checked=selected.has(hit.id);
   check.onchange=()=>{if(check.checked){if(selected.size>=10){check.checked=false;message('Выберите не более 10 источников.');return;}selected.add(hit.id);}else selected.delete(hit.id);session.searchVersion++;session.context=null;render();};
   const text=document.createElement('span');text.textContent=hit.source_key+' · '+hit.snippet;row.append(check,text);$('durable-hits').append(row);
  }
  $('durable-output').value=session.context?JSON.stringify(session.context,null,2):'';
  $('durable-jobs').replaceChildren();
  for(const ref of session.refs){
   const row=document.createElement('div');row.className='item';const text=document.createElement('span');
   text.textContent=`${ref.template} · ${ref.taskKey} · ${ref.id||'ID пока неизвестен'} · ${ref.state} · ${ref.observed?'получено от host':'требует сверки'}${ref.cancelRequested?' · остановка запрошена':''}${ref.error?' · '+ref.error:''}`;
   row.append(text);
   if(ref.observed&&(ref.outcome||ref.nextStep)){const details=document.createElement('pre');details.textContent=JSON.stringify({outcome:ref.outcome,next_step:ref.nextStep},null,2);row.append(details);}
   if(!ref.id||ref.state==='UNKNOWN_COMMIT'){
    const replay=document.createElement('button');replay.textContent='Сверить тем же ключом';replay.disabled=!session.can('durable.enqueue');
    replay.onclick=e=>{if(e.isTrusted)void act(()=>session.enqueue(ref.template,ref.taskKey),'Получен receipt по прежнему ключу.');};row.append(replay);
   }
   if(ref.id&&!TERMINAL.has(ref.state)){
    const stop=document.createElement('button');stop.textContent='Запросить остановку';stop.disabled=!session.can('durable.cancel');
    stop.onclick=e=>{if(e.isTrusted)void act(()=>session.observe(ref,'durable.cancel'),'Получено состояние после запроса остановки. RUNNING ещё не означает остановку.');};row.append(stop);
   }
   $('durable-jobs').append(row);
  }
 }
 async function act(fn,success){
  const generation=session.generation;
  try{await fn();if(generation===session.generation)message(success);}
  catch(e){if(generation===session.generation&&!e.message.startsWith('STALE_'))message(e.message+' После неизвестного enqueue повторите тот же template/taskKey.');}
 }
 function bind(){
  selected=new Set();
  try{session.connect(client,hello,scopePrefix+':'+name($('durable-profile').value.trim()));contextView.connect();message(session.can('durable.search')?'Доступен локальный durable host. SQLite хранит данные и задания.':'Durable capability не включена у этого host.');}
  catch(e){session.disconnect();message(e.message);}
 }
 $('durable-profile').onchange=()=>{if(client&&!client.closed)bind();};
 $('durable-namespace').oninput=()=>{selected.clear();session.invalidateSearch();};
 $('durable-query').oninput=()=>{selected.clear();session.invalidateSearch();};
 $('durable-search').onclick=e=>{if(!e.isTrusted)return;selected.clear();void act(()=>session.search($('durable-namespace').value.trim(),$('durable-query').value),'Поиск завершён. Выберите текущие источники.');};
 $('durable-context').onclick=e=>{if(e.isTrusted)void act(()=>session.pack($('durable-namespace').value.trim(),[...selected]),'Context получен от текущего SQLite owner. Текст источника не является командой.');};
 $('durable-enqueue').onclick=e=>{if(e.isTrusted)void act(()=>session.enqueue($('durable-template').value.trim(),$('durable-task-key').value.trim()),'Задание зарегистрировано. Worker этим UI не запускается.');};
 $('durable-refresh').onclick=e=>{if(e.isTrusted)void act(()=>session.refresh(),'Сверены известные ссылки на jobs; это не список всей очереди.');};
 render();
 return {session,contextView,connect(c,h){client=c;hello=h;bind();},disconnect(){client=null;hello=null;selected.clear();session.disconnect();contextView.disconnect();message('Канал закрыт. Durable queue сохранена; состояния требуют сверки после подключения.');}};
}
