from __future__ import annotations
import hashlib, json, time
from pathlib import Path

class MissionKernel:
    """UI/orchestration projection. Core remains the only effect authority."""
    def __init__(self,core,bridge,laya,questions_path,inbox_root):
        self.core=core;self.bridge=bridge;self.laya=laya;self.questions_path=Path(questions_path)
        self.root=Path(inbox_root).expanduser().resolve();self.root.mkdir(parents=True,exist_ok=True)
    def _answer(self,answers,key,default=None):
        value=(answers or {}).get(key,default)
        if isinstance(value,dict):
            for field in ('choice','label','answer','value'):
                if field in value:return value[field]
        return value
    def _state(self,mission,compile_result=None):
        return {'schema':'voice-agentos.decision-state.v1','goal':mission['goal'],'acceptance':mission.get('acceptance',[]),
                'effect_scope':mission.get('effects',['READ']),'has_context':bool(mission.get('context_text')),
                'context_sha256':hashlib.sha256(mission.get('context_text','').encode()).hexdigest() if mission.get('context_text') else None,
                'core_compile':compile_result,'time':time.time()}
    def _laya(self,state):
        if not self.laya or not self.laya.enabled:return None
        questions=json.loads(self.questions_path.read_text(encoding='utf-8'))
        return self.laya.decide(state,questions)
    def _system2_role(self,decision,compile_result):
        answers=(decision or {}).get('answers',{})
        role=self._answer(answers,'system2_role')
        if role and role!='NONE':return str(role)
        if compile_result and compile_result.get('state')!='COMPILED':return 'TOOL_DESIGNER'
        return 'PLANNER'
    def _system2_prompt(self,mission,state,role):
        return (
            'System-2 role: '+role+'\n'
            'You are a reasoning/coding service inside Voice AgentOS. You do not have effect authority.\n'
            'Return a concrete typed next result for the current goal. If a missing capability blocks progress, define a GapSpec/ToolCandidate with inputs, outputs, verifier, tests and effect class. '
            'If code is appropriate, create artifacts only in the bounded job sandbox. Do not claim merge/install/device success without receipts.\n\n'
            'MISSION:\n'+json.dumps({'goal':mission['goal'],'acceptance':mission.get('acceptance',[]),'effects':mission.get('effects',[])},ensure_ascii=False)+'\n\n'
            'DECISION_STATE:\n'+json.dumps(state,ensure_ascii=False)
        )
    def start(self,mission):
        if not isinstance(mission,dict) or not str(mission.get('goal','')).strip():raise ValueError('MISSION_GOAL_REQUIRED')
        criteria=[str(x) for x in mission.get('acceptance',[]) if str(x).strip()]
        refs=[mission.get('context_sha256')] if mission.get('context_sha256') else []
        compile_result=self.core.create_action(mission['goal'],criteria,refs)
        state=self._state(mission,compile_result)
        decision=None
        try:decision=self._laya(state)
        except Exception as exc:decision={'error':str(exc),'answers':{}}
        answers=(decision or {}).get('answers',{})
        route=self._answer(answers,'mission_route')
        if compile_result.get('state')=='COMPILED' and route not in {'SYSTEM2','CAPABILITY_GAP','GATHER_CONTEXT','WAIT','STOP'}:
            job=self.core.enqueue_action(compile_result['intent_id'],compile_result['revision'])
            return {'schema':'voice-agentos.mission-step.v1','state':'CORE_JOB_QUEUED','compile':compile_result,'laya':decision,'job':job}
        if route=='STOP':return {'schema':'voice-agentos.mission-step.v1','state':'STOPPED_BY_ROUTER','compile':compile_result,'laya':decision}
        if route=='WAIT':return {'schema':'voice-agentos.mission-step.v1','state':'WAITING_EXTERNAL','compile':compile_result,'laya':decision}
        if not self.bridge:return {'schema':'voice-agentos.mission-step.v1','state':'SYSTEM2_UNAVAILABLE','compile':compile_result,'laya':decision}
        role=self._system2_role(decision,compile_result)
        context=mission.get('context_text') or json.dumps({'compile':compile_result},ensure_ascii=False)
        prompt=self._system2_prompt(mission,state,role)
        submitted=self.bridge.codex_submit(prompt,context,'build' if role in {'CODER','TOOL_DESIGNER'} else 'analyze')
        job=submitted.get('job') if isinstance(submitted,dict) else None
        job_id=job.get('id') if isinstance(job,dict) else None
        if not job_id:raise ValueError('SYSTEM2_JOB_ID_REQUIRED')
        return {'schema':'voice-agentos.mission-step.v1','state':'WAITING_SYSTEM2','compile':compile_result,'laya':decision,'role':role,'system2_job_id':job_id}
    def poll_system2(self,job_id,mission):
        result=self.bridge.codex_result(job_id)
        job=result.get('job') if isinstance(result,dict) else None
        if not isinstance(job,dict):raise ValueError('SYSTEM2_RESULT_SCHEMA')
        if job.get('state')!='COMPLETE':return {'schema':'voice-agentos.mission-step.v1','state':'WAITING_SYSTEM2','system2_job':job}
        text=result.get('text')
        if not isinstance(text,str) or not text:raise ValueError('SYSTEM2_RESULT_EMPTY')
        digest=result.get('sha256') or hashlib.sha256(text.encode()).hexdigest()
        path=self.root/('system2_'+job_id+'_'+digest[:10]+'.txt');path.write_text(text,encoding='utf-8')
        receipt=self.core.capture_file(path,'system2_'+digest[:20])
        try:self.core.annotate_capture(receipt,project='AgentOS',note='System2 result job='+job_id)
        except Exception:pass
        return {'schema':'voice-agentos.mission-step.v1','state':'SYSTEM2_RESULT_INGESTED','system2_job':job,'text':text,'sha256':digest,'path':str(path),'library_receipt':receipt}
