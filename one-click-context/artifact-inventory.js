/* Deterministic, read-only inventory of visible web content access points. */
(() => {
  const VERSION = 2;
  const LIMIT = 100;
  const FILE_RE = /\.(txt|md|csv|tsv|jsonl?|ya?ml|xml|html?|pdf|docx?|pptx?|xlsx?|ods|odt|odp|rtf|zip|tar|gz|png|jpe?g|webp|gif|svg|mp3|wav|m4a|mp4|webm|mov)(?:$|[?#])/i;
  const MORE_RE = /(?:show|view|read|load|expand|continue|more|open|показать|развернуть|читать|загрузить|открыть|ещ[её])/i;
  const COPY_RE = /^(?:copy|copy code|copy text|копировать|скопировать|копировать код|копировать текст)$/i;
  const FEED_TYPES = new Set(['application/rss+xml', 'application/atom+xml', 'application/feed+json']);
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
    const add = (kind, method, state, el, label, source = '', decision = 'OBSERVE_ONLY', reason = '', requiresUser = true) => {
      if (items.length >= LIMIT) return;
      const key = [kind, method, source, clean(label)].join('|');
      if (seen.has(key)) return;
      seen.add(key);
      items.push({id: `artifact-${items.length + 1}`, kind, method, state,
        label: clean(label) || `${kind} ${items.length + 1}`, source: clean(source),
        decision, reason: clean(reason), requiresUser});
    };
    for (const feed of doc.querySelectorAll('link[rel~="alternate"][href]')) {
      const type = clean(feed.getAttribute('type')).toLowerCase();
      if (FEED_TYPES.has(type)) add('feed-link', 'CONNECT_READ_ONLY_FEED', 'AVAILABLE', feed,
        feed.getAttribute('title') || type, safeURL(feed.getAttribute('href'), doc.baseURI), 'IMPORT_FEED',
        'Лента подходит для дешёвого отслеживания новых записей по URL и времени.');
    }
    for (const script of doc.querySelectorAll('script[type="application/ld+json"]')) {
      const raw = script.textContent || ''; if (!raw.trim() || raw.length > 65536) continue;
      let label = 'JSON-LD';
      try { const parsed = JSON.parse(raw); const first = Array.isArray(parsed) ? parsed[0] : parsed; label = clean(first?.['@type']) || label; } catch { label = 'JSON-LD (invalid)'; }
      add('structured-data', 'READ_STRUCTURED_METADATA', 'METADATA_ONLY', script, label, '', 'INCLUDE_STRUCTURED_RECORD',
        'Структурированные метаданные могут дополнять наблюдённый текст; исходный блок хранится отдельно при импорте.', false);
    }
    for (const link of doc.querySelectorAll('a[href],a[download]')) {
      if (!visible(link)) continue;
      const raw = link.getAttribute('href') || '';
      const label = link.getAttribute('download') || link.textContent || link.getAttribute('aria-label') || '';
      if (link.hasAttribute('download') || FILE_RE.test(raw) || FILE_RE.test(label)) {
        add('file-link', 'USER_DOWNLOAD_IMPORT', 'AVAILABLE', link, label, safeURL(raw, doc.baseURI), 'IMPORT_ORIGINAL',
          'Исходные байты файла надёжнее текста карточки или снимка экрана.');
      }
    }
    for (const control of doc.querySelectorAll('button,[role="button"]')) {
      if (!visible(control)) continue;
      const label = control.getAttribute('aria-label') || control.getAttribute('title') || control.textContent || '';
      if (FILE_RE.test(label)) add('file-control', 'USER_OPEN_OR_DOWNLOAD', 'CONTROL_NOT_USED', control, label, '',
        'OPEN_OR_DOWNLOAD_ORIGINAL', 'Кнопка похожа на файловую карточку, но её действие не выполнялось.');
      else if (COPY_RE.test(clean(label))) add('copy-control', 'OBSERVE_DOM_FIRST', 'CONTROL_NOT_USED', control, label, '',
        'USE_OBSERVED_TEXT', 'Кнопка Copy не нужна, если связанный текст уже присутствует в наблюдённом DOM.');
    }
    for (const frame of doc.querySelectorAll('iframe,object,embed')) if (visible(frame)) {
      const raw = frame.getAttribute('src') || frame.getAttribute('data') || '';
      add('embedded-document', 'FRAME_ACCESS_OR_EXPORT', 'NOT_READ', frame,
        frame.getAttribute('title') || frame.getAttribute('aria-label') || frame.tagName, safeURL(raw, doc.baseURI),
        'OPEN_OR_EXPORT_SEPARATELY', 'Содержимое frame не принадлежит DOM выбранной области.');
    }
    for (const el of doc.querySelectorAll('details:not([open]),button[aria-expanded="false"],[role="button"][aria-expanded="false"]')) {
      if (!visible(el)) continue;
      const label = el.tagName === 'DETAILS' ? el.querySelector('summary')?.textContent : el.textContent || el.getAttribute('aria-label');
      if (el.tagName === 'DETAILS' || MORE_RE.test(label || '')) add('collapsed-content', 'USER_EXPAND_THEN_RECAPTURE', 'NOT_READ', el, label, '',
        'EXPAND_AND_RECAPTURE', 'Скрытый блок не читается до явного раскрытия пользователем.');
    }
    for (const el of doc.querySelectorAll('button:not([aria-expanded="false"]),[role="button"]:not([aria-expanded="false"])')) {
      if (!visible(el)) continue; const label = el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '';
      if (MORE_RE.test(label) && !FILE_RE.test(label) && !COPY_RE.test(clean(label))) add('long-text-control', 'USER_EXPAND_THEN_RECAPTURE', 'CONTROL_NOT_USED', el, label, '',
        'EXPAND_AND_RECAPTURE', 'Элемент похож на открытие большого текста; автоматический клик запрещён.');
    }
    for (const el of doc.querySelectorAll('canvas,img,picture,svg[role="img"]')) if (visible(el)) {
      const img = el.tagName === 'PICTURE' ? el.querySelector('img') : el;
      add(el.tagName === 'CANVAS' ? 'canvas' : 'image', 'SCREENSHOT_OR_OCR', 'TEXT_NOT_READ', el,
        img?.getAttribute('alt') || img?.getAttribute('aria-label') || el.tagName, '', 'CAPTURE_VISIBLE_SCREEN',
        'PNG сохраняет вид; текст внутри изображения требует отдельного OCR.');
    }
    for (const el of doc.querySelectorAll('audio,video')) if (visible(el)) {
      add(el.tagName.toLowerCase(), 'TRANSCRIPT_OR_USER_EXPORT', 'TEXT_NOT_READ', el,
        el.getAttribute('aria-label') || el.getAttribute('title') || el.tagName, '', 'EXPORT_TRANSCRIPT_OR_MEDIA',
        'Медиаплеер не доказывает наличие доступного транскрипта.');
    }
    for (const el of doc.querySelectorAll('.monaco-editor,.cm-editor,.ProseMirror,[contenteditable="true"]')) if (visible(el)) {
      add('editor', 'OBSERVE_VISIBLE_DOM_OR_EXPORT_ORIGINAL', 'VISIBLE_PART_ONLY', el,
        el.getAttribute('aria-label') || el.getAttribute('role') || 'Редактор', '', 'EXPORT_ORIGINAL_TEXT',
        'Виртуализированный редактор может держать вне DOM невидимые строки.');
    }
    return {schemaVersion: VERSION, limited: items.length >= LIMIT, items};
  }
  function summary(inventory) {
    if (!inventory?.items?.length) return ['SOURCE INVENTORY: no additional visible access points detected.'];
    const lines = [`SOURCE INVENTORY: ${inventory.items.length}${inventory.limited ? '+' : ''} access points; discovery is not content acquisition.`];
    for (const item of inventory.items) lines.push(`- ${item.id} | ${item.kind} | ${item.state} | ${item.method} | DECISION ${item.decision || 'OBSERVE_ONLY'} | ${item.label}${item.source ? ` | ${item.source}` : ''}`);
    return lines;
  }
  globalThis.OCCArtifactInventory = Object.freeze({VERSION, LIMIT, discover, summary, safeURL});
})();
