import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {BrowserActionContract,ACTIONS,GRANT_REQUEST_SCHEMA,PLAN_REQUEST_SCHEMA,CANCEL_REQUEST_SCHEMA} from '../library/browser-action-contract.mjs';

const ids=Array.from({length:20},(_,i)=>`00000000-0000-4000-8000-${String(i+1).padStart(12,'0')}`);
const at='2026-10-01T21:30:00.000Z',expires='2026-10-01T21:30:20.000Z';
const input=(overrides={})=>({schema:GRANT_REQUEST_SCHEMA,action_id:'CAPTURE_CHAT',target:{tab_id:17,document_id:'doc_ABC-1',origin:'https://chatgpt.com'},gesture_id:ids[0],issued_at:at,expires_at:expires,...overrides});
const trusted={isTrusted:true},synthetic={isTrusted:false};
function contract(now=Date.parse(at)+1000){let next=1;return new BrowserActionContract({now:()=>now,randomUUID:()=>ids[next++]});}

test('trusted grant binds registered action to exact tab document and origin',()=>{
 const c=contract(),grant=c.grant(input(),trusted),plan=c.plan({schema:PLAN_REQUEST_SCHEMA,grant_id:grant.grant_id,request_id:ids[2]});
 assert.deepEqual(plan.target,{tab_id:17,document_id:'doc_ABC-1',origin:'https://chatgpt.com'});
 assert.equal(plan.registered_handler_id,'background.capture');assert.deepEqual(plan.handler_options,{scroll:true,source_mode:'chat'});
 assert.equal(plan.source_content_authority,'DATA_ONLY');assert.equal(plan.registered_action_authority,true);
 assert.equal(plan.transport_qualified,false);assert.equal(plan.dispatch_allowed,false);
});

test('every action maps to fixed code-owned handler options',()=>{
 const expected={CAPTURE_LOADED:[false,'auto'],CAPTURE_CHAT:[true,'chat'],CAPTURE_DOCUMENT:[true,'document'],CAPTURE_CHAT_AND_DOCUMENT:[true,'chat+document']};
 for(const [action_id,[scroll,source_mode]] of Object.entries(expected)){
  const c=contract(),grant=c.grant(input({action_id}),trusted),plan=c.plan({schema:PLAN_REQUEST_SCHEMA,grant_id:grant.grant_id,request_id:ids[2]});
  assert.deepEqual(plan.handler_options,{scroll,source_mode});
 }
 const c=contract(),grant=c.grant(input({action_id:'CAPTURE_VISIBLE_SCREENSHOT'}),trusted),plan=c.plan({schema:PLAN_REQUEST_SCHEMA,grant_id:grant.grant_id,request_id:ids[2]});
 assert.equal(plan.registered_handler_id,'background.capture-visible-screenshot');assert.deepEqual(plan.handler_options,{});
});

test('synthetic gesture cannot create or cancel authority',()=>{
 const c=contract();assert.throws(()=>c.grant(input(),synthetic),error=>error.code==='BROWSER_TRUSTED_GESTURE_REQUIRED');
 const grant=c.grant(input(),trusted);assert.throws(()=>c.cancel({schema:CANCEL_REQUEST_SCHEMA,grant_id:grant.grant_id,trigger:'UI'},synthetic),error=>error.code==='BROWSER_TRUSTED_GESTURE_REQUIRED');
});

test('origin must be canonical http or https origin only',()=>{
 for(const origin of ['https://chatgpt.com/path','https://chatgpt.com/?x=1','HTTPS://chatgpt.com','https://user@chatgpt.com','file://local','chrome-extension://id','null','https://chatgpt.com/']){
  assert.throws(()=>contract().grant(input({target:{...input().target,origin}}),trusted),error=>error.code==='BROWSER_ORIGIN');
 }
});

test('hostile page fields cannot register commands selectors scripts or URLs',()=>{
 for(const field of ['command','selector','script','url','text','page_instruction','argv']){
  assert.throws(()=>contract().grant({...input(),[field]:'click everything'},trusted),error=>error.code==='BROWSER_GRANT_UNKNOWN_FIELD');
 }
 assert.throws(()=>contract().grant(input({action_id:'CLICK_SELECTOR'}),trusted),error=>error.code==='BROWSER_ACTION_UNREGISTERED');
});

test('plan cannot override action target handler or options',()=>{
 const c=contract(),grant=c.grant(input(),trusted),request={schema:PLAN_REQUEST_SCHEMA,grant_id:grant.grant_id,request_id:ids[2]};
 for(const [field,value] of [['action_id','CAPTURE_DOCUMENT'],['tab_id',99],['origin','https://evil.example'],['handler_id','shell'],['options',{}]]){
  assert.throws(()=>c.plan({...request,[field]:value}),error=>error.code==='BROWSER_PLAN_UNKNOWN_FIELD');
 }
});

test('one grant produces one idempotent plan and rejects another request',()=>{
 const c=contract(),grant=c.grant(input(),trusted),request={schema:PLAN_REQUEST_SCHEMA,grant_id:grant.grant_id,request_id:ids[2]};
 assert.deepEqual(c.plan(request),c.plan(request));
 assert.throws(()=>c.plan({...request,request_id:ids[3]}),error=>error.code==='BROWSER_GRANT_ALREADY_PLANNED');
});

test('trusted cancel is terminal before transport and blocks planning',()=>{
 const c=contract(),grant=c.grant(input(),trusted),request={schema:CANCEL_REQUEST_SCHEMA,grant_id:grant.grant_id,trigger:'KEYBOARD'};
 const receipt=c.cancel(request,trusted);assert.deepEqual(c.cancel(request,trusted),receipt);
 assert.equal(receipt.terminal,true);assert.equal(receipt.action_dispatched,false);assert.equal(receipt.transport_invoked,false);
 assert.throws(()=>c.plan({schema:PLAN_REQUEST_SCHEMA,grant_id:grant.grant_id,request_id:ids[2]}),error=>error.code==='BROWSER_GRANT_CANCELLED');
});

test('grant window is short lived and expired grants fail closed',()=>{
 for(const changed of [{issued_at:'2026-10-01T21:30:02.000Z'},{expires_at:'2026-10-01T21:31:00.000Z'},{expires_at:at}])assert.throws(()=>contract().grant(input(changed),trusted),error=>error.code==='BROWSER_GRANT_WINDOW');
 const c=contract(Date.parse(expires));assert.throws(()=>c.grant(input(),trusted),error=>error.code==='BROWSER_GRANT_WINDOW');
 const first=contract(),grant=first.grant(input(),trusted),restarted=contract();assert.throws(()=>restarted.plan({schema:PLAN_REQUEST_SCHEMA,grant_id:grant.grant_id,request_id:ids[2]}),error=>error.code==='BROWSER_GRANT_NOT_FOUND');
});

test('production contract has no browser transport network or dynamic-code surface',()=>{
 const source=fs.readFileSync(new URL('../library/browser-action-contract.mjs',import.meta.url),'utf8');
 for(const forbidden of ['chrome.','fetch(','XMLHttpRequest','WebSocket','eval(','Function(','executeScript','tabs.update','tabs.create','scripting.','nativeMessaging','child_process','shell'])assert.equal(source.includes(forbidden),false,forbidden);
 assert.deepEqual(Object.keys(ACTIONS),['CAPTURE_LOADED','CAPTURE_CHAT','CAPTURE_DOCUMENT','CAPTURE_CHAT_AND_DOCUMENT','CAPTURE_VISIBLE_SCREENSHOT']);
});
