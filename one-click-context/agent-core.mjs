const DEFAULT_MAX_TOKENS = 4096;

export function normalizeEndpoint(input, protocol = 'openai-chat') {
  const raw = String(input || '').trim();
  if (!raw) throw new Error('Укажите API endpoint.');
  const url = new URL(raw);
  if (!['https:', 'http:'].includes(url.protocol)) throw new Error('Поддерживаются только HTTP(S) endpoint.');
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol === 'http:' && !local) throw new Error('Незашифрованный HTTP разрешён только для localhost.');
  if (url.username || url.password) throw new Error('Логин/пароль нельзя помещать в URL.');
  const clean = url.toString().replace(/\/$/, '');
  if (protocol === 'openai-chat' && !/\/chat\/completions(?:$|[?#])/.test(clean)) {
    return clean.replace(/\/v1$/, '') + '/v1/chat/completions';
  }
  if (protocol === 'openai-responses' && !/\/responses(?:$|[?#])/.test(clean)) {
    return clean.replace(/\/v1$/, '') + '/v1/responses';
  }
  return clean;
}

function safeHeaders(extraHeaders) {
  if (!extraHeaders) return {};
  let parsed = extraHeaders;
  if (typeof extraHeaders === 'string') {
    if (!extraHeaders.trim()) return {};
    parsed = JSON.parse(extraHeaders);
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Extra headers должны быть JSON-объектом.');
  const result = {};
  for (const [name, value] of Object.entries(parsed)) {
    if (!/^[!#$%&'*+.^_`|~0-9A-Za-z-]{1,80}$/.test(name)) throw new Error('Недопустимое имя HTTP header.');
    if (typeof value !== 'string' || value.length > 2000 || /[\r\n]/.test(value)) throw new Error('Недопустимое значение HTTP header.');
    result[name] = value;
  }
  return result;
}

export function buildProviderRequest(config, messages) {
  if (!Array.isArray(messages) || !messages.length) throw new Error('Messages required.');
  const protocol = config.protocol || 'openai-chat';
  const endpoint = normalizeEndpoint(config.endpoint, protocol);
  const headers = {'Content-Type': 'application/json', ...safeHeaders(config.extraHeaders)};
  const key = String(config.apiKey || '').trim();
  const auth = config.auth || 'bearer';
  if (key) {
    if (auth === 'bearer') headers.Authorization = `Bearer ${key}`;
    else if (auth === 'x-api-key') headers['x-api-key'] = key;
    else if (auth === 'x-goog-api-key') headers['x-goog-api-key'] = key;
    else if (auth !== 'none') throw new Error('Unsupported auth mode.');
  }
  let body;
  if (protocol === 'openai-chat') {
    body = {model: config.model || 'hermes-agent', messages, stream: false,
      max_tokens: Number(config.maxTokens) || DEFAULT_MAX_TOKENS};
  } else if (protocol === 'openai-responses') {
    const system = messages.filter(m => m.role === 'system').map(m => m.content).join('\n\n');
    const input = messages.filter(m => m.role !== 'system').map(m => ({role: m.role === 'assistant' ? 'assistant' : 'user', content: String(m.content)}));
    body = {model: config.model || 'hermes-agent', input, store: false};
    if (system) body.instructions = system;
  } else if (protocol === 'anthropic') {
    const system = messages.filter(m => m.role === 'system').map(m => m.content).join('\n\n');
    body = {model: config.model, max_tokens: Number(config.maxTokens) || DEFAULT_MAX_TOKENS,
      messages: messages.filter(m => m.role !== 'system').map(m => ({role: m.role === 'assistant' ? 'assistant' : 'user', content: String(m.content)}))};
    if (system) body.system = system;
    if (!headers['anthropic-version']) headers['anthropic-version'] = '2023-06-01';
  } else if (protocol === 'gemini') {
    const system = messages.filter(m => m.role === 'system').map(m => m.content).join('\n\n');
    body = {contents: messages.filter(m => m.role !== 'system').map(m => ({role: m.role === 'assistant' ? 'model' : 'user', parts: [{text: String(m.content)}]}))};
    if (system) body.systemInstruction = {parts: [{text: system}]};
    body.generationConfig = {maxOutputTokens: Number(config.maxTokens) || DEFAULT_MAX_TOKENS};
  } else throw new Error('Unknown provider protocol.');
  return {endpoint, headers, body};
}

function extractOutputTextArray(output) {
  if (!Array.isArray(output)) return '';
  const chunks = [];
  for (const item of output) {
    if (item?.type === 'message' && Array.isArray(item.content)) {
      for (const part of item.content) if (typeof part?.text === 'string') chunks.push(part.text);
    } else if (typeof item?.text === 'string') chunks.push(item.text);
  }
  return chunks.join('\n').trim();
}

export function readProviderResponse(payload) {
  if (payload == null) throw new Error('Пустой ответ API.');
  if (typeof payload === 'string') return payload;
  const openai = payload?.choices?.[0]?.message?.content;
  if (typeof openai === 'string') return openai;
  if (Array.isArray(openai)) {
    const text = openai.map(x => x?.text || x?.content || '').filter(Boolean).join('\n').trim();
    if (text) return text;
  }
  if (typeof payload.output_text === 'string' && payload.output_text) return payload.output_text;
  const output = extractOutputTextArray(payload.output);
  if (output) return output;
  if (Array.isArray(payload.content)) {
    const text = payload.content.map(x => x?.text || '').filter(Boolean).join('\n').trim();
    if (text) return text;
  }
  const gemini = payload?.candidates?.[0]?.content?.parts;
  if (Array.isArray(gemini)) {
    const text = gemini.map(x => x?.text || '').filter(Boolean).join('\n').trim();
    if (text) return text;
  }
  for (const key of ['result', 'response', 'text', 'message', 'output']) {
    if (typeof payload[key] === 'string' && payload[key].trim()) return payload[key];
  }
  if (payload?.error) throw new Error(typeof payload.error === 'string' ? payload.error : payload.error.message || JSON.stringify(payload.error));
  throw new Error('Не удалось извлечь текст из ответа API.');
}

export function parseAgentAction(text) {
  const raw = String(text || '').trim();
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i)?.[1];
  const candidates = [raw, fenced].filter(Boolean);
  const first = raw.indexOf('{'), last = raw.lastIndexOf('}');
  if (first >= 0 && last > first) candidates.push(raw.slice(first, last + 1));
  let value = null;
  for (const candidate of candidates) {
    try { value = JSON.parse(candidate); break; } catch {}
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Agent должен вернуть один JSON action.');
  const action = String(value.action || '').toLowerCase();
  const allowed = new Set(['done','click','type','press','scroll','navigate','back','wait','snapshot','switch_tab','new_tab','close_tab']);
  if (!allowed.has(action)) throw new Error(`Неизвестное действие agent: ${action || '(empty)'}`);
  return {...value, action};
}

const RISK_WORDS = /\b(pay|payment|buy|purchase|checkout|order|transfer|withdraw|deposit|send funds|swap|trade|confirm transaction|sign transaction|approve token|delete|remove account|close account|merge pull request|publish|post publicly|send message|submit application)\b/i;

export function riskyAction(action, targetText = '') {
  if (!action || typeof action !== 'object') return false;
  if (action.action === 'close_tab') return true;
  if (['type','click','press'].includes(action.action) && RISK_WORDS.test(`${action.reason || ''} ${targetText || ''}`)) return true;
  if (action.action === 'navigate' && /(?:wallet|checkout|payment|bank|exchange|trading)/i.test(String(action.url || ''))) return true;
  return false;
}

export function plannerPrompt(goal, snapshot, history = []) {
  const cleanHistory = history.slice(-6).map(x => `${x.action}: ${x.result || ''}`).join('\n');
  return `You are OCC Hermes Lite Browser Planner. Choose exactly ONE next browser action needed to accomplish the user's goal.\n\n` +
    `Return ONLY one JSON object, no markdown. Allowed forms:\n` +
    `{"action":"click","ref":"@e12","reason":"..."}\n` +
    `{"action":"type","ref":"@e7","text":"...","reason":"..."}\n` +
    `{"action":"press","ref":"@e7","key":"Enter","reason":"..."}\n` +
    `{"action":"scroll","direction":"down","amount":700,"reason":"..."}\n` +
    `{"action":"navigate","url":"https://...","reason":"..."}\n` +
    `{"action":"switch_tab","tabId":123,"reason":"..."}\n` +
    `{"action":"new_tab","url":"https://...","reason":"..."}\n` +
    `{"action":"close_tab","tabId":123,"reason":"..."}\n` +
    `{"action":"back","reason":"..."}\n{"action":"wait","ms":1000,"reason":"..."}\n` +
    `{"action":"done","result":"..."}\n\n` +
    `Never request passwords, OTPs, recovery phrases, cookies or authentication tokens. Do not invent element refs. ` +
    `If an irreversible/financial/account/public action is required, choose the exact click/type action; the extension will pause for user approval.\n\n` +
    `GOAL:\n${goal}\n\nRECENT ACTIONS:\n${cleanHistory || '(none)'}\n\nBROWSER SNAPSHOT:\n${JSON.stringify(snapshot)}`;
}
