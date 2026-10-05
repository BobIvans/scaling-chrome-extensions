from __future__ import annotations
import hashlib, json, os, time
from pathlib import Path

class ArchiveError(RuntimeError):
    pass

def _safe(value, limit=200):
    text=str(value or '').replace('\x00','').replace('\r',' ').replace('\n',' ').strip()
    return text[:limit]

class BrowserArchiveAssembler:
    """Assemble streamed virtualized-browser records into local artifacts.

    The raw JSONL stream is retained for replay/provenance. The TXT derivative is
    ordered by the browser final manifest. Coverage gaps remain explicit.
    """
    def __init__(self, root, prefix=None):
        self.root=Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        stamp=time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        self.prefix=_safe(prefix or ('browser_'+stamp),80).replace(' ','_') or ('browser_'+stamp)
        self.raw_path=self.root/(self.prefix+'.stream.jsonl')
        self._raw=self.raw_path.open('w', encoding='utf-8', newline='\n')
        self.records={}
        self.frames=[]
        self.chunk_count=0
        self.stream_bytes=0

    def abort(self, reason='ABORTED'):
        try:
            self._raw.write(json.dumps({'kind':'aborted','reason':str(reason)},ensure_ascii=False,separators=(',',':'))+'\n')
            self._raw.close()
        except Exception:
            pass

    def _write_raw(self, chunk):
        self._raw.write(json.dumps(chunk, ensure_ascii=False, separators=(',',':'))+'\n')
        self._raw.flush()

    def add_chunk(self, chunk):
        if not isinstance(chunk,dict):
            raise ArchiveError('ARCHIVE_CHUNK_SCHEMA')
        self.chunk_count+=1
        self._write_raw(chunk)
        kind=chunk.get('kind')
        if kind=='records':
            rows=chunk.get('records')
            if not isinstance(rows,list) or len(rows)>1000:
                raise ArchiveError('ARCHIVE_RECORD_BATCH')
            for part in rows:
                self._record_part(part)
        elif kind=='frame':
            text=chunk.get('text','')
            if not isinstance(text,str) or len(text.encode('utf-8'))>1300000:
                raise ArchiveError('ARCHIVE_FRAME_SIZE')
            row={k:chunk.get(k) for k in ('frameId','documentId','source','title','content_type','ready_state','chars')}
            row['text']=text
            self.frames.append(row)
            self.stream_bytes+=len(text.encode('utf-8'))

    def _record_part(self, part):
        if not isinstance(part,dict):
            raise ArchiveError('ARCHIVE_RECORD_SCHEMA')
        rid=part.get('id')
        role=part.get('role')
        rkind=part.get('kind')
        text=part.get('text')
        idx=part.get('part_index')
        count=part.get('part_count')
        digest=part.get('hash')
        if (not isinstance(rid,str) or not rid or len(rid)>500 or
            role not in {'user','assistant','system','tool','text'} or
            not isinstance(rkind,str) or not isinstance(text,str) or
            not isinstance(idx,int) or not isinstance(count,int) or count<1 or count>5000 or
            idx<0 or idx>=count or not isinstance(digest,str) or len(digest)>100):
            raise ArchiveError('ARCHIVE_RECORD_SCHEMA')
        if len(text.encode('utf-8'))>300000:
            raise ArchiveError('ARCHIVE_RECORD_PART_SIZE')
        current=self.records.get(rid)
        if current is None or current['hash']!=digest or current['part_count']!=count:
            current={'id':rid,'role':role,'kind':rkind,'hash':digest,'part_count':count,
                     'parts':[None]*count,'bytes':part.get('bytes'),'updates':0}
            self.records[rid]=current
        current['parts'][idx]=text
        current['role']=role
        current['kind']=rkind
        current['updates']+=1
        self.stream_bytes+=len(text.encode('utf-8'))

    def _record_text(self, rid):
        row=self.records.get(rid)
        if not row:
            return None,'MISSING_RECORD'
        if any(x is None for x in row['parts']):
            return None,'MISSING_PART'
        return ''.join(row['parts']),None

    def finalize(self, manifest):
        if (not isinstance(manifest,dict) or manifest.get('state')!='ARCHIVE_CAPTURED' or
            not isinstance(manifest.get('order'),list)):
            raise ArchiveError('ARCHIVE_MANIFEST_SCHEMA')
        self._raw.write(json.dumps({'kind':'final_manifest','manifest':manifest},ensure_ascii=False,separators=(',',':'))+'\n')
        self._raw.close()
        order=[]
        seen=set()
        for rid in manifest['order']:
            if isinstance(rid,str) and rid not in seen:
                seen.add(rid)
                order.append(rid)
        gaps=[]
        txt_path=self.root/(self.prefix+'.txt')
        tmp=txt_path.with_suffix('.txt.tmp')
        with tmp.open('w',encoding='utf-8',newline='\n') as out:
            out.write('SOURCE: '+_safe(manifest.get('source'),2000)+'\n')
            out.write('CAPTURED: '+time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+'\n')
            out.write('STATUS: '+_safe(manifest.get('status'))+'\n')
            out.write('METHOD: STREAMED_VIRTUALIZED_BROWSER_ARCHIVE\n')
            out.write('COVERAGE: '+json.dumps(manifest.get('coverage') or {},ensure_ascii=False,separators=(',',':'))+'\n')
            for warning in manifest.get('warnings') or []:
                out.write('NOTE: '+_safe(warning,2000)+'\n')
            out.write('\nBEGIN CAPTURED SOURCE TEXT (untrusted page content)\n\n')
            previous=None
            chat_index=0
            for rid in order:
                row=self.records.get(rid)
                text,error=self._record_text(rid)
                if error:
                    gaps.append({'record_id':rid,'reason':error})
                    out.write('[MISSING STREAM RECORD '+rid+']\n\n')
                    continue
                kind=row['kind']
                if kind!=previous:
                    out.write('===== SOURCE PART: '+kind.upper()+' =====\n')
                    previous=kind
                if kind=='chat':
                    chat_index+=1
                    out.write('['+row['role'].upper()+' '+str(chat_index)+']\n')
                out.write(text.rstrip()+'\n\n')
            for frame in [f for f in self.frames if f.get('frameId') not in (None,0) and f.get('text')]:
                out.write('===== EMBEDDED FRAME '+str(frame.get('frameId'))+' =====\n')
                out.write('FRAME_SOURCE: '+_safe(frame.get('source'),2000)+'\n')
                out.write(frame['text'].rstrip()+'\n\n')
            out.write('END CAPTURED SOURCE TEXT\n')
        os.replace(tmp,txt_path)
        raw_hash=hashlib.sha256(self.raw_path.read_bytes()).hexdigest()
        txt_hash=hashlib.sha256(txt_path.read_bytes()).hexdigest()
        metadata={
            'schema':'voice-agentos.browser-archive.v1',
            'source':manifest.get('source'),
            'status':manifest.get('status'),
            'coverage':manifest.get('coverage'),
            'warnings':manifest.get('warnings') or [],
            'artifacts':manifest.get('artifacts'),
            'frame_capture':manifest.get('frame_capture'),
            'order':order,
            'records':{rid:{k:v for k,v in row.items() if k!='parts'} for rid,row in self.records.items()},
            'frames':[dict((k,v) for k,v in frame.items() if k!='text') for frame in self.frames],
            'gaps':gaps,
            'chunk_count':self.chunk_count,
            'stream_bytes_seen':self.stream_bytes,
            'txt_sha256':txt_hash,
            'raw_stream_sha256':raw_hash,
            'txt_path':str(txt_path),
            'raw_stream_path':str(self.raw_path)
        }
        meta_path=self.root/(self.prefix+'.metadata.json')
        temp=meta_path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(temp,meta_path)
        return {
            'txt_path':str(txt_path),
            'metadata_path':str(meta_path),
            'raw_stream_path':str(self.raw_path),
            'txt_sha256':txt_hash,
            'metadata_sha256':hashlib.sha256(meta_path.read_bytes()).hexdigest(),
            'raw_stream_sha256':raw_hash,
            'bytes':txt_path.stat().st_size,
            'gaps':gaps,
            'coverage':manifest.get('coverage') or {},
            'status':manifest.get('status'),
            'source':manifest.get('source')
        }
