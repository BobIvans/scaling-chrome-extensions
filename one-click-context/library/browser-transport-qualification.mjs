export const IDENTITY_SCHEMA='occ.extension-package-identity.v1';
export const QUALIFY_REQUEST_SCHEMA='occ.browser-transport-qualification-request.v1';
export const QUALIFY_RESULT_SCHEMA='occ.browser-transport-qualification-binding.v1';
export const RECEIPT_SCHEMA='occ.browser-transport-qualification-receipt.v1';
export const HOST_NAME='com.one_click_context.codex';
export const TREE_ALGORITHM='sha256-length-prefixed-path-bytes-v1';

const HEX=/^[0-9a-f]{64}$/u,EXTENSION=/^[a-p]{32}$/u,UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u;
const VERSION=/^[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?$/u;
const fail=code=>{throw Object.assign(new Error(code),{code});};
const exact=(value,keys,code)=>{if(!value||typeof value!=='object'||Array.isArray(value))fail(code+'_TYPE');const actual=Object.keys(value);if(keys.some(key=>!Object.hasOwn(value,key)))fail(code+'_MISSING');if(actual.some(key=>!keys.includes(key)))fail(code+'_UNKNOWN_FIELD');};
const bytes=value=>value instanceof Uint8Array?value:fail('PACKAGE_FILE_BYTES');
const u32=value=>new Uint8Array([(value>>>24)&255,(value>>>16)&255,(value>>>8)&255,value&255]);
const u64=value=>{if(!Number.isSafeInteger(value)||value<0)fail('PACKAGE_FILE_SIZE');const out=new Uint8Array(8);let n=BigInt(value);for(let i=7;i>=0;i--){out[i]=Number(n&255n);n>>=8n;}return out;};
const concat=parts=>{const out=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let at=0;for(const part of parts){out.set(part,at);at+=part.length;}return out;};
async function digest(value){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',value))].map(x=>x.toString(16).padStart(2,'0')).join('');}
function safePath(path){if(typeof path!=='string'||path.length>256||!/^[A-Za-z0-9][A-Za-z0-9._/-]*$/u.test(path)||path.includes('//')||path.split('/').includes('..')||path==='PACKAGE_IDENTITY.json')fail('PACKAGE_FILE_PATH');return path;}

export async function packageTreeSha256(entries){
 if(!Array.isArray(entries)||!entries.length)fail('PACKAGE_FILES_REQUIRED');
 const encoder=new TextEncoder(),parts=[];let previous='';
 for(const entry of entries){exact(entry,['path','bytes'],'PACKAGE_ENTRY');const path=safePath(entry.path);if(path<=previous)fail('PACKAGE_FILES_ORDER');previous=path;const data=bytes(entry.bytes),name=encoder.encode(path);parts.push(u32(name.length),name,u64(data.length),data);}
 return digest(concat(parts));
}

export async function verifyInstalledPackage(identityBytes,readPackageFile,expectedTreeSha256){
 if(!(typeof expectedTreeSha256==='string'&&HEX.test(expectedTreeSha256))||typeof readPackageFile!=='function')fail('PACKAGE_EXPECTATION');
 let identity;try{identity=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes(identityBytes)));}catch{fail('PACKAGE_IDENTITY_JSON');}
 exact(identity,['schema','version','algorithm','package_tree_sha256','files'],'PACKAGE_IDENTITY');
 if(identity.schema!==IDENTITY_SCHEMA||identity.algorithm!==TREE_ALGORITHM||!VERSION.test(identity.version)||identity.package_tree_sha256!==expectedTreeSha256||!Array.isArray(identity.files)||!identity.files.length||identity.files.length>500)fail('PACKAGE_IDENTITY_BINDING');
 const entries=[];let previous='';
 for(const item of identity.files){exact(item,['path','bytes','sha256'],'PACKAGE_IDENTITY_FILE');const path=safePath(item.path);if(path<=previous||!Number.isSafeInteger(item.bytes)||item.bytes<0||!HEX.test(item.sha256))fail('PACKAGE_IDENTITY_FILE');previous=path;const data=bytes(await readPackageFile(path));if(data.length!==item.bytes||await digest(data)!==item.sha256)fail('PACKAGE_FILE_MISMATCH');entries.push({path,bytes:data});}
 if(await packageTreeSha256(entries)!==expectedTreeSha256)fail('PACKAGE_TREE_MISMATCH');
 return {version:identity.version,package_tree_sha256:expectedTreeSha256,file_count:entries.length};
}

