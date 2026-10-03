import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {VoiceRecorder,attachVoicePreview,boundedTranscript,transcriptGoal,MAX_TRANSCRIPT_BYTES} from '../library/voice-preview.mjs';

test('final text uses the shared editable goal and preserves negations and numbers',()=>{
 const value='Не запускай 24 сделки; проверь 3 файла.\nLimit 0 EUR.';
 assert.deepEqual(transcriptGoal(value),{text:value,authority:'DATA_ONLY',dispatch_allowed:false});
 for(const input of ['', '   ', 'x\0y', 'Я'.repeat(4001)])assert.throws(()=>transcriptGoal(input));
});

const track=()=>({stopped:0,stop(){this.stopped++;}});
const stream=(audio=1)=>{const tracks=Array.from({length:audio},track);return {tracks,getTracks:()=>tracks,getAudioTracks:()=>tracks};};

class FakeRecorder{
 static data='voice';
 static isTypeSupported=value=>value==='audio/webm;codecs=opus';
 constructor(source,{mimeType}){this.source=source;this.mimeType=mimeType;this.state='inactive';FakeRecorder.last=this;}
 start(slice){this.state='recording';this.slice=slice;}
 stop(){if(this.state!=='recording')return;this.state='inactive';this.ondataavailable?.({data:new Blob([FakeRecorder.data],{type:this.mimeType})});this.onstop?.();}
}

test('press-to-talk requests microphone-only scope and stops tracks on release',async()=>{
 const source=stream(),calls=[],states=[];
 const recorder=new VoiceRecorder({mediaDevices:{getUserMedia:async options=>{calls.push(options);return source;}},MediaRecorderCtor:FakeRecorder,onState:s=>states.push(s.state)});
 await recorder.press();assert.equal(recorder.state,'RECORDING');assert.deepEqual(calls,[{audio:true,video:false}]);assert.equal(FakeRecorder.last.slice,1000);
 recorder.release();assert.equal(recorder.state,'RECORDED');assert.equal(recorder.recording.bytes,5);assert.equal(recorder.recording.stopReason,'USER_RELEASE');assert.equal(source.tracks[0].stopped,1);
 assert(states.includes('REQUESTING'));assert(states.includes('STOPPING'));assert(states.includes('RECORDED'));
});

test('release during permission prompt never starts a late recording',async()=>{
 let resolve;const pending=new Promise(r=>resolve=r),source=stream();
 const recorder=new VoiceRecorder({mediaDevices:{getUserMedia:()=>pending},MediaRecorderCtor:FakeRecorder});
 const start=recorder.press();recorder.release();resolve(source);await start;
 assert.equal(recorder.state,'IDLE');assert.equal(recorder.recording,null);assert.equal(source.tracks[0].stopped,1);
});

test('independent cancel is terminal, discards audio and invalidates late permission result',async()=>{
 const source=stream(),recorder=new VoiceRecorder({mediaDevices:{getUserMedia:async()=>source},MediaRecorderCtor:FakeRecorder,now:()=> '2026-10-01T15:00:00.000Z'});
 await recorder.press();const receipt=recorder.cancel('UI');
 assert.deepEqual(receipt,{schema:'occ.voice-cancel-receipt.v1',scope:'LOCAL_VOICE_PREVIEW',state:'CANCELLED',terminal:true,trigger:'UI',at:'2026-10-01T15:00:00.000Z',audio_retained:false,transcript_retained:false,action_dispatched:false});
 assert.equal(recorder.state,'CANCELLED');assert.equal(recorder.recording,null);assert.equal(source.tracks[0].stopped,1);
 let resolve;const pending=new Promise(r=>resolve=r),lateStream=stream(),late=new VoiceRecorder({mediaDevices:{getUserMedia:()=>pending},MediaRecorderCtor:FakeRecorder});
 const start=late.press();late.cancel('KEYBOARD');resolve(lateStream);await start;
 assert.equal(late.state,'CANCELLED');assert.equal(late.receipt.trigger,'KEYBOARD');assert.equal(late.recording,null);assert.equal(lateStream.tracks[0].stopped,1);
 assert.throws(()=>late.cancel('ASR'),error=>error.code==='CANCEL_TRIGGER_INVALID');
});

