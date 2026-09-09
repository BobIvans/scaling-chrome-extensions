const $ = id => document.getElementById(id);
const MAX_BYTES = 2200000;
let raw = '';
let originalBytes = null;
let selectedCapture = null;
let filename = 'context.txt';
let revision = 0;
let operation = 0;
let clearEpoch = 0;
let edited = false;

const encode = text => new TextEncoder().encode(text);
async function sha(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
    .map(b => b.toString(16).padStart(2, '0')).join('');
}
async function updateMeta(label) {
  const current = ++revision;
  const bytes = originalBytes || encode(raw);
  const digest = await sha(bytes);
  if (current !== revision) return;
  $('meta').textContent = `${label} | ${bytes.byteLength.toLocaleString('ru-RU')} байт UTF-8 | SHA-256 ${digest}`;
  $('save').disabled = !bytes.byteLength;
}
function setText(text) { raw = text; $('text').value = text; }
function partialReason(capture) {
  if (capture.status !== 'PARTIAL') return capture.status === 'BEST_EFFORT' ? 'BEST_EFFORT не гарантирует полноту истории.' : '';
  return capture.warnings.find(w => /time|step|size|unsupported|bound|структур/i.test(w)) || 'Причина ограничения не записана и неизвестна.';
}
const artifactMethod = {
  USER_DOWNLOAD_IMPORT: 'скачать и импортировать по явному действию', FRAME_ACCESS_OR_EXPORT: 'открыть или экспортировать отдельно',
  USER_EXPAND_THEN_RECAPTURE: 'развернуть вручную и повторить сбор', SCREENSHOT_OR_OCR: 'снимок видимой области; OCR не включён',
  TRANSCRIPT_OR_USER_EXPORT: 'получить транскрипт или экспорт', OBSERVE_VISIBLE_DOM_OR_EXPORT_ORIGINAL: 'видимый DOM или исходный экспорт'
};
function showArtifacts(inventory) {
  const list = $('artifacts'); list.replaceChildren();
  const items = inventory?.items || [];
  for (const item of items) {
    const row = document.createElement('li');
    row.textContent = `${item.kind}: ${item.label} — ${item.state}; ${artifactMethod[item.method] || item.method}${item.source ? `; ${item.source}` : ''}`;
    list.append(row);
  }
  $('inventory').hidden = !items.length;
}
async function load() {
  const current = operation;
  const state = await chrome.runtime.sendMessage({target: 'worker', type: 'getState'});
  if (current !== operation || !state?.ok) return;
  clearEpoch = state.clearEpoch;
  selectedCapture = state.session || state.saved;
  if (selectedCapture) {
    setText(selectedCapture.text); originalBytes = null; edited = false;
    const place = state.session ? 'Временный исходный снимок (session)' : 'Сохранённый по согласию снимок (local)';
    $('status').textContent = `${place}. ${selectedCapture.status}. ${partialReason(selectedCapture)} ${state.lastError || ''}`.trim();
    $('persist').disabled = false;
    showArtifacts(selectedCapture.artifacts);
    await updateMeta(`Исходный снимок ${selectedCapture.captureId}`);
  } else {
    showArtifacts(null);
    $('status').textContent = state.lastError || 'Снимка нет. Соберите страницу или откройте UTF-8 файл.';
    $('save').disabled = true; $('persist').disabled = true;
  }
}

