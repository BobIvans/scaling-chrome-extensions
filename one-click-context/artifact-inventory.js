/* Deterministic, read-only inventory of visible web content access points. */
(() => {
  const VERSION = 1;
  const LIMIT = 100;
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
      if (node.hidden || node.getAttribute('aria-hidden') === 'true') return false;
      const css = getComputedStyle(node);
      if (css.display === 'none' || css.visibility === 'hidden' || css.visibility === 'collapse') return false;
    }
    return true;
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
  globalThis.OCCArtifactInventory = Object.freeze({VERSION, LIMIT, discover, summary, safeURL});
})();
