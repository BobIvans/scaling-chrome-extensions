/* Typed campaign controls. The host owns manifests, Core jobs and STOP state. */
const NAME=/^[A-Za-z0-9_.:-]{1,100}$/;
export class CampaignView{
 constructor(session){this.session=session;this.alias=null;this.offset=0;this.page=null;this.version=0;}
 invalidate(){this.version++;this.alias=null;this.offset=0;this.page=null;}
 async inspect(alias,offset=0){
  if(!NAME.test(alias)||!Number.isSafeInteger(offset)||offset<0)throw Error('CAMPAIGN_ID_REQUIRED');
  const version=++this.version;
  const result=await this.session.request('durable.campaign.inspect',{campaign:alias,offset,limit:20});
  if(version!==this.version)throw Error('STALE_CAMPAIGN_REPLY');
  const c=result.campaign;
  if(!c||typeof c.campaign_id!=='string'||typeof c.state!=='string'||!Array.isArray(c.nodes)||!Number.isSafeInteger(c.total)||c.total<0||c.offset!==offset||c.nodes.length>20||c.nodes.some(n=>typeof n.id!=='string'||typeof n.state!=='string')||!(c.next_offset===null||Number.isSafeInteger(c.next_offset)&&c.next_offset>offset))throw Error('CAMPAIGN_RESULT_SCHEMA');
  this.alias=alias;this.offset=offset;this.page=c;return c;
 }
 async action(alias,action){
  if(!NAME.test(alias)||!['advance','cancel','pause','resume'].includes(action))throw Error('CAMPAIGN_ACTION_REQUIRED');
  this.invalidate();const version=this.version;
  const r=await this.session.request('durable.campaign.'+action,{campaign:alias});
  if(version!==this.version)throw Error('STALE_CAMPAIGN_REPLY');
  if(!r.campaign||typeof r.campaign.state!=='string')throw Error('CAMPAIGN_RESULT_SCHEMA');
  return this.inspect(alias);
 }
}
export function attachCampaignView({document,session}){
 const $=id=>document.getElementById(id);
 if(!$('campaign-inspect'))return {connect(){},disconnect(){}};
 const view=new CampaignView(session);let busy=false;
 const render=()=>{
  for(const action of ['inspect','advance','cancel','pause','resume'])$('campaign-'+action).disabled=busy||!session.can('durable.campaign.'+action);
  $('campaign-next').disabled=busy||view.page?.next_offset==null;
  $('campaign-output').textContent=view.page?`${view.page.campaign_id} · ${view.page.state}\n${view.page.offset+1}–${view.page.offset+view.page.nodes.length} / ${view.page.total}\n`+view.page.nodes.map(n=>`${n.id} · ${n.state}${n.reason?' · '+n.reason:''}`).join('\n'):'';
 };
 async function act(work){
  if(busy)return;busy=true;render();
  try{await work();$('campaign-status').textContent='Состояние получено. Остановка выполняющихся действий требует сверки.';}
  catch(e){if(!e.message.startsWith('STALE_'))$('campaign-status').textContent=e.message;}
  finally{busy=false;render();}
 }
 $('campaign-alias').oninput=()=>{view.invalidate();render();};
 for(const action of ['inspect','advance','cancel','pause','resume'])$('campaign-'+action).onclick=e=>{
  if(!e.isTrusted)return;
  const alias=$('campaign-alias').value.trim();
  void act(()=>action==='inspect'?view.inspect(alias):view.action(alias,action));
 };
 $('campaign-next').onclick=e=>{if(e.isTrusted&&view.page?.next_offset!=null)void act(()=>view.inspect(view.alias,view.page.next_offset));};
 render();return {view,connect(){view.invalidate();render();},disconnect(){view.invalidate();render();$('campaign-status').textContent='Канал закрыт; сохранённая очередь остаётся в Core.';}};
}
