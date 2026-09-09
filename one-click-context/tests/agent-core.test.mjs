import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeEndpoint,buildProviderRequest,readProviderResponse,parseAgentAction,riskyAction} from '../agent-core.mjs';

test('normalizes OpenAI-compatible base URL',()=>{
  assert.equal(normalizeEndpoint('https://example.com','openai-chat'),'https://example.com/v1/chat/completions');
  assert.equal(normalizeEndpoint('https://example.com/v1','openai-chat'),'https://example.com/v1/chat/completions');
});

test('blocks insecure remote HTTP but permits localhost',()=>{
  assert.throws(()=>normalizeEndpoint('http://example.com/v1','openai-chat'),/localhost/);
  assert.equal(normalizeEndpoint('http://127.0.0.1:8642/v1','openai-chat'),'http://127.0.0.1:8642/v1/chat/completions');
});

test('builds bearer request without persisting key',()=>{
  const r=buildProviderRequest({endpoint:'https://api.example',model:'x',apiKey:'secret',auth:'bearer'},[{role:'user',content:'hi'}]);
  assert.equal(r.headers.Authorization,'Bearer secret');
  assert.equal(r.body.model,'x');
});

test('reads common provider response formats',()=>{
  assert.equal(readProviderResponse({choices:[{message:{content:'a'}}]}),'a');
  assert.equal(readProviderResponse({content:[{text:'b'}]}),'b');
  assert.equal(readProviderResponse({candidates:[{content:{parts:[{text:'c'}]}}]}),'c');
});

test('parses fenced action and flags risky target',()=>{
  const action=parseAgentAction('```json\n{"action":"click","ref":"@e1","reason":"checkout"}\n```');
  assert.equal(action.action,'click');
  assert.equal(riskyAction(action,'Pay now'),true);
  assert.equal(riskyAction({action:'click',ref:'@e2',reason:'open docs'},'Documentation'),false);
});