test('timeout, byte budget and permission failures are explicit terminal states',async()=>{
 let timeout;const source=stream();
 const timed=new VoiceRecorder({mediaDevices:{getUserMedia:async()=>source},MediaRecorderCtor:FakeRecorder,setTimer:fn=>(timeout=fn,1),clearTimer:()=>{}});
 await timed.press();timeout();assert.equal(timed.state,'RECORDED');assert.equal(timed.recording.stopReason,'MAX_DURATION');
 FakeRecorder.data='oversize';const limited=new VoiceRecorder({mediaDevices:{getUserMedia:async()=>stream()},MediaRecorderCtor:FakeRecorder,maxBytes:2});
 await limited.press();limited.release();assert.equal(limited.state,'AUDIO_LIMIT');assert.equal(limited.recording,null);FakeRecorder.data='voice';
 const denied=new VoiceRecorder({mediaDevices:{getUserMedia:async()=>{throw Object.assign(Error('denied'),{name:'NotAllowedError'});}},MediaRecorderCtor:FakeRecorder});
 await assert.rejects(denied.press(),error=>error.code==='PERMISSION_DENIED');assert.equal(denied.state,'PERMISSION_DENIED');
 class StartFailure extends FakeRecorder{start(){throw Error('device lost');}}
 const failedStream=stream(),failed=new VoiceRecorder({mediaDevices:{getUserMedia:async()=>failedStream},MediaRecorderCtor:StartFailure});
 await assert.rejects(failed.press(),error=>error.code==='RECORDER_ERROR');assert.equal(failed.state,'RECORDER_ERROR');assert.equal(failedStream.tracks[0].stopped,1);
});

test('unsupported capabilities and editable transcript bounds fail closed',()=>{
 assert.equal(new VoiceRecorder({MediaRecorderCtor:FakeRecorder}).capability(),'UNSUPPORTED_MEDIA_DEVICES');
 assert.equal(new VoiceRecorder({mediaDevices:{getUserMedia(){}}}).capability(),'UNSUPPORTED_MEDIA_RECORDER');
 class UnknownFormat extends FakeRecorder{static isTypeSupported=()=>false;}
 assert.equal(new VoiceRecorder({mediaDevices:{getUserMedia(){}},MediaRecorderCtor:UnknownFormat}).capability(),'UNSUPPORTED_AUDIO_FORMAT');
 assert.deepEqual(boundedTranscript('Привет'),{text:'Привет',bytes:12,state:'EDITED_UNVERIFIED'});
 assert.equal(boundedTranscript('  ').state,'EMPTY');
 assert.throws(()=>boundedTranscript('\0'),error=>error.code==='TRANSCRIPT_INVALID');
 assert.throws(()=>boundedTranscript('x'.repeat(MAX_TRANSCRIPT_BYTES+1)),error=>error.code==='TRANSCRIPT_LIMIT');
});

class Element{
 constructor(){this.textContent='';this.value='';this.disabled=false;this.hidden=false;this.attributes={};}
 setAttribute(key,value){this.attributes[key]=String(value);}removeAttribute(key){delete this.attributes[key];}
 setPointerCapture(){}
}
function dom(){
 const ids=['voice-hold','voice-status','voice-audio','voice-download','voice-clear','voice-cancel','voice-cancel-receipt','voice-transcript','voice-transcript-meta','voice-to-repo-goal','repo-goal'];
 const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));
 const handlers={};return {elements,handlers,document:{getElementById:id=>elements[id],createElement:()=>Object.assign(new Element(),{click(){this.clicked=true;}}),addEventListener:(name,fn)=>handlers[name]=fn}};
}

