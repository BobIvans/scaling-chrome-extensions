import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/'artifact-inventory.js').read_text(encoding='utf-8')
results=[]
def check(name,fn):
    try:
        detail=fn();results.append({'name':name,'status':'PASS','detail':detail});print('PASS',name)
    except Exception as e:
        results.append({'name':name,'status':'FAIL','error':str(e)});print('FAIL',name,str(e))
def require(v,msg='fixture assertion failed'):
    if not v: raise AssertionError(msg)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1200,'height':800})
    def fixture(html,url='https://chatgpt.com/c/fixture'):
        page.set_content('<style>body{font:16px sans-serif}button,a,p,div{display:block;min-height:20px}</style>'+html)
        page.add_script_tag(content=SCRIPT)
        # Tool functions accept the explicit URL; fixture does not claim live navigation.
        return url
    def chatgpt():
        url=fixture('<main><div data-message-id="m1" data-message-author-role="user">Question<time datetime="2026-09-09T01:02:03Z"></time></div><div data-message-id="m2" data-message-author-role="assistant"><pre>Answer + code_\\path</pre></div><div aria-hidden="true" data-message-id="hidden" data-message-author-role="assistant">SECRET</div></main>')
        r=page.evaluate('(u)=>OCCArtifactInventory.observeMessages(document,u)',url)
        require(r['profile']=='chatgpt');require(r['coverage']=='BEST_EFFORT');require(len(r['records'])==2,r)
        require(r['records'][0]['messageId']=='m1' and r['records'][0]['role']=='user',r)
        require(r['records'][0]['messageAt']=='2026-09-09T01:02:03.000Z',r)
        require('SECRET' not in json.dumps(r),r);require('UNLOADED_HISTORY_NOT_OBSERVED' in r['warnings'],r)
        return {'messages':2,'maturity':r['maturity']}
    check('ChatGPT observed message ids roles times and hidden exclusion',chatgpt)
    def repeated():
        url=fixture('<main><p data-message-id="a" data-message-author-role="user">same</p><p data-message-id="b" data-message-author-role="user">same</p></main>')
        r=page.evaluate('(u)=>OCCArtifactInventory.observeMessages(document,u)',url)
        require([x['messageId'] for x in r['records']]==['a','b'],r);return {'retained':2}
    check('same text with different message IDs is not deduplicated',repeated)
    def deepseek():
        url=fixture('<main><div data-message-id="d1" data-role="assistant">Reply<time datetime="yesterday"></time></div><div data-role="user">No stable id</div></main>','https://chat.deepseek.com/a')
        r=page.evaluate('(u)=>OCCArtifactInventory.observeMessages(document,u)',url)
        require(r['profile']=='deepseek');require(r['records'][0]['messageAt'] is None);require('UNPARSED_MESSAGE_TIME' in r['warnings']);require('SOME_MESSAGES_WITHOUT_STABLE_ID' in r['warnings']);return {'messages':len(r['records'])}
    check('DeepSeek adapter keeps unknown dates and missing IDs explicit',deepseek)
    def cards():
        url=fixture('<main><button data-file-id="opaque-1" aria-label="report.pdf">report.pdf</button><button aria-label="notes.docx">notes.docx</button><button id="ordinary">Delete</button><a href="https://files.example/data.csv?token=SECRET#x">data.csv</a></main>')
        page.evaluate("window.clicked=0;document.addEventListener('click',()=>window.clicked++)")
        r=page.evaluate('()=>OCCArtifactInventory.discover(document)')
        require(page.evaluate('window.clicked')==0);files=[x for x in r['items'] if x['kind']=='file-link'];require(len(files)==3,files)
        opaque=next(x for x in files if x['label']=='report.pdf');require(opaque['state']=='NOT_READ' and opaque['source']=='',opaque)
        linked=next(x for x in files if x['label']=='data.csv');require(linked['source']=='https://files.example/data.csv',linked)
        require('SECRET' not in json.dumps(r),r);require(all(x['label']!='Delete' for x in files));return {'files':len(files),'clicked':0}
    check('site file cards are inventoried without clicks or signed URLs',cards)
    def generic():
        fixture('<main><p>ordinary page</p></main>','https://example.org/page')
        p=page.evaluate("()=>OCCArtifactInventory.siteProfile('https://example.org/page')")
        require(p['name']=='generic' and p['maturity']=='GENERIC_BEST_EFFORT',p);return p
    check('unknown sites stay generic best effort',generic)
    browser.close()
report={'scope':'synthetic DOM in real Chromium; no signed-in account and no network fetch/click','counts':{s:sum(x['status']==s for x in results) for s in ['PASS','FAIL']},'tests':results}
(ROOT/'evidence'/'site-adapters-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report['counts']))
raise SystemExit(1 if report['counts']['FAIL'] else 0)
