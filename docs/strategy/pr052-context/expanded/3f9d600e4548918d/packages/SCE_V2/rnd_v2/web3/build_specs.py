"""Regenerate specification JSON and demo-only fixtures; does not run a bot."""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from qualification import canonical_hash, file_hash, evaluate
ROOT = Path(__file__).resolve().parent
SPEC = ROOT / 'workflows'
SPEC.mkdir(exist_ok=True)

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

specs = [
('repo_inventory','Сверка полного репозитория и входных данных',[],['repo_snapshot','source_manifest'],['Фиксировать exact revision + dirty diff + submodules + LFS pointers separately','Сопоставлять полный путь/ordinal/bytes/hash между ожидаемым и прочитанным manifest','Отдельно сохранять unreadable/binary/excluded и причину'],['inventory_diff.v1','completeness_report'],['No silently omitted files; unresolved LFS or missing submodule remains UNKNOWN']),
('toolchain_build','Воспроизводимая сборка',['repo_inventory'],['lockfiles','compiler_versions','build_recipe'],['Проверять pinned dependency/runner/compiler versions','Собирать из isolated snapshot без live signer','Сохранять stdout/stderr/exit/tool versions и hashes compiled outputs'],['build_receipt','binary_manifest'],['Successful clean build; compiler warnings triaged; no secret embedded']),
('static_smells','Детерминированные code smells и проверка гипотез',['repo_inventory'],['sources','ruleset_sha256'],['Запускать language-specific AST/rules adapters','Laya ранжирует находки, но не закрывает их как исправленные','Сохранять file/range/rule/matched excerpt/repro и false-positive decision'],['finding_ledger','rule_run_receipt'],['Every suppressed finding has provenance; model belief is not test evidence']),
('unit_contracts','Unit и boundary regression',['toolchain_build'],['test_suite','requirements'],['Извлечь requirement→test mapping','Запустить exact unit selection и сохранить настоящий JUnit per testcase','Проверить repayment/rounding/config/nonce/decimal boundary cases'],['junit_xml.v1'],['Required named cases executed; no skipped/failure/error cases']),
('fuzz_campaign','Fuzz с corpus и seed',['unit_contracts'],['seed_set','corpus_hash','fuzz_budget'],['Пиновать seeds, tool version, cases/runs/depth и предел времени','Сохранять covered selectors, revert distribution, execution counts','Сжимать counterexample и добавлять regression test'],['campaign_metrics','counterexample','junit_xml.v1'],['Budgets actually reached; timeout or vacuous coverage does not pass']),
('stateful_invariants','Stateful invariants',['unit_contracts'],['invariant_spec','handler_config'],['Проверять balance accounting, authorization boundaries, atomic repayment, cleanup after revert','Измерять reachable handlers and non-vacuous execution','В Foundry учитывать runs/depth; для Solana выбрать отдельный harness после repo discovery'],['invariant_campaign','junit_xml.v1'],['No violation in recorded campaign; invariants not claimed exhaustive']),
('pinned_fork','Fork или local validator pinned state',['toolchain_build'],['network_adapter','anchor','protocol_addresses'],['Проверить chain/genesis, block/slot anchor and provider capabilities','EVM: bind blockHash and canonicality where supported; record actual tool support','Solana: record cluster, slot, account snapshots, program versions, commitment; do not call EVM fork equivalent'],['fork_or_validator_receipt','state_snapshot'],['Target protocol bytecode/program and state recorded; chain remains repo-dependent']),
('offline_replay','Детерминированный replay',['unit_contracts'],['immutable_market_dataset','replay_clock','strategy_config'],['Replay recorded event ordering with clock control','Compare decisions against expected behavior and aggregate reproducibility hashes','Track dropped/out-of-order events and rejected opportunities'],['replay_receipt','decision_log'],['OFFLINE_REPLAY only; does not satisfy paper observation']),
('market_collect','Сбор рыночных данных без подписи',[],['read_only_provider_scope','asset_universe','retention_policy'],['Collect selected RPC/API/subscription observations into append-only raw files','Preserve request id, network, time, anchor, provider id/version, raw response hash','Resume cursor and explicitly log gaps/throttling/provider errors'],['raw_market_manifest','collection_receipt'],['No signing/send method in collector capabilities; completeness/gaps explicit']),
('provider_compare','Сравнение независимых provider views',['market_collect'],['provider_set','same_anchor_queries'],['Normalize responses for same state anchor','Compute disagreements/latency/rate-limit/drop rates','Do not count two aliases to same upstream as demonstrated independent sources'],['provider_disagreement_report'],['Agreement scope and provider provenance recorded; disagreement triggers UNKNOWN']),
('oracle_freshness','Oracle и quote freshness',['market_collect'],['oracle_config','feed_identity','freshness_budget'],['Check timestamp/slot/block against configured source semantics','Inject stale quote and delayed oracle updates','Record every reject and any accepted stale candidate'],['freshness_cases','economics_samples.v1'],['No accepted candidate exceeds explicit freshness policy']),
('fees_and_costs','Полная стоимость opportunity',['offline_replay'],['cost_model','atomic_accounting_unit','fee_inputs'],['Record principal, flash/swap/network fees, slippage reserve, other known costs','Compute candidate net using integers in same accounting unit','Retain conversion source/timestamp and rejection reason'],['economics_samples.v1','cost_assumptions'],['Configured predicate only; model completeness and future profit not proven']),
('route_atomicity','Маршрут и атомарность',['pinned_fork','unit_contracts'],['route_template','protocol_adapters'],['Inject failure at each route step','Assert state rollback or compensation according to actual chain semantics','Test token decimals, transfer behaviors, pool liquidity boundaries'],['route_fault_cases','junit_xml.v1'],['Exact protocols/chain semantics qualified, not inferred from generic flashloan label']),
('slippage_stress','Slippage, liquidity и adverse timing',['fees_and_costs','pinned_fork'],['stress_grid','liquidity_states'],['Sweep liquidity/price movement/latency/fee shocks with immutable scenario ids','Separate invalid scenarios from adverse valid outcomes','Preserve worst-case failure and all accepted candidate cost computations'],['stress_surface','economics_samples.v1'],['No acceptance outside reviewed risk envelope; thresholds are configuration']),
('lender_repayment','Lender-neutral repayment contract',['route_atomicity'],['lender_adapter','repayment_cases'],['Verify principal+fee handling on exact adapter and chain','Inject insufficient repayment, authorization mismatch and wrong callback origin','Keep MarginFi work PAUSED unless separate current instruction resumes it'],['repayment_receipt','junit_xml.v1'],['No claim that a paused lender is implemented or live qualified']),
('paper_observation','Реальное paper-наблюдение',['market_collect','offline_replay'],['real_market_window','read_only_runtime','candidate_log'],['Observe current market via pinned provider config without signing or sending','Record gap/freshness/decision latencies and hypothetical outcomes with caveats','Separate actual observed quotes from modeled fills and offline replay'],['observation_window.v1','paper_economics','raw_rpc_manifest'],['Minimum chosen observation window/coverage met; simulated fills are not realized PnL']),
('fault_injection','Operational faults',['unit_contracts'],['fault_catalog','isolated_runner'],['Inject RPC disconnect, stale state, reorg signal, clock shift, disk full, restart','Check persistence cursor, retry idempotency, no duplicate dispatch','Record recovery time and missing evidence'],['fault_report','junit_xml.v1'],['Expected handling executed for every required fault; no production signing']),
('windows_device','Dell Windows 11 qualification',['toolchain_build'],['actual_device_profile','microphone','memory','disk'],['Benchmark cold/warm start, CPU/GPU/RAM and sustained heat under target workload','Test wake/sleep, network changes, microphone loss and disk pressure','Qualify installed runtime/provider/model separately from remote test runner'],['device_matrix','latency_measurements'],['Measured on actual Dell; Linux tests do not imply Windows readiness']),
('stop_and_pause','Пауза и остановка по голосу/кнопке',['fault_injection'],['stop_channel','cancel_token_protocol'],['Use accessible stop button plus configured voice alternative','Inject stop under load and process boundaries','Measure trigger-to-blocked dispatch with monotonic timestamps'],['stop_latency.v1'],['No forbidden dispatch after trigger; cancellation of pending external side effect verified separately']),
('release_artifact','Release, digest и rollback',['toolchain_build','unit_contracts'],['reviewed_commit','release_manifest','rollback_package'],['Download into staging and validate manifest/signed provenance via chosen verifier','Run migrations on a copied DB and health checks','Activate version atomically where supported; retain tested rollback including DB compatibility'],['release_manifest','migration_receipt','rollback_receipt'],['Artifact identity corresponds to reviewed revision; an archive download alone is not update qualification']),
('canary_plan','План ограниченного canary',['paper_observation','stop_and_pause','release_artifact'],['specific_operator_authorization','limits','expiry','network','signer_scope'],['Render exact proposed executable version/network/assets/limits and expiry','Check operational prerequisites and define immediate stop signals','Remain disabled in this R&D pack; no executable signing or broadcasting handler'],['canary_plan_only'],['Requires separate reviewed live authorization; offline TRUE never enables signer']),
('live_monitoring','Мониторинг уже разрешённого live',['canary_plan'],['authorized_runtime_id','read_only_telemetry','incident_policy'],['Read receipts, balances, nonce/sequence state, drawdown and provider health','Detect reconciliation differences, exposure/risk budget breach and config drift','Request/perform only preauthorized pause; propose further actions for operator'],['live_monitor_spec','incident_timeline'],['SPEC only here; no live runtime/transaction/watch task installed']),
('stale_invalidation','Инвалидация по изменению inputs',['repo_inventory'],['binding_before','binding_after','dependency_graph'],['Invalidate affected proofs on repo/config/data/provider/model/network/toolchain change','Recompute only nodes whose explicit dependency fingerprint changed','Keep earlier evidence readable as HISTORICAL, not current TRUE'],['invalidation_plan'],['No receipt reused across different binding without deliberate recomputation']),
('incident_replay','Incident→regression',['fault_injection'],['incident_bundle','redacted_logs','state_anchor'],['Snapshot evidence without deleting originals','Create minimal reproducer and deterministic test from observed failure','Patch in separate worktree; compare before/after under same scenario'],['incident_case','regression_receipt'],['Patch claim linked to failing-before/passing-after evidence']),
('qualification_packet','Пакет решения readiness',['unit_contracts','offline_replay','paper_observation','windows_device','stop_and_pause'],['all_explicit_receipts','reviewed_plan'],['Evaluate artifact integrity and exact bindings','Report own and dependency status per stage','Render TRUE/FALSE/UNKNOWN/NOT_RUN with reasons and no automatic live authorization'],['qualification.py report'],['Existing implemented offline verifier checks selected artifact contracts only']),
('coverage_holes','Поиск непроверенных требований',['repo_inventory','static_smells'],['goal_ledger','requirements','tests','receipts'],['Join goal ids→repo paths→required cases→current receipts','Distinguish no test, unexecuted test, failed test and stale result','Laya routes candidate next task; deterministic ledger counts coverage'],['coverage_gap_queue'],['No semantic completeness claim from a keyword match']),
('experiment_scheduler','Очередь R&D экспериментов',['coverage_holes'],['experiment_matrix','cost_budget','resource_locks'],['Compile typed tasks into existing automation_core queue','Parallelize read-only independent stages; isolate repo worktrees and shared devices','Checkpoint progress and resume exact failed nodes with idempotency keys'],['experiment_queue_spec'],['No second canonical production executor; schedule not installed by this pack']),
('voice_goal_binding','Голосовая цель→проверяемый Web3 план',[],['transcript','explicit_goal','current_context_manifest'],['Preserve transcript span/time and intent revision','Retrieve cited requirements and repo snapshot; disambiguate observe/test/deploy/live','Laya selects template or abstains; goal changes create new plan hash'],['typed_goal','qualification_plan_draft'],['Uncertain chain/asset/action stays unresolved; model does not self-authorize trading']),
]

