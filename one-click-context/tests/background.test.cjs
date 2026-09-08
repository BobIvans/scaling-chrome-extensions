/* Orchestration unit tests with mocked Chrome APIs; NOT real extension integration. */
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '..', 'background.js'), 'utf8');
function harness({capture, injectionError, clipboardError, beforeOffscreen, beforeInjection} = {}) {
  const writes=[], opened=[], stored={capture:{text:'stale result'}}, handlers={};
  let injections=0;
  const chrome={
    action:{onClicked:{addListener:fn=>handlers.action=fn},setBadgeText:async()=>{},setTitle:async()=>{}},
    runtime:{id:'test-id',getURL:x=>'chrome-extension://test-id/'+x,getContexts:async()=>[],
      onInstalled:{addListener:()=>{}},onMessage:{addListener:fn=>handlers.message=fn},
      sendMessage:async msg=>{if(msg.target==='offscreen'){if(clipboardError)return {ok:false,error:'blocked'};writes.push(msg.text);return {ok:true}}}},
    offscreen:{createDocument:async()=>{await beforeOffscreen?.()}},
    storage:{session:{remove:async key=>{delete stored[key]},set:async data=>Object.assign(stored,data),clear:async()=>{for(const k of Object.keys(stored))delete stored[k]}}},
    tabs:{create:async data=>{opened.push(data)}},
    contextMenus:{removeAll:cb=>cb(),create:()=>{},onClicked:{addListener:()=>{}}},
    scripting:{executeScript:async spec=>{injections++;if(spec.files)await beforeInjection?.();if(injectionError)throw new Error(injectionError);if(spec.func?.toString().includes('__occCapture'))return [{result:capture}];return []}}
  };
  const context=vm.createContext({chrome,TextEncoder,console});vm.runInContext(source,context);
  return {writes,opened,stored,handlers,get injections(){return injections},run:url=>vm.runInContext(`run({id:1,url:${JSON.stringify(url||'https://example.org/chat')}})`,context)};
}
test('cancelled capture does not write clipboard',async()=>{const h=harness({capture:{text:'partial',status:'CANCELLED',count:1}});await h.run();assert.equal(h.writes.length,0);assert.equal(h.stored.jobStatus,'CANCELLED');assert.equal(h.stored.capture.text,'partial')});
test('successful capture dispatches exactly one clipboard write',async()=>{const h=harness({capture:{text:'literal\\_text\n+  x',status:'BEST_EFFORT',count:1}});await h.run();assert.deepEqual(h.writes,['literal\\_text\n+  x']);assert.equal(h.opened.length,0)});
test('injection error clears stale capture without copying',async()=>{const h=harness({injectionError:'denied'});await h.run();assert.equal(h.writes.length,0);assert.equal(h.stored.capture,undefined);assert.equal(h.stored.jobStatus,'ERROR');assert.equal(h.opened.length,1)});
test('protected Chrome page is rejected before injection',async()=>{const h=harness();await h.run('chrome://settings');assert.equal(h.injections,0);assert.equal(h.writes.length,0);assert.equal(h.stored.jobStatus,'ERROR')});
test('oversized capture is not copied or labelled successful',async()=>{const h=harness({capture:{text:'a'.repeat(2200001),status:'RAW_TEXT'}});await h.run();assert.equal(h.writes.length,0);assert.equal(h.stored.jobStatus,'ERROR')});
test('clipboard failure opens preview and retains captured text',async()=>{const h=harness({capture:{text:'new text',status:'BEST_EFFORT'},clipboardError:true});await h.run();assert.equal(h.writes.length,0);assert.equal(h.opened.length,1);assert.equal(h.stored.capture.text,'new text');assert.match(h.stored.lastError,/Clipboard was blocked/)});
test('untrusted sender cannot invoke privileged copy route',()=>{const h=harness();let replied=false;const r=h.handlers.message({target:'worker',type:'copy',text:'bad'},{id:'test-id',url:'https://example.org/',tab:{id:1}},()=>replied=true);assert.equal(r,false);assert.equal(replied,false);assert.equal(h.writes.length,0)});
test('manifest has minimal declared scope and no persistent hosts',()=>{const m=JSON.parse(fs.readFileSync(path.join(__dirname,'..','manifest.json'),'utf8'));assert.equal(m.manifest_version,3);assert.equal(m.action.default_popup,undefined);assert.equal(m.host_permissions,undefined);for(const p of ['cookies','history','clipboardRead','debugger'])assert(!m.permissions.includes(p));assert(m.permissions.includes('activeTab'))});


test('ERROR result is rejected without copying',async()=>{const h=harness({capture:{text:'bad',status:'ERROR'}});await h.run();assert.equal(h.writes.length,0);assert.equal(h.stored.capture,undefined);assert.equal(h.stored.jobStatus,'ERROR')});
test('second click during injection cancels before scanning',async()=>{let release,entered;const ready=new Promise(r=>entered=r),gate=new Promise(r=>release=r);const h=harness({capture:{text:'new',status:'RAW_TEXT'},beforeInjection:async()=>{entered();await gate}});const task=h.run();await ready;await h.run();release();await task;assert.equal(h.writes.length,0);assert.equal(h.stored.jobStatus,'CANCELLED')});
test('second click during offscreen setup prevents clipboard dispatch',async()=>{let release,entered;const ready=new Promise(r=>entered=r),gate=new Promise(r=>release=r);const h=harness({capture:{text:'new',status:'RAW_TEXT'},beforeOffscreen:async()=>{entered();await gate}});const task=h.run();await ready;await h.run();release();await task;assert.equal(h.writes.length,0);assert.equal(h.stored.jobStatus,'CANCELLED')});
