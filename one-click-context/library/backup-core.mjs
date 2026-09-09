const BACKUP_KIND='occ-library-backup';
const BACKUP_VERSION=2;
const MAX_RECORDS=100;
const MAX_LIBRARY_BYTES=2200000;
const STATUSES=new Set(['ORIGINAL','EXTRACTED','EMPTY','UNSUPPORTED','SELECTION','RAW_TEXT','PARTIAL','BEST_EFFORT']);
const enc=new TextEncoder();

function fail(message){throw new Error(message);}
function bytesOf(value){return enc.encode(value).length;}
function clone(value){return structuredClone(value);}
function validDate(value){return typeof value==='string'&&Number.isFinite(Date.parse(value));}
function safeByteArray(value){return Array.isArray(value)&&value.every(b=>Number.isInteger(b)&&b>=0&&b<=255);}
async function sha256(text){
  const bytes=enc.encode(text);
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  return [...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
async function normalizeRecord(record,{includeOriginals=true}={}){
  if(!record||typeof record!=='object')fail('Повреждена запись библиотеки.');
  const required=['id','name','text','source','status','createdAt'];
  for(const key of required)if(typeof record[key]!=='string'||!record[key])fail('Неверное поле '+key+'.');
  if(!STATUSES.has(record.status))fail('Неподдерживаемый status: '+record.status);
  if(!validDate(record.createdAt))fail('Некорректная дата: '+record.name);
  if(!Array.isArray(record.warnings)||record.warnings.some(w=>typeof w!=='string'))fail('Некорректные warnings: '+record.name);
  if(bytesOf(record.text)>MAX_LIBRARY_BYTES)fail('Текст записи превышает лимит: '+record.name);
  if(record.original!=null&&!safeByteArray(record.original))fail('Повреждены исходные байты: '+record.name);
  const actual=await sha256(record.text);
  if(record.sha256&&record.sha256!==actual)fail('SHA-256 текста не совпадает: '+record.name);
  const out={...clone(record),sha256:actual};
  if(!includeOriginals)delete out.original;
  return out;
}
function validateLibrarySize(records){
  if(records.length>MAX_RECORDS)fail('После восстановления будет более 100 документов.');
  const serialized=JSON.stringify({version:1,records});
  const bytes=bytesOf(serialized);
  if(bytes>MAX_LIBRARY_BYTES)fail('После восстановления библиотека превысит 2 200 000 байт.');
  return bytes;
}
export async function makeBackup(records,{includeOriginals=false}={}){
  if(!Array.isArray(records))fail('Библиотека должна быть массивом.');
  const normalized=[];
  for(const record of records)normalized.push(await normalizeRecord(record,{includeOriginals}));
  const payload={kind:BACKUP_KIND,version:BACKUP_VERSION,exportedAt:new Date().toISOString(),includeOriginals:Boolean(includeOriginals),records:normalized};
  const canonical=JSON.stringify(payload);
  return {...payload,payloadSha256:await sha256(canonical)};
}
export async function parseBackup(value){
  const data=typeof value==='string'?JSON.parse(value):clone(value);
  if(!data||data.kind!==BACKUP_KIND||data.version!==BACKUP_VERSION||!Array.isArray(data.records))fail('Неподдерживаемый формат резервной копии.');
  if(data.records.length>MAX_RECORDS)fail('В копии более 100 документов.');
  const normalized=[];
  for(const record of data.records)normalized.push(await normalizeRecord(record,{includeOriginals:true}));
  return {...data,records:normalized};
}
export async function planRestore(current,backup){
  if(!Array.isArray(current))fail('Текущая библиотека повреждена.');
  const normalizedCurrent=[];
  for(const record of current)normalizedCurrent.push(await normalizeRecord(record,{includeOriginals:true}));
  const parsed=await parseBackup(backup);
  const byId=new Map(normalizedCurrent.map(r=>[r.id,r]));
  const additions=[],skipped=[],conflicts=[];
  for(const record of parsed.records){
    const existing=byId.get(record.id);
    if(!existing){additions.push(record);byId.set(record.id,record);continue;}
    if(existing.sha256===record.sha256&&existing.name===record.name&&existing.source===record.source&&existing.status===record.status&&existing.createdAt===record.createdAt){skipped.push(record);continue;}
    conflicts.push({id:record.id,current:{name:existing.name,sha256:existing.sha256},incoming:{name:record.name,sha256:record.sha256}});
  }
  if(conflicts.length)return {ok:false,additions,skipped,conflicts,merged:null,serializedBytes:null};
  const merged=[...normalizedCurrent,...additions];
  const serializedBytes=validateLibrarySize(merged);
  return {ok:true,additions,skipped,conflicts:[],merged,serializedBytes};
}
export function serializePersistentLibrary(records){
  validateLibrarySize(records);
  return JSON.stringify({version:1,records});
}
export {BACKUP_KIND,BACKUP_VERSION,MAX_LIBRARY_BYTES,MAX_RECORDS,sha256};
