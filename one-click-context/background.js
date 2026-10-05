/* One Click Context privileged orchestration. Captures stay temporary unless the user opts in. */
const MAX_BYTES = 2200000;
const SNAPSHOT_VERSION = 1;
const SESSION_CAPTURE = 'capture';
const LOCAL_CAPTURE = 'savedCapture';
let active = null;
let creatingOffscreen = null;
let copyQueue = Promise.resolve();
let storageQueue = Promise.resolve();
function mutateStorage(fn) { const pending=storageQueue.catch(()=>{}).then(fn); storageQueue=pending; return pending; }
const downloads = new Map();
const viewerURL = () => chrome.runtime.getURL('viewer.html');
const AGENTOS_NATIVE_HOST = 'com.one_click_context.codex';
let agentosNativePort = null;
let agentosNativeSeq = 0;
let agentosNativeConnectPromise = null;
const agentosNativePending = new Map();
const agentosArchiveStreams = new Map();
const utf8 = text => new TextEncoder().encode(text);

function validStatus(value) {
  return ['SELECTION', 'RAW_TEXT', 'BEST_EFFORT', 'PARTIAL'].includes(value);
}
function validArtifacts(value) {
  const kinds = new Set(['file-link', 'file-control', 'copy-control', 'feed-link', 'structured-data', 'embedded-document', 'collapsed-content', 'long-text-control', 'canvas', 'image', 'audio', 'video', 'editor']);
  const states = new Set(['AVAILABLE', 'NOT_READ', 'TEXT_NOT_READ', 'VISIBLE_PART_ONLY', 'CONTROL_NOT_USED', 'METADATA_ONLY']);
  const methods = new Set(['USER_DOWNLOAD_IMPORT', 'FRAME_ACCESS_OR_EXPORT', 'USER_EXPAND_THEN_RECAPTURE',
    'SCREENSHOT_OR_OCR', 'TRANSCRIPT_OR_USER_EXPORT', 'OBSERVE_VISIBLE_DOM_OR_EXPORT_ORIGINAL', 'USER_OPEN_OR_DOWNLOAD',
    'OBSERVE_DOM_FIRST', 'CONNECT_READ_ONLY_FEED', 'READ_STRUCTURED_METADATA']);
  const decisions = new Set(['OBSERVE_ONLY', 'IMPORT_FEED', 'INCLUDE_STRUCTURED_RECORD', 'IMPORT_ORIGINAL', 'OPEN_OR_DOWNLOAD_ORIGINAL',
    'USE_OBSERVED_TEXT', 'OPEN_OR_EXPORT_SEPARATELY', 'EXPAND_AND_RECAPTURE', 'CAPTURE_VISIBLE_SCREEN', 'EXPORT_TRANSCRIPT_OR_MEDIA', 'EXPORT_ORIGINAL_TEXT']);
  return [1, 2].includes(value?.schemaVersion) && typeof value.limited === 'boolean' && Array.isArray(value.items) &&
    value.items.length <= 100 && value.items.every((item, index) => item && item.id === `artifact-${index + 1}` &&
      kinds.has(item.kind) && states.has(item.state) && methods.has(item.method) &&
      typeof item.label === 'string' && item.label.length <= 160 && typeof item.source === 'string' && item.source.length <= 160 &&
      (value.schemaVersion === 1 || (decisions.has(item.decision) && typeof item.reason === 'string' && item.reason.length <= 160 && typeof item.requiresUser === 'boolean')));
}
function validSnapshot(value) {
  if (!value || value.schemaVersion !== SNAPSHOT_VERSION || typeof value.captureId !== 'string' ||
      !Number.isSafeInteger(value.revision) || value.revision < 1 || typeof value.text !== 'string' ||
      !value.text || !validStatus(value.status) || !Array.isArray(value.warnings) ||
      value.warnings.some(item => typeof item !== 'string') || typeof value.capturedAt !== 'string' ||
      (value.artifacts !== undefined && !validArtifacts(value.artifacts))) return false;
  try {
    // The bound applies to the complete versioned record, not merely its text field.
    return utf8(value.text).byteLength <= MAX_BYTES && utf8(JSON.stringify(value)).byteLength <= MAX_BYTES &&
      !Number.isNaN(Date.parse(value.capturedAt));
  }
  catch { return false; }
}
function safeFilename(capture, edited = false) {
  const date = new Date(capture?.capturedAt || Date.now());
  const stamp = Number.isNaN(date.valueOf()) ? new Date().toISOString() : date.toISOString();
  const cleanStamp = stamp.slice(0, 19).replace('T', '_').replaceAll(':', '-');
  const status = validStatus(capture?.status) ? capture.status : 'TEXT';
  return `context_${cleanStamp}_${status}${edited ? '_EDITED' : ''}.txt`
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, '_').slice(0, 180);
}
function bytesToBase64(bytes) {
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}
async function getCapture(captureId, revision) {
  const session = (await chrome.storage.session.get(SESSION_CAPTURE))[SESSION_CAPTURE];
  if (validSnapshot(session) && (!captureId || (session.captureId === captureId && session.revision === revision))) return {capture: session, location: 'session'};
  const saved = (await chrome.storage.local.get(LOCAL_CAPTURE))[LOCAL_CAPTURE];
  if (validSnapshot(saved) && (!captureId || (saved.captureId === captureId && saved.revision === revision))) return {capture: saved, location: 'local'};
  return null;
}
function validRecent(value){return Array.isArray(value)&&value.length<=50&&value.every(validSnapshot)&&new Set(value.map(c=>c.captureId)).size===value.length&&utf8(JSON.stringify(value)).length<=MAX_BYTES;}
async function getRecent(){const {recentCaptures}=await chrome.storage.session.get('recentCaptures');if(recentCaptures===undefined)return [];if(!validRecent(recentCaptures))throw new Error('Память сессии повреждена или превышает лимит.');return recentCaptures;}
async function downloadRecent() {
  const captures = await getRecent();
  if (!captures.length) throw new Error('В текущей сессии ещё нет собранных страниц.');
  // This is an explicitly labelled collection, not the byte-exact single-snapshot export.
  const text = captures.map((c, i) =>
    `===== ${i + 1} · ${c.capturedAt} · ${c.source || 'Источник не указан'} =====\nSTATUS: ${c.status}\n${limitation(c)}\n${c.warnings.join('\n')}\n${c.text}`
  ).join('\n\n');
  return downloadCapture({schemaVersion: 1, captureId: crypto.randomUUID(), revision: 1,
    capturedAt: new Date().toISOString(),
    status: captures.some(c => c.status === 'PARTIAL') ? 'PARTIAL' : 'BEST_EFFORT',
    warnings: ['Агрегат снимков; полнота исходных страниц не гарантируется.'], text});
}
function safeScreenshotFilename(capture) {
  return safeFilename(capture).replace(/\.txt$/, '_VISIBLE.png');
}

