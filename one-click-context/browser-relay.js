/* OCC Browser Relay: injected only into tabs/origins explicitly authorized by the user. */
(() => {
  const VERSION = '1.0.0';
  if (globalThis.__occBrowserRelay?.version === VERSION) return;
  const refs = new Map();
  const reverse = new WeakMap();
  let serial = 0;
  const MAX_ELEMENTS = 350;
  const INTERACTIVE = [
    'a[href]','button','input','textarea','select','summary','details','[contenteditable="true"]',
    '[role="button"]','[role="link"]','[role="textbox"]','[role="checkbox"]','[role="radio"]',
    '[role="combobox"]','[role="option"]','[role="menuitem"]','[role="tab"]','[tabindex]'
  ].join(',');

  function sensitive(el) {
    if (!(el instanceof Element)) return false;
    const type = (el.getAttribute('type') || '').toLowerCase();
    const autocomplete = (el.getAttribute('autocomplete') || '').toLowerCase();
    const name = `${el.getAttribute('name') || ''} ${el.id || ''} ${el.getAttribute('aria-label') || ''}`.toLowerCase();
    return type === 'password' || /(?:current-password|new-password|one-time-code|cc-number|cc-csc)/.test(autocomplete) ||
      /(?:password|passwd|\botp\b|one.?time|recovery phrase|seed phrase|private key|secret key)/.test(name);
  }

  function visible(el) {
    if (!(el instanceof Element) || !el.isConnected) return false;
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return false;
    for (let cur = el; cur && cur instanceof Element; cur = cur.parentElement || cur.getRootNode()?.host) {
      const css = getComputedStyle(cur);
      if (css.display === 'none' || css.visibility === 'hidden' || css.visibility === 'collapse') return false;
      if (cur.hidden || cur.getAttribute('aria-hidden') === 'true' || cur.hasAttribute('inert')) return false;
    }
    return true;
  }

  function roots(root = document) {
    const result = [root];
    const stack = root instanceof Document ? [...root.documentElement.querySelectorAll('*')] : [...root.querySelectorAll('*')];
    for (const el of stack) if (el.shadowRoot) result.push(el.shadowRoot);
    return result;
  }

  function allInteractive() {
    const out = [];
    const seen = new Set();
    for (const root of roots()) {
      for (const el of root.querySelectorAll(INTERACTIVE)) {
        if (seen.has(el) || !visible(el)) continue;
        seen.add(el); out.push(el);
        if (out.length >= MAX_ELEMENTS) return out;
      }
    }
    return out;
  }

  function refFor(el) {
    let ref = reverse.get(el);
    if (!ref) { ref = `@e${++serial}`; reverse.set(el, ref); }
    refs.set(ref, el);
    return ref;
  }

  function label(el) {
    const direct = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('placeholder') || '';
    const labelled = el.getAttribute('aria-labelledby')?.split(/\s+/).map(id => document.getElementById(id)?.innerText || '').join(' ') || '';
    const text = direct || labelled || el.innerText || el.textContent || '';
    return String(text).replace(/\s+/g, ' ').trim().slice(0, 240);
  }

  function role(el) {
    return el.getAttribute('role') || ({A:'link',BUTTON:'button',INPUT:'input',TEXTAREA:'textbox',SELECT:'select',SUMMARY:'summary'}[el.tagName] || el.tagName.toLowerCase());
  }

  function currentValue(el) {
    if (sensitive(el)) return '';
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) return String(el.value || '').slice(0, 400);
    if (el.isContentEditable) return String(el.innerText || '').slice(0, 400);
    return '';
  }

  function pageText(maxChars) {
    const text = String(document.body?.innerText || document.documentElement?.innerText || '')
      .replace(/\u00a0/g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{4,}/g, '\n\n\n').trim();
    return text.length > maxChars ? text.slice(0, maxChars) + '\n\n[OCC SNAPSHOT TRUNCATED]' : text;
  }

  function snapshot(options = {}) {
    refs.clear();
    const elements = allInteractive().map(el => {
      const rect = el.getBoundingClientRect();
      const item = {ref: refFor(el), role: role(el), text: label(el), disabled: !!el.disabled,
        x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height)};
      const value = currentValue(el); if (value) item.value = value;
      if (sensitive(el)) item.sensitive = true;
      if (el instanceof HTMLAnchorElement && el.href) item.href = el.href.slice(0, 1000);
      return item;
    });
    return {
      version: VERSION, url: location.href, title: document.title,
      viewport: {width: innerWidth, height: innerHeight, x: scrollX, y: scrollY,
        documentWidth: document.documentElement.scrollWidth, documentHeight: document.documentElement.scrollHeight},
      text: pageText(Math.max(5000, Math.min(Number(options.maxChars) || 50000, 120000))),
      elements, truncatedElements: elements.length >= MAX_ELEMENTS
    };
  }

  function resolve(ref) {
    const el = refs.get(String(ref || ''));
    if (!el || !el.isConnected || !visible(el)) throw new Error('STALE_OR_UNKNOWN_REF: take a new snapshot.');
    return el;
  }

  function targetText(ref) {
    const el = resolve(ref);
    return `${label(el)} ${el.getAttribute('name') || ''} ${el.id || ''}`.trim().slice(0, 500);
  }

  function setNativeValue(el, value) {
    if (sensitive(el)) throw new Error('SENSITIVE_FIELD_BLOCKED');
    if (el instanceof HTMLInputElement) {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
      setter ? setter.call(el, value) : (el.value = value);
    } else if (el instanceof HTMLTextAreaElement) {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      setter ? setter.call(el, value) : (el.value = value);
    } else if (el.isContentEditable) el.textContent = value;
    else throw new Error('TARGET_NOT_TYPEABLE');
    el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: value}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
  }

  async function act(action) {
    if (!action || typeof action !== 'object') throw new Error('ACTION_REQUIRED');
    const kind = String(action.action || '').toLowerCase();
    if (kind === 'snapshot') return {ok: true, snapshot: snapshot(action)};
    if (kind === 'click') {
      const el = resolve(action.ref); if (sensitive(el)) throw new Error('SENSITIVE_CONTROL_BLOCKED');
      el.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'}); el.focus({preventScroll: true}); el.click();
      return {ok: true, result: `clicked ${action.ref}`};
    }
    if (kind === 'type') {
      const el = resolve(action.ref); el.scrollIntoView({block: 'center', behavior: 'instant'}); el.focus({preventScroll: true});
      setNativeValue(el, String(action.text ?? '')); return {ok: true, result: `typed ${String(action.text ?? '').length} chars into ${action.ref}`};
    }
    if (kind === 'press') {
      const el = action.ref ? resolve(action.ref) : (document.activeElement instanceof Element ? document.activeElement : document.body);
      if (sensitive(el)) throw new Error('SENSITIVE_CONTROL_BLOCKED');
      const key = String(action.key || 'Enter').slice(0, 40);
      el.focus?.({preventScroll: true});
      for (const type of ['keydown','keypress','keyup']) el.dispatchEvent(new KeyboardEvent(type, {key, code: key === 'Enter' ? 'Enter' : key, bubbles: true, cancelable: true}));
      if (key === 'Enter' && el instanceof HTMLInputElement && el.form) el.form.requestSubmit?.();
      return {ok: true, result: `pressed ${key}${action.ref ? ` on ${action.ref}` : ''}`};
    }
    if (kind === 'scroll') {
      const amount = Math.max(100, Math.min(Math.abs(Number(action.amount) || 700), Math.max(innerHeight * 3, 3000)));
      const delta = String(action.direction || 'down').toLowerCase() === 'up' ? -amount : amount;
      scrollBy({top: delta, behavior: 'instant'}); return {ok: true, result: `scrolled ${delta}`};
    }
    throw new Error('UNSUPPORTED_CONTENT_ACTION');
  }

  globalThis.__occBrowserRelay = Object.freeze({version: VERSION, snapshot, act, targetText});
})();
