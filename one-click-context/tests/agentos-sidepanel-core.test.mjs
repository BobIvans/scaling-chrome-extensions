import test from 'node:test';
import assert from 'node:assert/strict';
import {classifyTab,originPattern,isObservable} from '../agentos/site-adapters.mjs';
import {buildUniversalCommand,extractUrls} from '../agentos/command-parser.mjs';

test('tab classification is display-only and generic sites remain supported',()=>{
  const known=classifyTab({id:7,windowId:2,title:'AI',url:'https://grok.com/example',active:true});
  assert.equal(known.provider_hint,'GROK_WEB');assert.equal(known.authority,'DISPLAY_HINT_ONLY');assert.equal(known.tab_id,7);
  const generic=classifyTab({id:8,windowId:2,title:'Custom AI',url:'https://ai.example.test/chat'});
  assert.equal(generic.provider_hint,'GENERIC_WEB');assert.equal(isObservable(generic),true);
  assert.equal(originPattern(generic.url),'https://ai.example.test/*');
});

test('command parser extracts hints but effect scope comes only from explicit UI input',()=>{
  const command=buildUniversalCommand({
    text:'Observe tab link: https://example.com/chat and implement a tool then merge it',
    mode:'LONG_HORIZON',effects:['READ'],acceptance:'verified'
  });
  assert.deepEqual(command.effect_scope,['READ']);
  assert.equal(command.self_improvement.allow_merge,false);
  assert.equal(command.target_hints.some(x=>x.url==='https://example.com/chat'),true);
});

test('explicit scopes control self-improvement gates',()=>{
  const command=buildUniversalCommand({
    text:'Build missing automation',mode:'LONG_HORIZON',
    effects:['READ','LOCAL_WRITE','LOCAL_PROCESS','GITHUB_WRITE','INSTALL_UPDATE'],acceptance:'qualified'
  });
  assert.equal(command.self_improvement.allow_tool_build,true);
  assert.equal(command.self_improvement.allow_pr_creation,true);
  assert.equal(command.self_improvement.allow_merge,true);
  assert.equal(command.self_improvement.allow_install_update,true);
});

test('URL extraction is stable and deduplicated',()=>{
  assert.deepEqual(extractUrls('a https://x.test/a b https://x.test/a. c https://y.test/'),['https://x.test/a','https://y.test/']);
});