async function offscreen() {
  const url = chrome.runtime.getURL('offscreen.html');
  const contexts = await chrome.runtime.getContexts({contextTypes: ['OFFSCREEN_DOCUMENT'], documentUrls: [url]});
  if (contexts.length) return;
  if (!creatingOffscreen) creatingOffscreen = chrome.offscreen.createDocument({url: 'offscreen.html', reasons: ['CLIPBOARD'],
    justification: 'Copy text the user explicitly captured to the system clipboard.'}).finally(() => { creatingOffscreen = null; });
  await creatingOffscreen;
}
function copyText(text, job = null) {
  if (typeof text !== 'string' || utf8(text).byteLength > MAX_BYTES) return Promise.reject(new Error('Invalid or oversized clipboard payload.'));
  const pending = copyQueue.catch(() => {}).then(async () => {
    await offscreen();
    if (job?.cancelled) throw new Error('Capture cancelled before clipboard dispatch.');
    if (job) job.committing = true;
    const result = await chrome.runtime.sendMessage({target: 'offscreen', type: 'copy', text});
    if (!result?.ok) throw new Error(result?.error || 'Clipboard write did not succeed.');
    return result;
  });
  copyQueue = pending; return pending;
}
async function badge(tabId, text, title) {
  await chrome.action.setBadgeText({tabId, text}).catch(() => {});
  if (title) await chrome.action.setTitle({tabId, title}).catch(() => {});
}
async function notify(tabId, message) {
  await chrome.scripting.executeScript({target: {tabId}, func: value => globalThis.__occNotify?.(value), args: [message]}).catch(() => {});
}
async function openViewer() { await chrome.tabs.create({url: viewerURL()}); }
async function nextRevision() {
  const data = await chrome.storage.session.get(['revisionCounter', 'clearEpoch','recentEpoch']);
  const revision = Number.isSafeInteger(data.revisionCounter) ? data.revisionCounter + 1 : 1;
  await chrome.storage.session.set({revisionCounter: revision});
  return {revision, clearEpoch: data.clearEpoch || 0,recentEpoch:data.recentEpoch||0};
}
function limitation(capture) {
  if (capture.status !== 'PARTIAL') return capture.status === 'BEST_EFFORT' ? 'BEST_EFFORT не гарантирует полную историю.' : '';
  const reason = capture.warnings.find(w => /time|step|size|unsupported|bound|структур/i.test(w));
  return `PARTIAL: ${reason || 'причина ограничения не записана и неизвестна.'}`;
}
async function downloadCapture(capture, tabId = null) {
  if (!validSnapshot(capture)) throw new Error('Снимок отсутствует, пуст или повреждён.');
  const bytes = utf8(capture.text);
  const id = await chrome.downloads.download({
    url: `data:text/plain;charset=utf-8;base64,${bytesToBase64(bytes)}`,
    filename: safeFilename(capture), conflictAction: 'uniquify', saveAs: false
  });
  if (!Number.isInteger(id)) throw new Error('Chrome не подтвердил начало загрузки.');
  downloads.set(id, {tabId, captureId: capture.captureId});
  return id;
}
async function downloadVisibleScreenshot(capture, sender) {
  if (!validSnapshot(capture)) throw new Error('Снимок отсутствует, пуст или повреждён.');
  const tab = await chrome.tabs.get(sender.tab.id);
  if (!tab?.active || tab.windowId !== sender.tab.windowId) throw new Error('Для снимка экрана исходная вкладка должна быть активна.');
  const url = await chrome.tabs.captureVisibleTab(sender.tab.windowId, {format: 'png'});
  if (typeof url !== 'string' || !url.startsWith('data:image/png')) throw new Error('Chrome не вернул снимок видимой области.');
  const id = await chrome.downloads.download({url, filename: safeScreenshotFilename(capture), conflictAction: 'uniquify', saveAs: false});
  if (!Number.isInteger(id)) throw new Error('Chrome не подтвердил начало загрузки снимка.');
  downloads.set(id, {tabId: sender.tab.id, captureId: capture.captureId});
  return id;
}

