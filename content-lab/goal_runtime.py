from __future__ import annotations
import time,uuid
import automation_core as core
import workflow_state as state

MAX_H2=32
MAX_H1=64
EFFECTS={'READ','LOCAL_READ','LOCAL_WRITE','LOCAL_PROCESS','BROWSER_WRITE','WINDOWS_WRITE','GIT_WRITE','GITHUB_WRITE','MESSAGE_SEND','INSTALL_UPDATE'}

def _text(value,limit=16000):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('GOAL_TEXT_REQUIRED')
    return value.strip()

def _list_text(value,max_items,limit=1000,allow_empty=True):
    if not isinstance(value,list) or len(value)>max_items or (not allow_empty and not value):raise ValueError('GOAL_LIST_SCHEMA')
    out=[]
    for x in value:
        if not isinstance(x,str) or not x.strip() or len(x)>limit:raise ValueError('GOAL_LIST_SCHEMA')
        out.append(x.strip())
    return out

def _effect_scope(value):
    if not isinstance(value,list) or not value or any(x not in EFFECTS for x in value) or len(set(value))!=len(value):raise ValueError('GOAL_EFFECT_SCOPE')
    return list(value)

def _h2(rows):
    if not isinstance(rows,list) or len(rows)>MAX_H2:raise ValueError('GOAL_H2_SCHEMA')
    out=[]
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','text','state','acceptance','depends_on'}:raise ValueError('GOAL_H2_SCHEMA')
        rid=core.identifier(row['id'])
        if rid in seen:raise ValueError('GOAL_H2_DUPLICATE')
        seen.add(rid)
        if row['state'] not in {'TENTATIVE','ACTIVE','VERIFIED','BLOCKED','INVALIDATED'}:raise ValueError('GOAL_H2_STATE')
        out.append({'id':rid,'text':_text(row['text'],2000),'state':row['state'],
                    'acceptance':_list_text(row['acceptance'],20,1000,False),
                    'depends_on':[core.identifier(x) for x in row['depends_on']]})
    if any(dep not in seen for row in out for dep in row['depends_on']):raise ValueError('GOAL_H2_DEPENDENCY')
    return out

def _candidate(row):
    required={'id','kind','text','depends_on','effect_class','verifier','resources','components','state'}
    if not isinstance(row,dict) or set(row)!=required:raise ValueError('GOAL_H1_SCHEMA')
    rid=core.identifier(row['id'])
    if row['state'] not in {'CANDIDATE','BLOCKED','DONE','INVALIDATED'}:raise ValueError('GOAL_H1_STATE')
    effect=row['effect_class']
    if effect not in EFFECTS:raise ValueError('GOAL_H1_EFFECT')
    if not isinstance(row['resources'],list) or len(row['resources'])>20 or any(not isinstance(x,str) or not x for x in row['resources']):raise ValueError('GOAL_H1_RESOURCES')
    components=row['components']
    names={'progress','information_gain','success_probability','latency_cost','human_cost','resource_cost','risk_penalty','freshness_penalty','unlock_count','parallelizable'}
    if not isinstance(components,dict) or set(components)!=names:raise ValueError('GOAL_H1_COMPONENTS')
    clean={}
    for k,v in components.items():
        if k=='parallelizable':
            if type(v) is not bool:raise ValueError('GOAL_H1_COMPONENTS')
            clean[k]=v
        else:
            if type(v) not in (int,float) or not 0<=float(v)<=100:raise ValueError('GOAL_H1_COMPONENTS')
            clean[k]=float(v)
    return {'id':rid,'kind':_text(row['kind'],100),'text':_text(row['text'],2000),
            'depends_on':[core.identifier(x) for x in row['depends_on']],'effect_class':effect,
            'verifier':_text(row['verifier'],2000),'resources':list(row['resources']),
            'components':clean,'state':row['state']}

def utility(candidate):
    c=candidate['components']
    score=(c['progress']*1.8+c['information_gain']*1.2+c['success_probability']*1.4+c['unlock_count']*.6+
           (8 if c['parallelizable'] else 0)-c['latency_cost']*.7-c['human_cost']*1.0-c['resource_cost']*.5-
           c['risk_penalty']*1.5-c['freshness_penalty']*.8)
    return round(score,6)

