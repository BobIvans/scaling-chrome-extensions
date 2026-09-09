import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const JSON_HEADERS = {"content-type":"application/json","cache-control":"no-store"};
const allowedActions = new Set(['capabilities','create_session','register_controller','start_run','run_status','stop_run']);

function env(name:string){const v=Deno.env.get(name)?.trim();if(!v)throw new Error(`SERVER_CONFIG_MISSING:${name}`);return v;}
function base(){const u=new URL(env('HERMES_GATEWAY_URL'));if(u.protocol!=='https:')throw new Error('HERMES_GATEWAY_URL must be HTTPS');u.pathname=u.pathname.replace(/\/(?:v1|api)\/?$/,'').replace(/\/$/,'');u.search='';u.hash='';return u.toString().replace(/\/$/,'');}
function wsUrl(){const u=new URL(base());u.protocol='wss:';u.pathname=u.pathname.replace(/\/$/,'')+'/v1/browser-control/ws';return u.toString();}
function cors(req:Request){const origin=req.headers.get('origin')||'';const allowed=env('OCC_EXTENSION_ORIGIN');if(origin!==allowed)throw new Error('ORIGIN_NOT_ALLOWED');return {'access-control-allow-origin':origin,'access-control-allow-headers':'authorization, x-client-info, apikey, content-type','access-control-allow-methods':'POST, OPTIONS','vary':'origin'};}
async function hermes(path:string, init:RequestInit={}){const res=await fetch(base()+path,{...init,headers:{'authorization':`Bearer ${env('HERMES_API_SERVER_KEY')}`,'content-type':'application/json',...(init.headers||{})}});const text=await res.text();if(!res.ok)return new Response(text||JSON.stringify({error:'Hermes error'}),{status:res.status,headers:JSON_HEADERS});return new Response(text||'{}',{status:res.status,headers:JSON_HEADERS});}
async function parse(res:Response){const text=await res.text();try{return JSON.parse(text)}catch{return {raw:text}}}

Deno.serve(async(req:Request)=>{
  try{
    const c=cors(req);
    if(req.method==='OPTIONS')return new Response(null,{status:204,headers:c});
    if(req.method!=='POST')return new Response(JSON.stringify({error:'POST_REQUIRED'}),{status:405,headers:{...JSON_HEADERS,...c}});
    const input=await req.json();const action=String(input?.action||'');if(!allowedActions.has(action))return new Response(JSON.stringify({error:'ACTION_NOT_ALLOWED'}),{status:400,headers:{...JSON_HEADERS,...c}});
    let out:Response;
    if(action==='capabilities') out=await hermes('/v1/capabilities');
    else if(action==='create_session') out=await hermes('/api/sessions',{method:'POST',body:JSON.stringify({title:String(input.title||'OCC Chrome Relay').slice(0,120)})});
    else if(action==='register_controller'){
      const body={protocol_version:Number(input.protocol_version)||1,session_id:String(input.session_id||''),controller_id:String(input.controller_id||''),browser_profile_id:String(input.browser_profile_id||''),capabilities:Array.isArray(input.capabilities)?input.capabilities.slice(0,20):[]};
      out=await hermes('/v1/browser-control/register',{method:'POST',body:JSON.stringify(body)});
      if(out.ok){const payload=await parse(out);payload.ws_url=wsUrl();out=new Response(JSON.stringify(payload),{headers:JSON_HEADERS});}
    }else if(action==='start_run'){
      const body={input:String(input.input||'').slice(0,100000),session_id:String(input.session_id||''),instructions:String(input.instructions||'').slice(0,20000)};
      out=await hermes('/v1/runs',{method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(body)});
    }else if(action==='run_status'){
      const id=encodeURIComponent(String(input.run_id||''));out=await hermes(`/v1/runs/${id}`);
    }else{
      const id=encodeURIComponent(String(input.run_id||''));out=await hermes(`/v1/runs/${id}/stop`,{method:'POST',body:'{}'});
    }
    const text=await out.text();return new Response(text,{status:out.status,headers:{...JSON_HEADERS,...c}});
  }catch(error){return new Response(JSON.stringify({error:String(error?.message||error)}),{status:403,headers:JSON_HEADERS});}
});
