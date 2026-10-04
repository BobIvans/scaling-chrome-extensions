"""Executable offline workflow: import, inventory, export. Unknown steps fail closed."""
import argparse
import json
from pathlib import Path
from context_store import Store

def run(recipe,library,source,destination):
    expected=['import_source','export_snapshot']
    if recipe.get('schema')!='sce.offline-recipe.v1' or recipe.get('steps')!=expected:
        raise ValueError('Only the implemented import_source → export_snapshot recipe is executable.')
    s=Store(library)
    try:
        sid=s.import_source(source)
        snapshot=next(x for x in s.snapshots() if x['id']==sid)
        if snapshot['state']!='COMPLETE':
            raise ValueError('Import is not COMPLETE; inspect snapshot '+sid)
        result=s.export(sid,destination,recipe.get('part_bytes',200000))
        return {'snapshot':sid,'export':str(Path(destination).resolve()),'coverage':result['coverage'],'laya_called':False}
    finally:s.close()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--recipe',required=True)
    p.add_argument('--library',required=True)
    p.add_argument('--source',required=True)
    p.add_argument('--destination',required=True)
    a=p.parse_args()
    print(json.dumps(run(json.loads(Path(a.recipe).read_text(encoding='utf-8')),a.library,a.source,a.destination),indent=2))
