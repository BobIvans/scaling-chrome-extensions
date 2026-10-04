"""Optional local PTT input, never an action executor or authorization source."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid
import wave


class Capture:
    def __init__(self, root, *, device=None, stream_factory=None, max_seconds=60):
        self.root=Path(root).absolute()
        self.root.mkdir(parents=True,exist_ok=True)
        if self.root.is_symlink() or any(p.is_symlink() for p in self.root.parents):
            raise ValueError('VOICE_CAPTURE_ROOT_LINK')
        self.device=device
        self.factory=stream_factory
        self.max_seconds=max_seconds
        self.lock=threading.RLock()
        self.stream=None
        self.output=None
        self.session=None
        self.tts_active=False
        self.failure=None
        self.lease=None
        self._recover()

    def _recover(self):
        # Called only after acquiring the OS capture lease in press().
        if self.lease is None:
            return
        # Recover only our explicit sidecars. A prior process's partial WAV is
        # retained as aborted evidence, never fed silently into a new command.
        for p in self.root.glob('voice-*.json'):
            if p.is_symlink() or p.stat().st_size>16_000:
                continue
            try:
                value=json.loads(p.read_text(encoding='utf-8'))
                if value.get('schema')=='occ.capture-session.v1' and value.get('state')=='CAPTURING':
                    value.update(state='ABORTED',reason='PROCESS_RESTART',gap=True)
                    p.write_text(json.dumps(value),encoding='utf-8')
            except (OSError,ValueError):
                continue

    def _save(self):
        path=self.root/(self.session['id']+'.json')
        tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.session,ensure_ascii=False),encoding='utf-8')
        os.replace(tmp,path)

    def press(self, *, physical=True):
        with self.lock:
            if self.stream is not None:
                return dict(self.session)
            if not physical or self.tts_active:
                raise ValueError('VOICE_PHYSICAL_ACTIVATION_REQUIRED')
            handle=(self.root/'capture.lock').open('a+b')
            try:
                if handle.seek(0,2)==0:
                    handle.write(b'0');handle.flush()
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc:
                handle.close()
                raise ValueError('VOICE_CAPTURE_BUSY') from exc
            self.lease=handle
            self._recover()
            if self.factory is None:
                try:
                    import sounddevice
                except ImportError as exc:
                    self.lease.close();self.lease=None
                    raise ValueError('VOICE_SOUNDDEVICE_UNAVAILABLE') from exc
                self.factory=sounddevice.RawInputStream
            self.failure=None
            key='voice-'+uuid.uuid4().hex
            self.session={'schema':'occ.capture-session.v1','id':key,'state':'CAPTURING','device':self.device,
                          'started':time.time(),'ended':None,'frames':0,'gap':False,'reason':None,
                          'physical_activation':True,'audio_filename':key+'.wav'}
            self.started=time.monotonic()
            try:
                self.output=wave.open(str(self.root/(key+'.wav')),'wb')
                self.output.setnchannels(1);self.output.setsampwidth(2);self.output.setframerate(16000)
                self._save()
                self.stream=self.factory(samplerate=16000,channels=1,dtype='int16',device=self.device,
                                         callback=self._audio,blocksize=1600)
            except BaseException:
                self.stop('DEVICE_ERROR')
                raise
        # PortAudio may run callbacks immediately. Start outside their lock.
        try:
            self.stream.start()
        except BaseException:
            self.stop('DEVICE_ERROR')
            raise
        return dict(self.session)

    def _audio(self, data, frames, _timing, status):
        with self.lock:
            if self.output is None:
                return
            if status or self.tts_active:
                self.session['gap']=True
            if self.tts_active:
                return
            try:
                self.output.writeframesraw(bytes(data))
                self.session['frames']+=frames
            except (OSError,ValueError) as exc:
                self.failure=type(exc).__name__

    def poll(self):
        if self.stream is not None and (self.failure or time.monotonic()-self.started>=self.max_seconds or
                getattr(self.stream,'active',True) is False):
            return self.stop('CAPTURE_ERROR' if self.failure else 'DEVICE_LOST' if getattr(self.stream,'active',True) is False else 'SESSION_DURATION')
        return self.session

    def stop(self, reason='USER_RELEASE'):
        # PortAudio stop waits for callbacks. Do not hold the callback lock while
        # stopping; otherwise GUI STOP could deadlock behind the audio thread.
        with self.lock:
            stream,self.stream=self.stream,None
        error=None
        if stream is not None:
            try:
                stream.stop()
            except Exception as exc:
                error=type(exc).__name__
            finally:
                try:
                    stream.close()
                except Exception as exc:
                    error=type(exc).__name__
        with self.lock:
            if self.output is not None:
                self.output.close();self.output=None
            if self.session is None:
                if self.lease is not None:self.lease.close();self.lease=None
                return None
            self.session.update(state='STOPPED' if not error and reason in {'USER_RELEASE','STOP','SESSION_DURATION'} else 'ABORTED',
                                ended=time.time(),reason=error or reason)
            try:
                self._save()
            finally:
                if self.lease is not None:self.lease.close();self.lease=None
            return dict(self.session)


class WindowsHotkey:
    """Register Ctrl+Shift+Space; poll WM_HOTKEY and key-up on Tk owner thread."""
    def __init__(self, on_press, on_release):
        if os.name!='nt':
            raise ValueError('VOICE_WINDOWS_HOTKEY_UNAVAILABLE')
        self.user=ctypes.windll.user32
        self.user.RegisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int,wintypes.UINT,wintypes.UINT]
        self.user.RegisterHotKey.restype=wintypes.BOOL
        self.user.PeekMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT,wintypes.UINT]
        self.user.GetAsyncKeyState.argtypes=[ctypes.c_int]
        self.user.GetAsyncKeyState.restype=ctypes.c_short
        self.id=0xB018
        self.press,self.release=on_press,on_release
        self.held=False
        if not self.user.RegisterHotKey(None,self.id,0x0002|0x0004|0x4000,0x20):
            raise ValueError('VOICE_HOTKEY_CONFLICT')

    def poll(self):
        message=wintypes.MSG()
        while self.user.PeekMessageW(ctypes.byref(message),None,0x0312,0x0312,1):
            if message.wParam==self.id and not self.held:
                self.held=True;self.press()
        if self.held and not self.user.GetAsyncKeyState(0x20)&0x8000:
            self.held=False;self.release()

    def close(self):
        self.user.UnregisterHotKey(None,self.id)
        if self.held:
            self.held=False;self.release()


def transcribe_local(capture, config, connection):
    """Use the existing Content Lab CPU ASR in a worker, with pinned backend."""
    connection.verify()
    import importlib.util
    path=Path(connection.adapter_path).parent/'content_lab.py'
    # This helper is part of the selected trusted backend installation. Do not
    # resolve modules from recorded source content or from a model response.
    if config.get('content_lab_sha256')!=hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('VOICE_BACKEND_CHANGED')
    spec=importlib.util.spec_from_file_location('_occ_voice_content_owner',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=Path(config['capture_root'])/capture['audio_filename']
    if capture['state']!='STOPPED' or capture['gap']:
        raise ValueError('VOICE_CAPTURE_GAP_REVIEW_REQUIRED')
    return module.transcribe_file(source,Path(config['model_dir']),language=config.get('language'),threads=config.get('threads',4))


def critical_metrics(attempts):
    """Human-gold slots are independent from ASR output; include failed trials."""
    denominator=wrong=admissions=0
    latency=[]
    for attempt in attempts:
        for key,value in attempt['gold_slots'].items():
            denominator+=1
            wrong+=attempt.get('observed_slots',{}).get(key)!=value
        admissions+=bool(attempt.get('wrong_effect_admitted'))
        if attempt.get('latency_ms') is not None:
            latency.append(attempt['latency_ms'])
    latency.sort()
    return {'attempts':len(attempts),'critical_slots':denominator,'critical_slot_errors':wrong,
            'critical_slot_error_rate':wrong/denominator if denominator else None,
            'false_effect_admissions':admissions,'latency_p95_ms':latency[max(0,(95*len(latency)+99)//100-1)] if latency else None,
            'device_qualification':'NOT_INFERRED_FROM_TEXT_FIXTURES'}
