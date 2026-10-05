from __future__ import annotations
import json
from urllib.request import Request,urlopen
class LayaError(RuntimeError):pass
class LayaClient:
    def __init__(self,endpoint,timeout=20,opener=urlopen):self.endpoint=str(endpoint or '').strip();self.timeout=timeout;self.opener=opener
    @property
    def enabled(self):return self.endpoint.startswith('http://127.0.0.1:') or self.endpoint.startswith('http://localhost:')
    def decide(self,state,questions,min_confidence=0.72):
        if not self.enabled:raise LayaError('LAYA_LOCAL_ENDPOINT_REQUIRED')
        body={'state':state,'questions':questions,'min_confidence':min_confidence}
        req=Request(self.endpoint,data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Accept':'application/json'},method='POST')
        try:raw=self.opener(req,timeout=self.timeout).read(1000001)
        except Exception as exc:raise LayaError('LAYA_UNAVAILABLE') from exc
        if len(raw)>1000000:raise LayaError('LAYA_RESPONSE_LIMIT')
        try:value=json.loads(raw.decode())
        except Exception as exc:raise LayaError('LAYA_RESPONSE_SCHEMA') from exc
        if not isinstance(value,dict) or not isinstance(value.get('answers'),dict):raise LayaError('LAYA_RESPONSE_SCHEMA')
        return value
