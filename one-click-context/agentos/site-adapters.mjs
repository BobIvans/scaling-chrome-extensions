const HINTS=[
  ['grok.com','GROK_WEB'],['chatgpt.com','CHATGPT_WEB'],['claude.ai','CLAUDE_WEB'],
  ['gemini.google.com','GEMINI_WEB'],['perplexity.ai','PERPLEXITY_WEB'],['copilot.microsoft.com','COPILOT_WEB']
];

export function httpUrl(value){
  try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)?u:null;}catch{return null;}
}
export function originPattern(value){
  const u=httpUrl(value);return u?`${u.origin}/*`:null;
}
export function classifyTab(tab){
  const u=httpUrl(tab?.url||'');
  const host=u?.hostname?.toLowerCase()||'';
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
