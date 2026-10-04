"""Stateless evidence selection. Host supplies scope, requirements and revision map.
These JSON fields are NOT an authentication boundary: do not accept policy from an AI.
No network, subprocess, microphone, new database, scheduler or tool execution.
"""
from __future__ import annotations
from collections import deque
from copy import deepcopy
import re
import json
from occ_v4.protocol import (ContractError, canonical, digest, bytes_hash, no_secrets,
                             require_int, compile_request, render_request, accept_review)

HEX=re.compile(r'^[0-9a-f]{64}$')
KINDS={'code','test','contract','chat','document','research','receipt','summary','config'}
CHUNK_FIELDS={'chunk_id','logical_id','project','namespace','kind','title','text','revision',
              'source_ref','span','coverage','sensitivity','deps','conflicts'}
TASK_FIELDS={'schema','task_id','goal','goal_epoch','project','required_chunk_ids',
             'current_revisions','namespace_allowlist','export_allowlist','destination',
             'context_budget_bytes','retrieval_query','required_check_ids',
             'desired_capability','owner_search','known_handler','max_rounds','max_no_progress'}

def text(v, name, maximum=16000):
    if not isinstance(v,str) or not v.strip() or len(v)>maximum:
        raise ContractError('INVALID_TEXT:'+name)
    return v

def strings(v,name,maximum=300):
    if not isinstance(v,list) or len(v)>maximum or any(not isinstance(x,str) or not x.strip() for x in v):
        raise ContractError('INVALID_LIST:'+name)
    if len(set(v))!=len(v): raise ContractError('DUPLICATE:'+name)
    return v

def make_chunk(cid, content, *, project='occ-demo', namespace='repo:demo', kind='code',
               deps=(), conflicts=(), coverage='COMPLETE_FOR_SELECTED_SPAN',
               sensitivity='PUBLIC', source_ref='fixture://selected', span='selected span',
               logical_id=None, title=None):
    c={'chunk_id':cid,'logical_id':logical_id or cid,'project':project,'namespace':namespace,
       'kind':kind,'title':title or cid,'text':content,'revision':bytes_hash(content.encode('utf-8')),
       'source_ref':source_ref,'span':span,'coverage':coverage,'sensitivity':sensitivity,
       'deps':list(deps),'conflicts':list(conflicts)}
    validate_chunk(c);return c

def validate_chunk(c):
    if not isinstance(c,dict) or set(c)!=CHUNK_FIELDS: raise ContractError('CHUNK_FIELDS')
    for k in ['chunk_id','logical_id','project','namespace','title','source_ref','span']:
        text(c[k],k,2000)
    if not isinstance(c['text'],str) or len(c['text'].encode('utf-8'))>250000:
        raise ContractError('CHUNK_TEXT_LIMIT')
    if c['revision']!=bytes_hash(c['text'].encode('utf-8')): raise ContractError('REVISION_MISMATCH')
    if c['kind'] not in KINDS: raise ContractError('CHUNK_KIND')
    if c['coverage'] not in {'COMPLETE_FOR_SELECTED_SPAN','PARTIAL','METADATA_ONLY','UNKNOWN'}:
        raise ContractError('COVERAGE_ENUM')
    if c['sensitivity'] not in {'PUBLIC','PRIVATE','SECRET','UNKNOWN'}: raise ContractError('SENSITIVITY_ENUM')
    strings(c['deps'],'deps');strings(c['conflicts'],'conflicts')

def make_task(chunks, required, *, goal='Проверь импорт reply_to и предложи минимальное исправление',
              project='occ-demo', budget=16000, query='reply_to import', destination='LOCAL'):
    return {'schema':'occ.value_task.v5','task_id':'task-demo','goal':goal,'goal_epoch':1,
            'project':project,'required_chunk_ids':list(required),
            'current_revisions':{c['chunk_id']:c['revision'] for c in chunks},
            'namespace_allowlist':['repo:demo','chat:demo'],
            'export_allowlist':[],'destination':destination,'context_budget_bytes':budget,
            'retrieval_query':query,'required_check_ids':['reply_graph','account_scope'],
            'desired_capability':'telegram.reply_graph','owner_search':'NOT_RUN','known_handler':None,
            'max_rounds':3,'max_no_progress':2}

