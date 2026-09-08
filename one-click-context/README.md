# One Click Context — local Chrome extension starter

A separate utility, not a change to studious-pancake or PR #471.
No account, backend, AI model, build step, automatic paste, or automatic Send.

## Install once

1. Extract ONE_CLICK_CONTEXT_EXTENSION.zip to a normal folder.
2. Open chrome://extensions in desktop Chrome and enable Developer mode.
3. Choose Load unpacked and select the one-click-context folder containing manifest.json.
4. Pin One Click Context from Chrome's Extensions menu.

If Chrome is managed and installation is blocked, administrator approval may be
needed. Do not disable enterprise policies. This starter is not a Web Store listing.

## Daily use

Select text and click the pinned action: copy only the selection.
With no selection, clicking captures a text/plain document or performs a bounded,
best-effort upward/downward DOM scan of the main page/conversation. Then paste
manually with Ctrl+V. Alt+Shift+C invokes the action when Chrome grants that shortcut;
customize it at chrome://extensions/shortcuts if another app uses it.

A second action click or Escape cancels a running scan without copying it.
Right-click the action -> Preview / copy last capture / open TXT opens the local
viewer. The Options page does the same. Import a local UTF-8 TXT, MD, PATCH, DIFF,
JSON or code file there; no blanket file-system access is required for selection
through the file picker. A rendered file URL may need Chrome's separate file-URL
access setting; the importer avoids that requirement.

Badges: OK = selection/raw text copied; DOM = best-effort DOM copied; PART = partial
text copied; STOP = cancelled and clipboard unchanged; COPY = clipboard requires
the visible preview; ERR = failed. BEST_EFFORT does not mean complete history.

## Scope and implementation

- Manifest V3, activeTab, scripting, clipboardWrite, offscreen, storage, contextMenus.
- No persistent host permissions, <all_urls>, cookies, history, debugger, clipboardRead,
  remote JavaScript, analytics or HTTP client calls.
- content.js reads DOM text and preserves code whitespace, backslashes and diff signs.
  It uses role attributes when supplied by the DOM and otherwise generic main content.
- background.js dispatches user actions; offscreen.js writes to the clipboard and
  checks success. Failed writes open the local viewer. No automatic AI submission.
- viewer.html imports UTF-8 text with strict decoding and displays original-byte
  SHA-256 where Web Crypto is available. Original-byte download is preserved until
  editing. Clipboard line endings can be normalized by the OS/browser.
- Temporary captures use chrome.storage.session. Clear removes extension-session
  data, NOT the system clipboard or downloaded files.

Default traversal limits: 20,000 ms, 160 steps, approximately 2 MB of captured
content. These are checked between DOM samples, not a preemptive hard CPU deadline.
Large/complex pages can take longer within a sample. Limits yield explicit warnings;
a huge code block is omitted whole rather than silently cut in the middle.
The initial scroll OFFSET is restored best-effort, not necessarily the same visual
message when the website rearranges its virtualized content.

## Important limitations

This is a tested starter, NOT a guarantee for every website. It has not been tested
inside the user's signed-in ChatGPT, Codex or DeepSeek sessions. Role-based selectors
are heuristics, not verified site-specific adapters. Sites can change their markup.

Unloaded server history, folded text, image/canvas text, inaccessible iframes,
closed shadow roots, browser PDF viewers and Chrome-protected pages are not fully
captured. OCR is deliberately not included. Reverse-layout scrollers are marked
partial. Recycled DOM elements without stable message IDs can create overlaps;
these are disclosed, not claimed as a complete reconstructed history.

Repeated messages with distinct IDs are preserved. A shared parent/container ID
is not accepted as a message ID. Missing IDs and disconnected samples are warned
about. The extension does not click arbitrary page controls or execute page text.

No content is transmitted by the extension. Scrolling can cause the WEBSITE to
load more data over the network. Visible chats can contain passwords or API keys;
excluding form fields is NOT secret detection. Review before sharing elsewhere.

## Tests and actual evidence

Run JavaScript syntax checks and orchestration unit tests:

    node --check background.js
    node --check content.js
    node --check offscreen.js
    node --check viewer.js
    node --test tests/background.test.cjs

Run browser fixtures with a locally installed Chromium and Python Playwright:

    CHROMIUM_PATH=/usr/bin/chromium python tests/run_browser_tests.py

On other operating systems set CHROMIUM_PATH to that browser's executable.
The extension itself needs neither Node, Python nor Playwright; these are test tools.
Install test dependencies: python -m pip install -r tests/requirements.txt
Then: python -m playwright install chromium
Use CHROMIUM_PATH to select a browser with extension-loading support.
The test runner uses an isolated temporary profile and synthetic local pages.
Clipboard tests overwrite the system clipboard with synthetic text.

See evidence/REVIEW_STATUS.txt and browser-tests.json for current results, browser
version, source hashes and untested areas.

## Development

No build step. Chunking and last-assistant copy are deferred. Add site adapters
only after observing authorized site markup. Cancellation prevents copying until
clipboard dispatch begins; an already submitted OS clipboard write cannot be undone.

## Official references


https://developer.chrome.com/docs/extensions/develop/concepts/activeTab
https://developer.chrome.com/docs/extensions/reference/api/scripting
https://developer.chrome.com/docs/extensions/reference/api/offscreen
https://developer.chrome.com/docs/extensions/reference/permissions-list
https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world
https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/innerText
https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText
