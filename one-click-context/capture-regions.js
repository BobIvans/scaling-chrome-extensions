/*
 * OCC capture-region selector. It only discovers and selects DOM regions.
 * Extraction, scrolling, storage, clipboard and downloads remain owned by OCC.
 */
(function (scope) {
  'use strict';
  const CHAT = '[data-message-author-role], [data-message-role], [data-role="user"], [data-role="assistant"]';
  const MAIN = 'main, [role="main"]';
  const EDITOR = '.cm-editor, .monaco-editor, .ProseMirror';
  const DOCUMENT = '[role="document"], [role="dialog"], aside, [role="complementary"], ' + EDITOR + ', textarea[readonly]';
  const NAV = 'nav, [role="navigation"], [role="menu"], [role="menubar"]';
  const IGNORE = '[hidden], [aria-hidden="true"], [inert], [data-occ-ignore], script, style, template, noscript, ' + NAV;
  const CONTROL = 'button, [role="button"], input, select, [role="toolbar"], header, footer';
  const COMPOSER = '#prompt-textarea, [data-testid="prompt-textarea"], [data-testid="composer"]';
  const TEXT = 'p, pre, h1, h2, h3, h4, h5, h6, table, blockquote, li';
  const LIMITS = Object.freeze({nodes: 12000, surfaces: 40, depth: 256});
  const ERR = code => Object.assign(new Error(code), {code});

  function parent(el) { return el?.parentElement || el?.getRootNode?.()?.host || null; }
  function within(root, node) {
    for (let e = node?.nodeType === 1 ? node : node?.parentElement, n = 0; e && n < LIMITS.depth; e = parent(e), n++) {
      if (e === root) return true;
    }
    return false;
  }
  function ancestor(el, selector) {
    for (let n = 0; el && n < LIMITS.depth; el = parent(el), n++) if (el.matches?.(selector)) return el;
    return null;
  }
  function visible(el) {
    if (!el?.isConnected || ancestor(el, IGNORE)) return false;
    for (let e = el, n = 0; e && n < LIMITS.depth; e = parent(e), n++) {
      const css = e.ownerDocument.defaultView.getComputedStyle(e);
      if (css.display === 'none' || css.visibility === 'hidden' || css.visibility === 'collapse' || css.opacity === '0') return false;
    }
    return !!el.getClientRects().length;
  }
  function nodes(doc, maxNodes) {
    const all = [], warnings = [], stack = doc.documentElement ? [doc.documentElement] : [];
    while (stack.length && all.length < maxNodes) {
      const el = stack.pop(); all.push(el);
      if (el.matches(IGNORE + ', iframe, object, embed')) continue;
      const children = el.shadowRoot ? [...el.shadowRoot.children, ...el.children] : [...el.children];
      for (let i = children.length - 1; i >= 0; i--) stack.push(children[i]);
    }
    if (stack.length) warnings.push('DISCOVERY_NODE_LIMIT');
    return {all, warnings};
  }
  function commonContainer(messages) {
    for (let p = parent(messages[0]), n = 0; p && n < LIMITS.depth; p = parent(p), n++) {
      if (messages.every(m => within(p, m))) return p;
    }
    return null;
  }
  function scrollRoot(root) {
    const choices = [root], walker = root.ownerDocument.createTreeWalker(root, 1);
    while (choices.length < 5000) { const next = walker.nextNode(); if (!next) break; choices.push(next); }
    return choices.filter(e => visible(e) && !ancestor(e, COMPOSER) &&
      /auto|scroll/.test(e.ownerDocument.defaultView.getComputedStyle(e).overflowY) &&
      e.scrollHeight > e.clientHeight + 4 && e.clientHeight > 50)
      .sort((a, b) => b.clientWidth * b.clientHeight - a.clientWidth * a.clientHeight)[0] || root;
  }
  function usableText(el, all) {
    if (el.matches('textarea[readonly]')) return el.value.length > 0;
    if (el.matches(EDITOR)) return (el.textContent || '').trim().length > 0;
    return all.some(n => within(el, n) && n.matches(TEXT) && visible(n) &&
      !ancestor(n, CONTROL + ', form, ' + COMPOSER) && (n.textContent || '').trim().length > 0);
  }
  function documentSignal(el) {
    if (!el.matches('aside, [role="complementary"]')) return true;
    return !!el.querySelector('pre, textarea[readonly], [role="document"], .cm-editor, .monaco-editor, .ProseMirror');
  }

  let serial = 0;
  function discover(doc, options = {}) {
    if (!doc?.documentElement) throw ERR('DOCUMENT_REQUIRED');
    const maxNodes = options.maxNodes ?? LIMITS.nodes;
    if (!Number.isInteger(maxNodes) || maxNodes < 1 || maxNodes > LIMITS.nodes) throw ERR('INVALID_NODE_LIMIT');
    const {all, warnings} = nodes(doc, maxNodes);
    const nonce = Array.from(scope.crypto.getRandomValues(new Uint32Array(4)), n => n.toString(16)).join('-');
    const scanId = 'scan-' + (++serial) + '-' + nonce;
    const live = all.filter(visible), surfaces = [], frames = [];
    let counter = 0;
    const add = (root, kind, reasons, notes = [], messageRoots = []) => {
      if (!root || surfaces.some(s => s.root === root && s.kind === kind)) return;
      if (surfaces.length >= LIMITS.surfaces) { warnings.push('DISCOVERY_SURFACE_LIMIT'); return; }
      surfaces.push({id: scanId + ':region-' + (++counter), root, document: doc, kind, reasons,
        warnings: [...notes], messageRoots, scrollRoot: scrollRoot(root), excludeRoots: []});
    };
    if (doc.contentType === 'text/plain') {
      add(doc.body, 'document', ['PLAIN_TEXT_DOCUMENT'], ['DOM_TEXT_IS_NOT_ORIGINAL_FILE_BYTES']);
    } else {
      const messageNodes = live.filter(e => e.matches(CHAT) && !ancestor(e, COMPOSER));
      const mains = live.filter(e => e.matches(MAIN));
      const assigned = new Set();
      mains.sort((a, b) => within(a, b) ? 1 : within(b, a) ? -1 : 0);
      for (const main of mains) {
        const ms = messageNodes.filter(m => within(main, m) && !assigned.has(m));
        if (ms.length) { add(main, 'chat', ['MESSAGE_MARKERS'], [], ms); ms.forEach(m => assigned.add(m)); }
      }
      const rest = messageNodes.filter(m => !assigned.has(m));
      if (rest.length) add(commonContainer(rest), 'chat', ['COMMON_MESSAGE_CONTAINER'], [], rest);

      const possibleDocs = live.filter(e => e.matches(DOCUMENT) && documentSignal(e) &&
        !ancestor(e, COMPOSER + ', form') && !ancestor(e, CHAT) && usableText(e, live) &&
        !messageNodes.some(m => within(e, m)));
      const docs = possibleDocs.filter(e => !possibleDocs.some(p => p !== e && within(p, e)));
      for (const el of docs) {
        if (messageNodes.some(m => within(el, m))) continue;
        add(el, 'document', ['DOCUMENT_OR_EDITOR_REGION'],
          [el.matches(EDITOR) || el.querySelector(EDITOR) ? 'EDITOR_DOM_MAY_BE_VIRTUALIZED' : 'DOM_COVERAGE_NOT_PROVEN',
            'DOCUMENT_HINT_IS_HEURISTIC']);
      }
      for (const el of live.filter(e => e.matches('pre, article') && !ancestor(e, CHAT + ', form, ' + COMPOSER))) {
        if (surfaces.some(s => within(s.root, el))) continue;
        if (usableText(el, live)) add(el, 'document', ['STANDALONE_TEXT_REGION'], ['DOCUMENT_HINT_IS_HEURISTIC']);
      }
      for (const main of mains) {
        if (surfaces.some(s => s.root === main || within(main, s.root) || within(s.root, main))) continue;
        if (usableText(main, live)) add(main, 'page', ['MEANINGFUL_MAIN'], ['DOM_COVERAGE_NOT_PROVEN']);
      }
    }
    for (const el of live.filter(e => e.matches('iframe, object, embed'))) {
      const r = el.getBoundingClientRect(); if (r.width < 80 || r.height < 60) continue;
      frames.push({element: el, id: scanId + ':embedded-' + frames.length, status: 'NOT_READ',
        reason: 'EXPLICIT_FRAME_TARGET_AND_PERMISSION_REQUIRED'});
    }
    for (const s of surfaces) {
      s.excludeRoots = live.filter(e => e.matches(NAV + ', ' + CONTROL + ', form, ' + COMPOSER) && within(s.root, e));
      for (const other of surfaces) if (other !== s && within(s.root, other.root)) s.excludeRoots.push(other.root);
      s.includeRoots = s.kind === 'chat' && s.messageRoots.length ? [...s.messageRoots] : [s.root];
    }
    return {schema: 1, scanId, document: doc, surfaces, frames,
      warnings: [...new Set(warnings)], nodesVisited: all.length};
  }
  function allowed(target, node) {
    return target.includeRoots.some(r => within(r, node)) && !target.excludeRoots.some(r => within(r, node)) &&
      !ancestor(node?.nodeType === 1 ? node : node?.parentElement, IGNORE);
  }
  function select(scan, mode = 'auto', selectedId = null) {
    if (!scan || scan.schema !== 1) throw ERR('SCAN_REQUIRED');
    if (!['auto', 'chat', 'document', 'chat+document', 'selected'].includes(mode)) throw ERR('INVALID_MODE');
    const valid = scan.surfaces.filter(s => s.root.ownerDocument === scan.document && visible(s.root));
    const chats = valid.filter(s => s.kind === 'chat'), docs = valid.filter(s => s.kind === 'document');
    const pages = valid.filter(s => s.kind === 'page');
    let chosen = [], state = 'READY';
    if (mode === 'selected') {
      chosen = valid.filter(s => s.id === selectedId); if (!chosen.length) state = 'STALE_OR_UNKNOWN_REGION';
    } else if (mode === 'document') {
      if (docs.length === 1) chosen = docs;
      else state = docs.length > 1 ? 'NEEDS_SELECTION' : scan.frames.length ? 'NEEDS_FRAME_ACCESS' : 'DOCUMENT_NOT_FOUND';
    } else if (mode === 'chat') {
      chosen = chats; if (!chosen.length) state = 'CHAT_NOT_FOUND';
    } else if (mode === 'chat+document') {
      if (docs.length > 1) state = 'NEEDS_SELECTION';
      else { chosen = [...chats, ...docs]; if (!chosen.length) state = scan.frames.length ? 'NEEDS_FRAME_ACCESS' : 'NO_SOURCE'; }
    } else if (docs.length === 1 && !scan.frames.length) chosen = docs;
    else if (docs.length > 1 || scan.frames.length) state = 'NEEDS_SELECTION';
    else if (chats.length) chosen = chats;
    else if (pages.length === 1) chosen = pages;
    else state = pages.length > 1 ? 'NEEDS_SELECTION' : 'NO_SOURCE';
    const warnings = [...scan.warnings, ...chosen.flatMap(s => s.warnings)];
    if (scan.frames.length) warnings.push('EMBEDDED_CONTENT_NOT_READ');
    return {state, mode, targets: chosen, warnings: [...new Set(warnings)], frameCount: scan.frames.length, coverage: 'UNKNOWN'};
  }
  function describe(scan) {
    return {schema: scan.schema, scanId: scan.scanId, nodesVisited: scan.nodesVisited, warnings: scan.warnings,
      surfaces: scan.surfaces.map(s => ({id: s.id, kind: s.kind, reasons: s.reasons, warnings: s.warnings,
        messageCount: s.messageRoots.length, tag: s.root.tagName.toLowerCase(), excludes: s.excludeRoots.length})),
      frames: scan.frames.map(f => ({id: f.id, status: f.status, reason: f.reason}))};
  }
  scope.OCCCaptureRegions = Object.freeze({discover, select, allowed, describe, within, LIMITS});
})(globalThis);
