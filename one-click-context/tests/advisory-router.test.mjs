import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {routeGoal,evaluateRoutes,ROUTER_SCHEMA} from '../library/advisory-router.mjs';

const dataset=JSON.parse(fs.readFileSync(fileURLToPath(new URL('./fixtures/advisory-routes.v1.json',import.meta.url)),'utf8'));
const proposal=overrides=>({...dataset[0].proposal,...overrides});

test('router returns advisory schema with no execution authority',()=>{
 const result=routeGoal(proposal());assert.equal(result.schema,ROUTER_SCHEMA);assert.equal(result.route,'ANALYZE_SELECTED_CONTEXT');assert.equal(result.suggested_mode,'analyze');assert.equal(result.action_authority,false);assert.equal(result.dispatch_allowed,false);
});

test('sensitive and ambiguous goals fail to manual review regardless of score',()=>{
 const sensitive=routeGoal(dataset.find(x=>x.id==='sensitive').proposal),ambiguous=routeGoal(dataset.find(x=>x.id==='ambiguous').proposal);
 assert.equal(sensitive.route,'MANUAL_REVIEW');assert.equal(sensitive.confidence_milli,1000);assert.equal(sensitive.action_authority,false);assert.equal(ambiguous.reason,'AMBIGUOUS_RULE_FAMILIES');
});

test('prohibitions are never treated as positive route requests',()=>{
 const result=routeGoal(proposal({goal:'Обработать набор',constraints:['Сохранить порядок'],prohibitions:['Создание кода','Синхронизация']}));assert.equal(result.route,'MANUAL_REVIEW');assert.deepEqual(result.matched_rule_ids,[]);
});

test('malformed, noncanonical and authority-bearing proposals reject',()=>{
 assert.throws(()=>routeGoal(proposal({schema:'x'})),error=>error.code==='GOAL_PROPOSAL_SCHEMA');
 assert.throws(()=>routeGoal(proposal({action_authority:true})),error=>error.code==='GOAL_PROPOSAL_AUTHORITY');
 assert.throws(()=>routeGoal({...proposal(),extra:true}),error=>error.code==='GOAL_PROPOSAL_UNKNOWN_FIELD');
 assert.throws(()=>routeGoal(proposal({goal:'  Сравнить документы  '})),error=>error.code==='GOAL_PROPOSAL_NOT_CANONICAL');
});

test('held-out fixture beats the compact goal-only rules baseline',()=>{
 const result=evaluateRoutes(dataset);assert.deepEqual(result,{schema:'occ.advisory-route-evaluation.v1',split:'HELD_OUT',cases:12,router_correct:12,baseline_correct:6,router_accuracy_milli:1000,baseline_accuracy_milli:500,delta_accuracy_milli:500,action_authority:false});
});

test('evaluation rejects duplicate IDs, non-held-out split and unknown fields',()=>{
 assert.throws(()=>evaluateRoutes([dataset[0],dataset[0]]),error=>error.code==='ROUTE_CASE_ID');assert.throws(()=>evaluateRoutes([{...dataset[0],split:'TRAIN'}]),error=>error.code==='ROUTE_CASE_SCHEMA');assert.throws(()=>evaluateRoutes([{...dataset[0],extra:true}]),error=>error.code==='ROUTE_CASE_UNKNOWN_FIELD');
});

test('production router has no network, Native Host, queue or shell dispatch surface',()=>{
 const source=fs.readFileSync(fileURLToPath(new URL('../library/advisory-router.mjs',import.meta.url)),'utf8');for(const forbidden of ['fetch(','XMLHttpRequest','WebSocket','chrome.runtime','durable.enqueue','child_process','postMessage','shell'])assert.equal(source.includes(forbidden),false,forbidden);
});