functions = []
implemented = [
('evidence.validate_plan','Проверка типизированного плана и DAG этапов'),
('evidence.bind_revision','Сравнение exact repo/config/input/environment/network/anchor/provider/model/toolchain'),
('evidence.verify_artifacts','Потоковая проверка bytes/SHA256 и contained paths'),
('evidence.invalidate_stale','Срок актуальности, будущие timestamps и несовпадение plan hash'),
('evidence.require_machine_receipt','Проверка pinned runner identity вместо текста/успешного boolean'),
('evidence.inventory_diff','Сверка полного path+ordinal manifest'),
('evidence.junit_cases','Проверка реальных записей testcase, failure/error/skipped и требуемых названий'),
('evidence.economic_predicates','Пересчёт net cost в integer atomic units и freshness accepted candidates'),
('evidence.observation_window','Длительность/gaps/provider ids/paper-only/source freshness по журналу'),
('evidence.stop_latency','Проверка записанных stop latency и запрещённых dispatch после trigger'),
('evidence.propagate_dependencies','Раздельный own status и readiness с учётом зависимостей'),
('evidence.four_states','TRUE/FALSE/UNKNOWN/NOT_RUN, причины и неизменное live_authorized=false'),
('evidence.refuse_ambiguous_receipts','Отказ от скрытого выбора между несколькими receipts'),
]
for idx,(fid,title) in enumerate(implemented,1):
    functions.append({'id':f'W3-F{idx:02d}','function':fid,'title_ru':title,'status':'IMPLEMENTED_OFFLINE_PROTOTYPE','owner_candidate':'content-lab/context_review.py + automation_core.py canonical queue adapter','implementation':'qualification.py','actual_bot_validation':'NOT_RUN'})