def _h1(rows):
    if not isinstance(rows,list) or len(rows)>MAX_H1:raise ValueError('GOAL_H1_SCHEMA')
    out=[_candidate(x) for x in rows]
    ids=[x['id'] for x in out]
    if len(ids)!=len(set(ids)):raise ValueError('GOAL_H1_DUPLICATE')
    known=set(ids)
    if any(dep not in known for row in out for dep in row['depends_on']):raise ValueError('GOAL_H1_DEPENDENCY')
    for row in out:row['utility']=utility(row)
    return sorted(out,key=lambda x:(x['state']!='CANDIDATE',-x['utility'],x['id']))

def _spec(value):
    required={'goal','acceptance','constraints','prohibitions','effect_scope'}
    if not isinstance(value,dict) or set(value)!=required:raise ValueError('GOAL_SPEC_SCHEMA')
    return {'goal':_text(value['goal']),'acceptance':_list_text(value['acceptance'],50,2000,False),
            'constraints':_list_text(value['constraints'],50,2000,True),
            'prohibitions':_list_text(value['prohibitions'],50,2000,True),
            'effect_scope':_effect_scope(value['effect_scope'])}

def create(store,spec,goal_id=None):
    spec=_spec(spec);gid=core.identifier(goal_id) if goal_id else uuid.uuid4().hex
    now=time.time()
    value={'schema':'voice-agentos.goal-state.v1','goal_id':gid,'state':'ACTIVE','spec':spec,
           'h2':[],'h1':[],'h0':None,'evidence_refs':[],'progress_digest':None,'progress_events':0,
           'no_progress':0,'closed_acceptance':[],'runtime':{},'created_at':now,'updated_at':now,'last_decision':None}
    with state.transaction(store) as db:
        if state.get(db,'goal',gid):raise ValueError('GOAL_ALREADY_EXISTS')
        revision=state.put(db,'goal',gid,value,0)
    return {'goal_id':gid,'revision':revision,'value':value}

def inspect(store,goal_id):
    gid=core.identifier(goal_id)
    with state.transaction(store) as db:
        row=state.get(db,'goal',gid)
        if not row:raise ValueError('GOAL_NOT_FOUND')
        return {'goal_id':gid,'revision':row['revision'],'value':row['value']}

def revise(store,goal_id,expected_revision,spec):
    spec=_spec(spec);gid=core.identifier(goal_id);state.integer(expected_revision,1)
    with state.transaction(store) as db:
        old=state.get(db,'goal',gid)
        if not old or old['revision']!=expected_revision:raise ValueError('GOAL_REVISION_CONFLICT')
        value={**old['value'],'spec':spec,'state':'ACTIVE','h0':None,'h1':[
            {**x,'state':'INVALIDATED'} if x['state']=='CANDIDATE' else x for x in old['value']['h1']],
            'updated_at':time.time(),'last_decision':{'kind':'USER_REVISION','previous_revision':expected_revision}}
        revision=state.put(db,'goal',gid,value,expected_revision)
    return {'goal_id':gid,'revision':revision,'value':value}

def plan(store,goal_id,expected_revision,h2,h1,decision):
    gid=core.identifier(goal_id);state.integer(expected_revision,1)
    h2=_h2(h2);h1=_h1(h1)
    if not isinstance(decision,dict) or len(core.encoded(decision))>16000:raise ValueError('GOAL_DECISION_SCHEMA')
    with state.transaction(store) as db:
        old=state.get(db,'goal',gid)
        if not old or old['revision']!=expected_revision or old['value']['state'] not in {'ACTIVE','WAITING','BLOCKED'}:raise ValueError('GOAL_REVISION_CONFLICT')
        value={**old['value'],'h2':h2,'h1':h1,'h0':None,'state':'ACTIVE','last_decision':decision,'updated_at':time.time()}
        revision=state.put(db,'goal',gid,value,expected_revision)
    return {'goal_id':gid,'revision':revision,'value':value}

def admit(store,goal_id,expected_revision,candidate_id):
    gid=core.identifier(goal_id);cid=core.identifier(candidate_id);state.integer(expected_revision,1)
    with state.transaction(store) as db:
        old=state.get(db,'goal',gid)
        if not old or old['revision']!=expected_revision:raise ValueError('GOAL_REVISION_CONFLICT')
        candidates={x['id']:x for x in old['value']['h1']};candidate=candidates.get(cid)
        if not candidate or candidate['state']!='CANDIDATE':raise ValueError('GOAL_H0_CANDIDATE_REQUIRED')
        done={x['id'] for x in old['value']['h1'] if x['state']=='DONE'}
        if any(dep not in done for dep in candidate['depends_on']):raise ValueError('GOAL_H0_DEPENDENCY_BLOCKED')
        scope=set(old['value']['spec']['effect_scope'])
        if candidate['effect_class'] not in {'READ','LOCAL_READ'} and candidate['effect_class'] not in scope:raise ValueError('GOAL_H0_EFFECT_OUTSIDE_SCOPE')
        h0={'candidate_id':cid,'effect_class':candidate['effect_class'],'resources':candidate['resources'],
            'verifier':candidate['verifier'],'utility':candidate['utility'],'state':'ADMITTED_PROPOSAL','admitted_at':time.time()}
        value={**old['value'],'h0':h0,'updated_at':time.time()}
        revision=state.put(db,'goal',gid,value,expected_revision)
    return {'goal_id':gid,'revision':revision,'h0':h0}

