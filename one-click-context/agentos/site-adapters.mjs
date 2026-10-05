const HINTS=[
  ['grok.com','GROK_WEB'],['chatgpt.com','CHATGPT_WEB'],['claude.ai','CLAUDE_WEB'],
  ['gemini.google.com','GEMINI_WEB'],['perplexity.ai','PERPLEXITY_WEB'],['copilot.microsoft.com','COPILOT_WEB']
];

export function httpUrl(value){
  const raw=String(value||'').trim();
  if(!/^https?:\/\//i.test(raw))return null;
  if(typeof globalThis.URL==='function'){
    try{
      const u=new globalThis.URL(raw);
      if(!['http:','https:'].includes(u.protocol))return null;
      return {href:u.href,origin:u.origin,hostname:u.hostname.toLowerCase(),protocol:u.protocol};
    }catch{}
  }
  const match=/^(https?):\/\/([^\s\/?#]+)([^\s]*)$/i.exec(raw);
  if(!match)return null;
  const protocol=match[1].toLowerCase()+':',hostname=match[2].toLowerCase();
  return {href:raw,origin:protocol+'//'+hostname,hostname,protocol};
}
export function originPattern(value){
  const u=httpUrl(value);return u?u.origin+'/*':null;
}
export function classifyTab(tab){
  const u=httpUrl(tab?.url||'');
  const host=u?.hostname||'';
  const hint=HINTS.find(([suffix])=>host===suffix||host.endsWith('.'+suffix));
  return {
    schema:'voice-agentos.tab-candidate.v1',
    tab_id:Number.isInteger(tab?.id)?tab.id:null,
    window_id:Number.isInteger(tab?.windowId)?tab.windowId:null,
    title:typeof tab?.title==='string'?tab.title:'',
    url:u?.href||'',
    origin:u?.origin||'',
    active:tab?.active===true,
    provider_hint:hint?.[1]||'GENERIC_WEB',
    authority:'DISPLAY_HINT_ONLY',
    action_readiness:'UNBOUND_REQUIRES_RUNTIME_IDENTITY'
  };
}
export function isObservable(candidate){return Number.isInteger(candidate?.tab_id)&&Boolean(candidate?.origin);}
