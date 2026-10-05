from __future__ import annotations
import hashlib, json, math, re, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SAFE_PARALLEL_EFFECTS={'READ','LOCAL_READ','LOCAL_PROCESS'}
ROUTE_TO_ID={
    'KNOWN_RECIPE':'route_known',
    'GATHER_CONTEXT':'route_context',
    'BROWSER_UI':'route_browser',
    'WINDOWS_UI':'route_windows',
    'SYSTEM2':'route_system2',
    'CAPABILITY_GAP':'route_capability',
}
ID_TO_ROUTE={v:k for k,v in ROUTE_TO_ID.items()}

class FastDecisionError(RuntimeError):
    pass

def _number(value,default=0.0):
    try:
        v=float(value)
        return v if math.isfinite(v) else float(default)
    except Exception:
        return float(default)

def utility(candidate):
    c=candidate.get('components') or {}
    score=(
        _number(c.get('progress'))*1.8+
        _number(c.get('information_gain'))*1.2+
        _number(c.get('success_probability'))*1.4+
        _number(c.get('unlock_count'))*.6+
        (8.0 if c.get('parallelizable') is True else 0.0)-
        _number(c.get('latency_cost'))*.7-
        _number(c.get('human_cost'))*1.0-
        _number(c.get('resource_cost'))*.5-
        _number(c.get('risk_penalty'))*1.5-
        _number(c.get('freshness_penalty'))*.8
    )
    return round(score,6)

def _keywords(goal,limit=6):
    words=re.findall(r"[A-Za-z0-9_\-]{4,}",str(goal or '').lower())
    stop={'this','that','with','from','into','then','when','have','will','your','please','about','need','goal','context','agent','automation'}
    out=[]
    for w in words:
        if w in stop or w in out:continue
        out.append(w)
        if len(out)>=limit:break
    return out

def compact_library(value,limit=8):
    rows=value.get('rows',[]) if isinstance(value,dict) else []
    out=[]
    for row in rows[:limit]:
        if not isinstance(row,dict):continue
        ref=row.get('source_ref') or {}
        ann=row.get('annotation') or {}
        out.append({
            'source_key':ref.get('source_key'),
            'revision':ref.get('revision'),
            'project':ann.get('project'),
            'labels':list(ann.get('labels') or [])[:12],
            'why_selected':row.get('why_selected'),
            'snippet':str(row.get('snippet') or '')[:320],
            'total_bytes':row.get('total_bytes'),
        })
    return {'state':value.get('state') if isinstance(value,dict) else 'NO_MATCH','rows':out}

class FastDecisionEngine:
    """Parallel read-prefetch + deterministic fastest-verified admission.

    Laya is a fast semantic ranker/critic. This engine owns no effects and can
    override an abstention or clearly lower-utility route with a deterministic
    admissible route. Core remains the authority for H0 admission/effects.
    """
    def __init__(self,core,bridge=None,windows_ui=None,stats_path=None,config=None):
        self.core=core;self.bridge=bridge;self.windows_ui=windows_ui
        self.config={
            'max_workers':4,
            'library_search_limit':8,
            'laya_override_margin':12.0,
            'human_quiet_ms':1800,
            'max_parallel_lanes':3,
            **(config or {})
        }
        self.stats_path=Path(stats_path).expanduser().resolve() if stats_path else None
        self._lock=threading.Lock()

    def _timed(self,name,fn):
        start=time.perf_counter()
        try:
            value=fn()
            return {'name':name,'state':'OK','elapsed_ms':round((time.perf_counter()-start)*1000,3),'value':value}
        except Exception as exc:
            return {'name':name,'state':'BLOCKED','elapsed_ms':round((time.perf_counter()-start)*1000,3),'error':str(exc)[:500]}

    def _library_lane(self,mission):
        goal=str(mission.get('goal') or '')
        words=_keywords(goal)
        # Search the most specific few terms in parallel would create extra Core
        # processes; one bounded query is faster and deterministic here.
        query=' '.join(words[:2]) if words else goal[:200]
        result=self.core.library_search(query=query,limit=int(self.config['library_search_limit']))
        if result.get('state')=='NO_MATCH' and words:
            result=self.core.library_search(query=words[0],limit=int(self.config['library_search_limit']))
        return compact_library(result,int(self.config['library_search_limit']))

    def _browser_lane(self):
        if not self.bridge:return None
        return self.bridge.ui_inventory()

    def _windows_lane(self):
        if not self.windows_ui:return None
        return self.windows_ui.inventory()

    def prefetch(self,mission):
        lanes={'library':lambda:self._library_lane(mission)}
        if self.bridge:lanes['browser_ui']=self._browser_lane
        if self.windows_ui:lanes['windows_ui']=self._windows_lane
        results={}
        start=time.perf_counter()
        with ThreadPoolExecutor(max_workers=min(int(self.config['max_workers']),len(lanes)),thread_name_prefix='agentos-decision') as pool:
            futures={pool.submit(self._timed,name,fn):name for name,fn in lanes.items()}
            for future in as_completed(futures):
                value=future.result();results[value['name']]=value
        elapsed=round((time.perf_counter()-start)*1000,3)
        receipt={'schema':'voice-agentos.fast-prefetch.v1','elapsed_ms':elapsed,'lanes':results,'parallel':len(lanes)>1}
        self._record_prefetch(receipt)
        return receipt

    def _record_prefetch(self,receipt):
        if not self.stats_path:return
        try:
            with self._lock:
                old={'schema':'voice-agentos.decision-stats.v1','prefetch':[]}
                if self.stats_path.exists():
                    value=json.loads(self.stats_path.read_text(encoding='utf-8'))
                    if isinstance(value,dict) and value.get('schema')==old['schema']:old=value
                rows=list(old.get('prefetch') or [])[-99:]
                rows.append({'observed_at':time.time(),'elapsed_ms':receipt['elapsed_ms'],
                             'lanes':{k:{'state':v.get('state'),'elapsed_ms':v.get('elapsed_ms')} for k,v in receipt['lanes'].items()}})
                old['prefetch']=rows
                self.stats_path.parent.mkdir(parents=True,exist_ok=True)
                tmp=self.stats_path.with_suffix('.tmp');tmp.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(self.stats_path)
        except Exception:
            pass

    def _eligible(self,candidate,effect_scope,prefetch):
        if candidate.get('state')!='CANDIDATE':return False,'NOT_CANDIDATE'
        effect=candidate.get('effect_class')
        if effect not in {'READ','LOCAL_READ'} and effect not in set(effect_scope):return False,'EFFECT_SCOPE'
        cid=candidate.get('id')
        lanes=prefetch.get('lanes',{}) if isinstance(prefetch,dict) else {}
        if cid=='route_browser':
            row=lanes.get('browser_ui') or {}
            if row.get('state')!='OK' or not row.get('value'):return False,'NO_BROWSER_BINDING'
            activity=_number((row.get('value') or {}).get('human_activity_ms'),999999)
            focused=(row.get('value') or {}).get('document_has_focus') is True
            if focused and activity<float(self.config['human_quiet_ms']):return False,'HUMAN_FOREGROUND'
        if cid=='route_windows':
            row=lanes.get('windows_ui') or {}
            if row.get('state')!='OK' or not row.get('value'):return False,'NO_WINDOWS_BINDING'
        return True,None

    def _dynamic(self,candidate,prefetch):
        row=json.loads(json.dumps(candidate))
        c=row.setdefault('components',{})
        lanes=prefetch.get('lanes',{}) if isinstance(prefetch,dict) else {}
        cid=row.get('id')
        lane=None
        if cid=='route_browser':lane=lanes.get('browser_ui')
        elif cid=='route_windows':lane=lanes.get('windows_ui')
        elif cid=='route_context':
            context_lanes=[x for x in (lanes.get('library'),lanes.get('browser_ui'),lanes.get('windows_ui')) if isinstance(x,dict)]
            healthy=[x for x in context_lanes if x.get('state')=='OK']
            lane=min(healthy,key=lambda x:_number(x.get('elapsed_ms'),999999)) if healthy else (context_lanes[0] if context_lanes else None)
        if lane:
            # Convert measured milliseconds into bounded 0..100 latency cost.
            ms=_number(lane.get('elapsed_ms'),1000)
            c['latency_cost']=min(100.0,max(0.0,math.log10(max(1.0,ms))*18.0))
            if lane.get('state')=='BLOCKED':
                c['success_probability']=min(_number(c.get('success_probability')),10.0)
                c['risk_penalty']=max(_number(c.get('risk_penalty')),25.0)
        row['utility']=utility(row)
        return row

    def choose(self,frontier,laya_route,effect_scope,prefetch):
        ranked=[];blocked=[]
        for raw in frontier:
            candidate=self._dynamic(raw,prefetch)
            ok,reason=self._eligible(candidate,effect_scope,prefetch)
            if ok:ranked.append(candidate)
            else:blocked.append({'id':candidate.get('id'),'reason':reason,'utility':candidate.get('utility')})
        ranked.sort(key=lambda x:(-x['utility'],x['id']))
        if not ranked:
            return {'schema':'voice-agentos.fast-decision.v1','route':'STOP','candidate_id':None,'reason':'NO_ADMISSIBLE_ROUTE','ranked':[],'blocked':blocked}
        top=ranked[0]
        laya_id=ROUTE_TO_ID.get(laya_route)
        laya_candidate=next((x for x in ranked if x.get('id')==laya_id),None)
        margin=float(self.config['laya_override_margin'])
        if laya_candidate and laya_candidate['utility']>=top['utility']-margin:
            selected=laya_candidate;reason='LAYA_WITHIN_FAST_MARGIN'
        else:
            selected=top;reason='DETERMINISTIC_FASTEST_VERIFIED'
        route=ID_TO_ROUTE.get(selected['id'],selected.get('kind'))
        return {'schema':'voice-agentos.fast-decision.v1','route':route,'candidate_id':selected['id'],'reason':reason,
                'selected_utility':selected['utility'],'laya_route':laya_route,'ranked':ranked,'blocked':blocked,
                'prefetch_elapsed_ms':prefetch.get('elapsed_ms') if isinstance(prefetch,dict) else None}

    def parallel_plan(self,frontier,primary_id,effect_scope,prefetch):
        selected=[];used=set()
        for raw in sorted((self._dynamic(x,prefetch) for x in frontier),key=lambda x:(-x['utility'],x['id'])):
            if raw.get('id')==primary_id or raw.get('components',{}).get('parallelizable') is not True:continue
            if raw.get('effect_class') not in SAFE_PARALLEL_EFFECTS:continue
            ok,_=self._eligible(raw,effect_scope,prefetch)
            if not ok:continue
            resources=set(raw.get('resources') or [])
            if resources & used:continue
            if _number(raw.get('components',{}).get('risk_penalty'))>25:continue
            selected.append({'candidate_id':raw['id'],'route':ID_TO_ROUTE.get(raw['id'],raw.get('kind')),
                             'utility':raw['utility'],'resources':sorted(resources)})
            used|=resources
            if len(selected)>=int(self.config['max_parallel_lanes']):break
        return selected
