export const GRANT_REQUEST_SCHEMA='occ.browser-action-grant-request.v1';
export const GRANT_SCHEMA='occ.browser-action-grant.v1';
export const PLAN_REQUEST_SCHEMA='occ.browser-action-plan-request.v1';
export const PLAN_SCHEMA='occ.browser-action-plan.v1';
export const CANCEL_REQUEST_SCHEMA='occ.browser-action-cancel-request.v1';
export const CANCEL_RECEIPT_SCHEMA='occ.browser-action-cancel-receipt.v1';
export const MAX_GRANT_MILLISECONDS=30000;

export const ACTIONS=Object.freeze({
 CAPTURE_LOADED:Object.freeze({handler_id:'background.capture',options:Object.freeze({scroll:false,source_mode:'auto'})}),
 CAPTURE_CHAT:Object.freeze({handler_id:'background.capture',options:Object.freeze({scroll:true,source_mode:'chat'})}),
 CAPTURE_DOCUMENT:Object.freeze({handler_id:'background.capture',options:Object.freeze({scroll:true,source_mode:'document'})}),
 CAPTURE_CHAT_AND_DOCUMENT:Object.freeze({handler_id:'background.capture',options:Object.freeze({scroll:true,source_mode:'chat+document'})}),
 CAPTURE_VISIBLE_SCREENSHOT:Object.freeze({handler_id:'background.capture-visible-screenshot',options:Object.freeze({})})
});

const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u;
const DOCUMENT=/^[A-Za-z0-9_-]{1,128}$/u;
const fail=code=>{throw Object.assign(new Error(code),{code});};
const clone=value=>JSON.parse(JSON.stringify(value));

function exact(value,keys,code){
 if(!value||typeof value!=='object'||Array.isArray(value))fail(code+'_TYPE');
 const actual=Object.keys(value);for(const key of keys)if(!Object.hasOwn(value,key))fail(code+'_MISSING');
 if(actual.some(key=>!keys.includes(key)))fail(code+'_UNKNOWN_FIELD');
}
function uuid(value,code){if(typeof value!=='string'||!UUID.test(value))fail(code);return value;}
function timestamp(value,code){
 if(typeof value!=='string'||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$/u.test(value))fail(code);
 const time=Date.parse(value);if(!Number.isFinite(time)||new Date(time).toISOString()!==value)fail(code);return time;
}
function target(value){
 exact(value,['tab_id','document_id','origin'],'BROWSER_TARGET');
 if(!Number.isSafeInteger(value.tab_id)||value.tab_id<1||value.tab_id>2147483647)fail('BROWSER_TAB_ID');
 if(typeof value.document_id!=='string'||!DOCUMENT.test(value.document_id))fail('BROWSER_DOCUMENT_ID');
 if(typeof value.origin!=='string'||value.origin.length>253)fail('BROWSER_ORIGIN');
 let parsed;try{parsed=new URL(value.origin);}catch{fail('BROWSER_ORIGIN');}
 if(!['http:','https:'].includes(parsed.protocol)||parsed.username||parsed.password||parsed.origin!==value.origin||parsed.href!==value.origin+'/')fail('BROWSER_ORIGIN');
 return {tab_id:value.tab_id,document_id:value.document_id,origin:value.origin};
}
function trusted(event){if(!event||event.isTrusted!==true)fail('BROWSER_TRUSTED_GESTURE_REQUIRED');}

