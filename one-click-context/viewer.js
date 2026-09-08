const $ = id => document.getElementById(id);
let raw = '', original = null, filename = 'context.txt', revision = 0, operation = 0;
const MAX_BYTES = 2200000;
async function sha(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2, '0')).join('');
}
async function updateMeta(label) {
  const current = ++revision, bytes = original || new TextEncoder().encode(raw);
  const length = Array.from(raw).length;
  const digest = globalThis.crypto?.subtle ? await sha(bytes) : 'unavailable in this browser context';
  if (current !== revision) return;
  $('meta').textContent = `${label} | ${length.toLocaleString()} Unicode code points | ${bytes.byteLength.toLocaleString()} bytes | SHA-256 ${digest}`;
}
function setText(text) { raw = text; $('text').value = text; }
async function load() {
  const current = operation;
  const {capture, lastError} = await chrome.storage.session.get(['capture', 'lastError']);
  if (current !== operation) return;
  if (capture) {
    setText(capture.text);
    $('status').textContent = lastError || `${capture.status}: ${capture.count} captured blocks. Review before sharing.`;
    await updateMeta(capture.mode);
  } else { $('status').textContent = lastError || 'No capture yet. Open a TXT file, or use the toolbar action on a page.'; }
}
$('text').addEventListener('input', () => { raw = $('text').value; original = null; void updateMeta('Edited text — not original file bytes'); });
$('copy').onclick = async () => {
  if (!raw) { $('status').textContent = 'Nothing to copy.'; return; }
  $('copy').disabled = true;
  try {
    let result;
    try { await navigator.clipboard.writeText(raw); result = {ok: true}; }
    catch { result = await chrome.runtime.sendMessage({target: 'worker', type: 'copy', text: raw}); }
    if (!result?.ok) throw new Error(result?.error || 'Clipboard write failed.');
    $('status').textContent = 'Copied. Switch to your AI and paste with Ctrl+V.';
  } catch (e) { $('status').textContent = `Not copied: ${e.message}. Select the text and press Ctrl+C manually.`; $('text').focus(); $('text').select(); }
  finally { $('copy').disabled = false; }
};
$('open').onclick = () => $('file').click();
$('file').onchange = async () => {
  const file = $('file').files[0]; if (!file) return;
  const current = ++operation;
  setText(''); original = null; revision++; $('meta').textContent = '';
  try {
    if (file.size > MAX_BYTES) throw new Error('File is larger than this starter\'s 2.2 MB bound. No text was truncated.');
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (current !== operation) return;
    const text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
    if (text.includes('\u0000')) throw new Error('This appears to be binary or UTF-16, not UTF-8 text.');
    original = bytes; filename = file.name; setText(text);
    $('status').textContent = `Opened ${filename}. Click Copy all text.`;
    await updateMeta('Original UTF-8 file');
  } catch (e) { if (current !== operation) return; $('status').textContent = `File not opened: ${e.message}`; }
  finally { $('file').value = ''; }
};
$('save').onclick = () => {
  const url = URL.createObjectURL(new Blob([original || new TextEncoder().encode(raw)], {type: 'text/plain;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
};
$('clear').onclick = async () => {
  operation++;
  await chrome.runtime.sendMessage({target: 'worker', type: 'clear'});
  setText(''); original = null; revision++; $('meta').textContent = ''; $('status').textContent = 'Local capture cleared. System clipboard is unchanged.';
};
void load();
