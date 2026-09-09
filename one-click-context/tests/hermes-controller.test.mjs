import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeHermesBase,hermesHttpUrl,hermesWsUrl,HERMES_BROWSER_CAPABILITIES} from '../hermes-controller.mjs';

test('normalizes remote HTTPS and localhost HTTP',()=>{
  assert.equal(normalizeHermesBase('https://agent.example/v1'),'https://agent.example');
  assert.equal(normalizeHermesBase('http://127.0.0.1:8642/v1/'),'http://127.0.0.1:8642');
  assert.throws(()=>normalizeHermesBase('http://agent.example/v1'),/HTTPS/);
});

test('builds HTTPS/WSS controller endpoints without ticket in URL',()=>{
  assert.equal(hermesHttpUrl('https://agent.example/v1','/v1/capabilities'),'https://agent.example/v1/capabilities');
  assert.equal(hermesWsUrl('https://agent.example/v1'),'wss://agent.example/v1/browser-control/ws');
  assert.equal(hermesWsUrl('http://localhost:8642/v1'),'ws://localhost:8642/v1/browser-control/ws');
});

test('requests only official extension-control capability surface',()=>{
  assert.ok(HERMES_BROWSER_CAPABILITIES.includes('browser_snapshot'));
  assert.ok(HERMES_BROWSER_CAPABILITIES.includes('browser_type'));
  assert.equal(HERMES_BROWSER_CAPABILITIES.some(x=>/cdp|eval|console|upload|vision/.test(x)),false);
});