def progress(store,goal_id,expected_revision,delta):
    gid=core.identifier(goal_id);state.integer(expected_revision,1)
    required={'digest','meaningful','evidence_refs','closed_acceptance','candidate_done','state'}
    if not isinstance(delta,dict) or set(delta)!=required:raise ValueError('GOAL_PROGRESS_SCHEMA')
    state.checked_hash(delta['digest'])
    if type(delta['meaningful']) is not bool or not isinstance(delta['evidence_refs'],list) or not all(isinstance(x,str) and x for x in delta['evidence_refs']):raise ValueError('GOAL_PROGRESS_SCHEMA')
    closed=_list_text(delta['closed_acceptance'],50,2000,True)
    candidate_done=delta['candidate_done']
    if candidate_done is not None:core.identifier(candidate_done)
    if delta['state'] not in {'ACTIVE','WAITING','BLOCKED','ACCEPTED','STOPPED'}:raise ValueError('GOAL_STATE')
    with state.transaction(store) as db:
        old=state.get(db,'goal',gid)
        if not old or old['revision']!=expected_revision:raise ValueError('GOAL_REVISION_CONFLICT')
        h1=[]
        for row in old['value']['h1']:
            h1.append({**row,'state':'DONE'} if candidate_done and row['id']==candidate_done else row)
        refs=list(dict.fromkeys([*old['value']['evidence_refs'],*delta['evidence_refs']]))[-500:]
        no_progress=0 if delta['meaningful'] else old['value']['no_progress']+1
        all_closed=list(dict.fromkeys([*old['value'].get('closed_acceptance',[]),*closed]))
        value={**old['value'],'h1':h1,'h0':None,'state':delta['state'],'evidence_refs':refs,
               'progress_digest':delta['digest'],'progress_events':old['value']['progress_events']+1,
               'no_progress':no_progress,'closed_acceptance':all_closed,'updated_at':time.time(),
               'last_progress':{'meaningful':delta['meaningful'],'closed_acceptance':closed,'candidate_done':candidate_done}}
        revision=state.put(db,'goal',gid,value,expected_revision)
    return {'goal_id':gid,'revision':revision,'value':value}

def checkpoint(store,goal_id,expected_revision,runtime,goal_state=None):
    gid=core.identifier(goal_id);state.integer(expected_revision,1)
    if not isinstance(runtime,dict) or len(core.encoded(runtime))>32000:raise ValueError('GOAL_RUNTIME_SCHEMA')
    if goal_state is not None and goal_state not in {'ACTIVE','WAITING','BLOCKED','STOPPED'}:raise ValueError('GOAL_STATE')
    with state.transaction(store) as db:
        old=state.get(db,'goal',gid)
        if not old or old['revision']!=expected_revision:raise ValueError('GOAL_REVISION_CONFLICT')
        value={**old['value'],'runtime':runtime,'updated_at':time.time()}
        if goal_state is not None:value['state']=goal_state
        revision=state.put(db,'goal',gid,value,expected_revision)
    return {'goal_id':gid,'revision':revision,'value':value}

def list_goals(store,offset=0,limit=50):
    state.integer(offset,0);state.integer(limit,1)
    if limit>200:raise ValueError('GOAL_LIST_LIMIT')
    with state.transaction(store) as db:
        rows=db.execute("SELECT id,revision,payload FROM workflow_records WHERE kind='goal' ORDER BY rowid DESC LIMIT ? OFFSET ?",(limit,offset)).fetchall()
        out=[]
        for row in rows:
            value=__import__('json').loads(row['payload'])
            out.append({'goal_id':row['id'],'revision':row['revision'],'state':value.get('state'),
                        'goal':value.get('spec',{}).get('goal'),'updated_at':value.get('updated_at'),
                        'h0':value.get('h0'),'no_progress':value.get('no_progress',0)})
        return {'items':out,'offset':offset,'limit':limit}
