import test from 'node:test';
import assert from 'node:assert/strict';
import {CampaignView} from '../library/campaign-ui.mjs';
const result=(offset=0)=>({campaign:{campaign_id:'campaign',state:'ACTIVE',offset,total:45,nodes:[{id:'node',state:'WAITING',reason:'RESOURCE_WAIT'}],next_offset:offset===0?20:null}});
test('campaign paging has continuation beyond twenty nodes',async()=>{
 const calls=[];const v=new CampaignView({request:async(type,args)=>{calls.push([type,args]);return result(args.offset);}});
 await v.inspect('registered');await v.inspect('registered',20);
 assert.equal(calls[1][1].offset,20);assert.equal(v.page.total,45);
});
test('stale reply cannot overwrite a newly selected campaign',async()=>{
 let complete;const v=new CampaignView({request:()=>new Promise(r=>{complete=r;})});
 const request=v.inspect('first');v.invalidate();complete(result());await assert.rejects(request,/STALE_CAMPAIGN_REPLY/);assert.equal(v.page,null);
});
test('UI cannot supply arbitrary commands or invalid target IDs',async()=>{
 let calls=0;const v=new CampaignView({request:async()=>{calls++;return result();}});
 await assert.rejects(v.action('registered','shell'),/ACTION_REQUIRED/);await assert.rejects(v.inspect('../path'),/ID_REQUIRED/);assert.equal(calls,0);
});
test('cancel sends only registered alias then reads actual canonical state',async()=>{
 const calls=[];const v=new CampaignView({request:async(type,args)=>{calls.push([type,args]);return type.endsWith('inspect')?result():{campaign:{state:'CANCELLED'}};}});
 await v.action('registered','cancel');assert.deepEqual(calls[0],['durable.campaign.cancel',{campaign:'registered'}]);assert.equal(calls[1][0],'durable.campaign.inspect');
});
test('malformed continuation is rejected',async()=>{
 const v=new CampaignView({request:async()=>({campaign:{...result().campaign,next_offset:0}})});await assert.rejects(v.inspect('registered'),/RESULT_SCHEMA/);
});
