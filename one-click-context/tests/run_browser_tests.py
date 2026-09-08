"""Synthetic Chromium fixtures; no live accounts. Requires playwright and Chromium.
Run: CHROMIUM_PATH=/usr/bin/chromium python tests/run_browser_tests.py
"""
import hashlib, http.server, json, os, tempfile, threading, time, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
BROWSER=os.environ.get('CHROMIUM_PATH')
SCRIPT=(ROOT/'content.js').read_text(encoding='utf-8'); RESULTS=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  body=b'<!doctype html><title>Local fixture</title><body></body>'; mime='text/html'
  if self.path=='/raw.txt': body='Привет 👋\n  + src/runtime_authority.py\\value\n'.encode(); mime='text/plain; charset=utf-8'
  if self.path=='/helper' and (ROOT.parent/'COPY_TO_CODEX.html').exists(): body=(ROOT.parent/'COPY_TO_CODEX.html').read_bytes();mime='text/html; charset=utf-8'
  self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(body)
 def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start();BASE=f'http://127.0.0.1:{server.server_port}'
def check(name,fn):
 start=time.monotonic()
 try:
  detail=fn();RESULTS.append(dict(test=name,status='PASS',seconds=round(time.monotonic()-start,3),detail=detail));print('PASS',name,flush=True)
 except Exception as e:
  if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(e) or (name=='loaded extension offscreen clipboard integration' and 'serviceworker' in str(e)):
   RESULTS.append(dict(test=name,status='BLOCKED_ENV',seconds=round(time.monotonic()-start,3),error=str(e)));print('BLOCKED_ENV',name,flush=True);return
  RESULTS.append(dict(test=name,status='FAIL',seconds=round(time.monotonic()-start,3),error=str(e),traceback=traceback.format_exc()));print('FAIL',name,str(e),flush=True)
