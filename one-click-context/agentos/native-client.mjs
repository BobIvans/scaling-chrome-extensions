const MAX_BYTES=2200000,CHUNK=49152;
const enc=new TextEncoder();

async function sha256(bytes){
  const raw=await crypto.subtle.digest('SHA-256',bytes);
  return [...new Uint8Array(raw)].map(x=>x.toString(16).padStart(2,'0')).join('');
}
function b64(bytes){
  let out='';for(let i=0;i<bytes.length;i+=0x8000)out+=String.fromCharCode(...bytes.subarray(i,i+0x8000));
  return btoa(out);
}
export class NativeClient{
  constructor(){this.closed=false;}
  async request(type,args={}){
    if(this.closed)throw new Error('NATIVE_CLOSED');
    const reply=await chrome.runtime.sendMessage({target:'agentos-background',type:'nativeRequest',request:{type,...args}});
    if(!reply?.ok)throw new Error(reply?.error||'NATIVE_OPERATION_FAILED');
    return reply.result;
  }
  hello(){return this.request('hello');}
  async durableAction(action,payload={}){
    const r=await this.request('durable.action',{action,payload});
    const d=r.durable;
    if(!d||d.schema!=='occ.native-durable-result.v1'||d.operation!=='durable.action')throw new Error('DURABLE_RESULT_SCHEMA');
    return d.action;
  }
  async submitCodex(instruction,text,mode='analyze'){
    const bytes=enc.encode(String(text||''));if(!bytes.length||bytes.length>MAX_BYTES)throw new Error('CODEX_INPUT_SIZE');
    const begin=await this.request('begin',{instruction:String(instruction),mode,bytes:bytes.length,sha256:await sha256(bytes)});
    const jobId=begin.job?.id;if(!jobId)throw new Error('CODEX_JOB_SCHEMA');
    try{
      for(let offset=0;offset<bytes.length;offset+=CHUNK){
        const part=bytes.subarray(offset,offset+CHUNK);
        await this.request('append',{jobId,offset,base64:b64(part)});
      }
      await this.request('run',{jobId});return jobId;
    }catch(error){await this.request('discard',{jobId}).catch(()=>{});throw error;}
  }
  close(){this.closed=true;}
}
export async function connectNative(){
  const ok=await chrome.permissions.request({permissions:['nativeMessaging']});
  if(!ok)throw new Error('NATIVE_PERMISSION_REQUIRED');
  const enabled=await chrome.runtime.sendMessage({target:'agentos-background',type:'enableNativeBridge'});
  if(!enabled?.ok)throw new Error(enabled?.error||'NATIVE_BRIDGE_UNAVAILABLE');
  return new NativeClient();
}
