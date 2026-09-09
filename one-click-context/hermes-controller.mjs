const PROTOCOL = 'hermes-browser-control-v1';
export const HERMES_BROWSER_CAPABILITIES = Object.freeze([
  'controller.noop','browser_back','browser_click','browser_navigate','browser_press',
  'browser_scroll','browser_snapshot','browser_tab_activate','browser_tabs','browser_type'
]);

export function normalizeHermesBase(input) {
  const raw = String(input || '').trim();
  if (!raw) throw new Error('Укажите Hermes gateway URL.');
  const url = new URL(raw);
  if (!['https:','http:'].includes(url.protocol)) throw new Error('Hermes URL должен быть HTTP(S).');
  const local = ['localhost','127.0.0.1','[::1]'].includes(url.hostname);
  if (url.protocol === 'http:' && !local) throw new Error('Удалённый Hermes требует HTTPS.');
  if (url.username || url.password) throw new Error('Не помещайте credentials в URL.');
  url.hash = ''; url.search = '';
  url.pathname = url.pathname.replace(/\/(?:v1|api)\/?$/, '').replace(/\/$/, '');
  return url.toString().replace(/\/$/, '');
}

export function hermesHttpUrl(base, path) {
  return normalizeHermesBase(base) + (path.startsWith('/') ? path : '/' + path);
}

export function hermesWsUrl(base) {
  const u = new URL(normalizeHermesBase(base));
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
  u.pathname = u.pathname.replace(/\/$/, '') + '/v1/browser-control/ws';
  u.search = ''; u.hash = '';
  return u.toString();
}

async function jsonFetch(url, apiKey, options = {}) {
  const headers = {'Authorization': `Bearer ${String(apiKey || '').trim()}`, ...(options.body ? {'Content-Type':'application/json'} : {}), ...(options.headers || {})};
  if (!headers.Authorization.replace('Bearer ','')) throw new Error('Введите API_SERVER_KEY.');
  const response = await fetch(url, {...options, headers, cache:'no-store'});
  const text = await response.text();
  let payload = null; try { payload = text ? JSON.parse(text) : {}; } catch { payload = {raw:text}; }
  if (!response.ok) {
    const message = payload?.error?.message || payload?.message || payload?.error || text || response.statusText;
    throw new Error(`Hermes ${response.status}: ${String(message).slice(0,1000)}`);
  }
  return payload;
}

function sessionIdOf(payload) {
  for (const value of [payload?.session_id,payload?.id,payload?.session?.id,payload?.session?.session_id,payload?.data?.id,payload?.data?.session_id]) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  throw new Error('Hermes создал session, но её ID не распознан.');
}

function ticketOf(payload) {
  for (const value of [payload?.ticket,payload?.ws_ticket,payload?.connection_ticket,payload?.data?.ticket]) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  throw new Error('Hermes browser-control register не вернул ticket.');
}

export class HermesBrowserController {
  constructor({baseUrl, apiKey, dispatch, onState = () => {}, WebSocketImpl = WebSocket}) {
    this.baseUrl = normalizeHermesBase(baseUrl);
    this.apiKey = String(apiKey || '').trim();
    this.dispatch = dispatch;
    this.onState = onState;
    this.WebSocketImpl = WebSocketImpl;
    this.controllerId = crypto.randomUUID();
    this.browserProfileId = `occ-${crypto.randomUUID()}`;
    this.sessionId = null;
    this.socket = null;
    this.cancelled = new Set();
  }

  async capabilities() {
    return jsonFetch(hermesHttpUrl(this.baseUrl,'/v1/capabilities'), this.apiKey);
  }

  async createSession(title = 'OCC Chrome Relay') {
    const payload = await jsonFetch(hermesHttpUrl(this.baseUrl,'/api/sessions'), this.apiKey, {
      method:'POST', body:JSON.stringify({title})
    });
    this.sessionId = sessionIdOf(payload);
    return this.sessionId;
  }

