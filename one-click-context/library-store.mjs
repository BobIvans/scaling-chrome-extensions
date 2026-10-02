import {digest,encode} from './library/convert.mjs';
import {normalizedRecord} from './library/workspace.mjs';

export const LIBRARY_RECORD_SCHEMA='occ.library-record.v1';
export const MAX_NATIVE_RECORD_TEXT_BYTES=8000;

function revision(value,name){
 if(value===null&&name==='parentRevision')return null;
 if(!Number.isSafeInteger(value)||value<1)throw Error('LIBRARY_RECORD_REVISION');
 return value;
}

export async function libraryMutation(record,{namespace,revision:nextRevision,parentRevision,tombstone=false}={}){
 const normalized=normalizedRecord(record);
 if(typeof namespace!=='string'||!/^[A-Za-z0-9_.:-]{1,90}$/.test(namespace))throw Error('LIBRARY_RECORD_NAMESPACE');
 if(!/^[A-Za-z0-9_.:-]{1,200}$/.test(normalized.id))throw Error('LIBRARY_RECORD_SOURCE_KEY');
 const rev=revision(nextRevision,'revision'),parent=revision(parentRevision,'parentRevision');
 if((rev===1)!==(parent===null))throw Error('LIBRARY_RECORD_REVISION');
 const bytes=encode(normalized.text);
 if(!tombstone&&bytes.length>MAX_NATIVE_RECORD_TEXT_BYTES)throw Error('LIBRARY_RECORD_TEXT_LIMIT');
 const sha256=await digest(bytes);
 if(normalized.sha256&&normalized.sha256!==sha256)throw Error('LIBRARY_CONTENT_HASH');
 return {
  schema:LIBRARY_RECORD_SCHEMA,namespace,sourceKey:normalized.id,revision:rev,
  parentRevision:parent,tombstone:!!tombstone,
  provenance:{source:normalized.source,savedAt:normalized.savedAt,
   capturedAt:normalized.capturedAt,status:normalized.status,
   warnings:[...normalized.warnings],project:normalized.project,session:normalized.session},
  content:tombstone?null:{name:normalized.name,text:normalized.text,sha256}
 };
}
