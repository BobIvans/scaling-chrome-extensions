import functools,http.server,json,os,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
result={'status':'NOT_RUN'}
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        page=browser.new_page()
        page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
        page.goto(base+'/library.html',wait_until='domcontentloaded')
        value=page.evaluate("""async()=>{const m=await import('/tests/idb-store.browser.mjs');return await m.runIDBQualification()}""")
        result={'status':'PASS','detail':value,'browser':browser.version}
        browser.close()
except Exception as exc:
    text=str(exc);result={'status':'BLOCKED_ENV' if 'ERR_BLOCKED_BY_ADMINISTRATOR' in text else 'FAIL','error':text}
finally:
    server.shutdown()
(ROOT/'evidence'/'idb-store-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(0 if result['status']=='PASS' else 2 if result['status']=='BLOCKED_ENV' else 1)