async function run(tab, scroll = true, sourceMode = 'auto') {
  if (typeof tab?.id !== 'number') return;
  if (active) {
    if (active.tabId === tab.id) {
      if (active.committing) return;
      active.cancelled = true;
      await chrome.scripting.executeScript({target: {tabId: tab.id}, func: () => globalThis.__occCancel?.()}).catch(() => {});
    } else await badge(tab.id, 'BUSY', 'A capture is already running in another tab.');
    return;
  }
  const token = crypto.randomUUID();
  const job = active = {tabId: tab.id, token, documentId: null, cancelled: false, committing: false};
  let injected = false;
  try {
    Object.assign(job, await mutateStorage(nextRevision));
    // Deliberately retain the last accepted capture while this independent operation runs.
    await chrome.storage.session.set({lastError: '', jobStatus: 'CAPTURING'});
    const url = tab.url || '';
    if (!/^(https?:|file:)/i.test(url) || /^https:\/\/(chromewebstore\.google\.com|chrome\.google\.com\/webstore)/i.test(url)) throw new Error('This Chrome-protected page cannot be captured.');
    await badge(tab.id, '…', 'Capturing locally. Click again or press Escape to cancel.');
    await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['artifact-inventory.js', 'capture-regions.js', 'content.js']}); injected = true;
    if (job.cancelled) throw new Error('Capture cancelled before scanning. Clipboard unchanged.');
    const results = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: opts => globalThis.__occCapture(opts), args: [{scroll, sourceMode, operationToken: token}]});
    const result = results?.[0]?.result;
    if (result?.status === 'CANCELLED') { job.cancelled = true; throw new Error('Capture cancelled. Clipboard unchanged.'); }
    if (!result || !validStatus(result.status) || typeof result.text !== 'string' || !result.text || utf8(result.text).byteLength > MAX_BYTES) throw new Error('No valid non-empty capture returned. Clipboard was not changed.');
    const state = await chrome.storage.session.get('clearEpoch');
    if (job.cancelled || active !== job || (state.clearEpoch || 0) !== job.clearEpoch) throw new Error('Capture cancelled. Clipboard unchanged.');
    const capture = {...result, schemaVersion: SNAPSHOT_VERSION, captureId: crypto.randomUUID(), revision: job.revision,
      capturedAt: new Date().toISOString(), sourceTabId: tab.id, sourceDocumentId: job.documentId || ''};
    if (!validSnapshot(capture)) throw new Error('Capture plus metadata exceeds the 2,200,000-byte storage bound. Previous capture retained.');
    await mutateStorage(async () => {
      const current=await chrome.storage.session.get('clearEpoch');
      if(job.cancelled || active!==job || (current.clearEpoch||0)!==job.clearEpoch)throw new Error('Capture cancelled. Clipboard unchanged.');
      await chrome.storage.session.set({capture, jobStatus: capture.status, lastError: ''});
      const epoch=(await chrome.storage.session.get('recentEpoch')).recentEpoch||0;
      if(epoch===job.recentEpoch){try{const recent=await getRecent(),next=[...recent,capture];if(!validRecent(next))throw new Error('Память сессии заполнена: максимум 50 снимков / 2 200 000 байт. Скачайте и очистите её.');await chrome.storage.session.set({recentCaptures:next,recentWarning:''});}catch(error){await chrome.storage.session.set({recentWarning:error.message});}}
    });
    try {
      await copyText(capture.text, job);
      await badge(tab.id, capture.status === 'PARTIAL' ? 'PART' : capture.status === 'BEST_EFFORT' ? 'DOM' : 'OK', `${capture.status}; ${utf8(capture.text).byteLength} UTF-8 bytes.`);
    } catch (error) {
      await chrome.storage.session.set({lastError: `Clipboard was blocked: ${error.message}. Download remains available.`});
      await badge(tab.id, 'COPY', 'Text captured. Clipboard blocked; Download remains available.');
    }
    const recentWarning=(await chrome.storage.session.get('recentWarning')).recentWarning||'';
    await notify(tab.id, {kind: 'capture', text: `${utf8(capture.text).byteLength.toLocaleString()} UTF-8 байт. ${limitation(capture)} ${recentWarning}`,
      captureId: capture.captureId, revision: capture.revision});
  } catch (error) {
    await chrome.storage.session.set({lastError: error.message || String(error), jobStatus: job.cancelled ? 'CANCELLED' : 'ERROR'});
    await badge(tab.id, job.cancelled ? 'STOP' : 'ERR', error.message || 'Capture failed');
    if (injected) await notify(tab.id, {kind: 'error', text: `Текущая операция не завершена: ${error.message}. Предыдущий снимок сохранён.`});
    else await openViewer();
  } finally { if (active === job) active = null; }
}

