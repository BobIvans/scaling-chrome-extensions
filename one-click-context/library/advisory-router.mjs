import {validateGoalProposal} from './goal-normalizer.mjs';

export const ROUTER_SCHEMA='occ.advisory-route.v1';
export const ROUTES=Object.freeze(['ANALYZE_SELECTED_CONTEXT','BUILD_JOB_ARTIFACTS','REVIEW_REGISTERED_ACTION','MANUAL_REVIEW']);
const fail=code=>{throw Object.assign(new Error(code),{code});};
const RULES=[
 {id:'ANALYZE_V1',route:'ANALYZE_SELECTED_CONTEXT',pattern:/(?:анализ|сравн|сводк|источник|неизвестн|analy|compar|summari|source|unknown|analiz|salīdzin|avot)/iu},
 {id:'BUILD_V1',route:'BUILD_JOB_ARTIFACTS',pattern:/(?:созда|реализ|патч|тест|код|артефакт|build|create|implement|patch|test|code|artifact|izveid|ievies|kods)/iu},
 {id:'REGISTERED_V1',route:'REVIEW_REGISTERED_ACTION',pattern:/(?:синхрон|импорт|индекс|очеред|sync|import|index|queue|sinhron|importē|indeks|rinda)/iu}
];
const SENSITIVE={id:'SENSITIVE_EFFECT_V1',pattern:/(?:deploy|merge|sign|send|purchase|buy|account|browser|click|transaction|trade|wallet|депло|слиян|подпис|отправ|покуп|аккаунт|браузер|клик|транзак|торгов|кошел|izvieto|apvieno|parakst|nosūt|pirk|kont|pārlūk|darījum|tirgo|mak)/iu};
const exact=(value,keys,code)=>{if(!value||typeof value!=='object'||Array.isArray(value))fail(code+'_TYPE');const actual=Object.keys(value);for(const key of keys)if(!Object.hasOwn(value,key))fail(code+'_MISSING');if(actual.some(key=>!keys.includes(key)))fail(code+'_UNKNOWN_FIELD');};

export function routeGoal(value){
 const proposal=validateGoalProposal(value),text=[proposal.goal,...proposal.constraints].join('\n');
 const matched=RULES.filter(rule=>rule.pattern.test(text));let route='MANUAL_REVIEW',reason='NO_RULE_MATCH',confidence=0;
 if(SENSITIVE.pattern.test(text)){reason='SENSITIVE_EFFECT_REVIEW';confidence=1000;matched.push(SENSITIVE);}
 else if(matched.length===1){route=matched[0].route;reason='ONE_RULE_FAMILY';confidence=800;}
 else if(matched.length>1){reason='AMBIGUOUS_RULE_FAMILIES';confidence=400;}
 return {schema:ROUTER_SCHEMA,route,reason,matched_rule_ids:matched.map(rule=>rule.id),confidence_milli:confidence,suggested_mode:route==='ANALYZE_SELECTED_CONTEXT'?'analyze':route==='BUILD_JOB_ARTIFACTS'?'build':null,requires_registered_template:route==='REVIEW_REGISTERED_ACTION',action_authority:false,dispatch_allowed:false};
}

export function baselineRoute(value){
 const goal=validateGoalProposal(value).goal;
 if(/\b(?:analyze|compare|summarize)\b/iu.test(goal))return 'ANALYZE_SELECTED_CONTEXT';
 if(/\b(?:build|create|implement)\b/iu.test(goal))return 'BUILD_JOB_ARTIFACTS';
 if(/\b(?:sync|import|index)\b/iu.test(goal))return 'REVIEW_REGISTERED_ACTION';
 return 'MANUAL_REVIEW';
}

export function evaluateRoutes(dataset){
 if(!Array.isArray(dataset)||!dataset.length||dataset.length>100)fail('ROUTE_DATASET_SIZE');const seen=new Set();let routerCorrect=0,baselineCorrect=0;
 for(const item of dataset){exact(item,['id','split','proposal','expected_route'],'ROUTE_CASE');if(typeof item.id!=='string'||!item.id||seen.has(item.id))fail('ROUTE_CASE_ID');seen.add(item.id);if(item.split!=='HELD_OUT'||!ROUTES.includes(item.expected_route))fail('ROUTE_CASE_SCHEMA');
  if(routeGoal(item.proposal).route===item.expected_route)routerCorrect++;if(baselineRoute(item.proposal)===item.expected_route)baselineCorrect++;}
 const accuracy=correct=>Math.floor(correct*1000/dataset.length);
 return {schema:'occ.advisory-route-evaluation.v1',split:'HELD_OUT',cases:dataset.length,router_correct:routerCorrect,baseline_correct:baselineCorrect,router_accuracy_milli:accuracy(routerCorrect),baseline_accuracy_milli:accuracy(baselineCorrect),delta_accuracy_milli:accuracy(routerCorrect)-accuracy(baselineCorrect),action_authority:false};
}
