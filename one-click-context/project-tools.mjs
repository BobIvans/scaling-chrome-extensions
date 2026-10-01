import {buildProviderRequest} from './agent-core.mjs';

function fail(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function positiveLimit(value, ceiling) {
  if (!Number.isSafeInteger(value) || value < 1 || value > ceiling) fail('invalid_limit');
  return value;
}

function checkAbort(signal) {
  if (signal?.aborted) fail('aborted');
}

function prepareRegistry(registry) {
  if (!(registry instanceof Map)) fail('invalid_registry');
  const result = new Map();
  for (const [name, entry] of registry) {
    if (!/^[a-zA-Z0-9_-]{1,64}$/.test(name) || entry?.definition?.name !== name ||
        entry.definition.type !== 'function' || entry.definition.parameters?.type !== 'object' ||
        typeof entry.validate !== 'function' || typeof entry.run !== 'function') fail('invalid_registry');
    result.set(name, {...entry, definition: structuredClone(entry.definition)});
  }
  return result;
}

/**
 * Opt-in, transport-injected Responses loop. No network, shell, storage or browser
 * operations are provided by this module. Callers own scope, costs, persistence
 * and callback timeouts. Validators must be pure and synchronously return true.
 * authorizeRequest must permit each individual transport invocation explicitly.
 */
export async function runProjectToolLoop({config, messages, registry, request,
  authorizeRequest, signal, maxTurns = 4, maxToolCalls = 8}) {
  const receipt = {requests: 0, calls: []};
  try {
    positiveLimit(maxTurns, 32);
    positiveLimit(maxToolCalls, 128);
    if (config?.protocol !== 'openai-responses' || !config.model?.trim() ||
        typeof request !== 'function' || typeof authorizeRequest !== 'function') fail('invalid_configuration');
    const entries = prepareRegistry(registry);
    const seed = buildProviderRequest(config, messages);
    const transcript = structuredClone(seed.body.input);
    const seenCalls = new Set();
    const maxOutputTokens = positiveLimit(Number(config.maxTokens ?? 4096), 1000000);

    for (let turn = 0; turn < maxTurns; turn++) {
      checkAbort(signal);
      if (await authorizeRequest({requestIndex: turn, maxOutputTokens, signal}) !== true) fail('request_not_authorized');
      checkAbort(signal);
      const nextRequest = {endpoint: seed.endpoint, headers: {...seed.headers}, body: {
        ...seed.body, input: structuredClone(transcript),
        tools: [...entries.values()].map(entry => structuredClone(entry.definition)),
        max_output_tokens: maxOutputTokens
      }};
      receipt.requests++;
      const response = await request(nextRequest, {signal});
      checkAbort(signal);
      if (response?.error || response?.status !== 'completed' || !Array.isArray(response.output)) fail('response_not_completed');
      const output = structuredClone(response.output);
      const pending = [];
      const batchIDs = new Set();
      const text = [];
      let refused = false;

      // Validate the entire batch before executing any handler in this response.
      for (const item of output) {
        if (item?.type === 'reasoning') continue;
        if (item?.type === 'message') {
          if (!Array.isArray(item.content)) fail('invalid_message');
          for (const part of item.content) {
            if (part.type === 'refusal') refused = true;
            else if (part.type === 'output_text' && typeof part.text === 'string') text.push(part.text);
            else fail('unsupported_message_part');
          }
          continue;
        }
        if (item?.type !== 'function_call') fail('unsupported_output_item');
        const entry = entries.get(item.name);
        if (!entry) fail('unknown_tool');
        if (typeof item.call_id !== 'string' || !item.call_id || item.call_id.length > 256 ||
            seenCalls.has(item.call_id) || batchIDs.has(item.call_id)) fail('invalid_call_id');
        batchIDs.add(item.call_id);
        if (typeof item.arguments !== 'string' || item.arguments.length > 16384) fail('invalid_arguments');
        let args;
        try { args = JSON.parse(item.arguments); } catch { fail('invalid_arguments'); }
        if (!args || typeof args !== 'object' || Array.isArray(args) || entry.validate(args) !== true) fail('invalid_arguments');
        pending.push({item, entry, args});
      }
      if (refused && pending.length) fail('refusal_with_calls');
      if (!pending.length) {
        if (!refused && !text.join('').trim()) fail('empty_response');
        return {status: refused ? 'refused' : 'completed', text: text.join('\n'), receipt};
      }
      if (turn + 1 >= maxTurns) fail('turn_limit');
      if (receipt.calls.length + pending.length > maxToolCalls) fail('tool_call_limit');

      // Preserve output items, including encrypted reasoning, phase and call IDs.
      transcript.push(...output);
      for (const {item, entry, args} of pending) {
        checkAbort(signal);
        seenCalls.add(item.call_id);
        const call = {call_id: item.call_id, name: item.name, status: 'started'};
        receipt.calls.push(call);
        let result;
        try {
          result = await entry.run(args, {callId: item.call_id, signal});
          call.status = 'returned';
        } catch {
          call.status = 'failed_or_unknown';
          fail('handler_failed');
        }
        let serialized;
        try { serialized = typeof result === 'string' ? result : JSON.stringify(result); }
        catch { fail('invalid_tool_result'); }
        if (typeof serialized !== 'string') fail('invalid_tool_result');
        transcript.push({type: 'function_call_output', call_id: item.call_id, output: serialized});
      }
    }
    fail('turn_limit');
  } catch (error) {
    // Keep evidence of possible partial effects; never silently retry a handler.
    const wrapped = new Error(error?.code || 'project_loop_failed');
    wrapped.code = error?.code || 'project_loop_failed';
    wrapped.receipt = receipt;
    throw wrapped;
  }
}
