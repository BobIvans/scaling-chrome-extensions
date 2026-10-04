# Сверенные inputs №5 / №6 / №7

| Package | Owner scope | Evidence |
| --- | --- | --- |
| №3 | Saved payload ZIP/offline index/resume | Input ZIP and contract refs checked; runtime not verified |
| №4 | Streaming Git inventory CLI | Own prepared input; runtime not verified |
| №5 | Formats/gaps/eligibility | Input ZIP and exact schema checked; actual facts/implementation not verified |
| №6 | Python related groups/SCC/tests/contracts | Input ZIP and policy checked; implementation not verified |
| №7 | JS/TS AST + conservative source refs | This prepared input; AST/runtime NOT_RUN |

№5 facts: analysis.format_eligibility / occ.format-eligibility.v1 /
utf8-controls-strict-lfs3.v1. Bound snapshot/path/ordinal/OID/size/hash must match.
Text ELIGIBLE + raw RECORDED alone не byte proof; №7 independently reconstructs
captured chunks. Use contracts/PR005_ADAPTER_MAP.json, no duplicate classifier.

№6: PYTHON_RAW_REFERENCE_GROUPS_V1, occ.repo-group-relation.v1, accepted topology
PYTHON_STATIC_IMPORT/STATIC_TEST_IMPORT. Он не принимает JS dialect №7 без
versioned consumer и новой policy. Не append/overwrite его RELATIONS.jsonl.
Raw chunks, IDs/revisions и Python groups не меняются в этом diff.
contracts/PR006_ADAPTER_MAP.json фиксирует эту точную границу.

В input №6 old PR005 preflight был unmapped. Он сохранён как original reference;
map №7 к полученному №5 дополняет знания, не выдумывает actual implementation.
Нужны current SHA/diff/runtime receipts обоих PR, затем actual semantic checks.
Numbering закреплено. Все 160 tasks open; inputs не означают merged capability.
