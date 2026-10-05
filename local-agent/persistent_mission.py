from __future__ import annotations
import hashlib,json,time
from pathlib import Path

class PersistentMissionError(RuntimeError):
    pass

def _digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _components(**overrides):
    value={'progress':50,'information_gain':50,'success_probability':70,'latency_cost':20,'human_cost':5,
           'resource_cost':10,'risk_penalty':0,'freshness_penalty':5,'unlock_count':20,'parallelizable':True}
    value.update(overrides);return value

class PersistentMissionController:
    """Durable H2/H1/H0 scheduler over the canonical Core goal runtime."""
    def __init__(self,core,kernel,laya=None):
        self.core=core;self.kernel=kernel;self.laya=laya

    def _spec(self,mission):
        effects=list(dict.fromkeys(['READ',*mission.get('effects',[])]))
        return {'goal':str(mission['goal']).strip(),'acceptance':[str(x) for x in mission.get('acceptance',[]) if str(x).strip()] or ['Outcome independently verified.'],
                'constraints':[str(x) for x in mission.get('constraints',[]) if str(x).strip()],
                'prohibitions':[str(x) for x in mission.get('prohibitions',[]) if str(x).strip()],
                'effect_scope':effects}

    def ensure_goal(self,mission,goal_id=None):
        if goal_id:
            try:return self.core.goal_inspect(goal_id)
            except Exception:pass
        return self.core.goal_create(self._spec(mission),goal_id=goal_id)

    def _h2(self,state):
        closed=set(state.get('closed_acceptance',[]));rows=[];prev=None
        for i,text in enumerate(state['spec']['acceptance'],1):
            rid='acceptance_'+str(i)
            verified=text in closed
            rows.append({'id':rid,'text':text,'state':'VERIFIED' if verified else ('ACTIVE' if prev is None or rows[-1]['state']=='VERIFIED' else 'TENTATIVE'),
                         'acceptance':[text],'depends_on':[prev] if prev else []})
            prev=rid
        return rows

    def _frontier(self,state,mission):
        rows=[];has_context=bool(mission.get('context_text'));no_progress=int(state.get('no_progress',0))
        if not state.get('evidence_refs') or no_progress>0:
            rows.append({'id':'library_search','kind':'context','text':'Search lifetime Library for evidence relevant to the current goal.',
                         'depends_on':[],'effect_class':'LOCAL_READ','verifier':'Search result digest and source references are recorded.',
                         'resources':['library:read'],'components':_components(progress=45,information_gain=90,success_probability=95,latency_cost=5,human_cost=0,resource_cost=2,unlock_count=35),'state':'CANDIDATE'})
        if not has_context or no_progress>0:
            rows.append({'id':'browser_context','kind':'context','text':'Capture current browser context and ingest exact archive evidence.',
                         'depends_on':[],'effect_class':'READ','verifier':'Browser archive hash and coverage receipt are recorded.',
                         'resources':['browser:selected:read'],'components':_components(progress=55,information_gain=95,success_probability=80,latency_cost=20,human_cost=0,resource_cost=8,unlock_count=40),'state':'CANDIDATE'})
        if 'LOCAL_PROCESS' in set(state['spec']['effect_scope']):
            rows.append({'id':'mission_step','kind':'decision','text':'Run one bounded AgentOS mission step through existing Core/Laya/System2/browser capability owners.',
                         'depends_on':[],'effect_class':'LOCAL_PROCESS','verifier':'Step returns a typed receipt or a durable waiting checkpoint.',
                         'resources':['agentos:mission'],'components':_components(progress=90,information_gain=55,success_probability=75,latency_cost=25,human_cost=0,resource_cost=15,risk_penalty=10 if no_progress else 2,unlock_count=60,parallelizable=False),'state':'CANDIDATE'})
        return rows

    def _choose(self,state,candidates):
        if self.laya and getattr(self.laya,'enabled',False):
            criteria={x['id']:x['text'] for x in candidates};criteria['NONE']='No candidate is safe/useful now.'
            compact={'goal':state['spec']['goal'],'no_progress':state.get('no_progress',0),'evidence_count':len(state.get('evidence_refs',[])),
                     'candidates':[{'id':x['id'],'effect':x['effect_class'],'components':x['components']} for x in candidates]}
            try:
                result=self.laya.decide(compact,{'frontier_choice':{'type':'choice','instructions':'Choose the safest fastest useful next candidate.','criteria':criteria}})
                answer=result.get('answers',{}).get('frontier_choice',{})
                choice=answer.get('choice') or answer.get('answer') or answer.get('value')
                if answer.get('voice_agentos_admitted') is not False and choice in criteria and choice!='NONE':
                    return choice,{'source':'LAYA','raw':answer}
            except Exception as exc:
                return candidates[0]['id'],{'source':'DETERMINISTIC_FALLBACK','error':str(exc)}
        scored=[]
        for row in candidates:
            c=row['components'];score=c['progress']*1.8+c['information_gain']*1.2+c['success_probability']*1.4+c['unlock_count']*.6+(8 if c['parallelizable'] else 0)-c['latency_cost']*.7-c['human_cost']-c['resource_cost']*.5-c['risk_penalty']*1.5-c['freshness_penalty']*.8
            scored.append((score,row['id']))
        scored.sort(reverse=True);return scored[0][1],{'source':'DETERMINISTIC_UTILITY','score':scored[0][0]}

    def _progress(self,goal,candidate_id,result,meaningful,state='ACTIVE',evidence=None,closed=None):
        delta={'digest':_digest(result),'meaningful':bool(meaningful),'evidence_refs':list(evidence or []),
               'closed_acceptance':list(closed or []),'candidate_done':candidate_id if meaningful else None,'state':state}
        return self.core.goal_progress(goal['goal_id'],goal['revision'],delta)

    def _resume_pending(self,goal,mission):
        runtime=goal['value'].get('runtime') or {};kind=runtime.get('pending_kind')
        if not kind:return None
        cid=runtime.get('candidate_id')
        if kind=='SYSTEM2':
            result=self.kernel.poll_system2(runtime['job_id'],mission)
            if result.get('state')=='WAITING_SYSTEM2':return {'state':'WAITING_SYSTEM2','goal':goal,'runtime':runtime}
            cp=self.core.goal_checkpoint(goal['goal_id'],goal['revision'],{},state='ACTIVE')
            return self._progress(cp,cid,result,True,evidence=['system2:'+str(result.get('sha256','unknown'))])
        if kind=='CORE_JOB':
            job=self.core.job_get(runtime['job_id'])
            state=job.get('state')
            if state in {'QUEUED','RETRY_READY','RUNNING','WAITING_CI','NEEDS_RECONCILIATION'}:
                return {'state':'WAITING_CORE_JOB','goal':goal,'job':job,'runtime':runtime}
            cp=self.core.goal_checkpoint(goal['goal_id'],goal['revision'],{},state='ACTIVE' if state=='SUCCEEDED' else 'BLOCKED')
            return self._progress(cp,cid,job,state=='SUCCEEDED',state='ACTIVE' if state=='SUCCEEDED' else 'BLOCKED',evidence=['job:'+runtime['job_id']])
        raise PersistentMissionError('UNKNOWN_PENDING_KIND')

    def step(self,mission,goal_id=None):
        goal=self.ensure_goal(mission,goal_id)
        pending=self._resume_pending(goal,mission)
        if pending is not None:return pending
        state=goal['value']
        if state['state'] in {'ACCEPTED','STOPPED'}:return {'state':'TERMINAL','goal':goal}
        h2=self._h2(state);frontier=self._frontier(state,mission);choice,decision=self._choose(state,frontier)
        plan=self.core.goal_plan(goal['goal_id'],goal['revision'],h2,frontier,{'choice':choice,'decision':decision,'observed_at':time.time()})
        admitted=self.core.goal_admit(plan['goal_id'],plan['revision'],choice)
        current=self.core.goal_inspect(plan['goal_id']);candidate={x['id']:x for x in current['value']['h1']}[choice]
        if choice=='library_search':
            result=self.core.library_search(state['spec']['goal'],limit=20)
            count=len(result.get('items',[])) if isinstance(result,dict) else 0
            return self._progress(current,choice,result,count>0,evidence=['library-search:'+_digest(result)])
        if choice=='browser_context':
            result=self.kernel.capture_browser_context()
            return self._progress(current,choice,result,True,evidence=['browser:'+str(result.get('sha256','unknown'))])
        result=self.kernel.start(mission)
        rstate=result.get('state')
        if rstate=='WAITING_SYSTEM2':
            return self.core.goal_checkpoint(current['goal_id'],current['revision'],
                {'pending_kind':'SYSTEM2','candidate_id':choice,'job_id':result['system2_job_id'],'role':result.get('role'),'started_at':time.time()},state='WAITING')
        if rstate=='CORE_JOB_QUEUED':
            job=result.get('job') or {};job_id=job.get('id')
            if not job_id:raise PersistentMissionError('CORE_JOB_ID_MISSING')
            return self.core.goal_checkpoint(current['goal_id'],current['revision'],
                {'pending_kind':'CORE_JOB','candidate_id':choice,'job_id':job_id,'started_at':time.time()},state='WAITING')
        if rstate in {'NEEDS_CONTEXT','BROWSER_UI_EFFECT','WINDOWS_UI_EFFECT'}:
            gathered=self.kernel.capture_browser_context() if rstate!='WINDOWS_UI_EFFECT' else result
            return self._progress(current,choice,{'step':result,'verification':gathered},True,evidence=['mission-step:'+_digest(result)])
        meaningful=rstate in {'SYSTEM2_RESULT_INGESTED','CORE_JOB_QUEUED','CONTEXT_GATHERED','BROWSER_UI_EFFECT','WINDOWS_UI_EFFECT'}
        blocked=rstate in {'SYSTEM2_UNAVAILABLE','BROWSER_UI_BLOCKED','WINDOWS_UI_BLOCKED','BLOCKED'}
        return self._progress(current,choice,result,meaningful,state='BLOCKED' if blocked else 'ACTIVE',evidence=['mission-step:'+_digest(result)])

    def snapshot(self,goal_id):
        return self.core.goal_inspect(goal_id)

    def list(self,offset=0,limit=50):
        return self.core.goal_list(offset,limit)
