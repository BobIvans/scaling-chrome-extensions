/* Production background.js tests with mocked Chrome APIs; not browser API integration. */
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {webcrypto} = require('node:crypto');
const source = fs.readFileSync(path.join(__dirname, '..', 'background.js'), 'utf8');
const id = n => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;

function snapshot(text = 'old', extra = {}) {
  return {schemaVersion: 1, captureId: id(1), revision: 1, text, status: 'BEST_EFFORT', warnings: [],
    capturedAt: '2026-09-08T23:21:23.000Z', sourceTabId: 1, sourceDocumentId: 'doc-1', ...extra};
}
function area(seed = {}) {
  const data = structuredClone(seed);
  return {data, get: async keys => {
    if (typeof keys === 'string') return {[keys]: data[keys]};
    const out = {}; for (const key of keys || Object.keys(data)) out[key] = data[key]; return out;
  }, set: async values => Object.assign(data, structuredClone(values)), remove: async key => {
    for (const item of Array.isArray(key) ? key : [key]) delete data[item];
  }, clear: async () => { for (const key of Object.keys(data)) delete data[key]; }, setAccessLevel: async () => {}};
}
function harness({capture, injectionError, clipboardError, beforeOffscreen, beforeInjection, beforeLocalSet, session, local, downloadError, localSetError} = {}) {
  const writes = [], opened = [], downloadCalls = [], notifications = [], handlers = {};
  const sessionArea = area(session || {capture: snapshot()}); const localArea = area(local);
  if (localSetError) localArea.set = async () => { throw new Error(localSetError); };
  if(beforeLocalSet){const original=localArea.set;localArea.set=async values=>{await beforeLocalSet();return original(values);};}
  let injections = 0, uuid = 10;
  const chrome = {
    action: {onClicked: {addListener: fn => handlers.action = fn}, setBadgeText: async () => {}, setTitle: async () => {}},
    runtime: {id: 'test-id', getURL: x => `chrome-extension://test-id/${x}`, getContexts: async () => [],
      onInstalled: {addListener: fn => handlers.installed = fn}, onMessage: {addListener: fn => handlers.message = fn},
      sendMessage: async msg => { if (msg.target === 'offscreen') { if (clipboardError) return {ok:false,error:'blocked'}; writes.push(msg.text); return {ok:true}; }}},
    offscreen: {createDocument: async () => { await beforeOffscreen?.(); }},
    storage: {session: sessionArea, local: localArea},
    tabs: {create: async data => { opened.push(data); }},
    contextMenus: {removeAll: cb => cb(), create: () => {}, onClicked: {addListener: fn => handlers.menu = fn}},
    downloads: {download: async spec => { if (downloadError) throw new Error(downloadError); downloadCalls.push(spec); return downloadCalls.length; },
      onChanged: {addListener: fn => handlers.downloadChanged = fn}},
    scripting: {executeScript: async spec => {
      injections++; if (spec.files) await beforeInjection?.(); if (injectionError) throw new Error(injectionError);
      if (spec.func?.toString().includes('__occCapture')) return [{result: capture}];
      if (spec.args?.[0]?.kind) notifications.push(spec.args[0]); return [];
    }}
  };
  const crypto = {subtle: webcrypto.subtle, randomUUID: () => id(uuid++)};
  const context = vm.createContext({chrome, TextEncoder, console, crypto, btoa: s => Buffer.from(s, 'binary').toString('base64'), setTimeout});
  vm.runInContext(source, context);
  function run(url = 'https://example.org/chat', tabId = 1) { return vm.runInContext(`run({id:${tabId},url:${JSON.stringify(url)}})`, context); }
  function message(msg, sender = {id:'test-id', url:'chrome-extension://test-id/viewer.html'}) {
    return new Promise(resolve => { const keep = handlers.message(msg, sender, resolve); if (!keep) resolve({ignored:true}); });
  }
  return {writes, opened, downloadCalls, notifications, handlers, session:sessionArea.data, local:localArea.data, run, message,
    get injections() { return injections; }};
}
function decodeDownload(spec) { return Buffer.from(spec.url.split(',')[1], 'base64'); }

