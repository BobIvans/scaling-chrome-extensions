import {aggregate,encode} from './convert.mjs';
import {splitBundle} from './bundle-core.mjs';
const $=id=>document.getElementById(id);
const KEY='occ-library-v1';
let records=[],selected=new Set(),bundle=null,current=0;
function notice(text){$('status').textContent=text;}
function download(bytes,name){
  const url=URL.createObjectURL(new Blob([bytes],{type:'application/octet-stream'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
}
function safeRecords(){
  const saved=JSON.parse(localStorage.getItem(KEY)||'null');
  if(!saved||saved.version!==1||!Array.isArray(saved.records))return [];
  return saved.records.filter(r=>r&&typeof r.id==='string'&&typeof r.name==='string'&&typeof r.text==='string'&&typeof r.source==='string');
}
function renderRecords(){
  const host=$('records');host.replaceChildren();
  if(!records.length){host.textContent='Сначала сохраните библиотеку на основной странице.';return;}
  for(const r of records){
    const row=document.createElement('div');row.className='item';
    const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=selected.has(r.id);
    check.onchange=()=>{check.checked?selected.add(r.id):selected.delete(r.id);};
    label.append(check,document.createTextNode(r.name));
    const meta=document.createElement('small');meta.textContent=`${r.status||'UNKNOWN'} · ${encode(r.text).length} байт\n${r.source}`;
    row.append(label,meta);host.append(row);
  }
}
function showPart(){
  const parts=bundle?.payloads||[];
  if(!parts.length){$('preview').value='';$('part-title').textContent='Часть не собрана';$('part-meta').textContent='';return;}
  current=Math.max(0,Math.min(current,parts.length-1));
  const part=parts[current];$('preview').value=part.text;
  $('part-title').textContent=`Часть ${current+1} из ${parts.length}`;
  $('part-meta').textContent=`${part.bytes} байт · SHA-256 ${part.sha256.slice(0,16)}…`;
  $('prev').disabled=current===0;$('next').disabled=current===parts.length-1;
  for(const id of ['copy','download','manifest'])$(id).disabled=false;
}
$('all').onchange=()=>{selected=$('all').checked?new Set(records.map(r=>r.id)):new Set();renderRecords();};
$('build').onclick=async()=>{
  try{
    const chosen=records.filter(r=>selected.has(r.id));if(!chosen.length)throw Error('Выберите хотя бы одну запись.');
    const text=aggregate(chosen);bundle=await splitBundle(text,{partBytes:Number($('limit').value),label:'occ_saved_library'});current=0;showPart();
    notice(`Собрано ${bundle.payloads.length} частей из ${bundle.totalBytes} байт. SHA-256 всего текста: ${bundle.wholeSha256}`);
  }catch(e){bundle=null;showPart();for(const id of ['copy','download','manifest'])$(id).disabled=true;notice(e.message);}
};
$('prev').onclick=()=>{current--;showPart();};$('next').onclick=()=>{current++;showPart();};
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText(bundle.payloads[current].text);notice(`Часть ${current+1} скопирована.`);}catch{notice('Буфер обмена заблокирован. Используйте Download.');}};
$('download').onclick=()=>{const p=bundle.payloads[current];download(encode(p.text),`context_part_${String(current+1).padStart(3,'0')}_of_${String(bundle.payloads.length).padStart(3,'0')}.txt`);notice('Скачивание текущей части запрошено.');};
$('manifest').onclick=()=>{const {payloads,...manifest}=bundle;download(encode(JSON.stringify(manifest,null,2)),'context_parts_manifest.json');notice('Скачивание manifest запрошено.');};
records=safeRecords();renderRecords();
if(records.length)notice(`Загружено сохранённых записей: ${records.length}. Выберите нужные.`);
