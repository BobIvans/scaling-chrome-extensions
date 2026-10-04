from pathlib import Path
import hashlib, json, sys
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
failures=[]
for item in manifest['files']:
    path=(root/item['path']).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        failures.append({'path':item['path'],'reason':'MISSING_OR_OUTSIDE_ROOT'});continue
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    if path.stat().st_size!=item['size_bytes'] or h.hexdigest()!=item['sha256']:
        failures.append({'path':item['path'],'reason':'SIZE_OR_HASH_MISMATCH'})
rows=json.loads((root/'evidence/PR001_021_STATUS.json').read_text(encoding='utf-8'))['packages']
if sorted(x['roadmap_number'] for x in rows)!=list(range(1,22)):failures.append({'reason':'21_PACKAGE_COVERAGE'})
print(json.dumps({'ok':not failures,'files_checked':len(manifest['files']),'roadmap_packages':len(rows),'failures':failures},ensure_ascii=False))
sys.exit(bool(failures))
