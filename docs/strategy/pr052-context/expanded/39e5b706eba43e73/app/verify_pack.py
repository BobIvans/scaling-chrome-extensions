"""Independent pack verifier: objective checks, no model inference."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import zipfile

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def verify(root):
    root=Path(root).resolve()
    index=json.loads((root/'index.json').read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in (root/'files.jsonl').read_text(encoding='utf-8').splitlines()]
    checks=[]
    def check(key,truth,reason):checks.append({'criterion':key,'truth':truth,'reason':reason})
    check('entry_count','TRUE' if len(rows)==index['entries'] else 'FALSE',{'manifest':len(rows),'index':index['entries']})
    def object_path(relative):
        path=(root/relative).resolve()
        if not path.is_relative_to(root):raise ValueError('PATH_OUTSIDE_PACK')
        return path
    errors=[]
    for row in rows:
        if row['sha256']:
            try:
                p=object_path(row['original_object'])
                if sha(p)!=row['sha256'] or p.stat().st_size!=row['size']:errors.append(row['id'])
            except (OSError,ValueError):errors.append(row['id'])
        elif row['kind']!='directory':errors.append(row['id'])
    check('all_entry_originals_integrity','FALSE' if errors else 'TRUE',{'failed_entry_ids':errors})
    part_errors=[]
    for part in index['parts']:
        try:
            p=object_path(part['path'])
            if sha(p)!=part['sha256'] or p.stat().st_size!=part['bytes']:part_errors.append(part['path'])
            p.read_bytes().decode('utf-8')
        except (OSError,ValueError):part_errors.append(part['path'])
    check('txt_part_integrity','FALSE' if part_errors else 'TRUE',{'failed_parts':part_errors})
    snapshot=index['snapshot']
    if snapshot.get('archive_sha'):
        try:
            archive=object_path('originals/'+snapshot['archive_sha'])
            good=sha(archive)==snapshot['archive_sha']
            with zipfile.ZipFile(archive) as z:
                expected=[i.filename for i in z.infolist()]
            actual=[r['path'] for r in sorted(rows,key=lambda r:r['ordinal'])]
            check('zip_inventory_paths_occurrences','TRUE' if good and actual==expected else 'FALSE',{'expected':len(expected),'actual':len(actual)})
        except (OSError,ValueError,zipfile.BadZipFile):check('zip_inventory_paths_occurrences','FALSE','Missing or damaged original archive')
    else:
        check('zip_inventory_paths_occurrences','UNKNOWN','Folder scan has no immutable archive inventory')
    gaps=[r['id'] for r in rows if r['text_state'] not in ('TEXT_COMPLETE','METADATA_ONLY')]
    check('all_entries_have_text_derivative','FALSE' if gaps else 'TRUE',{'non_text_or_error_entry_ids':gaps})
    check('ai_review_complete','NOT_RUN','This verifier checks package integrity, not AI reasoning or code behavior.')
    check('flashloan_ready','NOT_RUN','Bot runtime and qualification not executed.')
    return {'schema':'sce.pack-verification.v1','index_sha256':sha(root/'index.json'),'checks':checks,
            'laya_called':False,'financial_authority':False}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('pack')
    p.add_argument('--output',required=True)
    a=p.parse_args()
    result=verify(a.pack)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2))