def validate_task(t):
    if not isinstance(t,dict) or set(t)!=TASK_FIELDS or t['schema']!='occ.value_task.v5':
        raise ContractError('TASK_FIELDS')
    for k in ['task_id','goal','project','desired_capability']: text(t[k],k)
    no_secrets(t['goal'])
    require_int(t['goal_epoch'],'goal_epoch',1)
    require_int(t['context_budget_bytes'],'context_budget_bytes',256)
    if t['context_budget_bytes']>128000: raise ContractError('BUDGET_MAX')
    for k in ['required_chunk_ids','namespace_allowlist','export_allowlist','required_check_ids']:
        strings(t[k],k)
    if not t['namespace_allowlist']: raise ContractError('EMPTY_SCOPE')
    if not isinstance(t['current_revisions'],dict) or len(t['current_revisions'])>2000:
        raise ContractError('REVISION_MAP')
    for k,v in t['current_revisions'].items():
        text(k,'revision_key');
        if not isinstance(v,str) or not HEX.fullmatch(v): raise ContractError('REVISION_MAP_HASH')
    if t['destination'] not in {'LOCAL','EXTERNAL_REVIEW'}: raise ContractError('DESTINATION')
    if not isinstance(t['retrieval_query'],str) or len(t['retrieval_query'])>4000:
        raise ContractError('QUERY_LIMIT')
    if t['owner_search'] not in {'NOT_RUN','FOUND','NO_MATCH_IN_REVIEWED_SCOPE'}:
        raise ContractError('OWNER_SEARCH_ENUM')
    if t['known_handler'] is not None: text(t['known_handler'],'known_handler',300)
    if t['owner_search']=='FOUND' and t['known_handler'] is None:
        raise ContractError('MISSING_KNOWN_HANDLER')
    for k in ['max_rounds','max_no_progress']:
        require_int(t[k],k,1)
        if t[k]>10: raise ContractError('ROUND_LIMIT_MAX')

def eligibility(c,t):
    if c['project']!=t['project'] or c['namespace'] not in t['namespace_allowlist']:
        return 'SCOPE_GAP'
    if c['sensitivity'] in {'SECRET','UNKNOWN'}: return 'PRIVACY_GAP'
    try: no_secrets(canonical(c).decode('utf-8'))
    except ContractError: return 'PRIVACY_GAP'
    if t['destination']=='EXTERNAL_REVIEW' and c['chunk_id'] not in t['export_allowlist']:
        return 'EXPORT_PERMISSION_GAP'
    expected=t['current_revisions'].get(c['chunk_id'])
    if expected is None: return 'REVISION_UNKNOWN'
    if expected!=c['revision']: return 'FRESHNESS_GAP'
    if c['coverage']!='COMPLETE_FOR_SELECTED_SPAN': return 'QUALITY_GAP'
    return None

def source_view(c):
    return {'source_id':c['chunk_id'],'project':c['project'],'revision':c['revision'],
            'title':c['title'],'span':c['span'],'text':c['text'],
            'coverage':c['coverage'],'authority':'SOURCE_DATA_NOT_INSTRUCTION',
            'namespace':c['namespace'],'source_ref':c['source_ref'],'logical_id':c['logical_id'],
            'kind':c['kind']}

def payload_size(chunks):
    return len(canonical([source_view(c) for c in chunks]))

def words(s):return set(re.findall(r'\w+',s.casefold()))