test('simultaneous captures reserve one operation before asynchronous revision allocation',async()=>{
 const h=harness({capture:{text:'one',status:'BEST_EFFORT',warnings:[]}});
 await Promise.all([h.run('https://example.org/a',1),h.run('https://example.org/b',2)]);
 assert.equal(h.writes.length,1);assert.equal(h.session.capture.sourceTabId,1);
});
test('clear queued during a delayed persist removes the completed write',async()=>{
 let release,entered;const started=new Promise(r=>entered=r);const gate=new Promise(r=>release=r);
 const h=harness({beforeLocalSet:async()=>{entered();await gate;}});
 const pending=h.message({target:'worker',type:'persist',captureId:id(1),revision:1,clearEpoch:0});await started;
 const clear=h.message({target:'worker',type:'clear'});release();await pending;await clear;
 assert.equal(h.local.savedCapture,undefined);assert.equal(h.session.capture,undefined);
});
test('notification routes require an explicit snapshot identity',async()=>{
 const h=harness();for(const type of ['downloadCapture','openCapture'])assert.equal((await h.message({target:'worker',type,userGesture:true},{id:'test-id',tab:{id:1},documentId:'doc-1',url:'https://example.org'})).ignored,true);
 assert.equal(h.downloadCalls.length,0);
});

test('library route exposes only accepted capture to the exact trusted library page', async () => {
 const h=harness(); const req={target:'library',type:'getCapture'};
 assert.equal((await h.message(req,{id:'test-id',url:'chrome-extension://test-id/library.html'})).capture.text,'old');
 for(const sender of [{id:'other',url:'chrome-extension://test-id/library.html'},{id:'test-id',url:'https://example.org'},{id:'test-id',url:'chrome-extension://test-id/library.html',tab:{id:1}}]) assert.equal((await h.message(req,sender)).ignored,true);
 assert.equal((await h.message({target:'library',type:'clear'},{id:'test-id',url:'chrome-extension://test-id/library.html'})).ignored,true);
 assert.equal(h.session.capture.text,'old');assert.equal(h.writes.length,0);
});