async function agentosNativePermission() {
  if (!chrome.permissions?.contains || !chrome.runtime?.connectNative) return false;
  return await chrome.permissions.contains({permissions: ['nativeMessaging']});
}
function agentosExtensionPage(sender) {
  return sender?.id === chrome.runtime.id && !sender.tab && typeof sender.url === 'string' &&
    sender.url.startsWith(chrome.runtime.getURL(''));
}
function agentosRejectPending(reason) {
  for (const pending of agentosNativePending.values()) {
    clearTimeout(pending.timer);
    pending.reject(new Error(reason));
  }
  agentosNativePending.clear();
}
function agentosStream(controlId, chunk) {
  if (!agentosNativePort) throw new Error('NATIVE_BRIDGE_UNAVAILABLE');
  agentosNativePort.postMessage({type:'agentos.control.stream',controlId,chunk});
}
async function agentosFrameSnapshots(tabId, controlId) {
  try {
    const frames=await chrome.scripting.executeScript({target:{tabId,allFrames:true},func:()=>{
      const MAX=300000,skip=new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','HEAD','SVG','CANVAS']);
      const visible=el=>{
        if(!el?.isConnected||el.hidden||el.getAttribute?.('aria-hidden')==='true')return false;
        const css=getComputedStyle(el);return css.display!=='none'&&css.visibility!=='hidden'&&css.visibility!=='collapse'&&!!el.getClientRects().length;
      };
      const out=[];let chars=0;
      const selector='p,pre,li,h1,h2,h3,h4,h5,h6,blockquote,table,[role="document"],article';
      for(const el of document.querySelectorAll(selector)){
        if(skip.has(el.tagName)||!visible(el)||el.closest('nav,header,footer,[role="navigation"],form'))continue;
        const text=(el.tagName==='PRE'?el.textContent:(el.innerText||el.textContent||'')).trim();
        if(!text||text.length<2)continue;
        if(chars+text.length>MAX)break;
        out.push(text);chars+=text.length;
      }
      return {source:location.origin+location.pathname,title:document.title||'',content_type:document.contentType||'',
        text:out.join('\n\n'),chars,ready_state:document.readyState};
    }});
    for(const frame of frames){
      if(!frame?.result?.text)continue;
      agentosStream(controlId,{kind:'frame',frameId:frame.frameId,documentId:frame.documentId||null,...frame.result});
    }
    return {frames:frames.length,error:null};
  } catch(error) {
    return {frames:0,error:error.message||'FRAME_CAPTURE_FAILED'};
  }
}
async function agentosArchiveCapture(tab, controlId, args={}) {
  if(active)throw new Error('CAPTURE_BUSY');
  if(!tab||!Number.isInteger(tab.id))throw new Error('ACTIVE_TAB_UNAVAILABLE');
  const token=crypto.randomUUID();
  const job=active={tabId:tab.id,token,documentId:null,cancelled:false,committing:false,archive:true};
  const session={controlId,tabId:tab.id,lastSequence:0};agentosArchiveStreams.set(token,session);
  let injected=false;
  try{
    const url=tab.url||'';
    if(!/^(https?:|file:)/i.test(url)||/^https:\/\/(chromewebstore\.google\.com|chrome\.google\.com\/webstore)/i.test(url))throw new Error('CAPTURE_URL_UNSUPPORTED');
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:['artifact-inventory.js','capture-regions.js','content.js']});injected=true;
    const maxMs=Math.max(5000,Math.min(240000,Number.isSafeInteger(args.maxMs)?args.maxMs:120000));
    const maxSteps=Math.max(10,Math.min(8000,Number.isSafeInteger(args.maxSteps)?args.maxSteps:3000));
    const maxBytes=Math.max(1024*1024,Math.min(64*1024*1024,Number.isSafeInteger(args.maxBytes)?args.maxBytes:64*1024*1024));
    const results=await chrome.scripting.executeScript({target:{tabId:tab.id},func:opts=>globalThis.__occCapture(opts),
      args:[{scroll:true,sourceMode:'auto',operationToken:token,headless:true,streamRecords:true,
        maxMs,maxSteps,maxBytes,settleMs:Math.max(120,Math.min(1500,args.settleMs||260))}]});
    const result=results?.[0]?.result;
    if(!result||result.streamed!==true||!Array.isArray(result.order)||!result.coverage)throw new Error('ARCHIVE_CAPTURE_SCHEMA');
    const frameInfo=await agentosFrameSnapshots(tab.id,controlId);
    return {state:'ARCHIVE_CAPTURED',tabId:tab.id,source:result.source,status:result.status,mode:result.mode,
      count:result.count,steps:result.steps,contentVersion:result.contentVersion,scanId:result.scanId,
      regionIds:result.regionIds,warnings:result.warnings,artifacts:result.artifacts,coverage:result.coverage,
      order:result.order,frame_capture:frameInfo};
  } finally {
    agentosArchiveStreams.delete(token);
    if(injected)void chrome.scripting.executeScript({target:{tabId:tab.id},func:()=>globalThis.__occCancel?.()}).catch(()=>{});
    if(active===job)active=null;
  }
}
async function agentosResolveTab(args={}) {
  let tab;
  if(Number.isInteger(args.tabId))tab=await chrome.tabs.get(args.tabId);
  else tab=(await chrome.tabs.query({active:true,lastFocusedWindow:true}))[0];
  if(!tab||!Number.isInteger(tab.id))throw new Error('ACTIVE_TAB_UNAVAILABLE');
  const url=tab.url||'';
  if(!/^(https?:|file:)/i.test(url)||/^https:\/\/(chromewebstore\.google\.com|chrome\.google\.com\/webstore)/i.test(url))throw new Error('UI_URL_UNSUPPORTED');
  return tab;
}
async function agentosUIInventory(args={}) {
  const tab=await agentosResolveTab(args);
  await chrome.scripting.executeScript({target:{tabId:tab.id},files:['ui-inventory.js']});
  const rows=await chrome.scripting.executeScript({target:{tabId:tab.id},func:()=>globalThis.__occUIInventory?.()});
  const result=rows?.[0]?.result;
  if(!result||typeof result.snapshot_id!=='string'||!Array.isArray(result.elements))throw new Error('UI_INVENTORY_SCHEMA');
  return {tabId:tab.id,...result};
}
async function agentosUIAct(args={}) {
  const tab=await agentosResolveTab(args);
  if(!args.request||typeof args.request!=='object')throw new Error('UI_ACTION_SCHEMA');
  const request={...args.request};
  if(request.action!=='scroll_into_view'&&request.effect_class!=='BROWSER_WRITE')throw new Error('UI_EFFECT_GRANT_REQUIRED');
  await chrome.scripting.executeScript({target:{tabId:tab.id},files:['ui-inventory.js']});
  const rows=await chrome.scripting.executeScript({target:{tabId:tab.id},func:req=>globalThis.__occUIAct?.(req),args:[request]});
  const result=rows?.[0]?.result;
  if(!result||typeof result.state!=='string')throw new Error('UI_ACTION_RESULT_SCHEMA');
  return {tabId:tab.id,...result};
}
async function handleAgentOSLocalControl(message) {
  if (message.command === 'tabs.list') {
    const tabs = await chrome.tabs.query({});
    return tabs.filter(tab => Number.isInteger(tab.id)).map(tab => ({
      id: tab.id, windowId: tab.windowId, active: tab.active === true,
      title: typeof tab.title === 'string' ? tab.title : '',
      url: typeof tab.url === 'string' ? tab.url : ''
    }));
  }
  if (message.command === 'browser.ui.inventory') return await agentosUIInventory(message.args||{});
  if (message.command === 'browser.ui.act') return await agentosUIAct(message.args||{});
  if (message.command === 'tabs.active') {
    const tabs = await chrome.tabs.query({active: true, lastFocusedWindow: true});
    const tab = tabs[0];
    if (!tab || !Number.isInteger(tab.id)) throw new Error('ACTIVE_TAB_UNAVAILABLE');
    return {id: tab.id, windowId: tab.windowId, active: true,
      title: typeof tab.title === 'string' ? tab.title : '',
      url: typeof tab.url === 'string' ? tab.url : ''};
  }
  if (message.command === 'tab.capture.archive') {
    let tab;
    if (Number.isInteger(message.args?.tabId)) tab=await chrome.tabs.get(message.args.tabId);
    else tab=(await chrome.tabs.query({active:true,lastFocusedWindow:true}))[0];
    return await agentosArchiveCapture(tab,message.controlId,message.args||{});
  }
  if (message.command === 'capture.get') {
    const found = await getCapture();
    if (!found) throw new Error('CAPTURE_UNAVAILABLE');
    const cap = found.capture;
    if (Number.isInteger(message.args?.tabId) && cap.sourceTabId !== message.args.tabId) throw new Error('CAPTURE_TAB_MISMATCH');
    return {state: 'CAPTURE_AVAILABLE', tabId: cap.sourceTabId, captureId: cap.captureId, revision: cap.revision,
      status: cap.status, capturedAt: cap.capturedAt, text: cap.text, warnings: cap.warnings || [], source: cap.source || ''};
  }
  if (message.command === 'system2.codex.submit') return await agentosCodexSubmit(message.args || {});
  if (message.command === 'system2.codex.status') return await agentosCodexStatus(message.args || {});
  if (message.command === 'system2.codex.result') return await agentosCodexResult(message.args || {});
  if (message.command === 'tab.capture.start') {
    let tab;
    if (Number.isInteger(message.args?.tabId)) tab = await chrome.tabs.get(message.args.tabId);
    else tab = (await chrome.tabs.query({active: true, lastFocusedWindow: true}))[0];
    if (!tab || !Number.isInteger(tab.id)) throw new Error('ACTIVE_TAB_UNAVAILABLE');
    const prior = await getCapture();
    const priorKey = prior ? prior.capture.captureId + ':' + prior.capture.revision : null;
    await run(tab, true, 'auto');
    const found = await getCapture();
    const currentKey = found ? found.capture.captureId + ':' + found.capture.revision : null;
    if (!found || found.capture.sourceTabId !== tab.id || currentKey === priorKey) throw new Error('CAPTURE_NOT_CONFIRMED');
    return {state: 'CAPTURE_CONFIRMED', tabId: tab.id, captureId: found.capture.captureId,
      revision: found.capture.revision, status: found.capture.status};
  }
  throw new Error('LOCAL_CONTROL_COMMAND_UNAVAILABLE');
}
function agentosHandleNativeMessage(message, port) {
  if (message?.push === true && message.channel === 'agentos-local-control') {
    Promise.resolve().then(() => handleAgentOSLocalControl(message)).then(
      result => port.postMessage({type: 'agentos.control.reply', controlId: message.controlId, ok: true, result}),
      error => port.postMessage({type: 'agentos.control.reply', controlId: message.controlId, ok: false, error: error.message || 'LOCAL_CONTROL_FAILED'})
    );
    return;
  }
  const pending = agentosNativePending.get(message?.requestId);
  if (!pending) return;
  if (message.progress === true) {
    pending.onProgress?.();
    return;
  }
  agentosNativePending.delete(message.requestId);
  clearTimeout(pending.timer);
  message.ok === true ? pending.resolve(message) : pending.reject(new Error(message.error || 'NATIVE_OPERATION_FAILED'));
}
async function ensureAgentOSNativeBridge() {
  if (agentosNativePort) return agentosNativePort;
  if (agentosNativeConnectPromise) return await agentosNativeConnectPromise;
  agentosNativeConnectPromise = (async () => {
    if (!(await agentosNativePermission())) throw new Error('NATIVE_PERMISSION_REQUIRED');
    const port = chrome.runtime.connectNative(AGENTOS_NATIVE_HOST);
    agentosNativePort = port;
    port.onMessage.addListener(message => agentosHandleNativeMessage(message, port));
    port.onDisconnect.addListener(() => {
      if (agentosNativePort !== port) return;
      agentosNativePort = null;
      agentosRejectPending(chrome.runtime.lastError?.message || 'NATIVE_DISCONNECTED');
    });
    const requestId = 'agentos-claim-' + Date.now() + '-' + (++agentosNativeSeq);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        agentosNativePending.delete(requestId);
        reject(new Error('LOCAL_CONTROL_CLAIM_TIMEOUT'));
      }, 10000);
      agentosNativePending.set(requestId, {resolve, reject, timer});
      port.postMessage({type: 'agentos.bridge.claim', requestId});
    });
    return port;
  })();
  try { return await agentosNativeConnectPromise; }
  catch (error) {
    try { agentosNativePort?.disconnect(); } catch {}
    agentosNativePort = null;
    throw error;
  } finally { agentosNativeConnectPromise = null; }
}
async function agentosNativeRequest(request, onProgress) {
  const port = await ensureAgentOSNativeBridge();
  const requestId = 'agentos-bg-' + Date.now() + '-' + (++agentosNativeSeq);
  return await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      agentosNativePending.delete(requestId);
      reject(new Error('NATIVE_TIMEOUT'));
    }, 130000);
    agentosNativePending.set(requestId, {resolve, reject, timer, onProgress});
    port.postMessage({...request, requestId});
  });
}
async function agentosSha256(bytes) {
  const raw = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(raw)].map(x => x.toString(16).padStart(2, '0')).join('');
}
async function agentosCodexSubmit(args) {
  if (!args || typeof args.instruction !== 'string' || !args.instruction.trim() ||
      typeof args.text !== 'string' || !args.text || !['analyze','build'].includes(args.mode || 'analyze')) {
    throw new Error('SYSTEM2_CODEX_SCHEMA');
  }
  const bytes = utf8(args.text);
  if (bytes.byteLength > MAX_BYTES) throw new Error('SYSTEM2_CODEX_INPUT_LIMIT');
  const mode = args.mode || 'analyze';
  const begin = await agentosNativeRequest({type:'begin', instruction:args.instruction, mode,
    bytes:bytes.byteLength, sha256:await agentosSha256(bytes)});
  const jobId = begin.job?.id;
  if (typeof jobId !== 'string') throw new Error('SYSTEM2_CODEX_JOB_SCHEMA');
  try {
    for (let offset = 0; offset < bytes.length; offset += 49152) {
      const part = bytes.subarray(offset, Math.min(bytes.length, offset + 49152));
      await agentosNativeRequest({type:'append', jobId, offset, base64:bytesToBase64(part)});
    }
    const run = await agentosNativeRequest({type:'run', jobId});
    return {job:run.job || begin.job};
  } catch (error) {
    await agentosNativeRequest({type:'discard', jobId}).catch(() => {});
    throw error;
  }
}
async function agentosCodexStatus(args) {
  if (!args || typeof args.jobId !== 'string') throw new Error('SYSTEM2_CODEX_SCHEMA');
  const list = await agentosNativeRequest({type:'list'});
  const job = Array.isArray(list.jobs) ? list.jobs.find(x => x.id === args.jobId) : null;
  if (!job) throw new Error('SYSTEM2_CODEX_JOB_NOT_FOUND');
  return {job};
}
async function agentosCodexResult(args) {
  if (!args || typeof args.jobId !== 'string') throw new Error('SYSTEM2_CODEX_SCHEMA');
  const status = await agentosCodexStatus(args);
  if (status.job.state !== 'COMPLETE') return status;
  let offset = 0, total = null, sha = null, chunks = [];
  while (total === null || offset < total) {
    const frame = await agentosNativeRequest({type:'result', jobId:args.jobId, offset});
    if (!Number.isSafeInteger(frame.bytes) || frame.bytes < 0 || frame.offset !== offset ||
        typeof frame.base64 !== 'string' || typeof frame.sha256 !== 'string') throw new Error('SYSTEM2_CODEX_RESULT_SCHEMA');
    if (total !== null && (frame.bytes !== total || frame.sha256 !== sha)) throw new Error('SYSTEM2_CODEX_RESULT_CHANGED');
    total = frame.bytes; sha = frame.sha256;
    const raw = Uint8Array.from(atob(frame.base64), ch => ch.charCodeAt(0));
    chunks.push(raw); offset += raw.length;
    if (!raw.length && offset < total) throw new Error('SYSTEM2_CODEX_RESULT_SCHEMA');
  }
  const bytes = new Uint8Array(total || 0); let cursor = 0;
  for (const part of chunks) { bytes.set(part, cursor); cursor += part.length; }
  if (await agentosSha256(bytes) !== sha) throw new Error('SYSTEM2_CODEX_RESULT_HASH');
  return {job:status.job, text:new TextDecoder('utf-8',{fatal:true}).decode(bytes), sha256:sha};
}
void agentosNativePermission().then(ok => { if (ok) void ensureAgentOSNativeBridge().catch(() => {}); });
chrome.runtime.onStartup?.addListener(() => {
  void agentosNativePermission().then(ok => { if (ok) void ensureAgentOSNativeBridge().catch(() => {}); });
});