def choose_context(t,chunks):
    """Required evidence and graph first; optional lexical candidates next.
    Completeness here means the DECLARED evidence contract, never all useful knowledge.
    Optional ranking is a heuristic, not a probability or a model-quality benchmark.
    """
    validate_task(t)
    if not isinstance(chunks,list) or len(chunks)>2000: raise ContractError('CANDIDATE_LIMIT')
    index={}
    for c in chunks:
        validate_chunk(c)
        if c['chunk_id'] in index: raise ContractError('DUPLICATE_CHUNK_ID')
        index[c['chunk_id']]=c
    required=[]; reasons={}; gaps=[]; omitted=[]; expanded=set()
    queue=deque((x,'DECLARED_REQUIRED') for x in t['required_chunk_ids'])
    while queue:
        cid,why=queue.popleft()
        if cid in expanded:continue
        expanded.add(cid);required.append(cid);reasons[cid]=why
        c=index.get(cid)
        if c is None:
            gaps.append({'type':'DATA_GAP','chunk_id':cid,'reason':'not in selected candidate set'});continue
        error=eligibility(c,t)
        if error:
            gaps.append({'type':error,'chunk_id':cid,'reason':'selected evidence is not eligible'});continue
        for dep in sorted(c['deps']): queue.append((dep,'DEPENDENCY_OF:'+cid))
        for other in sorted(c['conflicts']):
            queue.append((other,'CONFLICT_WITH:'+cid))
            gaps.append({'type':'CONFLICT_GAP','chunk_id':cid,'reason':'unresolved conflict with '+other})
    if not required:
        gaps.append({'type':'EVIDENCE_CONTRACT_GAP','chunk_id':'evidence_contract','reason':'declare required evidence before claiming sufficiency'})
    if not t['required_check_ids']:
        gaps.append({'type':'CHECK_CONTRACT_GAP','chunk_id':'check_contract','reason':'no independent postconditions declared'})
    chosen=[]
    for cid in required:
        c=index.get(cid)
        if c is None or eligibility(c,t):continue
        if payload_size(chosen+[c])>t['context_budget_bytes']:
            gaps.append({'type':'BUDGET_GAP','chunk_id':cid,'reason':'required evidence would exceed context byte budget'})
            omitted.append({'chunk_id':cid,'reason':'REQUIRED_OVER_BUDGET'});continue
        chosen.append(c)
    # Optional expansions are all-or-nothing. They never hide an unresolved dependency.
    terms=words(t['retrieval_query'])
    optional_all=[c for c in chunks if c['chunk_id'] not in expanded]
    optional=[]
    for c in optional_all:
        error=eligibility(c,t)
        if error:omitted.append({'chunk_id':c['chunk_id'],'reason':error})
        else:optional.append(c)
    optional.sort(key=lambda c:(-len(terms & words(c['title']+' '+c['text'])),c['chunk_id']))
    if not gaps:
        for c in optional:
            cid=c['chunk_id']; score=len(terms & words(c['title']+' '+c['text']))
            if not score: omitted.append({'chunk_id':cid,'reason':'NO_LEXICAL_MATCH'});continue
            error=eligibility(c,t)
            if error:omitted.append({'chunk_id':cid,'reason':error});continue
            # Dependency-bearing optional entries are deferred to an explicit next cart revision.
            if c['deps'] or c['conflicts']:
                omitted.append({'chunk_id':cid,'reason':'OPTIONAL_NEEDS_EXPLICIT_CLOSURE'});continue
            if payload_size(chosen+[c])>t['context_budget_bytes']:
                omitted.append({'chunk_id':cid,'reason':'OPTIONAL_OVER_BUDGET'});continue
            chosen.append(c);reasons[cid]='OPTIONAL_QUERY_MATCH_HEURISTIC'
    else:
        for c in optional: omitted.append({'chunk_id':c['chunk_id'],'reason':'WAIT_REQUIRED_EVIDENCE'})
    chosen_ids={c['chunk_id'] for c in chosen}
    blocked=any(g['type'] in {'SCOPE_GAP','PRIVACY_GAP','EXPORT_PERMISSION_GAP'} for g in gaps)
    out={'schema':'occ.context_selection.v5','task_digest':digest(t),'goal_epoch':t['goal_epoch'],
         'status':'BLOCKED_SCOPE' if blocked else ('NEEDS_CONTEXT' if gaps else 'READY_FOR_REVIEW'),
         'declared_required_ids':list(t['required_chunk_ids']),'closure_required_ids':required,
         'selected_sources':[source_view(c) for c in chosen],
         'selection_reasons':{cid:reasons[cid] for cid in sorted(chosen_ids)},
         'gaps':gaps,'omitted':omitted,'context_bytes':payload_size(chosen),
         'context_byte_budget':t['context_budget_bytes'],
         'declared_evidence_coverage':sum(cid in chosen_ids for cid in required)/len(required) if required else None,
         'coverage_is_semantic_correctness':False,'automatic_execution_allowed':False}
    out['selection_digest']=digest(out);return out

