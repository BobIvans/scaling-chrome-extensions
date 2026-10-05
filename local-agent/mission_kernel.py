from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from browser_archive import BrowserArchiveAssembler

def bounded_utf8(text,limit=1_400_000):
    raw=str(text or '').encode('utf-8')
    if len(raw)<=limit:return str(text or '')
    return raw[:limit].decode('utf-8',errors='ignore')+'\n\n[WORKING_PACKET_TRUNCATED; FULL RAW SOURCE REMAINS IN CANONICAL LIBRARY]\n'

class MissionKernel:
    """UI/orchestration projection. Core remains the only effect authority."""
    def __init__(self,core,bridge,laya,questions_path,inbox_root,windows_ui=None,candidate_pipeline=None,github_pipeline=None):
        self.core=core;self.bridge=bridge;self.laya=laya;self.windows_ui=windows_ui;self.candidate_pipeline=candidate_pipeline;self.github_pipeline=github_pipeline;self.questions_path=Path(questions_path)
        self.root=Path(inbox_root).expanduser().resolve();self.root.mkdir(parents=True,exist_ok=True)
    def _answer(self,answers,key,default=None):
        value=(answers or {}).get(key,default)
        if isinstance(value,dict):
            for field in ('choice','label','answer','value'):
                if field in value:return value[field]
        return value
    def _browser_inventory(self,mission):
        if not self.bridge or 'BROWSER_WRITE' not in set(mission.get('effects',[])):return None,None
        try:full=self.bridge.ui_inventory()
        except Exception:return None,None
        rows=[]
        for item in full.get('elements',[]):
            if not isinstance(item,dict) or item.get('risk') not in {'READ_NAV','INPUT'}:continue
            name=str(item.get('name') or '').strip()
            if not name and item.get('role') not in {'textbox','button','link'}:continue
            rows.append({'element_id':item.get('element_id'),'role':item.get('role'),'risk':item.get('risk'),
                         'name':name[:180],'fingerprint':item.get('fingerprint')})
        rows=sorted(rows,key=lambda x:(x['risk']!='READ_NAV',x['role']!='button',len(x['name'])))[:60]
        return {'snapshot_id':full.get('snapshot_id'),'document_token':full.get('document_token'),'tab_id':full.get('tabId'),
                'url':full.get('url'),'title':full.get('title'),'human_activity_ms':full.get('human_activity_ms'),
                'document_has_focus':full.get('document_has_focus'),'visibility_state':full.get('visibility_state'),'candidates':rows},full
    def _windows_inventory(self,mission):
        if not self.windows_ui or 'WINDOWS_WRITE' not in set(mission.get('effects',[])):return None,None
        try:full=self.windows_ui.inventory()
        except Exception:return None,None
        rows=[]
        for item in full.get('elements',[]):
            if not isinstance(item,dict) or item.get('risk') not in {'READ_NAV','INPUT'}:continue
            name=str(item.get('name') or item.get('value') or item.get('text') or '').strip()
            if not name:continue
            rows.append({'element_id':item.get('element_id'),'role':item.get('control_type'),'risk':item.get('risk'),
                         'name':name[:180],'fingerprint':item.get('fingerprint')})
        rows=sorted(rows,key=lambda x:(x['risk']!='READ_NAV',len(x['name'])))[:60]
        return {'snapshot_id':full.get('snapshot_id'),'hwnd':full.get('hwnd'),'candidates':rows},full
    def _state(self,mission,compile_result=None,ui=None,windows_ui=None):
        value={'schema':'voice-agentos.decision-state.v1','goal':mission['goal'],'acceptance':mission.get('acceptance',[]),
                'effect_scope':mission.get('effects',['READ']),'has_context':bool(mission.get('context_text')),
                'context_sha256':hashlib.sha256(mission.get('context_text','').encode()).hexdigest() if mission.get('context_text') else None,
                'core_compile':compile_result,'time':time.time()}
        if ui:value['browser_ui']=ui
        if windows_ui:value['windows_ui']=windows_ui
        return value
    def _laya(self,state,ui=None,windows_ui=None):
        if not self.laya or not self.laya.enabled:return None
        questions=json.loads(self.questions_path.read_text(encoding='utf-8'))
        if ui and ui.get('candidates'):
            criteria={'NONE':'No visible exact-bound control safely advances the current goal.'}
            for item in ui['candidates']:
                criteria[item['element_id']]=('risk='+str(item['risk'])+' role='+str(item['role'])+' name='+str(item['name']))[:300]
            questions['ui_candidate']={'type':'choice',
                'instructions':'Choose one exact visible UI element only if it safely advances the mission. Prefer READ_NAV for context gathering; choose NONE when uncertain.',
                'criteria':criteria}
        if windows_ui and windows_ui.get('candidates'):
            criteria={'NONE':'No visible exact-bound Windows control safely advances the current goal.'}
            for item in windows_ui['candidates']:
                criteria[item['element_id']]=('risk='+str(item['risk'])+' role='+str(item['role'])+' name='+str(item['name']))[:300]
            questions['windows_ui_candidate']={'type':'choice',
                'instructions':'Choose one exact Windows UI element only if it safely advances the mission. Prefer READ_NAV; choose NONE when uncertain.',
                'criteria':criteria}
        return self.laya.decide(state,questions)
    def _route_frontier(self,mission,compile_result,ui,windows_ui):
        rows=[]
        def add(cid,kind,text,effect,progress,info,success,latency,risk,unlock,parallel):
            rows.append({'id':cid,'kind':kind,'text':text,'depends_on':[],'effect_class':effect,'verifier':'independent receipt/evidence delta',
                'resources':[],'components':{'progress':progress,'information_gain':info,'success_probability':success,
                'latency_cost':latency,'human_cost':0,'resource_cost':10,'risk_penalty':risk,'freshness_penalty':5,
                'unlock_count':unlock,'parallelizable':parallel},'state':'CANDIDATE'})
        if compile_result.get('state')=='COMPILED':
            effect=((compile_result.get('plan') or {}).get('capability') or {}).get('effect','LOCAL_READ')
            mapped={'LOCAL_READ':'LOCAL_READ','LOCAL_WRITE':'LOCAL_WRITE','EXTERNAL_WRITE':'MESSAGE_SEND'}.get(effect,'LOCAL_READ')
            add('route_known','KNOWN_RECIPE','Execute compiled registered Core capability',mapped,90,20,90,10,10,20,False)
        add('route_context','GATHER_CONTEXT','Gather fresh exact context before acting','READ',35,95,95,20,0,25,True)
        if ui and ui.get('candidates'):add('route_browser','BROWSER_UI','Advance context through exact-bound browser READ_NAV','BROWSER_WRITE',45,85,85,20,15,30,False)
        if windows_ui and windows_ui.get('candidates'):add('route_windows','WINDOWS_UI','Advance context through exact-bound Windows UIA READ_NAV','WINDOWS_WRITE',40,75,75,30,20,25,False)
        add('route_system2','SYSTEM2','Ask System-2 for novel reasoning or design','LOCAL_PROCESS',65,75,75,55,5,50,True)
        if compile_result.get('state')!='COMPILED':add('route_capability','CAPABILITY_GAP','Resolve missing capability and qualify a reusable tool','LOCAL_PROCESS',60,65,60,75,20,95,True)
        return rows
    def _persist_frontier(self,mission,compile_result,decision,ui,windows_ui,route):
        gid=mission.get('goal_id');rev=mission.get('goal_revision')
        if not gid or not isinstance(rev,int):return None,None
        h2=mission.get('h2')
        if not isinstance(h2,list) or not h2:
            h2=[
                {'id':'evidence','text':'Acquire sufficient current evidence/context','state':'ACTIVE','acceptance':['Required evidence and bindings are available'],'depends_on':[]},
                {'id':'outcome','text':'Achieve the requested outcome using qualified capabilities','state':'TENTATIVE','acceptance':['Requested outcome exists in reality'],'depends_on':['evidence']},
                {'id':'verify','text':'Verify acceptance independently and preserve receipts','state':'TENTATIVE','acceptance':['Every acceptance criterion has independent evidence'],'depends_on':['outcome']}
            ]
        frontier=self._route_frontier(mission,compile_result,ui,windows_ui)
        plan=self.core.goal_plan(gid,rev,h2,frontier,{'route':route,'laya':decision or {},'observed_at':time.time()})
        route_ids={'KNOWN_RECIPE':'route_known','GATHER_CONTEXT':'route_context','BROWSER_UI':'route_browser',
                   'WINDOWS_UI':'route_windows','SYSTEM2':'route_system2','CAPABILITY_GAP':'route_capability'}
        cid=route_ids.get(route)
        if cid:
            try:
                admitted=self.core.goal_admit(gid,plan['revision'],cid)
                return admitted['revision'],cid
            except Exception:
                return plan['revision'],None
        return plan['revision'],None
    def record_progress(self,mission,meaningful,evidence_refs,candidate_done=None,state='ACTIVE'):
        gid=mission.get('goal_id');rev=mission.get('goal_revision')
        if not gid or not isinstance(rev,int):return None
        digest=hashlib.sha256(json.dumps([bool(meaningful),evidence_refs,candidate_done,state],sort_keys=True).encode()).hexdigest()
        result=self.core.goal_progress(gid,rev,{'digest':digest,'meaningful':bool(meaningful),'evidence_refs':list(evidence_refs),
            'closed_acceptance':[],'candidate_done':candidate_done,'state':state})
        return result

    def _system2_role(self,decision,compile_result):
        answers=(decision or {}).get('answers',{})
        role=self._answer(answers,'system2_role')
        if role and role!='NONE':return str(role)
        if compile_result and compile_result.get('state')!='COMPILED':return 'TOOL_DESIGNER'
        return 'PLANNER'
    def _system2_prompt(self,mission,state,role):
        candidate_rule=''
        if role in {'CODER','TOOL_DESIGNER'}:
            candidate_rule=(
                '\nIf you propose a repo implementation and can create artifacts, write exactly two proposal artifacts: '
                'CAPABILITY_MANIFEST.json and PATCH.diff. CAPABILITY_MANIFEST.json schema must be voice-agentos.capability-candidate.v1 '
                'with only: schema, skill_id, version, kind="repo_patch", repo_profile, base_commit (40 hex), summary, effect_class, '
                'required_test_profile, expected_files, verifier. Do NOT include shell commands or credentials. PATCH.diff must apply to the exact base commit. '
                'The local runtime, not you, chooses and runs registered tests.\n'
            )
        return (
            'System-2 role: '+role+'\n'
            'You are a reasoning/coding service inside Voice AgentOS. You do not have effect authority.\n'
            'Return a concrete typed next result for the current goal. If a missing capability blocks progress, define a GapSpec/ToolCandidate with inputs, outputs, verifier, tests and effect class. '
            'If code is appropriate, create artifacts only in the bounded job sandbox. Do not claim merge/install/device success without receipts.'
            +candidate_rule+'\nMISSION:\n'+json.dumps({'goal':mission['goal'],'acceptance':mission.get('acceptance',[]),'effects':mission.get('effects',[])},ensure_ascii=False)+'\n\n'
            'DECISION_STATE:\n'+json.dumps(state,ensure_ascii=False)
        )
    def start(self,mission):
        if not isinstance(mission,dict) or not str(mission.get('goal','')).strip():raise ValueError('MISSION_GOAL_REQUIRED')
        criteria=[str(x) for x in mission.get('acceptance',[]) if str(x).strip()]
        refs=[mission.get('context_sha256')] if mission.get('context_sha256') else []
        compile_result=self.core.create_action(mission['goal'],criteria,refs)
        ui,ui_full=self._browser_inventory(mission)
        win,win_full=self._windows_inventory(mission)
        state=self._state(mission,compile_result,ui,win)
        decision=None
        try:decision=self._laya(state,ui,win)
        except Exception as exc:decision={'error':str(exc),'answers':{}}
        answers=(decision or {}).get('answers',{})
        route=self._answer(answers,'mission_route')
        goal_revision,h0_candidate=self._persist_frontier(mission,compile_result,decision,ui,win,route)
        if goal_revision is not None:mission['goal_revision']=goal_revision
        if compile_result.get('state')=='COMPILED' and route not in {'SYSTEM2','CAPABILITY_GAP','GATHER_CONTEXT','WAIT','STOP'}:
            job=self.core.enqueue_action(compile_result['intent_id'],compile_result['revision'])
            return {'schema':'voice-agentos.mission-step.v1','state':'CORE_JOB_QUEUED','compile':compile_result,'laya':decision,'job':job,'goal_revision':mission.get('goal_revision'),'h0_candidate_id':h0_candidate}
        if route=='STOP':return {'schema':'voice-agentos.mission-step.v1','state':'STOPPED_BY_ROUTER','compile':compile_result,'laya':decision}
        if route=='WAIT':return {'schema':'voice-agentos.mission-step.v1','state':'WAITING_EXTERNAL','compile':compile_result,'laya':decision}
        if route=='GATHER_CONTEXT':return {'schema':'voice-agentos.mission-step.v1','state':'NEEDS_CONTEXT','compile':compile_result,'laya':decision,'goal_revision':mission.get('goal_revision'),'h0_candidate_id':h0_candidate}
        if route=='WINDOWS_UI':
            if not win or not win_full:return {'schema':'voice-agentos.mission-step.v1','state':'NEEDS_WINDOWS_BINDING','compile':compile_result,'laya':decision}
            candidate_id=self._answer(answers,'windows_ui_candidate','NONE');action=self._answer(answers,'windows_ui_action','ABSTAIN')
            candidates={x.get('element_id'):x for x in win_full.get('elements',[]) if isinstance(x,dict)}
            candidate=candidates.get(candidate_id)
            if not candidate or candidate_id=='NONE':return {'schema':'voice-agentos.mission-step.v1','state':'WINDOWS_UI_ABSTAIN','laya':decision}
            request={'snapshot_id':win['snapshot_id'],'element_id':candidate_id,'expected_fingerprint':candidate.get('fingerprint')}
            if action=='SCROLL_INTO_VIEW':
                request['action']='scroll_into_view';request['effect_class']='READ'
            elif action=='INVOKE_READ_NAV':
                if candidate.get('risk')!='READ_NAV':return {'schema':'voice-agentos.mission-step.v1','state':'WINDOWS_UI_BLOCKED','reason':'NOT_READ_NAV','candidate':candidate,'laya':decision}
                request['action']='invoke';request['effect_class']='WINDOWS_WRITE'
            elif action=='NEED_TYPED_INPUT':
                route='SYSTEM2'
            else:return {'schema':'voice-agentos.mission-step.v1','state':'WINDOWS_UI_ABSTAIN','candidate':candidate,'laya':decision}
            if route=='WINDOWS_UI':
                try:receipt=self.windows_ui.act(request)
                except Exception as exc:
                    if 'WINDOWS_UI_HUMAN_FOREGROUND_LEASE' in str(exc):
                        return {'schema':'voice-agentos.mission-step.v1','state':'WAITING_HUMAN_FOREGROUND','surface':'WINDOWS',
                                'compile':compile_result,'laya':decision,'candidate':candidate}
                    raise
                return {'schema':'voice-agentos.mission-step.v1','state':'WINDOWS_UI_EFFECT','compile':compile_result,'laya':decision,'candidate':candidate,'ui_receipt':receipt}
        if route=='BROWSER_UI':
            if not ui or not ui_full:return {'schema':'voice-agentos.mission-step.v1','state':'NEEDS_BINDING','compile':compile_result,'laya':decision}
            candidate_id=self._answer(answers,'ui_candidate','NONE');action=self._answer(answers,'ui_action','ABSTAIN')
            candidates={x.get('element_id'):x for x in ui_full.get('elements',[]) if isinstance(x,dict)}
            candidate=candidates.get(candidate_id)
            if not candidate or candidate_id=='NONE':return {'schema':'voice-agentos.mission-step.v1','state':'BROWSER_UI_ABSTAIN','compile':compile_result,'laya':decision}
            request={'snapshot_id':ui['snapshot_id'],'document_token':ui['document_token'],'element_id':candidate_id,
                     'expected_fingerprint':candidate.get('fingerprint')}
            if action=='SCROLL_INTO_VIEW':
                request['action']='scroll_into_view';request['effect_class']='READ'
            elif action=='CLICK_READ_NAV':
                if candidate.get('risk')!='READ_NAV':return {'schema':'voice-agentos.mission-step.v1','state':'BROWSER_UI_BLOCKED','reason':'NOT_READ_NAV','candidate':candidate,'laya':decision}
                request['action']='click';request['effect_class']='BROWSER_WRITE'
            elif action=='NEED_TYPED_INPUT':
                route='SYSTEM2'
            else:return {'schema':'voice-agentos.mission-step.v1','state':'BROWSER_UI_ABSTAIN','candidate':candidate,'laya':decision}
            if route=='BROWSER_UI':
                try:receipt=self.bridge.ui_act(request,ui.get('tab_id'))
                except Exception as exc:
                    if 'UI_HUMAN_FOREGROUND_LEASE' in str(exc):
                        return {'schema':'voice-agentos.mission-step.v1','state':'WAITING_HUMAN_FOREGROUND','surface':'BROWSER',
                                'compile':compile_result,'laya':decision,'candidate':candidate}
                    raise
                return {'schema':'voice-agentos.mission-step.v1','state':'BROWSER_UI_EFFECT','compile':compile_result,
                        'laya':decision,'candidate':candidate,'ui_receipt':receipt}
        if not self.bridge:return {'schema':'voice-agentos.mission-step.v1','state':'SYSTEM2_UNAVAILABLE','compile':compile_result,'laya':decision}
        role=self._system2_role(decision,compile_result)
        context=bounded_utf8(mission.get('context_text') or json.dumps({'compile':compile_result},ensure_ascii=False))
        prompt=self._system2_prompt(mission,state,role)
        mode='build' if role in {'CODER','TOOL_DESIGNER'} else 'analyze'
        try:submitted=self.bridge.codex_submit(prompt,context,mode)
        except Exception:
            if mode!='build':raise
            submitted=self.bridge.codex_submit(prompt,context,'analyze')
            mode='analyze'
        job=submitted.get('job') if isinstance(submitted,dict) else None
        job_id=job.get('id') if isinstance(job,dict) else None
        if not job_id:raise ValueError('SYSTEM2_JOB_ID_REQUIRED')
        return {'schema':'voice-agentos.mission-step.v1','state':'WAITING_SYSTEM2','compile':compile_result,'laya':decision,'role':role,'system2_mode':mode,'system2_job_id':job_id,'goal_revision':mission.get('goal_revision'),'h0_candidate_id':h0_candidate}
    def observe_capability_pr(self,pr_receipt):
        if not self.github_pipeline:raise ValueError('GITHUB_PIPELINE_UNAVAILABLE')
        return self.github_pipeline.observe(pr_receipt)

    def merge_capability_pr(self,pr_receipt,effect_scope):
        if not self.github_pipeline:raise ValueError('GITHUB_PIPELINE_UNAVAILABLE')
        return self.github_pipeline.merge(pr_receipt,effect_scope)

    def capture_windows_context(self):
        if not self.windows_ui:raise ValueError('WINDOWS_UI_UNAVAILABLE')
        snap=self.windows_ui.text_snapshot()
        text=snap.get('text','')
        if not text.strip():raise ValueError('WINDOWS_UI_TEXT_EMPTY')
        digest=hashlib.sha256(text.encode()).hexdigest()
        path=self.root/('windows_'+str(int(time.time()))+'_'+digest[:10]+'.txt')
        path.write_text(text,encoding='utf-8')
        receipt=self.core.capture_file(path,'windows_ui_'+digest[:18])
        try:self.core.annotate_capture(receipt,project='WindowsUI',note='foreground Windows UI Automation snapshot',labels=['source:windows-uia','type:ui-context'])
        except Exception:pass
        return {'schema':'voice-agentos.mission-step.v1','state':'WINDOWS_CONTEXT_GATHERED','text':bounded_utf8(text),
                'sha256':digest,'snapshot':snap.get('snapshot'),'library_receipt':receipt}

    def capture_browser_context(self):
        if not self.bridge:raise ValueError('BROWSER_BRIDGE_UNAVAILABLE')
        tab=self.bridge.active_tab();tab_id=tab.get('id') if isinstance(tab,dict) else None
        assembler=BrowserArchiveAssembler(self.root/'mission-browser','mission_'+str(tab_id)+'_'+str(int(time.time())))
        try:
            manifest=self.bridge.capture_archive(tab_id,on_chunk=assembler.add_chunk,max_bytes=67108864,max_steps=2500,max_ms=90000)
            archive=assembler.finalize(manifest)
        except Exception as exc:
            assembler.abort(str(exc));raise
        receipts=[]
        for field,prefix in [('txt_path','mission_browser_txt'),('metadata_path','mission_browser_meta'),('raw_stream_path','mission_browser_stream')]:
            path=archive.get(field)
            if not path:continue
            digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
            receipt=self.core.capture_file(path,prefix+'_'+digest[:18]);receipts.append(receipt)
            try:self.core.annotate_capture(receipt,project='AgentOS',note='mission browser context '+str(archive.get('source')),labels=['source:browser','type:mission-context','status:'+str(archive.get('status') or 'unknown').lower()])
            except Exception:pass
        text=Path(archive['txt_path']).read_text(encoding='utf-8',errors='replace')
        return {'schema':'voice-agentos.mission-step.v1','state':'CONTEXT_GATHERED','text':bounded_utf8(text),
                'sha256':archive['txt_sha256'],'archive':archive,'library_receipts':receipts}

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
        try:self.core.annotate_capture(receipt,project='AgentOS',note='System2 result job='+job_id,labels=['source:system2','type:ai-result'])
        except Exception:pass
        candidate=None;capability_pr=None
        if self.candidate_pipeline and {'LOCAL_WRITE','GIT_WRITE'} & set(mission.get('effects',[])):
            try:candidate=self.candidate_pipeline.try_qualify_job(job_id)
            except Exception as exc:candidate={'state':'CAPABILITY_CANDIDATE_BLOCKED','reason':str(exc)}
        if isinstance(candidate,dict) and candidate.get('state')=='ISOLATED_TESTED' and self.github_pipeline and 'GITHUB_WRITE' in set(mission.get('effects',[])):
            try:capability_pr=self.github_pipeline.publish(candidate,mission.get('effects',[]))
            except Exception as exc:capability_pr={'state':'CAPABILITY_PR_BLOCKED','reason':str(exc)}
        final_state='SYSTEM2_RESULT_INGESTED'
        if isinstance(candidate,dict) and candidate.get('state')=='ISOLATED_TESTED':final_state='CAPABILITY_CANDIDATE_TESTED'
        if isinstance(capability_pr,dict) and capability_pr.get('state')=='PR_OPEN':final_state='CAPABILITY_PR_OPEN'
        return {'schema':'voice-agentos.mission-step.v1','state':final_state,'system2_job':job,'text':text,'sha256':digest,
                'path':str(path),'library_receipt':receipt,'capability_candidate':candidate,'capability_pr':capability_pr}