function qualifyPort(port,request,timeoutMilliseconds){
 return new Promise((resolve,reject)=>{let timer;const done=(fn,value)=>{clearTimeout(timer);port.onMessage.removeListener?.(message);port.onDisconnect.removeListener?.(disconnect);fn(value);};const message=value=>{if(value?.requestId!==request.requestId)return;if(value.ok!==true)return done(reject,Error(value?.error||'TRANSPORT_QUALIFY_REJECTED'));done(resolve,value.qualification);};const disconnect=()=>done(reject,Error('TRANSPORT_DISCONNECTED_BEFORE_BINDING'));port.onMessage.addListener(message);port.onDisconnect.addListener(disconnect);timer=setTimeout(()=>done(reject,Error('TRANSPORT_QUALIFY_TIMEOUT')),timeoutMilliseconds);try{port.postMessage(request);}catch(error){done(reject,error);}});
}
function binding(value,request){
 exact(value,['schema','nonce','extension_id','extension_version','package_tree_sha256','host_name','session_id','action_dispatch_allowed'],'TRANSPORT_BINDING');
 if(value.schema!==QUALIFY_RESULT_SCHEMA||value.nonce!==request.nonce||value.extension_id!==request.extensionId||value.extension_version!==request.extensionVersion||value.package_tree_sha256!==request.packageTreeSha256||value.host_name!==HOST_NAME||!UUID.test(value.session_id)||value.action_dispatch_allowed!==false)fail('TRANSPORT_BINDING_MISMATCH');return value;
}
async function closed(port,timeoutMilliseconds){return new Promise((resolve,reject)=>{let timer;const disconnected=()=>{clearTimeout(timer);port.onDisconnect.removeListener?.(disconnected);resolve();};port.onDisconnect.addListener(disconnected);timer=setTimeout(()=>{port.onDisconnect.removeListener?.(disconnected);reject(Error('TRANSPORT_DISCONNECT_TIMEOUT'));},timeoutMilliseconds);try{port.disconnect();}catch(error){clearTimeout(timer);port.onDisconnect.removeListener?.(disconnected);reject(error);}});}

export async function qualifyInstalledBrowserTransport({chromeApi=globalThis.chrome,readPackageFile,expectedPackageTreeSha256,randomUUID=()=>crypto.randomUUID(),timeoutMilliseconds=5000}={}){
 const extensionId=chromeApi?.runtime?.id,extensionVersion=chromeApi?.runtime?.getManifest?.().version;
 if(!EXTENSION.test(extensionId||'')||!VERSION.test(extensionVersion||'')||!Number.isSafeInteger(timeoutMilliseconds)||timeoutMilliseconds<1||timeoutMilliseconds>15000)fail('TRANSPORT_RUNTIME_IDENTITY');
 if(!await chromeApi.permissions.contains({permissions:['nativeMessaging']}))fail('TRANSPORT_PERMISSION_REQUIRED');
 const identityBytes=await readPackageFile('PACKAGE_IDENTITY.json'),pkg=await verifyInstalledPackage(identityBytes,readPackageFile,expectedPackageTreeSha256);
 if(pkg.version!==extensionVersion)fail('TRANSPORT_VERSION_MISMATCH');
 const sessions=[];
 for(let attempt=0;attempt<2;attempt++){
  const nonce=randomUUID(),requestId=randomUUID();if(!UUID.test(nonce)||!UUID.test(requestId))fail('TRANSPORT_NONCE');
  const request={type:'transport.qualify',requestId,schema:QUALIFY_REQUEST_SCHEMA,nonce,extensionId,extensionVersion,packageTreeSha256:expectedPackageTreeSha256};
  const port=chromeApi.runtime.connectNative(HOST_NAME);let value;try{value=binding(await qualifyPort(port,request,timeoutMilliseconds),request);await closed(port,timeoutMilliseconds);}catch(error){try{port.disconnect();}catch{}throw error;}sessions.push(value.session_id);
 }
 if(sessions[0]===sessions[1])fail('TRANSPORT_RECONNECT_NOT_FRESH');
 if(!await chromeApi.permissions.remove({permissions:['nativeMessaging']})||await chromeApi.permissions.contains({permissions:['nativeMessaging']}))fail('TRANSPORT_REVOKE_FAILED');
 return {schema:RECEIPT_SCHEMA,state:'QUALIFIED',extension_id:extensionId,extension_version:extensionVersion,package_tree_sha256:expectedPackageTreeSha256,file_count:pkg.file_count,handshakes:2,fresh_reconnect:true,permission_revoked:true,action_dispatch_allowed:false};
}
