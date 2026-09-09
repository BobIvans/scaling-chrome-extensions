const encoder = new TextEncoder();
export const DEFAULT_PART_BYTES = 180000;
export const MIN_PART_BYTES = 16000;
export const MAX_PART_BYTES = 500000;

export function byteLength(text) {
  return encoder.encode(String(text)).length;
}

export async function sha256(text) {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(String(text)));
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

function validateBudget(value) {
  const n = Number(value);
  if (!Number.isInteger(n) || n < MIN_PART_BYTES || n > MAX_PART_BYTES) {
    throw new Error(`Размер части должен быть ${MIN_PART_BYTES}-${MAX_PART_BYTES} байт.`);
  }
  return n;
}

function largestPrefix(text, budget) {
  if (byteLength(text) <= budget) return text.length;
  let lo = 1;
  let hi = text.length;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (byteLength(text.slice(0, mid)) <= budget) lo = mid;
    else hi = mid - 1;
  }
  let end = lo;
  if(end<text.length&&end>0&&text.charCodeAt(end-1)>=0xD800&&text.charCodeAt(end-1)<=0xDBFF&&text.charCodeAt(end)>=0xDC00&&text.charCodeAt(end)<=0xDFFF)end--;
  if (end > 1024) {
    const start = Math.max(0, end - 4096);
    const window = text.slice(start, end);
    for (const marker of ['\n\n=== ', '\n\n', '\n']) {
      const at = window.lastIndexOf(marker);
      if (at > 512) {
        const candidate = start + at + marker.length;
        if (candidate > 0 && byteLength(text.slice(0, candidate)) <= budget) {
          end = candidate;
          break;
        }
      }
    }
  }
  return end;
}

export async function splitBundle(text, options = {}) {
  const input = String(text || '');
  if (!input) throw new Error('Нет текста для разбиения.');
  const budget = validateBudget(options.partBytes ?? DEFAULT_PART_BYTES);
  const label = String(options.label || 'context_bundle').slice(0, 80);
  const payloads = [];
  let rest = input;
  while (rest) {
    const end = largestPrefix(rest, budget);
    if (!end) throw new Error('Не удалось безопасно разбить текст.');
    const body = rest.slice(0, end);
    payloads.push({index: payloads.length + 1, text: body, bytes: byteLength(body), sha256: await sha256(body)});
    rest = rest.slice(end);
    if (payloads.length > 1000) throw new Error('Слишком много частей.');
  }
  return {
    kind: 'occ-context-bundle-parts',
    version: 1,
    label,
    createdAt: new Date().toISOString(),
    partBytes: budget,
    totalBytes: byteLength(input),
    wholeSha256: await sha256(input),
    parts: payloads.map(({index, bytes, sha256}) => ({index, bytes, sha256})),
    payloads
  };
}

export function rejoin(payloads) {
  if (!Array.isArray(payloads) || !payloads.length) throw new Error('Нет частей.');
  const sorted = [...payloads].sort((a, b) => a.index - b.index);
  sorted.forEach((part, i) => {
    if (part.index !== i + 1 || typeof part.text !== 'string') throw new Error('Нарушена последовательность частей.');
  });
  return sorted.map(part => part.text).join('');
}
