/* Qualified text AI-site adapter. Installed code owns all executable DOM operations. */
(() => {
  const VERSION='browser-site-text.v1', MAX_SELECTOR=500, MAX_ROWS=200;
  if(globalThis.__occSiteAdapterVersion===VERSION)return;
  globalThis.__occSiteAdapterVersion=VERSION;
  function fnv(value){let h=0x811c9dc5;for(let i=0;i<value.length;i++){h^=value.charCodeAt(i);h=Math.imul(h,0x01000193);}return(h>>>0).toString(16).padStart(8,'0');}
  function visible(el){
    if(!el?.isConnected||el.hidden||el.getAttribute('aria-hidden')==='true')return false;
    for(let cur=el,n=0;cur&&n<80;cur=cur.parentElement,n++){const css=getComputedStyle(cur);if(css.display==='none'||css.visibility==='hidden'||css.visibility==='collapse'||css.opacity==='0')return false;}
    return !!el.getClientRects().length;
  }
  function selector(value){if(typeof value!=='string'||!value||value.length>MAX_SELECTOR)throw new Error('SITE_SELECTOR_SCHEMA');return value;}
  function validate(profile){
    const keys=['profile_id','origin','selectors','max_text_bytes','contract_digest'];
    if(!profile||typeof profile!=='object'||keys.some(k=>!(k in profile)))throw new Error('SITE_PROFILE_SCHEMA');
    const u=new URL(profile.origin);if(u.protocol!=='https:'||u.origin!==profile.origin||u.pathname!=='/')throw new Error('SITE_ORIGIN_SCHEMA');
    const s=profile.selectors||{};for(const key of ['account','workspace','composer','send','outgoing','response'])selector(s[key]);
    if(s.conversation!=null)selector(s.conversation);
    if(s.response_final!=null)selector(s.response_final);
    if(!Number.isSafeInteger(profile.max_text_bytes)||profile.max_text_bytes<1||profile.max_text_bytes>2000000)throw new Error('SITE_TEXT_LIMIT');
    if(typeof profile.contract_digest!=='string'||!/^[a-f0-9]{64}$/.test(profile.contract_digest))throw new Error('SITE_CONTRACT_DIGEST');
    return profile;
  }
  function one(sel,code){let rows;try{rows=document.querySelectorAll(sel);}catch{throw new Error('SITE_SELECTOR_INVALID');}if(rows.length!==1)throw new Error(code);return rows[0];}
  function identity(profile){
    validate(profile);if(location.origin!==profile.origin)throw new Error('SITE_ORIGIN_MISMATCH');
    const account=one(profile.selectors.account,'SITE_ACCOUNT_AMBIGUOUS').textContent.trim();
    const workspace=one(profile.selectors.workspace,'SITE_WORKSPACE_AMBIGUOUS').textContent.trim();
    if(!account||!workspace)throw new Error('SITE_IDENTITY_EMPTY');
    let conversation=location.href;
    if(profile.selectors.conversation!=null){
      const el=one(profile.selectors.conversation,'SITE_CONVERSATION_AMBIGUOUS');
      conversation=(el.getAttribute('data-conversation-id')||el.getAttribute('data-thread-id')||el.textContent||'').trim();
      if(!conversation)throw new Error('SITE_CONVERSATION_EMPTY');
    }
    return {origin:location.origin,account,workspace,conversation};
  }
  function fingerprint(el){
    const r=el.getBoundingClientRect();
    return fnv(JSON.stringify([el.tagName,el.getAttribute('role')||'',el.getAttribute('type')||'',el.getAttribute('data-testid')||'',Math.round(r.width),Math.round(r.height)]));
  }
  function bind(profile){
    const id=identity(profile),composer=one(profile.selectors.composer,'SITE_COMPOSER_AMBIGUOUS'),send=one(profile.selectors.send,'SITE_SEND_AMBIGUOUS');
    if(!visible(composer)||!visible(send))throw new Error('SITE_CONTROLS_NOT_VISIBLE');
    if(!(composer instanceof HTMLTextAreaElement||composer instanceof HTMLInputElement||composer.isContentEditable||composer.getAttribute('role')==='textbox'))throw new Error('SITE_COMPOSER_UNSUPPORTED');
    return {state:'BOUND',adapter_version:VERSION,contract_digest:profile.contract_digest,identity:id,
      composer_fingerprint:fingerprint(composer),send_fingerprint:fingerprint(send),bound_at:new Date().toISOString()};
  }
  function revalidate(profile,binding,{composer=true,send=true}={}){
    if(!binding||binding.adapter_version!==VERSION||binding.contract_digest!==profile.contract_digest)throw new Error('SITE_BINDING_VERSION');
    const id=identity(profile);
    for(const key of ['origin','account','workspace','conversation'])if(id[key]!==binding.identity?.[key])throw new Error('SITE_IDENTITY_DRIFT');
    let c=null,s=null;
    if(composer){c=one(profile.selectors.composer,'SITE_COMPOSER_AMBIGUOUS');if(!visible(c)||fingerprint(c)!==binding.composer_fingerprint)throw new Error('SITE_COMPOSER_DRIFT');}
    if(send){s=one(profile.selectors.send,'SITE_SEND_AMBIGUOUS');if(!visible(s)||fingerprint(s)!==binding.send_fingerprint)throw new Error('SITE_SEND_DRIFT');}
    return {identity:id,composer:c,send:s};
  }
  function getValue(el){return ('value' in el?el.value:el.textContent)||'';}
  function setValue(el,value){
    if(el instanceof HTMLInputElement||el instanceof HTMLTextAreaElement){
      if(el instanceof HTMLInputElement&&['password','file','hidden'].includes(el.type))throw new Error('SITE_SENSITIVE_INPUT_BLOCKED');
      const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
      const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;if(!setter)throw new Error('SITE_VALUE_SETTER');
      setter.call(el,value);
    }else{el.focus();el.replaceChildren(document.createTextNode(value));}
    try{el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:value}));}catch{el.dispatchEvent(new Event('input',{bubbles:true}));}
    el.dispatchEvent(new Event('change',{bubbles:true}));
  }
  function quiet(ms){
    const last=globalThis.__occLastHumanActivity;
    if(document.hasFocus()&&Number.isFinite(last)&&performance.now()-last<ms)throw new Error('SITE_HUMAN_FOREGROUND_LEASE');
  }
  function prepare(profile,binding,draft){
    validate(profile);if(typeof draft!=='string'||!draft||new TextEncoder().encode(draft).length>profile.max_text_bytes)throw new Error('SITE_DRAFT_LIMIT');
    quiet(1800);const {composer}=revalidate(profile,binding);
    const current=getValue(composer);
    if(current&&current!==draft)throw new Error('SITE_DRAFT_CONFLICT');
    if(current!==draft)setValue(composer,draft);
    const actual=getValue(composer);if(actual!==draft)throw new Error('SITE_DRAFT_READBACK_MISMATCH');
    return {state:'DRAFT_PREPARED',draft_fingerprint:fnv(draft),readback:true};
  }
  function send(profile,binding,draft){
    validate(profile);quiet(1800);const {composer,send}=revalidate(profile,binding);
    if(getValue(composer)!==draft)throw new Error('SITE_DRAFT_READBACK_MISMATCH');
    if(send.disabled||send.getAttribute('aria-disabled')==='true')throw new Error('SITE_SEND_UNAVAILABLE');
    send.click();return {state:'SEND_INVOKED',draft_fingerprint:fnv(draft),remote_effect:'UNKNOWN'};
  }
  function reconcile(profile,binding,draft){
    validate(profile);const {identity:id}=revalidate(profile,binding,{composer:false,send:false});
    const rows=[...document.querySelectorAll(profile.selectors.outgoing)].filter(visible);
    const matches=rows.filter(x=>(x.innerText||x.textContent||'').trim()===draft);
    if(matches.length>1)return {state:'CONFLICT',matches:matches.length,identity:id};
    if(matches.length===1)return {state:'MESSAGE_OBSERVED',matches:1,identity:id,message_id:matches[0].getAttribute('data-message-id')||matches[0].getAttribute('data-turn-id')||null};
    return {state:'EFFECT_UNKNOWN',reason:'OUTGOING_MESSAGE_NOT_OBSERVED',history_complete:false,identity:id};
  }
  function read(profile,binding){
    validate(profile);const {identity:id}=revalidate(profile,binding,{composer:false,send:false});
    const rows=[...document.querySelectorAll(profile.selectors.response)].filter(visible).slice(-MAX_ROWS);
    let finals=new Set();
    if(profile.selectors.response_final)finals=new Set([...document.querySelectorAll(profile.selectors.response_final)]);
    return {state:'RESPONSES_OBSERVED',identity:id,responses:rows.map((x,i)=>({ordinal:i,text:(x.innerText||x.textContent||'').trim(),
      message_id:x.getAttribute('data-message-id')||x.getAttribute('data-turn-id')||null,
      finalized:profile.selectors.response_final?finals.has(x):(x.getAttribute('data-finalized')==='true'||x.getAttribute('aria-busy')==='false')}))};
  }
  globalThis.__occSiteAdapter={version:VERSION,bind,prepare,send,reconcile,read};
})();