for idx,(sid,title,deps,inputs,steps,outputs,criteria) in enumerate(specs,1):
    data={'schema':'web3-workflow-spec/v1','id':f'W3-WF{idx:02d}','name':sid,'title_ru':title,'status':'SPEC_NOT_EXECUTABLE','enabled':False,
          'trigger_candidates':['manual_goal','new_snapshot','receipt_invalidated'] if sid not in {'market_collect','live_monitoring'} else ['explicitly_configured_read_only_watch'],
          'depends_on':deps,'inputs':inputs,'steps':[{'id':f'{sid}.{n}','handler':'PROPOSED.'+sid+'.'+str(n),'instruction':s} for n,s in enumerate(steps,1)],
          'outputs':outputs,'qualification_criteria':criteria,'on_missing_evidence':'UNKNOWN','idempotency_key':'sha256(workflow_id + goal_revision + exact_binding + step_inputs)',
          'execution_owner':'existing SCE automation_core.py queue, future reviewed adapter','laya_role':'advisory template/risk/task routing with abstention; no evidence fabrication','network_scope':'repo-dependent; unknown until actual bot repository is inspected','live_authorized':False,'signing_handler_present':False}
    write(SPEC/f'{idx:02d}_{sid}.SPEC.json',data)
    functions.append({'id':f'W3-F{len(implemented)+idx:02d}','function':'web3.'+sid,'title_ru':title,'status':'SPEC_NOT_EXECUTABLE','workflow_id':data['id'],'path':'workflows/'+f'{idx:02d}_{sid}.SPEC.json','actual_bot_validation':'NOT_RUN'})
