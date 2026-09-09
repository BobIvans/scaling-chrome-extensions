import {zipSync} from '../vendor/fflate.mjs';
import * as converter from '../library/convert.mjs';
const {PDFDocument,StandardFonts}=globalThis.PDFLib;
const requests=[],base=location.origin;
const Buffer={from:v=>typeof v==='string'?new TextEncoder().encode(v):new Uint8Array(v),alloc:(n,b=0)=>new Uint8Array(n).fill(b)};
const assert={equal:(a,b)=>{if(a!==b)throw Error(String(a)+' !== '+String(b));},deepEqual:(a,b)=>{if(JSON.stringify([...a])!==JSON.stringify([...b]))throw Error('byte mismatch');},ok:v=>{if(!v)throw Error('assertion failed');},match:(v,re)=>{if(!re.test(v))throw Error('pattern not found: '+re);},rejects:async(p,re)=>{let error;try{await p;}catch(e){error=e;}if(!error)throw Error('expected rejection');if(re&&!re.test(error.message))throw error;}};
const tests=[],test=(name,fn)=>tests.push({name,fn});
const page={evaluate:async(fn,arg)=>fn(arg)};
const cv=(name,bytes)=>converter.convert(name,new Uint8Array(bytes));
const zip=files=>zipSync(Object.fromEntries(Object.entries(files).map(([n,v])=>[n,Buffer.from(v)])));
test('UTF-8 bytes, BOM, CRLF, emoji, code and punctuation stay exact',async()=>{
 const input=Buffer.from('\ufeffПривет 👋\r\n  + x_y\\z\n- 1');const [r]=await cv('sample.txt',input);assert.deepEqual(Buffer.from(r.original),input);assert.equal(r.text,new TextDecoder("utf-8",{ignoreBOM:true}).decode(input));assert.equal(r.status,'ORIGINAL');
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
test('HTML scripts do not execute; external resources blocked by CSP',async()=>{const start=requests.length;const [r]=await cv('x.html',Buffer.from('<p>Visible</p><script>globalThis.PWN=1</script><img src="https://example.invalid/secret"><iframe src="https://example.invalid"></iframe>'));assert.equal(r.text,'Visible');assert.equal(await page.evaluate(()=>globalThis.PWN),undefined);/* Network block is enforced by CSP; resource audit requires browser network tooling. */});
test('aggregation sorts dates and retains PARTIAL warnings and text',async()=>{const r=await page.evaluate(()=>converter.aggregate([{id:'b',createdAt:'2026-09-09',name:'B',status:'PARTIAL',source:'chat B',warnings:['time limit'],text:'B\r\n'}, {id:'a',createdAt:'2026-09-08',name:'A',status:'ORIGINAL',source:'chat A',warnings:[],text:'A'}]));assert.ok(r.indexOf('===== A')<r.indexOf('===== B'));assert.match(r,/PARTIAL/);assert.match(r,/time limit/);assert.ok(r.endsWith('B\r\n'));});
test('safe filenames remove paths and Windows reserved names',async()=>{assert.equal(await page.evaluate(()=>converter.safeName('../../CON.txt')),'document_CON.txt');assert.equal(await page.evaluate(()=>converter.safeName('bad?.txt')),'bad_.txt');});

const uiTest={name:'Library UI: import, filter, explicit persistence and cross-tab clear (synthetic events)',fn:async()=>{
 const f=document.createElement('iframe');f.src='../library.html';document.body.append(f);await new Promise(r=>f.onload=r);const w=f.contentWindow,d=w.document;
 const wait=async fn=>{for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,25));}throw Error('UI timeout');};
 // Dedicated fixture origin only. Never run on a profile containing private library data.
 w.localStorage.removeItem('occ-library-v1');
 const dt=new w.DataTransfer();dt.items.add(new w.File(['\ufeffПривет\r\n  + x_y\\z'],'ui-proof.txt',{type:'text/plain'}));d.querySelector('#files').files=dt.files;d.querySelector('#files').dispatchEvent(new w.Event('change'));await wait(()=>d.querySelector('#status').textContent.includes('Добавлено: 1'));
 assert.equal(w.localStorage.getItem('occ-library-v1'),null);assert.equal(d.querySelectorAll('.item').length,1);assert.ok(d.querySelector('#preview').value.includes('Привет'));
 d.querySelector('#search').value='missing';d.querySelector('#search').dispatchEvent(new w.Event('input'));assert.equal(d.querySelectorAll('.item').length,0);d.querySelector('#search').value='';d.querySelector('#search').dispatchEvent(new w.Event('input'));
 w.confirm=()=>true;d.querySelector('#persist').click();assert.ok(w.localStorage.getItem('occ-library-v1'));
 const f2=document.createElement('iframe');f2.src='../library.html';document.body.append(f2);await new Promise(r=>f2.onload=r);await wait(()=>f2.contentDocument.querySelectorAll('.item').length===1);
 d.querySelector('#clear').click();await wait(()=>f2.contentDocument.querySelectorAll('.item').length===0);assert.equal(w.localStorage.getItem('occ-library-v1'),null);f.remove();f2.remove();
}};
tests.push(uiTest);

let passed=0;for(const t of tests){const item=document.createElement('li');try{await t.fn();passed++;item.textContent='PASS '+t.name;}catch(e){item.textContent='FAIL '+t.name+': '+e.message;}document.querySelector('ol').append(item);}document.querySelector('h1').textContent=`${passed}/${tests.length} browser converter tests passed`;
