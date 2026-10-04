#!/usr/bin/env python3
"""Validate R&D proposal consistency only. No capability is executed."""
from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[1]
known={c['id'] for c in json.loads((root/'schemas/CAPABILITY_CANDIDATES.json').read_text())}
errors=[]; count=0
for path in sorted((root/'workflows').glob('*.json')):
    count+=1
    try:
        p=json.loads(path.read_text(encoding='utf-8'))
        assert p['schema']=='occ.rnd.workflow.v1'
        assert p['status']=='PROPOSAL_NOT_EXECUTED'
        assert p['ready_for_automatic_execution'] is False
        assert p['native_laya_request'] is False
        assert p['money_budget']==0 and not p['signer_access'] and not p['live_trading']
        seen=set()
        for node in p['nodes']:
            assert node['id'] not in seen
            assert node['capability_id'] in known
            assert set(node['depends_on']) <= seen
            assert node['on_failure']=='BLOCK_AND_REPORT'
            seen.add(node['id'])
    except (AssertionError,KeyError,ValueError) as e:
        errors.append(path.name+': '+type(e).__name__)
print(json.dumps({'state':'VALIDATED_PROPOSALS_ONLY' if not errors else 'FAILED',
                  'workflows_checked':count,'executed':0,'errors':errors},indent=2))
sys.exit(bool(errors))
