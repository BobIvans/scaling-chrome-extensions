from __future__ import annotations
import hashlib, json, os, re
from pathlib import Path

SAFE=re.compile(r'[^A-Za-z0-9._ -]+')
class ConversationExportError(RuntimeError):pass

def _text_content(content):
    if isinstance(content,str):return content
    if isinstance(content,list):return '\n'.join(str(x) for x in content if isinstance(x,(str,int,float)))
    if isinstance(content,dict):
        parts=content.get('parts')
        if isinstance(parts,list):return '\n'.join(str(x) for x in parts if isinstance(x,(str,int,float)))
        text=content.get('text')
        if isinstance(text,str):return text
    return ''

def _chatgpt_rows(conversation):
    mapping=conversation.get('mapping')
    if not isinstance(mapping,dict):return []
    rows=[]
    for node_id,node in mapping.items():
        if not isinstance(node,dict):continue
        message=node.get('message')
        if not isinstance(message,dict):continue
        author=message.get('author') or {}
        role=author.get('role') if isinstance(author,dict) else None
        text=_text_content(message.get('content'))
        if not text.strip():continue
        created=message.get('create_time')
        rows.append((float(created) if isinstance(created,(int,float)) else 0.0,str(role or 'unknown'),text,node_id))
    rows.sort(key=lambda x:(x[0],x[3]))
    return rows

def _generic_rows(value):
    messages=value.get('messages') if isinstance(value,dict) else None
    if not isinstance(messages,list):return []
    rows=[]
    for i,m in enumerate(messages):
        if not isinstance(m,dict):continue
        role=m.get('role') or (m.get('author') or {}).get('role') if isinstance(m.get('author'),dict) else m.get('role')
        text=_text_content(m.get('content') if 'content' in m else m.get('text'))
        if text.strip():rows.append((float(m.get('create_time',i)) if isinstance(m.get('create_time',i),(int,float)) else float(i),str(role or 'unknown'),text,str(i)))
    return rows

def extract_conversations(path,output_root,max_source_bytes=50_000_000,max_conversations=5000,max_output_bytes=5_000_000):
    source=Path(path).resolve()
    if not source.is_file() or source.stat().st_size>max_source_bytes:raise ConversationExportError('CONVERSATION_EXPORT_SIZE')
    if source.suffix.lower() not in {'.json','.jsonl'}:return []
    try:
        if source.suffix.lower()=='.jsonl':
            items=[json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
        else:
            value=json.loads(source.read_text(encoding='utf-8'))
            if isinstance(value,list):items=value
            elif isinstance(value,dict) and isinstance(value.get('conversations'),list):items=value['conversations']
            else:items=[value]
    except Exception as exc:raise ConversationExportError('CONVERSATION_EXPORT_PARSE') from exc
    root=Path(output_root).resolve();root.mkdir(parents=True,exist_ok=True);results=[]
    for index,item in enumerate(items[:max_conversations]):
        if not isinstance(item,dict):continue
        rows=_chatgpt_rows(item) or _generic_rows(item)
        if not rows:continue
        title=str(item.get('title') or item.get('name') or ('Conversation '+str(index+1)))
        cid=str(item.get('id') or item.get('conversation_id') or hashlib.sha256((title+str(index)).encode()).hexdigest()[:24])
        header=['SOURCE_EXPORT: '+str(source),'CONVERSATION_ID: '+cid,'TITLE: '+title,'MESSAGE_COUNT: '+str(len(rows))]
        body=[]
        for _,role,text,_ in rows:body.append('['+role.upper()+']\n'+text.strip())
        rendered='\n'.join(header)+'\n\n'+'\n\n'.join(body)+'\n'
        raw=rendered.encode('utf-8')
        if len(raw)>max_output_bytes:
            rendered=raw[:max_output_bytes].decode('utf-8',errors='ignore')+'\n\n[TRUNCATED_DERIVATIVE; RAW EXPORT PRESERVED]\n'
        safe=SAFE.sub('_',title).strip(' ._')[:80] or 'conversation'
        target=root/(safe+'__'+hashlib.sha256(cid.encode()).hexdigest()[:12]+'.txt')
        tmp=target.with_suffix('.tmp');tmp.write_text(rendered,encoding='utf-8');os.replace(tmp,target)
        results.append({'path':str(target),'conversation_id':cid,'title':title,'messages':len(rows),'source_export':str(source),
                        'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    return results
