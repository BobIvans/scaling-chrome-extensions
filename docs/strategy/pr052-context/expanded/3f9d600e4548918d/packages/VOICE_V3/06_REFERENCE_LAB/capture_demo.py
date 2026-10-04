"""Synthetic multi-channel recording demo. No microphone, API, browser or bot."""
from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
from agentos_lab.observations import Observation, ObservationJournal, Producer, collect_complementary, fuse_claims, readiness
from agentos_lab.resources import TaskFootprint, independent_batches

async def main(output: Path):
    output.mkdir(parents=True,exist_ok=True)
    journal=ObservationJournal(output/'observations.sqlite3')
    fixtures=[
        ('voice',b'Continue repo research, no live trading',0,'intent-1',False),
        ('dom',b'Qualification blocked by missing evidence',.004,'message-17',True),
        ('export',b'Qualification blocked by missing evidence',.008,'message-17',False),
        ('git',b'synthetic sha1; current snapshot',.002,'git-sha1',False),
        ('test_log',b'SYNTHETIC_ONLY dependency unavailable',.006,'test-run-demo',False),
    ]
    producers=[]
    for name,payload,delay,root,partial in fixtures:
        def make_stream(n=name,p=payload,d=delay,r=root,pa=partial):
            async def stream():
                await asyncio.sleep(d)
                yield Observation('demo',n,0,'fixture://'+n,'revision-demo',r,n,int(d*1e9),p,pa)
            return stream
        producers.append(Producer(name,make_stream()))
    report=await collect_complementary(journal,'demo',producers,max_pending=2)
    report['demo_scope']='SYNTHETIC_ONLY_NOT_DEVICE_BENCHMARK'
    report['stored_observations']=len(journal.read('demo'))
    report['stored_unique_raw_objects']=journal.object_count()
    report['readiness_example']=readiness({'intent','snapshot','failure_evidence'},
                                        {'intent','snapshot','failure_evidence'},snapshot_current=True)
    report['independent_action_batches']=independent_batches([
        TaskFootprint('save_report',writes=frozenset({'report:new'})),
        TaskFootprint('prepare_patch_A',writes=frozenset({'worktree:A'})),
        TaskFootprint('prepare_patch_B',writes=frozenset({'worktree:B'})),
        TaskFootprint('foreground_action_A',foreground='desktop'),
        TaskFootprint('foreground_action_B',foreground='desktop'),
    ],max_parallel=3)
    report['source_lineage_example']=fuse_claims([
        dict(subject='qualification',predicate='state',value='blocked',source_revision='sha1',lineage_root='message-17',source_ref='dom'),
        dict(subject='qualification',predicate='state',value='blocked',source_revision='sha1',lineage_root='message-17',source_ref='export'),
    ])
    text=json.dumps(report,ensure_ascii=False,indent=2)
    (output/'capture-result.json').write_text(text+'\n',encoding='utf-8')
    print(text)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('capture-demo-output'))
    args=parser.parse_args()
    asyncio.run(main(args.output))
