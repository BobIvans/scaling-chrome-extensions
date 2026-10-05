const HOST='com.one_click_context.codex';
const MAX_BYTES=2_200_000,CHUNK=49_152;
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
  constructor(port){
    this.port=port;this.pending=new Map();this.closed=false;this.seq=0;
    port.onMessage.addListener(message=>{
      const p=this.pending.get(message?.requestId);if(!p)return;
      if(message.progress===true){p.onProgress?.();return;}
      this.pending.delete(message.requestId);clearTimeout(p.timer);
      message.ok?p.resolve(message):p.reject(new Error(message.error||'NATIVE_OPERATION_FAILED'));
    });
    port.onDisconnect.addListener(()=>{
      this.closed=true;const error=chrome.runtime.lastError?.message||'Native host disconnected';
      for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(new Error(error));}
      this.pending.clear();
    });
  }
  request(type,args={},onProgress){
    if(this.closed)return Promise.reject(new Error('NATIVE_CLOSED'));
    const requestId='agentos-'+Date.now()+'-'+(++this.seq);
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(requestId);reject(new Error('NATIVE_TIMEOUT'));},130000);
      this.pending.set(requestId,{resolve,reject,timer,onProgress});
      this.port.postMessage({requestId,type,...args});
    });
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
  close(){this.closed=true;try{this.port.disconnect();}catch{}}
}
export async function connectNative(){
  const ok=await chrome.permissions.request({permissions:['nativeMessaging']});
  if(!ok)throw new Error('NATIVE_PERMISSION_REQUIRED');
  return new NativeClient(chrome.runtime.connectNative(HOST));
}