write(ROOT/'FUNCTIONS_WEB3.json',{'schema':'function-catalog/v1','implemented_offline_count':len(implemented),'spec_only_count':len(specs),'functions':functions})

experiments = [
('W3-E01','Replay reproducibility','same event dataset+seed+clock','different decision/artifact digests','exact match or explained nondeterminism','OFFLINE_ONLY'),
('W3-E02','Stale quote rejection','delay quotes above reviewed budget','accepted stale candidate','zero such acceptances over recorded cases','OFFLINE_ONLY'),
('W3-E03','Full cost accounting','sweep each fee and token decimals','accepted net below configured threshold','integer recomputation and matching accounting unit','OFFLINE_ONLY'),
('W3-E04','Repayment boundaries','principal/fee/rounding edge cases','invariant failure / unauthorized callback','required cases execute with true machine receipts','CHAIN_ADAPTER_REQUIRED'),
('W3-E05','Stateful invariant non-vacuity','handler runs/depth/corpus','zero useful handler calls or hidden revert loop','reviewed campaign coverage reached','CHAIN_ADAPTER_REQUIRED'),
('W3-E06','Provider inconsistency','same-anchor responses from distinct upstreams','unexpected divergence','divergence yields UNKNOWN and pause candidate','READ_ONLY_NETWORK_SPEC'),
('W3-E07','Reorg/slot change','replace canonical anchor or source view','old proof stays TRUE','invalidate affected evidence by exact binding','OFFLINE_ONLY'),
('W3-E08','Observation vs replay','supply replay artifact for paper stage','replay classified as market observation','refuse mode mismatch','OFFLINE_ONLY'),
('W3-E09','RPC quota and disconnect','429/timeout/drop','unbounded retry or cursor loss','bounded backoff + explicit gap ledger','ISOLATED_RUNNER_SPEC'),
('W3-E10','Stop latency','voice/button stop under CPU load','post-trigger forbidden dispatch','measured latency distribution within reviewed target','WINDOWS_DEVICE_REQUIRED'),
('W3-E11','Update rollback','failed migration/new version health check','library corruption or inability to restore','copy migration + tested compatible rollback','WINDOWS_DEVICE_REQUIRED'),
('W3-E12','Wrong network protection','network/genesis mismatch','receipt passes despite wrong chain','UNKNOWN mismatch and no side effect','OFFLINE_ONLY'),
('W3-E13','Evidence corruption','alter one artifact byte','same TRUE status','FALSE hash integrity status','OFFLINE_ONLY'),
('W3-E14','False claim robustness','success=true / AI text / empty JUnit','any automatic ready-for-live','UNKNOWN or FALSE; live_authorized always false','OFFLINE_ONLY'),
('W3-E15','Device sustained performance','Dell CPU/RAM/GPU heating + voice + indexing','p99 delay exceeds actual target','measured local profile; no remote extrapolation','WINDOWS_DEVICE_REQUIRED'),
('W3-E16','Worktree isolation','two parallel patch/test tasks','shared state/test pollution','separate roots+locked shared resources+exact versions','LOCAL_RUNNER_SPEC'),
('W3-E17','Secret isolation','fixture fake key in repository/log','key in model context or exported text','secret policy catches fixtures; authorized raw retained locally','SYNTHETIC_FIXTURES_ONLY'),
('W3-E18','Paper economics honesty','modeled fills vs observed quotes','hypothetical PnL labeled realized','separate metrics and assumptions stored','READ_ONLY_NETWORK_SPEC'),
]
with (ROOT/'EXPERIMENT_MATRIX.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['id','experiment','intervention','failure_signal','candidate_acceptance','execution_status']);w.writerows([(*r,'NOT_RUN') for r in experiments])
# Header must include both mode and execution status.
p=ROOT/'EXPERIMENT_MATRIX.csv';s=p.read_text(encoding='utf-8-sig');s=s.replace('candidate_acceptance,execution_status','candidate_acceptance,mode,execution_status',1);p.write_text(s,encoding='utf-8-sig')
write(ROOT/'SOURCES_WEB3.json',{'checked_at':'2026-10-03','scope':'Primary sources only. Architecture below is a proposed design, not a source claim.', 'sources':[
{'id':'W3-S01','url':'https://eips.ethereum.org/EIPS/eip-1898','claim_ru':'EVM state queries may specify blockHash and requireCanonical; actual provider support must be tested.','ref':'turn13view0'},
{'id':'W3-S02','url':'https://ethereum.org/developers/docs/apis/json-rpc/','claim_ru':'Ethereum RPC block selectors and block identity; no assumption that the actual bot is EVM.','ref':'turn13view1'},
{'id':'W3-S03','url':'https://solana.com/docs/rpc','claim_ru':'Solana cluster endpoints and distinct processed/confirmed/finalized commitment levels.','ref':'turn16view0'},
{'id':'W3-S04','url':'https://getfoundry.sh/forge/invariant-testing','claim_ru':'Foundry invariant campaigns use runs/depth and need target/handler coverage. Indexed official page; direct open returned content-type error.','ref':'turn12search0'}]})

# Small synthetic fixture demonstrates evaluator behavior, never actual bot readiness.
EX = ROOT/'examples'; EX.mkdir(exist_ok=True)
config={'synthetic_fixture':True,'never_trade':True};env={'environment':'synthetic documentation fixture'}
write(EX/'config.json',config);write(EX/'environment.json',env)
manifest=[{'path':'synthetic/repayment.py','ordinal':0,'bytes':11,'sha256':hashlib.sha256(b'fixture only').hexdigest()}]
(EX/'expected.jsonl').write_text(json.dumps(manifest[0])+'\n');(EX/'observed.jsonl').write_text((EX/'expected.jsonl').read_text())
(EX/'tests.xml').write_text('<testsuite><testcase classname="fixture" name="repayment"/><testcase classname="fixture" name="stale_quote"/><testcase classname="fixture" name="stop"/></testsuite>')
(EX/'costs.jsonl').write_text(json.dumps({'sample_id':'synthetic-1','accounting_unit':'FIXTURE_ATOMIC','proceeds_minor':120,'principal_minor':100,'flash_fee_minor':1,'swap_fee_minor':1,'network_fee_minor':1,'slippage_reserve_minor':1,'other_cost_minor':1,'quote_age_ms':10,'decision':'ACCEPT'})+'\n')
observations=[]
for i in range(2):
    t=f'2026-10-03T16:{58+i}:00Z'
    observations.append({'sample_id':f'synthetic-{i}','mode':'OFFLINE_REPLAY','network_id':'fixture:1','anchor_hash':f'fixture-{i}','height':str(i),'finality':'fixture','observed_at':t,'source_at':t,'provider_id':'synthetic-provider','signed_transactions':0,'sent_transactions':0})
(EX/'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in observations))
(EX/'stop.jsonl').write_text(json.dumps({'probe_id':'synthetic-1','fault':'rpc_timeout','trigger_monotonic_ns':1000000000,'blocked_monotonic_ns':1010000000,'forbidden_dispatches_after_trigger':0})+'\n')
binding={'repo_revision':'0'*40,'config_sha256':file_hash(EX/'config.json'),'input_manifest_sha256':file_hash(EX/'expected.jsonl'),'environment_sha256':file_hash(EX/'environment.json'),'network':{'family':'offline_fixture','network_id':'fixture:1','genesis_hash':'synthetic'},'anchor':{'height':'0','hash':'synthetic','finality':'fixture'},'provider':{'id':'synthetic','version':'1'},'model':{'id':'none','revision':'none'},'toolchain':{'fixture_generator':'build_specs.py/v1'}}
producer={'id':'synthetic-fixture-generator','version':'1','binary_sha256':file_hash(Path(__file__))}
stage_data=[('inventory','inventory_diff.v1',[],{'min_entries':1},[('expected_manifest','expected.jsonl'),('observed_manifest','observed.jsonl')]),('unit','junit_xml.v1',['inventory'],{'min_cases':3,'required_name_fragments':['repayment','stale_quote','stop']},[('test_results','tests.xml')]),('cost','economics_samples.v1',['unit'],{'min_samples':1,'min_accepted':1,'max_quote_age_ms':100,'min_net_minor':1,'accounting_unit':'FIXTURE_ATOMIC'},[('economics','costs.jsonl')]),('observation','observation_window.v1',['cost'],{'min_samples':2,'min_duration_seconds':60,'max_gap_seconds':60,'min_providers':1,'max_source_age_ms':1000,'mode':'OFFLINE_REPLAY'},[('observations','observations.jsonl')]),('stop','stop_latency.v1',['unit'],{'min_probes':1,'max_stop_latency_ms':50,'required_faults':['rpc_timeout']},[('stop_probes','stop.jsonl')])]
plan={'schema':'web3-qualification/v1','campaign_id':'SYNTHETIC_FIXTURE_NOT_ACTUAL_BOT','status':'RND_EXAMPLE_NOT_OPERATIONAL','live_authorized':False,'binding':binding,'stages':[{'id':sid,'adapter':adapter,'depends_on':deps,'producer':producer,'max_age_seconds':3600,'criteria':criteria} for sid,adapter,deps,criteria,_ in stage_data]}
write(EX/'plan.SYNTHETIC.json',plan)
receipts=[]
for sid,adapter,_,_,arts in stage_data:
    r={'schema':'web3-qualification/v1/receipt','campaign_id':plan['campaign_id'],'plan_sha256':canonical_hash(plan),'stage_id':sid,'adapter':adapter,'binding':binding,'producer':dict(producer,kind='machine_runner'),'started_at':'2026-10-03T16:50:00Z','completed_at':'2026-10-03T16:59:30Z','process':{'state':'EXITED','exit_code':0},'artifacts':[{'role':role,'path':name,'bytes':(EX/name).stat().st_size,'sha256':file_hash(EX/name)} for role,name in arts]}
    write(EX/f'receipt_{sid}.SYNTHETIC.json',r);receipts.append(r)
write(EX/'REPORT.SYNTHETIC.json',evaluate(plan,receipts,EX,dt.datetime(2026,10,3,17,0,tzinfo=dt.timezone.utc)))
print(json.dumps({'specs':len(specs),'implemented_functions':len(implemented),'spec_functions':len(specs),'experiments':len(experiments)}))