chrome.action.onClicked.addListener(tab => { void run(tab); });
chrome.runtime.onInstalled.addListener(() => {
  void chrome.storage.local.setAccessLevel?.({accessLevel: 'TRUSTED_CONTEXTS'});
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({id: 'viewer', title: 'Просмотр последнего снимка', contexts: ['action']});
    chrome.contextMenus.create({id: 'library', title: 'Библиотека документов по датам', contexts: ['action']});
    chrome.contextMenus.create({id: 'download', title: 'Скачать последний собранный текст', contexts: ['action']});
    chrome.contextMenus.create({id:'recent-download',title:'Скачать все снимки текущей сессии TXT',contexts:['action']});
    chrome.contextMenus.create({id: 'capture-chat', title: 'Собрать только переписку', contexts: ['action']});
    chrome.contextMenus.create({id: 'capture-document', title: 'Собрать открытый документ', contexts: ['action']});
    chrome.contextMenus.create({id: 'capture-both', title: 'Собрать переписку + документ', contexts: ['action']});
    chrome.contextMenus.create({id: 'loaded', title: 'Собрать загруженный текст без прокрутки', contexts: ['action']});
    chrome.contextMenus.create({id: 'agentos-enable', title: 'Включить локальный AgentOS bridge для HTTP(S) сайтов', contexts: ['action']});
  });
});
void chrome.storage.local.setAccessLevel?.({accessLevel: 'TRUSTED_CONTEXTS'});
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'viewer') void openViewer();
  if (info.menuItemId === 'library') void chrome.tabs.create({url: chrome.runtime.getURL('library.html')});
  if (info.menuItemId === 'loaded') void run(tab, false);
  if (info.menuItemId === 'agentos-enable') {
    void chrome.permissions.request({permissions: ['nativeMessaging','tabs'], origins:['https://*/*','http://*/*']}).then(granted => {
      if (granted) return ensureAgentOSNativeBridge();
      throw new Error('AGENTOS_BROWSER_PERMISSION_REQUIRED');
    }).catch(() => {});
  }
  if (info.menuItemId === 'capture-chat') void run(tab, true, 'chat');
  if (info.menuItemId === 'capture-document') void run(tab, true, 'document');
  if (info.menuItemId === 'capture-both') void run(tab, true, 'chat+document');
  if(info.menuItemId==='recent-download')void downloadRecent().catch(error=>{void chrome.tabs.create({url:`${viewerURL()}?downloadError=${encodeURIComponent(error.message)}`});});
  if (info.menuItemId === 'download') void getCapture().then(found => {
    if (!found) throw new Error('Нет доступного снимка для скачивания.');
    return downloadCapture(found.capture);
  }).catch(error => { void chrome.tabs.create({url: `${viewerURL()}?downloadError=${encodeURIComponent(error.message)}`}); });
});
chrome.downloads.onChanged.addListener(delta => {
  const own = downloads.get(delta.id); if (!own) return;
  if (delta.state?.current === 'complete') {
    downloads.delete(delta.id);
    if (own.tabId != null) void notify(own.tabId, {kind: 'download', text: 'Загрузка завершена. Файл записан Chrome.'});
  } else if (delta.state?.current === 'interrupted') {
    downloads.delete(delta.id);
    if (own.tabId != null) void notify(own.tabId, {kind: 'error', text: `Загрузка прервана: ${delta.error?.current || 'причина не сообщена Chrome'}.`});
  }
});

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message?.target === 'agentos-background') {
    if (!agentosExtensionPage(sender)) return false;
    if (message.type === 'enableNativeBridge') {
      ensureAgentOSNativeBridge().then(() => respond({ok: true}), error => respond({ok: false, error: error.message}));
      return true;
    }
    if (message.type === 'nativeRequest' && message.request && typeof message.request.type === 'string') {
      agentosNativeRequest(message.request).then(result => respond({ok: true, result}), error => respond({ok: false, error: error.message}));
      return true;
    }
    return false;
  }

  // Exact library page only: capture reads and bounded recent-session commands; no arbitrary payloads.
  if (message?.target === 'library') {
    if (sender.id !== chrome.runtime.id || sender.tab || sender.url !== chrome.runtime.getURL('library.html')) return false;
    if(message.type==='getRecent'){getRecent().then(captures=>respond({ok:true,captures}),error=>respond({ok:false,error:error.message}));return true;}
    if(message.type==='downloadRecent'){downloadRecent().then(downloadId=>respond({ok:true,downloadId}),error=>respond({ok:false,error:error.message}));return true;}
    if(message.type==='clearRecent'){mutateStorage(async()=>{const epoch=(await chrome.storage.session.get('recentEpoch')).recentEpoch||0;await chrome.storage.session.set({recentCaptures:[],recentEpoch:epoch+1,recentWarning:''});}).then(()=>respond({ok:true}),error=>respond({ok:false,error:error.message}));return true;}
    if(message.type!=='getCapture')return false;
    getCapture().then(found => respond({ok: true, capture: found?.capture || null}), error => respond({ok:false,error:error.message}));
    return true;
  }
  if (message?.target !== 'worker' || sender.id !== chrome.runtime.id) return false;
  if (message.type === 'progress' && sender.tab?.id === active?.tabId && message.operationToken === active.token) {
    active.documentId ||= sender.documentId || ''; void badge(sender.tab.id, String(message.blocks).slice(0, 4)); respond({ok: true}); return false;
  }
  if (message.type === 'captureStream') {
    const session=agentosArchiveStreams.get(message.operationToken);
    if(!session||sender.tab?.id!==session.tabId||!Number.isSafeInteger(message.sequence)||message.sequence<=session.lastSequence||
       !message.chunk||typeof message.chunk!=='object'){respond({ok:false,error:'CAPTURE_STREAM_SCOPE'});return false;}
    session.lastSequence=message.sequence;
    try{agentosStream(session.controlId,{sequence:message.sequence,...message.chunk});respond({ok:true});}
    catch(error){respond({ok:false,error:error.message||'CAPTURE_STREAM_FAILED'});}
    return false;
  }
  if (message.type === 'captureContext' && sender.tab?.id === active?.tabId && message.operationToken === active.token) {
    active.documentId = sender.documentId || ''; respond({ok: true}); return false;
  }
  if (message.type === 'downloadCapture') {
    // Content scripts may request only their own exact snapshot, never arbitrary text or the latest capture.
    if (!sender.tab || message.userGesture !== true || typeof message.captureId !== 'string' || !message.captureId || !Number.isSafeInteger(message.revision)) return false;
    getCapture(message.captureId, message.revision).then(found => {
      if (!found) throw new Error('Этот снимок больше недоступен; более новый результат не будет подставлен.');
      const c = found.capture;
      if (c.sourceTabId !== sender.tab.id || (c.sourceDocumentId && c.sourceDocumentId !== (sender.documentId || ''))) throw new Error('Снимок принадлежит другой вкладке или документу.');
      return downloadCapture(c, sender.tab.id);
    }).then(id => respond({ok: true, downloadId: id}), error => respond({ok: false, error: error.message})); return true;
  }
  if (message.type === 'captureScreenshot') {
    if (!sender.tab || message.userGesture !== true || typeof message.captureId !== 'string' || !message.captureId || !Number.isSafeInteger(message.revision)) return false;
    getCapture(message.captureId, message.revision).then(found => {
      if (!found) throw new Error('Этот снимок больше недоступен; снимок другой вкладки сделан не будет.');
      const c = found.capture;
      if (c.sourceTabId !== sender.tab.id || (c.sourceDocumentId && c.sourceDocumentId !== (sender.documentId || ''))) throw new Error('Снимок принадлежит другой вкладке или документу.');
      return downloadVisibleScreenshot(c, sender);
    }).then(id => respond({ok: true, downloadId: id}), error => respond({ok: false, error: error.message})); return true;
  }
  if (message.type === 'openCapture') {
    if (!sender.tab || message.userGesture !== true || typeof message.captureId !== 'string' || !message.captureId || !Number.isSafeInteger(message.revision)) return false;
    getCapture(message.captureId, message.revision).then(found => {
      if (!found || found.capture.sourceTabId !== sender.tab.id || (found.capture.sourceDocumentId && found.capture.sourceDocumentId !== (sender.documentId || ''))) throw new Error('Этот снимок больше недоступен.');
      return openViewer();
    }).then(() => respond({ok: true}), error => respond({ok: false, error: error.message})); return true;
  }
  // Remaining commands are privileged extension-page operations.
  if (sender.tab || sender.url?.split(/[?#]/)[0] !== viewerURL()) return false;
  if (message.type === 'copy') {
    copyText(message.text).then(() => respond({ok: true}), error => respond({ok: false, error: error.message})); return true;
  }
  if (message.type === 'getState') {
    Promise.all([chrome.storage.session.get(['capture', 'lastError', 'jobStatus', 'clearEpoch']), chrome.storage.local.get(LOCAL_CAPTURE)])
      .then(([s, l]) => respond({ok: true, session: validSnapshot(s.capture) ? s.capture : null,
        saved: validSnapshot(l[LOCAL_CAPTURE]) ? l[LOCAL_CAPTURE] : null, lastError: s.lastError || '', jobStatus: s.jobStatus || '', clearEpoch: s.clearEpoch || 0})); return true;
  }
  if (message.type === 'downloadStored') {
    getCapture(message.captureId, message.revision).then(found => {
      if (!found) throw new Error('Выбранный снимок больше недоступен.'); return downloadCapture(found.capture);
    }).then(id => respond({ok: true, downloadId: id}), error => respond({ok: false, error: error.message})); return true;
  }
  if (message.type === 'persist') {
    mutateStorage(async () => {
      const state = await chrome.storage.session.get('clearEpoch');
      if ((state.clearEpoch || 0) !== message.clearEpoch) throw new Error('Данные были удалены в другой вкладке; сохранение отменено.');
      const found = await getCapture(message.captureId, message.revision);
      if (!found) throw new Error('Выбранный снимок больше недоступен.');
      await chrome.storage.local.set({[LOCAL_CAPTURE]: found.capture});
      const verify = (await chrome.storage.local.get(LOCAL_CAPTURE))[LOCAL_CAPTURE];
      if (!validSnapshot(verify) || verify.captureId !== found.capture.captureId) throw new Error('Chrome не подтвердил сохранение.');
      return verify;
    }).then(saved => respond({ok: true, saved}), error => respond({ok: false, error: error.message})); return true;
  }
  if (message.type === 'clear') {
    mutateStorage(async () => {
      if (active && !active.committing) { active.cancelled = true; void chrome.scripting.executeScript({target: {tabId: active.tabId}, func: () => globalThis.__occCancel?.()}).catch(() => {}); }
      const current = (await chrome.storage.session.get('clearEpoch')).clearEpoch || 0;
      await chrome.storage.session.clear(); await chrome.storage.session.set({clearEpoch: current + 1});
      await chrome.storage.local.remove(LOCAL_CAPTURE);
      return current + 1;
    }).then(clearEpoch => respond({ok: true, clearEpoch}), error => respond({ok: false, error: error.message})); return true;
  }
  return false;
});
