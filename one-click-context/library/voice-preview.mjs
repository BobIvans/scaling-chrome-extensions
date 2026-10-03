const AUDIO_TYPES=['audio/webm;codecs=opus','audio/webm'];
export const MAX_RECORDING_MS=60000;
export const MAX_AUDIO_BYTES=16*1024*1024;
export const MAX_TRANSCRIPT_BYTES=16000;

const utf8=value=>new TextEncoder().encode(value).length;
const error=(code,cause)=>Object.assign(new Error(code),{code,cause});

export function boundedTranscript(value){
 if(typeof value!=='string'||value.includes('\0'))throw error('TRANSCRIPT_INVALID');
 const bytes=utf8(value);if(bytes>MAX_TRANSCRIPT_BYTES)throw error('TRANSCRIPT_LIMIT');
 return {text:value,bytes,state:value.trim()?'EDITED_UNVERIFIED':'EMPTY'};
}

export function transcriptGoal(value){
 const transcript=boundedTranscript(value);
 if(transcript.state==='EMPTY')throw error('TRANSCRIPT_EMPTY');
 if(transcript.bytes>8000)throw error('REPO_GOAL_LIMIT');
 // Preserve negations/numbers verbatim. This is an editable goal, never dispatch.
 return {text:transcript.text,authority:'DATA_ONLY',dispatch_allowed:false};
}

export class VoiceRecorder{
 constructor({mediaDevices,MediaRecorderCtor,onState=()=>{},setTimer=setTimeout,clearTimer=clearTimeout,now=()=>new Date().toISOString(),maxMs=MAX_RECORDING_MS,maxBytes=MAX_AUDIO_BYTES}={}){
  this.mediaDevices=mediaDevices;this.MediaRecorderCtor=MediaRecorderCtor;this.onState=onState;
  this.setTimer=setTimer;this.clearTimer=clearTimer;this.now=now;this.maxMs=maxMs;this.maxBytes=maxBytes;
  this.state='IDLE';this.reason=null;this.recorder=null;this.stream=null;this.timer=null;
  this.holding=false;this.epoch=0;this.chunks=[];this.bytes=0;this.recording=null;this.receipt=null;
 }
 capability(){
  if(!this.mediaDevices||typeof this.mediaDevices.getUserMedia!=='function')return 'UNSUPPORTED_MEDIA_DEVICES';
  if(typeof this.MediaRecorderCtor!=='function')return 'UNSUPPORTED_MEDIA_RECORDER';
  if(typeof this.MediaRecorderCtor.isTypeSupported!=='function'||!AUDIO_TYPES.some(t=>this.MediaRecorderCtor.isTypeSupported(t)))return 'UNSUPPORTED_AUDIO_FORMAT';
  return 'READY';
 }
 snapshot(){return {state:this.state,reason:this.reason,holding:this.holding,recording:this.recording,receipt:this.receipt};}
 emit(state,reason=null){this.state=state;this.reason=reason;this.onState(this.snapshot());}
 stopTracks(){for(const track of this.stream?.getTracks?.()||[])try{track.stop();}catch{}this.stream=null;}
 async press(){
  if(this.holding||['REQUESTING','RECORDING','STOPPING'].includes(this.state))throw error('VOICE_BUSY');
  const capability=this.capability();if(capability!=='READY'){this.emit(capability);throw error(capability);}
  this.clear();this.holding=true;const epoch=++this.epoch;this.emit('REQUESTING');
  let stream;
  try{stream=await this.mediaDevices.getUserMedia({audio:true,video:false});}
  catch(cause){if(epoch!==this.epoch)return;this.holding=false;this.emit(cause?.name==='NotAllowedError'?'PERMISSION_DENIED':'MICROPHONE_ERROR');throw error(this.state,cause);}
  if(epoch!==this.epoch||!this.holding){for(const track of stream?.getTracks?.()||[])try{track.stop();}catch{}if(epoch===this.epoch)this.emit('IDLE','RELEASED_BEFORE_START');return;}
  this.stream=stream;
  if(!(stream.getAudioTracks?.().length>0)){this.holding=false;this.stopTracks();this.emit('NO_AUDIO_TRACK');throw error('NO_AUDIO_TRACK');}
  const mimeType=AUDIO_TYPES.find(t=>this.MediaRecorderCtor.isTypeSupported(t));
  try{this.recorder=new this.MediaRecorderCtor(stream,{mimeType});}
  catch(cause){this.holding=false;this.stopTracks();this.emit('RECORDER_ERROR');throw error('RECORDER_ERROR',cause);}
  this.chunks=[];this.bytes=0;this.recording=null;
  this.recorder.ondataavailable=event=>{
   if(epoch!==this.epoch||!event.data?.size)return;
   this.bytes+=event.data.size;if(this.bytes>this.maxBytes){this.reason='AUDIO_LIMIT';this.holding=false;if(this.recorder?.state==='recording')this.recorder.stop();return;}
   this.chunks.push(event.data);
  };
  this.recorder.onerror=()=>{if(epoch===this.epoch){this.reason='RECORDER_ERROR';this.holding=false;if(this.recorder?.state==='recording')this.recorder.stop();}};
  this.recorder.onstop=()=>this.finish(epoch,mimeType);
  try{this.recorder.start(1000);}catch(cause){this.holding=false;this.recorder=null;this.stopTracks();this.emit('RECORDER_ERROR');throw error('RECORDER_ERROR',cause);}
  this.emit('RECORDING');
  this.timer=this.setTimer(()=>this.release('MAX_DURATION'),this.maxMs);
 }
 release(reason='USER_RELEASE'){
  this.holding=false;
  if(this.state==='REQUESTING'){this.reason=reason;return;}
  if(this.state!=='RECORDING'||!this.recorder)return;
  this.clearTimer(this.timer);this.timer=null;this.reason=reason;this.emit('STOPPING',reason);
  if(this.recorder.state==='recording')this.recorder.stop();else this.finish(this.epoch,this.recorder.mimeType);
 }
 finish(epoch,mimeType){
  if(epoch!==this.epoch)return;
  this.clearTimer(this.timer);this.timer=null;this.stopTracks();const reason=this.reason||'USER_RELEASE';
  if(reason==='AUDIO_LIMIT'||reason==='RECORDER_ERROR'){this.chunks=[];this.bytes=0;this.recording=null;this.recorder=null;this.emit(reason);return;}
  const blob=new Blob(this.chunks,{type:mimeType});this.recording={blob,bytes:blob.size,mimeType,stopReason:reason};
  this.chunks=[];this.bytes=0;this.recorder=null;this.emit(blob.size?'RECORDED':'EMPTY_RECORDING',reason);
 }
 cancel(trigger='UI'){
  if(!['UI','KEYBOARD'].includes(trigger))throw error('CANCEL_TRIGGER_INVALID');
  this.epoch++;this.holding=false;this.clearTimer(this.timer);this.timer=null;
  if(this.recorder?.state==='recording')try{this.recorder.stop();}catch{}
  this.stopTracks();this.recorder=null;this.chunks=[];this.bytes=0;this.recording=null;
  this.receipt={schema:'occ.voice-cancel-receipt.v1',scope:'LOCAL_VOICE_PREVIEW',state:'CANCELLED',terminal:true,trigger,at:this.now(),audio_retained:false,transcript_retained:false,action_dispatched:false};
  this.emit('CANCELLED',trigger);return this.receipt;
 }
 clear(){
  this.epoch++;this.holding=false;this.clearTimer(this.timer);this.timer=null;
  if(this.recorder?.state==='recording')try{this.recorder.stop();}catch{}
  this.stopTracks();this.recorder=null;this.chunks=[];this.bytes=0;this.recording=null;this.receipt=null;this.emit('IDLE');
 }
}