  async connect(sessionId = null) {
    if (this.socket) await this.disconnect();
    const caps = await this.capabilities();
    const ext = caps?.browser_extension_control || caps?.features?.browser_extension_control;
    if (!ext || ext.enabled === false) throw new Error('На Hermes gateway не включён browser.extension_control.enabled.');
    this.sessionId = sessionId || this.sessionId || await this.createSession();
    const protocolVersion = Number(ext.protocol_version || ext.protocolVersion || caps?.browser_extension_control_protocol_version || 1) || 1;
    const requested = HERMES_BROWSER_CAPABILITIES.filter(x => !Array.isArray(ext.capabilities) || ext.capabilities.includes(x));
    const registration = await jsonFetch(hermesHttpUrl(this.baseUrl,'/v1/browser-control/register'), this.apiKey, {
      method:'POST', body:JSON.stringify({protocol_version:protocolVersion, session_id:this.sessionId,
        controller_id:this.controllerId, browser_profile_id:this.browserProfileId, capabilities:requested})
    });
    const ticket = ticketOf(registration);
    await this._open(ticket);
    this.onState({state:'connected',sessionId:this.sessionId,capabilities:registration.capabilities || requested});
    return {sessionId:this.sessionId, capabilities:registration.capabilities || requested};
  }

  _open(ticket) {
    return new Promise((resolve,reject) => {
      let settled = false;
      const ws = new this.WebSocketImpl(hermesWsUrl(this.baseUrl), [PROTOCOL, `hermes-browser-control-ticket.${ticket}`]);
      this.socket = ws;
      const timer = setTimeout(() => { if (!settled) { settled=true; try{ws.close();}catch{} reject(new Error('Hermes WebSocket timeout.')); } }, 15000);
      ws.onopen = () => { if (settled) return; settled=true; clearTimeout(timer); resolve(); };
      ws.onerror = () => { if (!settled) { settled=true; clearTimeout(timer); reject(new Error('Не удалось открыть Hermes browser-control WebSocket.')); } else this.onState({state:'socket-error'}); };
      ws.onclose = event => { clearTimeout(timer); if (this.socket === ws) this.socket=null; this.onState({state:'disconnected',code:event.code,reason:event.reason||''}); };
      ws.onmessage = event => { void this._onFrame(event.data, ws); };
    });
  }

  async _onFrame(raw, ws) {
    let frame; try { frame = JSON.parse(String(raw)); } catch { return; }
    const method = frame?.method;
    const params = frame?.params || {};
    if (method === 'browser.controller.cancel') {
      if (params.command_id) this.cancelled.add(params.command_id);
      return;
    }
    if (method !== 'browser.controller.command' || !params.command_id || typeof params.action !== 'string') return;
    const id = params.command_id;
    let reply;
    try {
      const result = await this.dispatch(params.action, Object.freeze({...params.arguments}), {commandId:id,toolCallId:params.tool_call_id||null});
      if (this.cancelled.delete(id)) return;
      reply = {method:'browser.controller.result',params:{command_id:id,ok:true,result:result ?? null}};
    } catch (error) {
      if (this.cancelled.delete(id)) return;
      reply = {method:'browser.controller.result',params:{command_id:id,ok:false,error:String(error?.message || error).slice(0,2000)}};
    }
    if (ws.readyState === this.WebSocketImpl.OPEN) ws.send(JSON.stringify(reply));
  }

  async startRun(input, {instructions = '', provider = '', model = ''} = {}) {
    if (!this.sessionId) throw new Error('Сначала подключите Hermes browser controller.');
    const body = {input:String(input || ''), session_id:this.sessionId};
    if (!body.input.trim()) throw new Error('Введите задачу.');
    if (instructions) body.instructions=instructions;
    if (provider) body.provider=provider;
    if (model) body.model=model;
    const payload = await jsonFetch(hermesHttpUrl(this.baseUrl,'/v1/runs'), this.apiKey, {
      method:'POST', headers:{'Idempotency-Key':crypto.randomUUID()}, body:JSON.stringify(body)
    });
    if (typeof payload?.run_id !== 'string') throw new Error('Hermes не вернул run_id.');
    return payload.run_id;
  }

  async runStatus(runId) { return jsonFetch(hermesHttpUrl(this.baseUrl,`/v1/runs/${encodeURIComponent(runId)}`),this.apiKey); }
  async stopRun(runId) { return jsonFetch(hermesHttpUrl(this.baseUrl,`/v1/runs/${encodeURIComponent(runId)}/stop`),this.apiKey,{method:'POST',body:'{}'}); }

  async disconnect() {
    const ws=this.socket; this.socket=null;
    if (ws && ws.readyState === this.WebSocketImpl.OPEN) {
      try { ws.send(JSON.stringify({method:'browser.controller.detach',params:{controller_id:this.controllerId,browser_profile_id:this.browserProfileId}})); } catch {}
      try { ws.close(1000,'user detach'); } catch {}
    } else { try{ws?.close();}catch{} }
    this.onState({state:'disconnected'});
  }
}
