// Real browser execution of production converters and the library UI; synthetic documents only.
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'), path=require('node:path'), http=require('node:http');
const {createRequire}=require('node:module');
const deps=process.env.OCC_NODE_MODULES;
const req=deps?createRequire(path.join(deps,'_occ.cjs')):require;
const {chromium}=req('playwright');
const {PDFDocument,StandardFonts}=req('pdf-lib');
const root=path.resolve(__dirname,'..');
let browser,context,page,server,base,zipSync;
const requests=[];
before(async()=>{
 ({zipSync}=await import('../vendor/fflate.mjs'));
 server=http.createServer((q,r)=>{const file=path.resolve(root,'.'+decodeURIComponent(q.url.split('?')[0]));if(!file.startsWith(root+path.sep)){r.writeHead(403).end();return;}fs.readFile(file,(e,data)=>{if(e){r.writeHead(404).end();return;}r.setHeader('Content-Type',file.endsWith('.mjs')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');r.end(data);});});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port;
 browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,headless:true});context=await browser.newContext({acceptDownloads:true});
 context.on('request',r=>requests.push(r.url()));page=await context.newPage();await page.goto(base+'/library.html');
 await page.evaluate(async()=>{globalThis.converter=await import('./library/convert.mjs');});
});
after(async()=>{await browser?.close();await new Promise(r=>server?.close(r));});
const cv=(name,bytes)=>page.evaluate(async({name,bytes})=>converter.convert(name,new Uint8Array(bytes)),{name,bytes:[...bytes]});
const zip=files=>zipSync(Object.fromEntries(Object.entries(files).map(([n,v])=>[n,Buffer.from(v)])));
test('UTF-8 bytes, BOM, CRLF, emoji, code and punctuation stay exact',async()=>{
 const input=Buffer.from('\ufeffПривет 👋\r\n  + x_y\\z\n- 1');const [r]=await cv('sample.txt',input);assert.deepEqual(Buffer.from(r.original),input);assert.equal(r.text,input.toString());assert.equal(r.status,'ORIGINAL');
});
test('synthetic 181807-byte fixture is unchanged',async()=>{const bytes=Buffer.alloc(181807,65);const [r]=await cv('fixture.txt',bytes);assert.deepEqual(Buffer.from(r.original),bytes);});
test('DOCX extracts paragraphs tabs and breaks',async()=>{const [r]=await cv('x.docx',zip({'word/document.xml':'<w:document xmlns:w="w"><w:p><w:r><w:t>Привет</w:t><w:tab/><w:t>code</w:t><w:br/><w:t>next</w:t></w:r></w:p></w:document>'}));assert.equal(r.text,'Привет\tcode\nnext');assert.equal(r.status,'EXTRACTED');});
test('PPTX follows presentation order, not ZIP entry order',async()=>{
 const [r]=await cv('x.pptx',zip({'ppt/slides/slide1.xml':'<p xmlns:a="a"><a:p><a:r><a:t>ONE</a:t></a:r></a:p></p>','ppt/slides/slide2.xml':'<p xmlns:a="a"><a:p><a:r><a:t>TWO</a:t></a:r></a:p></p>','ppt/presentation.xml':'<p xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sldId r:id="b"/><sldId r:id="a"/></p>','ppt/_rels/presentation.xml.rels':'<R><Relationship Id="a" Target="slides/slide1.xml"/><Relationship Id="b" Target="slides/slide2.xml"/></R>'}));assert.ok(r.text.indexOf('TWO')<r.text.indexOf('ONE'));
});
test('XLSX preserves shared strings and cached formula labels',async()=>{
 const [r]=await cv('x.xlsx',zip({'xl/workbook.xml':'<w xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheet name="Prices" r:id="s"/></w>','xl/_rels/workbook.xml.rels':'<R><Relationship Id="s" Target="worksheets/sheet1.xml"/></R>','xl/sharedStrings.xml':'<sst><si><t>BTC</t></si></sst>','xl/worksheets/sheet1.xml':'<w><row><c r="A1" t="s"><v>0</v></c><c r="B1"><f>1+2</f><v>3</v></c></row></w>'}));assert.match(r.text,/A1: BTC/);assert.match(r.text,/B1: =1\+2 \[cached: 3\]/);
});
test('PDF extracts text using packaged pdf.js',async()=>{const doc=await PDFDocument.create();const font=await doc.embedFont(StandardFonts.Helvetica);doc.addPage().drawText('PDF fixture',{font});const [r]=await cv('x.pdf',await doc.save());assert.match(r.text,/PDF fixture/);});
test('empty PDF is EMPTY, page headers do not imply extracted content',async()=>{const doc=await PDFDocument.create();doc.addPage();const [r]=await cv('x.pdf',await doc.save());assert.equal(r.status,'EMPTY');assert.equal(r.text,'');});
test('ZIP returns supported and explicit unsupported records',async()=>{const r=await cv('x.zip',zip({'a.txt':'hello','b.exe':'binary'}));assert.equal(r.length,2);assert.equal(r[0].text,'hello');assert.equal(r[1].status,'UNSUPPORTED');});
test('ZIP traversal and unpack budget rejected',async()=>{await assert.rejects(cv('x.zip',zip({'../escape.txt':'x'})),/Небезопасный/);await assert.rejects(cv('x.zip',zip({'bomb.txt':Buffer.alloc(9*1024*1024)})),/8 MiB/);});
test('oversize input, invalid UTF-8 and XML entity declarations rejected',async()=>{await assert.rejects(cv('x.txt',Buffer.alloc(2200001)),/2 200 000/);await assert.rejects(cv('x.txt',Buffer.from([0xff])));await assert.rejects(cv('x.docx',zip({'word/document.xml':'<!DOCTYPE x [<!ENTITY a "x">]><x>&a;</x>'})),/DTD/);});
test('HTML scripts and external resources do not execute or load',async()=>{const start=requests.length;const [r]=await cv('x.html',Buffer.from('<p>Visible</p><script>globalThis.PWN=1</script><img src="https://example.invalid/secret"><iframe src="https://example.invalid"></iframe>'));assert.equal(r.text,'Visible');assert.equal(await page.evaluate(()=>globalThis.PWN),undefined);assert.ok(requests.slice(start).every(u=>u.startsWith(base)));});
test('aggregation sorts dates and retains PARTIAL warnings and text',async()=>{const r=await page.evaluate(()=>converter.aggregate([{id:'b',createdAt:'2026-09-09',name:'B',status:'PARTIAL',source:'chat B',warnings:['time limit'],text:'B\r\n'}, {id:'a',createdAt:'2026-09-08',name:'A',status:'ORIGINAL',source:'chat A',warnings:[],text:'A'}]));assert.ok(r.indexOf('===== A')<r.indexOf('===== B'));assert.match(r,/PARTIAL/);assert.match(r,/time limit/);assert.ok(r.endsWith('B\r\n'));});
test('safe filenames remove paths and Windows reserved names',async()=>{assert.equal(await page.evaluate(()=>converter.safeName('../../CON.txt')),'document_CON.txt');assert.equal(await page.evaluate(()=>converter.safeName('bad?.txt')),'bad_.txt');});
test('UI import, filter, byte-exact download, consent and cross-tab clear',async()=>{
 const input=Buffer.from('\ufeffПроверка\r\n  + a_b\\c');await page.locator('#files').setInputFiles({name:'proof.txt',mimeType:'text/plain',buffer:input});await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Добавлено: 1'));
 assert.equal(await page.evaluate(()=>localStorage.getItem('occ-library-v1')),null);
 const event=page.waitForEvent('download');await page.locator('#original').click();const dl=await event;assert.deepEqual(fs.readFileSync(await dl.path()),input);
 await page.locator('#search').fill('not-found');assert.equal(await page.locator('.item').count(),0);await page.locator('#search').fill('proof');assert.equal(await page.locator('.item').count(),1);
 page.once('dialog',d=>d.accept());await page.locator('#persist').click();await page.reload();assert.equal(await page.locator('.item').count(),1);
 const second=await context.newPage();await second.goto(base+'/library.html');assert.equal(await second.locator('.item').count(),1);await page.locator('#clear').click();await second.waitForFunction(()=>document.querySelectorAll('.item').length===0);assert.equal(await second.evaluate(()=>localStorage.getItem('occ-library-v1')),null);await second.close();
});
test('JSON collection restore preserves dates, rejects tampering and never persists implicitly',async()=>{
 const record={id:'old',name:'restored',source:'chat fixture',createdAt:'2026-08-01T12:00:00.000Z',status:'PARTIAL',warnings:['unknown limit'],text:'Привет\r\n',sha256:require('node:crypto').createHash('sha256').update('Привет\r\n').digest('hex')};
 const upload=async r=>page.locator('#backup').setInputFiles({name:'collection.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({version:1,records:[r]}))});
 await upload(record);await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Восстановлено документов: 1'));assert.match(await page.locator('#list').textContent(),/2026-08-01/);assert.equal(await page.evaluate(()=>localStorage.getItem('occ-library-v1')),null);
 await upload({...record,text:'changed'});await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('SHA-256'));assert.equal(await page.locator('#list .item').count(),1);await page.locator('#clear').click();
});
test('real browser agent file download with mocked native API rejects synthetic connect',async()=>{
 const p=await context.newPage();const bytes=Buffer.from([0,255,128,65]);const sha=require('node:crypto').createHash('sha256').update(bytes).digest('hex');
 await p.addInitScript(({sha,base64})=>{globalThis.nativeCalls=[];window.chrome={runtime:{id:'fixture',connectNative(){let receive;return {onMessage:{addListener:f=>receive=f},onDisconnect:{addListener(){}},disconnect(){},postMessage(m){nativeCalls.push(m.type);const replies={hello:{version:1},list:{jobs:[{id:'job',createdAt:'2026-09-09T00:00:00Z',mode:'build',state:'COMPLETE'}]},artifacts:{artifacts:[{id:'file',name:'report.zip',bytes:4,sha256:sha}]},artifact:{offset:0,bytes:4,sha256:sha,base64}};queueMicrotask(()=>receive({requestId:m.requestId,ok:true,...replies[m.type]}));}};}},permissions:{request:async()=>true}};},{sha,base64:bytes.toString('base64')});
 await p.goto(base+'/library.html');await p.locator('summary').filter({hasText:'Задания локальному Codex'}).click();await p.evaluate(()=>document.querySelector('#agent-connect').click());assert.deepEqual(await p.evaluate(()=>nativeCalls),[]);await p.locator('#agent-connect').click();await p.getByRole('button',{name:'Файлы результата',exact:true}).click();const event=p.waitForEvent('download');await p.getByRole('button',{name:'Скачать report.zip · 4 байт',exact:true}).click();assert.deepEqual(fs.readFileSync(await(await event).path()),bytes);await p.close();
});