test('successful capture retains exact UTF-8 and writes clipboard once', async () => {
  const text = 'Кириллица 😀\n  code\\path\r\n_under_\n+plus\n-minus'; const h = harness({capture:{text,status:'BEST_EFFORT',warnings:[],count:1}});
  await h.run(); assert.deepEqual(h.writes, [text]); assert.equal(h.session.capture.text, text);
});
test('failed new capture preserves previous accepted snapshot', async () => {
  const old = snapshot('precious'); const h = harness({session:{capture:old}, injectionError:'denied'}); await h.run();
  assert.equal(h.session.capture.text, 'precious'); assert.equal(h.session.jobStatus, 'ERROR');
});
test('cancelled new capture preserves previous accepted snapshot and does not copy', async () => {
  let release, entered; const ready = new Promise(r => entered=r), gate = new Promise(r => release=r);
  const h = harness({capture:{text:'new',status:'RAW_TEXT',warnings:[]},beforeInjection:async()=>{entered();await gate}});
  const task=h.run(); await ready; await h.run(); release(); await task;
  assert.equal(h.session.capture.text,'old'); assert.equal(h.writes.length,0); assert.equal(h.session.jobStatus,'CANCELLED');
});
test('clipboard rejection does not discard capture or prevent download', async () => {
  const h=harness({capture:{text:'download me',status:'PARTIAL',warnings:['Time bound reached.']},clipboardError:true}); await h.run();
  const c=h.session.capture; const r=await h.message({target:'worker',type:'downloadStored',captureId:c.captureId,revision:c.revision});
  assert.equal(r.ok,true); assert.deepEqual(decodeDownload(h.downloadCalls[0]),Buffer.from('download me')); assert.match(h.session.lastError,/blocked/);
});
test('181,807-byte PARTIAL snapshot downloads without loss', async () => {
  const text='я'.repeat(90903)+'a'; assert.equal(Buffer.byteLength(text),181807);
  const c=snapshot(text,{status:'PARTIAL',warnings:['Time/step bound reached.']}); const h=harness({session:{capture:c}});
  const r=await h.message({target:'worker',type:'downloadStored',captureId:c.captureId,revision:c.revision});
  assert.equal(r.ok,true); assert.deepEqual(decodeDownload(h.downloadCalls[0]),Buffer.from(text));
});
test('safe filename has status, no URL data, and uniquifies collisions', async () => {
  const c=snapshot('x',{status:'PARTIAL',source:'https://host/secret?q=token'}), h=harness({session:{capture:c}});
  await h.message({target:'worker',type:'downloadStored',captureId:c.captureId,revision:c.revision});
  assert.equal(h.downloadCalls[0].filename,'context_2026-09-08_23-21-23_PARTIAL.txt');
  assert.equal(h.downloadCalls[0].conflictAction,'uniquify'); assert(!h.downloadCalls[0].filename.includes('secret'));
});
test('oversized and empty capture are rejected and previous capture remains', async () => {
  for (const text of ['', 'a'.repeat(2200001)]) { const h=harness({capture:{text,status:'RAW_TEXT',warnings:[]}}); await h.run(); assert.equal(h.session.capture.text,'old'); assert.equal(h.writes.length,0); }
});
test('stale notification cannot substitute newer snapshot', async () => {
  const newer=snapshot('new',{captureId:id(2),revision:2}); const h=harness({session:{capture:newer}});
  const r=await h.message({target:'worker',type:'downloadCapture',captureId:id(1),revision:1,userGesture:true},
    {id:'test-id',url:'https://example.org',tab:{id:1},documentId:'doc-1'});
  assert.equal(r.ok,false); assert.equal(h.downloadCalls.length,0); assert.match(r.error,/больше недоступен/);
});
test('content download verifies tab, document, gesture and capture id', async () => {
  const c=snapshot('owned'), h=harness({session:{capture:c}}), base={id:'test-id',url:'https://example.org',tab:{id:1},documentId:'doc-1'};
  assert.equal((await h.message({target:'worker',type:'downloadCapture',captureId:c.captureId,revision:1,userGesture:true},base)).ok,true);
  for (const sender of [{...base,tab:{id:2}},{...base,documentId:'other'}]) assert.equal((await h.message({target:'worker',type:'downloadCapture',captureId:c.captureId,revision:1,userGesture:true},sender)).ok,false);
  assert.equal((await h.message({target:'worker',type:'downloadCapture',captureId:c.captureId,revision:1,userGesture:false},base)).ignored,true);
});
test('menu download works without source tab and reads no clipboard', async () => {
  const h=harness({session:{capture:snapshot('menu')}}); h.handlers.menu({menuItemId:'download'}, undefined); await new Promise(r=>setTimeout(r,5));
  assert.equal(h.downloadCalls.length,1); assert.equal(h.writes.length,0); assert.deepEqual(decodeDownload(h.downloadCalls[0]),Buffer.from('menu'));
});
test('one request creates exactly one download and reports interruption', async () => {
  const c=snapshot('once'),h=harness({session:{capture:c}}); await h.message({target:'worker',type:'downloadStored',captureId:c.captureId,revision:1});
  assert.equal(h.downloadCalls.length,1); h.handlers.downloadChanged({id:1,state:{current:'interrupted'},error:{current:'USER_CANCELED'}}); assert.equal(h.downloadCalls.length,1);
});
test('explicit consent route persists; ordinary capture never writes local', async () => {
  const h1=harness({capture:{text:'new',status:'RAW_TEXT',warnings:[]}}); await h1.run(); assert.equal(h1.local.savedCapture,undefined);
  const c=h1.session.capture; const r=await h1.message({target:'worker',type:'persist',captureId:c.captureId,revision:c.revision,clearEpoch:0});
  assert.equal(r.ok,true); assert.equal(h1.local.savedCapture.text,'new');
});
test('local saved snapshot survives worker recreation', async () => {
  const c=snapshot('restart'); const h=harness({session:{},local:{savedCapture:c}});
  const state=await h.message({target:'worker',type:'getState'}); assert.equal(state.session,null); assert.equal(state.saved.text,'restart');
});
test('invalid restored schema, status, or size is ignored', async () => {
  for (const bad of [{...snapshot(),schemaVersion:2},{...snapshot(),status:'CANCELLED'},{...snapshot(),text:'x'.repeat(2200001)}]) {
    const h=harness({session:{capture:bad}}), state=await h.message({target:'worker',type:'getState'}); assert.equal(state.session,null);
  }
});
test('quota failure preserves former saved copy', async () => {
  const prior=snapshot('prior',{captureId:id(3)}), current=snapshot('current');
  const h=harness({session:{capture:current},local:{savedCapture:prior},localSetError:'QUOTA_BYTES'});
  const result=await h.message({target:'worker',type:'persist',captureId:current.captureId,revision:1,clearEpoch:0});
  assert.equal(result.ok,false); assert.match(result.error,/QUOTA_BYTES/); assert.equal(h.local.savedCapture.text,'prior');
});
test('clear removes session/local and stale viewer cannot persist', async () => {
  const c=snapshot('secret'),h=harness({session:{capture:c},local:{savedCapture:c}}); const cleared=await h.message({target:'worker',type:'clear'}); assert.equal(cleared.ok,true);
  assert.equal(h.session.capture,undefined); assert.equal(h.local.savedCapture,undefined);
  const stale=await h.message({target:'worker',type:'persist',captureId:c.captureId,revision:1,clearEpoch:0}); assert.equal(stale.ok,false); assert.equal(h.local.savedCapture,undefined);
});
test('late capture after clear cannot resurrect data', async () => {
  let release,entered; const ready=new Promise(r=>entered=r), gate=new Promise(r=>release=r);
  const h=harness({capture:{text:'late',status:'RAW_TEXT',warnings:[]},beforeInjection:async()=>{entered();await gate}}); const task=h.run(); await ready;
  await h.message({target:'worker',type:'clear'}); release(); await task; assert.equal(h.session.capture,undefined);
});
test('untrusted sender cannot use privileged viewer routes', async () => {
  const h=harness(); const r=await h.message({target:'worker',type:'clear'},{id:'test-id',url:'https://evil.example',tab:{id:1}});
  assert.equal(r.ignored,true); assert(h.session.capture);
});
test('manifest is MV3 with narrow scope and explicitly optional native messaging', () => {
  const m=JSON.parse(fs.readFileSync(path.join(__dirname,'..','manifest.json'),'utf8'));
  assert.equal(m.manifest_version,3); assert.equal(m.version,'0.5.1'); assert.equal(m.action.default_popup,undefined); assert.equal(m.host_permissions,undefined);
  for(const p of ['cookies','history','clipboardRead','debugger','all_urls']) assert(!m.permissions.includes(p)); assert(m.permissions.includes('activeTab')); assert(m.permissions.includes('downloads'));
  assert.deepEqual(m.optional_permissions,['nativeMessaging']);assert.equal(m.optional_host_permissions,undefined);assert(!m.permissions.includes('nativeMessaging'));
});
test('export implementation has no capture, clipboard, DOM, scroll, or network side effect', () => {
  const fn=source.slice(source.indexOf('async function downloadCapture'),source.indexOf('\n}\n\nasync function run'));
  for(const forbidden of ['__occCapture','copyText(','clipboard','executeScript','fetch(','XMLHttpRequest','scroll']) assert(!fn.includes(forbidden),forbidden);
  assert(fn.includes('capture.text'));
});
