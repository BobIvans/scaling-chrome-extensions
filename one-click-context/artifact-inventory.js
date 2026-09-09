/* Deterministic, read-only inventory of visible web content access points. */
(() => {
  const VERSION = 1;
  const LIMIT = 100;
  const MESSAGE_LIMIT = 5000;
  const FILE_RE = /\.(txt|md|csv|tsv|jsonl?|ya?ml|xml|html?|pdf|docx?|pptx?|xlsx?|ods|odt|odp|rtf|zip|tar|gz|png|jpe?g|webp|gif|svg|mp3|wav|m4a|mp4|webm|mov)(?:$|[?#])/i;
  const MORE_RE = /(?:show|view|read|load|expand|continue|more|open|показать|развернуть|читать|загрузить|открыть|ещ[её])/i;
  const clean = value => String(value || '').replace(/\s+/g, ' ').trim().slice(0, 160);
  function safeURL(value, base) {
    try {
      const url = new URL(value, base);
      if (!['http:', 'https:', 'blob:', 'file:'].includes(url.protocol)) return '';
      if (url.protocol === 'blob:') return 'blob: current page object';
      if (url.protocol === 'file:') return 'local file (path omitted)';
      return url.origin + url.pathname;
    } catch { return ''; }
  }
  function visible(el) {
    if (!el?.isConnected || !el.getClientRects().length || el.closest('[data-occ-ignore]')) return false;
    for (let node = el; node; node = node.parentElement) {
      if (node.hidden || node.inert || node.getAttribute('aria-hidden') === 'true') return false;
      const css = getComputedStyle(node);
      if (css.display === 'none' || css.visibility === 'hidden' || css.visibility === 'collapse') return false;
    }
    return true;
  }
  function siteProfile(url = location.href) {
    let host = '';
    try { host = new URL(url).hostname; } catch {}
    if (host === 'chatgpt.com') return {name:'chatgpt', maturity:'LIVE_DOM_REQUIRES_SMOKE', selector:'[data-message-id][data-message-author-role], [data-turn-id][data-message-author-role]'};
    if (host === 'chat.deepseek.com') return {name:'deepseek', maturity:'LIVE_DOM_REQUIRES_SMOKE', selector:'[data-message-id], [data-turn-id], [data-role="user"], [data-role="assistant"]'};
    return {name:'generic', maturity:'GENERIC_BEST_EFFORT', selector:'[data-message-id][data-message-author-role], [data-turn-id][data-message-author-role]'};
  }
  function parseTime(node) {
    const raw = node.querySelector?.('time[datetime]')?.getAttribute('datetime') || null;
    if (!raw) return {messageAt:null, raw:null, warning:null};
    const time = Date.parse(raw);
    return Number.isFinite(time) ? {messageAt:new Date(time).toISOString(), raw, warning:null} : {messageAt:null, raw, warning:'UNPARSED_MESSAGE_TIME'};
  }
  function explicitRole(node) {
    const direct = node.getAttribute('data-message-author-role') || node.getAttribute('data-message-role') || node.getAttribute('data-role');
    if (['user','assistant','system','tool'].includes(direct)) return direct;
    for (let parent=node.parentElement, i=0; parent && i<3; parent=parent.parentElement,i++) {
      const role=parent.getAttribute('data-message-author-role') || parent.getAttribute('data-message-role') || parent.getAttribute('data-role');
      if (['user','assistant','system','tool'].includes(role)) return role;
    }
    return 'unknown';
  }
  function messageID(node) {
    for (let owner=node, i=0; owner && i<3; owner=owner.parentElement,i++) {
      for (const attr of ['data-message-id','data-turn-id']) {
        const value=owner.getAttribute(attr);
        if (value && value.length<=256) return {id:value, attr};
      }
    }
    return {id:null, attr:null};
  }
  function observeMessages(doc=document, url=location.href, {max=MESSAGE_LIMIT}={}) {
    if (!Number.isInteger(max) || max<1 || max>MESSAGE_LIMIT) throw Error('INVALID_MESSAGE_LIMIT');
    const profile=siteProfile(url), found=[...doc.querySelectorAll(profile.selector)].filter(visible), records=[], warnings=['UNLOADED_HISTORY_NOT_OBSERVED',profile.maturity];
    const seenNodes=new Set();
    for (const node of found) {
      if (records.length>=max) { warnings.push('MESSAGE_LIMIT'); break; }
      if (seenNodes.has(node)) continue;seenNodes.add(node);
      const ident=messageID(node), role=explicitRole(node), time=parseTime(node);
      if (time.warning) warnings.push(time.warning);
      const text=typeof node.innerText==='string'?node.innerText:node.textContent||'';
      if (!text.trim()) continue;
      records.push({messageId:ident.id,messageIdSource:ident.attr,role,messageAt:time.messageAt,messageTimeRaw:time.raw,text});
    }
    if (!records.length) warnings.push('NO_STABLE_MESSAGES_USE_GENERIC_CAPTURE');
    if (records.some(r=>!r.messageId)) warnings.push('SOME_MESSAGES_WITHOUT_STABLE_ID');
    if (records.some(r=>r.role==='unknown')) warnings.push('SOME_ROLES_UNKNOWN');
    return {profile:profile.name, maturity:profile.maturity, coverage:'BEST_EFFORT', records, warnings:[...new Set(warnings)]};
  }
  function discover(doc = document) {
    const items = [], seen = new Set();
    const add = (kind, method, state, el, label, source = '') => {
      if (items.length >= LIMIT) return;
      const key = [kind, method, source, clean(label)].join('|');
      if (seen.has(key)) return;
      seen.add(key);
      items.push({id: `artifact-${items.length + 1}`, kind, method, state,
        label: clean(label) || `${kind} ${items.length + 1}`, source: clean(source)});
    };
    for (const link of doc.querySelectorAll('a[href],a[download]')) {
      if (!visible(link)) continue;
      const raw = link.getAttribute('href') || '';
      const label = link.getAttribute('download') || link.textContent || link.getAttribute('aria-label') || '';
      if (link.hasAttribute('download') || FILE_RE.test(raw) || FILE_RE.test(label)) {
        add('file-link', 'USER_DOWNLOAD_IMPORT', 'AVAILABLE', link, label, safeURL(raw, doc.baseURI));
      }
    }
    // Site-managed file cards/buttons are inventory only. No click, no URL guessing, no auth/cookie access.
    for (const control of doc.querySelectorAll('[data-file-id],button,[role="button"]')) {
      if (!visible(control)) continue;
      const label=control.getAttribute('aria-label') || control.getAttribute('title') || control.textContent || '';
      if (!control.hasAttribute('data-file-id') && !FILE_RE.test(label)) continue;
      add('file-link','USER_DOWNLOAD_IMPORT','NOT_READ',control,label,'');
    }
    for (const frame of doc.querySelectorAll('iframe,object,embed')) if (visible(frame)) {
      const raw = frame.getAttribute('src') || frame.getAttribute('data') || '';
      add('embedded-document', 'FRAME_ACCESS_OR_EXPORT', 'NOT_READ', frame,
        frame.getAttribute('title') || frame.getAttribute('aria-label') || frame.tagName, safeURL(raw, doc.baseURI));
    }
    for (const el of doc.querySelectorAll('details:not([open]),button[aria-expanded="false"],[role="button"][aria-expanded="false"]')) {
      if (!visible(el)) continue;
      const label = el.tagName === 'DETAILS' ? el.querySelector('summary')?.textContent : el.textContent || el.getAttribute('aria-label');
      if (el.tagName === 'DETAILS' || MORE_RE.test(label || '')) add('collapsed-content', 'USER_EXPAND_THEN_RECAPTURE', 'NOT_READ', el, label);
    }
    for (const el of doc.querySelectorAll('canvas,img,picture')) if (visible(el)) {
      const img = el.tagName === 'PICTURE' ? el.querySelector('img') : el;
      add(el.tagName === 'CANVAS' ? 'canvas' : 'image', 'SCREENSHOT_OR_OCR', 'TEXT_NOT_READ', el,
        img?.getAttribute('alt') || img?.getAttribute('aria-label') || el.tagName);
    }
    for (const el of doc.querySelectorAll('audio,video')) if (visible(el)) {
      add(el.tagName.toLowerCase(), 'TRANSCRIPT_OR_USER_EXPORT', 'TEXT_NOT_READ', el,
        el.getAttribute('aria-label') || el.getAttribute('title') || el.tagName);
    }
    for (const el of doc.querySelectorAll('.monaco-editor,.cm-editor,.ProseMirror,[contenteditable="true"]')) if (visible(el)) {
      add('editor', 'OBSERVE_VISIBLE_DOM_OR_EXPORT_ORIGINAL', 'VISIBLE_PART_ONLY', el,
        el.getAttribute('aria-label') || el.getAttribute('role') || 'Редактор');
    }
    return {schemaVersion: VERSION, limited: items.length >= LIMIT, items};
  }
  function summary(inventory) {
    if (!inventory?.items?.length) return ['SOURCE INVENTORY: no additional visible access points detected.'];
    const lines = [`SOURCE INVENTORY: ${inventory.items.length}${inventory.limited ? '+' : ''} access points; discovery is not content acquisition.`];
    for (const item of inventory.items) lines.push(`- ${item.id} | ${item.kind} | ${item.state} | ${item.method} | ${item.label}${item.source ? ` | ${item.source}` : ''}`);
    return lines;
  }
  globalThis.OCCArtifactInventory = Object.freeze({VERSION, LIMIT, MESSAGE_LIMIT, discover, summary, safeURL, siteProfile, observeMessages});
})();
