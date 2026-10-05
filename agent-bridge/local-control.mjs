import fs from 'node:fs/promises';
import net from 'node:net';
import path from 'node:path';
import {randomUUID} from 'node:crypto';

const MAX_LINE=2400000;
const COMMANDS=new Set(['ping','tabs.list','tabs.active','tab.capture.start']);

function exactObject(value){return value && typeof value==='object' && !Array.isArray(value);}
export class LocalControlBridge{
  constructor(config,{createServer=net.createServer,writeFile=fs.writeFile,unlink=fs.unlink}={}){
    this.config=config?.localControl||null;this.createServer=createServer;this.writeFile=writeFile;this.unlink=unlink;
    this.server=null;this.push=null;this.pending=new Map();this.closed=false;
  }
  get enabled(){return this.config?.enabled===true;}
  validate(){
    const c=this.config;
    if(!this.enabled)return;
    if(!exactObject(c)||c.host!=='127.0.0.1'||!Number.isInteger(c.port)||c.port<0||c.port>65535||
       typeof c.token!=='string'||c.token.length<32||/[\r\n]/.test(c.token)||
       typeof c.stateFile!=='string'||!path.isAbsolute(c.stateFile))throw Error('LOCAL_CONTROL_CONFIG');
  }
  async start(push){
    if(!this.enabled)return null;this.validate();this.push=push;
    this.server=this.createServer(socket=>this.connection(socket));
    this.server.on('error',()=>{});
    await new Promise((resolve,reject)=>{
      const fail=e=>{this.server.off('listening',ok);reject(e);};
      const ok=()=>{this.server.off('error',fail);resolve();};
      this.server.once('error',fail);this.server.once('listening',ok);this.server.listen(this.config.port,this.config.host);
    });
    const address=this.server.address();
    const state={schema:'occ.agentos-local-control.v1',host:this.config.host,port:address.port,token:this.config.token,
      pid:process.pid,started_at:new Date().toISOString(),commands:[...COMMANDS]};
    await this.writeFile(this.config.stateFile,JSON.stringify(state),{encoding:'utf8',mode:0o600});
    return state;
  }
  connection(socket){
    socket.setTimeout(20000,()=>socket.destroy());let raw=Buffer.alloc(0),handled=false;
    const fail=message=>{if(!socket.destroyed)socket.end(JSON.stringify({ok:false,error:message})+'\n');};
    socket.on('data',chunk=>{
      if(handled)return;raw=Buffer.concat([raw,chunk]);
      if(raw.length>MAX_LINE){handled=true;fail('LOCAL_CONTROL_INPUT_LIMIT');return;}
      const end=raw.indexOf(10);if(end<0)return;handled=true;
      try{
        const value=JSON.parse(raw.subarray(0,end).toString('utf8'));
        if(!exactObject(value)||value.token!==this.config.token||!COMMANDS.has(value.command)||
           !exactObject(value.args||{}))throw Error('LOCAL_CONTROL_AUTH_OR_SCHEMA');
        if(value.command==='ping'){socket.end(JSON.stringify({ok:true,result:{state:'READY',pid:process.pid}})+'\n');return;}
        const controlId=randomUUID();
        const timer=setTimeout(()=>{
          const p=this.pending.get(controlId);if(!p)return;this.pending.delete(controlId);fail('LOCAL_CONTROL_CHROME_TIMEOUT');
        },30000);
        timer.unref?.();
        this.pending.set(controlId,{socket,timer});
        this.push({push:true,channel:'agentos-local-control',controlId,command:value.command,args:value.args||{}});
      }catch(error){fail(/^[A-Z_]{1,100}$/.test(error.message||'')?error.message:'LOCAL_CONTROL_SCHEMA');}
    });
    socket.on('error',()=>{});
  }
  acceptChromeReply(message){
    if(!exactObject(message)||message.type!=='agentos.control.reply'||typeof message.controlId!=='string')return false;
    const pending=this.pending.get(message.controlId);if(!pending)return true;
    this.pending.delete(message.controlId);clearTimeout(pending.timer);
    const value=message.ok===true?{ok:true,result:message.result}:{ok:false,error:typeof message.error==='string'?message.error:'LOCAL_CONTROL_CHROME_FAILED'};
    if(!pending.socket.destroyed)pending.socket.end(JSON.stringify(value)+'\n');
    return true;
  }
  async close(){
    if(this.closed)return;this.closed=true;
    for(const {socket,timer} of this.pending.values()){clearTimeout(timer);if(!socket.destroyed)socket.end(JSON.stringify({ok:false,error:'LOCAL_CONTROL_CLOSED'})+'\n');}
    this.pending.clear();
    if(this.server)await new Promise(resolve=>this.server.close(()=>resolve())).catch(()=>{});
    if(this.enabled)await this.unlink(this.config.stateFile).catch(()=>{});
  }
}