$('text').addEventListener('input', () => {
  raw = $('text').value; originalBytes = null; edited = true;
  void updateMeta('ИЗМЕНЁННЫЙ текст — не байты исходного снимка/файла');
});
$('copy').onclick = async () => {
  if (!raw) { $('status').textContent = 'Нечего копировать.'; return; }
  $('copy').disabled = true;
  try {
    let result;
    try { await navigator.clipboard.writeText(raw); result = {ok: true}; }
    catch { result = await chrome.runtime.sendMessage({target: 'worker', type: 'copy', text: raw}); }
    if (!result?.ok) throw new Error(result?.error || 'Буфер обмена недоступен.');
    $('status').textContent = 'Текст скопирован.';
  } catch (error) { $('status').textContent = `Не скопировано: ${error.message}. Скачивание остаётся доступно.`; }
  finally { $('copy').disabled = false; }
};
$('open').onclick = () => $('file').click();
$('file').onchange = async () => {
  const file = $('file').files[0]; if (!file) return;
  const current = ++operation; setText(''); originalBytes = null; selectedCapture = null; edited = false; revision++;
  showArtifacts(null);
  try {
    if (file.size > MAX_BYTES) throw new Error('Файл превышает предел 2 200 000 байт; усечение не выполнялось.');
    const bytes = new Uint8Array(await file.arrayBuffer()); if (current !== operation) return;
    const text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
    if (text.includes('\u0000')) throw new Error('Похоже на бинарный или UTF-16 файл, а не UTF-8.');
    originalBytes = bytes; filename = file.name; setText(text);
    $('status').textContent = `Открыт ${filename}. До правки скачиваются исходные байты, включая BOM и CRLF/LF.`;
    $('persist').disabled = true; await updateMeta('Исходный импортированный UTF-8 файл');
  } catch (error) { if (current === operation) $('status').textContent = `Файл не открыт: ${error.message}`; }
  finally { $('file').value = ''; }
};
function downloadBytes(bytes, name) {
  const url = URL.createObjectURL(new Blob([bytes], {type: 'text/plain;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
$('save').onclick = async () => {
  if (!raw && !originalBytes?.byteLength) { $('status').textContent = 'Нечего скачивать.'; return; }
  $('save').disabled = true;
  try {
    if (selectedCapture && !edited) {
      const result = await chrome.runtime.sendMessage({target: 'worker', type: 'downloadStored', captureId: selectedCapture.captureId, revision: selectedCapture.revision});
      if (!result?.ok) throw new Error(result?.error || 'Загрузка не началась.');
      $('status').textContent = 'Загрузка исходного снимка начата; это ещё не подтверждение записи файла.';
    } else {
      const bytes = originalBytes || encode(raw);
      const name = edited ? filename.replace(/\.txt$/i, '') + '_EDITED.txt' : filename;
      downloadBytes(bytes, name); $('status').textContent = edited ? 'Запрошено скачивание ИЗМЕНЁННОГО текста.' : 'Запрошено скачивание исходных байтов файла.';
    }
  } catch (error) { $('status').textContent = `Не скачано: ${error.message}`; }
  finally { $('save').disabled = false; }
};
$('persist').onclick = async () => {
  if (!selectedCapture || edited) { $('status').textContent = 'Сохранить можно только выбранный неизменённый снимок.'; return; }
  if (!confirm('Приватный текст останется в chrome.storage.local на этом компьютере после перезапуска. Продолжить?')) return;
  $('persist').disabled = true;
  const result = await chrome.runtime.sendMessage({target: 'worker', type: 'persist', captureId: selectedCapture.captureId,
    revision: selectedCapture.revision, clearEpoch});
  $('status').textContent = result?.ok ? 'Снимок сохранён по вашему согласию на этом компьютере.' : `Не сохранено: ${result?.error || 'неизвестная ошибка'}. Предыдущая копия не удалялась.`;
  $('persist').disabled = false;
};
$('clear').onclick = async () => {
  operation++;
  const result = await chrome.runtime.sendMessage({target: 'worker', type: 'clear'});
  if (!result?.ok) { $('status').textContent = `Не удалено: ${result?.error}`; return; }
  clearEpoch = result.clearEpoch; setText(''); originalBytes = null; selectedCapture = null; edited = false; revision++;
  showArtifacts(null);
  $('meta').textContent = ''; $('save').disabled = true; $('persist').disabled = true;
  $('status').textContent = 'Временный и сохранённый текст удалены. Уже скачанные файлы и системный буфер обмена не удалены.';
};
void load();
