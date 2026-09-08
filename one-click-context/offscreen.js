// Offscreen documents expose runtime messaging and DOM APIs, not tabs/scripting.
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message?.target !== 'offscreen' || message.type !== 'copy' || sender.id !== chrome.runtime.id || sender.tab) return false;
  if (sender.url && sender.url !== chrome.runtime.getURL('background.js')) return false;
  const buffer = document.getElementById('buffer');
  if (typeof message.text !== 'string') { respond({ok: false, error: 'Clipboard text must be a string.'}); return false; }
  (async () => {
    try {
      try {
        await navigator.clipboard.writeText(message.text);
      } catch {
        // Chromium's documented offscreen clipboard sample uses this legacy fallback.
        // Success must be checked; selection alone is not a successful copy.
        buffer.value = message.text;
        buffer.focus(); buffer.select();
        if (!document.execCommand('copy')) throw new Error('The browser blocked clipboard copying.');
      }
      respond({ok: true});
    } catch (error) { respond({ok: false, error: error.message}); }
    finally { buffer.value = ''; }
  })();
  return true;
});