test('trusted transfer edits the repo goal and invalidates its prior request; STOP clears input',()=>{
 const d=dom();let invalidations=0;d.elements['repo-goal'].oninput=()=>invalidations++;
 attachVoicePreview({document:d.document,window:{addEventListener(){}},mediaDevices:null,MediaRecorderCtor:FakeRecorder,urlAPI:{}});
 d.elements['voice-transcript'].value='Не запускай 24 сделки';
 d.elements['voice-to-repo-goal'].onclick({isTrusted:false});assert.equal(invalidations,0);
 d.elements['voice-to-repo-goal'].onclick({isTrusted:true});assert.equal(invalidations,1);assert.equal(d.elements['repo-goal'].value,'Не запускай 24 сделки');
 d.elements['voice-cancel'].onclick({isTrusted:true});
 d.elements['voice-to-repo-goal'].onclick({isTrusted:true});assert.equal(invalidations,1);assert.match(d.elements['voice-status'].textContent,/TRANSCRIPT_EMPTY/);
});

test('view shows unsupported device and ignores synthetic recording gesture',async()=>{
 const unsupported=dom();attachVoicePreview({document:unsupported.document,window:{addEventListener(){}},mediaDevices:null,MediaRecorderCtor:FakeRecorder,urlAPI:{}});
 assert.equal(unsupported.elements['voice-hold'].disabled,true);assert.match(unsupported.elements['voice-status'].textContent,/недоступен/);
 let calls=0;const handlers={},supported=dom();const view=attachVoicePreview({document:supported.document,window:{addEventListener:(name,fn)=>handlers[name]=fn},mediaDevices:{getUserMedia:async()=>{calls++;return stream();}},MediaRecorderCtor:FakeRecorder,urlAPI:{createObjectURL:()=>'',revokeObjectURL(){}}});
 supported.elements['voice-hold'].onpointerdown({isTrusted:false});await new Promise(resolve=>setImmediate(resolve));assert.equal(calls,0);
 supported.elements['voice-transcript'].value='editable';supported.elements['voice-transcript'].oninput();assert.match(supported.elements['voice-transcript-meta'].textContent,/EDITED_UNVERIFIED/);
 supported.elements['voice-hold'].onpointerdown({isTrusted:true,pointerId:1,preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));assert.equal(view.recorder.state,'RECORDING');handlers.blur();assert.equal(view.recorder.recording.stopReason,'FOCUS_LOST');view.dispose();
});

test('trusted STOP button and Escape cancel without ASR and show terminal receipt',async()=>{
 const button=dom(),windowHandlers={},source=stream();
 const view=attachVoicePreview({document:button.document,window:{addEventListener:(name,fn)=>windowHandlers[name]=fn},mediaDevices:{getUserMedia:async()=>source},MediaRecorderCtor:FakeRecorder,urlAPI:{createObjectURL:()=>'',revokeObjectURL(){}}});
 button.elements['voice-transcript'].value='untrusted draft';button.elements['voice-cancel'].onclick({isTrusted:false});assert.equal(view.recorder.state,'IDLE');
 button.elements['voice-hold'].onpointerdown({isTrusted:true,pointerId:1,preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));
 let prevented=false;button.handlers.keydown({isTrusted:true,repeat:false,key:'Escape',preventDefault(){prevented=true;}});
 assert.equal(prevented,true);assert.equal(view.recorder.state,'CANCELLED');assert.equal(view.recorder.receipt.trigger,'KEYBOARD');assert.equal(button.elements['voice-transcript'].value,'');
 assert.equal(button.elements['voice-cancel-receipt'].hidden,false);assert.match(button.elements['voice-cancel-receipt'].textContent,/"terminal": true/);assert.match(button.elements['voice-status'].textContent,/независимо/);
 button.elements['voice-cancel'].onclick({isTrusted:true,preventDefault(){}});assert.equal(view.recorder.receipt.trigger,'UI');view.dispose();
});

test('production voice module has no network, speech provider or action dispatch',()=>{
 const source=fs.readFileSync(fileURLToPath(new URL('../library/voice-preview.mjs',import.meta.url)),'utf8');
 for(const forbidden of ['fetch(','XMLHttpRequest','WebSocket','RTCPeerConnection','SpeechRecognition','chrome.runtime','durable.enqueue'])assert.equal(source.includes(forbidden),false,forbidden);
});
