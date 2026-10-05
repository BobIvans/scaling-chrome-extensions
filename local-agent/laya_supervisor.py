from __future__ import annotations
import json,os,subprocess,time
from pathlib import Path
from urllib.request import Request,urlopen

PINNED_LAYA_VERSION='0.3.23'
PINNED_LAYA_COMMIT='d8a2e59'

class LayaSupervisorError(RuntimeError):pass

class LayaSupervisor:
    """Own one pinned local laya-serve process for System-1 decisions."""
    def __init__(self,config,opener=urlopen,runner=subprocess.Popen):
        self.c=config or {};self.opener=opener;self.runner=runner;self.process=None
        self._validate()
    @property
    def enabled(self):return self.c.get('enabled') is True
    def _validate(self):
        if not self.enabled:return
        required={'enabled','python_path','host','port','device','models','default_model','threads','max_loaded',
                  'preload','api_key_env','min_confidence','startup_timeout_seconds','idle_unload_seconds'}
        if set(self.c)!=required:raise LayaSupervisorError('LAYA_SUPERVISOR_CONFIG')
        if self.c['host'] not in {'127.0.0.1','localhost'}:raise LayaSupervisorError('LAYA_LOOPBACK_REQUIRED')
        if not isinstance(self.c['port'],int) or not (1024<=self.c['port']<=65535):raise LayaSupervisorError('LAYA_PORT')
        if self.c['device'] not in {'cpu','cuda','mps','auto'}:raise LayaSupervisorError('LAYA_DEVICE')
        if not isinstance(self.c['models'],list) or not self.c['models'] or any(x not in {'english','multilingual','typed-decisions'} for x in self.c['models']):raise LayaSupervisorError('LAYA_MODELS')
        if self.c['default_model'] not in self.c['models']:raise LayaSupervisorError('LAYA_DEFAULT_MODEL')
        if not isinstance(self.c['threads'],int) or not 1<=self.c['threads']<=32:raise LayaSupervisorError('LAYA_THREADS')
        if not isinstance(self.c['max_loaded'],int) or not 1<=self.c['max_loaded']<=3:raise LayaSupervisorError('LAYA_MAX_LOADED')
        if not isinstance(self.c['min_confidence'],(int,float)) or not 0<=float(self.c['min_confidence'])<=1:raise LayaSupervisorError('LAYA_CONFIDENCE')
    @property
    def endpoint(self):return f"http://{self.c['host']}:{self.c['port']}/v1/systemone"
    @property
    def health_url(self):return f"http://{self.c['host']}:{self.c['port']}/health"
    def _headers(self):
        headers={'Accept':'application/json','User-Agent':'VoiceAgentOS/1'}
        env_name=self.c.get('api_key_env')
        token=str(os.environ.get(env_name,'')).strip() if env_name else ''
        if token:headers['Authorization']='Bearer '+token
        return headers
    def health(self,timeout=3):
        try:
            raw=self.opener(Request(self.health_url,headers=self._headers()),timeout=timeout).read(1000001)
        except Exception as exc:raise LayaSupervisorError('LAYA_HEALTH_UNAVAILABLE') from exc
        if len(raw)>1000000:raise LayaSupervisorError('LAYA_HEALTH_LIMIT')
        try:value=json.loads(raw.decode('utf-8'))
        except Exception as exc:raise LayaSupervisorError('LAYA_HEALTH_SCHEMA') from exc
        if not isinstance(value,dict) or value.get('status')!='ok':raise LayaSupervisorError('LAYA_HEALTH_BAD')
        return value
    def _python(self):
        p=Path(os.path.expandvars(os.path.expanduser(self.c['python_path']))).resolve()
        if not p.is_file():raise LayaSupervisorError('LAYA_PYTHON_MISSING')
        return p
    def start(self):
        if not self.enabled:return {'state':'DISABLED'}
        try:
            h=self.health()
            return {'state':'READY','reused':True,'health':h,'endpoint':self.endpoint,
                    'expected_package_version':PINNED_LAYA_VERSION,'expected_release_commit':PINNED_LAYA_COMMIT}
        except LayaSupervisorError:pass
        env=dict(os.environ)
        env.update({
            'LAYA_HOST':self.c['host'],'LAYA_PORT':str(self.c['port']),'LAYA_DEVICE':self.c['device'],
            'LAYA_MODELS':','.join(self.c['models']),'LAYA_DEFAULT_MODEL':self.c['default_model'],
            'LAYA_THREADS':str(self.c['threads']),'LAYA_MAX_LOADED':str(self.c['max_loaded']),
            'LAYA_PRELOAD':'1' if self.c['preload'] else '0',
            'LAYA_IDLE_UNLOAD_SECONDS':str(self.c['idle_unload_seconds']),
        })
        key_env=self.c.get('api_key_env')
        if key_env and os.environ.get(key_env):env['LAYA_API_KEY']=os.environ[key_env]
        kwargs=dict(cwd=str(self._python().parent),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,shell=False)
        if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
        try:self.process=self.runner([str(self._python()),'-m','laya.serve'],**kwargs)
        except OSError as exc:raise LayaSupervisorError('LAYA_START_FAILED') from exc
        deadline=time.monotonic()+max(5,int(self.c['startup_timeout_seconds']))
        last=None
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise LayaSupervisorError('LAYA_EXITED_DURING_START')
            try:
                h=self.health()
                return {'state':'READY','reused':False,'health':h,'endpoint':self.endpoint,
                        'expected_package_version':PINNED_LAYA_VERSION,'expected_release_commit':PINNED_LAYA_COMMIT}
            except Exception as exc:last=exc;time.sleep(.5)
        self.stop()
        raise LayaSupervisorError('LAYA_START_TIMEOUT') from last
    def ensure(self):
        if not self.enabled:return {'state':'DISABLED'}
        try:return {'state':'READY','health':self.health(),'endpoint':self.endpoint}
        except Exception:return self.start()
    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=8)
            except Exception:self.process.kill()
        self.process=None
    def benchmark(self,client,rounds=5):
        if rounds<1 or rounds>50:raise LayaSupervisorError('LAYA_BENCH_ROUNDS')
        self.ensure()
        state={'goal':'benchmark routing','context':'refund twice, fix code after gathering evidence'}
        questions={'route':{'type':'choice','instructions':'Choose route','criteria':{'research':'gather evidence','code':'implement change','wait':'wait'}}}
        times=[];answers=[]
        for _ in range(rounds):
            start=time.perf_counter();value=client.decide(state,questions,float(self.c['min_confidence']));times.append((time.perf_counter()-start)*1000)
            answers.append(value.get('answers'))
        ordered=sorted(times)
        return {'schema':'voice-agentos.laya-benchmark.v1','rounds':rounds,'p50_ms':ordered[len(ordered)//2],
                'min_ms':min(times),'max_ms':max(times),'answers':answers,'health':self.health(),
                'expected_package_version':PINNED_LAYA_VERSION,'expected_release_commit':PINNED_LAYA_COMMIT}
