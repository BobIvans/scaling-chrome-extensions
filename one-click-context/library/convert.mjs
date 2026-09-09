import {unzipSync} from '../vendor/fflate.mjs';

// Capture/export limit is unchanged. Office containers have a separate unpacking budget.
export const MAX_BYTES = 2200000;
export const MAX_UNPACKED = 8 * 1024 * 1024;
export const encode = text => new TextEncoder().encode(text);
export async function digest(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2,'0')).join('');
}
export function safeName(name) { const value=String(name).split(/[\\/]/).pop().replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,100).replace(/[. ]+$/,''); return (!value || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(value)) ? 'document_'+value : value; }
function xml(bytes) {
  const text = new TextDecoder('utf-8',{fatal:true}).decode(bytes);
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw Error('XML с DTD не поддерживается.');
  const doc = new DOMParser().parseFromString(text,'application/xml');
  if (doc.querySelector('parsererror')) throw Error('Повреждённый XML.');
  return doc;
}
const nodes = (root, name) => [...root.getElementsByTagNameNS('*',name)];
const textRuns = root => nodes(root,'t').map(x=>x.textContent).join('');
function paragraphs(doc) {
  return nodes(doc,'p').map(p => {
    const walk = n => n.nodeType === 1 ? (n.localName === 't' ? n.textContent : n.localName === 'tab' ? '\t' : ['br','cr'].includes(n.localName) ? '\n' : [...n.childNodes].map(walk).join('')) : '';
    return walk(p);
  }).join('\n');
}
export function unpack(bytes) {
  let total=0, count=0;
  return unzipSync(bytes,{filter(entry){
    if (++count>300 || !Number.isSafeInteger(entry.originalSize) || entry.originalSize<0 || (total+=entry.originalSize)>MAX_UNPACKED) throw Error('ZIP превышает предел: 300 элементов / 8 MiB после распаковки.');
    if (/^(\/|\\)|(^|[\\/])\.\.([\\/]|$)/.test(entry.name)) throw Error('Небезопасный путь внутри ZIP.');
    return !entry.name.endsWith('/');
  }});
}
function office(files, ext) {
  const get = name => { if (!files[name]) throw Error('Не найден '+name); return xml(files[name]); };
  if (ext==='docx') return paragraphs(get('word/document.xml'));
  if (ext==='pptx') {
    const rels = new Map(nodes(get('ppt/_rels/presentation.xml.rels'),'Relationship').map(x=>[x.getAttribute('Id'),x.getAttribute('Target')]));
    return nodes(get('ppt/presentation.xml'),'sldId').map((slide,i)=>{
      const id=slide.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id');
      const target=rels.get(id);
      if (!target || !/^slides\/slide\d+\.xml$/.test(target)) throw Error('Неподдерживаемая связь слайда.');
      return `СЛАЙД ${i+1}\n${paragraphs(get('ppt/'+target))}`;
    }).join('\n\n');
  }
  const strings = files['xl/sharedStrings.xml'] ? nodes(get('xl/sharedStrings.xml'),'si').map(textRuns) : [];
  const rels = new Map(nodes(get('xl/_rels/workbook.xml.rels'),'Relationship').map(x=>[x.getAttribute('Id'),x.getAttribute('Target')]));
  return nodes(get('xl/workbook.xml'),'sheet').map(sheet=>{
    const target=rels.get(sheet.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id'));
    if (!target || !/^(\/?xl\/)?worksheets\/sheet\d+\.xml$/.test(target)) throw Error('Неподдерживаемая связь листа.');
    const path=target.startsWith('/') ? target.slice(1) : target.startsWith('xl/') ? target : 'xl/'+target;
    return 'ЛИСТ '+sheet.getAttribute('name')+'\n'+nodes(get(path),'row').map(row=>nodes(row,'c').map(cell=>{
      const value=nodes(cell,'v')[0]?.textContent || '';
      const t=cell.getAttribute('t');
      const formula=nodes(cell,'f')[0]?.textContent;
      const result=t==='s' ? strings[Number(value)] ?? '' : t==='inlineStr' ? textRuns(cell) : value;
      return cell.getAttribute('r')+': '+(formula ? '='+formula+' [cached: '+result+']' : result);
    }).join('\t')).join('\n');
  }).join('\n\n');
}
async function pdf(bytes) {
  // pdf.js 4 uses Promise.withResolvers; retain Chrome 116 compatibility.
  if (!Promise.withResolvers) Promise.withResolvers = function(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};};
  const lib=await import('../vendor/pdf.mjs');
  lib.GlobalWorkerOptions.workerSrc=new URL('../vendor/pdf.worker.mjs',import.meta.url).href;
  const task=lib.getDocument({data:bytes.slice(),isEvalSupported:false,useSystemFonts:true,disableFontFace:true,stopAtErrors:true});
  try {
    const doc=await task.promise;
    if(doc.numPages>200) throw Error('PDF превышает 200 страниц.');
    let result='', hasText=false;
    for(let n=1;n<=doc.numPages;n++) {
      const page=await doc.getPage(n), content=await page.getTextContent();
      hasText ||= content.items.some(x=>x.str?.trim());
      result+=`СТРАНИЦА ${n}\n`+content.items.map(x=>x.str+(x.hasEOL?'\n':' ')).join('')+'\n\n';
      if(encode(result).length>MAX_BYTES) throw Error('Извлечённый PDF превышает 2 200 000 байт.');
    }
    return hasText ? result : '';
  } finally { await task.destroy(); }
}
export async function convert(name, bytes, depth=0) {
  if(!(bytes instanceof Uint8Array) || bytes.length>MAX_BYTES) throw Error('Входной файл превышает 2 200 000 байт.');
  const ext=name.split('.').pop().toLowerCase();
  if(ext==='zip') {
    if(depth>=2) throw Error('Вложенность ZIP превышает 2 уровня.');
    const results=[];
    for(const [path,data] of Object.entries(unpack(bytes))) {
      try { results.push(...(await convert(path,data,depth+1)).map(x=>({...x,name:safeName(name)+' / '+x.name}))); }
      catch(e){results.push({name:safeName(path),status:'UNSUPPORTED',text:'',warnings:[e.message]});}
    }
    return results;
  }
  let text, warnings=[], status='EXTRACTED', original=null;
  if(['docx','pptx','xlsx'].includes(ext)) {
    text=office(unpack(bytes),ext);
    warnings=['Извлечён текст. Оформление, изображения, встроенные объекты и часть метаданных не включены.'];
    if(ext==='xlsx') warnings.push('Числа и формулы без пересчёта; даты могут быть серийными числами Excel.');
  } else if(ext==='pdf') {
    text=await pdf(bytes); warnings=['PDF: порядок чтения приблизительный; изображения не распознаны (OCR не включён).'];
  } else if(['txt','md','csv','tsv','json','jsonl','xml','yaml','yml','log','js','ts','py','sql','patch','diff','toml','html','htm','css'].includes(ext)) {
    text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);
    if(text.includes('\0')) throw Error('Бинарный или UTF-16 файл: экспортируйте UTF-8.');
    original=Array.from(bytes); status='ORIGINAL';
    if(['html','htm'].includes(ext)) {
      // Detached HTML is never inserted in the live page.
      const doc=new DOMParser().parseFromString(text,'text/html');
      doc.querySelectorAll('script,style,iframe,object,embed').forEach(x=>x.remove());
      text=doc.body.textContent || '';original=null;status='EXTRACTED';warnings=['HTML: извлечён текст без выполнения скриптов; расположение блоков не сохранено.'];
    }
  } else throw Error('Формат .'+ext+' пока не поддерживается. Экспортируйте в DOCX/PPTX/XLSX/PDF/UTF-8.');
  if(encode(text).length>MAX_BYTES) throw Error('Извлечённый текст превышает 2 200 000 байт; усечение не выполнено.');
  if(!text.trim()) {status='EMPTY';warnings.push('Текст не найден. Для скана требуется OCR.');}
  return [{name:safeName(name),text,status,warnings,original,sha256:await digest(encode(text)),inputSha256:await digest(bytes)}];
}
export function aggregate(records) {
  const sorted=[...records].sort((a,b)=>a.createdAt.localeCompare(b.createdAt)||a.id.localeCompare(b.id));
  const text=sorted.map(r=>`===== ${r.name} | ${r.createdAt} | ${r.status} =====\nИсточник: ${r.source}\n${r.warnings.join('\n')}\n\n${r.text}`).join('\n\n');
  if(encode(text).length>MAX_BYTES) throw Error('Общий TXT превышает 2 200 000 байт. Выберите меньше документов.');
  return text;
}
