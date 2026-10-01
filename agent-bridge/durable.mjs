import path from 'node:path';
import {spawn} from 'node:child_process';

export const DURABLE_COMMANDS=Object.freeze(['durable.search','durable.context','durable.enqueue','durable.get','durable.cancel','durable.record']);
export const DURABLE_INPUT_BYTES=16000,DURABLE_OUTPUT_BYTES=192000,DURABLE_TIMEOUT_MS=10000;
const fields={
 'durable.search':['namespace','query','limit'],
 'durable.context':['namespace','ids','maxBytes'],
 'durable.enqueue':['template','taskKey'],
 'durable.get':['jobId'],
 'durable.cancel':['jobId'],
 'durable.record':['mutation']
};
export function durableEnvironment(source=process.env){
 const env={PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'};
 for(const name of ['PATH','SystemRoot','SYSTEMROOT','WINDIR','TEMP','TMP','LANG','LC_ALL'])if(typeof source[name]==='string')env[name]=source[name];
 return env;
}
export class DurableBridge{
 constructor(config,{spawnProcess=spawn}={}){
  this.config=config;this.spawnProcess=spawnProcess;this.children=new Map();this.closed=false;
  if(config?.enabled===true&&['pythonPath','profilePath','adapterPath'].some(key=>typeof config[key]!=='string'||!path.isAbsolute(config[key])||config[key].includes('\0')))throw Error('DURABLE_OPERATOR_CONFIG_REQUIRED');
 }
 get enabled(){return this.config?.enabled===true;}
 async handle(message){
  if(this.closed)throw Error('CLOSED');
  if(!this.enabled)throw Error('DURABLE_UNAVAILABLE');
  const allowed=fields[message.type];
  if(!allowed||Object.keys(message).some(key=>!['type','requestId',...allowed].includes(key)))throw Error('DURABLE_SCHEMA');
  // The caller never chooses a path, argv, policy, worker command or executable.
  const request=Object.fromEntries(Object.entries(message).filter(([key])=>key!=='requestId'));
  const input=Buffer.from(JSON.stringify(request));
  if(input.length>DURABLE_INPUT_BYTES)throw Error('DURABLE_INPUT_LIMIT');
  const argv=['-I','-X','utf8',this.config.adapterPath,'--profile',this.config.profilePath];
  return new Promise((resolve,reject)=>{
   let child,timer,done=false,total=0;const output=[];
   const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);if(child)this.children.delete(child);error?reject(error):resolve(value);};
   const stop=()=>{try{child.kill('SIGKILL');}catch{/* Already exited. No descendant worker is started by this adapter. */}};
   try{
    child=this.spawnProcess(this.config.pythonPath,argv,{env:durableEnvironment(),shell:false,windowsHide:true,stdio:['pipe','pipe','pipe']});
    this.children.set(child,()=>{stop();finish(Error('CLOSED'));});
    child.once('error',()=>finish(Error('DURABLE_PROCESS_FAILED')));
    const consume=(bytes,keep)=>{if(done)return;total+=bytes.length;if(total>DURABLE_OUTPUT_BYTES){stop();finish(Error('DURABLE_OUTPUT_LIMIT'));}else if(keep)output.push(bytes);};
    child.stdout.on('data',bytes=>consume(bytes,true));child.stderr.on('data',bytes=>consume(bytes,false));
    child.once('close',code=>{
     if(done)return;
     try{
      if(code!==0)throw Error('DURABLE_PROCESS_FAILED');
      const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Buffer.concat(output)));
      if(!value||typeof value!=='object'||typeof value.ok!=='boolean')throw Error('DURABLE_RESULT_SCHEMA');
      if(!value.ok)throw Error(typeof value.error==='string'&&/^[A-Z_]{1,100}$/.test(value.error)?value.error:'DURABLE_OPERATION_FAILED');
      if(!value.result||value.result.schema!=='occ.native-durable-result.v1'||value.result.operation!==request.type)throw Error('DURABLE_RESULT_SCHEMA');
      finish(null,{durable:value.result});
     }catch(error){finish(error.message?.startsWith('DURABLE_')||/^[A-Z_]{1,100}$/.test(error.message||'')?error:Error('DURABLE_INVALID_RESPONSE'));}
    });
    timer=setTimeout(()=>{stop();finish(Error('DURABLE_TIMEOUT'));},DURABLE_TIMEOUT_MS);timer.unref?.();
    child.stdin.on('error',()=>{});child.stdin.end(input);
   }catch{if(child)stop();finish(Error('DURABLE_PROCESS_FAILED'));}
  });
 }
 close(){this.closed=true;for(const cancel of this.children.values())cancel();this.children.clear();}
}
