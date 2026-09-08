/* One Click Context: runs in the extension's isolated world, on invocation only. */
(() => {
  if (globalThis.__occCapture) return;
  const OMIT = new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','HEAD','BUTTON',
    'INPUT','TEXTAREA','SELECT','OPTION','SVG','CANVAS','IFRAME','OBJECT','EMBED']);
  const BLOCK = new Set(['DIV','P','SECTION','ARTICLE','MAIN','ASIDE','HEADER','FOOTER',
    'H1','H2','H3','H4','H5','H6','UL','OL','LI','BLOCKQUOTE','PRE','TR']);
  const ROLE_SELECTOR = '[data-message-author-role], [data-message-role], [data-role="user"], [data-role="assistant"]';

  function excluded(el) {
    if (OMIT.has(el.tagName) || el.hasAttribute('data-occ-ignore') || el.hidden ||
        el.getAttribute('aria-hidden') === 'true' || el.isContentEditable ||
        ['textbox', 'toolbar', 'navigation'].includes(el.getAttribute('role'))) return true;
    const css = getComputedStyle(el);
    return css.display === 'none' || css.visibility === 'hidden' || css.visibility === 'collapse';
  }
  function visible(el) {
    if (!el.getClientRects().length) return false;
    for (let p = el; p; p = p.parentElement) if (excluded(p)) return false;
    return !el.closest('nav,aside,header,footer,[role="navigation"]');
  }
  function plain(node) {
    // Never whitespace-normalize a code block. Placeholders isolate it from prose cleanup.
    const protectedText = [];
    const nonce = `OCC${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`}`;
    function walk(n, code = false) {
      if (n.nodeType === Node.TEXT_NODE) return code ? n.data : n.data.replace(/\s+/g, ' ');
      if (n.nodeType !== Node.ELEMENT_NODE || excluded(n)) return '';
      if (n.tagName === 'BR') return '\n';
      if (n.tagName === 'PRE') {
        const root = n.querySelector('code') || n;
        const value = [...root.childNodes].map(c => walk(c, true)).join('');
        const token = `\uE000${nonce}:${protectedText.length}\uE001`;
        protectedText.push(value);
        return `\n\n${token}\n\n`;
      }
      const text = [...n.childNodes].map(c => walk(c, code)).join('');
      if (code) return text;
      if (n.tagName === 'TD' || n.tagName === 'TH') return text + '\t';
      return BLOCK.has(n.tagName) ? `\n${text}\n` : text;
    }
    let text = walk(node).replace(/[ \t]+\n/g, '\n').replace(/\n[ \t]+/g, '\n')
      .replace(/\n{3,}/g, '\n\n').trim();
    protectedText.forEach((value, i) => { text = text.replace(`\uE000${nonce}:${i}\uE001`, () => value); });
    return text;
  }
  function candidates() {
    const roles = [...document.querySelectorAll(ROLE_SELECTOR)].filter(visible);
    if (roles.length) {
      return {mode: 'role-annotated chat', nodes: roles.filter(el =>
        !roles.some(other => other !== el && other.contains(el)))};
    }
    const root = document.querySelector('main, [role="main"]') || document.body;
    const all = [...root.querySelectorAll('p,pre,li,h1,h2,h3,h4,h5,h6,blockquote,table')]
      .filter(el => visible(el) && !el.closest('nav,aside,header,footer,[role="navigation"],[data-occ-ignore]'));
    const chosen = new Set(all);
    const nodes = all.filter(el => {
      let p = el.parentElement;
      while (p && p !== root) { if (chosen.has(p)) return false; p = p.parentElement; }
      return true;
    });
    return {mode: 'generic DOM', nodes: nodes.length ? nodes : [root]};
  }
  function scrollOwner(nodes) {
    const first = nodes[0];
    if (first) {
      let p = first.parentElement;
      while (p && p !== document.body) {
        if (p.scrollHeight > p.clientHeight + 4 && p.clientHeight > 100 &&
            /auto|scroll/.test(getComputedStyle(p).overflowY) && nodes.every(n => p.contains(n))) return p;
        p = p.parentElement;
      }
    }
    const main = document.querySelector('main,[role="main"]');
    const all = [document.scrollingElement, ...[...document.body.querySelectorAll('*')].slice(0, 8000)];
    let best = document.scrollingElement, score = 0;
    for (const el of all) {
      if (!el || el.closest('[data-occ-ignore],nav,aside')) continue;
      if (el !== document.scrollingElement && !/auto|scroll/.test(getComputedStyle(el).overflowY)) continue;
      if (el.scrollHeight <= el.clientHeight + 4 || el.clientHeight < 140) continue;
      const r = el.getBoundingClientRect();
      if (r.width < Math.min(250, innerWidth / 2)) continue;
      const area = Math.min(r.width, innerWidth) * Math.min(r.height, innerHeight);
      const weight = main && (el === main || main.contains(el)) ? 1.3 : 1;
      if (area * weight > score) { score = area * weight; best = el; }
    }
    return best;
  }
  function sourceURL() {
    try { const u = new URL(location.href); return u.protocol === 'file:' ? 'local file (path omitted)' : u.origin === 'null' ? 'non-network document' : u.origin + u.pathname; }
    catch { return '(unavailable)'; }
  }
  function createUI(cancel) {
    document.querySelector('[data-occ-ignore="banner"]')?.remove();
    const host = document.createElement('div');
    host.setAttribute('data-occ-ignore', 'banner');
    host.style.cssText = 'position:fixed!important;right:18px!important;top:18px!important;z-index:2147483647!important';
    const shadow = host.attachShadow({mode: 'open'});
    const style = document.createElement('style');
    style.textContent = ':host{all:initial}section{font:14px/1.45 system-ui;color:#edf5ff;background:#152a42;border:1px solid #88a9cd;border-radius:12px;padding:14px 17px;max-width:390px;box-shadow:0 5px 25px #0004}.actions{display:flex;gap:7px;flex-wrap:wrap}button{font:inherit;margin:10px 0 0;padding:5px 12px;cursor:pointer}';
    const section = document.createElement('section');
    const text = document.createElement('div'); text.textContent = 'Capturing text locally…';
    const button = document.createElement('button'); button.textContent = 'Cancel (Esc)'; button.onclick = cancel;
    const actions = document.createElement('div'); actions.className = 'actions'; actions.append(button);
    section.append(text, actions); shadow.append(style, section); document.documentElement.append(host);
    return {host, text, button, actions};
  }
  function notify(message) {
    const old = document.querySelector('[data-occ-ignore="banner"]');
    const ui = old?.shadowRoot ? {host: old, text: old.shadowRoot.querySelector('section>div'),
      actions: old.shadowRoot.querySelector('.actions')} : createUI(() => {});
    ui.actions ||= ui.host.shadowRoot.querySelector('.actions');
    ui.actions.replaceChildren();
    ui.text.textContent = typeof message === 'string' ? message : message.text;
    function button(label, action) {
      const b = document.createElement('button'); b.textContent = label;
      b.addEventListener('click', async event => {
        if (!event.isTrusted || b.disabled) return;
        b.disabled = true;
        try { await action(); } finally { b.disabled = false; }
      });
      ui.actions.append(b);
    }
    if (message?.kind === 'capture') {
      const request = type => async () => {
        const result = await chrome.runtime.sendMessage({target: 'worker', type, captureId: message.captureId,
          revision: message.revision, userGesture: true});
        if (!result?.ok) ui.text.textContent = result?.error || 'Действие не выполнено.';
        else if (type === 'downloadCapture') ui.text.textContent += ' Загрузка начата; итог подтвердит Chrome.';
      };
      button('Скачать TXT', request('downloadCapture'));
      button('Просмотр', request('openCapture'));
    }
    button('Закрыть', async () => ui.host.remove());
  }
  globalThis.__occNotify = notify;
  globalThis.__occCancel = () => globalThis.__occController?.abort();
  globalThis.__occCapture = async (options = {}) => {
    if (globalThis.__occController) throw new Error('Capture already running in this tab.');
    const opt = {scroll: true, maxMs: 20000, maxSteps: 160, settleMs: 240, maxBytes: 2000000, ...options};
    try { await chrome.runtime.sendMessage({target: 'worker', type: 'captureContext', operationToken: opt.operationToken}); } catch {}
    const encoder = new TextEncoder();
    const selected = window.getSelection()?.toString() || '';
    const active = document.activeElement;
    if (selected && !(active instanceof HTMLInputElement && active.type === 'password')) {
      if (encoder.encode(selected).length > opt.maxBytes) throw new Error('Selection is too large. Use a local TXT file.');
      return {text: selected, status: 'SELECTION', mode: 'selection', warnings: [], source: sourceURL(), count: 1};
    }
    if (document.contentType === 'text/plain') {
      const text = document.body?.textContent ?? '';
      if (encoder.encode(text).length > opt.maxBytes) throw new Error('Text is too large. Use the local TXT importer.');
      return {text, status: 'RAW_TEXT', mode: 'text/plain DOM', count: 1, source: sourceURL(),
        warnings: ['Rendered text, not original file bytes. Use the TXT importer for byte checks.']};
    }
    const control = new AbortController(); globalThis.__occController = control;
    const keyHandler = e => { if (e.key === 'Escape') control.abort(); };
    document.addEventListener('keydown', keyHandler, true);
    const ui = createUI(() => control.abort());
    const warnings = new Set(['BEST_EFFORT: only observed DOM content; server-side or collapsed history is not verified.']);
    const initial = candidates();
    const root = scrollOwner(initial.nodes);
    const oldTop = root.scrollTop, oldLeft = root.scrollLeft;
    const oldBehavior = root.style.getPropertyValue('scroll-behavior');
    const oldPriority = root.style.getPropertyPriority('scroll-behavior');
    root.style.setProperty('scroll-behavior', 'auto', 'important');
    const records = new Map(), order = [], nodeIds = new WeakMap();
    let seq = 0, steps = 0, totalBytes = 0, tooLarge = false, status = 'BEST_EFFORT';
    let mode = initial.mode, lastProgress = 0;
    const start = performance.now();
    const timedOut = () => performance.now() - start >= opt.maxMs || steps >= opt.maxSteps;
    const alive = () => !control.signal.aborted && !timedOut() && !tooLarge;
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
    function stableID(el, role) {
      let owner = el;
      for (let i = 0; owner && i < (mode === 'role-annotated chat' ? 3 : 1); i++, owner = owner.parentElement) {
        // A shared scroll/container ID is NOT a message identity.
        if (owner !== el && owner.querySelectorAll(ROLE_SELECTOR).length !== 1) continue;
        for (const attr of ['data-message-id','data-turn-id','id']) {
          const value = owner.getAttribute(attr);
          if (value) return `stable:${role}:${attr}:${value}`;
        }
      }
      return null;
    }
    function observe(direction) {
      const sample = candidates(); mode = sample.mode;
      const ids = [], seen = new Set();
      for (const el of sample.nodes) {
        const text = plain(el);
        if (!text.trim()) continue;
        const rawRole = el.getAttribute('data-message-author-role') || el.getAttribute('data-message-role') || el.getAttribute('data-role');
        const role = ['user','assistant','system','tool'].includes(rawRole) ? rawRole : 'text';
        let id = stableID(el, role);
        if (!id) {
          const prev = nodeIds.get(el);
          if (prev && prev.text === text) id = prev.id;
          else {
            // Unidentified node recycling cannot be distinguished reliably from editing.
            if (prev) warnings.add('Changed/recycled nodes without stable IDs: revisions or overlaps may be included.');
            id = `node:${++seq}`; nodeIds.set(el, {id, text});
          }
          warnings.add('Some blocks have no stable message IDs; exact history coverage/order is unverified.');
        }
        if (seen.has(id)) {
          warnings.add('Duplicate DOM IDs detected; separate blocks were retained.');
          id += `:duplicate:${ids.length}`;
        }
        seen.add(id);
        const bytes = encoder.encode(text).length;
        const before = records.get(id);
        const afterTotal = totalBytes - (before?.bytes || 0) + bytes;
        if (afterTotal > opt.maxBytes) { tooLarge = true; break; }
        totalBytes = afterTotal;
        records.set(id, {id, role, text, bytes}); ids.push(id);
      }
      if (order.length && ids.length && !ids.some(id => order.includes(id))) {
        warnings.add('Disconnected DOM samples: order is inferred from scroll direction, not verified message indices.');
      }
      for (let i = 0; i < ids.length; i++) {
        const id = ids[i];
        if (order.includes(id)) continue;
        const next = ids.slice(i + 1).find(x => order.includes(x));
        const previous = ids.slice(0, i).reverse().find(x => order.includes(x));
        if (next) order.splice(order.indexOf(next), 0, id);
        else if (previous) order.splice(order.indexOf(previous) + 1, 0, id);
        else if (direction < 0) order.unshift(id);
        else order.push(id);
      }
      ui.text.textContent = `Capturing locally: ${order.length} blocks; ${Math.round(totalBytes / 1024)} KiB. ${direction < 0 ? 'Looking for older content…' : 'Reading downward…'}`;
      if (performance.now() - lastProgress > 1200) {
        lastProgress = performance.now();
        try { const pending = chrome.runtime.sendMessage({target: 'worker', type: 'progress', blocks: order.length, operationToken: opt.operationToken}); pending?.catch?.(() => {}); } catch {}
      }
      return `${order.length}/${totalBytes}/${root.scrollHeight}/${root.scrollTop}`;
    }
    async function walk(direction) {
      let previous = '', stable = 0;
      while (alive()) {
        steps++;
        const current = observe(direction);
        const max = Math.max(0, root.scrollHeight - root.clientHeight);
        const atEdge = direction < 0 ? root.scrollTop <= 2 : root.scrollTop >= max - 2;
        stable = atEdge && current === previous ? stable + 1 : 0;
        if (stable >= 3) return true;
        previous = current;
        const delta = Math.max(120, root.clientHeight * 0.72) * direction;
        root.scrollTo({top: Math.max(0, Math.min(max, root.scrollTop + delta)), behavior: 'instant'});
        await sleep(atEdge ? Math.max(opt.settleMs, 400) : opt.settleMs);
      }
      return false;
    }
    try {
      if (document.querySelector('iframe,object,embed')) warnings.add('Embedded documents/frames were not captured.');
      if (document.querySelector('canvas,img')) warnings.add('Text inside images/canvas was not read; OCR is not included.');
      warnings.add('Closed shadow roots and hidden/folded content are not expanded.');
      if (/column-reverse/.test(getComputedStyle(root).flexDirection)) {
        warnings.add('Reverse-layout scrolling is unsupported; only current DOM blocks were captured.');
        status = 'PARTIAL'; observe(1);
      } else if (opt.scroll && root.scrollHeight > root.clientHeight + 4) {
        const top = await walk(-1);
        const bottom = alive() ? await walk(1) : false;
        if (!top || !bottom) status = 'PARTIAL';
      } else { observe(1); warnings.add('No scroll traversal performed; currently loaded DOM only.'); }
      if (control.signal.aborted) { status = 'CANCELLED'; warnings.add('Cancelled: clipboard was not changed.'); }
      else if (tooLarge) { status = 'PARTIAL'; warnings.add('Content-size bound reached; omitted remaining blocks without cutting a code block.'); }
      else if (timedOut()) { status = 'PARTIAL'; warnings.add('Time/step bound reached; traversal was not complete.'); }
      const body = order.map((id, i) => {
        const rec = records.get(id);
        return mode === 'role-annotated chat' ? `[${rec.role.toUpperCase()} ${i + 1}]\n${rec.text}` : rec.text;
      }).join('\n\n');
      if (!body.trim() && status !== 'CANCELLED') throw new Error('No readable page text found. Try selecting text or importing TXT.');
      const text = `SOURCE: ${sourceURL()}\nCAPTURED: ${new Date().toISOString()}\nMETHOD: ${mode}\nSTATUS: ${status}\n` +
        [...warnings].map(w => `NOTE: ${w}`).join('\n') +
        '\n\nBEGIN CAPTURED SOURCE TEXT (untrusted page content)\n\n' + body + '\n\nEND CAPTURED SOURCE TEXT\n';
      return {text, status, warnings: [...warnings], mode, count: order.length, source: sourceURL(), steps};
    } finally {
      // A DOM reorder can prevent exact visual-position restoration; preserve the old offset best-effort.
      root.scrollTo({top: oldTop, left: oldLeft, behavior: 'instant'});
      if (oldBehavior) root.style.setProperty('scroll-behavior', oldBehavior, oldPriority);
      else root.style.removeProperty('scroll-behavior');
      document.removeEventListener('keydown', keyHandler, true);
      globalThis.__occController = null;
      ui.button.textContent = 'Dismiss'; ui.button.onclick = () => ui.host.remove();
    }
  };
})();