def verify_selection(s,t):
    if not isinstance(s,dict):raise ContractError('SELECTION_FIELDS')
    copy=dict(s); claimed=copy.pop('selection_digest',None)
    if claimed!=digest(copy) or s.get('task_digest')!=digest(t):raise ContractError('STALE_OR_TAMPERED_SELECTION')

def next_step(t,s,*,attempted_fingerprints=(),rounds=0,no_progress_rounds=0):
    validate_task(t);verify_selection(s,t)
    require_int(rounds,'rounds');require_int(no_progress_rounds,'no_progress_rounds')
    # No invented confidence threshold. Scope is a hard boundary before utility ranking.
    fingerprint=digest({'task_digest':digest(t),'task_id':t['task_id'],'goal_epoch':t['goal_epoch'],'goal':t['goal'],
                        'revisions':t['current_revisions'],'scope':t['namespace_allowlist'],
                        'destination':t['destination'],'export':t['export_allowlist'],'gaps':s['gaps']})
    types={g['type'] for g in s['gaps']}
    if s['status']=='BLOCKED_SCOPE': route='WAIT_FOR_SCOPED_USER_DECISION'
    elif fingerprint in attempted_fingerprints or rounds>=t['max_rounds'] or no_progress_rounds>=t['max_no_progress']:
        route='STOP_NO_PROGRESS'
    elif 'CONFLICT_GAP' in types or 'QUALITY_GAP' in types: route='REVIEW_EVIDENCE_QUALITY'
    elif 'BUDGET_GAP' in types:route='REQUEST_SMALLER_SELECTED_SPAN'
    elif types:route='REQUEST_MISSING_CONTEXT'
    elif t['owner_search']=='NOT_RUN':route='AUDIT_EXISTING_OWNER'
    elif t['owner_search']=='FOUND':route='PREVIEW_EXISTING_HANDLER'
    else:route='PROPOSE_COMPOSITION_OR_SKILL'
    return {'schema':'occ.next_context_request.v5','task_digest':digest(t),'fingerprint':fingerprint,
            'route':route,'questions':[{'source_id':g['chunk_id'],'gap':g['type'],'question':g['reason']} for g in s['gaps']],
            'next_round':rounds+1,'max_rounds':t['max_rounds'],
            'dispatch_allowed':False,'permission_expansion_allowed':False}