def require(ok,detail='Assertion failed'):
 if not ok: raise AssertionError(detail)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=BROWSER,headless=True,args=['--no-sandbox']);version=browser.version
 ctx=browser.new_context(permissions=['clipboard-read','clipboard-write'])
 ctx.route('**/*',lambda r:r.continue_() if r.request.url.startswith(BASE) else r.abort());page=ctx.new_page()
 def fixture(html):
  global page
  page.close();page=ctx.new_page();page.set_content('<!doctype html><style>body{margin:0}pre{white-space:pre}</style>'+html);page.add_script_tag(content=SCRIPT)
 def capture(**opts): return page.evaluate('(o)=>__occCapture(o)',dict(scroll=False,**opts)) if 'scroll' not in opts else page.evaluate('(o)=>__occCapture(o)',opts)
 def code():
  fixture('<main><div data-message-id="1" data-message-author-role="assistant"><p>Patch:</p><pre><code>def x():\n    return r"src/runtime_authority.py\\value"\n+    next_line\n-    old_line\n</code></pre></div></main>')
  r=capture();require('def x():\n    return r"src/runtime_authority.py\\value"\n+    next_line\n-    old_line\n' in r['text'],r['text'])
 check('code whitespace / diff signs / literal backslashes',code)
 def duplicates():
  fixture('<main><p data-message-id="1" data-message-author-role="user">same</p><p data-message-id="2" data-message-author-role="user">same</p></main>');r=capture();require(r['count']==2,r);require(r['text'].count('\nsame')==2,r)
 check('identical messages with distinct IDs retained',duplicates)
 def ordered():
  fixture('<main>'+''.join(f'<p data-message-id="m{i}" data-message-author-role="user">Turn {i}</p>' for i in range(5))+'</main>');r=capture();positions=[r['text'].index(f'\nTurn {i}') for i in range(5)];require(positions==sorted(positions),r)
 check('initial DOM chronological order',ordered)
 def hidden_parent():
  fixture('<main><section aria-hidden="true"><p data-message-id="secret" data-message-author-role="user">ANCESTOR_SECRET</p></section><p data-message-id="ok" data-message-author-role="user">Visible</p></main>');r=capture();require('ANCESTOR_SECRET' not in r['text'],r)
 check('role messages under hidden ancestors excluded',hidden_parent)
 def controls():
  fixture('<nav><p>SIDEBAR_SECRET</p></nav><main><p>Visible text</p><input value="INPUT_SECRET"><textarea>TEXTAREA_SECRET</textarea><p hidden>HIDDEN_SECRET</p><script>const secret="SCRIPT_SECRET";</script><p aria-hidden="true">ARIA_SECRET</p><button>BUTTON_SECRET</button></main>');r=capture();require('Visible text' in r['text']);require('_SECRET' not in r['text'],r['text'])
 check('form values / hidden content / scripts / sidebar excluded',controls)
 def selection():
  fixture('<main><pre id="pick">  + literal\\_value\n  Привет 👋</pre><p>Not selected</p></main>');page.evaluate("const r=document.createRange();r.selectNodeContents(document.querySelector('#pick'));getSelection().removeAllRanges();getSelection().addRange(r)");r=capture();require(r['status']=='SELECTION');require(r['text']=='  + literal\\_value\n  Привет 👋',repr(r['text']))
 check('selection copied without wrappers or escaping',selection)
 def raw():
  page.goto(BASE+'/raw.txt');page.add_script_tag(content=SCRIPT);r=capture();require(r['status']=='RAW_TEXT');require(r['text']=='Привет 👋\n  + src/runtime_authority.py\\value\n',r)
 check('text/plain direct capture',raw)
 def nested():
  fixture('<main><div id="scroll" style="height:210px;overflow-y:auto">'+''.join(f'<p data-message-id="m{i}" data-message-author-role="user" style="height:70px">Message {i}</p>' for i in range(10))+'</div></main>');page.evaluate("document.querySelector('#scroll').scrollTop=130");r=capture(scroll=True,settleMs=10,maxMs=7000);require(r['count']==10,r);require(r['status']=='BEST_EFFORT',r);require(page.evaluate("document.querySelector('#scroll').scrollTop")==130)
 check('nested scroller and scroll-position restoration',nested)
 def prepend():
  fixture('<main><div id="scroll" style="height:210px;overflow-y:auto">'+''.join(f'<p data-message-id="m{i}" data-message-author-role="user" style="height:70px">Message {i}</p>' for i in range(3,8))+'</div></main>')
  page.evaluate('''const s=document.querySelector('#scroll');s.scrollTop=180;let added=false;s.addEventListener('scroll',()=>{if(s.scrollTop===0&&!added){added=true;const f=document.createDocumentFragment();for(let i=0;i<3;i++){let e=document.createElement('p');e.dataset.messageId='m'+i;e.dataset.messageAuthorRole='user';e.style.height='70px';e.textContent='Message '+i;f.append(e)}s.prepend(f)}})''')
  r=capture(scroll=True,settleMs=20,maxMs=7000);require(r['count']==8,r);positions=[r['text'].index(f'\nMessage {i}') for i in range(8)];require(positions==sorted(positions),r['text'])
 check('older messages prepended during capture',prepend)
 def virtual(stable=True):
  fixture('<main><div id="scroll" style="height:200px;overflow-y:auto;position:relative"><div style="height:1000px;position:relative" id="space"></div></div></main>')
  page.evaluate('''stable=>{const s=document.querySelector('#scroll'),space=document.querySelector('#space');for(let i=0;i<4;i++){let e=document.createElement('p');e.dataset.messageAuthorRole='assistant';e.style.cssText='position:absolute;height:80px;margin:0';space.append(e)}function render(){let first=Math.max(0,Math.min(6,Math.floor(s.scrollTop/100)));[...space.children].forEach((e,j)=>{let n=first+j;if(stable)e.dataset.messageId='m'+n;e.textContent='Virtual '+n;e.style.top=(n*100)+'px'})}s.addEventListener('scroll',render);s.scrollTop=350;render();}''',stable)
  r=capture(scroll=True,settleMs=30,maxMs=7000)
  if stable:
   require(r['count']==10,r);positions=[r['text'].index(f'\nVirtual {i}') for i in range(10)];require(positions==sorted(positions),r['text'])
  else: require(any('recycled' in w for w in r['warnings']),r)
 check('virtualized stable-ID messages accumulated in order',virtual)
 check('recycled nodes without IDs disclose uncertainty',lambda:virtual(False))
 def infinite():
  fixture('<main><div id="scroll" style="height:200px;overflow:auto">'+''.join(f'<p data-message-id="m{i}" data-message-author-role="user" style="height:100px">Row {i}</p>' for i in range(4))+'</div></main>')
  page.evaluate('''const s=document.querySelector('#scroll');let i=4;s.addEventListener('scroll',()=>{if(s.scrollTop+s.clientHeight>=s.scrollHeight-20){let e=document.createElement('p');e.dataset.messageId='m'+i;e.dataset.messageAuthorRole='user';e.style.height='100px';e.textContent='Row '+i++;s.append(e)}})''');r=capture(scroll=True,settleMs=10,maxMs=2000,maxSteps=18);require(r['status']=='PARTIAL',r);require(any('bound' in w for w in r['warnings']),r)
 check('infinite scroll bounded with PARTIAL status',infinite)
 def cancel():
  fixture('<main><div style="height:200px;overflow:auto">'+''.join(f'<p style="height:100px">row {i}</p>' for i in range(30))+'</div></main>');r=page.evaluate('''async()=>{const task=__occCapture({scroll:true,settleMs:40});setTimeout(()=>__occCancel(),70);return task}''');require(r['status']=='CANCELLED',r);require(page.evaluate('globalThis.__occController===null'))
 check('cancellation and controller cleanup',cancel)
 def size():
  fixture('<main><p>Short</p><pre><code>'+('a'*12000)+'</code></pre></main>');r=capture(maxBytes=1000);require(r['status']=='PARTIAL',r);require('Short' in r['text']);require('a'*100 not in r['text'])
 check('oversized code block omitted whole, never silently sliced',size)
 def role():
  fixture('<main><p data-message-id="1" data-message-author-role="alien">Not an assistant</p></main>');r=capture();require('[TEXT 1]' in r['text'],r);require('[ASSISTANT' not in r['text'])
 check('unknown roles not fabricated',role)
 def streaming():
  fixture('<main><div style="height:150px;overflow:auto"><p data-message-id="m1" data-message-author-role="assistant" style="height:500px">Original streaming</p></div></main>');page.evaluate("setTimeout(()=>document.querySelector('[data-message-id]').textContent='Updated streaming complete',100)");r=capture(scroll=True,settleMs=20,maxMs=6500);require(r['count']==1,r);require('Updated streaming complete' in r['text']);require('Original streaming' not in r['text'])
 check('stable-ID streaming update replaces same record',streaming)
 def viewer_import():
  page.goto(BASE)
  page.set_content((ROOT/'viewer.html').read_text(encoding='utf-8').replace('<script src="viewer.js"></script>',''))
  page.evaluate("window.chrome={storage:{session:{get:async()=>({})}},runtime:{sendMessage:async()=>({ok:true})}}")
  page.add_script_tag(content=(ROOT/'viewer.js').read_text(encoding='utf-8'))
  data=b'\xef\xbb\xbf'+'Привет English 👋\r\n--- a/file\r\n+++ b/file\r\n- old\r\n+    literal\\_value\r\n'.encode()
  page.set_input_files('#file',{'name':'unicode.txt','mimeType':'text/plain','buffer':data})
  page.wait_for_function("document.querySelector('#status').textContent.startsWith('Opened unicode')")
  require(page.evaluate('raw')==data.decode('utf-8'))
  page.wait_for_function("document.querySelector('#meta').textContent.includes('SHA-256')")
  require(hashlib.sha256(data).hexdigest() in page.locator('#meta').inner_text())
  with page.expect_download() as download: page.click('#save')
  require(Path(download.value.path()).read_bytes()==data)
  page.click('#copy');page.wait_for_function("document.querySelector('#status').textContent.startsWith('Copied')")
  require(page.evaluate('navigator.clipboard.readText()').replace('\r\n','\n')==data.decode('utf-8').replace('\r\n','\n'))
  page.set_input_files('#file',{'name':'bad.txt','mimeType':'text/plain','buffer':b'\xff\xfe\x00'})
  page.wait_for_function("document.querySelector('#status').textContent.startsWith('File not opened')")
  require(page.evaluate('raw')=='')
  return 'Real viewer source, localhost Web Crypto/clipboard/download; Chrome storage and runtime mocked. Not installed-extension evidence.'
 check('viewer UTF-8 BOM CRLF hash byte download copy invalid input',viewer_import)
 ctx.close();browser.close()
 def clipboard():
  with tempfile.TemporaryDirectory(prefix='occ-test-') as profile:
   ext=p.chromium.launch_persistent_context(profile,executable_path=BROWSER,headless=True,args=['--no-sandbox',f'--disable-extensions-except={ROOT}',f'--load-extension={ROOT}'])
   try:
    sw=ext.service_workers[0] if ext.service_workers else ext.wait_for_event('serviceworker',timeout=12000);extid=sw.url.split('/')[2];v=ext.new_page();v.goto(f'chrome-extension://{extid}/viewer.html');ext.grant_permissions(['clipboard-read','clipboard-write'])
    sample='Привет 👋\n+    exact\\_patch\n';result=v.evaluate("text=>chrome.runtime.sendMessage({target:'worker',type:'copy',text})",sample);require(result and result.get('ok'),result);require(v.evaluate('navigator.clipboard.readText()').replace('\r\n','\n')==sample);require(not v.evaluate("chrome.runtime.getManifest().permissions.includes('clipboardRead')"));
    data=b'\xef\xbb\xbf'+'Привет English 👋\r\n--- a/file\r\n+++ b/file\r\n- old\r\n+    literal\\_value\r\n'.encode()
    v.set_input_files('#file',{'name':'unicode.txt','mimeType':'text/plain','buffer':data})
    v.wait_for_function("() => document.querySelector('#status').textContent.startsWith('Opened unicode')")
    require(v.evaluate('raw')==data.decode('utf-8'))
    v.wait_for_function("() => document.querySelector('#meta').textContent.includes('SHA-256')")
    require(hashlib.sha256(data).hexdigest() in v.locator('#meta').inner_text())
    with v.expect_download() as download: v.click('#save')
    require(Path(download.value.path()).read_bytes()==data)
    v.click('#copy');v.wait_for_function("() => document.querySelector('#status').textContent.startsWith('Copied')")
    require(v.evaluate('navigator.clipboard.readText()').replace('\r\n','\n')==data.decode('utf-8').replace('\r\n','\n'))
    v.set_input_files('#file',{'name':'bad.txt','mimeType':'text/plain','buffer':b'\xff\xfe\x00'})
    v.wait_for_function("() => document.querySelector('#status').textContent.startsWith('File not opened')")
    require(v.evaluate('raw')=='')
    v.click('#clear');v.wait_for_function("() => document.querySelector('#status').textContent.startsWith('Local capture cleared')")
    require(v.evaluate('raw')=='')
    return 'Loaded extension worker/offscreen clipboard + viewer UTF-8/BOM/CRLF import, SHA-256, byte-identical download, Copy, invalid UTF-8 rejection and Clear. Clipboard comparison normalizes OS CRLF.'
   finally:ext.close()
 check('loaded extension offscreen clipboard integration',clipboard)
server.shutdown()
RESULTS.append(dict(test='Signed-in ChatGPT / Codex / DeepSeek adapters',status='NOT_RUN',error='No authorized signed-in site DOM inspected; generic semantic extraction only.'))
report=dict(browser=version,python=os.sys.version,test_basis='Synthetic local fixtures, not signed-in ChatGPT/Codex/DeepSeek.',toolbar_activeTab_real_click='NOT_TESTED: internal messaging / functions, not toolbar UI.',results=RESULTS,passed=sum(r['status']=='PASS' for r in RESULTS),failed=sum(r['status']=='FAIL' for r in RESULTS),skipped=0,blocked_env=sum(r['status']=='BLOCKED_ENV' for r in RESULTS),not_run=sum(r['status']=='NOT_RUN' for r in RESULTS),source_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(ROOT.glob('*')) if f.suffix in ['.js','.json','.html','.css']})
(ROOT/'evidence').mkdir(exist_ok=True);(ROOT/'evidence/browser-tests.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:report[k] for k in ['passed','failed','skipped','blocked_env','not_run','browser']}),flush=True)
raise SystemExit(1 if report['failed'] else 0)
