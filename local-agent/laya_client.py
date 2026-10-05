from __future__ import annotations
import json,os
from urllib.request import Request,urlopen

class LayaError(RuntimeError):pass

class LayaClient:
    def __init__(self,endpoint,timeout=20,opener=urlopen,api_key_env='',model=None):
        self.endpoint=str(endpoint or '').strip().rstrip('/')
        self.timeout=timeout;self.opener=opener;self.api_key_env=str(api_key_env or '');self.model=model
    @property
    def enabled(self):return self.endpoint.startswith('http://127.0.0.1:') or self.endpoint.startswith('http://localhost:')
    @property
    def health_url(self):
        if self.endpoint.endswith('/v1/systemone'):return self.endpoint[:-len('/v1/systemone')]+'/health'
        return self.endpoint.rsplit('/',1)[0]+'/health'
    def _headers(self,json_body=False):
        h={'Accept':'application/json','User-Agent':'VoiceAgentOS/1'}
        if json_body:h['Content-Type']='application/json'
        token=str(os.environ.get(self.api_key_env,'')).strip() if self.api_key_env else ''
        if token:h['Authorization']='Bearer '+token
        return h
    def _json(self,req,limit=1000000):
        try:raw=self.opener(req,timeout=self.timeout).read(limit+1)
        except Exception as exc:raise LayaError('LAYA_UNAVAILABLE') from exc
        if len(raw)>limit:raise LayaError('LAYA_RESPONSE_LIMIT')
        try:value=json.loads(raw.decode())
        except Exception as exc:raise LayaError('LAYA_RESPONSE_SCHEMA') from exc
        if not isinstance(value,dict):raise LayaError('LAYA_RESPONSE_SCHEMA')
        return value
    def health(self):
        if not self.enabled:raise LayaError('LAYA_LOCAL_ENDPOINT_REQUIRED')
        value=self._json(Request(self.health_url,headers=self._headers()),200000)
        if value.get('status')!='ok':raise LayaError('LAYA_HEALTH_BAD')
        return value
    def decide(self,state,questions,min_confidence=0.72,model=None):
        if not self.enabled:raise LayaError('LAYA_LOCAL_ENDPOINT_REQUIRED')
        if not isinstance(questions,dict) or not questions:raise LayaError('LAYA_QUESTIONS_REQUIRED')
        body={'state':state,'questions':questions,'min_confidence':float(min_confidence)}
        chosen=model or self.model
        if chosen:body['model']=chosen
        req=Request(self.endpoint,data=json.dumps(body,ensure_ascii=False).encode(),headers=self._headers(True),method='POST')
        value=self._json(req)
        answers=value.get('answers')
        if not isinstance(answers,dict):raise LayaError('LAYA_RESPONSE_SCHEMA')
        for key,answer in answers.items():
            if key not in questions or not isinstance(answer,dict):raise LayaError('LAYA_ANSWER_SCHEMA')
            confidence=answer.get('answer_confidence')
            if confidence is not None and (not isinstance(confidence,(int,float)) or not 0<=float(confidence)<=1):raise LayaError('LAYA_CONFIDENCE_SCHEMA')
            if answer.get('abstention') is True:
                answer['voice_agentos_admitted']=False
            elif confidence is not None and float(confidence)<float(min_confidence):
                answer['voice_agentos_admitted']=False
            else:answer['voice_agentos_admitted']=True
        return value