const messages={
 IDLE:'Готово. Удерживайте кнопку для одной локальной записи.',
 REQUESTING:'Ожидание явного разрешения на микрофон…',RECORDING:'Идёт запись только микрофона. Отпустите кнопку для остановки.',
 STOPPING:'Завершение локальной записи…',RECORDED:'Запись готова в памяти вкладки; транскрипт остаётся непроверенным.',
 UNSUPPORTED_MEDIA_DEVICES:'На этом устройстве API микрофона недоступен.',UNSUPPORTED_MEDIA_RECORDER:'На этом устройстве MediaRecorder недоступен.',
 UNSUPPORTED_AUDIO_FORMAT:'Нет поддерживаемого локального WebM/Opus формата.',PERMISSION_DENIED:'Доступ к микрофону не разрешён.',
 MICROPHONE_ERROR:'Микрофон не открылся.',NO_AUDIO_TRACK:'Устройство не вернуло аудиодорожку.',RECORDER_ERROR:'Ошибка локальной записи.',
 AUDIO_LIMIT:'Запись превышает лимит 16 MiB и отброшена.',EMPTY_RECORDING:'Пустая запись отброшена.',
 CANCELLED:'Voice-сессия отменена независимо от распознавания; audio и транскрипт отброшены.'
};

export function attachVoicePreview({document:doc=globalThis.document,window:win=globalThis.window,mediaDevices=globalThis.navigator?.mediaDevices,MediaRecorderCtor=globalThis.MediaRecorder,urlAPI=globalThis.URL}={}){
 const $=id=>doc.getElementById(id),hold=$('voice-hold');if(!hold)return null;
 const status=$('voice-status'),audio=$('voice-audio'),download=$('voice-download'),clear=$('voice-clear'),cancel=$('voice-cancel'),cancelReceipt=$('voice-cancel-receipt'),transcript=$('voice-transcript'),meta=$('voice-transcript-meta');
 let objectURL=null;
 const revoke=()=>{if(objectURL){urlAPI.revokeObjectURL(objectURL);objectURL=null;}audio.removeAttribute?.('src');audio.hidden=true;download.disabled=true;};
 const render=s=>{if(['IDLE','REQUESTING','CANCELLED'].includes(s.state)&&!s.recording)revoke();status.textContent=messages[s.state]||s.state;hold.setAttribute?.('aria-pressed',String(s.state==='RECORDING'));hold.textContent=s.state==='RECORDING'?'Отпустите, чтобы остановить':'Удерживайте для записи';cancelReceipt.textContent=s.receipt?JSON.stringify(s.receipt,null,2):'';cancelReceipt.hidden=!s.receipt;if(s.state==='RECORDED'&&s.recording){revoke();objectURL=urlAPI.createObjectURL(s.recording.blob);audio.src=objectURL;audio.hidden=false;download.disabled=false;status.textContent+=` ${s.recording.bytes} байт; ${s.recording.stopReason}.`;}};
 const recorder=new VoiceRecorder({mediaDevices,MediaRecorderCtor,onState:render});
 const capability=recorder.capability();if(capability!=='READY'){hold.disabled=true;render({state:capability});}else render(recorder.snapshot());
 const press=event=>{if(!event.isTrusted||event.repeat)return;event.preventDefault?.();if(Number.isInteger(event.pointerId))hold.setPointerCapture?.(event.pointerId);void recorder.press().catch(()=>{});};
 const release=event=>{if(!event.isTrusted)return;event.preventDefault?.();recorder.release('USER_RELEASE');};
 hold.onpointerdown=press;hold.onpointerup=release;hold.onpointercancel=release;hold.onlostpointercapture=release;
 hold.onkeydown=event=>{if([' ','Enter'].includes(event.key))press(event);};hold.onkeyup=event=>{if([' ','Enter'].includes(event.key))release(event);};
 transcript.oninput=()=>{try{const value=boundedTranscript(transcript.value);meta.textContent=`${value.state} · ${value.bytes} / ${MAX_TRANSCRIPT_BYTES} байт UTF-8`;transcript.setAttribute?.('aria-invalid','false');}catch(e){meta.textContent=e.code==='TRANSCRIPT_LIMIT'?'Транскрипт превышает 16 000 байт UTF-8.':'Транскрипт содержит неподдерживаемые данные.';transcript.setAttribute?.('aria-invalid','true');}};
 if($('voice-to-repo-goal'))$('voice-to-repo-goal').onclick=event=>{
  if(!event.isTrusted)return;
  try{const goal=transcriptGoal(transcript.value),target=$('repo-goal');if(!target)throw error('REPO_GOAL_UNAVAILABLE');target.value=goal.text;target.oninput?.();status.textContent='Текст перенесён в редактируемую цель review. Проверьте область и критерии; экспорт запускается отдельно.';}
  catch(e){status.textContent=e.code||e.message;}
 };
 download.onclick=event=>{if(!event.isTrusted||!recorder.recording||!objectURL)return;const link=doc.createElement('a');link.href=objectURL;link.download=`occ_voice_${new Date().toISOString().replace(/[:.]/g,'-')}.webm`;link.click();status.textContent='Скачивание локальной записи запрошено; завершение проверьте в Chrome.';};
 clear.onclick=event=>{if(!event.isTrusted)return;recorder.clear();revoke();transcript.value='';transcript.oninput();};
 const cancelSession=trigger=>{const receipt=recorder.cancel(trigger);revoke();transcript.value='';transcript.oninput();return receipt;};
 cancel.onclick=event=>{if(!event.isTrusted)return;event.preventDefault?.();cancelSession('UI');};
 doc.addEventListener?.('keydown',event=>{if(!event.isTrusted||event.repeat||event.key!=='Escape')return;event.preventDefault?.();cancelSession('KEYBOARD');});
 const dispose=()=>{recorder.clear();revoke();};win?.addEventListener?.('pagehide',dispose,{once:true});
 win?.addEventListener?.('blur',()=>recorder.release('FOCUS_LOST'));
 doc.addEventListener?.('visibilitychange',()=>{if(doc.hidden)recorder.release('PAGE_HIDDEN');});
 transcript.oninput();return {recorder,cancel:cancelSession,dispose};
}
