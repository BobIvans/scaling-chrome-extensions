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
const utf8 = text => new TextEncoder().encode(text);

function validStatus(value) {
  return ['SELECTION', 'RAW_TEXT', 'BEST_EFFORT', 'PARTIAL'].includes(value);
}
function validSnapshot(value) {
  if (!value || value.schemaVersion !== SNAPSHOT_VERSION || typeof value.captureId !== 'string' ||
      !Number.isSafeInteger(value.revision) || value.revision < 1 || typeof value.text !== 'string' ||
      !value.text || !validStatus(value.status) || !Array.isArray(value.warnings) ||
      value.warnings.some(item => typeof item !== 'string') || typeof value.capturedAt !== 'string') return false;
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
    await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['capture-regions.js', 'content.js']}); injected = true;
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
  });
});
void chrome.storage.local.setAccessLevel?.({accessLevel: 'TRUSTED_CONTEXTS'});
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'viewer') void openViewer();
  if (info.menuItemId === 'library') void chrome.tabs.create({url: chrome.runtime.getURL('library.html')});
  if (info.menuItemId === 'loaded') void run(tab, false);
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
