import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeEndpoint,buildProviderRequest,readProviderResponse,parseAgentAction,riskyAction} from '../agent-core.mjs';
import {runProjectToolLoop} from '../project-tools.mjs';

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

const call = (id, args = '{"project":"fixture"}', name = 'inspect_project') =>
  ({type: 'function_call', call_id: id, name, arguments: args});
const message = text => ({type: 'message', role: 'assistant', phase: 'final_answer',
  content: [{type: 'output_text', text}]});
const completed = (...output) => ({status: 'completed', output});
function fixture(responses, overrides = {}) {
  const requests = [], executions = [];
  const definition = {type: 'function', name: 'inspect_project', strict: true,
    parameters: {type: 'object', properties: {project: {type: 'string'}},
      required: ['project'], additionalProperties: false}};
  const options = {config: {endpoint: 'https://api.example/v1', protocol: 'openai-responses',
    model: 'fixture-model', maxTokens: 256}, messages: [{role: 'user', content: 'inspect'}],
    registry: new Map([['inspect_project', {definition,
      validate: args => Object.keys(args).length === 1 && args.project === 'fixture',
      run: async (args, context) => {executions.push({args, context}); return {ready: false};}}]]),
    authorizeRequest: async () => true,
    request: async request => {requests.push(request); return responses.shift();}, ...overrides};
  return {options, requests, executions};
}

test('project loop accepts final text without a tool call', async () => {
  const f = fixture([completed(message('done'))]);
  const result = await runProjectToolLoop(f.options);
  assert.equal(result.text, 'done');
  assert.equal(result.receipt.requests, 1);
  assert.equal(f.executions.length, 0);
  assert.equal(f.requests[0].body.store, false);
  assert.equal(f.requests[0].body.max_output_tokens, 256);
});

test('native function-call-only response executes and retains call ID', async () => {
  const f = fixture([completed(call('call-1')), completed(message('blocked'))]);
  const result = await runProjectToolLoop(f.options);
  assert.equal(result.status, 'completed');
  assert.equal(f.requests[0].body.tools[0].name, 'inspect_project');
  assert.equal(f.executions.length, 1);
  assert.deepEqual(f.requests[1].body.input.at(-1), {
    type: 'function_call_output', call_id: 'call-1', output: '{"ready":false}'});
  assert.equal(result.receipt.calls[0].status, 'returned');
});

test('multiple calls retain reasoning and phase in the continuation', async () => {
  const reasoning = {type: 'reasoning', id: 'r1', summary: [], encrypted_content: 'fixture'};
  const commentary = {...message('checking'), phase: 'commentary'};
  const f = fixture([completed(reasoning, commentary, call('a'), call('b')), completed(message('done'))]);
  await runProjectToolLoop(f.options);
  const input = f.requests[1].body.input;
  assert.deepEqual(input[1], reasoning);
  assert.deepEqual(input[2], commentary);
  assert.deepEqual(input.slice(-2).map(x => x.call_id), ['a', 'b']);
  assert.equal(f.requests[0].body.input.length, 1);
});

test('the whole batch is validated before its first effect', async () => {
  for (const bad of [call('b', '{'), call('b', '[]'), call('b', '{"project":"other"}'),
    call('b', '{}', 'unregistered'), call('a')]) {
    const f = fixture([completed(call('a'), bad)]);
    await assert.rejects(runProjectToolLoop(f.options));
    assert.equal(f.executions.length, 0);
  }
});

test('a repeated call ID cannot rerun a completed handler', async () => {
  const f = fixture([completed(call('a')), completed(call('a'))]);
  await assert.rejects(runProjectToolLoop(f.options), error =>
    error.code === 'invalid_call_id' && error.receipt.calls.length === 1);
  assert.equal(f.executions.length, 1);
});

test('failed and incomplete responses never execute their calls', async () => {
  for (const status of ['failed', 'incomplete', 'in_progress', undefined]) {
    const f = fixture([{status, output: [call('a')]}]);
    await assert.rejects(runProjectToolLoop(f.options), {code: 'response_not_completed'});
    assert.equal(f.executions.length, 0);
  }
});

test('refusal is terminal and cannot accompany an executable call', async () => {
  const refusal = {type: 'message', content: [{type: 'refusal', refusal: 'declined'}]};
  const f = fixture([completed(refusal)]);
  assert.equal((await runProjectToolLoop(f.options)).status, 'refused');
  const mixed = fixture([completed(refusal, call('a'))]);
  await assert.rejects(runProjectToolLoop(mixed.options), {code: 'refusal_with_calls'});
  assert.equal(mixed.executions.length, 0);
});

test('request authorization is checked before every transport call', async () => {
  let permits = 1;
  const f = fixture([completed(call('a'))], {authorizeRequest: () => permits-- > 0});
  await assert.rejects(runProjectToolLoop(f.options), {code: 'request_not_authorized'});
  assert.equal(f.requests.length, 1);
  assert.equal(f.executions.length, 1);
  const denied = fixture([], {authorizeRequest: () => false});
  await assert.rejects(runProjectToolLoop(denied.options), {code: 'request_not_authorized'});
  assert.equal(denied.requests.length, 0);
});

test('limits stop a batch before effects and require a continuation turn', async () => {
  for (const limits of [{maxToolCalls: 1}, {maxTurns: 1}]) {
    const f = fixture([completed(call('a'), call('b'))], limits);
    await assert.rejects(runProjectToolLoop(f.options));
    assert.equal(f.executions.length, 0);
  }
});

test('cancellation during a batch stops the next handler', async () => {
  const controller = new AbortController();
  const f = fixture([completed(call('a'), call('b'))], {signal: controller.signal});
  f.options.registry.get('inspect_project').run = async () => {controller.abort(); return 'stopped';};
  await assert.rejects(runProjectToolLoop(f.options), error =>
    error.code === 'aborted' && error.receipt.calls.length === 1);
  assert.equal(f.requests.length, 1);
});

test('handler failure retains an unknown-effect receipt without retry or raw error', async () => {
  const f = fixture([completed(call('a'), call('b'))]);
  f.options.registry.get('inspect_project').run = async () => {throw new Error('private detail');};
  await assert.rejects(runProjectToolLoop(f.options), error => {
    assert.equal(error.message, 'handler_failed');
    assert.deepEqual(error.receipt.calls, [{call_id: 'a', name: 'inspect_project', status: 'failed_or_unknown'}]);
    return true;
  });
  assert.equal(f.requests.length, 1);
});

test('unserializable tool results preserve returned status and stop', async () => {
  const f = fixture([completed(call('a'))]);
  f.options.registry.get('inspect_project').run = async () => undefined;
  await assert.rejects(runProjectToolLoop(f.options), error =>
    error.code === 'invalid_tool_result' && error.receipt.calls[0].status === 'returned');
  assert.equal(f.requests.length, 1);
});

test('invalid profiles and missing registry validators fail before transport', async () => {
  const wrongProfile = fixture([], {config: {protocol: 'openai-chat'}});
  await assert.rejects(runProjectToolLoop(wrongProfile.options), {code: 'invalid_configuration'});
  assert.equal(wrongProfile.requests.length, 0);
  const missingValidator = fixture([]);
  delete missingValidator.options.registry.get('inspect_project').validate;
  await assert.rejects(runProjectToolLoop(missingValidator.options), {code: 'invalid_registry'});
  assert.equal(missingValidator.requests.length, 0);
});
