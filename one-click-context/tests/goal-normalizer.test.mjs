import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {normalizeGoal,normalizeGoalForm,GOAL_SCHEMA,MAX_GOAL_BYTES} from '../library/goal-normalizer.mjs';

const valid=()=>({goal:'Сравнить источники',constraints:['Сохранить provenance','Показать неизвестные измерения'],prohibitions:['Публикация данных','Изменение внешних систем'],money_budget:0,max_parallel:1});

test('normalizer emits one typed proposal with no action authority',()=>{
 assert.deepEqual(normalizeGoal(valid()),{schema:GOAL_SCHEMA,goal:'Сравнить источники',constraints:['Сохранить provenance','Показать неизвестные измерения'],prohibitions:['Публикация данных','Изменение внешних систем'],money_budget:0,max_parallel:1,action_authority:false});
});

test('every field is required and unknown fields fail closed',()=>{
 for(const field of Object.keys(valid())){const value=valid();delete value[field];assert.throws(()=>normalizeGoal(value),error=>error.code===field.toUpperCase()+'_MISSING',field);}
 assert.throws(()=>normalizeGoal({...valid(),command:'shell'}),error=>error.code==='GOAL_UNKNOWN_FIELD');
});

test('negation is rejected in goal, constraints and explicit prohibition labels',()=>{
 for(const [field,value] of [['goal','Не публиковать данные'],['constraints',['never truncate']],['prohibitions',['bez tīkla']]]){const input=valid();input[field]=value;assert.throws(()=>normalizeGoal(input),error=>error.code.endsWith('_NEGATION_AMBIGUOUS'),field);}
});

test('budget and concurrency require numbers and current zero/one policy',()=>{
 assert.throws(()=>normalizeGoal({...valid(),money_budget:'0'}),error=>error.code==='MONEY_BUDGET_TYPE');
 assert.throws(()=>normalizeGoal({...valid(),money_budget:1}),error=>error.code==='MONEY_BUDGET_POLICY');
 assert.throws(()=>normalizeGoal({...valid(),max_parallel:true}),error=>error.code==='MAX_PARALLEL_TYPE');
 assert.throws(()=>normalizeGoal({...valid(),max_parallel:2}),error=>error.code==='MAX_PARALLEL_POLICY');
});

test('form adapter parses lines and strict integer strings without granting authority',()=>{
 const result=normalizeGoalForm({goal:'  Проверить   diff ',constraints:'Сохранить SHA\nПоказать receipts\n',prohibitions:'Merge\nDeploy',moneyBudget:'0',maxParallel:'1'});
 assert.equal(result.goal,'Проверить diff');assert.deepEqual(result.constraints,['Сохранить SHA','Показать receipts']);assert.equal(result.action_authority,false);
 for(const moneyBudget of ['','00','1.0','-0'])assert.throws(()=>normalizeGoalForm({goal:'Цель',constraints:'Лимит',prohibitions:'Deploy',moneyBudget,maxParallel:'1'}));
});

test('empty, duplicate and oversized semantic values reject without truncation',()=>{
 assert.throws(()=>normalizeGoal({...valid(),constraints:[]}),error=>error.code==='CONSTRAINTS_MISSING');
 assert.throws(()=>normalizeGoal({...valid(),constraints:['SHA','sha']}),error=>error.code==='CONSTRAINTS_DUPLICATE');
 assert.throws(()=>normalizeGoal({...valid(),goal:'я'.repeat(MAX_GOAL_BYTES)}),error=>error.code==='GOAL_LIMIT');
});

test('production normalizer has no network, queue, shell or browser dispatch surface',()=>{
 const source=fs.readFileSync(fileURLToPath(new URL('../library/goal-normalizer.mjs',import.meta.url)),'utf8');
 for(const forbidden of ['fetch(','XMLHttpRequest','WebSocket','chrome.runtime','durable.enqueue','child_process','shell'])assert.equal(source.includes(forbidden),false,forbidden);
});
