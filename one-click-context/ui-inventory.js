/* Universal UI inventory/broker for the local AgentOS. No autonomous authority. */
(() => {
  const VERSION='1.0.0';
  if(globalThis.__occUIInventory && globalThis.__occUIVersion===VERSION)return;
  globalThis.__occUIVersion=VERSION;
  const MAX_ELEMENTS=1200, MAX_NAME=240, MAX_VALUE=100000;
  const SNAPSHOTS=globalThis.__occUISnapshots instanceof Map ? globalThis.__occUISnapshots : new Map();
  globalThis.__occUISnapshots=SNAPSHOTS;
  const SELECTOR=[
    'button','a[href]','input:not([type="hidden"])','textarea','select',
    '[role="button"]','[role="link"]','[role="textbox"]','[role="menuitem"]','[role="option"]',
    '[role="tab"]','[role="checkbox"]','[role="radio"]','[role="switch"]','[contenteditable="true"]','[tabindex]'
  ].join(',');
  const DANGER=/\b(delete|remove|erase|destroy|pay|purchase|buy|checkout|merge|logout|log out|sign out|transfer|withdraw|deposit|swap|send funds|connect wallet|approve token|authorize|grant permission|revoke|close account|cancel subscription)\b/i;
  const WRITE=/\b(send|submit|save|post|publish|comment|reply|create|apply|upload|attach|confirm|accept|join|follow|like|edit|rename)\b/i;
  const READ=/\b(show more|load more|more|expand|collapse|open|view|details|next|previous|older|newer|continue reading|read more|download)\b/i;
  function visible(el){
    if(!el?.isConnected||el.hidden||el.getAttribute('aria-hidden')==='true'||el.closest('[data-occ-ignore]'))return false;
    let cur=el;
    for(let i=0;cur&&i<80;i++,cur=cur.parentElement){
      const css=getComputedStyle(cur);
      if(css.display==='none'||css.visibility==='hidden'||css.visibility==='collapse'||css.opacity==='0')return false;
    }
    const r=el.getBoundingClientRect();
    return r.width>1&&r.height>1&&r.bottom>=-20&&r.top<=innerHeight+20&&r.right>=-20&&r.left<=innerWidth+20;
  }
  function labelText(el){
    const ids=(el.getAttribute('aria-labelledby')||'').trim().split(/\s+/).filter(Boolean);
    const labelled=ids.map(id=>document.getElementById(id)?.textContent||'').join(' ');
    let label='';
    if(el.id){
      try{label=document.querySelector('label[for="'+CSS.escape(el.id)+'"]')?.textContent||'';}catch{}
    }
    const own=(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim();
    const value=(el instanceof HTMLInputElement||el instanceof HTMLTextAreaElement)?el.value:'';
    return [el.getAttribute('aria-label'),labelled,label,el.getAttribute('title'),el.getAttribute('alt'),
      el.getAttribute('placeholder'),own,value].filter(Boolean).join(' ').replace(/\s+/g,' ').trim().slice(0,MAX_NAME);
  }
  function role(el){
    const explicit=el.getAttribute('role');if(explicit)return explicit;
    if(el instanceof HTMLAnchorElement)return 'link';
    if(el instanceof HTMLButtonElement)return 'button';
    if(el instanceof HTMLTextAreaElement)return 'textbox';
    if(el instanceof HTMLInputElement){
      if(['checkbox','radio'].includes(el.type))return el.type;
      return ['button','submit','reset'].includes(el.type)?'button':'textbox';
    }
    if(el instanceof HTMLSelectElement)return 'combobox';
    if(el.isContentEditable)return 'textbox';
    return el.tagName.toLowerCase();
  }
  function risk(el,name){
    const href=el instanceof HTMLAnchorElement?el.href:'';
    const value=(name+' '+href).slice(0,1000);
    if(DANGER.test(value))return 'DANGEROUS';
    if(WRITE.test(value))return 'WRITE';
    if(READ.test(value)||el instanceof HTMLAnchorElement)return 'READ_NAV';
    if(role(el)==='textbox')return 'INPUT';
    return 'UNKNOWN';
  }
  function fnv(value){let h=0x811c9dc5;for(let i=0;i<value.length;i++){h^=value.charCodeAt(i);h=Math.imul(h,0x01000193);}return(h>>>0).toString(16).padStart(8,'0');}
  function pathOf(el){
    const parts=[];let cur=el;
    for(let depth=0;cur&&cur.nodeType===1&&depth<12;depth++,cur=cur.parentElement){
      let p=cur.tagName.toLowerCase();
      if(cur.id){p+='#'+cur.id.slice(0,80);parts.unshift(p);break;}
      const test=cur.getAttribute('data-testid');if(test)p+='[data-testid='+test.slice(0,80)+']';
      const parent=cur.parentElement;if(parent){const same=[...parent.children].filter(x=>x.tagName===cur.tagName);if(same.length>1)p+=':nth-of-type('+(same.indexOf(cur)+1)+')';}
      parts.unshift(p);
    }
    return parts.join('>');
  }
  function describe(el,index){
    const name=labelText(el),r=el.getBoundingClientRect(),href=el instanceof HTMLAnchorElement?el.href:'';
    const info={element_id:'e'+index,tag:el.tagName.toLowerCase(),role:role(el),name,href:href.slice(0,2000),
      input_type:el instanceof HTMLInputElement?el.type:null,disabled:!!el.disabled,contenteditable:!!el.isContentEditable,
      risk:risk(el,name),rect:{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)},
      path:pathOf(el)};
    info.fingerprint=fnv(JSON.stringify([info.tag,info.role,info.name,info.href,info.input_type,info.disabled,info.contenteditable,
      Math.round(r.width),Math.round(r.height)]));
    return info;
  }
  function docToken(){return fnv([location.href,document.title,performance.timeOrigin,document.documentElement?.childElementCount].join('|'));}
  function inventory(){
    const snapshot_id=crypto.randomUUID(),map=new Map(),elements=[];
    let n=0;
    for(const el of document.querySelectorAll(SELECTOR)){
      if(!visible(el)||el.closest('nav,[role="navigation"]')&&role(el)==='link')continue;
      const info=describe(el,++n);elements.push(info);map.set(info.element_id,{el,fingerprint:info.fingerprint,risk:info.risk,role:info.role});
      if(elements.length>=MAX_ELEMENTS)break;
    }
    const snap={snapshot_id,document_token:docToken(),url:location.href,title:document.title||'',created_at:new Date().toISOString(),elements};
    SNAPSHOTS.set(snapshot_id,{map,document_token:snap.document_token,url:snap.url,created:Date.now()});
    while(SNAPSHOTS.size>4)SNAPSHOTS.delete(SNAPSHOTS.keys().next().value);
    return snap;
  }
  function setValue(el,value){
    if(typeof value!=='string'||value.length>MAX_VALUE)throw new Error('UI_VALUE_LIMIT');
    if(el instanceof HTMLInputElement){
      if(['password','file','hidden'].includes(el.type))throw new Error('UI_SENSITIVE_INPUT_BLOCKED');
      const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')?.set;if(!setter)throw new Error('UI_VALUE_SETTER');
      setter.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return el.value;
    }
    if(el instanceof HTMLTextAreaElement){
      const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value')?.set;if(!setter)throw new Error('UI_VALUE_SETTER');
      setter.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));return el.value;
    }
    if(el.isContentEditable||el.getAttribute('role')==='textbox'){
      el.focus();el.replaceChildren(document.createTextNode(value));
      try{el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:value}));}catch{el.dispatchEvent(new Event('input',{bubbles:true}));}
      return el.textContent||'';
    }
    throw new Error('UI_NOT_TEXT_CONTROL');
  }
  function act(req={}){
    const snap=SNAPSHOTS.get(req.snapshot_id);if(!snap)throw new Error('UI_SNAPSHOT_STALE');
    if(snap.document_token!==req.document_token||snap.url!==location.href||snap.document_token!==docToken())throw new Error('UI_DOCUMENT_CHANGED');
    const bound=snap.map.get(req.element_id);if(!bound||!bound.el?.isConnected||!visible(bound.el))throw new Error('UI_ELEMENT_STALE');
    const now=describe(bound.el,0);if(now.fingerprint!==req.expected_fingerprint||bound.fingerprint!==req.expected_fingerprint)throw new Error('UI_ELEMENT_DRIFT');
    if(req.action==='scroll_into_view'){bound.el.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});return{state:'UI_SCROLLED',fingerprint:now.fingerprint,url:location.href};}
    if(req.effect_class!=='BROWSER_WRITE')throw new Error('UI_EFFECT_GRANT_REQUIRED');
    if(bound.risk==='DANGEROUS')throw new Error('UI_DANGEROUS_GENERIC_ACTION_BLOCKED');
    const before={url:location.href,name:now.name,risk:bound.risk,fingerprint:now.fingerprint};
    if(req.action==='click'){
      bound.el.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});bound.el.focus?.();bound.el.click();
      return{state:'UI_CLICK_INVOKED',before,after_url:location.href,desired_outcome_verified:false};
    }
    if(req.action==='type'){
      const readback=setValue(bound.el,req.value);
      if(readback!==req.value)throw new Error('UI_TYPE_READBACK_MISMATCH');
      return{state:'UI_TYPE_READBACK_VERIFIED',before,readback_sha:fnv(readback),desired_outcome_verified:false};
    }
    throw new Error('UI_ACTION_UNSUPPORTED');
  }
  globalThis.__occUIInventory=inventory;
  globalThis.__occUIAct=act;
})();