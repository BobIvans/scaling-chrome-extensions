export const GOAL_SCHEMA='occ.goal-proposal.v1';
export const MAX_GOAL_BYTES=4000,MAX_ENTRY_BYTES=1000,MAX_ENTRIES=20,MAX_PROPOSAL_BYTES=16000;
const REQUIRED=['goal','constraints','prohibitions','money_budget','max_parallel'];
const PROPOSAL_REQUIRED=['schema',...REQUIRED,'action_authority'];
const NEGATION=/(^|[^\p{L}\p{N}_])(?:do\s+not|don't|cannot|can't|not|no|never|without|не|нет|без|нельзя|никогда|ne|nav|bez|nedrīkst|nekad)(?=$|[^\p{L}\p{N}_])/iu;
const bytes=value=>new TextEncoder().encode(value).length;
const fail=code=>{throw Object.assign(new Error(code),{code});};

function clean(value,limit,field){
 if(typeof value!=='string'||value.includes('\0'))fail(field+'_TYPE');
 const normalized=value.trim().replace(/\s+/gu,' ');if(!normalized)fail(field+'_EMPTY');
 if(bytes(normalized)>limit)fail(field+'_LIMIT');if(NEGATION.test(normalized))fail(field+'_NEGATION_AMBIGUOUS');return normalized;
}
function entries(value,field){
 if(!Array.isArray(value)||!value.length)fail(field+'_MISSING');if(value.length>MAX_ENTRIES)fail(field+'_COUNT');
 const normalized=value.map(v=>clean(v,MAX_ENTRY_BYTES,field));
 if(new Set(normalized.map(v=>v.toLocaleLowerCase('und'))).size!==normalized.length)fail(field+'_DUPLICATE');return normalized;
}
function exactShape(input){
 if(!input||typeof input!=='object'||Array.isArray(input))fail('GOAL_INPUT_TYPE');
 const keys=Object.keys(input);for(const field of REQUIRED)if(!Object.hasOwn(input,field))fail(field.toUpperCase()+'_MISSING');
 if(keys.some(key=>!REQUIRED.includes(key)))fail('GOAL_UNKNOWN_FIELD');
}

export function normalizeGoal(input){
 exactShape(input);
 if(typeof input.money_budget!=='number'||!Number.isSafeInteger(input.money_budget))fail('MONEY_BUDGET_TYPE');
 if(input.money_budget!==0)fail('MONEY_BUDGET_POLICY');
 if(typeof input.max_parallel!=='number'||!Number.isSafeInteger(input.max_parallel))fail('MAX_PARALLEL_TYPE');
 if(input.max_parallel!==1)fail('MAX_PARALLEL_POLICY');
 const proposal={schema:GOAL_SCHEMA,goal:clean(input.goal,MAX_GOAL_BYTES,'GOAL'),constraints:entries(input.constraints,'CONSTRAINTS'),prohibitions:entries(input.prohibitions,'PROHIBITIONS'),money_budget:input.money_budget,max_parallel:input.max_parallel,action_authority:false};
 if(bytes(JSON.stringify(proposal))>MAX_PROPOSAL_BYTES)fail('GOAL_PROPOSAL_LIMIT');return proposal;
}

export function validateGoalProposal(value){
 if(!value||typeof value!=='object'||Array.isArray(value))fail('GOAL_PROPOSAL_TYPE');
 const keys=Object.keys(value);for(const field of PROPOSAL_REQUIRED)if(!Object.hasOwn(value,field))fail(field.toUpperCase()+'_MISSING');
 if(keys.some(key=>!PROPOSAL_REQUIRED.includes(key)))fail('GOAL_PROPOSAL_UNKNOWN_FIELD');
 if(value.schema!==GOAL_SCHEMA)fail('GOAL_PROPOSAL_SCHEMA');if(value.action_authority!==false)fail('GOAL_PROPOSAL_AUTHORITY');
 const normalized=normalizeGoal({goal:value.goal,constraints:value.constraints,prohibitions:value.prohibitions,money_budget:value.money_budget,max_parallel:value.max_parallel});
 if(value.goal!==normalized.goal||value.constraints.some((v,i)=>v!==normalized.constraints[i])||value.prohibitions.some((v,i)=>v!==normalized.prohibitions[i]))fail('GOAL_PROPOSAL_NOT_CANONICAL');
 return normalized;
}

const lines=value=>typeof value==='string'?value.split(/\r?\n/u).map(v=>v.trim()).filter(Boolean):fail('GOAL_FORM_TYPE');
const integer=(value,field)=>{if(typeof value!=='string'||! /^(?:0|[1-9]\d*)$/u.test(value))fail(field+'_TYPE');const number=Number(value);if(!Number.isSafeInteger(number))fail(field+'_TYPE');return number;};
export function normalizeGoalForm({goal,constraints,prohibitions,moneyBudget,maxParallel}={}){
 return normalizeGoal({goal,constraints:lines(constraints),prohibitions:lines(prohibitions),money_budget:integer(moneyBudget,'MONEY_BUDGET'),max_parallel:integer(maxParallel,'MAX_PARALLEL')});
}
