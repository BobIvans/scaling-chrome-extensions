// Session-only capture storage. No remote requests or automatic pasting.
const MAX_BYTES = 2200000;
let active = null;
let creatingOffscreen = null;
let copyQueue = Promise.resolve();
const viewerURL = () => chrome.runtime.getURL('viewer.html');

async function offscreen() {
  const url = chrome.runtime.getURL('offscreen.html');
  const contexts = await chrome.runtime.getContexts({contextTypes: ['OFFSCREEN_DOCUMENT'], documentUrls: [url]});
  if (contexts.length) return;
  if (!creatingOffscreen) {
    creatingOffscreen = chrome.offscreen.createDocument({url: 'offscreen.html', reasons: ['CLIPBOARD'],
      justification: 'Copy text the user explicitly captured to the system clipboard.'}).finally(() => { creatingOffscreen = null; });
  }
  await creatingOffscreen;
}
function copyText(text, job = null) {
  if (typeof text !== 'string' || new TextEncoder().encode(text).length > MAX_BYTES) {
    return Promise.reject(new Error('Invalid or oversized clipboard payload.'));
  }
  const pending = copyQueue.catch(() => {}).then(async () => {
    await offscreen();
    if (job?.cancelled) throw new Error('Capture cancelled before clipboard dispatch.');
    if (job) job.committing = true;
    const result = await chrome.runtime.sendMessage({target: 'offscreen', type: 'copy', text});
    if (!result?.ok) throw new Error(result?.error || 'Clipboard write did not succeed.');
    return result;
  });
  copyQueue = pending;
  return pending;
}
async function badge(tabId, text, title) {
  await chrome.action.setBadgeText({tabId, text}).catch(() => {});
  if (title) await chrome.action.setTitle({tabId, title}).catch(() => {});
}
async function notify(tabId, text) {
  await chrome.scripting.executeScript({target: {tabId}, func: message => globalThis.__occNotify?.(message), args: [text]}).catch(() => {});
}
async function openViewer() { await chrome.tabs.create({url: viewerURL()}); }

async function run(tab, scroll = true) {
  if (typeof tab?.id !== 'number') return;
  if (active) {
    if (active.tabId === tab.id) {
      if (active.committing) return;
      active.cancelled = true;
      await chrome.scripting.executeScript({target: {tabId: tab.id}, func: () => globalThis.__occCancel?.()}).catch(() => {});
    } else { await badge(tab.id, 'BUSY', 'A capture is already running in another tab.'); }
    return;
  }
  const job = active = {tabId: tab.id, cancelled: false, committing: false};
  let injected = false;
  try {
    // Remove a previous capture before starting; failures must not masquerade as fresh data.
    await chrome.storage.session.remove('capture');
    await chrome.storage.session.set({lastError: '', jobStatus: 'CAPTURING'});
    const url = tab.url || '';
    if (!/^(https?:|file:)/i.test(url) || /^https:\/\/(chromewebstore\.google\.com|chrome\.google\.com\/webstore)/i.test(url)) {
      throw new Error('This Chrome-protected page cannot be captured. Open an ordinary webpage, or import TXT in the local viewer.');
    }
    await badge(tab.id, '…', 'Capturing locally. Click again or press Escape to cancel.');
    await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']});
    injected = true;
    if (job.cancelled) throw new Error('Capture cancelled before scanning. Clipboard unchanged.');
    const results = await chrome.scripting.executeScript({target: {tabId: tab.id},
      func: opts => globalThis.__occCapture(opts), args: [{scroll}]});
    const capture = results?.[0]?.result;
    if (!capture || !['SELECTION','RAW_TEXT','BEST_EFFORT','PARTIAL','CANCELLED'].includes(capture.status) || typeof capture.text !== 'string' || new TextEncoder().encode(capture.text).length > MAX_BYTES) {
      throw new Error('No valid capture returned. Clipboard was not changed.');
    }
    capture.capturedAt = new Date().toISOString();
    if (job.cancelled) capture.status = 'CANCELLED';
    await chrome.storage.session.set({capture, jobStatus: capture.status});
    if (capture.status === 'CANCELLED') {
      await badge(tab.id, 'STOP', 'Cancelled. Clipboard unchanged. Preview is available through Options.');
      await notify(tab.id, 'Cancelled. Clipboard unchanged. Partial capture is available in Options.');
      return;
    }
    try {
      await copyText(capture.text, job);
      const label = capture.status === 'PARTIAL' ? 'PART' : capture.status === 'BEST_EFFORT' ? 'DOM' : 'OK';
      await badge(tab.id, label, `Copied ${capture.text.length} UTF-16 code units. ${capture.status}. Right-click for preview.`);
      await notify(tab.id, `Copied ${new TextEncoder().encode(capture.text).length.toLocaleString()} bytes of UTF-8 text. ${capture.status}. Paste with Ctrl+V. Right-click the extension for preview.`);
    } catch (error) {
      if (job.cancelled) {
        await chrome.storage.session.remove('capture');
        await chrome.storage.session.set({jobStatus: 'CANCELLED', lastError: ''});
        await badge(tab.id, 'STOP', 'Cancelled. Clipboard unchanged.');
        await notify(tab.id, 'Cancelled. Clipboard unchanged.');
        return;
      }
      await chrome.storage.session.set({lastError: `Clipboard was blocked: ${error.message}. Use Copy in this viewer.`});
      await badge(tab.id, 'COPY', 'Text captured. Use the local preview Copy button.');
      await openViewer();
    }
  } catch (error) {
    await chrome.storage.session.remove('capture');
    await chrome.storage.session.set({lastError: error.message || String(error), jobStatus: job.cancelled ? 'CANCELLED' : 'ERROR'});
    await badge(tab.id, job.cancelled ? 'STOP' : 'ERR', error.message || 'Capture failed');
    if (injected) await notify(tab.id, `Capture failed: ${error.message}. Clipboard unchanged.`);
    await openViewer();
  } finally { active = null; }
}

chrome.action.onClicked.addListener(tab => { void run(tab); });
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({id: 'viewer', title: 'Preview / copy last capture / open TXT', contexts: ['action']});
    chrome.contextMenus.create({id: 'loaded', title: 'Copy loaded text only (no scrolling)', contexts: ['action']});
  });
});
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'viewer') void openViewer();
  if (info.menuItemId === 'loaded') void run(tab, false);
});
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message?.target !== 'worker' || sender.id !== chrome.runtime.id) return false;
  if (message.type === 'progress' && sender.tab?.id === active?.tabId) {
    void badge(sender.tab.id, String(message.blocks).slice(0, 4));
    respond({ok: true}); return false;
  }
  // Only our visible extension page may command the clipboard or clear storage.
  if (sender.url?.split('?')[0] !== viewerURL()) return false;
  if (message.type === 'copy') {
    copyText(message.text).then(() => respond({ok: true}), error => respond({ok: false, error: error.message}));
    return true;
  }
  if (message.type === 'clear') {
    if (active && !active.committing) {
      active.cancelled = true;
      void chrome.scripting.executeScript({target: {tabId: active.tabId}, func: () => globalThis.__occCancel?.()}).catch(() => {});
    }
    chrome.storage.session.clear().then(() => respond({ok: true}), error => respond({ok: false, error: error.message}));
    return true;
  }
  return false;
});
