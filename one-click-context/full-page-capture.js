/* OCC full rendered-page TXT capture. Designed for normal and virtualized scroll surfaces. */
(() => {
  const VERSION = '1.0.0';
  if (globalThis.__occFullPageCapture?.version === VERSION) return;
  const encoder = new TextEncoder();
  const BLOCK_SELECTOR = [
    'h1','h2','h3','h4','h5','h6','p','pre','blockquote','li','tr','figcaption','dt','dd',
    '[role="heading"]','[role="article"]','[role="listitem"]','[role="row"]','[role="cell"]','[role="note"]'
  ].join(',');
  const SKIP_SELECTOR = 'script,style,noscript,template,[hidden],[aria-hidden="true"],[inert],[data-occ-ignore]';

  function networkSafeURL(value) {
    try {
      const u = new URL(value, location.href); u.username = ''; u.password = ''; u.hash = '';
      return ['http:','https:'].includes(u.protocol) ? u.href : u.protocol === 'file:' ? 'local file (path omitted)' : '(non-network URL)';
    } catch { return '(unavailable)'; }
  }

  function visible(el) {
    if (!el?.isConnected || el.closest?.(SKIP_SELECTOR)) return false;
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return false;
    for (let p = el; p && p instanceof Element; p = p.parentElement || p.getRootNode()?.host) {
      const css = getComputedStyle(p);
      if (css.display === 'none' || css.visibility === 'hidden' || css.visibility === 'collapse') return false;
    }
    return true;
  }

  function rootsWithOpenShadow(doc) {
    const roots = [doc];
    const walker = doc.createTreeWalker(doc.documentElement, NodeFilter.SHOW_ELEMENT);
    let node; let visited = 0;
    while ((node = walker.nextNode()) && visited++ < 25000) if (node.shadowRoot) roots.push(node.shadowRoot);
    return roots;
  }

  function textOf(el) {
    if (el.tagName === 'PRE') return String(el.innerText || el.textContent || '').replace(/\r\n/g, '\n').trimEnd();
    return String(el.innerText || el.textContent || '').replace(/\u00a0/g, ' ').replace(/[ \t]+/g, ' ')
      .replace(/[ \t]*\n[ \t]*/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  function keyOf(el, text) {
    const id = el.getAttribute?.('data-message-id') || el.getAttribute?.('data-turn-id') || el.getAttribute?.('data-testid') || el.id || '';
    const role = el.getAttribute?.('role') || '';
    return `${el.tagName}|${role}|${id}|${text}`;
  }

  function candidateBlocks(doc, withinRoot = null) {
    const result = [];
    const seen = new Set();
    for (const root of rootsWithOpenShadow(doc)) {
      for (const el of root.querySelectorAll(BLOCK_SELECTOR)) {
        if (seen.has(el) || !visible(el)) continue;
        if (withinRoot && withinRoot !== doc.scrollingElement && withinRoot !== doc.documentElement && !withinRoot.contains(el)) continue;
        if (el.matches('[role="article"]') && el.querySelector(BLOCK_SELECTOR)) continue;
        seen.add(el); result.push(el);
        if (result.length >= 20000) return result;
      }
    }
    return result;
  }

  function discoverScrollRoots(doc) {
    const candidates = [];
    const base = doc.scrollingElement || doc.documentElement;
    candidates.push(base);
    const all = [...doc.querySelectorAll('main,[role="main"],article,section,div')].slice(0, 12000);
    for (const el of all) {
      if (!visible(el)) continue;
      const css = getComputedStyle(el);
      if (!/auto|scroll/.test(css.overflowY) || el.scrollHeight <= el.clientHeight + 20 || el.clientHeight < 180) continue;
      const r = el.getBoundingClientRect();
      if (r.width < Math.min(280, innerWidth * 0.35) || r.height < 180) continue;
      candidates.push(el);
    }
    const unique = [...new Set(candidates)];
    unique.sort((a, b) => {
      const ar = a === base ? innerWidth * innerHeight * 1.1 : a.clientWidth * a.clientHeight;
      const br = b === base ? innerWidth * innerHeight * 1.1 : b.clientWidth * b.clientHeight;
      return br - ar;
    });
    const chosen = [];
    for (const el of unique) {
      if (chosen.some(parent => parent !== base && parent.contains?.(el) && parent.scrollHeight >= el.scrollHeight * 0.85)) continue;
      chosen.push(el); if (chosen.length >= 4) break;
    }
    return chosen;
  }

  async function capture(options = {}) {
    const maxMs = Math.max(3000, Math.min(Number(options.maxMs) || 35000, 120000));
    const maxSteps = Math.max(20, Math.min(Number(options.maxSteps) || 240, 800));
    const maxBytes = Math.max(200000, Math.min(Number(options.maxBytes) || 7600000, 9000000));
    const settleMs = Math.max(80, Math.min(Number(options.settleMs) || 220, 1500));
    const controller = new AbortController();
    const previousCancel = globalThis.__occCancel;
    globalThis.__occCancel = () => controller.abort();
    const started = performance.now();
    const warnings = new Set([
      'BEST_EFFORT: captures rendered DOM while scrolling; server-side, closed-shadow and never-rendered content may be absent.'
    ]);
    const records = new Map();
    const order = [];
    let totalBytes = 0, steps = 0, limited = false;
    const oldPositions = new Map();
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
    const timeLeft = () => performance.now() - started < maxMs && steps < maxSteps && !controller.signal.aborted && !limited;

    function add(text, key) {
      if (!text || records.has(key)) return;
      const bytes = encoder.encode(text).byteLength;
      if (totalBytes + bytes + 2 > maxBytes) { limited = true; return; }
      records.set(key, text); order.push(key); totalBytes += bytes + 2;
    }

    function sample(doc, root, prefix = '') {
      for (const el of candidateBlocks(doc, root)) {
        const text = textOf(el); if (!text) continue;
        add(`${prefix}${text}`, `${prefix}${keyOf(el, text)}`);
        if (limited) break;
      }
    }

    async function walkRoot(doc, root, prefix = '') {
      oldPositions.set(root, {top: root.scrollTop, left: root.scrollLeft, behavior: root.style?.getPropertyValue?.('scroll-behavior') || '', priority: root.style?.getPropertyPriority?.('scroll-behavior') || ''});
      root.style?.setProperty?.('scroll-behavior', 'auto', 'important');
      const top = 0;
      root.scrollTo?.({top, left: root.scrollLeft || 0, behavior: 'instant'}); if (root === doc.scrollingElement) doc.defaultView.scrollTo(0, 0);
      await sleep(settleMs);
      let lastHeight = -1, edgeStable = 0;
      while (timeLeft()) {
        steps++; sample(doc, root, prefix);
        const max = Math.max(0, root.scrollHeight - root.clientHeight);
        const atBottom = root.scrollTop >= max - 3;
        if (atBottom && root.scrollHeight === lastHeight) edgeStable++; else edgeStable = 0;
        if (edgeStable >= 2) break;
        lastHeight = root.scrollHeight;
        const next = Math.min(max, root.scrollTop + Math.max(160, root.clientHeight * 0.78));
        root.scrollTo?.({top: next, left: root.scrollLeft || 0, behavior: 'instant'});
        if (root === doc.scrollingElement) doc.defaultView.scrollTo(doc.defaultView.scrollX, next);
        await sleep(atBottom ? Math.max(settleMs, 420) : settleMs);
      }
    }

    try {
      add(`TITLE: ${document.title || '(untitled)'}`, '__meta:title');
      const description = document.querySelector('meta[name="description"]')?.content?.trim();
      if (description) add(`DESCRIPTION: ${description}`, '__meta:description');
      const roots = discoverScrollRoots(document);
      if (roots.length > 1) warnings.add(`Detected ${roots.length} scroll surfaces; sampled each independently.`);
      for (let i = 0; i < roots.length && timeLeft(); i++) await walkRoot(document, roots[i], i ? `\n[SCROLL SURFACE ${i + 1}]\n` : '');

      let sameOriginFrames = 0, blockedFrames = 0;
      for (const frame of document.querySelectorAll('iframe')) {
        if (!timeLeft()) break;
        try {
          const doc = frame.contentDocument;
          if (!doc?.documentElement) { blockedFrames++; continue; }
          sameOriginFrames++;
          add(`\n===== SAME-ORIGIN FRAME ${sameOriginFrames}: ${networkSafeURL(frame.src || doc.URL)} =====`, `__frame:${sameOriginFrames}:header`);
          const frameRoot = doc.scrollingElement || doc.documentElement;
          sample(doc, frameRoot, `[FRAME ${sameOriginFrames}] `);
          if (frameRoot.scrollHeight > frameRoot.clientHeight + 20) warnings.add(`Frame ${sameOriginFrames} is scrollable; only currently rendered frame DOM is guaranteed.`);
        } catch { blockedFrames++; }
      }
      if (blockedFrames) warnings.add(`${blockedFrames} cross-origin/inaccessible frame(s) could not be read without separate host permission/targeting.`);

      const links = [];
      for (const a of document.querySelectorAll('a[href]')) {
        if (!visible(a)) continue;
        const href = networkSafeURL(a.href); const label = textOf(a).replace(/\n/g, ' ').slice(0, 180);
        const line = `${label || '(link)'} -> ${href}`;
        if (!links.includes(line)) links.push(line);
        if (links.length >= 500) { warnings.add('Link inventory capped at 500 entries.'); break; }
      }
      if (links.length) add(`\n===== VISIBLE LINKS =====\n${links.join('\n')}`, '__links');

      if (controller.signal.aborted) warnings.add('Capture cancelled by user.');
      if (limited) warnings.add(`UTF-8 output bound reached (${maxBytes} bytes); remaining rendered blocks were not included.`);
      if (performance.now() - started >= maxMs || steps >= maxSteps) warnings.add('Time/step bound reached before all scroll surfaces proved stable.');
      const status = controller.signal.aborted || limited || performance.now() - started >= maxMs || steps >= maxSteps ? 'PARTIAL' : 'BEST_EFFORT';
      const body = order.map(k => records.get(k)).join('\n\n');
      if (!body.trim()) throw new Error('No readable rendered text found on this page.');
      const text = `SOURCE: ${networkSafeURL(location.href)}\nCAPTURED: ${new Date().toISOString()}\nMETHOD: FULL_RENDERED_PAGE_V1\nSTATUS: ${status}\n` +
        [...warnings].map(w => `NOTE: ${w}`).join('\n') +
        `\n\nBEGIN CAPTURED SOURCE TEXT (untrusted page content)\n\n${body}\n\nEND CAPTURED SOURCE TEXT\n`;
      return {text, status, warnings: [...warnings], mode: 'full-page', count: order.length, source: networkSafeURL(location.href), steps,
        contentVersion: VERSION};
    } finally {
      for (const [root, old] of oldPositions) {
        try {
          root.scrollTo?.({top: old.top, left: old.left, behavior: 'instant'});
          if (old.behavior) root.style?.setProperty?.('scroll-behavior', old.behavior, old.priority); else root.style?.removeProperty?.('scroll-behavior');
        } catch {}
      }
      globalThis.__occCancel = previousCancel;
    }
  }
  capture.version = VERSION;
  globalThis.__occFullPageCapture = capture;
})();