export class BrowserActionContract{
 constructor({now=()=>Date.now(),randomUUID=()=>crypto.randomUUID()}={}){this.now=now;this.randomUUID=randomUUID;this.grants=new Map();}
 grant(input,event){
  trusted(event);exact(input,['schema','action_id','target','gesture_id','issued_at','expires_at'],'BROWSER_GRANT');
  if(input.schema!==GRANT_REQUEST_SCHEMA)fail('BROWSER_GRANT_SCHEMA');
  if(typeof input.action_id!=='string'||!Object.hasOwn(ACTIONS,input.action_id))fail('BROWSER_ACTION_UNREGISTERED');
  uuid(input.gesture_id,'BROWSER_GESTURE_ID');const boundTarget=target(input.target);
  const issued=timestamp(input.issued_at,'BROWSER_ISSUED_AT'),expires=timestamp(input.expires_at,'BROWSER_EXPIRES_AT'),now=this.now();
  if(!Number.isSafeInteger(now)||issued>now||now>=expires||expires-issued<1||expires-issued>MAX_GRANT_MILLISECONDS)fail('BROWSER_GRANT_WINDOW');
  const grantId=uuid(this.randomUUID(),'BROWSER_GRANT_ID');if(this.grants.has(grantId))fail('BROWSER_GRANT_ID_COLLISION');
  const action=ACTIONS[input.action_id],value={schema:GRANT_SCHEMA,grant_id:grantId,action_id:input.action_id,target:boundTarget,gesture_id:input.gesture_id,issued_at:input.issued_at,expires_at:input.expires_at,registered_handler_id:action.handler_id,source:'TRUSTED_EXTENSION_UI',state:'GRANTED',transport_qualified:false,dispatch_allowed:false};
  this.grants.set(grantId,{grant:value,requestId:null,plan:null,cancelReceipt:null});return clone(value);
 }
 plan(input){
  exact(input,['schema','grant_id','request_id'],'BROWSER_PLAN');if(input.schema!==PLAN_REQUEST_SCHEMA)fail('BROWSER_PLAN_SCHEMA');
  uuid(input.grant_id,'BROWSER_GRANT_ID');uuid(input.request_id,'BROWSER_REQUEST_ID');const record=this.grants.get(input.grant_id);
  if(!record)fail('BROWSER_GRANT_NOT_FOUND');if(record.cancelReceipt)fail('BROWSER_GRANT_CANCELLED');
  if(this.now()>=timestamp(record.grant.expires_at,'BROWSER_EXPIRES_AT'))fail('BROWSER_GRANT_EXPIRED');
  if(record.plan){if(record.requestId!==input.request_id)fail('BROWSER_GRANT_ALREADY_PLANNED');return clone(record.plan);}
  const action=ACTIONS[record.grant.action_id];record.requestId=input.request_id;record.grant.state='PLANNED';
  record.plan={schema:PLAN_SCHEMA,request_id:input.request_id,grant_id:record.grant.grant_id,action_id:record.grant.action_id,target:record.grant.target,registered_handler_id:action.handler_id,handler_options:action.options,source:'TRUSTED_EXTENSION_UI',source_content_authority:'DATA_ONLY',state:'READY_FOR_TRANSPORT_QUALIFICATION',registered_action_authority:true,transport_qualified:false,dispatch_allowed:false};
  return clone(record.plan);
 }
 cancel(input,event){
  trusted(event);exact(input,['schema','grant_id','trigger'],'BROWSER_CANCEL');if(input.schema!==CANCEL_REQUEST_SCHEMA)fail('BROWSER_CANCEL_SCHEMA');
  uuid(input.grant_id,'BROWSER_GRANT_ID');if(!['UI','KEYBOARD'].includes(input.trigger))fail('BROWSER_CANCEL_TRIGGER');
  const record=this.grants.get(input.grant_id);if(!record)fail('BROWSER_GRANT_NOT_FOUND');
  if(record.cancelReceipt){if(record.cancelReceipt.trigger!==input.trigger)fail('BROWSER_CANCEL_CONFLICT');return clone(record.cancelReceipt);}
  record.grant.state='CANCELLED';record.cancelReceipt={schema:CANCEL_RECEIPT_SCHEMA,grant_id:record.grant.grant_id,action_id:record.grant.action_id,target:record.grant.target,state:'CANCELLED',terminal:true,trigger:input.trigger,at:new Date(this.now()).toISOString(),action_dispatched:false,transport_invoked:false};return clone(record.cancelReceipt);
 }
}