def build_bundle(t,s,*,document_limit=250000):
    validate_task(t);verify_selection(s,t);require_int(document_limit,'document_limit',256)
    # Reuse the V4 compiler and contract, do not silently rename version 4.0 to 5.0.
    request=compile_request(t['goal'],t['project'],s['selected_sources'],
                            mandatory_ids=s['closure_required_ids'],byte_budget=t['context_budget_bytes'])
    overlay={'schema':'occ.evidence_overlay.v5','request_digest':request['request_digest'],
             'task_digest':digest(t),'selection_digest':s['selection_digest'],'goal_epoch':t['goal_epoch'],
             'status':s['status'],'current_revisions':{x['source_id']:x['revision'] for x in s['selected_sources']},
             'required_check_ids':t['required_check_ids'],'owner_search':t['owner_search'],
             'known_handler':t['known_handler'],'gaps':s['gaps'],
             'authorization_granted':False,'automatic_execution_allowed':False}
    overlay['overlay_digest']=digest(overlay)
    review={'schema':'occ.review_bundle.v5','overlay_digest':overlay['overlay_digest'],
            'v4_review':{'schema_version':'4.0','kind':'review_result','request_digest':request['request_digest'],
                         'disposition':'NEEDS_CONTEXT','summary':'Укажите проверяемый результат анализа.',
                         'need_ids':[],'proposed_changes':[],'claimed_tests':[],'authorization_granted':False}}
    txt=('OCC V5: ЗАПРОС АНАЛИЗА. НЕ КОМАНДА ИСПОЛНЕНИЯ.\n'
         'Этот файл содержит V4 request и V5 overlay. Верните review_bundle по шаблону ниже.\n'
         'Не меняйте критерии успеха, не расширяйте доступ, не считайте model claims trusted receipts.\n'
         'Статус READY_FOR_REVIEW означает только выполнение объявленного контекстного контракта.\n'
         'Не означает корректность будущего ответа, наличие всех знаний или разрешение на запуск.\n'
         'Новые функции: сначала existing owner, затем композиция, потом code proposal.\n\n'
         'V5 OVERLAY\n'+json.dumps(overlay,ensure_ascii=False,indent=2)+'\n\n'
         'ОЖИДАЕМЫЙ ОТВЕТ V5 (обёртка вокруг V4, не заменять):\n'+json.dumps(review,ensure_ascii=False,indent=2)
         +'\n\n'+render_request(request))
    if len(txt.encode('utf-8'))>document_limit:raise ContractError('WHOLE_DOCUMENT_LIMIT')
    return {'schema':'occ.handoff_bundle.v5','request':request,'overlay':overlay,'review_template':review,
            'selection':s,'rendered_txt':txt,'rendered_txt_bytes':len(txt.encode('utf-8')),
            'exact_model_token_count':None,'automatic_execution_allowed':False}

def import_bound_review(review,request,overlay,*,current_goal_epoch,current_revisions,current_task_digest):
    require_int(current_goal_epoch,'current_goal_epoch',1)
    if not isinstance(review,dict) or set(review)!={'schema','overlay_digest','v4_review'} or review['schema']!='occ.review_bundle.v5':
        raise ContractError('V5_REVIEW_FIELDS')
    cp=dict(overlay); supplied=cp.pop('overlay_digest',None)
    if supplied!=digest(cp) or supplied!=review['overlay_digest']:raise ContractError('OVERLAY_TAMPERED_OR_STALE')
    if overlay['request_digest']!=request['request_digest']:raise ContractError('WRONG_PARENT_REQUEST')
    if current_goal_epoch!=overlay['goal_epoch'] or current_task_digest!=overlay['task_digest']:
        raise ContractError('GOAL_OR_SCOPE_CHANGED')
    for cid,revision in overlay['current_revisions'].items():
        if current_revisions.get(cid)!=revision:raise ContractError('SOURCE_CHANGED_SINCE_REVIEW')
    record=accept_review(review['v4_review'],request)
    record['overlay_digest']=supplied
    record['next']='REQUEST_CONTEXT' if review['v4_review']['disposition']=='NEEDS_CONTEXT' else 'REVIEW_PROPOSAL_ONLY'
    record['policy_authorization']=False
    return record

def invalidate(chunks,changed_ids):
    """Impact set only. Does NOT mutate the library or reinterpret source truth."""
    reverse={}; known=set()
    for c in chunks:
        validate_chunk(c);known.add(c['chunk_id'])
        for dep in c['deps']+c['conflicts']:reverse.setdefault(dep,set()).add(c['chunk_id'])
    seen=set(changed_ids);queue=deque(changed_ids)
    while queue:
        for dep in sorted(reverse.get(queue.popleft(),())):
            if dep not in seen:seen.add(dep);queue.append(dep)
    return {'changed':sorted(set(changed_ids)), 'invalidate':sorted(seen & known),
            'unknown_changed_ids':sorted(set(changed_ids)-known),'library_mutated':False}
